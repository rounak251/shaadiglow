"""Concern metadata and normalisation of the AI Skin Analysis response.

YouCam scores are 1-100 where HIGHER = HEALTHIER.  `ui_score` is the calibrated
number YouCam recommends showing to shoppers; `raw_score` is the model's direct
estimate.  We display ui_score and rank priorities by raw_score (ties by ui).
"""
from __future__ import annotations

CONCERNS: dict[str, dict] = {
    "acne": {"label": {"en": "Breakouts", "hi": "मुंहासे"}, "icon": "dot",
             "what": {"en": "Active spots and clogged pores the AI can see.",
                      "hi": "दिखने वाले दाने और बंद रोमछिद्र।"},
             "sim": "acne"},
    "pore": {"label": {"en": "Visible pores", "hi": "खुले रोमछिद्र"}, "icon": "pores",
             "what": {"en": "How noticeable pores are on the nose and cheeks.",
                      "hi": "नाक और गालों पर रोमछिद्र कितने दिखते हैं।"},
             "sim": "pores"},
    "texture": {"label": {"en": "Smoothness", "hi": "त्वचा की बनावट"}, "icon": "texture",
                "what": {"en": "Bumps and roughness that make makeup sit unevenly.",
                         "hi": "उभार और खुरदुरापन, जिससे मेकअप ठीक से नहीं बैठता।"},
                "sim": "texture"},
    "oiliness": {"label": {"en": "Oil control", "hi": "तेल नियंत्रण"}, "icon": "drop",
                 "what": {"en": "Shine on the T-zone; decides how long makeup lasts.",
                          "hi": "टी-ज़ोन पर चमक; इसी से मेकअप कितनी देर टिकेगा।"},
                 "sim": "oiliness"},
    "moisture": {"label": {"en": "Hydration", "hi": "नमी"}, "icon": "water",
                 "what": {"en": "How plump and hydrated the skin surface looks.",
                          "hi": "त्वचा कितनी भरी-भरी और नम दिखती है।"},
                 "sim": None},
    "redness": {"label": {"en": "Calmness", "hi": "लालिमा"}, "icon": "flame",
                "what": {"en": "Redness and sensitivity, e.g. around the nose and cheeks.",
                         "hi": "नाक और गालों के आसपास लालिमा और संवेदनशीलता।"},
                "sim": "redness"},
    "age_spot": {"label": {"en": "Even tone", "hi": "एक-सा रंग"}, "icon": "spots",
                 "what": {"en": "Dark spots and post-acne marks.",
                          "hi": "काले धब्बे और मुंहासों के निशान।"},
                 "sim": "spots"},
    "dark_circle_v2": {"label": {"en": "Dark circles", "hi": "काले घेरे"}, "icon": "eye",
                       "what": {"en": "Darkness under the eyes; shows up in close-up photos.",
                                "hi": "आँखों के नीचे कालापन; क्लोज़-अप फ़ोटो में दिखता है।"},
                       "sim": "dark_circle"},
    "eye_bag": {"label": {"en": "Puffiness", "hi": "आँखों की सूजन"}, "icon": "eye",
                "what": {"en": "Puffiness under the eyes (sleep, salt and late nights).",
                         "hi": "आँखों के नीचे सूजन (नींद, नमक, देर रात)।"},
                "sim": "eye_bags"},
    "radiance": {"label": {"en": "Glow", "hi": "चमक"}, "icon": "sun",
                 "what": {"en": "Overall brightness; dull skin looks flat in flash photos.",
                          "hi": "कुल चमक; फ़्लैश फ़ोटो में बेजान त्वचा फीकी दिखती है।"},
                 "sim": "radiance"},
    "wrinkle": {"label": {"en": "Fine lines", "hi": "महीन रेखाएँ"}, "icon": "lines",
                "what": {"en": "Fine lines on the forehead and around the eyes.",
                         "hi": "माथे और आँखों के आसपास महीन रेखाएँ।"},
                "sim": "wrinkle"},
}

SKIN_TYPES = {"Normal": "सामान्य", "Oily": "तैलीय", "Dry": "रूखी", "Combination": "मिश्रित",
              "Redness": "लालिमा-प्रवण", "Dry & Redness": "रूखी व लालिमा", "Oily & Redness": "तैलीय व लालिमा",
              "Combination & Redness": "मिश्रित व लालिमा"}


def band(ui: float) -> str:
    if ui < 60:
        return "focus"
    if ui < 75:
        return "improve"
    if ui < 85:
        return "good"
    return "great"


def normalise(results: dict) -> dict:
    """Turn YouCam `results.output` into {concerns: [...], overall, skin_age, skin_type, resized}."""
    out = results.get("output", []) if isinstance(results, dict) else []
    concerns, skin_type, overall, skin_age, resized = [], {}, None, None, None
    for o in out:
        t = (o.get("type") or "")
        base = t[3:] if t.startswith("hd_") else t
        base = "dark_circle_v2" if base == "dark_circle" else base
        if base == "skin_type":
            skin_type[o.get("region", "whole")] = {"type": o.get("skin_type") or o.get("value") or "Normal",
                                                   "mask": (o.get("mask_urls") or [None])[0]}
        elif base == "all":
            overall = o.get("score")
        elif base == "skin_age":
            skin_age = o.get("score")
        elif base == "resize_image":
            resized = (o.get("mask_urls") or [None])[0]
        elif base in CONCERNS:
            if o.get("region") not in (None, "whole"):
                continue   # HD sub-regions: keep the whole-face score
            ui = float(o.get("ui_score", o.get("score", 0)) or 0)
            raw = float(o.get("raw_score", ui) or ui)
            concerns.append({"id": base, "ui": round(ui), "raw": round(raw, 1), "band": band(ui),
                             "mask": (o.get("mask_urls") or [None])[0], "label": CONCERNS[base]["label"],
                             "what": CONCERNS[base]["what"]})
    concerns.sort(key=lambda c: (c["raw"], c["ui"]))
    for i, c in enumerate(concerns):
        c["rank"] = i + 1
    if overall is None and concerns:
        overall = sum(c["ui"] for c in concerns) / len(concerns)
    return {"concerns": concerns, "overall": round(float(overall or 0)), "skin_age": skin_age,
            "skin_type": skin_type, "resized": resized}


def focus_concerns(concerns: list[dict], k: int = 3) -> list[dict]:
    """Up to k concerns that need work (ui < 75); if skin is already good, the k lowest."""
    weak = [c for c in concerns if c["ui"] < 75]
    return (weak or concerns)[:k]
