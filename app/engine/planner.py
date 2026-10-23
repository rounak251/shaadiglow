"""Deterministic countdown planner: skin report + wedding date + city + budget -> prep plan.

Pure functions, no randomness, no LLM: the same inputs always give the same plan,
and every step carries the rule ids that put it there.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from . import catalog, climate
from .concerns import CONCERNS, focus_concerns
from .knowledge import DISCLAIMER, INGREDIENTS, RULES

PHASE_TEXT = {
    "reset": ({"en": "Reset", "hi": "रीसेट"},
              {"en": "Build the habit: gentle cleanse, moisturise, sunscreen. Patch-test your first active.",
               "hi": "आदत बनाएँ: हल्का क्लींज़, मॉइस्चराइज़, सनस्क्रीन। पहला एक्टिव पैच-टेस्ट करें।"}),
    "treat": ({"en": "Treat", "hi": "उपचार"},
              {"en": "Targeted actives for your top concerns, introduced one at a time.",
               "hi": "मुख्य चिंताओं के लिए एक्टिव, एक-एक करके।"}),
    "refine": ({"en": "Refine", "hi": "निखार"},
               {"en": "Keep going, re-scan, and book your makeup trial with your look.",
                "hi": "जारी रखें, दोबारा स्कैन करें, और अपने लुक के साथ मेकअप ट्रायल बुक करें।"}),
    "calm": ({"en": "Calm & hydrate", "hi": "शांत व नम"},
             {"en": "Short runway: one gentle active plus hydration. No experiments.",
              "hi": "कम समय: एक हल्का एक्टिव और भरपूर नमी। कोई प्रयोग नहीं।"}),
    "protect": ({"en": "Protect", "hi": "सुरक्षा"},
                {"en": "Nothing new from here. Wind down strong actives, keep hydration and SPF.",
                 "hi": "अब कुछ नया नहीं। तेज़ एक्टिव धीरे-धीरे बंद, नमी और SPF जारी।"}),
    "glow": ({"en": "Glow", "hi": "चमक"},
             {"en": "Hydrating mask, early night, and a calm makeup prep routine.",
              "hi": "हाइड्रेटिंग मास्क, जल्दी सोना, और शांत मेकअप-प्रेप।"}),
}

SLOT_LABEL = {
    "first_cleanse": {"en": "First cleanse", "hi": "पहला क्लींज़"}, "cleanser": {"en": "Cleanse", "hi": "क्लींज़"},
    "serum_am": {"en": "Antioxidant serum", "hi": "एंटीऑक्सीडेंट सीरम"}, "serum": {"en": "Serum", "hi": "सीरम"},
    "treatment": {"en": "Treatment", "hi": "ट्रीटमेंट"}, "hydrator": {"en": "Hydrate", "hi": "नमी"},
    "eye": {"en": "Eyes", "hi": "आँखें"}, "moisturiser": {"en": "Moisturise", "hi": "मॉइस्चराइज़"},
    "sunscreen": {"en": "Protect (SPF)", "hi": "सुरक्षा (SPF)"}, "spot": {"en": "Spot care", "hi": "स्पॉट केयर"},
    "weekly": {"en": "Weekly mask", "hi": "साप्ताहिक मास्क"}, "beard": {"en": "Beard", "hi": "दाढ़ी"},
    "lip": {"en": "Lips", "hi": "होंठ"}, "primer": {"en": "Makeup prep", "hi": "मेकअप-प्रेप"},
    "kit": {"en": "Wedding-day kit", "hi": "शादी के दिन का किट"}, "night": {"en": "Night cream", "hi": "नाइट क्रीम"},
}

TIER_ORDER = ["essential", "balanced", "premium"]
BASIC_INGREDIENTS = {"caffeine", "hyaluronic_acid"}
MAX_ACTIVES = {"essential": 2, "balanced": 3, "premium": 4}


@dataclass
class PlanInput:
    wedding_date: date
    today: date
    city: str = "delhi"
    budget: str = "balanced"
    role: str = "bride"
    pregnant: bool = False
    sensitive: bool = False
    events: list[str] = field(default_factory=lambda: ["haldi", "mehendi", "sangeet", "wedding", "reception"])
    lang: str = "en"


def _t(rule: str, **kw) -> dict:
    r = RULES[rule]
    out = {"id": rule}
    for lang in ("en", "hi"):
        vals = {k: (v[lang] if isinstance(v, dict) else v) for k, v in kw.items()}
        out[lang] = r[lang].format(**vals)
    return out


def _cheapest(ingredient: str, tier: str, role: str) -> dict | None:
    allowed = TIER_ORDER[:TIER_ORDER.index(tier) + 1]
    cands = [p for p in catalog.SKINCARE if ingredient in p["ingredients"] and p["tier"] in allowed
             and role in p["roles"] and p["slot"] in ("serum", "serum_am", "treatment", "hydrator")]
    if not cands:
        return None
    # prefer the best product the tier allows, then price
    return sorted(cands, key=lambda p: (-allowed.index(p["tier"]) if tier == "premium" else 0, p["price"]))[0]


def plan_type(days: int) -> str:
    if days >= 60:
        return "full"
    if days >= 30:
        return "standard"
    if days >= 14:
        return "gentle"
    return "rescue"


def _phases(kind: str, today: date, wedding: date) -> list[tuple[str, date, date]]:
    d = lambda n: wedding - timedelta(days=n)
    if kind == "full":
        spans = [("reset", today, today + timedelta(days=13)), ("treat", today + timedelta(days=14), d(31)),
                 ("refine", d(30), d(15)), ("protect", d(14), d(2)), ("glow", d(1), wedding)]
    elif kind == "standard":
        spans = [("reset", today, today + timedelta(days=6)), ("treat", today + timedelta(days=7), d(15)),
                 ("protect", d(14), d(2)), ("glow", d(1), wedding)]
    elif kind == "gentle":
        spans = [("calm", today, d(15)), ("protect", d(14), d(2)), ("glow", d(1), wedding)]
    else:
        spans = [("protect", today, max(today, d(2))), ("glow", max(today, d(1)), wedding)]
    return [(k, s, e) for k, s, e in spans if e >= s]


def select_actives(focus: list[dict], days: int, inp: PlanInput) -> tuple[list[dict], list[dict], list[dict]]:
    weights = {c["id"]: max(1.0, 80.0 - c["ui"]) for c in focus}
    chosen, skipped, fired = [], [], []
    covered: dict[str, float] = {}
    exfoliants = 0
    limit = MAX_ACTIVES[inp.budget] if days >= 14 else 0
    if days < 14:
        fired.append(_t("R-RESCUE"))
    # caffeine (eyes) and hyaluronic acid (hydration) are support steps, added by _basics, not "actives"
    pool = [(k, v) for k, v in INGREDIENTS.items() if k not in BASIC_INGREDIENTS]
    while len(chosen) < limit:
        best, best_gain = None, 0.0
        for key, ing in pool:
            if any(a["key"] == key for a in chosen) or any(s["key"] == key for s in skipped):
                continue
            gain = sum(weights.get(c, 0) * s * (1 - min(1.0, covered.get(c, 0))) for c, s in ing["targets"].items())
            if gain > best_gain:
                best, best_gain = (key, ing), gain
        if not best or best_gain <= 0:
            break
        key, ing = best
        name = ing["name"]
        reason = None
        if days < ing["min_days"]:
            reason = _t("R-TIME-SKIP", ingredient=name, need=ing["min_days"], days=days)
        elif inp.pregnant and not ing["preg_ok"]:
            reason = _t("R-PREG", ingredient=name)
        elif inp.sensitive and not ing["sensitive_ok"]:
            reason = _t("R-SENSITIVE", ingredient=name)
        elif ing["exfoliant"] and exfoliants >= (2 if days >= 60 and not inp.sensitive else 1):
            reason = _t("R-ONE-EXFOLIANT", ingredient=name)
        product = None if reason else _cheapest(key, inp.budget, inp.role)
        if not reason and product is None:
            reason = _t("R-BUDGET", tier=catalog.TIERS[inp.budget]["label"], n=limit, ingredient=name)
        if reason:
            skipped.append({"key": key, "name": name, "reason": reason})
            fired.append(reason)
            continue
        if ing["exfoliant"]:
            exfoliants += 1
        why = []
        for c in focus:
            if c["id"] in ing["targets"] and weights.get(c["id"], 0) >= 5:
                why.append(_t("R-FOCUS", concern=CONCERNS[c["id"]]["label"], ui=c["ui"]))
        for c, s in ing["targets"].items():
            covered[c] = covered.get(c, 0) + s / 3.0
        chosen.append({"key": key, "name": name, "product": product["id"], "when": ing["when"],
                       "how": ing["how"], "evidence": ing["evidence"], "stop_before": ing["stop_before"],
                       "exfoliant": ing["exfoliant"], "targets": [c for c in ing["targets"] if c in weights],
                       "why": why})
        fired.extend(why)
    return chosen, skipped, fired


def _basics(inp: PlanInput, skin_type: str, air: str, focus_ids: set[str], cl_now: dict) -> tuple[dict, list[dict]]:
    tier = inp.budget
    fired = []
    oily = skin_type in ("Oily", "Combination", "Oily & Redness", "Combination & Redness")
    dry = skin_type in ("Dry", "Dry & Redness") or air == "dry"
    if air == "humid":
        fired.append(_t("R-HUMID", city={"en": cl_now["name"], "hi": cl_now["name_hi"]}, month=cl_now["month"]))
    elif air == "dry":
        fired.append(_t("R-DRY", city={"en": cl_now["name"], "hi": cl_now["name_hi"]}, month=cl_now["month"]))
    texture = "gel" if (oily or air == "humid") and not dry else ("cream" if dry else "lotion")
    fired.append(_t("R-SKINTYPE", type=skin_type, tz=skin_type.split(" ")[0],
                    texture={"en": texture, "hi": {"gel": "जेल", "cream": "क्रीम", "lotion": "लोशन"}[texture]}))
    b = {}
    if "acne" in focus_ids and not inp.sensitive and not inp.pregnant:
        b["cleanser"] = "cl_bha"
    else:
        b["cleanser"] = "cl_cream" if dry else "cl_gel"
    b["moisturiser"] = {"gel": "mo_gel", "cream": "mo_cream", "lotion": "mo_lotion"}[texture]
    if tier == "premium" and "redness" in focus_ids:
        b["sunscreen"] = "ss_tinted"
    elif texture == "gel":
        b["sunscreen"] = "ss_gel"
    elif texture == "cream":
        b["sunscreen"] = "ss_cream"
    else:
        b["sunscreen"] = "ss_fluid" if tier != "essential" else "ss_gel"
    fired.append(_t("R-UV", city={"en": cl_now["name"], "hi": cl_now["name_hi"]}, month=cl_now["month"],
                    uv={"en": cl_now["uv"], "hi": {"high": "ऊँचा", "very high": "बहुत ऊँचा",
                                                   "extreme": "अत्यधिक"}[cl_now["uv"]]}))
    if cl_now["smog"] and tier != "essential":
        b["first_cleanse"] = "cl_balm"
        fired.append(_t("R-SMOG", city={"en": cl_now["name"], "hi": cl_now["name_hi"]}))
    if {"dark_circle_v2", "eye_bag"} & focus_ids:
        b["eye"] = "ey_lux" if tier == "premium" else "ey_caff"
    if "moisture" in focus_ids or dry:
        b["hydrator"] = "se_ha"
    if oily and ({"oiliness", "pore"} & focus_ids):
        b["weekly"] = "mk_clay"
    b["glow_mask"] = "mk_sheet"
    if "acne" in focus_ids:
        b["spot"] = "sp_patch"
    b["lip"] = "lp_balm"
    if inp.role in ("bride", "guest"):
        b["primer"] = "pr_matte" if oily else "pr_glow"
        if oily or air == "humid":
            b["kit"] = "bl_paper"
    if inp.role == "groom":
        b["beard"] = "gr_beardoil"
        if "redness" in focus_ids:
            b["aftershave"] = "gr_aftershave"
        if oily:
            b["kit"] = "bl_paper"
    return b, fired


def _step(slot: str, pid: str, note: dict | None = None, why: list | None = None) -> dict:
    p = catalog.get(pid)
    return {"slot": slot, "label": SLOT_LABEL.get(slot, {"en": slot, "hi": slot}), "product": pid,
            "name": p["name"], "note": note, "why": why or []}


def build_plan(inp: PlanInput, scan: dict) -> dict:
    days = (inp.wedding_date - inp.today).days
    kind = plan_type(days) if days >= 0 else "after"
    concerns = scan.get("concerns", [])
    focus = focus_concerns(concerns, k=4 if inp.budget == "premium" else 3)
    focus_ids = {c["id"] for c in focus}
    st = (scan.get("skin_type") or {}).get("whole", {}).get("type", "Normal")
    tz = (scan.get("skin_type") or {}).get("t_zone", {}).get("type", st)
    cl_now = climate.bands(inp.city, inp.today)
    cl_wed = climate.bands(inp.city, inp.wedding_date)
    air = cl_now["skin_air"]
    actives, skipped, fired = select_actives(focus, max(days, 0), inp)
    basics, fired_b = _basics(inp, st, air, focus_ids, cl_now)
    fired += fired_b
    fired.append(_t("R-PATCH"))
    by_key = {a["key"]: a for a in actives}

    # ---------------- routines
    am, pm = [], []
    if "first_cleanse" in basics:
        pm.append(_step("first_cleanse", basics["first_cleanse"]))
    am.append(_step("cleanser", basics["cleanser"]))
    pm.append(_step("cleanser", basics["cleanser"]))
    for a in actives:
        note = a["how"]
        if a["when"] in ("am", "am_pm"):
            am.append(_step("serum_am" if a["key"] == "vitamin_c" else "serum", a["product"], note, a["why"]))
        if a["when"] in ("pm", "am_pm"):
            pm.append(_step("treatment" if a["exfoliant"] or a["key"] == "azelaic_acid" else "serum",
                            a["product"], note, a["why"]))
    if "hydrator" in basics and "hyaluronic_acid" not in by_key:
        am.append(_step("hydrator", basics["hydrator"]))
        pm.append(_step("hydrator", basics["hydrator"]))
    if "eye" in basics:
        am.append(_step("eye", basics["eye"]))
        pm.append(_step("eye", basics["eye"]))
    if "beard" in basics:
        am.append(_step("beard", basics["beard"]))
    am.append(_step("moisturiser", basics["moisturiser"]))
    pm.append(_step("moisturiser", basics["moisturiser"]))
    am.append(_step("sunscreen", basics["sunscreen"],
                    {"en": "Two finger-lengths for face and neck; reapply outdoors.",
                     "hi": "चेहरे और गर्दन के लिए दो उँगली भर; बाहर हों तो दोबारा।"}))
    pm.append(_step("lip", basics["lip"]))
    weekly = []
    if "weekly" in basics:
        weekly.append(_step("weekly", basics["weekly"], {"en": "Once a week on the T-zone.",
                                                          "hi": "हफ़्ते में एक बार टी-ज़ोन पर।"}))

    # ---------------- phases (actives switch on/off by date)
    phases = []
    for key, start, end in _phases(kind, inp.today, inp.wedding_date):
        name, goal = PHASE_TEXT[key]
        p_am = [s for s in am if _active_allowed(s, key, by_key)]
        p_pm = [s for s in pm if _active_allowed(s, key, by_key)]
        if key == "protect":
            p_am = [_with_stop_note(s, by_key, inp.wedding_date) for s in p_am]
            p_pm = [_with_stop_note(s, by_key, inp.wedding_date) for s in p_pm]
        p_weekly = list(weekly) if key not in ("glow",) else []
        notes = []
        if key in ("reset", "calm"):
            notes.append(_t("R-KEEP-BASICS"))
        if key == "protect":
            notes.append(_t("R-NO-NEW"))
            if "retinol" in by_key:
                notes.append(_t("R-STOP-RETINOL"))
            if any(a["exfoliant"] for a in actives):
                notes.append(_t("R-STOP-ACIDS"))
            if "spot" in basics:
                p_pm.append(_step("spot", basics["spot"], {"en": "Only on a new spot, overnight.",
                                                            "hi": "सिर्फ़ नए दाने पर, रात भर।"}))
        if key == "glow":
            p_pm.append(_step("weekly", basics["glow_mask"], {"en": "The night before: hydrating sheet mask.",
                                                               "hi": "एक रात पहले: हाइड्रेटिंग शीट मास्क।"}))
            if "primer" in basics:
                p_am.append(_step("primer", basics["primer"]))
        phases.append({"id": key, "name": name, "goal": goal, "start": start.isoformat(), "end": end.isoformat(),
                       "days": (end - start).days + 1, "am": p_am, "pm": p_pm, "weekly": p_weekly, "notes": notes})
        fired.extend(notes)

    milestones = _milestones(inp, kind, actives, days)
    season = _season_switch(inp, st, air, basics)
    if season:
        milestones.append(season["milestone"])
        milestones.sort(key=lambda m: m["date"])
        fired.append(season["rule"])
        basics["season_moisturiser"] = season["product"]
    if "mehendi" in inp.events:
        fired.append(_t("R-HENNA"))
    if "haldi" in inp.events:
        fired.append(_t("R-HALDI"))

    # ---------------- shopping list for the plan
    pids: list[str] = []
    for s in am + pm + weekly:
        if s["product"] not in pids:
            pids.append(s["product"])
    for extra in ("spot", "glow_mask", "primer", "kit", "aftershave", "season_moisturiser"):
        if extra in basics and basics[extra] not in pids:
            pids.append(basics[extra])
    items = [_line(pid, focus_ids, by_key) for pid in pids]
    cap = catalog.TIERS[inp.budget]["cap"]
    total = sum(i["price"] for i in items)
    dropped = []
    optional_order = ["kit", "primer", "weekly", "lip", "eye", "first_cleanse", "hydrator"]
    for slot in optional_order:
        if total <= cap:
            break
        for i in list(items):
            if i["slot"] == slot and total > cap:
                items.remove(i)
                dropped.append(i)
                total -= i["price"]
    seen, rules = set(), []
    for r in fired:
        k = (r["id"], r["en"])
        if k not in seen:
            seen.add(k)
            rules.append(r)
    return {
        "days_left": days, "plan_type": kind, "wedding_date": inp.wedding_date.isoformat(),
        "today": inp.today.isoformat(), "role": inp.role, "budget": {"tier": inp.budget, **catalog.TIERS[inp.budget]},
        "climate": {"now": cl_now, "wedding": cl_wed}, "skin_type": {"whole": st, "t_zone": tz},
        "focus": [{"id": c["id"], "ui": c["ui"], "label": c["label"]} for c in focus],
        "actives": actives, "skipped": skipped, "phases": phases, "milestones": milestones,
        "products": items, "dropped": dropped, "total": total, "rules": rules, "disclaimer": DISCLAIMER,
        "current_phase": _current_phase(phases, inp.today),
    }


def _season_switch(inp: PlanInput, skin_type: str, air_now: str, basics: dict) -> dict | None:
    """If the city's air changes before the wedding (e.g. Delhi turns dry and cold), plan the swap."""
    d = date(inp.today.year, inp.today.month, 1)
    while True:
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        if d > inp.wedding_date:
            return None
        cl = climate.bands(inp.city, d)
        if cl["skin_air"] != air_now and cl["skin_air"] in ("dry", "humid"):
            break
    oily = skin_type in ("Oily", "Combination", "Oily & Redness", "Combination & Redness")
    if cl["skin_air"] == "dry":
        texture, pid = ("lotion", "mo_lotion") if oily else ("cream", "mo_cream")
    else:
        texture, pid = "gel", "mo_gel"
    if pid == basics.get("moisturiser"):
        return None
    hi_air = {"dry": "रूखा/ठंडा", "humid": "नम"}[cl["skin_air"]]
    hi_tex = {"gel": "जेल", "cream": "क्रीम", "lotion": "लोशन"}[texture]
    rule = _t("R-SEASON", city={"en": cl["name"], "hi": cl["name_hi"]}, month=cl["month"],
              air={"en": "dry and cool" if cl["skin_air"] == "dry" else "humid", "hi": hi_air},
              texture={"en": texture, "hi": hi_tex})
    m = {"date": d.isoformat(), "d": (d - inp.wedding_date).days, "kind": "skin", "rule": "R-SEASON",
         "title": {"en": f"Season switch: {cl['name']} turns {'dry' if cl['skin_air'] == 'dry' else 'humid'}, "
                         f"swap to {catalog.get(pid)['name']}",
                   "hi": f"मौसम बदला: {cl['name_hi']} {hi_air}, अब {catalog.get(pid)['name']}"}}
    return {"rule": rule, "milestone": m, "product": pid}


