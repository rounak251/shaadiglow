#!/usr/bin/env python3
"""Verify the live YouCam API with as few units as possible, and record real fixtures.

    export YOUCAM_API_KEY=...            # never commit it
    export YOUCAM_REGION=india           # or global; YOUCAM_BASE_URL overrides both
    python scripts/live_smoke.py --dry-run          # plan + unit estimate, no calls, no key needed
    python scripts/live_smoke.py                    # --verify: every endpoint once (~19 units)
    python scripts/live_smoke.py --prewarm core     # cache the sample-persona demo flows (~89 units)
    python scripts/live_smoke.py --noise            # measure scan-to-scan variation (18 units)

--verify   Calls each API once with the cheapest legal request and writes the real
           request/response JSON (pre-signed URLs redacted) and result images to
           fixtures/recorded/.  Free calls (unit balance, feature-cost price list,
           File API, templates, task delete) are used to check prices and clean up.
           The unit balance is read before and after every paid call, so the script
           prints "documented vs actually charged" per feature.
--prewarm  Runs the exact calls the app makes for the sample personas through the
           app's own service layer and copies the results into cache_seed/live/.
           Commit that folder: a fresh deploy then serves the samples for 0 units.
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
from PIL import Image  # noqa: E402

from app import flows, imaging  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.engine import catalog, looks  # noqa: E402
from app.engine.progress import tracked  # noqa: E402
from app.mock.personas import variant_bytes  # noqa: E402
from app.services import YouCamService  # noqa: E402
from app.youcam.errors import YouCamEngineError  # noqa: E402
from app.youcam.client import YouCamClient, result_urls  # noqa: E402
from app.youcam.features import FULL_SCAN, units_for  # noqa: E402

REC = ROOT / "fixtures" / "recorded"
SEED = ROOT / "cache_seed"
JEWEL = ROOT / "app" / "static" / "jewellery"

VERIFY_PLAN = [  # (feature, image, params builder) - cheapest legal request per API
    ("skin_analysis", ("ananya", "face"), lambda: flows.scan_params(["acne", "pore", "oiliness", "skin_type"])),
    ("skin_simulation", ("ananya", "face"), lambda: {"radiance": 0.5}),
    ("makeup_vto", ("ananya", "face"), lambda: {"version": "1.0", "effects": [
        {"category": "lip_color", "shape": {"name": "original"}, "style": {"type": "full"},
         "palettes": [{"color": "#B3132B", "texture": "matte", "colorIntensity": 80}]}]}),
    ("hair_color", ("ananya", "portrait"), lambda: {"preset": "Burgundy"}),
    ("earring", ("meera", "portrait"), lambda: {}),
    ("necklace", ("meera", "portrait"), lambda: {}),
    ("beard_style", ("arjun", "beard"), None),   # template id comes from the template list
]


def redact(obj):
    s = json.dumps(obj)
    s = re.sub(r'(https://[^"?\s]+)\?[^"\s]*', r'\1?<signature-redacted>', s)
    return json.loads(s)


def save_json(name: str, obj) -> None:
    REC.mkdir(parents=True, exist_ok=True)
    (REC / name).write_text(json.dumps(redact(obj), indent=1))


def estimate(feature: str, params: dict, n_refs: int = 0) -> int:
    return units_for(feature, {**params, "object_infos": [{}] * max(1, n_refs)})


async def verify(client: YouCamClient, dry: bool) -> None:
    rows = []
    if dry:
        total = 0
        for feature, img, build in VERIFY_PLAN:
            p = build() if build else {"template_id": "<first template>"}
            u = estimate(feature, p)
            total += u
            print(f"  {feature:16s} {u:3d} units  ({img[0]}/{img[1]})")
        print(f"  total            {total:3d} units (+ free: credit, feature-cost, file upload, templates, delete)")
        return
    bal0 = await client.credit()
    print(f"unit balance: {bal0}")
    save_json("credit_200.json", {"results_total_units": bal0})
    skus = await client.feature_costs()
    save_json("feature_cost_200.json", {"skus": skus})
    tasks = []
    for feature, (pid, variant), build in VERIFY_PLAN:
        image = variant_bytes(pid, variant)
        fid = await client.upload(image, "image/jpeg", f"{pid}_{variant}.jpg")
        if feature == "beard_style":
            tpl = await client.templates("beard_style")
            save_json("beard_templates_200.json", {"templates": tpl})
            params = {"template_id": tpl[0]["id"]}
        else:
            params = build()
        payload = {"src_file_id": fid, **params}
        if feature in ("earring", "necklace"):
            ref_name = "jhumka_gold_ref.jpg" if feature == "earring" else "kundan_choker_ref.jpg"
            rid = await client.upload((JEWEL / ref_name).read_bytes(), "image/jpeg", ref_name)
            spec = flows.EARRING_PARAMS if feature == "earring" else flows.NECKLACE_PARAMS
            payload.update({"ref_file_ids": [rid], "source_info": {"name": fid},
                            "object_infos": [{"name": rid, "parameter": spec}]})
        before = await client.credit()
        t0 = time.monotonic()
        try:
            res = await client.run(feature, payload)
        except Exception as e:  # noqa: BLE001 - record and continue with the next API
            print(f"  {feature}: FAILED {e}")
            save_json(f"{feature}_error.json", {"error": str(e), "request": {**payload, "src_file_id": "<file_id>"}})
            rows.append((feature, estimate(feature, payload), None, "failed"))
            continue
        await asyncio.sleep(2)
        after = await client.credit()
        charged = round(before - after, 2)
        doc = estimate(feature, payload, len(payload.get("ref_file_ids", [])))
        rows.append((feature, doc, charged, f"{time.monotonic() - t0:.1f}s/{res.polls} polls"))
        save_json(f"{feature}_request.json", {**payload, "src_file_id": "<file_id>"})
        save_json(f"{feature}_response.json", {"status": 200, "data": res.data})
        urls = result_urls(res.data)
        if feature == "skin_analysis":
            out = res.data.get("results", {}).get("output", [])
            urls = [u for o in out for u in (o.get("mask_urls") or [])][:2]
        for i, u in enumerate(urls[:2]):
            data = await client.download(u)
            ext = "png" if data[:4] == b"\x89PNG" else "jpg"
            (REC / f"{feature}_result_{i}.{ext}").write_bytes(data)
        tasks.append(res.task_id)
        print(f"  {feature:16s} documented {doc:3d}  charged {charged}  {rows[-1][3]}")
    if tasks:
        ok = await client.delete_task(tasks[-1])          # proves the Task Management API (free)
        print(f"task delete: {'ok' if ok else 'failed'}")
    bal1 = await client.credit()
    save_json("units_measured.json", {"before": bal0, "after": bal1, "spent": round(bal0 - bal1, 2),
                                      "per_feature": [{"feature": f, "documented": d, "charged": c, "note": n}
                                                      for f, d, c, n in rows]})
    print(f"spent {round(bal0 - bal1, 2)} units; fixtures in {REC.relative_to(ROOT)}")


def prewarm_calls(level: str):
    """(persona, feature, variant, params, refs, ref_params) in the order the demo uses them."""
    calls = []
    for pid in ("ananya", "arjun", "meera"):
        calls.append((pid, "scan", None))
    bride = [lk["id"] for lk in looks.looks_for("bride")]
    groom = [lk["id"] for lk in looks.looks_for("groom")]
    guest = [lk["id"] for lk in looks.looks_for("guest")]
    hair_all = [p["id"] for p in catalog.HAIR]
    jewels = [p["id"] for p in catalog.JEWELLERY]
    plan = {
        "ananya": {"sim": True, "looks": bride, "hair": hair_all[:2] if level == "core" else hair_all,
                   "jewel": ["jhumka_gold", "kundan_choker"] if level == "core" else jewels},
        "arjun": {"sim": level == "full", "looks": groom, "hair": ["hair_black"] if level == "core" else hair_all,
                  "beard": 3 if level == "core" else 6},
        "meera": {"sim": True, "looks": guest, "hair": [] if level == "core" else hair_all, "jewel": jewels},
    }
    return plan


async def prewarm(level: str, dry: bool, settings=None, seed_root: Path = SEED) -> int:
    """Returns units spent.  `settings`/`seed_root` let the test-suite run this against the mock."""
    plan = prewarm_calls(level)
    est = 0
    for pid, p in plan.items():
        est += 14 + (4 if p.get("sim") else 0) + len(p["looks"]) + len(p["hair"]) + len(p.get("jewel", [])) \
            + 2 * p.get("beard", 0) + (9 if pid == "arjun" else 0)
    print(f"prewarm {level}: about {est} units")
    if dry:
        return 0
    tmp = Path(tempfile.mkdtemp(prefix="sg_prewarm_"))
    s = settings or load_settings()
    s.data_dir, s.seed_dirs, s.reserve_units, s.client_daily_units = tmp, [seed_root], 0, 10**6
    svc = YouCamService(s)
    skipped = []

    async def attempt(label, coro):
        # Engine errors (bad photo for this feature) cost no units: note them and keep going.
        try:
            return await coro
        except YouCamEngineError as e:
            skipped.append({"call": label, "code": e.code, "message": e.message})
            print(f"  skipped {label}: {e.message}")
    try:
        for pid, p in plan.items():
            ref = f"persona:{pid}"
            scan = (await svc.skin_scan(ref, FULL_SCAN, "prewarm"))["scan"]
            print(f"  {pid}: scan ok ({len(scan['concerns'])} concerns)")
            if pid == "arjun":
                await svc.skin_scan("persona:arjun2", tracked(scan), "prewarm")
            if p.get("sim"):
                await attempt(f"{pid}/skin_simulation", svc.run("skin_simulation", svc.image_bytes(ref, "face"),
                              flows.sim_params(flows.sim_focus(scan)), "prewarm"))
            shade = catalog.shade_for(imaging.cheek_colour(svc.image_bytes(ref, "face")))["id"]
            for lk in p["looks"]:
                params, _ = flows.makeup_params(lk, shade)
                await attempt(f"{pid}/makeup/{lk}", svc.run("makeup_vto", svc.image_bytes(ref, "face"), params, "prewarm"))
            for h in p["hair"]:
                await attempt(f"{pid}/hair/{h}", svc.run("hair_color", svc.image_bytes(ref, "portrait"), flows.hair_params(h), "prewarm"))
            for j in p.get("jewel", []):
                kind, ref_name, rp = flows.jewellery_spec(j)
                await attempt(f"{pid}/{kind}/{j}", svc.run(kind, svc.image_bytes(ref, "portrait"), {}, "prewarm",
                              refs=[svc.jewellery_ref(ref_name)], ref_params=rp))
            if p.get("beard"):
                for t in (await svc.templates("beard_style"))[: p["beard"]]:
                    await attempt(f"{pid}/beard/{t['id']}", svc.run("beard_style", svc.image_bytes(ref, "beard"),
                                  flows.beard_params(t["id"]), "prewarm"))
            print(f"  {pid}: done")
    finally:
        await svc.close()
        ns = svc.cache.ns
        src = tmp / "cache" / ns
        if src.exists():
            n = 0
            for d in src.glob("*/*"):
                dest = seed_root / ns / d.parent.name / d.name
                if not dest.exists():
                    shutil.copytree(d, dest)
                    n += 1
            print(f"copied {n} cached results into {seed_root}/{ns} (commit them)")
        if skipped:
            save_json("prewarm_skipped.json", skipped)
            print(f"skipped {len(skipped)} calls (engine errors, 0 units); see fixtures/recorded/prewarm_skipped.json")
        print(f"units spent: {svc.ledger.spent}")
        shutil.rmtree(tmp, ignore_errors=True)
    return svc.ledger.spent


async def noise(client: YouCamClient, dry: bool) -> None:
    concerns = ["acne", "pore", "oiliness", "dark_circle_v2"]
    print(f"noise check: 2 scans x {units_for('skin_analysis', {'dst_actions': concerns})} units")
    if dry:
        return
    img = Image.open(io.BytesIO(variant_bytes("ananya", "face")))
    scores = []
    for q in (95, 90):    # identical photo, different bytes: two real API calls
        b = io.BytesIO()
        img.save(b, "JPEG", quality=q)
        fid = await client.upload(b.getvalue(), "image/jpeg", f"noise_{q}.jpg")
        res = await client.run("skin_analysis", {"src_file_id": fid, **flows.scan_params(concerns)})
        scores.append({o["type"]: o.get("ui_score") for o in res.data["results"]["output"] if "ui_score" in o})
    diffs = {k: abs(scores[0][k] - scores[1].get(k, scores[0][k])) for k in scores[0]}
    save_json("noise_check.json", {"scores": scores, "abs_diff": diffs})
    print(f"abs ui_score differences: {diffs}; suggested NOISE_BAND = {max(diffs.values()) + 1}")


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true", help="each endpoint once (default)")
    ap.add_argument("--prewarm", choices=["core", "full"])
    ap.add_argument("--noise", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and unit estimate only")
    a = ap.parse_args()
    s = load_settings()
    if not a.dry_run and not s.is_live:
        sys.exit("Set YOUCAM_API_KEY first (and YOUCAM_REGION/YOUCAM_BASE_URL if needed), or use --dry-run.")
    print(f"YouCam host: {s.base_url}  mode: {'DRY RUN' if a.dry_run else 'LIVE'}")
    async with httpx.AsyncClient(timeout=httpx.Timeout(90, connect=20)) as http:
        client = YouCamClient(s.api_key or "dry-run", s.base_url, http, poll_interval=2.0)
        if a.verify or not (a.prewarm or a.noise):
            print("== verify: every endpoint once")
            await verify(client, a.dry_run)
        if a.noise:
            await noise(client, a.dry_run)
    if a.prewarm:
        await prewarm(a.prewarm, a.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
