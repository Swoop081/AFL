"""Full stat sheet (22 stats, 35-99) for every player, from real per-game numbers.

Each stat is a percentile against every regular player in the league (so a defender's
Scoring is honestly low). 2026 is blended with 2025, and low-sample players are pulled
toward the league average.
"""
import csv
from pathlib import Path
from ratings import DATA, CODES, num, read, W26

# (label, group, kind, spec)   kind "pg": per game of a column; "ratio": a/(a+b); "inv": lower is better
STATS = [
    ("Kicking", "Ball use", "pg", "KI"), ("Handball", "Ball use", "pg", "HB"),
    ("Disposal", "Ball use", "pg", "DI"), ("Ball security", "Ball use", "inv_ratio", ("CG", "DI")),
    ("Contested", "Ball winning", "pg", "CP"), ("Uncontested", "Ball winning", "pg", "UP"),
    ("Clearance", "Ball winning", "pg", "CL"), ("Hit-out", "Ball winning", "pg", "HO"),
    ("Inside 50", "Attack", "pg", "IF"), ("Scoring", "Attack", "pg", "GL"),
    ("Accuracy", "Attack", "ratio", ("GL", "BH")), ("Assist", "Attack", "pg", "GA"),
    ("Forward mark", "Attack", "pg", "MI"), ("Run", "Attack", "pg", "BO"),
    ("Marking", "Marking", "pg", "MK"), ("Contested mark", "Marking", "pg", "CM"),
    ("Tackling", "Defence", "pg", "TK"), ("Spoil", "Defence", "pg", "1%"),
    ("Rebound", "Defence", "pg", "RB"), ("Discipline", "Other", "inv_pg", "FA"),
    ("Wins frees", "Other", "pg", "FF"), ("Match winner", "Other", "pg", "BR"),
]
LABELS = [s[0] for s in STATS]
MIN_POOL = 8
PRIOR = 5


def raw(r, kind, spec):
    gm = num(r["GM"])
    if kind == "pg": return num(r[spec]) / gm, gm
    if kind == "inv_pg": return num(r[spec]) / gm, gm
    a, b = num(r[spec[0]]), num(r[spec[1]])
    if kind == "ratio":
        return (a / (a + b) if a + b else 0.0), a + b          # weight = shots
    return (a / b if b else 0.0), b                                # clangers per disposal; weight = disposals


def build():
    d26, d25 = read(DATA / "players_2026_totals.csv"), read(DATA / "players_2025_totals.csv")
    players = []
    for name, r in d26.items():
        p = {"name": name, "team": CODES[r["TM"]], "gm": num(r["GM"]), "v": {}, "w": {}}
        r25 = d25.get(name)
        for label, _, kind, spec in STATS:
            v26, w26 = raw(r, kind, spec)
            if r25 and num(r25["GM"]) > 0:
                v25, w25 = raw(r25, kind, spec)
                a = W26 * min(p["gm"], 12) / 12 + (1 - min(p["gm"], 12) / 12) * 0.35
                v, w = a * v26 + (1 - a) * v25, w26 + 0.5 * w25
            else:
                v, w = v26, w26
            p["v"][label], p["w"][label] = v, w
        players.append(p)
    for label, _, kind, spec in STATS:
        pool = [p for p in players if p["gm"] >= MIN_POOL]
        avg = sum(p["v"][label] for p in pool) / len(pool)
        prior = 10 if kind in ("ratio",) else (40 if kind == "inv_ratio" else PRIOR)
        shrunk = {}
        for p in players:
            w = p["w"][label] / (p["w"][label] + prior)
            shrunk[id(p)] = w * p["v"][label] + (1 - w) * avg
        xs = sorted(shrunk[id(p)] for p in pool)
        for p in players:
            v = shrunk[id(p)]
            pct = sum(1 for x in xs if x <= v) / len(xs)
            if kind.startswith("inv"):
                pct = 1 - sum(1 for x in xs if x < v) / len(xs)
            p.setdefault("s", {})[label] = round(35 + 64 * pct)
    # Durability: share of the season played (2026), capped at 100%
    for p in players:
        p["s"]["Durability"] = round(35 + 64 * min(p["gm"] / 24, 1.0))
    return players


if __name__ == "__main__":
    ps = build()
    out = DATA / "player_stats_2026.csv"
    cols = LABELS + ["Durability"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["player", "team"] + cols)
        for p in sorted(ps, key=lambda p: p["name"]):
            w.writerow([p["name"], p["team"]] + [p["s"][c] for c in cols])
    print(out, len(ps), "players,", len(cols), "stats")
    for n in ["Bontempelli, Marcus", "Nankervis, Toby", "Miller, Ben", "Curnow, Charlie"]:
        p = [p for p in ps if p["name"] == n][0]
        print(f"\n{n} ({p['team']})")
        print("  " + ", ".join(f"{c} {p['s'][c]}" for c in cols))