def _active_allowed(step: dict, phase: str, by_key: dict) -> bool:
    """Which routine steps run in which phase (basics always run)."""
    a = _active_of(step, by_key)
    if a is None:
        return True
    if phase == "reset":            # one new active at a time: only the first during Reset
        return a is next(iter(by_key.values()))
    if phase == "glow":             # final days: no exfoliants
        return not a["exfoliant"]
    return True


def _active_of(step: dict, by_key: dict) -> dict | None:
    for a in by_key.values():
        if a["product"] == step["product"]:
            return a
    return None


def _with_stop_note(step: dict, by_key: dict, wedding: date) -> dict:
    a = _active_of(step, by_key)
    if not a or not a["stop_before"]:
        return step
    stop = wedding - timedelta(days=a["stop_before"])
    note = {"en": f"Last use {stop.strftime('%d %b')} ({a['stop_before']} days before).",
            "hi": f"आख़िरी बार {stop.strftime('%d %b')} ({a['stop_before']} दिन पहले)।"}
    return {**step, "note": note}


def _line(pid: str, focus_ids: set[str], by_key: dict) -> dict:
    p = catalog.get(pid)
    reasons = [CONCERNS[c]["label"] for c in p["concerns"] if c in focus_ids][:2]
    return {"id": pid, "name": p["name"], "price": p["price"], "size": p["size"], "slot": p["slot"],
            "category": p["category"], "art": p["art"], "for": reasons, "note": p.get("note")}


