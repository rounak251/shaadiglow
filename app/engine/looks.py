"""Wedding-event looks, each a list of catalogue products -> one AI Makeup VTO request.

A look costs 1 unit no matter how many effects it stacks (lip + liner + shadow +
blush + highlighter + base), so we render a complete look per call.  Foundation
and concealer follow the shopper's shade; lip colours shift deeper for deeper
skin so "classic red" stays classic on every tone.
"""
from __future__ import annotations

import copy

from . import catalog

LOOKS = [
    {"id": "haldi_fresh", "event": "haldi", "roles": ["bride", "guest"],
     "name": {"en": "Haldi Fresh Glow", "hi": "हल्दी फ़्रेश ग्लो"},
     "desc": {"en": "Dewy, waterproof and sunny: coral lips, soft brown kohl, peach cheeks.",
              "hi": "ओस-सी, वॉटरप्रूफ़ और खिली-खिली: कोरल होंठ, हल्का भूरा काजल, पीच गाल।"},
     "products": ["lip_coral", "kohl_brown", "mascara", "blush_peach", "hl_golden"], "base": 30, "smooth": 45},
    {"id": "mehendi_boho", "event": "mehendi", "roles": ["bride", "guest"],
     "name": {"en": "Mehendi Bronze", "hi": "मेहंदी ब्रॉन्ज़"},
     "desc": {"en": "Warm bronze-olive eyes and a terracotta matte lip to match green outfits.",
              "hi": "गर्म ब्रॉन्ज़-ऑलिव आँखें और टेराकोटा मैट होंठ, हरे परिधान के साथ।"},
     "products": ["lip_terracotta", "pal_bronze", "kajal_black", "mascara", "blush_berry", "contour_soft"],
     "base": 40, "smooth": 45},
    {"id": "sangeet_glam", "event": "sangeet", "roles": ["bride", "guest"],
     "name": {"en": "Sangeet Night Glam", "hi": "संगीत नाइट ग्लैम"},
     "desc": {"en": "Smoky plum eyes, a nude-rose gloss and strong highlight for stage lights.",
              "hi": "स्मोकी प्लम आँखें, न्यूड-रोज़ ग्लॉस और स्टेज लाइट के लिए तेज़ हाइलाइट।"},
     "products": ["lip_nude", "pal_plum", "kajal_black", "mascara", "blush_rose", "hl_champagne", "contour_soft"],
     "base": 50, "smooth": 50},
    {"id": "pheras_red", "event": "wedding", "roles": ["bride"],
     "name": {"en": "Pheras Classic Red", "hi": "फेरों का क्लासिक लाल"},
     "desc": {"en": "Sindoor-red matte lips, bold kohl, gold-dust lids and a warm flush.",
              "hi": "सिंदूरी लाल मैट होंठ, गहरा काजल, सुनहरी पलकें और गर्म ब्लश।"},
     "products": ["lip_sindoor", "pal_gold", "kajal_black", "mascara", "blush_rose", "hl_golden", "contour_soft",
                  "concealer_peach"], "base": 55, "smooth": 50},
    {"id": "reception_rose", "event": "reception", "roles": ["bride", "guest"],
     "name": {"en": "Reception Rose Gold", "hi": "रिसेप्शन रोज़ गोल्ड"},
     "desc": {"en": "Rose-gold shimmer eyes, a mauve satin lip and soft definition for photos.",
              "hi": "रोज़-गोल्ड शिमर आँखें, मॉव साटन होंठ और फ़ोटो के लिए हल्की शेपिंग।"},
     "products": ["lip_mauve", "pal_rose", "kohl_brown", "mascara", "blush_rose", "hl_champagne", "contour_soft"],
     "base": 50, "smooth": 50},
    {"id": "guest_wine", "event": "wedding", "roles": ["guest"],
     "name": {"en": "Wedding Guest Wine", "hi": "वेडिंग गेस्ट वाइन"},
     "desc": {"en": "A deep wine lip with clean kohl: elegant without upstaging the bride.",
              "hi": "गहरे वाइन होंठ और साफ़ काजल: सुंदर, पर दुल्हन से ज़्यादा नहीं।"},
     "products": ["lip_wine", "kajal_black", "mascara", "blush_berry", "hl_champagne"], "base": 40, "smooth": 45},
    {"id": "groom_natural", "event": "wedding", "roles": ["groom"],
     "name": {"en": "Groom Natural Finish", "hi": "दूल्हे का नैचुरल फ़िनिश"},
     "desc": {"en": "Camera-ready, not 'made up': evens tone, softens dark circles, tames shine.",
              "hi": "कैमरा के लिए तैयार, पर मेकअप जैसा नहीं: रंग एक-सा, काले घेरे हल्के, चमक कम।"},
     "products": ["concealer_peach", "lip_balm_tint"], "base": 25, "smooth": 35},
    {"id": "groom_reception", "event": "reception", "roles": ["groom"],
     "name": {"en": "Groom Reception Sharp", "hi": "दूल्हे का रिसेप्शन लुक"},
     "desc": {"en": "A touch more definition for evening flash photography.",
              "hi": "शाम की फ़्लैश फ़ोटोग्राफ़ी के लिए थोड़ी ज़्यादा परिभाषा।"},
     "products": ["concealer_peach", "contour_soft", "lip_balm_tint"], "base": 30, "smooth": 40},
]

BY_ID = {lk["id"]: lk for lk in LOOKS}
DEEP_SHADES = {"Caramel 330", "Almond 410", "Espresso 510"}
DEEPER_LIPS = {"lip_sindoor": "#8E1022", "lip_coral": "#C24A36", "lip_nude": "#9C5A55", "lip_mauve": "#7E4257"}


def looks_for(role: str) -> list[dict]:
    return [lk for lk in LOOKS if role in lk["roles"]]


def effects_for(look_id: str, shade_id: str | None) -> tuple[list[dict], list[str]]:
    """Build the documented `effects` array (version 1.0) and the product ids it uses."""
    look = BY_ID[look_id]
    found = catalog.get(shade_id) if shade_id and shade_id in catalog.PRODUCTS else catalog.FOUNDATIONS[4]
    deep = any(found["name"].endswith(s) for s in DEEP_SHADES)
    effects = [{"category": "skin_smooth", "skinSmoothStrength": look["smooth"], "skinSmoothColorIntensity": 40}]
    f = copy.deepcopy(found["vto"])
    f["palettes"][0]["coverageIntensity"] = look["base"]
    effects.append(f)
    used = [found["id"]]
    for pid in look["products"]:
        p = catalog.get(pid)
        e = copy.deepcopy(p["vto"])
        if deep and pid in DEEPER_LIPS:
            e["palettes"][0]["color"] = DEEPER_LIPS[pid]
        if e["category"] == "concealer":
            # concealer follows the base shade, the peach corrector only tints under the eyes
            e["palettes"][0]["color"] = "#E9A07D" if not deep else "#C9774F"
        effects.append(e)
        used.append(pid)
    return effects, used


def public() -> list[dict]:
    return [{k: v for k, v in lk.items()} for lk in LOOKS]
