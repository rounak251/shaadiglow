"""Pillow/numpy renderers for MOCK mode only.

They let the app, the tests and the pre-key demo run end-to-end without spending
YouCam units.  Results are deliberately approximate and are always labelled
"demo fixture" in the UI; with a key, every image comes from the YouCam API.
"""
from __future__ import annotations

import io
import json
import math
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

PERSONA_DIR = Path(__file__).resolve().parents[1] / "static" / "personas"


# --------------------------------------------------------------------------- io helpers
def to_img(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def jpeg(img: Image.Image, q: int = 90) -> bytes:
    b = io.BytesIO()
    img.convert("RGB").save(b, "JPEG", quality=q, optimize=True)
    return b.getvalue()


def png(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, "PNG", optimize=True)
    return b.getvalue()


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# --------------------------------------------------------------------------- geometry
@lru_cache(maxsize=32)
def persona_geometry(pid: str) -> dict:
    return json.loads((PERSONA_DIR / pid / "geometry.json").read_text())


@lru_cache(maxsize=8)
def _template(variant: str) -> dict:
    return persona_geometry("ananya")[variant if variant in ("face", "portrait", "beard") else "face"]


def scale_geometry(g: dict, size: tuple[int, int]) -> dict:
    sx, sy = size[0] / g["size"][0], size[1] / g["size"][1]

    def sc(v):
        if isinstance(v, list) and v and isinstance(v[0], (int, float)):
            return [v[0] * sx, v[1] * sy]
        if isinstance(v, list):
            return [sc(x) for x in v]
        if isinstance(v, dict):
            return {k: sc(x) for k, x in v.items()}
        return v

    out = {k: sc(v) for k, v in g.items() if k not in ("size", "face_box")}
    fb = g["face_box"]
    out["face_box"] = [fb[0] * sx, fb[1] * sy, fb[2] * sx, fb[3] * sy]
    out["size"] = list(size)
    return out


def geometry_for(size: tuple[int, int], pid: str | None, variant: str) -> dict:
    """Persona landmarks if we know the photo, else a centred template face."""
    if pid:
        g = persona_geometry(pid).get(variant)
        if g:
            return scale_geometry(g, size)
    return scale_geometry(_template(variant), size)


def persona_mask(pid: str | None, variant: str, kind: str, size) -> np.ndarray | None:
    if not pid:
        return None
    p = PERSONA_DIR / pid / f"{variant}_{kind}.png"
    if not p.exists():
        return None
    return np.asarray(Image.open(p).convert("L").resize(size, Image.BILINEAR)).astype(np.float32) / 255.0


# --------------------------------------------------------------------------- mask helpers
def poly_mask(size, pts, blur: float = 2.0, ss: int = 2) -> np.ndarray:
    W, H = size
    m = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in pts], fill=255)
    m = m.resize((W, H), Image.LANCZOS)
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(m).astype(np.float32) / 255.0


def ellipse_mask(size, c, rx, ry, blur: float = 0.0, angle: float = 0.0) -> np.ndarray:
    """Soft (rotated) ellipse, evaluated only inside its bounding window for speed."""
    W, H = size
    out = np.zeros((H, W), np.float32)
    rmax = max(rx, ry) * 1.05 + 2
    x0, x1 = int(max(0, c[0] - rmax)), int(min(W, c[0] + rmax + 1))
    y0, y1 = int(max(0, c[1] - rmax)), int(min(H, c[1] + rmax + 1))
    if x1 <= x0 or y1 <= y0:
        return out
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    ca, sa = math.cos(angle), math.sin(angle)
    dx, dy = xx - c[0], yy - c[1]
    u = (dx * ca + dy * sa) / max(rx, 1)
    v = (-dx * sa + dy * ca) / max(ry, 1)
    d = np.sqrt(u * u + v * v)
    out[y0:y1, x0:x1] = (d <= 1).astype(np.float32) if blur <= 0 else np.clip((1.0 - d) / blur, 0, 1) ** 1.5
    return out


def stroke_mask(size, pts, width: float, blur: float = 1.0, ss: int = 3) -> np.ndarray:
    W, H = size
    m = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(m).line([(x * ss, y * ss) for x, y in pts], fill=255, width=max(1, int(width * ss)),
                           joint="curve")
    m = m.resize((W, H), Image.LANCZOS)
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(m).astype(np.float32) / 255.0


