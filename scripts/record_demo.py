#!/usr/bin/env python3
"""Record the narrated demo video (1920x1080 MP4) of the real app on a phone viewport.

    python scripts/record_demo.py                       # demo mode, writes demo/demo.mp4
    YOUCAM_API_KEY=... python scripts/record_demo.py    # live mode (pre-warm first: 0 units for samples)
    python scripts/record_demo.py --voice Rishi --rate 172

How it works: one continuous Chromium session (390x844 CSS px @2x, touch, mobile)
drives the app while Chrome's screencast streams frames; macOS `say` speaks each
scene and the actions are spread across its narration.  The phone recording is
composited onto a branded 1080p canvas with a caption panel naming the YouCam
API and unit cost of each step.  No music is used.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo"
W, H = 1920, 1080
PHONE_W, PHONE_H = 780, 1688          # 390x844 CSS px at 2x
SCREEN_H = 940                        # on-canvas phone screen height
SCREEN_W = round(SCREEN_H * PHONE_W / PHONE_H)

TAP_JS = """
(() => {
  const style = document.createElement('style');
  style.textContent = `.sg-tap{position:fixed;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;
    background:rgba(242,160,7,.35);border:2px solid rgba(242,160,7,.9);pointer-events:none;z-index:99999;
    animation:sgtap .55s ease-out forwards}@keyframes sgtap{from{transform:scale(.4);opacity:1}to{transform:scale(1.4);opacity:0}}`;
  document.addEventListener('DOMContentLoaded', () => document.head.appendChild(style));
  window.addEventListener('pointerdown', (e) => {
    const d = document.createElement('div'); d.className = 'sg-tap';
    d.style.left = e.clientX + 'px'; d.style.top = e.clientY + 'px';
    document.body.appendChild(d); setTimeout(() => d.remove(), 700);
  }, true);
})();
"""

# Each scene: caption panel + narration + actions (spread over the narration).
SCENES = [
    dict(step="ShaadiGlow", title="Wedding-ready skin, planned to the day",
         body="A mobile web app for India's wedding season: brides, grooms and guests.",
         apis=["Built on YouCam AI APIs"],
         say="Namaste! India hosts around forty-six lakh weddings in one six-week season. Brides, grooms and guests all want to glow, but most start skin prep too late and buy looks they have never tried. Meet ShaadiGlow.",
         actions=[("wait", 2500), ("scroll", 420), ("wait", 1500), ("scroll", -420)]),
    dict(step="1 · Start", title="Pick a sample bride, or take a guided selfie",
         body="Selfies use the YouCam JS Camera Kit: it checks light, angle and distance before capture.",
         apis=["YouCam JS Camera Kit", "Sample models: 0 units"],
         say="It's a mobile web app. I'll pick Ananya, a sample bride in Mumbai, eight weeks out. Real users can take a guided selfie with YouCam's JS Camera Kit.",
         actions=[("click", '.persona[data-id="ananya"]'), ("wait_for", "#wdate")]),
    dict(step="2 · Details", title="Date, city, budget and events",
         body="Wedding date, city climate, a prep budget and the functions she'll attend shape the plan.",
         apis=["Rules engine input"],
         say="She confirms her wedding date, city, budget, and the events she'll attend, from haldi to the reception.",
         actions=[("scroll", 300), ("wait", 900), ("scroll", 400), ("click", '[data-act="setup-next"]')]),
    dict(step="3 · Scan", title="AI Skin Analysis v2.1: 12 concerns",
         body="We request only the 12 concerns a 30-90 day routine can act on: the 14-unit tier, not 16.",
         apis=["File API (0 units)", "AI Skin Analysis · 14 units"],
         say="The photo goes through YouCam's File API, then AI Skin Analysis version two point one measures twelve concerns, chosen to fit the fourteen-unit tier.",
         actions=[("wait_for", ".summary"), ("wait", 600)]),
    dict(step="4 · Report", title="Scores, skin age and AI masks",
         body="T-zone vs cheeks skin type, a 1-100 score per concern and the AI's own masks.",
         apis=["AI Skin Analysis · masks", "enable_mask_overlay: false"],
         say="Her report shows a skin score, skin age, and T-zone versus cheek skin type. Tap a concern to see where the AI looked. Oil control and dark circles are her focus.",
         actions=[("click", '[data-act="mask"][data-id="oiliness"]'), ("wait", 1600),
                  ("click", '[data-act="mask"][data-id="dark_circle_v2"]'), ("wait", 1200), ("scroll", 520)]),
    dict(step="5 · Goal", title="AI Skin Simulation: her wedding-day goal",
         body="A realistic preview of her top concerns improved, labelled as a preview, not a promise.",
         apis=["AI Skin Simulation · 4 units"],
         say="AI Skin Simulation previews a realistic wedding-day goal, labelled as a preview, not a promise.",
         actions=[("scroll_to", "#goal"), ("click", '[data-act="goal"]'), ("wait_for", "#goalbody img.after"),
                  ("drag_compare", "#goalbody [data-compare]")]),
    dict(step="6 · Plan", title="A countdown plan you can audit",
         body="Scores → ingredients → AM/PM routine, tuned to Mumbai's humidity and UV, her budget and the "
              "days left. Every step has a 'why'.",
         apis=["Deterministic rules engine", "Calendar (.ics) export"],
         say="The countdown plan comes from a deterministic rules engine. Her scores map to ingredients and a morning and night routine, tuned to Mumbai's humidity and UV, her budget, and the days left. Every step has a why, and it enforces wedding rules: patch tests, nothing new in the final fourteen days, and natural henna only.",
         actions=[("click", '[data-act="nav"][data-to="plan"]'), ("wait_for", ".countdown"), ("wait", 1500),
                  ("scroll", 560), ("click_first", '[data-act="why"]'), ("wait", 1200), ("scroll", 700),
                  ("wait", 1200), ("scroll", 600)]),
    dict(step="7 · Look studio", title="One call = one complete event look",
         body="Lipstick, kohl, eyeshadow, blush, highlighter and a shade-matched foundation in one request.",
         apis=["AI Makeup Virtual Try-On · 1 unit"],
         say="In the look studio, each event is one AI Makeup Virtual Try-On request that stacks lipstick, kohl, eyeshadow, blush, highlighter and a shade-matched foundation. One unit, one complete pheras look.",
         actions=[("goto", "#/looks"), ("wait_for", ".lookcard"), ("click", '.lookcard[data-id="pheras_red"]'),
                  ("wait_for", "#viewer img.after"), ("drag_compare", "#viewer [data-compare]")]),
    dict(step="8 · Hair & jewellery", title="Hair colour, jhumkas and more",
         body="Try a shade before the salon and jewellery before buying. Grooms get beard styles.",
         apis=["AI Hair Color · 1 unit", "AI Earrings · 1 unit", "AI Necklace · 1 unit", "AI Beard Style · 2 units"],
         say="AI Hair Color tries a burgundy shade, and AI Earrings tries temple jhumkas. Necklaces use the AI Necklace try-on, and grooms get the AI Beard Style Generator.",
         actions=[("click", '[data-act="ltab"][data-tab="hair"]'), ("click", '[data-act="tryprod"][data-id="hair_burgundy"]'),
                  ("wait_for_new", "#viewer img.after"), ("click", '[data-act="ltab"][data-tab="jewel"]'),
                  ("click", '[data-act="tryprod"][data-id="jhumka_gold"]'), ("wait_for_new", "#viewer img.after"),
                  ("click", '[data-act="add"][data-id="jhumka_gold"]'), ("scroll", -2400)]),
    dict(step="9 · Shop", title="Shop the look: one cart",
         body="Routine, look and jewellery together, each item tagged with the concern it treats. Sample store.",
         apis=["Sample catalogue (fictional)"],
         say="Everything she tried lands in one cart, each item tagged with the concern it treats, in a clearly marked sample store.",
         actions=[("goto", "#/plan"), ("wait_for", '[data-act="shop-routine"]'), ("click", '[data-act="shop-routine"]'),
                  ("wait_for", ".totals"), ("wait", 1600), ("scroll", 500)]),
    dict(step="10 · Progress", title="Re-scans that respect noise",
         body="Every 14 days: only the 4 tracked concerns (9 units). Changes within ±3 points count as steady.",
         apis=["AI Skin Analysis · 9 units", "Task Delete API on 'delete my data'"],
         say="Every two weeks, a quick re-scan of four concerns costs nine units, and only changes beyond normal scan noise count as progress. Here's the sample groom's re-scan.",
         actions=[("goto", "#/progress"), ("click", '[data-act="demo-progress"]'), ("wait_for", ".pair"),
                  ("scroll_to", ".pair"), ("wait", 1500), ("scroll", 520)]),
    dict(step="Under the hood", title="Built to spend units once",
         body="FastAPI · disk cache keyed by image hash + params · unit budget guard · mock that speaks the "
              "documented contract · English & Hindi.",
         apis=["7 YouCam AI APIs", "Cache: repeat = 0 units"],
         say="Under the hood: FastAPI, a disk cache so no call is ever paid twice, a unit budget guard, and full Hindi support. ShaadiGlow: wedding-ready skin, planned to the day.",
         actions=[("click", '[data-act="lang"]'), ("goto", "#/plan"), ("wait_for", ".countdown"), ("wait", 2200),
                  ("click", '[data-act="about"]'), ("wait", 2500)]),
]


def run(cmd, **kw):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def narrate(tmp: Path, voice: str, rate: int) -> list[float]:
    durs = []
    for i, sc in enumerate(SCENES):
        aiff = tmp / f"n{i}.aiff"
        run(["say", "-v", voice, "-r", str(rate), "-o", str(aiff), sc["say"]])
        run(["ffmpeg", "-y", "-i", str(aiff), "-ar", "48000", "-ac", "2", str(tmp / f"n{i}.wav")])
        durs.append(duration(tmp / f"n{i}.wav"))
    return durs


def render_overlays(tmp: Path, p, app_base: str) -> None:
    """Background, phone bezel, rounded-screen mask and one caption panel per scene (HTML -> PNG)."""
    base = (f"<link rel='stylesheet' href='/static/fonts/fonts.css'><style>*{{margin:0;box-sizing:border-box}}"
            f"body{{width:{W}px;height:{H}px;font-family:'Plus Jakarta Sans';}}</style>")
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": W, "height": H})
    page.goto(app_base + "/api/health")          # same origin as the self-hosted fonts

    def shot(html: str, path: Path, **kw):
        page.set_content(html, wait_until="load")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(150)
        page.screenshot(path=str(path), **kw)

    px, py = 210, (H - SCREEN_H) // 2
    shot(base + f"""<body style="background:radial-gradient(circle at 15% 20%,#3b0d1c 0,#2a0a14 40%,#1d070e 100%);overflow:hidden">
      <div style="position:absolute;inset:0;background:radial-gradient(circle at 85% 85%,rgba(242,160,7,.18),transparent 45%)"></div>
      <svg style="position:absolute;right:-160px;top:-160px;opacity:.07" width="760" height="760" viewBox="0 0 200 200"><g fill="none" stroke="#fff" stroke-width="1.2">
      {''.join(f'<ellipse cx="100" cy="45" rx="14" ry="40" transform="rotate({i*22.5} 100 100)"/>' for i in range(16))}
      <circle cx="100" cy="100" r="30"/><circle cx="100" cy="100" r="88"/></g></svg>
      <div style="position:absolute;left:{px-18}px;top:{py-18}px;width:{SCREEN_W+36}px;height:{SCREEN_H+36}px;border-radius:64px;
        box-shadow:0 40px 90px rgba(0,0,0,.55),0 0 0 1px rgba(255,255,255,.08)"></div></body>""", tmp / "bg.png")
    shot(base + f"""<body style="background:transparent">
      <div style="position:absolute;left:{px-18}px;top:{py-18}px;width:{SCREEN_W+36}px;height:{SCREEN_H+36}px;border-radius:64px;
        border:18px solid #111;box-shadow:inset 0 0 0 2px #333"></div>
      <div style="position:absolute;left:{px+SCREEN_W//2-60}px;top:{py-6}px;width:120px;height:26px;border-radius:14px;background:#111"></div></body>""",
         tmp / "bezel.png", omit_background=True)
    shot(base + f"""<body style="background:#000"><div style="position:absolute;left:0;top:0;width:{SCREEN_W}px;height:{SCREEN_H}px;
      border-radius:46px;background:#fff"></div></body>""", tmp / "mask_full.png",
         clip={"x": 0, "y": 0, "width": SCREEN_W, "height": SCREEN_H})
    for i, sc in enumerate(SCENES):
        chips = "".join(f'<span style="display:inline-block;margin:0 10px 12px 0;padding:10px 18px;border-radius:99px;'
                        f'background:rgba(242,160,7,.16);border:1.5px solid rgba(242,160,7,.55);color:#FFD36B;'
                        f'font-weight:700;font-size:23px">{a}</span>' for a in sc["apis"])
        shot(base + f"""<body style="background:transparent">
          <div style="position:absolute;left:{px+SCREEN_W+120}px;top:250px;width:{W-(px+SCREEN_W+120)-110}px;color:#fff">
            <div style="font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#F2A007;font-size:22px">{sc['step']}</div>
            <div style="font-family:'Playfair Display';font-weight:700;font-size:58px;line-height:1.12;margin:14px 0 22px">{sc['title']}</div>
            <div style="font-size:27px;line-height:1.5;color:rgba(255,255,255,.82);margin-bottom:30px">{sc['body']}</div>
            <div>{chips}</div></div>
          <div style="position:absolute;left:{px+SCREEN_W+120}px;bottom:70px;color:rgba(255,255,255,.5);font-size:19px">
            ShaadiGlow · YouCam API Skin AI & eCommerce VTO Hackathon</div></body>""", tmp / f"panel{i}.png",
             omit_background=True)
    browser.close()


