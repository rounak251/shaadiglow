"""Disk cache: every YouCam call is keyed by sha256(image bytes) + feature + params.

A cache hit costs 0 units.  Result images are downloaded immediately (YouCam's
result URLs expire after 2 hours) and stored next to the JSON, so a cached result
keeps working forever.  `seed_dirs` are read-only caches shipped in the repo
(filled by `scripts/live_smoke.py --prewarm`), so a fresh deploy (Render's disk is
ephemeral) still serves the sample personas without spending units.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

SCHEMA_VERSION = 1
_SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class DiskCache:
    def __init__(self, root: Path, namespace: str, seed_dirs: list[Path] | None = None):
        self.root = Path(root)
        self.ns = namespace
        self.seed_dirs = [Path(p) for p in (seed_dirs or [])]
        (self.root / self.ns).mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(feature: str, image_sha: str, params: dict) -> str:
        return sha256(canonical({"v": SCHEMA_VERSION, "f": feature, "img": image_sha, "p": params}).encode())

    def _dir(self, base: Path, key: str) -> Path:
        return base / self.ns / key[:2] / key

    def _find(self, key: str) -> Path | None:
        for base in [self.root, *self.seed_dirs]:
            d = self._dir(base, key)
            if (d / "result.json").exists():
                return d
        return None

    def get(self, key: str) -> dict | None:
        d = self._find(key)
        if not d:
            self.misses += 1
            return None
        self.hits += 1
        rec = json.loads((d / "result.json").read_text())
        rec["cached"] = True
        return rec

    def put(self, key: str, record: dict, files: dict[str, bytes] | None = None) -> dict:
        d = self._dir(self.root, key)
        d.mkdir(parents=True, exist_ok=True)
        for name, data in (files or {}).items():
            if not _SAFE.match(name):
                raise ValueError(f"unsafe file name {name!r}")
            (d / name).write_bytes(data)
        record = {**record, "cache_key": key, "stored_at": int(time.time())}
        tmp = d / "result.json.tmp"
        tmp.write_text(json.dumps(record, indent=1))
        os.replace(tmp, d / "result.json")
        record["cached"] = False
        return record

    def media_url(self, key: str, name: str) -> str:
        return f"/media/{self.ns}/{key}/{name}"

    def media_path(self, ns: str, key: str, name: str) -> Path | None:
        if ns != self.ns or not _SAFE.match(key) or not _SAFE.match(name):
            return None
        for base in [self.root, *self.seed_dirs]:
            p = base / ns / key[:2] / key / name
            if p.exists():
                return p
        return None

    def stats(self) -> dict:
        n = sum(1 for _ in (self.root / self.ns).glob("*/*/result.json"))
        seeded = sum(1 for b in self.seed_dirs for _ in (b / self.ns).glob("*/*/result.json"))
        return {"namespace": self.ns, "entries": n, "seed_entries": seeded, "hits": self.hits, "misses": self.misses}