def blend(arr: np.ndarray, mask: np.ndarray, rgb, alpha: float, mode: str = "normal") -> np.ndarray:
    col = np.array(rgb, dtype=np.float32)[None, None, :]
    a = np.clip(mask * alpha, 0, 1)[..., None]
    if mode == "multiply":
        target = arr * col / 255.0
    elif mode == "screen":
        target = 255 - (255 - arr) * (255 - col) / 255.0
    elif mode == "softlight":
        b, s = arr / 255.0, col / 255.0
        target = 255 * np.where(s < 0.5, 2 * b * s + b * b * (1 - 2 * s),
                                2 * b * (1 - s) + np.sqrt(np.clip(b, 0, 1)) * (2 * s - 1))
    elif mode == "color":   # keep luminance, take hue/sat from colour
        lum = (arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32))[..., None]
        clum = float(col[0, 0] @ np.array([0.299, 0.587, 0.114], dtype=np.float32))
        target = np.clip(col * (lum / max(clum, 1.0)), 0, 255)
    else:
        target = np.broadcast_to(col, arr.shape)
    return arr * (1 - a) + target * a


def shimmer(size, density: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    W, H = size
    n = rng.random((H, W)).astype(np.float32)
    return (n > 1 - density * 0.06).astype(np.float32)


_REGION_CACHE: dict = {}


def face_region_masks(g: dict, size) -> dict[str, np.ndarray]:
    """Soft region masks (cheeks, T-zone, under-eyes...) built from landmarks (memoised)."""
    ck = (tuple(size), json.dumps(g["named"], sort_keys=True))
    if ck in _REGION_CACHE:
        return _REGION_CACHE[ck]
    if len(_REGION_CACHE) > 16:
        _REGION_CACHE.clear()
    _REGION_CACHE[ck] = m = _face_region_masks(g, size)
    return m


def _face_region_masks(g: dict, size) -> dict[str, np.ndarray]:
    n = g["named"]
    fb = g["face_box"]
    fw, fh = fb[2] - fb[0], fb[3] - fb[1]
    m = {}
    m["face"] = poly_mask(size, g["face_oval"], blur=fw * 0.02)
    for side in ("r", "l"):
        c = n[f"cheek_{side}"]
        m[f"cheek_{side}"] = ellipse_mask(size, c, fw * 0.14, fh * 0.10, blur=0.8)
        ue = n[f"under_eye_{side}"]
        eo, ei = n[f"eye_{side}_outer"], n[f"eye_{side}_inner"]
        cx = (eo[0] + ei[0]) / 2
        m[f"under_eye_{side}"] = ellipse_mask(size, (cx, ue[1] + fh * 0.045), abs(eo[0] - ei[0]) * 0.62,
                                              fh * 0.035, blur=0.9)
        cb = n[f"cheekbone_{side}"]
        m[f"cheekbone_{side}"] = ellipse_mask(size, (cb[0], cb[1] - fh * 0.01), fw * 0.10, fh * 0.035, blur=0.9,
                                              angle=-0.35 if side == "r" else 0.35)
    fh_top = n["forehead"]
    gl = n["glabella"]
    m["forehead"] = ellipse_mask(size, (fh_top[0], (fh_top[1] + gl[1]) / 2), fw * 0.30, fh * 0.09, blur=0.9)
    nb, nt = n["nose_bridge"], n["nose_tip"]
    m["nose"] = ellipse_mask(size, ((nb[0] + nt[0]) / 2, (nb[1] + nt[1]) / 2), fw * 0.07,
                             abs(nt[1] - nb[1]) * 0.65, blur=0.8)
    m["tzone"] = np.clip(m["forehead"] + m["nose"], 0, 1)
    m["uzone"] = np.clip(m["cheek_r"] + m["cheek_l"] + ellipse_mask(size, n["chin"], fw * 0.15, fh * 0.06, 0.9),
                         0, 1)
    m["skin"] = np.clip(m["face"] - poly_mask(size, g["eye_r"], 1) - poly_mask(size, g["eye_l"], 1)
                        - poly_mask(size, g["lips_outer"], 1), 0, 1)
    return m


# --------------------------------------------------------------------------- makeup
def render_makeup(img: Image.Image, g: dict, effects: list[dict], skin_mask: np.ndarray | None = None) -> Image.Image:
    size = img.size
    arr = np.asarray(img).astype(np.float32)
    regions = face_region_masks(g, size)
    skin = skin_mask if skin_mask is not None else regions["skin"]
    skin = np.clip(skin * regions["face"] * 1.15, 0, 1)
    fb = g["face_box"]
    fw, fh = fb[2] - fb[0], fb[3] - fb[1]
    by_cat = {e.get("category"): e for e in effects}
    smooth = by_cat.get("skin_smooth", {"skinSmoothStrength": 50})
    s = float(smooth.get("skinSmoothStrength", 50)) / 100.0
    if s > 0:
        blur = np.asarray(img.filter(ImageFilter.GaussianBlur(max(1.0, fw * 0.012)))).astype(np.float32)
        arr = arr * (1 - skin[..., None] * 0.55 * s) + blur * skin[..., None] * 0.55 * s

    def pal(e, i=0):
        ps = e.get("palettes") or [{}]
        p = ps[min(i, len(ps) - 1)]
        return hex_rgb(p.get("color", "#cc6677")), float(p.get("colorIntensity", 50)) / 100.0, p

    if "foundation" in by_cat:
        rgb, k, p = pal(by_cat["foundation"])
        cov = float(p.get("coverageIntensity", 50)) / 100.0
        arr = blend(arr, skin, rgb, 0.18 * k + 0.12 * cov, "softlight")
    if "concealer" in by_cat:
        rgb, k, p = pal(by_cat["concealer"])
        ue = np.clip(regions["under_eye_r"] + regions["under_eye_l"], 0, 1)
        arr = blend(arr, ue, rgb, 0.45 * float(p.get("colorUnderEyeIntensity", 50)) / 100.0 + 0.1, "screen")
    if "contour" in by_cat or "bronzer" in by_cat:
        e = by_cat.get("contour") or by_cat.get("bronzer")
        rgb, k, _ = pal(e)
        n = g["named"]
        m = np.zeros(size[::-1], np.float32)
        for side, sign in (("r", -1), ("l", 1)):
            cb = n[f"cheekbone_{side}"]
            m += ellipse_mask(size, (cb[0] + sign * fw * 0.02, cb[1] + fh * 0.09), fw * 0.12, fh * 0.03, 0.9,
                              angle=0.5 * sign)
        arr = blend(arr, np.clip(m, 0, 1), rgb, 0.35 * k, "multiply")
    if "blush" in by_cat:
        rgb, k, p = pal(by_cat["blush"])
        m = np.clip(regions["cheek_r"] + regions["cheek_l"], 0, 1)
        arr = blend(arr, m, rgb, 0.55 * k, "softlight")
        arr = blend(arr, m, rgb, 0.12 * k, "multiply")
    if "highlighter" in by_cat:
        rgb, k, p = pal(by_cat["highlighter"])
        m = np.clip(regions["cheekbone_r"] + regions["cheekbone_l"] + regions["nose"] * 0.5, 0, 1)
        arr = blend(arr, m, rgb, 0.5 * k + 0.1, "screen")
        sh = shimmer(size, float(p.get("shimmerDensity", 50)) / 100.0, 7) * m
        arr = blend(arr, sh, (255, 248, 230), 0.6, "screen")
    if "eye_shadow" in by_cat:
        e = by_cat["eye_shadow"]
        for side in ("r", "l"):
            eye = np.array(g[f"eye_{side}"])
            brow = np.array(g[f"brow_{side}"])
            top = eye[eye[:, 1] < eye[:, 1].mean() + 1]
            top = top[np.argsort(top[:, 0])]
            lid_top = [(x, y - (y - brow[:, 1].mean()) * 0.62) for x, y in top[::-1]]
            lid = poly_mask(size, [tuple(p) for p in top] + lid_top, blur=fw * 0.012)
            lid = np.clip(lid - poly_mask(size, g[f"eye_{side}"], 0.5), 0, 1)
            for i, p in enumerate((e.get("palettes") or [{}])[:3]):
                rgb = hex_rgb(p.get("color", "#8a5a44"))
                k = float(p.get("colorIntensity", 50)) / 100.0
                arr = blend(arr, lid, rgb, (0.5 - 0.12 * i) * k, "multiply" if i == 0 else "softlight")
                if p.get("texture") in ("shimmer", "metallic"):
                    sh = shimmer(size, float(p.get("shimmerIntensity", 50)) / 100.0, 11 + i) * lid
                    arr = blend(arr, sh, hex_rgb(p.get("shimmerColor", "#f6d38a")), 0.8, "screen")
    if "eye_liner" in by_cat or "eyelashes" in by_cat:
        e = by_cat.get("eye_liner") or by_cat.get("eyelashes")
        rgb, k, _ = pal(e)
        for side in ("r", "l"):
            eye = np.array(g[f"eye_{side}"])
            top = eye[eye[:, 1] <= np.median(eye[:, 1]) + 0.5]
            top = top[np.argsort(top[:, 0])]
            pts = [tuple(p) for p in top]
            outer = g["named"][f"eye_{side}_outer"]
            wing_dir = -1 if outer[0] < np.mean(eye[:, 0]) else 1
            wing = (outer[0] + wing_dir * fw * 0.05, outer[1] - fh * 0.025)
            pts = pts + [wing] if wing_dir > 0 else [wing] + pts
            m = stroke_mask(size, pts, max(2.0, fw * 0.011), blur=0.7)
            arr = blend(arr, m, rgb, 0.95 * max(k, 0.6))
            bottom = eye[eye[:, 1] > np.median(eye[:, 1])]
            bottom = bottom[np.argsort(bottom[:, 0])]
            arr = blend(arr, stroke_mask(size, [tuple(p) for p in bottom], max(1.5, fw * 0.006), 0.8), rgb,
                        0.55 * max(k, 0.5))
    if "eyebrows" in by_cat:
        rgb, k, _ = pal(by_cat["eyebrows"])
        for side in ("r", "l"):
            m = poly_mask(size, g[f"brow_{side}"], blur=fw * 0.006)
            arr = blend(arr, m, rgb, 0.35 * max(k, 0.5), "multiply")
    if "lip_color" in by_cat:
        e = by_cat["lip_color"]
        rgb, k, p = pal(e)
        lips = np.clip(poly_mask(size, g["lips_outer"], blur=1.2) - poly_mask(size, g["lips_inner"], blur=0.8), 0, 1)
        tex = p.get("texture", "matte")
        lum = (arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32))
        arr = blend(arr, lips, rgb, 0.78 * max(k, 0.45), "color")
        arr = blend(arr, lips, rgb, 0.35 * max(k, 0.45), "multiply")
        if tex in ("gloss", "sheer", "shimmer", "holographic", "metallic", "satin"):
            spec = np.clip((lum - np.percentile(lum[lips > 0.5], 70)) / 40.0, 0, 1) if (lips > 0.5).any() else lum * 0
            arr = blend(arr, spec * lips, (255, 255, 255), 0.45 if tex != "satin" else 0.2, "screen")
    if "lip_liner" in by_cat:
        rgb, k, _ = pal(by_cat["lip_liner"])
        pts = g["lips_outer"] + [g["lips_outer"][0]]
        arr = blend(arr, stroke_mask(size, pts, max(1.5, fw * 0.005), 0.8), rgb, 0.4 * max(k, 0.5), "multiply")
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# --------------------------------------------------------------------------- hair colour
def heuristic_hair_mask(img: Image.Image, g: dict) -> np.ndarray:
    arr = np.asarray(img).astype(np.float32)
    lum = arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    face = poly_mask(img.size, g["face_oval"], blur=3)
    H = img.size[1]
    yy = np.mgrid[0:H, 0:img.size[0]][0] / H
    m = ((lum < 75) & (yy < 0.85)).astype(np.float32) * (1 - face)
    return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))) / 255.0


