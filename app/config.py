"""Runtime settings, all from environment variables (12-factor; nothing secret in the repo).

    YOUCAM_API_KEY      enables live mode (never commit it; set it as a secret on Render)
    YOUCAM_REGION       india (default, console yce.makeupar.com) | global (yce.perfectcorp.com)
    YOUCAM_BASE_URL     overrides the API host chosen by the region
    SG_MODE             auto (default: live if a key is set) | mock | live
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REGION_HOSTS = {
    # Both hosts are taken from the official docs / consoles; India is the documented default.
    "india": "https://yce-api-01.makeupar.com",
    "global": "https://yce-api-01.perfectcorp.com",
}


@dataclass
class Settings:
    api_key: str = ""
    region: str = "india"
    base_url: str = REGION_HOSTS["india"]
    mode: str = "mock"                      # resolved: "mock" or "live"
    data_dir: Path = ROOT / "data"
    seed_dirs: list[Path] = field(default_factory=lambda: [ROOT / "cache_seed"])
    unit_budget: int = 1000
    reserve_units: int = 60
    client_daily_units: int = 80
    allow_live_uploads: bool = True
    poll_interval: float = 1.5
    mock_latency: float = 0.5
    max_upload_mb: int = 8

    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    def public(self) -> dict:
        return {"mode": self.mode, "region": self.region, "api_host": self.base_url.split("//")[-1],
                "allow_live_uploads": self.allow_live_uploads}


def load_settings(env: dict | None = None) -> Settings:
    e = env if env is not None else os.environ
    key = (e.get("YOUCAM_API_KEY") or "").strip()
    region = (e.get("YOUCAM_REGION") or "india").strip().lower()
    if region not in REGION_HOSTS:
        region = "india"
    base = (e.get("YOUCAM_BASE_URL") or REGION_HOSTS[region]).strip().rstrip("/")
    want = (e.get("SG_MODE") or "auto").strip().lower()
    if want == "live" and not key:
        raise RuntimeError("SG_MODE=live needs YOUCAM_API_KEY")
    mode = "live" if (want == "live" or (want == "auto" and key)) else "mock"
    data_dir = Path(e.get("SG_DATA_DIR") or (ROOT / "data"))
    seeds = [Path(p) for p in (e.get("SG_CACHE_SEED_DIRS") or str(ROOT / "cache_seed")).split(os.pathsep) if p]
    g = lambda n, d: (e.get(n) if e.get(n) not in (None, "") else d)
    s = Settings(api_key=key, region=region, base_url=base, mode=mode, data_dir=data_dir, seed_dirs=seeds)
    try:
        s.unit_budget = int(g("SG_UNIT_BUDGET", 1000))
        s.reserve_units = int(g("SG_RESERVE_UNITS", 60))
        s.client_daily_units = int(g("SG_CLIENT_DAILY_UNITS", 80))
        s.poll_interval = float(g("SG_POLL_INTERVAL", 1.5))
        s.mock_latency = float(g("SG_MOCK_LATENCY", 0.5))
        s.max_upload_mb = int(g("SG_MAX_UPLOAD_MB", 8))
    except ValueError:
        pass
    s.allow_live_uploads = str(g("SG_ALLOW_LIVE_UPLOADS", "true")).lower() in ("1", "true", "yes", "on")
    return s
