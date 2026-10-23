"""The countdown planner is a deterministic, explainable rules engine."""
import copy
import json
from datetime import date, timedelta
from functools import lru_cache

import pytest

from app.engine import catalog
from app.engine.concerns import normalise
from app.engine.knowledge import RULES
from app.engine.planner import PlanInput, build_plan, plan_type
from app.mock.engine import MockEngine
from app.mock.personas import variant_bytes
from app.youcam.features import FULL_SCAN

TODAY = date(2026, 10, 23)


@lru_cache(maxsize=None)
def _scan(pid):
    res, _ = MockEngine().skin_analysis(variant_bytes(pid, "face"), {"dst_actions": FULL_SCAN, "format": "json"})
    return normalise(res)


def scan_for(pid="ananya"):
    return copy.deepcopy(_scan(pid))


def synthetic(scores: dict, skin="Normal"):
    out = [{"type": k, "raw_score": v - 10, "ui_score": v, "mask_urls": []} for k, v in scores.items()]
    out += [{"type": "skin_type", "region": r, "skin_type": skin} for r in ("whole", "t_zone", "u_zone")]
    return normalise({"output": out})


def plan(days, scan=None, **kw):
    inp = PlanInput(wedding_date=TODAY + timedelta(days=days), today=TODAY, **kw)
    return build_plan(inp, scan or scan_for())


AGEING = {"wrinkle": 52, "texture": 58, "pore": 70, "acne": 80, "oiliness": 80, "moisture": 78, "redness": 82,
          "age_spot": 77, "dark_circle_v2": 80, "eye_bag": 85, "radiance": 76}


@pytest.mark.parametrize("days,kind", [(120, "full"), (60, "full"), (59, "standard"), (30, "standard"),
                                       (29, "gentle"), (14, "gentle"), (13, "rescue"), (1, "rescue")])
def test_plan_type_by_runway(days, kind):
    assert plan_type(days) == kind
    assert plan(days)["plan_type"] == kind


def test_retinol_only_with_eight_weeks():
    s = synthetic(AGEING)
    long = plan(90, s, city="bengaluru", budget="premium")
    short = plan(45, s, city="bengaluru", budget="premium")
    assert "retinol" in [a["key"] for a in long["actives"]]
    assert "retinol" not in [a["key"] for a in short["actives"]]
    skip = [x for x in short["skipped"] if x["key"] == "retinol"]
    assert skip and skip[0]["reason"]["id"] == "R-TIME-SKIP"
    stops = [m for m in long["milestones"] if m["rule"] == "R-STOP-RETINOL"]
    assert stops and stops[0]["d"] == -7


def test_pregnancy_excludes_retinoids_and_leave_on_acids():
    p = plan(90, synthetic(AGEING), city="bengaluru", budget="premium", pregnant=True)
    keys = {a["key"] for a in p["actives"]}
    assert not keys & {"retinol", "salicylic_acid", "lactic_acid", "alpha_arbutin"}
    assert any(s["reason"]["id"] == "R-PREG" for s in p["skipped"])


def test_sensitive_skin_gets_no_exfoliants():
    acne = {"acne": 50, "pore": 55, "texture": 60, "oiliness": 62, "moisture": 80, "redness": 70, "age_spot": 80,
            "dark_circle_v2": 82, "eye_bag": 85, "radiance": 78, "wrinkle": 88}
    p = plan(70, synthetic(acne, "Oily"), sensitive=True, budget="premium")
    assert not any(a["exfoliant"] for a in p["actives"])
    assert p["actives"], "sensitive skin still gets gentle actives"


def test_nothing_new_in_the_last_two_weeks():
    for days in (90, 58, 35, 20):
        p = plan(days, budget="premium")
        wedding = date.fromisoformat(p["wedding_date"])
        for m in p["milestones"]:
            if m["title"]["en"].startswith(("Add ", "Patch-test")):
                assert (wedding - date.fromisoformat(m["date"])).days > 14, m


def test_rescue_plan_starts_no_actives():
    p = plan(9)
    assert p["actives"] == [] and any(r["id"] == "R-RESCUE" for r in p["rules"])


def test_climate_changes_the_textures():
    humid = plan(58, city="mumbai")
    assert any(r["id"] == "R-HUMID" for r in humid["rules"])
    am = [s["product"] for s in humid["phases"][1]["am"]]
    assert "mo_gel" in am and "ss_gel" in am
    dry = plan(58, scan_for("meera"), city="jaipur")
    assert any(r["id"] == "R-DRY" for r in dry["rules"])
    assert "mo_cream" in [s["product"] for s in dry["phases"][0]["am"]]


def test_smog_and_season_switch_for_a_delhi_winter_wedding():
    p = plan((date(2026, 12, 20) - TODAY).days, city="delhi", budget="balanced")
    ids = {r["id"] for r in p["rules"]}
    assert "R-SEASON" in ids and "R-SMOG" in ids
    sw = [m for m in p["milestones"] if m["rule"] == "R-SEASON"][0]
    assert sw["date"] == "2026-12-01"


def test_budget_caps_are_respected():
    for tier in ("essential", "balanced", "premium"):
        p = plan(58, budget=tier)
        assert p["total"] <= catalog.TIERS[tier]["cap"], tier
        assert sum(i["price"] for i in p["products"]) == p["total"]


def test_wedding_rituals_add_safety_rules():
    p = plan(40, events=["mehendi", "haldi", "wedding"])
    ids = {r["id"] for r in p["rules"]}
    assert {"R-HENNA", "R-HALDI"} <= ids
    p2 = plan(40, events=["wedding"])
    assert "R-HENNA" not in {r["id"] for r in p2["rules"]}


def test_every_reference_resolves_and_is_bilingual():
    for days in (120, 58, 20, 5):
        for city in ("mumbai", "delhi", "jaipur"):
            for role in ("bride", "groom", "guest"):
                p = plan(days, city=city, role=role, budget="premium")
                for ph in p["phases"]:
                    for s in ph["am"] + ph["pm"] + ph["weekly"]:
                        assert s["product"] in catalog.PRODUCTS
                for r in p["rules"]:
                    assert r["id"] in RULES and r["en"] and r["hi"]
                for m in p["milestones"]:
                    assert m["title"]["en"] and m["title"]["hi"]


def test_plan_is_deterministic():
    a = json.dumps(plan(58), sort_keys=True)
    b = json.dumps(plan(58), sort_keys=True)
    assert a == b


def test_focus_comes_from_the_weakest_scores():
    p = plan(58)
    assert [f["id"] for f in p["focus"]] == ["oiliness", "dark_circle_v2", "radiance"]
    assert any(r["id"] == "R-FOCUS" for r in p["rules"])