def render_hair_color(img: Image.Image, hair: np.ndarray, colors: list[str], intensity: float = 0.75,
                      ombre: bool = False) -> Image.Image:
    arr = np.asarray(img).astype(np.float32)
    lum = arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    H = arr.shape[0]
    if ombre and len(colors) > 1:
        c1, c2 = np.array(hex_rgb(colors[0]), np.float32), np.array(hex_rgb(colors[1]), np.float32)
        ys = np.where(hair.sum(1) > 2)[0]
        y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, H)
        t = np.clip((np.arange(H) - y0) / max(1, (y1 - y0)), 0, 1) ** 1.4
        col = (c1[None, :] * (1 - t[:, None]) + c2[None, :] * t[:, None])[:, None, :]
    else:
        col = np.array(hex_rgb(colors[0]), np.float32)[None, None, :]
    clum = col @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    # lift dark hair so the new colour reads, keep strand detail from the original luminance
    detail = (lum / max(1.0, float(np.median(lum[hair > 0.5])) if (hair > 0.5).any() else 60.0))[..., None]
    target = np.clip(col * np.clip(detail, 0.25, 2.2) * 0.9 + (lum[..., None] - clum[..., None]) * 0.08, 0, 255)
    a = np.clip(hair * intensity, 0, 1)[..., None]
    out = arr * (1 - a) + target * a
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


