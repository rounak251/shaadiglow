"""Draws the sample-catalogue jewellery (original artwork, MIT like the rest of the repo).

Each item is written twice into app/static/jewellery/:
    <id>.png      transparent PNG for the shop UI and the mock compositor
    <id>_ref.jpg  the same piece on pure white, used as the YouCam *reference* image
                  (the 2D jewellery VTO APIs remove plain backgrounds themselves)

Run:  .venv/bin/python tools/make_jewellery.py
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[1] / "app" / "static" / "jewellery"
SS = 4  # supersampling factor

GOLD = dict(hi=(255, 236, 170), mid=(214, 166, 58), lo=(128, 88, 22), line=(110, 74, 16))
SILVER = dict(hi=(250, 250, 252), mid=(190, 196, 205), lo=(110, 116, 126), line=(90, 95, 104))
ROSE = dict(hi=(255, 222, 205), mid=(214, 150, 128), lo=(130, 78, 64), line=(110, 62, 52))


class Canvas:
    def __init__(self, w: int, h: int):
        self.w, self.h = w * SS, h * SS
        self.img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))

    def metal_fill(self, mask: Image.Image, metal: dict, light=(0.35, 0.25), bands: int = 0):
        """Fill a mask with a brushed-metal gradient lit from the top-left (bbox-local for speed)."""
        bb = mask.getbbox()
        if not bb:
            return
        x0, y0, x1, y1 = bb
        m = np.asarray(mask.crop(bb)).astype(np.float32) / 255.0
        h, w = m.shape
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        u, v = xx / max(1, w), yy / max(1, h)
        t = np.clip(0.55 * v + 0.25 * u + 0.15 * np.sin(u * 9 + v * 4), 0, 1)
        if bands:
            t = np.clip(t + 0.18 * np.sign(np.sin(v * math.pi * bands)), 0, 1)
        hi, mid, lo = (np.array(metal[k], np.float32) for k in ("hi", "mid", "lo"))
        tt = t[..., None]
        col = np.where(tt < 0.5, hi * (1 - tt * 2) + mid * tt * 2, mid * (1 - (tt - 0.5) * 2) + lo * (tt - 0.5) * 2)
        spec = np.exp(-(((u - light[0]) / 0.18) ** 2 + ((v - light[1]) / 0.12) ** 2))
        col = np.clip(col + spec[..., None] * 90, 0, 255)
        layer = np.zeros((h, w, 4), np.uint8)
        layer[..., :3] = col.astype(np.uint8)
        layer[..., 3] = (m * 255).astype(np.uint8)
        self.img.alpha_composite(Image.fromarray(layer, "RGBA"), (x0, y0))

    def shape(self, draw_fn, metal: dict, outline: bool = True, bands: int = 0):
        mask = Image.new("L", (self.w, self.h), 0)
        draw_fn(ImageDraw.Draw(mask))
        self.metal_fill(mask, metal, bands=bands)
        bb = mask.getbbox()
        if outline and bb:
            pad = 4
            bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(self.w, bb[2] + pad), min(self.h, bb[3] + pad))
            edge = mask.crop(bb).filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
            layer = Image.new("RGBA", edge.size, metal["line"] + (0,))
            layer.putalpha(edge.point(lambda v: int(v * 0.7)))
            self.img.alpha_composite(layer, (bb[0], bb[1]))

    def gem(self, cx, cy, r, color, facet=True):
        cx, cy, r = cx * SS, cy * SS, r * SS
        x0, y0 = int(max(0, cx - r - 2)), int(max(0, cy - r - 2))
        x1, y1 = int(min(self.w, cx + r + 3)), int(min(self.h, cy + r + 3))
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        inside = d <= 1
        base = np.array(color, np.float32)
        shade = np.clip(1.15 - 0.55 * d, 0.45, 1.2)[..., None]
        col = np.clip(base * shade, 0, 255)
        if facet:
            ang = np.arctan2(yy - cy, xx - cx)
            col = np.clip(col * (1 + 0.12 * np.sign(np.sin(ang * 4)))[..., None], 0, 255)
        hl = np.exp(-(((xx - (cx - r * 0.35)) / (r * 0.28)) ** 2 + ((yy - (cy - r * 0.38)) / (r * 0.2)) ** 2))
        col = np.clip(col + hl[..., None] * 200, 0, 255)
        layer = np.zeros(xx.shape + (4,), np.uint8)
        layer[..., :3] = col.astype(np.uint8)
        alpha = np.clip((1 - d) * r / 1.5, 0, 1) * 255
        layer[..., 3] = np.where(inside, alpha, 0).astype(np.uint8)
        self.img.alpha_composite(Image.fromarray(layer, "RGBA"), (x0, y0))

    def pearl(self, cx, cy, r):
        self.gem(cx, cy, r, (246, 238, 228), facet=False)

    def bead(self, cx, cy, r, metal):
        self.shape(lambda d: d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=255),
                   metal, outline=False)

    def line(self, pts, width, metal):
        self.shape(lambda d: d.line([(x * SS, y * SS) for x, y in pts], fill=255, width=int(width * SS),
                                    joint="curve"), metal, outline=False)

    def final(self, w, h) -> Image.Image:
        img = self.img.resize((w, h), Image.LANCZOS)
        bb = img.getbbox()
        return img.crop(bb) if bb else img


# ------------------------------------------------------------------ earrings (one piece)
def jhumka(metal=GOLD, stone=(178, 18, 46), pearls=True) -> Image.Image:
    W, H = 300, 520
    c = Canvas(W, H)
    cx = W / 2
    c.shape(lambda d: d.ellipse([(cx - 40) * SS, 18 * SS, (cx + 40) * SS, 98 * SS], fill=255), metal)
    c.gem(cx, 58, 24, stone)
    for i in range(6):
        a = i * math.pi / 3
        c.bead(cx + 33 * math.cos(a), 58 + 33 * math.sin(a), 6, metal)
    for y in (110, 128, 146):
        c.bead(cx, y, 8, metal)
    c.shape(lambda d: d.chord([(cx - 46) * SS, 140 * SS, (cx + 46) * SS, 210 * SS], 180, 360, fill=255), metal)

    def bell_mirror(d):
        right = []
        for i in range(41):
            t = i / 40
            w = 46 + 92 * math.sin(t * math.pi / 2) ** 1.4
            right.append((cx + w, 175 + 225 * t))
        left = [(2 * cx - x, y) for x, y in reversed(right)]
        d.polygon([(x * SS, y * SS) for x, y in right + left], fill=255)

    c.shape(bell_mirror, metal, bands=7)
    for k in range(5):  # granulation rows
        y = 210 + k * 38
        t = (y - 175) / 225
        w = 46 + 92 * math.sin(t * math.pi / 2) ** 1.4
        n = 5 + k * 2
        for j in range(n):
            x = cx - w * 0.85 + (2 * w * 0.85) * j / max(1, n - 1)
            c.bead(x, y, 3.2, metal)
    for j in range(13):  # rim balls
        x = cx - 138 + 276 * j / 12
        c.bead(x, 402, 7, metal)
    if pearls:
        for j in range(9):
            x = cx - 124 + 248 * j / 8
            c.line([(x, 408), (x, 440)], 2.5, metal)
            c.pearl(x, 452, 11)
    return c.final(W, H)


def chandbali(metal=GOLD, stones=((14, 122, 74), (178, 18, 46))) -> Image.Image:
    W, H = 340, 460
    c = Canvas(W, H)
    cx = W / 2
    c.shape(lambda d: d.ellipse([(cx - 30) * SS, 10 * SS, (cx + 30) * SS, 70 * SS], fill=255), metal)
    c.gem(cx, 40, 18, (244, 241, 232))
    for y in (82, 98):
        c.bead(cx, y, 7, metal)

    def crescent(d):
        d.ellipse([(cx - 150) * SS, 90 * SS, (cx + 150) * SS, 390 * SS], fill=255)
        d.ellipse([(cx - 120) * SS, 40 * SS, (cx + 120) * SS, 280 * SS], fill=0)

    c.shape(crescent, metal, bands=0)
    for j in range(9):
        a = math.pi * (0.12 + 0.76 * j / 8)
        x, y = cx + 132 * math.cos(a), 240 + 128 * math.sin(a)
        c.gem(x, y, 11, stones[j % 2])
    for j in range(11):
        a = math.pi * (0.08 + 0.84 * j / 10)
        x, y = cx + 150 * math.cos(a), 240 + 150 * math.sin(a)
        c.pearl(x, y + 14, 8)
    return c.final(W, H)


def polki_stud(metal=GOLD) -> Image.Image:
    W, H = 220, 220
    c = Canvas(W, H)
    cx = cy = 110
    c.shape(lambda d: d.ellipse([(cx - 92) * SS, (cy - 92) * SS, (cx + 92) * SS, (cy + 92) * SS], fill=255), metal)
    for i in range(8):
        a = i * math.pi / 4
        c.gem(cx + 58 * math.cos(a), cy + 58 * math.sin(a), 22, (244, 241, 232))
    c.gem(cx, cy, 30, (244, 241, 232))
    c.gem(cx, cy, 10, (178, 18, 46))
    return c.final(W, H)


def pearl_jhumki() -> Image.Image:
    return jhumka(SILVER, stone=(36, 70, 140), pearls=True)


def pair(piece: Image.Image, gap: int = 60) -> Image.Image:
    mirror = piece.transpose(Image.FLIP_LEFT_RIGHT)
    w = piece.width * 2 + gap
    out = Image.new("RGBA", (w, piece.height), (0, 0, 0, 0))
    out.alpha_composite(piece, (0, 0))
    out.alpha_composite(mirror, (piece.width + gap, 0))
    return out


# ------------------------------------------------------------------ necklaces (front view, worn)
def kundan_choker() -> Image.Image:
    W, H = 900, 520
    c = Canvas(W, H)
    cx, cy, rx, ry = W / 2, 40, 360, 330

    def band(d):
        outer = [(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in np.linspace(0.12 * math.pi, 0.88 * math.pi, 80)]
        inner = [(cx + (rx - 70) * math.cos(a), cy + (ry - 62) * math.sin(a))
                 for a in np.linspace(0.88 * math.pi, 0.12 * math.pi, 80)]
        d.polygon([(x * SS, y * SS) for x, y in outer + inner], fill=255)

    c.shape(band, GOLD)
    for j in range(15):
        a = math.pi * (0.16 + 0.68 * j / 14)
        x, y = cx + (rx - 35) * math.cos(a), cy + (ry - 31) * math.sin(a)
        c.gem(x, y, 20 if j % 2 == 0 else 14, (244, 241, 232) if j % 2 == 0 else (14, 122, 74))
    for j in range(13):
        a = math.pi * (0.18 + 0.64 * j / 12)
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        c.line([(x, y), (x, y + 26)], 2.5, GOLD)
        c.pearl(x, y + 36, 9)
    c.gem(cx, cy + ry + 30, 26, (178, 18, 46))
    c.shape(lambda d: d.ellipse([(cx - 34) * SS, (cy + ry - 4) * SS, (cx + 34) * SS, (cy + ry + 64) * SS],
                                outline=255, width=6 * SS), GOLD, outline=False)
    return c.final(W, H)


def temple_haar() -> Image.Image:
    W, H = 900, 640
    c = Canvas(W, H)
    cx, cy, rx, ry = W / 2, 20, 330, 470
    pts = [(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in np.linspace(0.1 * math.pi, 0.9 * math.pi, 120)]
    c.line(pts, 9, GOLD)
    for j in range(17):
        a = math.pi * (0.14 + 0.72 * j / 16)
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        c.shape(lambda d, x=x, y=y: d.ellipse([(x - 22) * SS, (y - 6) * SS, (x + 22) * SS, (y + 38) * SS], fill=255),
                GOLD)
        c.bead(x, y + 16, 6, GOLD)
    c.shape(lambda d: d.ellipse([(cx - 56) * SS, (cy + ry - 10) * SS, (cx + 56) * SS, (cy + ry + 110) * SS],
                                fill=255), GOLD, bands=4)
    c.gem(cx, cy + ry + 50, 22, (178, 18, 46))
    for j in range(7):
        x = cx - 48 + 96 * j / 6
        c.pearl(x, cy + ry + 124, 7)
    return c.final(W, H)


def pearl_layers() -> Image.Image:
    W, H = 900, 560
    c = Canvas(W, H)
    cx, cy = W / 2, 20
    for k, (rx, ry, pr) in enumerate([(300, 300, 9), (340, 380, 10), (380, 460, 11)]):
        n = 34 + k * 6
        for j in range(n):
            a = math.pi * (0.12 + 0.76 * j / (n - 1))
            c.pearl(cx + rx * math.cos(a), cy + ry * math.sin(a), pr)
    c.shape(lambda d: d.polygon([(cx * SS, (cy + 470) * SS), ((cx + 30) * SS, (cy + 510) * SS),
                                 (cx * SS, (cy + 550) * SS), ((cx - 30) * SS, (cy + 510) * SS)], fill=255), ROSE)
    c.gem(cx, cy + 510, 14, (14, 122, 74))
    return c.final(W, H)


ITEMS = {
    "jhumka_gold": lambda: pair(jhumka()),
    "chandbali_kundan": lambda: pair(chandbali()),
    "polki_studs": lambda: pair(polki_stud(), gap=80),
    "pearl_jhumki": lambda: pair(pearl_jhumki()),
    "kundan_choker": kundan_choker,
    "temple_haar": temple_haar,
    "pearl_layers": pearl_layers,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in ITEMS.items():
        img = fn()
        img.save(OUT / f"{name}.png", optimize=True)
        bg = Image.new("RGB", (img.width + 80, img.height + 80), (255, 255, 255))
        bg.paste(img, (40, 40), img)
        bg.save(OUT / f"{name}_ref.jpg", quality=95)
        print(name, img.size)


if __name__ == "__main__":
    main()
