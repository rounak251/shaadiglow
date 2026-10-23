"""Playwright smoke test: the main shopper journey on a phone viewport, in mock mode.

Starts the real server (uvicorn) on a free port with no YouCam key, then drives
Chromium: sample bride -> wedding details -> AI scan -> report + skin mask ->
wedding-day goal -> countdown plan -> look studio try-on -> shop the look -> progress.
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

pw = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[2]


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    port = free_port()
    env = {k: v for k, v in os.environ.items() if k not in ("YOUCAM_API_KEY", "SG_MODE")}
    env.update(SG_DATA_DIR=str(tmp_path_factory.mktemp("e2e")), SG_MOCK_LATENCY="0.05",
               SG_CACHE_SEED_DIRS=str(tmp_path_factory.mktemp("seed")))
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(base + "/api/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield base
    proc.terminate()
    proc.wait(timeout=10)


def test_main_flow_on_a_phone(server):
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chromium not installed for Playwright: {e}")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                                  has_touch=True)
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(server + "/")
        page.wait_for_selector(".persona")
        assert "Wedding-ready skin" in page.inner_text("h1")
        page.click('.persona[data-id="ananya"]')
        page.wait_for_selector("#wdate")
        page.select_option("#city", "delhi")
        page.click('[data-act="tier"][data-tier="essential"]')
        page.click('[data-act="setup-next"]')
        page.wait_for_selector(".summary", timeout=30000)
        assert page.locator(".ring .val b").inner_text().isdigit()
        assert "AI Skin Analysis" in page.inner_text(".apitag")
        page.click('[data-act="mask"][data-id="oiliness"]')
        page.wait_for_function("document.querySelector('#mask').style.opacity > 0")
        page.click('[data-act="goal"]')
        page.wait_for_selector("#goalbody img.after", timeout=30000)
        page.click('[data-act="nav"][data-to="plan"]')
        page.wait_for_selector(".countdown")
        assert page.inner_text(".countdown .big").startswith("D-")
        assert page.locator(".routine-step").count() >= 3
        page.click(".routine-step .check")
        page.wait_for_selector(".routine-step .check.on")
        page.click('.nav a[href="#/looks"]')
        page.wait_for_selector(".lookcard")
        page.click('.lookcard[data-id="pheras_red"]')
        page.wait_for_selector("#viewer img.after", timeout=30000)
        assert "Makeup Virtual Try-On" in page.inner_text("#viewer + .apitag, .apitag")
        page.click('[data-act="add-many"]')
        page.click('.nav a[href="#/plan"]')
        page.wait_for_selector('[data-act="shop-routine"]')
        page.click('[data-act="shop-routine"]')
        page.wait_for_selector(".totals")
        assert "₹" in page.inner_text(".totals")
        assert page.locator(".product").count() >= 6
        page.click('.nav a[href="#/progress"]')
        page.click('[data-act="demo-progress"]')
        page.wait_for_selector(".pair", timeout=30000)
        assert page.locator(".delta").count() == 4
        page.click('[data-act="lang"]')
        page.wait_for_selector(".nav")
        assert "प्रगति" in page.inner_text(".nav")
        assert not errors, errors
        browser.close()