# --------------------------------------------------------------------------- jewellery
def _paste_rgba(base: Image.Image, item: Image.Image, center_top: tuple[float, float], height: float,
                hair: np.ndarray | None = None, shadow: float = 0.35) -> Image.Image:
    it = item.copy()
    scale = height / it.height
    it = it.resize((max(1, int(it.width * scale)), max(1, int(height))), Image.LANCZOS)
    x = int(center_top[0] - it.width / 2)
    y = int(center_top[1])
    out = base.convert("RGBA")
    if shadow > 0:
        sh = Image.new("RGBA", it.size, (40, 25, 20, 0))
        sh.putalpha(it.getchannel("A").point(lambda v: int(v * shadow)).filter(ImageFilter.GaussianBlur(3)))
        out.alpha_composite(sh, (x + 3, y + 4))
    if hair is not None:
        # hair falling over the ear partly hides the earring
        crop = hair[max(0, y):y + it.height, max(0, x):x + it.width]
        if crop.shape[0] == it.height and crop.shape[1] == it.width:
            a = np.asarray(it.getchannel("A")).astype(np.float32) * (1 - 0.55 * crop)
            it.putalpha(Image.fromarray(a.astype(np.uint8)))
    out.alpha_composite(it, (x, y))
    return out.convert("RGB")


