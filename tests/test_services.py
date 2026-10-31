"""Cache, unit ledger, budget guard and mock/live switching."""
import asyncio
import shutil

import pytest

from app import flows
from app.config import REGION_HOSTS, load_settings
from app.services import YouCamService
from app.youcam.cache import DiskCache
from app.youcam.errors import BudgetExceeded
from app.youcam.features import FULL_SCAN, cost_table, skin_analysis_units
from app.youcam.ledger import UnitLedger

run = asyncio.run


def make_service(tmp_path, **env):
    base = {"SG_DATA_DIR": str(tmp_path / "data"), "SG_CACHE_SEED_DIRS": str(tmp_path / "seed"),
            "SG_MOCK_LATENCY": "0.01"}
    base.update(env)
    return YouCamService(load_settings(base))


def test_second_identical_call_is_a_free_cache_hit(tmp_path):
    svc = make_service(tmp_path)

    async def go():
        a = await svc.skin_scan("persona:ananya", FULL_SCAN, "1.2.3.4")
        calls = len(svc.mock.calls)
        b = await svc.skin_scan("persona:ananya", FULL_SCAN, "1.2.3.4")
        await svc.close()
        return a, b, calls, len(svc.mock.calls)
    a, b, calls_after_first, calls_after_second = run(go())
    assert a["units_charged"] == 14 and not a["cached"]
    assert b["units_charged"] == 0 and b["cached"]
    assert calls_after_first == calls_after_second          # no request reached the API
    assert a["scan"] == b["scan"]
    assert svc.ledger.spent == 14


def test_cache_key_depends_on_image_and_params():
    k1 = DiskCache.key("makeup_vto", "abc", {"params": {"x": 1}})
    assert k1 == DiskCache.key("makeup_vto", "abc", {"params": {"x": 1}})
    assert k1 != DiskCache.key("makeup_vto", "abd", {"params": {"x": 1}})
    assert k1 != DiskCache.key("makeup_vto", "abc", {"params": {"x": 2}})
    assert k1 != DiskCache.key("hair_color", "abc", {"params": {"x": 1}})


def test_results_survive_url_expiry_because_files_are_stored(tmp_path):
    svc = make_service(tmp_path)

    async def go():
        params, _ = flows.makeup_params("pheras_red", "found_4")
        r = await svc.run("makeup_vto", svc.image_bytes("persona:ananya", "face"), params, "c")
        await svc.close()
        return r
    r = run(go())
    ns, key, name = r["url"].split("/")[2:5]
    assert svc.cache.media_path(ns, key, name).stat().st_size > 10_000


def test_seed_cache_is_served_without_spending(tmp_path):
    svc = make_service(tmp_path)
    run(svc.skin_scan("persona:arjun", FULL_SCAN, "c"))
    run(svc.close())
    shutil.copytree(tmp_path / "data" / "cache", tmp_path / "seed")       # ship it as a read-only seed
    fresh = make_service(tmp_path, SG_DATA_DIR=str(tmp_path / "data2"))
    r = run(fresh.skin_scan("persona:arjun", FULL_SCAN, "c"))
    run(fresh.close())
    assert r["cached"] and r["units_charged"] == 0 and fresh.ledger.spent == 0


def test_budget_guard_keeps_the_reserve(tmp_path):
    led = UnitLedger(tmp_path / "l.jsonl", mode="live", budget=100, reserve=60, per_client_daily=1000)
    led.authorize(14, "a")
    led.record("skin_analysis", 14, "t1", "a")
    led.record("skin_analysis", 14, "t2", "a")
    with pytest.raises(BudgetExceeded):
        led.authorize(14, "a")                                  # 100 - 28 - 14 < 60
    led2 = UnitLedger(tmp_path / "l.jsonl", mode="live", budget=100, reserve=60, per_client_daily=1000)
    assert led2.spent == 28                                     # persisted across restarts


def test_budget_guard_prefers_the_real_balance(tmp_path):
    led = UnitLedger(tmp_path / "l.jsonl", mode="live", budget=1000, reserve=50, per_client_daily=1000)
    led.set_live_balance(60)
    with pytest.raises(BudgetExceeded):
        led.authorize(14, "a")


def test_per_visitor_daily_cap(tmp_path):
    led = UnitLedger(tmp_path / "l.jsonl", mode="live", budget=1000, reserve=0, per_client_daily=20)
    led.record("skin_analysis", 14, "t", "visitor")
    with pytest.raises(BudgetExceeded):
        led.authorize(9, "visitor")
    led.authorize(9, "someone-else")


def test_mode_switches_on_the_key_alone():
    s = load_settings({})
    assert s.mode == "mock" and s.base_url == REGION_HOSTS["india"]
    s = load_settings({"YOUCAM_API_KEY": "sk_live_x"})
    assert s.mode == "live" and s.is_live
    s = load_settings({"YOUCAM_API_KEY": "k", "YOUCAM_REGION": "global"})
    assert s.base_url == REGION_HOSTS["global"]
    s = load_settings({"YOUCAM_API_KEY": "k", "YOUCAM_BASE_URL": "https://example.test/"})
    assert s.base_url == "https://example.test"
    assert load_settings({"YOUCAM_API_KEY": "k", "SG_MODE": "mock"}).mode == "mock"
    with pytest.raises(RuntimeError):
        load_settings({"SG_MODE": "live"})


def test_live_service_uses_the_network_transport(tmp_path):
    svc = make_service(tmp_path, YOUCAM_API_KEY="sk_test_not_real")
    assert svc.live and svc.mock is None
    assert svc.client.base_url == REGION_HOSTS["india"]
    assert svc.client._headers()["Authorization"] == "Bearer sk_test_not_real"
    assert svc.cache.ns == "live"
    run(svc.close())


def test_documented_skin_tiers():
    assert [skin_analysis_units(n) for n in (1, 4, 5, 8, 9, 12, 13, 16)] == [9, 9, 12, 12, 14, 14, 16, 16]
    assert [skin_analysis_units(n, hd=True) for n in (4, 8, 12, 16)] == [12, 16, 20, 22]
    assert len(FULL_SCAN) == 12 and skin_analysis_units(len(FULL_SCAN)) == 14
    assert {r["units"] for r in cost_table()} >= {14, 9, 4, 2, 1, 0}


def test_demo_only_persona_hidden_in_live_mode():
    from app.mock.personas import public_list
    assert "meera" in [p["id"] for p in public_list()]
    assert [p["id"] for p in public_list(live=True)] == ["ananya", "arjun"]
