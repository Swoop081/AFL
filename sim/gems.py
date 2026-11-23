"""Base roster: every AFL player with overall, gem tier and the full 23-stat sheet."""
import csv
from collections import Counter, defaultdict
from pathlib import Path
DATA = Path(__file__).resolve().parent.parent / "data"

# (gem, min overall, colour)
GEMS = [("Diamond", 90, "#9ee7ff"), ("Ruby", 85, "#e0263f"), ("Amethyst", 80, "#a855f7"),
        ("Sapphire", 75, "#2f6df0"), ("Emerald", 70, "#1fb86a"), ("Topaz", 65, "#f2a516"),
        ("Quartz", 0, "#b9c2cc")]

def gem_of(o):
    for name, lo, _ in GEMS:
        if o >= lo:
            return name

def build():
    rt = {r["player"]: r for r in csv.DictReader(open(DATA / "ratings_2026.csv"))}
    st = {r["player"]: r for r in csv.DictReader(open(DATA / "player_stats_2026.csv"))}
    stat_cols = [c for c in next(iter(st.values())).keys() if c not in ("player", "team")]
    rows = []
    for name, r in rt.items():
        o = int(r["overall"])
        rows.append({"player": name, "team": r["team"], "group": r["group"], "overall": o, "gem": gem_of(o),
                     **{c: st[name][c] for c in stat_cols}})
    rows.sort(key=lambda x: (-x["overall"], x["player"]))
    return rows, stat_cols

if __name__ == "__main__":
    rows, cols = build()
    out = DATA / "players_base_2026.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["player", "team", "group", "overall", "gem"] + cols)
        w.writeheader(); w.writerows(rows)
    print(out, len(rows), "players")
    c = Counter(r["gem"] for r in rows)
    for name, lo, _ in GEMS:
        ex = [r["player"].split(", ")[1][0] + ". " + r["player"].split(", ")[0] for r in rows if r["gem"] == name][:3]
        print(f"{name:<9} {lo:>2}+  {c[name]:>3} players   e.g. {', '.join(ex)}")
    print("\nPer club (Diamond/Ruby/Amethyst/Sapphire/Emerald/Topaz/Quartz):")
    per = defaultdict(Counter)
    for r in rows: per[r["team"]][r["gem"]] += 1
    for t, cc in sorted(per.items()):
        print(f"  {t:<24}" + " ".join(f"{cc[g[0]]:>3}" for g in GEMS) + f"   ({sum(cc.values())})")
