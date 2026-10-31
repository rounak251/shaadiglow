"""ShaadiGlow: FastAPI backend + static mobile web app.

    uvicorn app.main:app --reload            # mock mode (no key needed)
    YOUCAM_API_KEY=... uvicorn app.main:app  # live YouCam calls, same code
"""
from __future__ import annotations

import re
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import flows, imaging
from .config import load_settings
from .engine import catalog, climate, looks, progress
from .engine.ics import to_ics
from .engine.planner import PlanInput, build_plan
from .mock.personas import public_list
from .services import YouCamService
from .youcam.errors import BudgetExceeded, YouCamEngineError, YouCamError, YouCamTimeout
from .youcam.features import FEATURES, FULL_SCAN, cost_table

STATIC = Path(__file__).resolve().parent / "static"
VERSION = "1.0.0"
IST = timezone(timedelta(hours=5, minutes=30))
REF_RE = re.compile(r"^(persona:[a-z0-9]{2,20}|upload:[a-f0-9]{24})$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    app.state.settings = settings
    app.state.svc = YouCamService(settings)
    yield
    await app.state.svc.close()


app = FastAPI(title="ShaadiGlow", version=VERSION, lifespan=lifespan, docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def svc(request: Request) -> YouCamService:
    return request.app.state.svc


def client_id(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "local")


def today_ist() -> date:
    return datetime.now(IST).date()


def check_ref(ref: str) -> str:
    if not REF_RE.match(ref or ""):
        raise HTTPException(400, "unknown photo reference")
    return ref


# ---------------------------------------------------------------------------- errors
@app.exception_handler(BudgetExceeded)
async def _budget(_: Request, e: BudgetExceeded):
    return JSONResponse({"error": "budget", "message": "Live AI units are paused for this demo right now: "
                         + e.reason + ". Sample models still work.", "reason": e.reason}, status_code=402)


@app.exception_handler(YouCamEngineError)
async def _engine(_: Request, e: YouCamEngineError):
    return JSONResponse({"error": e.code, "message": e.hint, "detail": e.message}, status_code=422)


@app.exception_handler(YouCamError)
async def _yc(_: Request, e: YouCamError):
    return JSONResponse({"error": e.code, "message": e.hint, "status": e.status}, status_code=502)


@app.exception_handler(YouCamTimeout)
async def _timeout(_: Request, e: YouCamTimeout):
    return JSONResponse({"error": "timeout", "message": "The AI is busy. Please try again in a minute."},
                        status_code=504)


@app.exception_handler(imaging.BadImage)
async def _badimg(_: Request, e: imaging.BadImage):
    return JSONResponse({"error": "bad_image", "message": str(e)}, status_code=400)


# ---------------------------------------------------------------------------- pages
@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest", include_in_schema=False)
async def manifest():
    return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/media/{ns}/{key}/{name}", include_in_schema=False)
async def media(ns: str, key: str, name: str, request: Request):
    p = svc(request).cache.media_path(ns, key, name)
    if not p:
        raise HTTPException(404)
    return FileResponse(p, headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/uploads/{uid}/{variant}.jpg", include_in_schema=False)
async def upload_file(uid: str, variant: str, request: Request):
    p = svc(request).store.upload_path(uid, variant)
    if not p:
        raise HTTPException(404)
    return FileResponse(p, headers={"Cache-Control": "private, max-age=86400"})


# ---------------------------------------------------------------------------- meta
@app.get("/api/health")
async def health(request: Request):
    return {"ok": True, "mode": request.app.state.settings.mode, "version": VERSION}


@app.get("/api/config")
async def config(request: Request):
    s = request.app.state.settings
    return {"version": VERSION, **s.public(), "today": today_ist().isoformat(), "costs": cost_table(),
            "apis": {k: {"title": f.title, "doc": f.doc_url} for k, f in FEATURES.items()},
            "personas": public_list(), "cities": climate.city_list(), "full_scan": FULL_SCAN,
            "budgets": catalog.TIERS, "units": svc(request).units()}


@app.get("/api/catalog")
async def get_catalog():
    return {"products": catalog.public(), "notice": "Sample catalogue: fictional, unbranded products; prices are illustrative."}


@app.get("/api/units")
async def units(request: Request):
    await svc(request).refresh_balance(max_age=30)
    return svc(request).units()


# ---------------------------------------------------------------------------- photos
@app.post("/api/photo")
async def photo(request: Request, face: UploadFile = File(...), portrait: UploadFile | None = File(None),
                source: Literal["upload", "camera_kit"] = Form("upload")):
    s = request.app.state.settings
    limit = s.max_upload_mb * 1024 * 1024
    fb = await face.read(limit + 1)
    pb = await portrait.read(limit + 1) if portrait else None
    if len(fb) > limit or (pb and len(pb) > limit):
        raise HTTPException(413, f"Photos must be under {s.max_upload_mb} MB")
    variants = imaging.make_variants(fb, pb)
    uid = svc(request).store.save_upload(variants, source)
    ref = f"upload:{uid}"
    return {"image_ref": ref, "source": source,
            "urls": {v: svc(request).image_url(ref, v) for v in ("face", "portrait", "beard")}}


class ShadeIn(BaseModel):
    image_ref: str


@app.post("/api/shade")
async def shade(body: ShadeIn, request: Request):
    data = svc(request).image_bytes(check_ref(body.image_ref), "face")
    p = catalog.shade_for(imaging.cheek_colour(data))
    return {"product": p["id"], "name": p["name"], "hex": p["art"]["color"],
            "shades": [{"id": f["id"], "name": f["name"], "hex": f["art"]["color"]} for f in catalog.FOUNDATIONS]}


# ---------------------------------------------------------------------------- skin
class ScanIn(BaseModel):
    image_ref: str
    profile_id: str | None = None
    kind: Literal["full", "quick"] = "full"
    concerns: list[str] | None = None
    camera_kit: bool = False


@app.post("/api/scan")
async def scan(body: ScanIn, request: Request):
    ref = check_ref(body.image_ref)
    if ref.startswith("upload:") and svc(request).live and not request.app.state.settings.allow_live_uploads:
        raise HTTPException(403, "Live uploads are switched off on this demo; try a sample model.")
    if body.kind == "quick":
        wanted = [c for c in (body.concerns or []) if c in FULL_SCAN and c != "skin_type"][:4]
        if not wanted:
            raise HTTPException(400, "a quick re-scan needs 1-4 tracked concerns")
    else:
        wanted = FULL_SCAN
    res = await svc(request).skin_scan(ref, wanted, client_id(request), camera_kit=body.camera_kit)
    entry = {"scan_id": res["task_id"], "task_id": res["task_id"], "at": datetime.now(IST).isoformat(timespec="seconds"),
             "image_ref": ref, "kind": body.kind, "scan": res["scan"]}
    if body.profile_id:
        try:
            svc(request).store.add_scan(body.profile_id, entry)
        except ValueError:
            pass
    return {**res, "image_ref": ref, "image": svc(request).image_url(ref, "face"), "kind": body.kind}


class SimIn(BaseModel):
    image_ref: str
    focus: list[str] = Field(default_factory=list)
    strength: float = Field(0.6, ge=0.1, le=1.0)
    profile_id: str | None = None


@app.post("/api/simulate")
async def simulate(body: SimIn, request: Request):
    ref = check_ref(body.image_ref)
    params = flows.sim_params(body.focus, body.strength)
    res = await svc(request).run("skin_simulation", svc(request).image_bytes(ref, "face"), params, client_id(request))
    svc(request).store.add_task(body.profile_id, res.get("task_id"), ref)
    return {**res, "before": svc(request).image_url(ref, "face"), "params": params}


# ---------------------------------------------------------------------------- plan
class PlanIn(BaseModel):
    scan: dict
    wedding_date: date
    city: str = "delhi"
    budget: Literal["essential", "balanced", "premium"] = "balanced"
    role: Literal["bride", "groom", "guest"] = "bride"
    pregnant: bool = False
    sensitive: bool = False
    events: list[str] = Field(default_factory=lambda: ["haldi", "mehendi", "sangeet", "wedding", "reception"])
    today: date | None = None


def _plan(body: PlanIn) -> dict:
    if body.city not in climate.CITIES:
        raise HTTPException(400, "unknown city")
    inp = PlanInput(wedding_date=body.wedding_date, today=body.today or today_ist(), city=body.city,
                    budget=body.budget, role=body.role, pregnant=body.pregnant, sensitive=body.sensitive,
                    events=body.events)
    return build_plan(inp, body.scan)


@app.post("/api/plan")
async def plan(body: PlanIn):
    return _plan(body)


@app.post("/api/plan.ics")
async def plan_ics(body: PlanIn, lang: str = "en"):
    return Response(to_ics(_plan(body), lang), media_type="text/calendar",
                    headers={"Content-Disposition": 'attachment; filename="shaadiglow-plan.ics"'})


# ---------------------------------------------------------------------------- try-on
@app.get("/api/looks")
async def get_looks(role: str = "bride"):
    out = []
    for lk in looks.looks_for(role):
        prods = [catalog.get(p) for p in lk["products"]]
        out.append({**lk, "items": [{"id": p["id"], "name": p["name"], "price": p["price"], "art": p["art"]}
                                     for p in prods]})
    return {"looks": out}


class MakeupIn(BaseModel):
    image_ref: str
    look_id: str
    shade_id: str | None = None
    profile_id: str | None = None


@app.post("/api/tryon/makeup")
async def tryon_makeup(body: MakeupIn, request: Request):
    ref = check_ref(body.image_ref)
    if body.look_id not in looks.BY_ID:
        raise HTTPException(404, "unknown look")
    params, used = flows.makeup_params(body.look_id, body.shade_id)
    res = await svc(request).run("makeup_vto", svc(request).image_bytes(ref, "face"), params, client_id(request))
    svc(request).store.add_task(body.profile_id, res.get("task_id"), ref)
    return {**res, "before": svc(request).image_url(ref, "face"), "products": used}


class ProductTryIn(BaseModel):
    image_ref: str
    product_id: str
    profile_id: str | None = None


@app.post("/api/tryon/hair")
async def tryon_hair(body: ProductTryIn, request: Request):
    ref = check_ref(body.image_ref)
    p = catalog.PRODUCTS.get(body.product_id)
    if not p or p["category"] != "Hair colour":
        raise HTTPException(404, "unknown hair colour")
    res = await svc(request).run("hair_color", svc(request).image_bytes(ref, "portrait"),
                                 flows.hair_params(p["id"]), client_id(request))
    svc(request).store.add_task(body.profile_id, res.get("task_id"), ref)
    return {**res, "before": svc(request).image_url(ref, "portrait"), "products": [p["id"]]}


@app.post("/api/tryon/jewellery")
async def tryon_jewellery(body: ProductTryIn, request: Request):
    ref = check_ref(body.image_ref)
    p = catalog.PRODUCTS.get(body.product_id)
    if not p or p["category"] != "Jewellery":
        raise HTTPException(404, "unknown jewellery item")
    kind, ref_name, params = flows.jewellery_spec(p["id"])
    res = await svc(request).run(kind, svc(request).image_bytes(ref, "portrait"), {}, client_id(request),
                                 refs=[svc(request).jewellery_ref(ref_name)], ref_params=params)
    svc(request).store.add_task(body.profile_id, res.get("task_id"), ref)
    return {**res, "before": svc(request).image_url(ref, "portrait"), "products": [p["id"]]}


@app.get("/api/tryon/beard/templates")
async def beard_templates(request: Request):
    return {"templates": await svc(request).templates("beard_style")}


class BeardIn(BaseModel):
    image_ref: str
    template_id: str
    profile_id: str | None = None


@app.post("/api/tryon/beard")
async def tryon_beard(body: BeardIn, request: Request):
    ref = check_ref(body.image_ref)
    ids = {t.get("id") for t in await svc(request).templates("beard_style")}
    if body.template_id not in ids:
        raise HTTPException(404, "unknown beard template")
    res = await svc(request).run("beard_style", svc(request).image_bytes(ref, "beard"),
                                 flows.beard_params(body.template_id), client_id(request))
    svc(request).store.add_task(body.profile_id, res.get("task_id"), ref)
    return {**res, "before": svc(request).image_url(ref, "beard")}


# ---------------------------------------------------------------------------- progress & privacy
@app.get("/api/profile/{pid}")
async def profile(pid: str, request: Request):
    try:
        prof = svc(request).store.profile(pid)
    except ValueError:
        raise HTTPException(400, "bad profile id")
    scans = prof.get("scans", [])
    full = [s for s in scans if s.get("kind") == "full"]
    out = {"id": pid, "scans": scans, "tasks": len(prof.get("tasks", []))}
    if full and len(scans) > 1:
        out["compare"] = progress.compare(full[0]["scan"], scans[-1]["scan"])
        out["tracked"] = progress.tracked(full[0]["scan"])
    elif full:
        out["tracked"] = progress.tracked(full[0]["scan"])
    return out


@app.get("/api/demo/progress/{persona}")
async def demo_progress(persona: str, request: Request):
    """Example timeline built from two real photos of the same person (sample groom)."""
    if persona != "arjun":
        raise HTTPException(404, "progress demo is available for the sample groom")
    a = await svc(request).skin_scan("persona:arjun", FULL_SCAN, client_id(request))
    tracked = progress.tracked(a["scan"])
    b = await svc(request).skin_scan("persona:arjun2", tracked, client_id(request))
    return {"baseline": {**a, "image": "/static/personas/arjun/face.jpg", "label": "Scan 1"},
            "latest": {**b, "image": "/static/personas/arjun2/face.jpg", "label": "Re-scan"},
            "tracked": tracked, "compare": progress.compare(a["scan"], b["scan"])}


@app.post("/api/profile/{pid}/delete")
async def delete_profile(pid: str, request: Request):
    try:
        prof = svc(request).store.delete_profile(pid)
    except ValueError:
        raise HTTPException(400, "bad profile id")
    deleted = await svc(request).delete_tasks(prof.get("tasks", []))
    return {"deleted_local": True, "youcam_tasks_deleted": deleted, "uploads_deleted": len(prof.get("uploads", []))}
