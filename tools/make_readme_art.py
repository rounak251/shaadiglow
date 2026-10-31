"""Build README art from the screenshots and the demo video.

    .venv/bin/python tools/make_readme_art.py
writes docs/img/hero.png (three phone screens) and docs/img/demo.gif (short silent loop from demo/demo.mp4).
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "screenshots"
OUT = ROOT / "docs" / "img"


def rounded(img: Image.Image, r: int) -> Image.Image:
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=r, fill=255)
    out = img.convert("RGBA")
    out.putalpha(m)
    return out


def hero() -> None:
    names = ["02-skin-report.png", "04-countdown-plan.png", "05-look-studio.png"]
    shots = [Image.open(SHOTS / n).convert("RGB") for n in names]
    h = 900
    shots = [s.resize((round(s.width * h / s.height), h), Image.LANCZOS) for s in shots]
    gap, pad = 48, 70
    W = sum(s.width for s in shots) + gap * (len(shots) - 1) + 2 * pad
    H = h + 2 * pad
    bg = Image.new("RGB", (W, H), (251, 246, 240))
    grad = Image.new("RGB", (W, H))
    px = grad.load()
    for y in range(H):
        for x in range(0, W, 2):
            t = (x / W) * 0.6 + (y / H) * 0.4
            c = tuple(int(a + (b - a) * t) for a, b in zip((122, 18, 48), (194, 65, 12)))
            px[x, y] = c
            if x + 1 < W:
                px[x + 1, y] = c
    bg = Image.blend(bg, grad, 0.92)
    canvas = bg.convert("RGBA")
    x = pad
    for s in shots:
        r = rounded(s, 46)
        shadow = Image.new("RGBA", (r.width + 80, r.height + 80), (0, 0, 0, 0))
        sm = Image.new("L", r.size, 0)
        ImageDraw.Draw(sm).rounded_rectangle([0, 0, r.width - 1, r.height - 1], radius=46, fill=150)
        shadow.paste((20, 5, 10, 255), (40, 52), sm)
        shadow = shadow.filter(ImageFilter.GaussianBlur(22))
        canvas.alpha_composite(shadow, (x - 40, pad - 40))
        canvas.alpha_composite(r, (x, pad))
        x += s.width + gap
    OUT.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(OUT / "hero.png", optimize=True)
    print("hero.png", canvas.size)


def gif() -> None:
    video = ROOT / "demo" / "demo.mp4"
    if not video.exists():
        print("no demo/demo.mp4 yet")
        return
    with tempfile.TemporaryDirectory() as td:
        pal = Path(td) / "pal.png"
        # 12 s of the look studio + shop, cropped to the phone, 12 fps
        vf = "crop=470:980:192:50,fps=12,scale=300:-1:flags=lanczos"
        start = "88"
        scenes = ROOT / "demo" / "scenes.json"
        if scenes.exists():
            import json
            for sc in json.loads(scenes.read_text()):
                if "Look studio" in sc["step"]:
                    start = f"{sc['start'] + 1.0:.2f}"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", start, "-t", "12", "-i", str(video), "-vf",
                        f"{vf},palettegen=max_colors=160", str(pal)], check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", start, "-t", "12", "-i", str(video), "-i", str(pal),
                        "-lavfi", f"{vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4", str(OUT / "demo.gif")],
                       check=True)
    print("demo.gif", (OUT / "demo.gif").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    hero()
    gif()
