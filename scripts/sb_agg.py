"""Télécharge les événements StatsBomb 2015/16 (5 ligues) et les résume par match et par équipe, sans les stocker.

    python scripts/sb_agg.py data/statsbomb_2015.pkl     (~6 Go transférés, ~3 min ; résultat ~20 Mo)
"""
import json, sys, urllib.request, pickle, os
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
OUT = sys.argv[1]
BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
COMPS = {9: "D1", 11: "SP1", 7: "F1", 2: "E0", 12: "I1"}
NX, NY = 12, 8
cell = lambda x, y: min(int(x / 120 * NX), NX - 1) * NY + min(int(y / 80 * NY), NY - 1)

def get(url):
    for _ in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            err = e
    raise err

def resume(m):
    ev = get(f"{BASE}/events/{m['match_id']}.json")
    teams = [m["home_team"]["home_team_name"], m["away_team"]["away_team_name"]]
    f = {t: Counter() for t in teams}
    moves = {t: Counter() for t in teams}          # (case départ, case arrivée) des passes et conduites réussies
    grid = {"shots": Counter(), "goals": Counter(), "moves": Counter(), "trans": Counter()}
    dist = {t: [] for t in teams}
    for e in ev:
        t = e.get("team", {}).get("name"); ty = e["type"]["name"]
        if t not in f:
            continue
        pt = e.get("possession_team", {}).get("name")
        if pt in f and e.get("duration"):
            f[pt]["poss_time"] += e["duration"]
        loc = e.get("location")
        if loc:
            x, y = loc
            f[t]["events"] += 1; f[t]["ev_def3"] += x < 40; f[t]["ev_att3"] += x > 80
            f[t]["ev_box"] += (x > 102 and 18 <= y <= 62); dist[t].append(((120 - x) ** 2 + (40 - y) ** 2) ** .5)
        if ty == "Pass":
            p = e["pass"]; ok = "outcome" not in p
            f[t]["passes"] += 1; f[t]["passes_ok"] += ok; f[t]["pass_len"] += p.get("length", 0)
            if ok and p["end_location"][0] > 80:
                f[t]["passes_att3"] += 1
            if loc and ok:
                a, b = cell(*loc), cell(*p["end_location"][:2]); moves[t][(a, b)] += 1; grid["moves"][a] += 1; grid["trans"][(a, b)] += 1
            elif loc:
                grid["moves"][cell(*loc)] += 1               # tentative ratée : action sans transition
        elif ty == "Carry" and loc:
            end = e["carry"]["end_location"]; a, b = cell(*loc), cell(*end[:2])
            f[t]["carries"] += 1; f[t]["carry_len"] += ((end[0] - loc[0]) ** 2 + (end[1] - loc[1]) ** 2) ** .5
            moves[t][(a, b)] += 1; grid["moves"][a] += 1; grid["trans"][(a, b)] += 1
        elif ty == "Dribble":
            f[t]["dribbles"] += 1; f[t]["dribbles_ok"] += e["dribble"].get("outcome", {}).get("name") == "Complete"
        elif ty == "Shot":
            s = e["shot"]; out = s["outcome"]["name"]
            f[t]["shots"] += 1; f[t]["xg"] += s.get("statsbomb_xg", 0); f[t]["sot"] += out in ("Goal", "Saved", "Saved To Post")
            if loc:
                c = cell(*loc); grid["shots"][c] += 1; grid["goals"][c] += out == "Goal"
    for t in teams:
        f[t]["dist_goal"] = sum(dist[t]) / max(len(dist[t]), 1)
    return {"match_id": m["match_id"], "date": m["match_date"], "comp": COMPS[m["competition"]["competition_id"]],
            "home": teams[0], "away": teams[1], "hg": m["home_score"], "ag": m["away_score"], "week": m.get("match_week"),
            "f": {t: dict(v) for t, v in f.items()}, "moves": {t: dict(v) for t, v in moves.items()}, "grid": {k: dict(v) for k, v in grid.items()}}

matches = []
for cid in COMPS:
    matches += get(f"{BASE}/matches/{cid}/27.json")
print(len(matches), "matchs", flush=True)
res = []
with ThreadPoolExecutor(16) as ex:
    for i, r in enumerate(ex.map(resume, matches)):
        res.append(r)
        if i % 200 == 0:
            print(i, flush=True)
pickle.dump(res, open(OUT, "wb"))
print("ok", len(res))