def split_pair(item: Image.Image) -> list[Image.Image]:
    """Product shots show a pair side by side; return one earring per ear."""
    a = np.asarray(item.getchannel("A"))
    cols = np.where(a.max(0) > 20)[0]
    if len(cols) == 0:
        return [item]
    gaps = np.where(np.diff(cols) > 8)[0]
    if len(gaps) == 0:
        return [item.crop(item.getbbox())]
    split = (cols[gaps[0]] + cols[gaps[0] + 1]) // 2
    left = item.crop((0, 0, split, item.height))
    right = item.crop((split, 0, item.width, item.height))
    return [left.crop(left.getbbox()), right.crop(right.getbbox())]


def render_earrings(img: Image.Image, g: dict, item: Image.Image, hair: np.ndarray | None = None) -> Image.Image:
    n = g["named"]
    fb = g["face_box"]
    fh = fb[3] - fb[1]
    fw = fb[2] - fb[0]
    pieces = split_pair(item)
    out = img
    for i, side in enumerate(("r", "l")):
        piece = pieces[min(i, len(pieces) - 1)]
        edge = n[f"face_{side}"]
        low = n[f"ear_{side}_low"]
        sign = -1 if side == "r" else 1
        lobe = (edge[0] * 0.55 + low[0] * 0.45 + sign * fw * 0.035, edge[1] * 0.35 + low[1] * 0.65)
        out = _paste_rgba(out, piece, lobe, fh * 0.30, hair)
    return out