def _milestones(inp: PlanInput, kind: str, actives: list[dict], days: int) -> list[dict]:
    w = inp.wedding_date
    out = []

    def add(d: date, kind_: str, en: str, hi: str, rule: str | None = None):
        if inp.today <= d <= w:
            out.append({"date": d.isoformat(), "d": (d - w).days, "kind": kind_, "title": {"en": en, "hi": hi},
                        "rule": rule})

    if actives and kind != "rescue":
        a0 = actives[0]
        add(inp.today, "skin", f"Patch-test {a0['name']['en']} behind your ear (48 h)",
            f"{a0['name']['hi']} कान के पीछे पैच-टेस्ट करें (48 घंटे)", "R-PATCH")
        gap = 7 if kind in ("standard", "gentle") else 10
        for i, a in enumerate(actives[1:], 1):
            d = inp.today + timedelta(days=gap * i)
            if (w - d).days > 14:
                add(d, "skin", f"Add {a['name']['en']} (after a 48 h patch test)",
                    f"{a['name']['hi']} जोड़ें (48 घंटे पैच-टेस्ट के बाद)", "R-PATCH")
    d = inp.today + timedelta(days=14)
    while (w - d).days >= 7:
        add(d, "scan", "Quick re-scan: track your top concerns (9 units)",
            "क्विक री-स्कैन: मुख्य चिंताएँ ट्रैक करें (9 यूनिट)")
        d += timedelta(days=14)
    if inp.role == "bride" and days >= 21:
        add(w - timedelta(days=21), "beauty", "Makeup trial: show your artist your saved looks",
            "मेकअप ट्रायल: अपने सेव किए लुक आर्टिस्ट को दिखाएँ")
    if days >= 15:
        add(w - timedelta(days=14), "skin", "Last facial or clean-up (only one you've had before). Nothing new after today.",
            "आख़िरी फ़ेशियल/क्लीन-अप (सिर्फ़ पहले कराया हुआ)। आज के बाद कुछ नया नहीं।", "R-NO-NEW")
    if any(a["key"] == "retinol" for a in actives):
        add(w - timedelta(days=7), "skin", "Stop retinol", "रेटिनॉल बंद करें", "R-STOP-RETINOL")
    if any(a["exfoliant"] for a in actives):
        add(w - timedelta(days=5), "skin", "Stop exfoliating acids", "एक्सफ़ोलिएटिंग एसिड बंद करें", "R-STOP-ACIDS")
    if inp.role in ("bride", "guest"):
        add(w - timedelta(days=4), "beauty", "Threading & waxing (redness needs 2-3 days to settle)",
            "थ्रेडिंग और वैक्सिंग (लालिमा जाने में 2-3 दिन लगते हैं)")
    if inp.role == "groom":
        add(w - timedelta(days=2), "beauty", "Beard shape-up at the barber (not on the day)",
            "नाई के पास दाढ़ी की सेटिंग (शादी के दिन नहीं)")
    if "mehendi" in inp.events:
        add(w - timedelta(days=2), "ritual", "Mehendi: natural henna only (no 'black henna')",
            "मेहंदी: सिर्फ़ प्राकृतिक मेहंदी ('काली मेहंदी' नहीं)", "R-HENNA")
    if "haldi" in inp.events:
        add(w - timedelta(days=1), "ritual", "Haldi: gentle cleanse and moisturise afterwards",
            "हल्दी: बाद में हल्का क्लींज़ और मॉइस्चराइज़ करें", "R-HALDI")
    add(w - timedelta(days=1), "skin", "Sheet mask and 8 hours of sleep", "शीट मास्क और 8 घंटे की नींद")
    add(w, "ritual", "Wedding day: cleanse, hydrate, SPF, primer, blot", "शादी का दिन: क्लींज़, नमी, SPF, प्राइमर, ब्लॉट")
    out.sort(key=lambda m: m["date"])
    return out


def _current_phase(phases: list[dict], today: date) -> str | None:
    t = today.isoformat()
    for p in phases:
        if p["start"] <= t <= p["end"]:
            return p["id"]
    return phases[0]["id"] if phases else None
