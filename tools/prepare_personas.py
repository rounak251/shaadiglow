"""Offline prep for the sample personas (run once; NOT a runtime dependency).

Downloads the licensed sample photos listed in ASSETS.md, finds the face with
MediaPipe Face Landmarker + the multiclass selfie segmenter, and writes API-ready
crops plus landmark/mask files that the *mock* engine uses to render plausible
fixture images.  In live mode none of this is used: YouCam does the real work.

    python -m venv /tmp/tools && /tmp/tools/bin/pip install mediapipe pillow numpy
    /tmp/tools/bin/python tools/prepare_personas.py --models /path/to/models

Outputs (per persona) in app/static/personas/<id>/:
    face.jpg       768x1024, face ~66% of width  -> Skin Analysis, Skin Simulation, Makeup VTO
    beard.jpg      720x960,  same framing        -> Beard Style (needs long side < 1024)
    portrait.jpg   768x1024, head + shoulders    -> Hair Color, Earrings, Necklace
    geometry.json  landmarks / anchor points in each crop's pixel space
    *_hair.png, *_skin.png  soft masks for the mock renderer
"""
from __future__ import annotations

import argparse
import io
import json
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "static" / "personas"

# Unsplash License photos (see ASSETS.md for photographer credit and page URLs).
PERSONAS = {
    "ananya": "https://images.unsplash.com/photo-1609371497456-3a55a205d5eb?fm=jpg&q=92&w=2400",
    "arjun": "https://images.unsplash.com/photo-1712425718085-cdd2b2298669?fm=jpg&q=92&w=2400",
    "arjun2": "https://images.unsplash.com/photo-1712425718137-491250cfde88?fm=jpg&q=92&w=2400",
    "meera": "https://images.unsplash.com/photo-1747264465820-87d6c1a0692c?fm=jpg&q=92&w=2400",
}

FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377,
             152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
LIPS_OUTER = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
LIPS_INNER = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
EYE_R = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
EYE_L = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
BROW_R = [46, 53, 52, 65, 55, 70, 63, 105, 66, 107]
BROW_L = [276, 283, 282, 295, 285, 300, 293, 334, 296, 336]
NAMED = {"forehead": 10, "chin": 152, "nose_tip": 1, "nose_bridge": 6, "glabella": 9,
         "cheek_r": 205, "cheek_l": 425, "cheekbone_r": 116, "cheekbone_l": 345,
         "mouth_r": 61, "mouth_l": 291, "eye_r_outer": 33, "eye_l_outer": 263,
         "eye_r_inner": 133, "eye_l_inner": 362, "jaw_r": 172, "jaw_l": 397,
         "face_r": 234, "face_l": 454, "ear_r_low": 132, "ear_l_low": 361,
         "nose_wing_r": 129, "nose_wing_l": 358, "under_eye_r": 145, "under_eye_l": 374}

SEG_CLASSES = ["background", "hair", "body_skin", "face_skin", "clothes", "others"]


def fetch(url: str) -> Image.Image:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 shaadiglow-prep"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def detect(img: Image.Image, models: Path):
    import mediapipe as mp
    from mediapipe.tasks import python as mpp
    from mediapipe.tasks.python import vision

    arr = np.asarray(img)
    mimg = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
    lmk = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mpp.BaseOptions(model_asset_path=str(models / "face_landmarker.task")), num_faces=1))
    res = lmk.detect(mimg)
    if not res.face_landmarks:
        raise SystemExit("no face found")
    h, w = arr.shape[:2]
    pts = np.array([[p.x * w, p.y * h] for p in res.face_landmarks[0]], dtype=np.float32)
    seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=mpp.BaseOptions(model_asset_path=str(models / "selfie_multiclass_256x256.tflite")),
        output_confidence_masks=True, output_category_mask=False))
    sres = seg.segment(mimg)
    masks = {name: np.asarray(m.numpy_view()).astype(np.float32).reshape(h, w)
             for name, m in zip(SEG_CLASSES, sres.confidence_masks)}
    return pts, masks


