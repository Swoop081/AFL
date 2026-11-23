"""Read the 2026 fixture and results from the saved AFL Tables page."""
import re
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "seas_2026.html"

TEAMS = ["Adelaide", "Brisbane Lions", "Carlton", "Collingwood", "Essendon", "Fremantle",
         "Geelong", "Gold Coast", "Greater Western Sydney", "Hawthorn", "Melbourne",
         "North Melbourne", "Port Adelaide", "Richmond", "St Kilda", "Sydney",
         "West Coast", "Western Bulldogs"]

def load_games():
    html = RAW.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text)
    team_re = "|".join(sorted(map(re.escape, TEAMS), key=len, reverse=True))
    # Team q1 q2 q3 final total
    side = rf"({team_re}) (\d+\.\d+) (\d+\.\d+) (\d+\.\d+) (\d+)\.(\d+) (\d+)"
    pat = re.compile(
        rf"{side} (\w{{3}} \d\d-\w{{3}}-\d{{4}}).*?Venue: ([^\[]*?) {side}")
    # split into round sections
    games = []
    parts = re.split(r"(Round \d+|Qualifying Final|Elimination Final|Semi Final|Preliminary Final|Grand Final)(?= \*| Rnd| Tot|\s)", text)
    label = None
    for chunk in parts:
        if re.fullmatch(r"Round \d+|Qualifying Final|Elimination Final|Semi Final|Preliminary Final|Grand Final", chunk or ""):
            label = chunk
            continue
        if label is None:
            continue
        for m in pat.finditer(chunk):
            g = m.groups()
            games.append({
                "round": label,
                "home": g[0], "home_goals": int(g[4]), "home_behinds": int(g[5]), "home_pts": int(g[6]),
                "date": g[7], "venue": g[8].strip(),
                "away": g[9], "away_goals": int(g[13]), "away_behinds": int(g[14]), "away_pts": int(g[15]),
            })
    return games

if __name__ == "__main__":
    g = load_games()
    print(len(g), "games")
    hm = [x for x in g if x["round"].startswith("Round")]
    print(len(hm), "home-and-away,", len(g) - len(hm), "finals")
    for x in g[:2] + g[-2:]:
        print(x)
