"""Rate every player 40-99 from real stats, inside their position group.

Card stats (3 per group):
  Defence : Spoil (1%), Mark (MK), Rebound (RB)
  Midfield: Gather (CP), Clearance (CL), Drive (IF)
  Forward : Lead (MI), Mark in front (CM), Finish (GL)
  Ruck    : Tap (HO), Follow-up (CL), Pressure (TK)
Per-game values: 70% 2026 + 30% 2025, pulled toward the group average for players with few games.
"""
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
CODES = {"CW": "Collingwood", "BL": "Brisbane Lions", "GE": "Geelong", "CA": "Carlton",
         "GW": "Greater Western Sydney", "NM": "North Melbourne", "FR": "Fremantle",
         "ES": "Essendon", "HW": "Hawthorn", "SK": "St Kilda", "AD": "Adelaide",
         "GC": "Gold Coast", "SY": "Sydney", "ME": "Melbourne", "RI": "Richmond",
         "PA": "Port Adelaide", "WC": "West Coast", "WB": "Western Bulldogs"}
STATS = {
    "DEF": [("Spoil", "1%"), ("Mark", "MK"), ("Rebound", "RB")],
    "MID": [("Gather", "CP"), ("Clearance", "CL"), ("Drive", "IF")],
    "FWD": [("Lead", "MI"), ("Mark in front", "CM"), ("Finish", "GL")],
    "RUC": [("Tap", "HO"), ("Follow-up", "CL"), ("Pressure", "TK")],
}
FANTASY = {"KI": 3, "HB": 2, "MK": 3, "TK": 4, "HO": 1, "FF": 1, "FA": -3, "GL": 6, "BH": 1}  # AFL Fantasy scoring
FANTASY_WEIGHT = 0.5  # overall = half Fantasy average, half the position stats
PRIOR_GAMES = 5      # how strongly low-game players are pulled to the group average
MIN_POOL_GAMES = 8   # who counts when building the percentile scale
W26 = 0.7


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["Player"]: r for r in csv.DictReader(f) if r["TM"] in CODES and num(r["GM"]) > 0}


def group_of(r):
    gm = num(r["GM"])
    g = lambda k: num(r[k]) / gm
    if g("HO") > 5: return "RUC"
    if g("CL") >= 3.5 or g("DI") >= 20: return "MID"
    if g("GL") >= 0.55: return "FWD"
    if g("RB") >= 1.5: return "DEF"
    return "MID"


def blended(r26, r25, key):
    v26 = num(r26[key]) / num(r26["GM"])
    if r25 and num(r25["GM"]) > 0:
        v25 = num(r25[key]) / num(r25["GM"])
        g26, g25 = num(r26["GM"]), num(r25["GM"])
        w26 = W26 * min(g26, 12) / 12 + (1 - min(g26, 12) / 12) * 0.35   # lean on 2025 if 2026 had few games
        v = w26 * v26 + (1 - w26) * v25
        games = g26 + 0.5 * g25
    else:
        v, games = v26, num(r26["GM"])
    return v, games


CURVE = [(0.0, 42), (0.25, 55), (0.5, 64), (0.75, 74), (0.9, 84), (0.97, 91), (1.0, 99)]


def curve(q):
    for (q0, o0), (q1, o1) in zip(CURVE, CURVE[1:]):
        if q <= q1:
            return round(o0 + (o1 - o0) * (q - q0) / (q1 - q0))
    return 99


def rate():
    d26, d25 = read(DATA / "players_2026_totals.csv"), read(DATA / "players_2025_totals.csv")
    rows = []
    for name, r in d26.items():
        grp = group_of(r)
        vals = {}
        games = 0
        for label, key in STATS[grp]:
            vals[label], games = blended(r, d25.get(name), key)
        fan = sum(w * blended(r, d25.get(name), k)[0] for k, w in FANTASY.items())
        rows.append({"name": name, "team": CODES[r["TM"]], "group": grp, "games": games, "vals": vals, "fan": fan})
    # group averages and percentile scales from regular players
    scale, avg = {}, {}
    for grp, defs in STATS.items():
        pool = [p for p in rows if p["group"] == grp and p["games"] >= MIN_POOL_GAMES]
        for label, _ in defs:
            xs = sorted(p["vals"][label] for p in pool)
            scale[(grp, label)] = xs
            avg[(grp, label)] = sum(xs) / len(xs)
    fscale, favg = {}, {}
    for grp in STATS:
        xs = sorted(p["fan"] for p in rows if p["group"] == grp and p["games"] >= MIN_POOL_GAMES)
        fscale[grp], favg[grp] = xs, sum(xs) / len(xs)
    for p in rows:
        pcts, stars = [], []
        for label, _ in STATS[p["group"]]:
            k = (p["group"], label)
            # pull toward average when games are few
            w = p["games"] / (p["games"] + PRIOR_GAMES)
            v = w * p["vals"][label] + (1 - w) * avg[k]
            xs = scale[k]
            pct = sum(1 for x in xs if x <= v) / len(xs)
            pcts.append(pct)
            stars.append(max(1, min(5, int(pct * 5 - 1e-9) + 1)))
        p["pcts"], p["stars"] = pcts, stars
        wf = p["games"] / (p["games"] + PRIOR_GAMES)
        fv = wf * p["fan"] + (1 - wf) * favg[p["group"]]
        p["fan_pct"] = sum(1 for x in fscale[p["group"]] if x <= fv) / len(fscale[p["group"]])
        p["score"] = (1 - FANTASY_WEIGHT) * sum(pcts) / 3 + FANTASY_WEIGHT * p["fan_pct"]
    # Overall comes from where a player ranks across the whole league (so 90+ stays rare).
    order = sorted(rows, key=lambda p: p["score"])
    n = len(order)
    for i, p in enumerate(order):
        p["overall"] = curve((i + 0.5) / n)
    return rows


def write_csv(rows):
    out = DATA / "ratings_2026.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["player", "team", "group", "overall", "stat1", "stars1", "stat2", "stars2", "stat3", "stars3", "games_weighted"])
        for p in sorted(rows, key=lambda p: -p["overall"]):
            labs = [l for l, _ in STATS[p["group"]]]
            w.writerow([p["name"], p["team"], p["group"], p["overall"],
                        labs[0], p["stars"][0], labs[1], p["stars"][1], labs[2], p["stars"][2], round(p["games"], 1)])
    return out


if __name__ == "__main__":
    from collections import Counter
    rows = rate()
    print(write_csv(rows), len(rows), "players rated\n")
    top = sorted(rows, key=lambda p: -p["overall"])
    print("TOP 20 IN THE LEAGUE")
    for p in top[:20]:
        print(f"{p['overall']:>3} {p['group']} {p['name']:<22}{p['team']:<24}{p['stars']}")
    b = Counter(min(p['overall'] // 10 * 10, 90) for p in rows)
    print("\nspread:", {f"{k}+": b[k] for k in sorted(b, reverse=True)})
    print("\nBY POSITION GROUP (count, best):")
    for g in STATS:
        ps = [p for p in top if p["group"] == g]
        print(f"  {g}: {len(ps)} players, best {ps[0]['name']} {ps[0]['overall']}")
    print("\nRICHMOND TOP 12")
    for p in [p for p in top if p["team"] == "Richmond"][:12]:
        print(f"{p['overall']:>3} {p['group']} {p['name']:<22}{p['stars']}")
