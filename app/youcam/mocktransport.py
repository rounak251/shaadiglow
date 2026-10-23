"""httpx transport that simulates the documented YouCam API contract (no network, no units).

It answers the same endpoints with the same JSON shapes as the docs, validates
requests the way the docs say the server does (auth header, SD/HD mixing,
pattern labels, template ids, image-size limits...), runs tasks through
`app.mock.engine` and serves result files from fake pre-signed URLs.
Swap it for a real transport by setting YOUCAM_API_KEY: nothing else changes.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import re
import time
from pathlib import Path

import httpx
from PIL import Image

from ..mock.engine import DEFAULT_TEMPLATES, MockEngine
from .features import FEATURES, HD_CONCERNS, SD_CONCERNS, units_for

STORAGE = "https://mock-storage.youcam.local"
PATTERNS = json.loads((Path(__file__).with_name("patterns.json")).read_text())["categories"]
MAKEUP_CATEGORIES = {"skin_smooth", "blush", "bronzer", "concealer", "contour", "eyebrows", "eye_liner",
                     "eye_shadow", "eyelashes", "foundation", "highlighter", "lip_color", "lip_liner"}
HAIR_PRESETS = {"Jet Black", "Chocolate Brown", "Honey Blonde", "Platinum Blonde", "Ash Gray", "Rose Gold",
                "Burgundy", "Copper Red", "Lavender", "Teal Blue", "Dark Brown/Caramel Blonde",
                "Jet Black/Silver Gray", "Ash Brown/Lavender", "Rose Gold/Peach Blonde", "Burgundy/Magenta Pink",
                "Deep Blue/Teal Green", "Plum Purple/Pastel Lilac", "Copper Red/Golden Blonde",
                "Dark Gray/Ice Blonde", "Midnight Blue/Denim Blue"}
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
FEATURE_BY_PATH = {f.run_path: k for k, f in FEATURES.items()}


def _json(status: int, body: dict) -> httpx.Response:
    return httpx.Response(status, json=body)


def _bad(msg: str, code: str = "InvalidParameters") -> httpx.Response:
    return _json(400, {"status": 400, "error": msg, "error_code": code})


class MockYouCam:
    def __init__(self, balance: float = 1000.0, latency_polls: int = 1, engine: MockEngine | None = None):
        self.engine = engine or MockEngine()
        self.balance = balance
        self.latency_polls = latency_polls
        self.files: dict[str, dict] = {}      # file_id -> {"meta":..., "data": bytes|None}
        self.tasks: dict[str, dict] = {}
        self.results: dict[str, bytes] = {}   # "<task_id>/<name>" -> bytes
        self.calls: list[str] = []
        self.charged: list[tuple[str, int]] = []

    # ----------------------------------------------------------------- entry point
    def handler(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        path = url.path
        self.calls.append(f"{request.method} {path}")
        if url.host == "mock-storage.youcam.local":
            return self._storage(request)
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer ") or len(auth) < 12:
            return _json(401, {"status": 401, "error_code": "InvalidApiKey", "error": "Invalid API key"})
        try:
            body = json.loads(request.content or b"{}") if request.method == "POST" else {}
        except ValueError:
            return _bad("body is not valid JSON", "BadRequest")
        if request.method == "POST" and path == "/s2s/v2.0/file":
            return self._create_file(body)
        if request.method == "POST" and path == "/s2s/v2.0/task/delete":
            tid = body.get("task_id")
            if not tid:
                return _bad("task_id is missing")
            if tid not in self.tasks:
                return _json(400, {"status": 400, "error": "task not found", "error_code": "InvalidTaskId"})
            self.tasks.pop(tid)
            for k in [k for k in self.results if k.startswith(tid + "/")]:
                self.results.pop(k)
            return _json(200, {"status": 200})
        if request.method == "POST" and path in FEATURE_BY_PATH:
            return self._run(FEATURE_BY_PATH[path], body)
        if request.method == "GET":
            if path == "/s2s/v1.0/client/credit":
                return _json(200, {"status": 200, "results": [
                    {"id": 13105541279084536, "type": "ApiPaygToken", "amount": int(self.balance),
                     "amount_dec": round(self.balance, 2), "expiry": int((time.time() + 90 * 86400) * 1000)}]})
            if path == "/s2s/v2.0/credit/feature-cost":
                return _json(200, {"status": 200, "result": {"next_token": None, "skus": self._skus()}})
            for k, f in FEATURES.items():
                if f.template_path == path:
                    return _json(200, {"status": 200, "data": {"templates": self._templates(k), "next_token": None}})
                prefix = f.poll_path.split("{task_id}")[0]
                if path.startswith(prefix) and path.count("/") == prefix.count("/"):
                    return self._poll(k, path[len(prefix):])
        return _json(404, {"status": 404, "error": f"no mock route for {request.method} {path}"})

    # ----------------------------------------------------------------- File API
    def _create_file(self, body: dict) -> httpx.Response:
        files = body.get("files")
        if not isinstance(files, list) or not files:
            return _bad("files is required")
        out = []
        for f in files:
            if not all(k in f for k in ("content_type", "file_name", "file_size")):
                return _bad("content_type, file_name and file_size are required")
            if f["file_size"] > 10 * 1024 * 1024 and f["content_type"].startswith("image/"):
                return _bad("image files must be under 10 MB")
            fid = hashlib.sha256(f"{f['file_name']}|{f['file_size']}|{len(self.files)}|{time.time()}".encode()
                                 ).hexdigest()[:40] + "=="
            self.files[fid] = {"meta": f, "data": None}
            out.append({"content_type": f["content_type"], "file_name": f["file_name"], "file_id": fid,
                        "requests": [{"method": "PUT", "url": f"{STORAGE}/upload/{fid}",
                                      "headers": {"Content-Type": f["content_type"],
                                                  "Content-Length": str(f["file_size"])}}]})
        return _json(200, {"status": 200, "data": {"files": out}})

    def _storage(self, request: httpx.Request) -> httpx.Response:
        parts = request.url.path.strip("/").split("/", 1)
        if request.method == "PUT" and parts[0] == "upload":
            fid = parts[1]
            if fid not in self.files:
                return httpx.Response(403, text="AccessDenied")
            self.files[fid]["data"] = bytes(request.content)
            return httpx.Response(200)
        if request.method == "GET" and parts[0] == "results":
            data = self.results.get(parts[1])
            if data is None:
                return httpx.Response(404, text="NoSuchKey")
            ctype = "image/png" if parts[1].endswith(".png") else "image/jpeg"
            return httpx.Response(200, content=data, headers={"Content-Type": ctype})
        return httpx.Response(404)

    def _file(self, fid: str | None) -> bytes | None:
        f = self.files.get(fid or "")
        return f["data"] if f else None

    # ----------------------------------------------------------------- tasks
    def _run(self, feature: str, body: dict) -> httpx.Response:
        src = self._file(body.get("src_file_id"))
        if src is None:
            if body.get("src_file_id"):
                # documented: forgetting the PUT to the pre-signed URL ends in a 404/500
                return _json(404, {"status": 404, "error": "file not uploaded", "error_code": "NotFound"})
            return _bad("src_file_id or src_file_url is required")
        err = self._validate(feature, body, src)
        if isinstance(err, httpx.Response):
            return err
        cost = units_for(feature, body)
        if self.balance < cost:
            return _bad("The operation could not be completed", "CreditInsufficiency")
        tid = "mock" + hashlib.sha256(f"{feature}|{time.time_ns()}|{len(self.tasks)}".encode()).hexdigest()[:44]
        engine_error = err  # a string means the engine will fail this task (no units charged)
        self.tasks[tid] = {"id": tid, "feature": feature, "body": body, "src": src, "polls": 0, "cost": cost,
                           "engine_error": engine_error, "result": None}
        return _json(200, {"status": 200, "data": {"task_id": tid}})

    def _poll(self, feature: str, tid: str) -> httpx.Response:
        t = self.tasks.get(tid)
        if not t or t["feature"] != feature:
            return _json(400, {"status": 400, "error_code": "InvalidTaskId", "error": "Invalid task ID"})
        t["polls"] += 1
        if t["polls"] <= self.latency_polls:
            return _json(200, {"status": 200, "data": {"task_status": "running"}})
        if t["engine_error"]:
            return _json(200, {"status": 200, "data": {"task_status": "error", "error": t["engine_error"],
                                                       "error_message": "mock engine rejected the input"}})
        if t["result"] is None:
            t["result"] = self._compute(feature, t)
            self.balance -= t["cost"]               # units are only charged on success
            self.charged.append((feature, t["cost"]))
        return _json(200, {"status": 200, "data": {"task_status": "success", "results": t["result"]}})

    def _compute(self, feature: str, t: dict) -> dict:
        body, src = t["body"], t["src"]
        if feature in ("earring", "necklace"):
            refs = [self._file(i) for i in body.get("ref_file_ids", [])]
            results, files = getattr(self.engine, feature)(src, body, [r for r in refs if r])
        else:
            results, files = getattr(self.engine, feature)(src, body)
        for name, data in files.items():
            self.results[f"{t['id']}/{name}"] = data

        def fix(v):
            if isinstance(v, str) and v in files:
                return f"{STORAGE}/results/{t['id']}/{v}"
            if isinstance(v, list):
                return [fix(x) for x in v]
            if isinstance(v, dict):
                return {k: fix(x) for k, x in v.items()}
            return v
        return fix(results)

    # ----------------------------------------------------------------- validation (per docs)
    def _validate(self, feature: str, body: dict, src: bytes):
        try:
            w, h = Image.open(io.BytesIO(src)).size
        except Exception:
            return "error_decode_image"
        if feature == "skin_analysis":
            acts = body.get("dst_actions") or []
            if not acts:
                return _bad("dst_actions is required")
            for a in acts:
                if a not in SD_CONCERNS and a not in HD_CONCERNS:
                    return _bad(f"Not available dst_action {a}")
            if any(a.startswith("hd_") for a in acts) and any(not a.startswith("hd_") for a in acts):
                return _bad("cannot mix HD and SD dst_actions")
            hd = acts[0].startswith("hd_")
            if min(w, h) < (1080 if hd else 480):
                return "error_below_min_image_size"
            if body.get("format", "zip") not in ("json", "zip"):
                return _bad("format must be json or zip")
        elif feature == "makeup_vto":
            effects = body.get("effects")
            if not isinstance(effects, list) or not effects:
                return _bad("effects is required")
            for e in effects:
                cat = e.get("category")
                if cat not in MAKEUP_CATEGORIES:
                    return _bad(f"unknown makeup category {cat}")
                labels = PATTERNS.get(cat)
                name = (e.get("pattern") or {}).get("name") if cat != "lip_color" else (e.get("shape") or {}).get("name")
                if labels is not None and cat != "eyebrows" and name not in labels:
                    return _bad(f"{cat} pattern {name!r} is not in the catalog", "InvalidStyle")
                if cat == "eyebrows" and (e.get("pattern") or {}).get("type", "shape") == "shape" and name not in labels:
                    return _bad(f"eyebrows pattern {name!r} is not in the catalog", "InvalidStyle")
                need = labels.get(name) if labels else None
                if need and len(e.get("palettes") or []) < need:
                    return _bad(f"{cat} pattern {name} needs {need} palettes")
                for p in e.get("palettes") or []:
                    if "color" in p and not HEX.match(p["color"]):
                        return _bad(f"bad colour {p['color']}")
            if w >= 1920 or h >= 1920:
                return "error_exceed_max_image_size"
        elif feature == "hair_color":
            preset, pal, pat = body.get("preset"), body.get("palettes"), body.get("pattern")
            if not preset and not (pat and pal):
                return _bad("preset, or pattern + palettes, is required")
            if preset and preset not in HAIR_PRESETS:
                return _bad(f"unknown preset {preset}")
            for p in pal or []:
                if not HEX.match(p.get("color", "")):
                    return _bad("palette colour must be #RRGGBB")
            if pat and pat.get("name") not in ("full", "ombre"):
                return _bad("pattern.name must be full or ombre")
        elif feature == "beard_style":
            if body.get("template_id") not in {t["id"] for t in self._templates("beard_style")}:
                return _bad("Invalid style id", "InvalidStyle")
            if max(w, h) >= 1024:
                return "error_exceed_max_image_size"
        elif feature in ("earring", "necklace"):
            if not body.get("ref_file_ids") and not body.get("ref_file_urls"):
                return _bad("ref_file_ids or ref_file_urls is required")
            if not (body.get("source_info") or {}).get("name"):
                return _bad("source_info.name is required")
            if not body.get("object_infos"):
                return _bad("object_infos is required")
            for fid in body.get("ref_file_ids", []):
                if self._file(fid) is None:
                    return _json(404, {"status": 404, "error": "reference not uploaded", "error_code": "NotFound"})
        elif feature == "skin_simulation":
            vals = {k: body.get(k, 0) for k in ("wrinkle", "radiance", "oiliness", "acne", "eye_bags", "dark_circle",
                                                 "spots", "pores", "texture", "redness")}
            if all(float(v or 0) == 0 for v in vals.values()):
                return _bad("Simulation intensity cannot be all zero.")
            if any(not 0 <= float(v or 0) <= 1 for v in vals.values()):
                return _bad("intensities must be between 0 and 1")
            if min(w, h) < 480:
                return "error_below_min_image_size"
        return None

    # ----------------------------------------------------------------- utilities
    def _templates(self, feature: str) -> list[dict]:
        return [{k: v for k, v in t.items() if k != "style"} | {"thumb": f"/static/img/beard/{t['style']}.svg"}
                for t in DEFAULT_TEMPLATES.get(feature, [])]

    @staticmethod
    def _skus() -> list[dict]:
        base = "https://yce-api-01.makeupar.com"
        rows = [("AI Skin Analysis for SD 1~4 concerns", 9), ("AI Skin Analysis for SD 5~8 concerns", 12),
                ("AI Skin Analysis for SD 9~12 concerns", 14), ("AI Skin Analysis for SD 13~16 concerns", 16)]
        out = [{"description": d, "amount": a, "unit": "result_image", "proc_unit": 1,
                "run_task_url": base + FEATURES["skin_analysis"].run_path} for d, a in rows]
        for k in ("makeup_vto", "hair_color", "earring", "necklace"):
            out.append({"description": FEATURES[k].title, "amount": 1, "unit": "result_image", "proc_unit": 1,
                        "run_task_url": base + FEATURES[k].run_path})
        out.append({"description": FEATURES["beard_style"].title, "amount": 2, "unit": "result_image",
                    "proc_unit": 1, "run_task_url": base + FEATURES["beard_style"].run_path})
        out.append({"description": "AI Skin Simulation 1~4 concerns", "amount": 4, "unit": "result_image",
                    "proc_unit": 1, "run_task_url": base + FEATURES["skin_simulation"].run_path})
        return out


def mock_transport(mock: MockYouCam) -> httpx.MockTransport:
    async def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and "/task/" in request.url.path:
            # the success poll renders images: keep the event loop responsive
            return await asyncio.to_thread(mock.handler, request)
        return mock.handler(request)
    return httpx.MockTransport(handle)