class Screencast:
    def __init__(self, page, tmp: Path):
        self.frames: list[tuple[float, Path]] = []
        self.tmp = tmp
        self.cdp = page.context.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self._on)

    def _on(self, ev):
        f = self.tmp / f"f{len(self.frames):06d}.jpg"
        f.write_bytes(base64.b64decode(ev["data"]))
        self.frames.append((time.monotonic(), f))
        try:
            self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
        except Exception:  # noqa: BLE001
            pass

    def start(self):
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": PHONE_W,
                                               "maxHeight": PHONE_H, "everyNthFrame": 1})

    def stop(self):
        self.cdp.send("Page.stopScreencast")


def act(page, a, base):
    kind, arg = a[0], a[1]
    if kind == "wait":
        page.wait_for_timeout(arg)
    elif kind == "click":
        page.wait_for_selector(arg, timeout=60000)
        page.click(arg)
    elif kind == "click_first":
        page.locator(arg).first.click()
    elif kind == "wait_for":
        page.wait_for_selector(arg, timeout=60000)
    elif kind == "wait_for_new":
        page.wait_for_function(f"""(() => {{ const i = document.querySelector('{arg}');
            return i && i.complete && !document.querySelector('#viewer .busy'); }})()""", timeout=60000)
    elif kind == "scroll":
        page.mouse.wheel(0, arg)
    elif kind == "scroll_to":
        page.evaluate(f"document.querySelector('{arg}').scrollIntoView({{behavior:'smooth',block:'start'}})")
    elif kind == "goto":
        page.evaluate(f"location.hash = '{arg}'")
    elif kind == "drag_compare":
        page.wait_for_selector(arg)
        box = page.locator(arg).bounding_box()
        y = box["y"] + box["height"] * 0.55
        page.mouse.move(box["x"] + box["width"] * 0.5, y)
        page.mouse.down()
        for k in range(18):
            page.mouse.move(box["x"] + box["width"] * (0.5 + 0.4 * (k / 17)), y)
            page.wait_for_timeout(30)
        for k in range(30):
            page.mouse.move(box["x"] + box["width"] * (0.9 - 0.7 * (k / 29)), y)
            page.wait_for_timeout(30)
        for k in range(12):
            page.mouse.move(box["x"] + box["width"] * (0.2 + 0.3 * (k / 11)), y)
            page.wait_for_timeout(30)
        page.mouse.up()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Tara")
    ap.add_argument("--rate", type=int, default=174)
    ap.add_argument("--out", default=str(OUT / "demo.mp4"))
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="sg_demo_"))
    durs = narrate(tmp, a.voice, a.rate)
    total = sum(d + 0.45 for d in durs)
    print(f"narration {total:.1f}s over {len(SCENES)} scenes")

    port = free_port()
    env = dict(os.environ, SG_DATA_DIR=str(tmp / "data"), SG_MOCK_LATENCY="0.35")
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=ROOT, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(150):
        try:
            if httpx.get(base + "/api/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    marks = []
    try:
        with sync_playwright() as p:
            render_overlays(tmp, p, base)
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                                      has_touch=True)
            ctx.add_init_script(TAP_JS)
            page = ctx.new_page()
            page.goto(base + "/")
            page.wait_for_selector(".persona")
            page.wait_for_timeout(800)
            cast = Screencast(page, tmp)
            cast.start()
            page.wait_for_timeout(300)
            t0 = time.monotonic()
            for i, sc in enumerate(SCENES):
                start = time.monotonic()
                marks.append(start - t0)
                acts = sc["actions"]
                budget = durs[i] + 0.45
                gap = max(0.25, min(1.0, (budget - 1.0) / (len(acts) + 1)))
                for x in acts:
                    page.wait_for_timeout(int(gap * 1000))
                    act(page, x, base)
                left = budget - (time.monotonic() - start)
                if left > 0:
                    page.wait_for_timeout(int(left * 1000))
            end = time.monotonic() - t0
            cast.stop()
            browser.close()
    finally:
        srv.terminate()

    # ---- phone video: hold each screencast frame until the next one (constant 30 fps)
    before = [f for t, f in cast.frames if t < t0]
    frames = [(0.0, before[-1] if before else cast.frames[0][1])] + [(t - t0, f) for t, f in cast.frames if t >= t0]
    lst = tmp / "frames.txt"
    with lst.open("w") as fh:
        for k, (t, f) in enumerate(frames):
            nxt = frames[k + 1][0] if k + 1 < len(frames) else end
            fh.write(f"file '{f}'\nduration {max(0.001, nxt - t):.4f}\n")
        fh.write(f"file '{frames[-1][1]}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf",
         f"scale={PHONE_W}:{PHONE_H}:flags=lanczos,fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "16",
         str(tmp / "phone.mp4")])
    # ---- narration track aligned to scene starts
    filt, ins = [], []
    for i in range(len(SCENES)):
        ins += ["-i", str(tmp / f"n{i}.wav")]
        ms = int(marks[i] * 1000) + 250
        filt.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
    filt.append("".join(f"[a{i}]" for i in range(len(SCENES))) + f"amix=inputs={len(SCENES)}:normalize=0[aout]")
    run(["ffmpeg", "-y", *ins, "-filter_complex", ";".join(filt), "-map", "[aout]", "-t", f"{end:.2f}",
         str(tmp / "voice.wav")])
    # ---- composite: per-scene background (bg + caption panel) + rounded phone screen + bezel
    from PIL import Image
    px, py = 210, (H - SCREEN_H) // 2
    bg = Image.open(tmp / "bg.png").convert("RGBA")
    blst = tmp / "base.txt"
    with blst.open("w") as fh:
        for i in range(len(SCENES)):
            frame = bg.copy()
            frame.alpha_composite(Image.open(tmp / f"panel{i}.png").convert("RGBA"))
            frame.convert("RGB").save(tmp / f"base{i}.png")
            a1 = marks[i + 1] if i + 1 < len(SCENES) else end
            fh.write(f"file '{tmp / f'base{i}.png'}'\nduration {max(0.04, a1 - marks[i]):.3f}\n")
        fh.write(f"file '{tmp / f'base{len(SCENES) - 1}.png'}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(blst), "-vf", "fps=30,format=yuv420p",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(tmp / "base.mp4")])
    fc = [f"[1:v]scale={SCREEN_W}:{SCREEN_H}:flags=lanczos,format=rgba[ph]",
          f"[2:v]format=gray,scale={SCREEN_W}:{SCREEN_H}[mk]",
          "[ph][mk]alphamerge[phr]",
          f"[0:v][phr]overlay={px}:{py}[v0]",
          "[v0][3:v]overlay=0:0[v1]",
          f"[v1]fade=t=in:st=0:d=0.6,fade=t=out:st={end - 0.8:.2f}:d=0.8,format=yuv420p[vout]"]
    OUT.mkdir(exist_ok=True)
    run(["ffmpeg", "-y", "-i", str(tmp / "base.mp4"), "-i", str(tmp / "phone.mp4"), "-loop", "1", "-i",
         str(tmp / "mask_full.png"), "-loop", "1", "-i", str(tmp / "bezel.png"), "-i", str(tmp / "voice.wav"),
         "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "4:a", "-c:v", "libx264", "-preset", "medium",
         "-crf", "20", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-t", f"{end:.2f}", "-movflags", "+faststart",
         a.out])
    (OUT / "scenes.json").write_text(json.dumps([{"start": round(m, 2), "step": s["step"], "title": s["title"],
                                                  "narration": s["say"]} for m, s in zip(marks, SCENES)], indent=1))
    print(f"wrote {a.out} ({duration(Path(a.out)):.1f}s)")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
