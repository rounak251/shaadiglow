#!/usr/bin/env python3
"""Re-shoot the Devpost screenshots on a phone viewport (390x844 @2x).

    python scripts/make_screenshots.py                 # demo mode (no key)
    YOUCAM_API_KEY=... python scripts/make_screenshots.py   # live mode; sample flows hit cache_seed (0 units)

Starts its own server on a free port with a throwaway data folder, walks the
bride journey (plus groom/guest extras) and writes PNGs to screenshots/ and docs/img/.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "screenshots"
EXTRA = ROOT / "docs" / "img"


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start_server() -> tuple[subprocess.Popen, str]:
    port = free_port()
    env = dict(os.environ, SG_DATA_DIR=tempfile.mkdtemp(prefix="sg_shots_"), SG_MOCK_LATENCY="0.2")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=ROOT,
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(150):
        try:
            if httpx.get(base + "/api/health", timeout=1).status_code == 200:
                return proc, base
        except httpx.HTTPError:
            time.sleep(0.1)
    proc.kill()
    raise SystemExit("server did not start")


def settle(page, ms=700):
    page.wait_for_timeout(ms)


def scroll_to(page, selector, offset=-70):
    page.evaluate(f"""(() => {{ const el = document.querySelector('{selector}');
        window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY + ({offset})); }})()""")
    settle(page, 500)


def main():
    SHOTS.mkdir(exist_ok=True)
    EXTRA.mkdir(parents=True, exist_ok=True)
    proc, base = start_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                                      has_touch=True)
            page = ctx.new_page()
            page.goto(base + "/")
            page.wait_for_selector(".persona")
            settle(page)
            page.screenshot(path=SHOTS / "01-welcome.png")

            page.click('.persona[data-id="ananya"]')
            page.wait_for_selector("#wdate")
            settle(page)
            page.screenshot(path=EXTRA / "setup.png")
            page.click('[data-act="setup-next"]')
            page.wait_for_selector(".scanner")
            page.wait_for_timeout(900)
            page.screenshot(path=EXTRA / "scanning.png")
            page.wait_for_selector(".summary", timeout=60000)
            settle(page)
            page.click('[data-act="mask"][data-id="oiliness"]')
            settle(page, 900)
            scroll_to(page, "#photo", -96)
            page.screenshot(path=SHOTS / "02-skin-report.png")

            page.click('[data-act="goal"]')
            page.wait_for_selector("#goalbody img.after", timeout=60000)
            settle(page)
            page.evaluate("document.querySelector('#goalbody [data-compare]').style.setProperty('--split','46%')")
            scroll_to(page, "#goal", -64)
            page.screenshot(path=SHOTS / "03-wedding-day-goal.png")

            page.click('[data-act="nav"][data-to="plan"]')
            page.wait_for_selector(".countdown")
            settle(page)
            page.screenshot(path=SHOTS / "04-countdown-plan.png")
            scroll_to(page, ".screen .seg", -64)
            page.locator('[data-act="why"]').first.click()
            settle(page, 400)
            page.screenshot(path=EXTRA / "plan-why.png")

            page.click('.nav a[href="#/looks"]')
            page.wait_for_selector(".lookcard")
            page.click('.lookcard[data-id="pheras_red"]')
            page.wait_for_selector("#viewer img.after", timeout=60000)
            settle(page)
            page.evaluate("document.querySelector('#viewer [data-compare]').style.setProperty('--split','42%')")
            settle(page, 300)
            page.screenshot(path=SHOTS / "05-look-studio.png")
            page.click('[data-act="add-many"]')
            page.click('[data-act="ltab"][data-tab="jewel"]')
            page.click('[data-act="tryprod"][data-id="jhumka_gold"]')
            page.wait_for_selector("#viewer img.after", timeout=60000)
            page.wait_for_selector(".toast", state="detached", timeout=10000)
            settle(page)
            page.screenshot(path=EXTRA / "jewellery.png")
            page.click('[data-act="add"][data-id="jhumka_gold"]')

            page.click('.nav a[href="#/plan"]')
            page.wait_for_selector('[data-act="shop-routine"]')
            page.click('[data-act="shop-routine"]')
            page.wait_for_selector(".totals")
            page.wait_for_timeout(2800)          # let the toast fade
            page.screenshot(path=SHOTS / "06-shop-the-look.png")

            page.click('.nav a[href="#/progress"]')
            page.click('[data-act="demo-progress"]')
            page.wait_for_selector(".pair", timeout=60000)
            settle(page)
            scroll_to(page, ".pair", -110)
            page.screenshot(path=EXTRA / "progress.png")

            page.click('[data-act="lang"]')
            page.goto(base + "/#/plan")
            page.wait_for_selector(".countdown")
            settle(page)
            page.screenshot(path=EXTRA / "plan-hindi.png")
            page.click('[data-act="lang"]')

            page.goto(base + "/#/")
            page.wait_for_selector(".persona")
            page.click('.persona[data-id="arjun"]')
            page.wait_for_selector("#wdate")
            page.click('[data-act="setup-next"]')
            page.wait_for_selector(".summary", timeout=60000)
            page.goto(base + "/#/looks")
            page.wait_for_selector(".seg")
            page.click('[data-act="ltab"][data-tab="beard"]')
            page.click('.tile[data-act="beard"]')
            page.wait_for_selector("#viewer img.after", timeout=60000)
            settle(page)
            page.screenshot(path=EXTRA / "groom-beard.png")
            browser.close()
    finally:
        proc.terminate()
    print("wrote", sorted(x.name for x in SHOTS.glob("*.png")), sorted(x.name for x in EXTRA.glob("*.png")))


if __name__ == "__main__":
    main()
