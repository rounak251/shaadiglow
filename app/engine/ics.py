"""Export plan milestones as an .ics calendar (all-day events, RFC 5545)."""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    out, b = [], line.encode("utf-8")
    while len(b) > 74:
        cut = 74
        while cut > 0 and (b[cut] & 0xC0) == 0x80:   # don't split a UTF-8 character
            cut -= 1
        out.append(b[:cut].decode("utf-8"))
        b = b[cut:]
    out.append(b.decode("utf-8"))
    return "\r\n ".join(out)


def to_ics(plan: dict, lang: str = "en") -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ShaadiGlow//Countdown Plan//EN", "CALSCALE:GREGORIAN",
             "X-WR-CALNAME:ShaadiGlow countdown"]
    for m in plan.get("milestones", []):
        d = date.fromisoformat(m["date"])
        title = m["title"].get(lang) or m["title"]["en"]
        uid = hashlib.sha1(f"{m['date']}|{m['title']['en']}".encode()).hexdigest()[:16] + "@shaadiglow"
        label = "D-day" if m["d"] == 0 else f"D{m['d']}"
        lines += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{now}", f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
                  f"DTEND;VALUE=DATE:{d + timedelta(days=1):%Y%m%d}", _fold(f"SUMMARY:{_esc(f'{label} · {title}')}"),
                  _fold("DESCRIPTION:" + _esc("ShaadiGlow skin-prep plan. Cosmetic guidance, not medical advice.")),
                  "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
