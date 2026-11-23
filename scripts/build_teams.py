"""Build teams.js (club info, 2026 record, best 3 players) for the front end."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sim"))
from fixtures import load_games
from season import load_players, ladder_from, CODES, DATA

COLOURS = {  # primary, secondary, text-on-primary
 "AD": ("#002B5C", "#E21937", "#FFD200"), "BL": ("#7C0A2A", "#0055A3", "#FDBE57"),
 "CA": ("#031A29", "#0E1E2D", "#FFFFFF"), "CW": ("#111111", "#333333", "#FFFFFF"),
 "ES": ("#111111", "#CC2031", "#FFFFFF"), "FR": ("#2A0D54", "#4B2A86", "#FFFFFF"),
 "GE": ("#1C3C63", "#FFFFFF", "#FFFFFF"), "GC": ("#D93E39", "#FFCC00", "#FFFFFF"),
 "GW": ("#F15C22", "#4A4A4A", "#FFFFFF"), "HW": ("#4D2004", "#FBBF15", "#FBBF15"),
 "ME": ("#0F1131", "#CC2031", "#FFFFFF"), "NM": ("#013B9F", "#FFFFFF", "#FFFFFF"),
 "PA": ("#008AAB", "#000000", "#FFFFFF"), "RI": ("#FFD200", "#111111", "#111111"),
 "SK": ("#ED0F05", "#111111", "#FFFFFF"), "SY": ("#ED171F", "#FFFFFF", "#FFFFFF"),
 "WC": ("#062EE2", "#F2A900", "#F2A900"), "WB": ("#014896", "#E21937", "#FFFFFF"),
}
NICK = {"AD":"Crows","BL":"Lions","CA":"Blues","CW":"Magpies","ES":"Bombers","FR":"Dockers",
 "GE":"Cats","GC":"Suns","GW":"Giants","HW":"Hawks","ME":"Demons","NM":"Kangaroos",
 "PA":"Power","RI":"Tigers","SK":"Saints","SY":"Swans","WC":"Eagles","WB":"Bulldogs"}

def short(n):
    last, _, first = n.partition(", ")
    return f"{first[:1]}. {last}" if first else n

games = [g for g in load_games() if g["round"].startswith("Round")]
rows = ladder_from([(g["home"], g["away"], g["home_pts"], g["away_pts"]) for g in games])
rec = {t: (i + 1, r["W"], r["L"], r["D"]) for i, (t, r) in enumerate(rows)}
players = load_players(DATA / "players_2026_totals.csv")
out = []
for code, name in sorted(CODES.items(), key=lambda kv: kv[1]):
    best = sorted([p for p in players if p["team"] == name and p["gm"] >= 8],
                  key=lambda p: p["imp"], reverse=True)[:3]
    pos, w, l, d = rec[name]
    p, s, t = COLOURS[code]
    out.append({"code": code, "name": name, "nick": NICK[code], "primary": p, "secondary": s,
                "accent": t, "rank": pos, "w": w, "l": l, "d": d,
                "stars": [short(b["name"]) for b in best]})
(ROOT / "teams.js").write_text("window.TEAMS = " + json.dumps(out, indent=1) + ";\n")
print(len(out), "clubs written")
