"""Request builders shared by the API routes and `scripts/live_smoke.py --prewarm`.

Keeping them in one place guarantees that a pre-warmed cache entry has exactly
the cache key the app will look up later (same image bytes + same parameters).
"""
from __future__ import annotations

from .engine import catalog, looks

SIM_KEY = {"acne": "acne", "pore": "pores", "texture": "texture", "oiliness": "oiliness", "redness": "redness",
           "age_spot": "spots", "dark_circle_v2": "dark_circle", "eye_bag": "eye_bags", "radiance": "radiance",
           "wrinkle": "wrinkle"}
SIM_STRENGTH = 0.6
EARRING_PARAMS = {"earring_need_remove_background": True, "earring_occluded_type": 0,
                  "earring_shadow_intensity": 0.35, "earring_ambient_light_intensity": 0.8}
NECKLACE_PARAMS = {"necklace_need_remove_background": True, "necklace_shadow_intensity": 0.3,
                   "necklace_ambient_light_intensity": 0.8}


def scan_params(concerns: list[str], camera_kit: bool = False) -> dict:
    p = {"dst_actions": list(concerns), "miniserver_args": {"enable_mask_overlay": False}, "format": "json"}
    if camera_kit:
        p["pf_camera_kit"] = True
    return p


def sim_focus(scan: dict) -> list[str]:
    """Default goal: the 4 weakest concerns that Skin Simulation can render (it has no 'hydration' knob)."""
    return [c["id"] for c in scan.get("concerns", []) if c["id"] in SIM_KEY][:4]


def sim_params(focus: list[str], strength: float = SIM_STRENGTH) -> dict:
    keys = [SIM_KEY[c] for c in focus if c in SIM_KEY][:4] or ["radiance", "texture"]
    return {k: round(strength, 2) for k in keys}


def makeup_params(look_id: str, shade_id: str | None) -> tuple[dict, list[str]]:
    effects, used = looks.effects_for(look_id, shade_id)
    return {"effects": effects, "version": "1.0"}, used


def hair_params(product_id: str) -> dict:
    return dict(catalog.get(product_id)["vto"])


def jewellery_spec(product_id: str) -> tuple[str, str, dict]:
    """-> (feature, reference image file name, per-object parameters)."""
    p = catalog.get(product_id)
    kind = p["vto"]["kind"]
    return kind, p["vto"]["ref"], dict(EARRING_PARAMS if kind == "earring" else NECKLACE_PARAMS)


def beard_params(template_id: str) -> dict:
    return {"template_id": template_id}
