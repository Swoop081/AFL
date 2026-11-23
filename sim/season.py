"""AFL season simulator.

Player 2026 stats -> impact per game -> team strength -> match margins.
Run:  python3 sim/season.py            (backtest + one season + premiership odds)
"""
import csv
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import load_games, TEAMS

DATA = Path(__file__).resolve().parent.parent / "data"
CODES = {"CW": "Collingwood", "BL": "Brisbane Lions", "GE": "Geelong", "CA": "Carlton",
         "GW": "Greater Western Sydney", "NM": "North Melbourne", "FR": "Fremantle",
         "ES": "Essendon", "HW": "Hawthorn", "SK": "St Kilda", "AD": "Adelaide",
         "GC": "Gold Coast", "SY": "Sydney", "ME": "Melbourne", "RI": "Richmond",
         "PA": "Port Adelaide", "WC": "West Coast", "WB": "Western Bulldogs"}

# Weights: how much each per-game stat is worth, in rough "impact points".
W = {"DI": 0.30, "CP": 0.35, "CL": 0.70, "IF": 0.50, "TK": 0.50, "MK": 0.35, "CM": 0.90,
     "GL": 6.0, "GA": 1.0, "RB": 0.80, "MI": 0.90, "HO": 0.35, "1%": 0.30, "CG": -0.50}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def load_players(path):
    players = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            gm = num(r["GM"])
            if gm <= 0 or r["TM"] not in CODES:
                continue
            imp = sum(W[k] * num(r[k]) for k in W) / gm
            players.append({"name": r["Player"], "team": CODES[r["TM"]], "gm": gm, "imp": imp})
    return players


def team_strengths(players, top=22):
    by = defaultdict(list)
    for p in players:
        by[p["team"]].append(p)
    out = {}
    for t, ps in by.items():
        # Weight impact by how much of the season the player was available (caps at 22 games).
        ps = sorted(ps, key=lambda p: p["imp"] * min(p["gm"], 22) / 22, reverse=True)[:top]
        out[t] = sum(p["imp"] * min(p["gm"], 22) / 22 for p in ps)
    return out


def fit_margin_model(games, strength):
    """margin = k * (home - away strength) + home_adv, least squares."""
    xs = [strength[g["home"]] - strength[g["away"]] for g in games]
    ys = [g["home_pts"] - g["away_pts"] for g in games]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    k = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    ha = my - k * mx
    res = [y - (k * x + ha) for x, y in zip(xs, ys)]
    sd = math.sqrt(sum(r * r for r in res) / n)
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - sum(r * r for r in res) / ss_tot
    return k, ha, sd, r2


def ladder_from(results):
    t = {x: {"P": 0, "W": 0, "L": 0, "D": 0, "pts": 0, "F": 0, "A": 0} for x in TEAMS}
    for h, a, hp, ap in results:
        for me, you, mp, yp in ((h, a, hp, ap), (a, h, ap, hp)):
            r = t[me]
            r["P"] += 1; r["F"] += mp; r["A"] += yp
            if mp > yp: r["W"] += 1; r["pts"] += 4
            elif mp == yp: r["D"] += 1; r["pts"] += 2
            else: r["L"] += 1
    rows = sorted(t.items(), key=lambda kv: (-kv[1]["pts"], -(kv[1]["F"] / max(kv[1]["A"], 1))))
    return rows


class Model:
    def __init__(self, strength, k, ha, sd, avg_total=187.0, total_sd=28.0):
        self.s, self.k, self.ha, self.sd = strength, k, ha, sd
        self.avg_total, self.total_sd = avg_total, total_sd

    def play(self, home, away, rng, neutral=False):
        mu = self.k * (self.s[home] - self.s[away]) + (0 if neutral else self.ha)
        margin = round(rng.gauss(mu, self.sd))
        total = max(100, round(rng.gauss(self.avg_total, self.total_sd)))
        hp = round((total + margin) / 2)
        ap = total - hp
        return hp, ap