def crop_box(pts: np.ndarray, face_frac: float, face_cy: float, size=(768, 1024)):
    oval = pts[FACE_OVAL]
    x0, y0 = oval.min(0)
    x1, y1 = oval.max(0)
    fw = x1 - x0
    cw = fw / face_frac
    ch = cw * size[1] / size[0]
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    return cw, ch, cx, cy, face_cy


def fit_inside(box, W: int, H: int):
    """Keep the crop inside the photo (shrink, then shift) so we never smear edges."""
    cw, ch, cx, cy, face_cy = box
    scale = min(1.0, W / cw, H / ch)
    cw, ch = cw * scale, ch * scale
    left = min(max(cx - cw / 2, 0), W - cw)
    top = min(max(cy - face_cy * ch, 0), H - ch)
    return left, top, cw, ch


def apply_crop(img: Image.Image, box, size):
    left, top, cw, ch = box
    # pad with edge colour when the box leaves the photo
    W, H = img.size
    pad = int(max(0, -left, -top, left + cw - W, top + ch - H)) + 2
    if pad > 2:
        arr = np.asarray(img)
        arr = np.pad(arr, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
        img = Image.fromarray(arr)
        left += pad
        top += pad
    out = img.crop((int(round(left)), int(round(top)), int(round(left + cw)), int(round(top + ch))))
    return out.resize(size, Image.LANCZOS), pad


def map_pts(pts, box, pad, size):
    left, top, cw, ch = box
    sx, sy = size[0] / cw, size[1] / ch
    return np.stack([(pts[:, 0] - left) * sx, (pts[:, 1] - top) * sy], 1)


def crop_mask(mask: np.ndarray, box, size):
    m = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
    left, top, cw, ch = box
    W, H = m.size
    pad = int(max(0, -left, -top, left + cw - W, top + ch - H)) + 2
    if pad > 2:
        arr = np.pad(np.asarray(m), ((pad, pad), (pad, pad)), mode="edge")
        m = Image.fromarray(arr)
        left += pad
        top += pad
    m = m.crop((int(round(left)), int(round(top)), int(round(left + cw)), int(round(top + ch))))
    return m.resize(size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.2))


def geometry(p: np.ndarray) -> dict:
    r = lambda idx: [[round(float(p[i, 0]), 1), round(float(p[i, 1]), 1)] for i in idx]
    oval = p[FACE_OVAL]
    return {
        "face_oval": r(FACE_OVAL), "lips_outer": r(LIPS_OUTER), "lips_inner": r(LIPS_INNER),
        "eye_r": r(EYE_R), "eye_l": r(EYE_L), "brow_r": r(BROW_R), "brow_l": r(BROW_L),
        "named": {k: [round(float(p[i, 0]), 1), round(float(p[i, 1]), 1)] for k, i in NAMED.items()},
        "face_box": [round(float(v), 1) for v in (*oval.min(0), *oval.max(0))],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True, type=Path)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    for pid, url in PERSONAS.items():
        if a.only and pid not in a.only:
            continue
        print("persona", pid)
        img = fetch(url)
        pts, masks = detect(img, a.models)
        d = OUT / pid
        d.mkdir(parents=True, exist_ok=True)
        geo = {"source_size": list(img.size)}
        variants = {"face": (0.66, 0.50, (768, 1024)), "beard": (0.66, 0.50, (720, 960)),
                    "portrait": (0.40, 0.34, (768, 1024))}
        for name, (frac, cy, size) in variants.items():
            box = fit_inside(crop_box(pts, frac, cy, size), *img.size)
            out, pad = apply_crop(img, box, size)
            out.save(d / f"{name}.jpg", quality=92, optimize=True)
            g = geometry(map_pts(pts, box, pad, size))
            g["size"] = list(size)
            geo[name] = g
            if name in ("face", "portrait"):
                crop_mask(masks["hair"], box, size).save(d / f"{name}_hair.png", optimize=True)
                skin = np.maximum(masks["face_skin"], 0.0)
                crop_mask(skin, box, size).save(d / f"{name}_skin.png", optimize=True)
                crop_mask(masks["body_skin"], box, size).save(d / f"{name}_body.png", optimize=True)
        (d / "geometry.json").write_text(json.dumps(geo, separators=(",", ":")))
        print("  ok", {k: v for k, v in geo.items() if k == "source_size"})


if __name__ == "__main__":
    main()