def render_necklace(img: Image.Image, g: dict, item: Image.Image) -> Image.Image:
    n = g["named"]
    fb = g["face_box"]
    fw, fh = fb[2] - fb[0], fb[3] - fb[1]
    chin = n["chin"]
    it = item.crop(item.getbbox()) if item.getbbox() else item
    width = fw * 1.05
    height = it.height * width / it.width
    top = (chin[0], chin[1] + fh * 0.30)
    return _paste_rgba(img, it, top, height, None, shadow=0.3)


# --------------------------------------------------------------------------- beard
BEARD_STYLES = {
    # alpha: max darkness, reach: how far up the cheeks (0 = chin only), moustache, density of strands
    "stubble": dict(alpha=0.42, reach=0.85, moustache=0.55, density=0.55, length=3),
    "short_boxed": dict(alpha=0.72, reach=0.80, moustache=0.85, density=0.80, length=6),
    "full": dict(alpha=0.80, reach=1.00, moustache=0.95, density=0.90, length=10),
    "goatee": dict(alpha=0.78, reach=0.0, moustache=0.9, density=0.85, length=7),
    "clean": dict(alpha=0.0, reach=0.0, moustache=0.0, density=0.0, length=0),
}


def _strands(shape, density: float, length: int, seed: int = 5) -> np.ndarray:
    """Short vertical hair strokes: sparse noise smeared downwards."""
    rng = np.random.default_rng(seed)
    seeds = (rng.random(shape) < 0.10 + 0.25 * density).astype(np.float32)
    acc = np.zeros(shape, np.float32)
    for k in range(max(1, length)):
        acc[k:, :] += seeds[:shape[0] - k, :] * (1 - k / (length + 1))
    acc = np.clip(acc, 0, 1)
    return np.asarray(Image.fromarray((acc * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(0.5))).astype(np.float32) / 255.0


def render_beard(img: Image.Image, g: dict, style: str, skin: np.ndarray | None = None) -> Image.Image:
    cfg = BEARD_STYLES.get(style, BEARD_STYLES["short_boxed"])
    size = img.size
    W, H = size
    arr = np.asarray(img).astype(np.float32)
    n = g["named"]
    fb = g["face_box"]
    fw, fh = fb[2] - fb[0], fb[3] - fb[1]
    face = poly_mask(size, g["face_oval"], blur=fw * 0.03)
    mouth = poly_mask(size, g["lips_outer"], blur=1.5)
    mouth_d = np.asarray(Image.fromarray((mouth * 255).astype(np.uint8)).filter(
        ImageFilter.MaxFilter(5))).astype(np.float32) / 255.0
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx = (n["face_r"][0] + n["face_l"][0]) / 2
    half = max(1.0, (n["face_l"][0] - n["face_r"][0]) / 2)
    t = np.clip(np.abs(xx - cx) / half, 0, 1)                     # 0 centre -> 1 face edge
    lip_y = n["mouth_r"][1] * 0.5 + n["mouth_l"][1] * 0.5
    edge_y = n["face_r"][1] * 0.5 + n["face_l"][1] * 0.5 + fh * 0.05     # sideburn height
    top = lip_y + fh * 0.03 + (edge_y - lip_y - fh * 0.03) * (t ** 1.6) * cfg["reach"]
    beard = np.clip((yy - top) / (fh * 0.05), 0, 1) * face
    if cfg["reach"] == 0:  # goatee: chin only, soft sides
        beard = np.clip((yy - (lip_y + fh * 0.05)) / (fh * 0.04), 0, 1) * np.clip((0.40 - t) / 0.14, 0, 1) * face
    if style == "clean":
        blur = np.asarray(img.filter(ImageFilter.GaussianBlur(fw * 0.02))).astype(np.float32)
        lower = np.clip((yy - (lip_y - fh * 0.12)) / (fh * 0.05), 0, 1) * face
        lift = np.clip(lower - mouth_d, 0, 1)[..., None]
        out = arr * (1 - lift * 0.7) + (blur * 1.06 + 8) * lift * 0.7
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    nose_y = n["nose_tip"][1]
    moustache = ellipse_mask(size, (cx, (nose_y + lip_y) / 2 + fh * 0.012), fw * 0.20, fh * 0.032, 0.6)
    region = np.clip(beard + moustache * cfg["moustache"], 0, 1)
    region = np.clip(region - mouth_d * 1.3, 0, 1)
    strands = _strands((H, W), cfg["density"], cfg["length"])
    dens = region * (0.45 + 0.55 * strands)
    arr = blend(arr, dens, (34, 24, 18), cfg["alpha"] * 0.9, "multiply")
    arr = blend(arr, region * strands, (14, 10, 8), cfg["alpha"] * 0.55)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# --------------------------------------------------------------------------- skin simulation
def render_skin_simulation(img: Image.Image, g: dict, params: dict, skin_mask: np.ndarray | None = None) -> Image.Image:
    size = img.size
    arr = np.asarray(img).astype(np.float32)
    r = face_region_masks(g, size)
    skin = np.clip((skin_mask if skin_mask is not None else r["skin"]) * r["face"] * 1.1, 0, 1)
    fw = g["face_box"][2] - g["face_box"][0]
    v = lambda k: float(params.get(k, 0) or 0)
    smooth = max(v("texture"), v("pores"), v("acne") * 0.9, v("spots") * 0.8, v("wrinkle") * 0.8)
    if smooth > 0:
        blur = np.asarray(img.filter(ImageFilter.GaussianBlur(max(1.0, fw * 0.016)))).astype(np.float32)
        a = (skin * 0.75 * smooth)[..., None]
        arr = arr * (1 - a) + blur * a
    if v("redness") > 0:
        lum = (arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32))[..., None]
        red = np.clip((arr[..., 0:1] - arr[..., 1:2]) / 60.0, 0, 1)
        k = (skin[..., None] * red * 0.45 * v("redness"))
        arr = arr * (1 - k) + (arr * 0.4 + lum * 0.6) * k
    ue = np.clip(r["under_eye_r"] + r["under_eye_l"], 0, 1)
    if v("dark_circle") > 0 or v("eye_bags") > 0:
        arr = blend(arr, ue, (236, 198, 170), 0.35 * max(v("dark_circle"), v("eye_bags")), "screen")
    if v("oiliness") > 0:
        lum = arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        hi = np.clip((lum - 190) / 50.0, 0, 1) * skin
        arr = arr * (1 - (hi * 0.5 * v("oiliness"))[..., None]) + arr.mean(-1, keepdims=True) * 0.92 * (
            hi * 0.5 * v("oiliness"))[..., None]
    if v("radiance") > 0:
        arr = blend(arr, skin, (255, 236, 214), 0.16 * v("radiance"), "softlight")
        arr = arr * (1 + skin[..., None] * 0.05 * v("radiance"))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# --------------------------------------------------------------------------- skin analysis masks
