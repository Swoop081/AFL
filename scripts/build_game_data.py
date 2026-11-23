"""Write players.js (every AFL player: name, club code, position group, overall, 23 stats) for the game."""
import csv, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CODES = {"Collingwood":"CW","Brisbane Lions":"BL","Geelong":"GE","Carlton":"CA","Greater Western Sydney":"GW",
 "North Melbourne":"NM","Fremantle":"FR","Essendon":"ES","Hawthorn":"HW","St Kilda":"SK","Adelaide":"AD",
 "Gold Coast":"GC","Sydney":"SY","Melbourne":"ME","Richmond":"RI","Port Adelaide":"PA","West Coast":"WC","Western Bulldogs":"WB"}
rows = list(csv.DictReader(open(ROOT / "data" / "players_base_2026.csv", encoding="utf-8")))
stat_cols = [c for c in rows[0].keys() if c not in ("player", "team", "group", "overall", "gem")]
def nice(n):
    last, _, first = n.partition(", ")
    return f"{first} {last}".strip()
pl = [[nice(r["player"]), CODES[r["team"]], r["group"], int(r["overall"]), [int(r[c]) for c in stat_cols]] for r in rows]
(ROOT / "players.js").write_text("window.ST=" + json.dumps(stat_cols) + ";\nwindow.PL=" + json.dumps(pl, separators=(",", ":")) + ";\n")
print(len(pl), "players,", len(stat_cols), "stats:", stat_cols)
