"""The MOCK 'AI engine' behind the mock transport.

Given the uploaded bytes and a documented request payload it returns a result
dict shaped exactly like YouCam's success response, plus the image files that
the result URLs point to.  Sample-persona photos get hand-written fixture
scores; any other photo gets deterministic hash-seeded scores.
"""
from __future__ import annotations

import hashlib
import random

from PIL import Image

from . import render
from .personas import PERSONAS, identify

DEFAULT_TEMPLATES = {
    # Placeholder template list in the documented shape; live mode lists the real ones.
    "beard_style": [
        {"id": "mock_beard_short_boxed", "title": "Short Boxed", "category_name": "Beard", "style": "short_boxed"},
        {"id": "mock_beard_stubble", "title": "Designer Stubble", "category_name": "Beard", "style": "stubble"},
        {"id": "mock_beard_full", "title": "Full Beard", "category_name": "Beard", "style": "full"},
        {"id": "mock_beard_goatee", "title": "Goatee", "category_name": "Beard", "style": "goatee"},
        {"id": "mock_beard_clean", "title": "Clean Shave", "category_name": "Beard", "style": "clean"},
    ],
}

SIM_KEYS = ["wrinkle", "radiance", "oiliness", "acne", "eye_bags", "dark_circle", "spots", "pores", "texture",
            "redness"]