MASK_STYLE = {   # colours echo YouCam's own mask palette in the docs
    "acne": (235, 64, 52), "pore": (255, 196, 0), "texture": (56, 140, 255), "wrinkle": (40, 220, 90),
    "dark_circle_v2": (160, 80, 220), "eye_bag": (245, 105, 180), "redness": (255, 70, 70),
    "oiliness": (255, 214, 0), "moisture": (0, 170, 255), "age_spot": (150, 85, 40),
    "radiance": (255, 255, 255), "skin_type": (255, 120, 0),
}


def render_concern_mask(size, g: dict, concern: str, score: float, seed: int) -> Image.Image:
    """RGBA mask like YouCam's raw masks (enable_mask_overlay=false): draw on transparent."""
    W, H = size
    rng = random.Random(seed)
    sev = max(0.05, min(1.0, (100 - score) / 55.0))
    r = face_region_masks(g, size)
    fb = g["face_box"]
    fw, fh = fb[2] - fb[0], fb[3] - fb[1]
    rgb = MASK_STYLE.get(concern, (255, 255, 255))
    alpha = np.zeros((H, W), np.float32)
    canvas = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(canvas)

    def dots(region, count, rad):
        ys, xs = np.where(region > 0.45)
        if len(xs) == 0:
            return
        for _ in range(count):
            i = rng.randrange(len(xs))
            rr = rad * (0.6 + rng.random() * 0.8)
            d.ellipse([xs[i] - rr, ys[i] - rr, xs[i] + rr, ys[i] + rr], fill=255)

    if concern == "acne":
        dots(np.clip(r["cheek_r"] + r["cheek_l"] + r["forehead"] * 0.8 + r["uzone"] * 0.5, 0, 1),
             int(4 + 14 * sev), fw * 0.012)
    elif concern == "pore":
        dots(np.clip(r["nose"] + r["cheek_r"] * 0.9 + r["cheek_l"] * 0.9, 0, 1), int(60 + 260 * sev), fw * 0.0035)
    elif concern == "age_spot":
        dots(np.clip(r["cheek_r"] + r["cheek_l"] + r["forehead"] * 0.6, 0, 1), int(5 + 16 * sev), fw * 0.009)
    elif concern == "wrinkle":
        n = g["named"]
        for k in range(int(2 + 5 * sev)):
            y = n["forehead"][1] + fh * (0.06 + 0.03 * k)
            x0 = n["forehead"][0] - fw * (0.18 + rng.random() * 0.06)
            x1 = n["forehead"][0] + fw * (0.18 + rng.random() * 0.06)
            d.line([(x0, y), ((x0 + x1) / 2, y - fh * 0.01), (x1, y)], fill=255, width=max(1, int(fw * 0.004)))
        for side, sign in (("r", -1), ("l", 1)):
            eo = n[f"eye_{side}_outer"]
            for k in range(int(1 + 3 * sev)):
                d.line([(eo[0] + sign * fw * 0.02, eo[1] + fh * (k - 1) * 0.015),
                        (eo[0] + sign * fw * 0.07, eo[1] + fh * (k - 1) * 0.03)], fill=255,
                       width=max(1, int(fw * 0.004)))
    if concern in ("acne", "pore", "age_spot", "wrinkle"):
        alpha = np.asarray(canvas.filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255.0 * 0.95
    elif concern == "dark_circle_v2":
        alpha = np.clip(r["under_eye_r"] + r["under_eye_l"], 0, 1) * (0.35 + 0.5 * sev)
    elif concern == "eye_bag":
        ue = np.clip(r["under_eye_r"] + r["under_eye_l"], 0, 1)
        shifted = np.roll(ue, int(fh * 0.025), axis=0)
        alpha = np.clip(shifted, 0, 1) * (0.3 + 0.5 * sev)
    elif concern == "redness":
        alpha = np.clip(r["cheek_r"] + r["cheek_l"] + r["nose"] * 0.7, 0, 1) * (0.25 + 0.55 * sev)
    elif concern == "oiliness":
        alpha = r["tzone"] * (0.3 + 0.55 * sev)
    elif concern == "moisture":
        alpha = np.clip(r["cheek_r"] + r["cheek_l"], 0, 1) * (0.25 + 0.5 * sev)
    elif concern == "texture":
        noise = np.asarray(Image.effect_noise((W, H), 60).filter(ImageFilter.GaussianBlur(fw * 0.01))).astype(
            np.float32) / 255.0
        alpha = np.clip((noise - 0.5) * 3, 0, 1) * np.clip(r["uzone"] + r["forehead"] * 0.6, 0, 1) * (0.4 + 0.5 * sev)
    elif concern == "radiance":
        alpha = r["skin"] * (0.15 + 0.35 * (1 - sev))
    elif concern == "skin_type":
        tz, uz = r["tzone"], r["uzone"]
        out = np.zeros((H, W, 4), np.float32)
        out[..., 0] = 255 * tz + 70 * uz
        out[..., 1] = 160 * tz + 200 * uz
        out[..., 2] = 0 * tz + 255 * uz
        out[..., 3] = np.clip(tz + uz, 0, 1) * 150
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
    out = np.zeros((H, W, 4), np.float32)
    out[..., :3] = rgb
    out[..., 3] = np.clip(alpha, 0, 1) * 235
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def overlay_masks(img: Image.Image, masks: list[Image.Image]) -> Image.Image:
    out = img.convert("RGBA")
    for m in masks:
        out.alpha_composite(m.resize(out.size))
    return out.convert("RGB")


def diff_score(a: Image.Image, b: Image.Image) -> float:
    """Mean absolute pixel change (used by tests to prove a render changed the photo)."""
    return float(np.asarray(ImageChops.difference(a.convert("RGB"), b.convert("RGB"))).mean())