def play_finals(top8, model, rng):
    """Standard AFL top-8 finals. Returns (premier, finals results list)."""
    log = []

    def game(name, a, b):
        hp, ap = model.play(a, b, rng, neutral=True)
        while hp == ap:
            hp, ap = model.play(a, b, rng, neutral=True)
        w, l = (a, b) if hp > ap else (b, a)
        log.append((name, a, hp, b, ap, w))
        return w, l

    q1w, q1l = game("Qualifying Final", top8[0], top8[3])
    q2w, q2l = game("Qualifying Final", top8[1], top8[2])
    e1w, _ = game("Elimination Final", top8[4], top8[7])
    e2w, _ = game("Elimination Final", top8[5], top8[6])
    s1w, _ = game("Semi Final", q1l, e2w)
    s2w, _ = game("Semi Final", q2l, e1w)
    p1w, _ = game("Preliminary Final", q1w, s2w)
    p2w, _ = game("Preliminary Final", q2w, s1w)
    pw, _ = game("Grand Final", p1w, p2w)
    return pw, log


def simulate_season(fixture, model, rng):
    results = []
    for g in fixture:
        hp, ap = model.play(g["home"], g["away"], rng)
        results.append((g["home"], g["away"], hp, ap))
    rows = ladder_from(results)
    top8 = [t for t, _ in rows[:8]]
    premier, finals = play_finals(top8, model, rng)
    return rows, premier, finals, results


def main():
    games = load_games()
    ha_games = [g for g in games if g["round"].startswith("Round")]
    p26 = load_players(DATA / "players_2026_totals.csv")
    s26 = team_strengths(p26)

    # 1) Backtest: do strengths from 2026 stats explain the 2026 results?
    k, ha, sd, r2 = fit_margin_model(ha_games, s26)
    print(f"Backtest on {len(ha_games)} real 2026 games: R2={r2:.2f}, "
          f"1 strength point = {k:.2f} pts margin, home edge {ha:+.1f}, spread {sd:.1f} pts")
    real = ladder_from([(g["home"], g["away"], g["home_pts"], g["away_pts"]) for g in ha_games])
    real_rank = {t: i + 1 for i, (t, _) in enumerate(real)}
    by_strength = sorted(s26, key=s26.get, reverse=True)
    str_rank = {t: i + 1 for i, t in enumerate(by_strength)}
    d2 = sum((real_rank[t] - str_rank[t]) ** 2 for t in TEAMS)
    rho = 1 - 6 * d2 / (18 * (18 ** 2 - 1))
    print(f"Rank agreement between real ladder and team strength: {rho:.2f} (1.00 = identical)\n")

    model = Model(s26, k, ha, sd)

    # 2) One full simulated season (2027 using 2026 stats and the 2026 draw as the template)
    rng = random.Random(2027)
    rows, premier, finals, _ = simulate_season(ha_games, model, rng)
    print("SIMULATED 2027 LADDER (real 2026 ladder rank in brackets)")
    print(f"{'#':>2} {'Team':<24}{'W':>3}{'L':>3}{'D':>3}{'Pts':>4}{'%':>7}")
    for i, (t, r) in enumerate(rows, 1):
        print(f"{i:>2} {t:<24}{r['W']:>3}{r['L']:>3}{r['D']:>3}{r['pts']:>4}{100*r['F']/r['A']:>7.1f}   ({real_rank[t]})")
    print("\nFINALS")
    for name, a, hp, b, ap, w in finals:
        print(f"{name:<18} {a} {hp} v {b} {ap}  -> {w}")
    print(f"\nPREMIERS: {premier}\n")

    # 3) Premiership odds over many seasons
    N = 2000
    flags = defaultdict(int)
    for i in range(N):
        _, prem, _, _ = simulate_season(ha_games, model, random.Random(i))
        flags[prem] += 1
    print(f"PREMIERSHIP ODDS ({N} simulated seasons)")
    for t, c in sorted(flags.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {t:<24}{100*c/N:5.1f}%")

    print("\nTop 10 player ratings (impact per game)")
    for p in sorted(p26, key=lambda p: p["imp"], reverse=True)[:10]:
        if p["gm"] >= 8:
            print(f"  {p['name']:<22}{p['team']:<24}{p['imp']:.1f}")


if __name__ == "__main__":
    main()
