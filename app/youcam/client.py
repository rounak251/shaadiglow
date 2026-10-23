"""Thin async client for the YouCam REST API (File API -> AI task -> poll -> download).

The same code path runs in mock mode: `app.youcam.mocktransport` plugs a
documented-contract simulator into httpx, so tests exercise the real client.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import httpx

from .errors import YouCamEngineError, YouCamError, YouCamTimeout
from .features import (CREDIT_PATH, FEATURE_COST_PATH, FEATURES, FILE_PATH, TASK_DELETE_PATH)


def _payload(body: Any) -> dict:
    """YouCam wraps results as {"status":200,"data":{...}} (sometimes "result")."""
    if not isinstance(body, dict):
        return {}
    for k in ("data", "result"):
        if isinstance(body.get(k), dict):
            return body[k]
    return body


@dataclass
class TaskResult:
    feature: str
    task_id: str
    data: dict
    elapsed_s: float
    polls: int
    calls: list[str] = field(default_factory=list)


class YouCamClient:
    def __init__(self, api_key: str, base_url: str, http: httpx.AsyncClient, *,
                 poll_interval: float = 1.5, max_poll_interval: float = 4.0, timeout_s: float = 180.0,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep, max_retries: int = 3):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.http = http
        self.poll_interval = poll_interval
        self.max_poll_interval = max_poll_interval
        self.timeout_s = timeout_s
        self.sleep = sleep
        self.max_retries = max_retries
        self.log: list[str] = []          # endpoint trace, shown in the UI "how it works" drawer

    # ---------------------------------------------------------------- plumbing
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def _request(self, method: str, path: str, **kw) -> dict:
        url = f"{self.base_url}{path}"
        delay = 1.0
        for attempt in range(self.max_retries + 1):
            r = await self.http.request(method, url, headers=self._headers(), **kw)
            self.log.append(f"{method} {path} -> {r.status_code}")
            if r.status_code == 429 and attempt < self.max_retries:
                await self.sleep(delay)
                delay *= 2
                continue
            if r.status_code >= 400:
                try:
                    body = r.json()
                except ValueError:
                    body = {}
                raise YouCamError(r.status_code, body.get("error_code"), body.get("error") or r.text[:200])
            try:
                return r.json()
            except ValueError:
                return {}
        raise YouCamError(429, "TooManyRequests", "rate limited")  # pragma: no cover

    # ---------------------------------------------------------------- File API
    async def upload(self, data: bytes, content_type: str = "image/jpeg", file_name: str = "photo.jpg") -> str:
        body = await self._request("POST", FILE_PATH, json={"files": [
            {"content_type": content_type, "file_name": file_name, "file_size": len(data)}]})
        files = _payload(body).get("files") or body.get("files") or []
        if not files:
            raise YouCamError(502, "BadFileResponse", "File API returned no files")
        f = files[0]
        req = (f.get("requests") or [{}])[0]
        headers = {k: str(v) for k, v in (req.get("headers") or {}).items()}
        headers.setdefault("Content-Type", content_type)
        # Pre-signed storage URL: no YouCam auth header here.
        put = await self.http.request(req.get("method", "PUT"), req["url"], headers=headers, content=data)
        self.log.append(f"PUT <pre-signed upload url> -> {put.status_code}")
        if put.status_code >= 300:
            raise YouCamError(put.status_code, "UploadFailed", "pre-signed upload was rejected")
        return f["file_id"]

    # ---------------------------------------------------------------- AI tasks
    async def run_task(self, feature: str, payload: dict) -> str:
        body = await self._request("POST", FEATURES[feature].run_path, json=payload)
        task_id = _payload(body).get("task_id")
        if not task_id:
            raise YouCamError(502, "NoTaskId", "run task returned no task_id")
        return task_id

    async def poll(self, feature: str, task_id: str) -> tuple[dict, int]:
        path = FEATURES[feature].poll_path.format(task_id=task_id)
        start, interval, polls = time.monotonic(), self.poll_interval, 0
        while True:
            body = await self._request("GET", path)
            polls += 1
            data = _payload(body)
            status = data.get("task_status") or data.get("status")
            if status == "success" or (status is None and ("results" in data or "url" in data)):
                return data, polls
            if status == "error":
                raise YouCamEngineError(data.get("error"), data.get("error_message"), task_id)
            if time.monotonic() - start > self.timeout_s:
                raise YouCamTimeout(f"{feature} task {task_id} still running after {self.timeout_s}s")
            await self.sleep(interval)
            interval = min(self.max_poll_interval, interval * 1.3)

    async def run(self, feature: str, payload: dict) -> TaskResult:
        t0 = time.monotonic()
        mark = len(self.log)
        task_id = await self.run_task(feature, payload)
        data, polls = await self.poll(feature, task_id)
        return TaskResult(feature, task_id, data, time.monotonic() - t0, polls, self.log[mark:])

    async def download(self, url: str) -> bytes:
        r = await self.http.get(url)   # result URLs are pre-signed, valid for 2 hours
        if r.status_code >= 400:
            raise YouCamError(r.status_code, "DownloadFailed", url[:80])
        return r.content

    # ---------------------------------------------------------------- utilities (0 units)
    async def templates(self, feature: str, max_pages: int = 5) -> list[dict]:
        path = FEATURES[feature].template_path
        if not path:
            return []
        out, token = [], None
        for _ in range(max_pages):
            params = {"page_size": 20}
            if token:
                params["starting_token"] = token
            data = _payload(await self._request("GET", path, params=params))
            out.extend(data.get("templates") or [])
            token = data.get("next_token")
            if not token:
                break
        return out

    async def credit(self) -> float:
        body = await self._request("GET", CREDIT_PATH)
        rows = body.get("results") or _payload(body).get("results") or []
        total = 0.0
        for row in rows:
            total += float(row.get("amount_dec", row.get("amount", 0)) or 0)
        return round(total, 2)

    async def feature_costs(self, max_pages: int = 10) -> list[dict]:
        out, token = [], None
        for _ in range(max_pages):
            params = {"page_size": 20}
            if token:
                params["starting_token"] = token
            data = _payload(await self._request("GET", FEATURE_COST_PATH, params=params))
            out.extend(data.get("skus") or [])
            token = data.get("next_token")
            if not token:
                break
        return out

    async def delete_task(self, task_id: str) -> bool:
        try:
            await self._request("POST", TASK_DELETE_PATH, json={"task_id": task_id})
            return True
        except YouCamError:
            return False


def result_urls(data: dict) -> list[str]:
    """Collect output image URLs across the documented response variants."""
    res = data.get("results", data)
    urls: list[str] = []
    if isinstance(res, str):
        return [res]
    if isinstance(res, dict):
        for k in ("url", "download_url"):
            if isinstance(res.get(k), str):
                urls.append(res[k])
        for k in ("urls", "output_urls"):
            if isinstance(res.get(k), list):
                urls += [u for u in res[k] if isinstance(u, str)]
    if isinstance(res, list):
        for item in res:
            if isinstance(item, dict):
                for k in ("url", "download_url"):
                    if isinstance(item.get(k), str):
                        urls.append(item[k])
    return urls
