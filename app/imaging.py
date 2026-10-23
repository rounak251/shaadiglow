"""Photo hygiene: decode safely, fix EXIF rotation, strip metadata, and size each
variant to the limits the YouCam docs give for the API that will receive it."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 40_000_000     # refuse decompression bombs

VARIANTS = {
    # name: (size, purpose)
    "face": ((768, 1024), "AI Skin Analysis (SD: short side >= 480), Skin Simulation, Makeup VTO (< 1080 px high)"),
    "beard": ((720, 960), "AI Beard Style Generator (long side < 1024)"),
    "portrait": ((768, 1024), "Hair Color, Earrings, Necklace (head and shoulders)"),
}


class BadImage(ValueError):
    pass


def load(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
    except Exception as e:  # noqa: BLE001 - any decode problem is a bad upload
        raise BadImage("This file is not a readable JPEG or PNG photo.") from e
    if img.width < 480 or img.height < 480:
        raise BadImage("This photo is too small. Use one at least 480 px on each side.")
    return img.convert("RGB")


def fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Centre-crop to the target aspect ratio, then resize (metadata is dropped on save)."""
    return ImageOps.fit(img, size, Image.LANCZOS, centering=(0.5, 0.45))


def to_jpeg(img: Image.Image, quality: int = 92) -> bytes:
    b = io.BytesIO()
    img.save(b, "JPEG", quality=quality, optimize=True)
    return b.getvalue()


def make_variants(face: bytes, portrait: bytes | None = None) -> dict[str, bytes]:
    f = load(face)
    p = load(portrait) if portrait else f
    return {"face": to_jpeg(fit(f, VARIANTS["face"][0])), "beard": to_jpeg(fit(f, VARIANTS["beard"][0])),
            "portrait": to_jpeg(fit(p, VARIANTS["portrait"][0]))}


def cheek_colour(face_jpeg: bytes) -> tuple[float, float, float]:
    """Average colour of both cheeks on our standard 3:4 face crop (face fills ~2/3 of the width)."""
    img = Image.open(io.BytesIO(face_jpeg)).convert("RGB")
    a = np.asarray(img).astype(np.float32)
    h, w = a.shape[:2]
    patches = []
    for cx in (0.33, 0.67):
        x0, x1 = int((cx - 0.05) * w), int((cx + 0.05) * w)
        y0, y1 = int(0.53 * h), int(0.61 * h)
        patches.append(a[y0:y1, x0:x1].reshape(-1, 3))
    px = np.concatenate(patches)
    lum = px @ np.array([0.299, 0.587, 0.114], np.float32)
    keep = px[(lum > np.percentile(lum, 15)) & (lum < np.percentile(lum, 90))]   # skip shadows and shine
    m = keep.mean(0) if len(keep) else px.mean(0)
    return float(m[0]), float(m[1]), float(m[2])
