#!/usr/bin/env python3
"""Turn the raw Garmin export into the shape the page reads.

  python3 build_data.py            # garmin-raw.json -> data.json

One session (28 Nov 2025) was logged at a gym grading in Japanese kyu. Those
climbs are converted to the V-scale with the standard table below and flagged
so the page can mark them.
"""
import json, datetime as dt, collections, sys

RAW = sys.argv[1] if len(sys.argv) > 1 else "garmin-raw.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data.json"

# Japanese kyu -> V. Garmin's DANKYU sortOrder is relative within its own scale,
# so the mapping has to be explicit. Conversion is approximate and gym-dependent.
KYU_TO_GS = {
    "_7_KYUU": 1,   # 7 kyu -> V0
    "_6_KYUU": 2,   # 6 kyu -> V1
    "_5_KYUU": 3,   # 5 kyu -> V2
    "_4_KYUU": 4,   # 4 kyu -> V3
    "_3_KYUU": 5,   # 3 kyu -> V4
    "_2_KYUU": 6,   # 2 kyu -> V5
    "_1_KYUU": 7,   # 1 kyu -> V6
}

def as_v(c):
    """Return (gradeSortOrder, converted?) or (None, False) if not mappable."""
    if c["sc"] == "VERMIN":
        return c["gs"], False
    if c["sc"] == "DANKYU" and c["g"] in KYU_TO_GS:
        return KYU_TO_GS[c["g"]], True
    return None, False

def gname(gs):
    return "VB" if gs == 0 else "V%d" % (gs - 1)

def monday(d):
    return d - dt.timedelta(days=d.weekday())

raw = json.load(open(RAW))
sessions = [s for s in raw["sessions"] if s["type"] == "bouldering"]
sessions.sort(key=lambda s: s["date"])

out_sessions, weeks = [], collections.OrderedDict()
grades_seen = set()

for s in sessions:
    day = dt.date.fromisoformat(s["date"][:10])
    v, nconv = [], 0
    for c in s["climbs"]:
        gs, conv = as_v(c)
        if gs is None:
            continue
        v.append({"gs": gs, "ok": c["ok"]})
        nconv += conv

    wall = sum(c["d"] for c in s["climbs"])
    rest = sum(s["rests"])
    per = collections.defaultdict(lambda: [0, 0])
    for c in v:
        per[c["gs"]][0] += 1
        per[c["gs"]][1] += c["ok"]
        grades_seen.add(c["gs"])

    sent = [c["gs"] for c in v if c["ok"]]
    allg = sorted(c["gs"] for c in v)
    out_sessions.append({
        "d": s["date"][:10],
        "t": s["date"][11:16],
        "id": s["id"],
        "n": len(v),                                     # V-scale attempts
        "s": sum(c["ok"] for c in v),                    # sends
        "max": max(sent) if sent else None,              # hardest send
        "top": max(allg) if allg else None,              # hardest tried
        "med": allg[len(allg) // 2] if allg else None,   # median tried
        "wall": wall, "rest": rest,
        "hr": s["hr"], "hrx": s["hrx"], "cal": s["cal"],
        "load": round(s["load"], 1) if s["load"] else None,
        "byGrade": {str(k): per[k] for k in sorted(per)},
        "kyu": nconv,                                    # climbs converted from kyu
    })

    if v:
        wk = monday(day).isoformat()
        w = weeks.setdefault(wk, {"w": wk, "sessions": 0, "cells": {}, "kyu": 0,
                                   "dur": 0, "wall": 0})
        w["sessions"] += 1
        w["kyu"] += nconv
        w["dur"] += int(s["dur"] or 0)       # whole session, door to door
        w["wall"] += wall                    # seconds actually on a boulder
        for k, (a, sd) in per.items():
            cell = w["cells"].setdefault(str(k), [0, 0])
            cell[0] += a
            cell[1] += sd

# fill empty weeks so the heatmap keeps real time on the x-axis
if weeks:
    keys = sorted(weeks)
    cur, last = dt.date.fromisoformat(keys[0]), dt.date.fromisoformat(keys[-1])
    while cur <= last:
        weeks.setdefault(cur.isoformat(), {"w": cur.isoformat(), "sessions": 0, "cells": {},
                                           "kyu": 0, "dur": 0, "wall": 0})
        cur += dt.timedelta(days=7)

grades = sorted(grades_seen)
totals = collections.defaultdict(lambda: [0, 0])
for s in out_sessions:
    for k, (a, sd) in s["byGrade"].items():
        totals[int(k)][0] += a
        totals[int(k)][1] += sd

data = {
    "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    "from": out_sessions[0]["d"], "to": out_sessions[-1]["d"],
    "grades": [{"gs": g, "key": gname(g)} for g in grades],
    "weeks": [weeks[k] for k in sorted(weeks)],
    "sessions": out_sessions,
    "byGrade": {str(g): totals[g] for g in grades},
}
json.dump(data, open(OUT, "w"), separators=(",", ":"))

n = sum(s["n"] for s in out_sessions)
print(f"{len(out_sessions)} sessions, {n} V-scale climbs, "
      f"{sum(s['s'] for s in out_sessions)} sends, {len(data['weeks'])} weeks -> {OUT}")
