"""Registry of the YouCam endpoints ShaadiGlow uses, with documented unit costs.

Every path and price below comes from the official docs (docs.perfectcorp.com /
docs.makeupar.com, API v1.16, read 23 Oct 2026).  `scripts/live_smoke.py`
re-checks the prices against GET /s2s/v2.0/credit/feature-cost once a key exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# SD skin-analysis concerns (SD and HD must never be mixed in one call).
SD_CONCERNS = [
    "wrinkle", "pore", "texture", "acne", "oiliness", "radiance", "eye_bag", "age_spot",
    "dark_circle_v2", "droopy_upper_eyelid", "droopy_lower_eyelid", "firmness", "moisture",
    "redness", "tear_trough", "skin_type",
]
HD_CONCERNS = ["hd_" + c.replace("dark_circle_v2", "dark_circle") for c in SD_CONCERNS]

# The 12 concerns a 30-90 day skincare plan can actually act on.  We skip eyelid
# droop, firmness and tear trough on purpose: no cream fixes them before a wedding,
# and dropping them moves the scan from the 16-unit tier to the 14-unit tier.
FULL_SCAN = ["acne", "pore", "texture", "oiliness", "moisture", "redness", "age_spot",
             "dark_circle_v2", "eye_bag", "radiance", "wrinkle", "skin_type"]


def skin_analysis_units(n_concerns: int, hd: bool = False) -> int:
    """Documented tiers: 1-4, 5-8, 9-12, 13-16 concerns."""
    if n_concerns <= 0:
        raise ValueError("at least one concern is required")
    tiers = [(4, 9, 12), (8, 12, 16), (12, 14, 20), (16, 16, 22)]
    for upper, sd, hd_cost in tiers:
        if n_concerns <= upper:
            return hd_cost if hd else sd
    raise ValueError("at most 16 concerns per call")


def skin_simulation_units(n_concerns: int) -> int:
    return 4 if n_concerns <= 4 else 6


@dataclass(frozen=True)
class Feature:
    key: str
    title: str                 # official API name, used in UI + video
    run_path: str
    poll_path: str
    units: Callable[[dict], int]
    template_path: str | None = None
    doc_url: str = ""


def _n_sim(payload: dict) -> int:
    keys = ["wrinkle", "radiance", "oiliness", "acne", "eye_bags", "dark_circle", "spots", "pores",
            "texture", "redness"]
    return sum(1 for k in keys if float(payload.get(k, 0) or 0) > 0)


FEATURES: dict[str, Feature] = {f.key: f for f in [
    Feature("skin_analysis", "AI Skin Analysis",
            "/s2s/v2.1/task/skin-analysis", "/s2s/v2.1/task/skin-analysis/{task_id}",
            lambda p: skin_analysis_units(len(p.get("dst_actions", [])),
                                          hd=any(a.startswith("hd_") for a in p.get("dst_actions", []))),
            doc_url="https://docs.perfectcorp.com/reference/ai_skin_analysis"),
    Feature("skin_simulation", "AI Skin Simulation",
            "/s2s/v2.0/task/skin-simulation", "/s2s/v2.0/task/skin-simulation/{task_id}",
            lambda p: skin_simulation_units(_n_sim(p)),
            doc_url="https://docs.perfectcorp.com/reference/ai_skin_simulation"),
    Feature("makeup_vto", "AI Makeup Virtual Try-On",
            "/s2s/v2.0/task/makeup-vto", "/s2s/v2.0/task/makeup-vto/{task_id}",
            lambda p: 1, doc_url="https://docs.perfectcorp.com/reference/makeup_vto"),
    Feature("hair_color", "AI Hair Color Virtual Try-On",
            "/s2s/v2.0/task/hair-color", "/s2s/v2.0/task/hair-color/{task_id}",
            lambda p: 1, doc_url="https://docs.perfectcorp.com/reference/ai_hair_color"),
    Feature("beard_style", "AI Beard Style Generator",
            "/s2s/v2.0/task/beard-style", "/s2s/v2.0/task/beard-style/{task_id}",
            lambda p: 2, template_path="/s2s/v2.0/task/template/beard-style",
            doc_url="https://docs.perfectcorp.com/reference/ai_beard_style"),
    Feature("earring", "AI Earrings Virtual Try-On",
            "/s2s/v2.0/task/2d-vto/earring", "/s2s/v2.0/task/2d-vto/earring/{task_id}",
            lambda p: 2 if len(p.get("object_infos", [])) > 1 else 1,
            doc_url="https://docs.perfectcorp.com/reference/ai_earrings"),
    Feature("necklace", "AI Necklace Virtual Try-On",
            "/s2s/v2.0/task/2d-vto/necklace", "/s2s/v2.0/task/2d-vto/necklace/{task_id}",
            lambda p: 1, doc_url="https://docs.perfectcorp.com/reference/ai_necklace"),
]}

# Free utility endpoints (no units): file upload, polling, templates, unit balance, task delete.
FILE_PATH = "/s2s/v2.0/file"
CREDIT_PATH = "/s2s/v1.0/client/credit"
CREDIT_HISTORY_PATH = "/s2s/v1.0/client/credit/history"
FEATURE_COST_PATH = "/s2s/v2.0/credit/feature-cost"
TASK_DELETE_PATH = "/s2s/v2.0/task/delete"


def units_for(feature: str, payload: dict) -> int:
    return FEATURES[feature].units(payload)


def cost_table() -> list[dict]:
    """Human-readable price list used by the UI, README and tests."""
    return [
        {"feature": "AI Skin Analysis (full scan, 12 SD concerns)", "api": "skin_analysis", "units": skin_analysis_units(12)},
        {"feature": "AI Skin Analysis (re-scan, 4 tracked concerns)", "api": "skin_analysis", "units": skin_analysis_units(4)},
        {"feature": "AI Skin Simulation (wedding-day goal, up to 4 concerns)", "api": "skin_simulation", "units": 4},
        {"feature": "AI Makeup Virtual Try-On (one event look)", "api": "makeup_vto", "units": 1},
        {"feature": "AI Hair Color Virtual Try-On (one shade)", "api": "hair_color", "units": 1},
        {"feature": "AI Earrings Virtual Try-On (one pair)", "api": "earring", "units": 1},
        {"feature": "AI Necklace Virtual Try-On (one piece)", "api": "necklace", "units": 1},
        {"feature": "AI Beard Style Generator (one style)", "api": "beard_style", "units": 2},
        {"feature": "File upload, polling, templates, unit balance, task delete", "api": "utility", "units": 0},
    ]