def _seed(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def _raw(ui: int, rng: random.Random) -> float:
    # ui_score is the calibrated, friendlier number; raw_score sits lower (see docs).
    return round(max(1.0, min(99.0, ui * 1.45 - 38 + rng.uniform(-4, 4))), 2)


class MockEngine:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    # ------------------------------------------------------------ skin analysis
    def skin_analysis(self, image: bytes, payload: dict) -> tuple[dict, dict[str, bytes]]:
        img = render.to_img(image)
        pid, variant = identify(image)
        g = render.geometry_for(img.size, pid, variant or "face")
        acts = payload["dst_actions"]
        rng = random.Random(_seed("skin", hashlib.sha256(image).hexdigest()))
        fixture = PERSONAS.get(pid, {}) if pid else {}
        output, files = [], {}
        overlay = bool((payload.get("miniserver_args") or {}).get("enable_mask_overlay"))
        for a in acts:
            base = a[3:] if a.startswith("hd_") else a
            base = "dark_circle_v2" if base == "dark_circle" else base
            if base == "skin_type":
                types = fixture.get("skin_type") or rng.choice(
                    [["Combination", "Oily", "Normal"], ["Normal", "Normal", "Dry"], ["Oily", "Oily", "Combination"]])
                mask = render.render_concern_mask(img.size, g, "skin_type", 50, _seed(a))
                for region, st in zip(("whole", "t_zone", "u_zone"), types):
                    name = f"{a}_{region}.png"
                    files[name] = render.png(mask)
                    output.append({"type": a, "region": region, "skin_type": st, "mask_urls": [name]})
                continue
            ui = int(fixture.get("scores", {}).get(base, rng.randint(52, 90)))
            mask = render.render_concern_mask(img.size, g, base, ui, _seed(a, ui))
            if overlay:
                name = f"{a}_output.jpg"
                files[name] = render.jpeg(render.overlay_masks(img, [mask]))
            else:
                name = f"{a}_output.png"
                files[name] = render.png(mask)
            output.append({"type": a, "raw_score": _raw(ui, rng), "ui_score": ui, "mask_urls": [name]})
        scored = [o["ui_score"] for o in output if "ui_score" in o]
        overall = round(sum(scored) / len(scored), 2) if scored else 70.0
        output.append({"type": "skin_age", "score": fixture.get("skin_age", rng.randint(22, 34))})
        output.append({"type": "all", "score": overall})
        files["resized_image.jpg"] = render.jpeg(img)
        output.append({"type": "resize_image", "mask_urls": ["resized_image.jpg"]})
        if payload.get("format", "zip") == "zip":
            return {"url": "skin_result.zip"}, files   # not used by ShaadiGlow (we ask for json)
        return {"output": output}, files

    # ------------------------------------------------------------ image-out features
    def skin_simulation(self, image: bytes, payload: dict) -> tuple[dict, dict[str, bytes]]:
        img = render.to_img(image)
        pid, variant = identify(image)
        g = render.geometry_for(img.size, pid, variant or "face")
        skin = render.persona_mask(pid, variant or "face", "skin", img.size)
        out = render.render_skin_simulation(img, g, {k: payload.get(k, 0) for k in SIM_KEYS}, skin)
        return {"url": "result.jpg"}, {"result.jpg": render.jpeg(out)}

    def makeup_vto(self, image: bytes, payload: dict) -> tuple[dict, dict[str, bytes]]:
        img = render.to_img(image)
        pid, variant = identify(image)
        g = render.geometry_for(img.size, pid, variant or "face")
        skin = render.persona_mask(pid, variant or "face", "skin", img.size)
        out = render.render_makeup(img, g, payload.get("effects", []), skin)
        return {"url": "result.jpg"}, {"result.jpg": render.jpeg(out)}

    def hair_color(self, image: bytes, payload: dict) -> tuple[dict, dict[str, bytes]]:
        img = render.to_img(image)
        pid, variant = identify(image)
        v = variant or "portrait"
        g = render.geometry_for(img.size, pid, v)
        hair = render.persona_mask(pid, v, "hair", img.size)
        if hair is None:
            hair = render.heuristic_hair_mask(img, g)
        pal = payload.get("palettes") or []
        colors = [p["color"] for p in pal] or [PRESET_HEX.get(payload.get("preset", ""), "#4A1C1C")]
        if "/" in (payload.get("preset") or "") and not pal:
            colors = [PRESET_HEX.get(c.strip(), "#5a3a2a") for c in payload["preset"].split("/")]
        ombre = (payload.get("pattern") or {}).get("name") == "ombre" or len(colors) > 1
        k = (pal[0].get("color_intensity", 75) if pal else 75) / 100.0
        out = render.render_hair_color(img, hair, colors, intensity=0.55 + 0.4 * k, ombre=ombre)
        return {"url": "result.jpg"}, {"result.jpg": render.jpeg(out)}

    def beard_style(self, image: bytes, payload: dict) -> tuple[dict, dict[str, bytes]]:
        img = render.to_img(image)
        pid, variant = identify(image)
        g = render.geometry_for(img.size, pid, variant or "beard")
        style = next((t["style"] for t in DEFAULT_TEMPLATES["beard_style"] if t["id"] == payload.get("template_id")),
                     "short_boxed")
        out = render.render_beard(img, g, style)
        return {"url": "result.jpg"}, {"result.jpg": render.jpeg(out)}

    def _jewellery(self, image: bytes, ref: bytes, kind: str) -> tuple[dict, dict[str, bytes]]:
        img = render.to_img(image)
        pid, variant = identify(image)
        v = variant or "portrait"
        g = render.geometry_for(img.size, pid, v)
        item = _ref_rgba(ref)
        if kind == "earring":
            hair = render.persona_mask(pid, v, "hair", img.size)
            out = render.render_earrings(img, g, item, hair)
        else:
            out = render.render_necklace(img, g, item)
        return {"url": "result.jpg"}, {"result.jpg": render.jpeg(out)}

    def earring(self, image: bytes, payload: dict, refs: list[bytes]) -> tuple[dict, dict[str, bytes]]:
        return self._jewellery(image, refs[0], "earring")

    def necklace(self, image: bytes, payload: dict, refs: list[bytes]) -> tuple[dict, dict[str, bytes]]:
        return self._jewellery(image, refs[0], "necklace")


PRESET_HEX = {
    "Jet Black": "#16110F", "Chocolate Brown": "#4B2E22", "Honey Blonde": "#B8834A", "Platinum Blonde": "#D9D2C2",
    "Ash Gray": "#8C8C88", "Rose Gold": "#B76E5C", "Burgundy": "#5E1528", "Copper Red": "#9A3E1F",
    "Lavender": "#9C86C4", "Teal Blue": "#1F6F78", "Dark Brown": "#3A2418", "Caramel Blonde": "#A86F3A",
}


JEWEL_DIR = render.PERSONA_DIR.parent / "jewellery"


def _jewel_index() -> dict[str, str]:
    idx = {}
    for p in JEWEL_DIR.glob("*_ref.jpg"):
        idx[hashlib.sha256(p.read_bytes()).hexdigest()] = str(p).replace("_ref.jpg", ".png")
    return idx


def _ref_rgba(ref: bytes) -> Image.Image:
    """Reference product shots arrive on white; use our cut-out PNG, else key the white out."""
    import numpy as np
    known = _jewel_index().get(hashlib.sha256(ref).hexdigest())
    if known:
        im = Image.open(known).convert("RGBA")
        return im.crop(im.getbbox()) if im.getbbox() else im
    im = render.to_img(ref).convert("RGBA")
    arr = np.asarray(im).astype(np.float32)
    whiteness = arr[..., :3].min(-1)
    alpha = np.clip((250 - whiteness) / 30.0, 0, 1) * 255
    arr[..., 3] = alpha
    out = Image.fromarray(arr.astype("uint8"), "RGBA")
    bb = out.getbbox()
    return out.crop(bb) if bb else out
