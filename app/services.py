"""Orchestration: cache -> budget guard -> File API upload -> AI task -> download -> cache.

Every YouCam feature in the app goes through `YouCamService.run`, so caching,
unit accounting and error handling are identical for all seven APIs.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import httpx

from . import flows
from .config import Settings
from .engine.concerns import normalise
from .mock.personas import variant_bytes
from .store import Store
from .youcam.cache import DiskCache, sha256
from .youcam.client import YouCamClient, result_urls
from .youcam.errors import BudgetExceeded
from .youcam.features import FEATURES, units_for
from .youcam.ledger import UnitLedger
from .youcam.mocktransport import MockYouCam, mock_transport

JEWEL_DIR = Path(__file__).resolve().parent / "static" / "jewellery"
FILE_ID_TTL = 7 * 86400          # docs: uploaded files live 30 days; re-upload weekly to be safe


class YouCamService:
    def __init__(self, settings: Settings):
        self.s = settings
        self.live = settings.is_live
        self.mock = None if self.live else MockYouCam(latency_polls=1)
        transport = None if self.live else mock_transport(self.mock)
        self.http = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(90.0, connect=20.0),
                                      follow_redirects=True)
        key = settings.api_key if self.live else "mock-key-not-a-secret"
        poll = settings.poll_interval if self.live else max(0.05, settings.mock_latency)
        self.client = YouCamClient(key, settings.base_url, self.http, poll_interval=poll)
        ns = "live" if self.live else "mock"
        self.cache = DiskCache(settings.data_dir / "cache", ns, settings.seed_dirs)
        daily = settings.client_daily_units if self.live else 10**9
        self.ledger = UnitLedger(settings.data_dir / "ledger.jsonl", mode=ns, budget=settings.unit_budget,
                                 reserve=settings.reserve_units if self.live else 0, per_client_daily=daily)
        self.store = Store(settings.data_dir)
        self._file_ids: dict[str, tuple[str, float]] = {}
        self._fid_path = settings.data_dir / "file_ids.json"
        if self.live and self._fid_path.exists():
            try:
                self._file_ids = {k: tuple(v) for k, v in json.loads(self._fid_path.read_text()).items()}
            except ValueError:
                self._file_ids = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._templates: dict[str, tuple[list, float]] = {}

    async def close(self):
        await self.http.aclose()

    # ------------------------------------------------------------------ images
    def image_bytes(self, image_ref: str, variant: str) -> bytes:
        if image_ref.startswith("persona:"):
            return variant_bytes(image_ref.split(":", 1)[1], variant)
        if image_ref.startswith("upload:"):
            p = self.store.upload_path(image_ref.split(":", 1)[1], variant)
            if p:
                return p.read_bytes()
        raise FileNotFoundError(image_ref)

    def image_url(self, image_ref: str, variant: str) -> str:
        if image_ref.startswith("persona:"):
            return f"/static/personas/{image_ref.split(':', 1)[1]}/{variant}.jpg"
        return f"/uploads/{image_ref.split(':', 1)[1]}/{variant}.jpg"

    async def _file_id(self, data: bytes, name: str) -> str:
        h = sha256(data)
        fid = self._file_ids.get(h)
        if fid and time.time() - fid[1] < FILE_ID_TTL:
            return fid[0]
        file_id = await self.client.upload(data, "image/jpeg", name)
        self._file_ids[h] = (file_id, time.time())
        if self.live:
            self._fid_path.write_text(json.dumps(self._file_ids))
        return file_id

    async def refresh_balance(self, max_age: float = 60.0) -> None:
        if self.live and time.time() - self.ledger.live_balance_at > max_age:
            try:
                self.ledger.set_live_balance(await self.client.credit())
            except Exception:   # noqa: BLE001 - balance is advisory; local ledger still guards
                pass

    # ------------------------------------------------------------------ core
    async def run(self, feature: str, image: bytes, params: dict, client_id: str,
                  refs: list[bytes] | None = None, ref_params: dict | None = None) -> dict:
        refs = refs or []
        key = self.cache.key(feature, sha256(image), {"params": params, "refs": [sha256(r) for r in refs],
                                                      "ref_params": ref_params or {}})
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:                   # two taps on the same button never pay twice
            hit = self.cache.get(key)
            if hit:
                return self._present(hit)
            units = units_for(feature, {**params, "object_infos": [{}] * max(1, len(refs))})
            await self.refresh_balance()
            self.ledger.authorize(units, client_id)
            t0 = time.monotonic()
            src_id = await self._file_id(image, "photo.jpg")
            payload = {"src_file_id": src_id, **params}
            if refs:
                ref_ids = [await self._file_id(r, f"product_{i}.jpg") for i, r in enumerate(refs)]
                payload.update({"ref_file_ids": ref_ids, "source_info": {"name": src_id},
                                "object_infos": [{"name": rid, "parameter": ref_params or {}} for rid in ref_ids]})
            res = await self.client.run(feature, payload)
            files: dict[str, bytes] = {}
            record = {"feature": feature, "api": FEATURES[feature].title, "task_id": res.task_id, "units": units,
                      "mode": "live" if self.live else "mock", "elapsed_s": round(time.monotonic() - t0, 2),
                      "polls": res.polls, "calls": res.calls, "request": _redact(payload)}
            if feature == "skin_analysis":
                record["results"] = await self._localise_skin(res.data.get("results", {}), files)
            else:
                urls = result_urls(res.data)
                if not urls:
                    raise RuntimeError(f"{feature} returned no result url")
                files["result.jpg"] = await self.client.download(urls[0])
                record["result"] = "result.jpg"
            self.ledger.record(feature, units, res.task_id, client_id)
            stored = self.cache.put(key, record, files)
            return self._present(stored)

    async def _localise_skin(self, results: dict, files: dict[str, bytes]) -> dict:
        """Download every mask now (URLs expire after 2 h) and point the JSON at local copies."""
        out = []
        sem = asyncio.Semaphore(6)

        async def grab(url: str, name: str):
            async with sem:
                files[name] = await self.client.download(url)

        jobs = []
        for i, o in enumerate(results.get("output", [])):
            o = dict(o)
            names = []
            for j, u in enumerate(o.get("mask_urls") or []):
                ext = ".png" if ".png" in u.split("?")[0].lower() else ".jpg"
                name = f"m{i}_{j}{ext}"
                jobs.append(grab(u, name))
                names.append(name)
            if names:
                o["mask_urls"] = names
            out.append(o)
        await asyncio.gather(*jobs)
        return {"output": out}

    def _present(self, rec: dict) -> dict:
        key = rec["cache_key"]
        out = {k: v for k, v in rec.items() if k not in ("request",)}
        out["request"] = rec.get("request")
        if rec.get("result"):
            out["url"] = self.cache.media_url(key, rec["result"])
        if rec.get("feature") == "skin_analysis":
            res = json.loads(json.dumps(rec["results"]))
            for o in res.get("output", []):
                if o.get("mask_urls"):
                    o["mask_urls"] = [self.cache.media_url(key, n) for n in o["mask_urls"]]
            out["scan"] = normalise(res)
        out["units_charged"] = 0 if rec.get("cached") else rec.get("units", 0)
        return out

    # ------------------------------------------------------------------ feature helpers
    async def skin_scan(self, image_ref: str, concerns: list[str], client_id: str, camera_kit: bool = False) -> dict:
        return await self.run("skin_analysis", self.image_bytes(image_ref, "face"),
                              flows.scan_params(concerns, camera_kit), client_id)

    async def templates(self, feature: str) -> list[dict]:
        cached = self._templates.get(feature)
        if cached and time.time() - cached[1] < 6 * 3600:
            return cached[0]
        tpl = await self.client.templates(feature)
        self._templates[feature] = (tpl, time.time())
        return tpl

    def jewellery_ref(self, ref_name: str) -> bytes:
        return (JEWEL_DIR / ref_name).read_bytes()

    async def delete_tasks(self, task_ids: list[str]) -> int:
        n = 0
        for t in task_ids:
            if await self.client.delete_task(t):
                n += 1
        return n

    def units(self) -> dict:
        return {**self.ledger.summary(), "cache": self.cache.stats()}


def _redact(payload: dict) -> dict:
    """What we sent, minus file ids (shown in the UI's 'API request' drawer)."""
    out = {}
    for k, v in payload.items():
        if k in ("src_file_id", "source_info"):
            out[k] = "<file_id>" if k == "src_file_id" else {"name": "<file_id>"}
        elif k == "ref_file_ids":
            out[k] = ["<file_id>"] * len(v)
        elif k == "object_infos":
            out[k] = [{**o, "name": "<file_id>"} for o in v]
        else:
            out[k] = v
    return out


__all__ = ["YouCamService", "BudgetExceeded"]
