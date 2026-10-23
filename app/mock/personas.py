"""Sample personas: licensed photos (see ASSETS.md) + hand-written fixture scores for MOCK mode.

The scores are invented, plausible values used only until a YouCam key is
connected; live mode always shows the real AI Skin Analysis output.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

PERSONA_DIR = Path(__file__).resolve().parents[1] / "static" / "personas"

PERSONAS = {
    "ananya": {
        "name": "Ananya", "role": "bride", "age": 27, "city": "mumbai", "wedding_in_days": 58,
        "blurb": {"en": "Bride · Mumbai · wedding in 8 weeks", "hi": "दुल्हन · मुंबई · शादी 8 हफ़्ते में"},
        "credit": "Andre Styles / Unsplash", "skin_age": 26, "skin_type": ["Combination", "Oily", "Normal"],
        "scores": {"acne": 72, "pore": 64, "texture": 70, "oiliness": 57, "moisture": 66, "redness": 78,
                   "age_spot": 68, "dark_circle_v2": 60, "eye_bag": 74, "radiance": 62, "wrinkle": 86},
    },
    "arjun": {
        "name": "Arjun", "role": "groom", "age": 26, "city": "varanasi", "wedding_in_days": 45,
        "blurb": {"en": "Groom · Varanasi · wedding in 6 weeks", "hi": "दूल्हा · वाराणसी · शादी 6 हफ़्ते में"},
        "credit": "ARTO SURAJ / Unsplash", "skin_age": 25, "skin_type": ["Oily", "Oily", "Combination"],
        "scores": {"acne": 63, "pore": 59, "texture": 66, "oiliness": 54, "moisture": 71, "redness": 76,
                   "age_spot": 72, "dark_circle_v2": 58, "eye_bag": 69, "radiance": 61, "wrinkle": 89},
    },
    "arjun2": {   # same groom, a later photo: used as the "re-scan" in the progress demo
        "name": "Arjun", "role": "groom", "hidden": True, "credit": "ARTO SURAJ / Unsplash", "skin_age": 24,
        "skin_type": ["Combination", "Oily", "Normal"],
        "scores": {"acne": 69, "pore": 61, "texture": 69, "oiliness": 61, "moisture": 73, "redness": 77,
                   "age_spot": 73, "dark_circle_v2": 63, "eye_bag": 71, "radiance": 67, "wrinkle": 89},
    },
    "meera": {
        "name": "Meera", "role": "guest", "age": 24, "city": "jaipur", "wedding_in_days": 21,
        "blurb": {"en": "Bride's sister · Jaipur · sangeet in 3 weeks", "hi": "दुल्हन की बहन · जयपुर · संगीत 3 हफ़्ते में"},
        "credit": "Himanshu Dewangan / Unsplash", "skin_age": 24, "skin_type": ["Normal", "Combination", "Dry"],
        "scores": {"acne": 79, "pore": 66, "texture": 73, "oiliness": 68, "moisture": 58, "redness": 70,
                   "age_spot": 66, "dark_circle_v2": 61, "eye_bag": 73, "radiance": 64, "wrinkle": 87},
    },
}

VARIANTS = ("face", "beard", "portrait")


@lru_cache(maxsize=1)
def hash_index() -> dict[str, tuple[str, str]]:
    """sha256(variant bytes) -> (persona, variant): lets the mock engine recognise sample photos."""
    out = {}
    for pid in PERSONAS:
        for v in VARIANTS:
            p = PERSONA_DIR / pid / f"{v}.jpg"
            if p.exists():
                out[hashlib.sha256(p.read_bytes()).hexdigest()] = (pid, v)
    return out


def identify(data: bytes) -> tuple[str | None, str | None]:
    return hash_index().get(hashlib.sha256(data).hexdigest(), (None, None))


def variant_bytes(pid: str, variant: str) -> bytes:
    return (PERSONA_DIR / pid / f"{variant}.jpg").read_bytes()


def public_list() -> list[dict]:
    return [{"id": pid, "name": p["name"], "role": p["role"], "blurb": p["blurb"], "credit": p["credit"],
             "city": p["city"], "wedding_in_days": p["wedding_in_days"],
             "image": f"/static/personas/{pid}/face.jpg", "portrait": f"/static/personas/{pid}/portrait.jpg"}
            for pid, p in PERSONAS.items() if not p.get("hidden")]
