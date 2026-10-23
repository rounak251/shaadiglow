"""`live_smoke.py --prewarm` must fill exactly the cache keys the app looks up.

Runs the prewarm against the mock into a temporary seed folder, then walks the
sample-persona journeys through the HTTP API and checks every call is a 0-unit hit.
"""
import asyncio
import importlib.util
from pathlib import Path

from app.config import load_settings

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("live_smoke", ROOT / "scripts" / "live_smoke.py")
live_smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live_smoke)


def test_prewarmed_samples_cost_zero_units(tmp_path, monkeypatch):
    seed = tmp_path / "seed"
    settings = load_settings({"SG_MOCK_LATENCY": "0.01"})
    spent = asyncio.run(live_smoke.prewarm("core", False, settings=settings, seed_root=seed))
    assert 80 <= spent <= 100

    for k in ("YOUCAM_API_KEY", "SG_MODE"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("SG_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SG_CACHE_SEED_DIRS", str(seed))
    monkeypatch.setenv("SG_MOCK_LATENCY", "0.01")
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        def free(r):
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["units_charged"] == 0 and body["cached"], body.get("api")
            return body
        for pid, role in (("ananya", "bride"), ("arjun", "groom"), ("meera", "guest")):
            ref = f"persona:{pid}"
            scan = free(c.post("/api/scan", json={"image_ref": ref}))["scan"]
            shade = c.post("/api/shade", json={"image_ref": ref}).json()["product"]
            looks = c.get(f"/api/looks?role={role}").json()["looks"]
            for lk in looks:
                free(c.post("/api/tryon/makeup", json={"image_ref": ref, "look_id": lk["id"], "shade_id": shade}))
            if pid != "arjun":
                focus = [x["id"] for x in scan["concerns"] if x["id"] != "moisture"][:4]   # same rule as app.js
                free(c.post("/api/simulate", json={"image_ref": ref, "focus": focus, "strength": 0.6}))
        free(c.post("/api/tryon/hair", json={"image_ref": "persona:ananya", "product_id": "hair_burgundy"}))
        free(c.post("/api/tryon/jewellery", json={"image_ref": "persona:ananya", "product_id": "jhumka_gold"}))
        for j in ("jhumka_gold", "kundan_choker", "pearl_layers"):
            free(c.post("/api/tryon/jewellery", json={"image_ref": "persona:meera", "product_id": j}))
        tpl = c.get("/api/tryon/beard/templates").json()["templates"]
        free(c.post("/api/tryon/beard", json={"image_ref": "persona:arjun", "template_id": tpl[0]["id"]}))
        prog = c.get("/api/demo/progress/arjun").json()
        assert prog["baseline"]["units_charged"] == 0 and prog["latest"]["units_charged"] == 0
        assert c.get("/api/units").json()["spent"] == 0
