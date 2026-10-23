"""Before/after deltas between skin scans, with an honest noise band.

Two photos of the same face never score identically (light, angle, expression).
We only call a change "better"/"worse" when it is larger than NOISE_BAND points;
smaller moves are reported as "steady".  Re-scans measure just the 4 tracked
concerns (9 units instead of 14).
"""
from __future__ import annotations

from .concerns import CONCERNS

NOISE_BAND = 3   # ui_score points; tune with scripts/live_smoke.py --noise once a key exists


def tracked(baseline: dict, k: int = 4) -> list[str]:
    ranked = sorted(baseline.get("concerns", []), key=lambda c: (c["raw"], c["ui"]))
    return [c["id"] for c in ranked[:k]]


def compare(baseline: dict, latest: dict) -> dict:
    b = {c["id"]: c for c in baseline.get("concerns", [])}
    rows = []
    for c in latest.get("concerns", []):
        if c["id"] not in b:
            continue
        d = c["ui"] - b[c["id"]]["ui"]
        verdict = "better" if d > NOISE_BAND else ("worse" if d < -NOISE_BAND else "steady")
        rows.append({"id": c["id"], "label": CONCERNS[c["id"]]["label"], "before": b[c["id"]]["ui"],
                     "after": c["ui"], "delta": d, "verdict": verdict})
    rows.sort(key=lambda r: -r["delta"])
    better = [r for r in rows if r["verdict"] == "better"]
    worse = [r for r in rows if r["verdict"] == "worse"]
    return {"rows": rows, "noise_band": NOISE_BAND, "better": len(better), "worse": len(worse),
            "steady": len(rows) - len(better) - len(worse),
            "headline": _headline(better, worse)}


def _headline(better: list[dict], worse: list[dict]) -> dict:
    if better and not worse:
        top = better[0]
        return {"en": f"{top['label']['en']} improved by {top['delta']} points. Keep going!",
                "hi": f"{top['label']['hi']} में {top['delta']} अंक सुधार। ऐसे ही जारी रखें!"}
    if worse:
        w = worse[-1]
        return {"en": f"{w['label']['en']} dipped by {abs(w['delta'])}. Check sleep, sunscreen and any new product.",
                "hi": f"{w['label']['hi']} {abs(w['delta'])} अंक घटा। नींद, सनस्क्रीन और नए प्रोडक्ट जाँचें।"}
    return {"en": "Steady: changes are within normal scan-to-scan variation.",
            "hi": "स्थिर: बदलाव सामान्य स्कैन-अंतर के भीतर हैं।"}
