"""Tiny JSON-file persistence for uploads and anonymous profiles (no accounts, no PII).

A profile is a random id generated in the browser.  It holds scan results and the
YouCam task ids, so "Delete my data" can also delete the tasks and files on
YouCam's side through the Task Management API.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
from pathlib import Path

from .youcam.cache import sha256

PROFILE_RE = re.compile(r"^[a-zA-Z0-9-]{8,64}$")
UPLOAD_RE = re.compile(r"^[a-f0-9]{24}$")


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)
        (self.root / "uploads").mkdir(parents=True, exist_ok=True)
        (self.root / "profiles").mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # ------------------------------------------------------------- uploads
    def save_upload(self, variants: dict[str, bytes], source: str) -> str:
        uid = sha256(variants["face"])[:24]
        d = self.root / "uploads" / uid
        d.mkdir(parents=True, exist_ok=True)
        for name, data in variants.items():
            (d / f"{name}.jpg").write_bytes(data)
        (d / "meta.json").write_text(json.dumps({"source": source, "created": int(time.time())}))
        return uid

    def upload_path(self, uid: str, variant: str) -> Path | None:
        if not UPLOAD_RE.match(uid) or variant not in ("face", "beard", "portrait"):
            return None
        p = self.root / "uploads" / uid / f"{variant}.jpg"
        return p if p.exists() else None

    def upload_meta(self, uid: str) -> dict:
        p = self.root / "uploads" / uid / "meta.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def delete_upload(self, uid: str) -> None:
        if UPLOAD_RE.match(uid):
            shutil.rmtree(self.root / "uploads" / uid, ignore_errors=True)

    # ------------------------------------------------------------- profiles
    def _ppath(self, pid: str) -> Path:
        if not PROFILE_RE.match(pid or ""):
            raise ValueError("bad profile id")
        return self.root / "profiles" / f"{pid}.json"

    def profile(self, pid: str) -> dict:
        p = self._ppath(pid)
        if p.exists():
            return json.loads(p.read_text())
        return {"id": pid, "created": int(time.time()), "scans": [], "tasks": [], "uploads": []}

    def save_profile(self, prof: dict) -> None:
        p = self._ppath(prof["id"])
        tmp = p.with_suffix(".tmp")
        with self._lock:
            tmp.write_text(json.dumps(prof))
            os.replace(tmp, p)

    def add_scan(self, pid: str, scan: dict) -> dict:
        prof = self.profile(pid)
        prof["scans"].append(scan)
        if scan.get("task_id") and scan["task_id"] not in prof["tasks"]:
            prof["tasks"].append(scan["task_id"])
        ref = scan.get("image_ref", "")
        if ref.startswith("upload:") and ref[7:] not in prof["uploads"]:
            prof["uploads"].append(ref[7:])
        self.save_profile(prof)
        return prof

    def add_task(self, pid: str | None, task_id: str | None, image_ref: str | None = None) -> None:
        if not pid or not task_id or not PROFILE_RE.match(pid):
            return
        prof = self.profile(pid)
        if task_id not in prof["tasks"]:
            prof["tasks"].append(task_id)
        if image_ref and image_ref.startswith("upload:") and image_ref[7:] not in prof["uploads"]:
            prof["uploads"].append(image_ref[7:])
        self.save_profile(prof)

    def delete_profile(self, pid: str) -> dict:
        prof = self.profile(pid)
        for uid in prof.get("uploads", []):
            self.delete_upload(uid)
        p = self._ppath(pid)
        if p.exists():
            p.unlink()
        return prof
