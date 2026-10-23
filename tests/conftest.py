import json
import os
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.youcam.client import YouCamClient  # noqa: E402
from app.youcam.mocktransport import MockYouCam, mock_transport  # noqa: E402

DOCS = ROOT / "fixtures" / "docs"


def docs_fixture(name: str) -> dict:
    return json.loads((DOCS / name).read_text())["body"]


async def _no_sleep(_):
    return None


@pytest.fixture
def mock_api():
    """A fresh documented-contract simulator plus a real YouCamClient wired to it."""
    mock = MockYouCam(latency_polls=1)
    http = httpx.AsyncClient(transport=mock_transport(mock))
    client = YouCamClient("test-key-123456", "https://yce-api-01.makeupar.com", http, poll_interval=0.0,
                          sleep=_no_sleep)
    yield mock, client
    import asyncio
    asyncio.run(http.aclose())


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """FastAPI TestClient in mock mode with an isolated data directory."""
    for k in ("YOUCAM_API_KEY", "SG_MODE", "YOUCAM_BASE_URL", "YOUCAM_REGION"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("SG_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SG_CACHE_SEED_DIRS", str(tmp_path / "seed"))
    monkeypatch.setenv("SG_MOCK_LATENCY", "0.01")
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def shape(obj):
    """Structural signature of a JSON value: dict keys and element types, not values."""
    if isinstance(obj, dict):
        return {k: shape(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [shape(obj[0])] if obj else []
    if isinstance(obj, bool):
        return "bool"
    if isinstance(obj, (int, float)):
        return "number"
    if obj is None:
        return "null"
    return "string"


def contains_shape(big, small) -> bool:
    """True if every key path in `small` exists in `big` with the same kind of value."""
    if isinstance(small, dict):
        return isinstance(big, dict) and all(k in big and contains_shape(big[k], v) for k, v in small.items())
    if isinstance(small, list):
        return isinstance(big, list) and (not small or (bool(big) and contains_shape(big[0], small[0])))
    return big == small


os.environ.setdefault("PYTHONHASHSEED", "0")
