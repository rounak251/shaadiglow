"""Every wedding look and catalogue item must be a valid YouCam request."""
import json
from pathlib import Path

import pytest

from app.engine import catalog, looks
from app.youcam.mocktransport import HAIR_PRESETS, MAKEUP_CATEGORIES, PATTERNS

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("look", [lk["id"] for lk in looks.LOOKS])
@pytest.mark.parametrize("shade", [None, "found_0", "found_7"])
def test_look_effects_follow_the_makeup_schema(look, shade):
    effects, used = looks.effects_for(look, shade)
    assert effects[0]["category"] == "skin_smooth"
    for e in effects:
        assert e["category"] in MAKEUP_CATEGORIES
        labels = PATTERNS.get(e["category"])
        name = (e.get("shape") or {}).get("name") if e["category"] == "lip_color" else (e.get("pattern") or {}).get("name")
        if labels is not None:
            assert name in labels, (look, e["category"], name)
            need = labels.get(name) or 1
            assert len(e["palettes"]) >= need
        for p in e.get("palettes", []):
            assert p["color"].startswith("#") and len(p["color"]) == 7
            for k, v in p.items():
                if k.endswith(("Intensity", "Density", "Size", "Level", "Strength")) or k in ("gloss",):
                    assert 0 <= v <= 100, (k, v)
    assert all(pid in catalog.PRODUCTS for pid in used)


def test_deeper_shades_get_deeper_reds():
    light, _ = looks.effects_for("pheras_red", "found_1")
    deep, _ = looks.effects_for("pheras_red", "found_7")
    lip = lambda eff: next(e for e in eff if e["category"] == "lip_color")["palettes"][0]["color"]
    assert lip(light) == "#B3132B" and lip(deep) == "#8E1022"


def test_each_role_has_looks():
    for role in ("bride", "groom", "guest"):
        assert looks.looks_for(role)


def test_hair_and_jewellery_items_are_valid():
    for p in catalog.HAIR:
        assert p["vto"]["preset"] in HAIR_PRESETS
    for p in catalog.JEWELLERY:
        assert (ROOT / "app/static/jewellery" / p["vto"]["ref"]).exists()
        assert (ROOT / "app/static" / p["art"]["src"].removeprefix("/static/")).exists()
        assert p["vto"]["kind"] in ("earring", "necklace")


def test_catalogue_is_unbranded_and_priced():
    for p in catalog.PRODUCTS.values():
        assert p["price"] > 0 and p["name"]
        assert p["tier"] in catalog.TIERS


def test_shade_matching_picks_a_close_foundation():
    assert catalog.shade_for((241, 211, 190))["id"] == "found_0"
    assert catalog.shade_for((110, 68, 41))["id"] == "found_7"


def test_patterns_file_came_from_the_official_catalog():
    meta = json.loads((ROOT / "app/youcam/patterns.json").read_text())
    assert "plugins-media.makeupar.com" in meta["_source"]
