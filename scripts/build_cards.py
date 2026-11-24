"""Pick the 54 base cards (3 per club, spread of positions) and write cards.js."""
import csv, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CODES = {"Collingwood":"CW","Brisbane Lions":"BL","Geelong":"GE","Carlton":"CA","Greater Western Sydney":"GW","North Melbourne":"NM","Fremantle":"FR","Essendon":"ES","Hawthorn":"HW","St Kilda":"SK","Adelaide":"AD","Gold Coast":"GC","Sydney":"SY","Melbourne":"ME","Richmond":"RI","Port Adelaide":"PA","West Coast":"WC","Western Bulldogs":"WB"}
rows = list(csv.DictReader(open(ROOT/"data"/"players_base_2026.csv", encoding="utf-8")))
cols = [c for c in rows[0].keys() if c not in ("player","team","group","overall","gem")]
def nice(n):
    last,_,first = n.partition(", "); return first.strip(), last.strip()
def img(first,last):
    b = f"{re.sub('[^a-z]','',last.lower())}-{first.lower()}"
    for ext in (".png",".jpg"):
        if (ROOT/"assets"/"players"/(b+ext)).exists(): return b+ext
    return ""
# 2026 trade/free-agency moves for players in the data
MOVED = {"Neale, Lachie":"Collingwood","Hogan, Jesse":"Collingwood","Greene, Toby":"Geelong","Butters, Zak":"Western Bulldogs"}
EXCLUDE = {"Stringer, Jake"}   # delisted, no club yet
by = {}
for r in rows:
    if r["player"] in EXCLUDE: continue
    r["team"] = MOVED.get(r["player"], r["team"])
    first,last = nice(r["player"]); r["first"],r["last"] = first,last; r["img"] = img(first,last); r["o"] = int(r["overall"])
    by.setdefault(r["team"],[]).append(r)
teams = sorted(by, key=lambda t: CODES[t])
def best(t,pos): return sorted([r for r in by[t] if r["group"]==pos], key=lambda r:-r["o"])
# ruck teams: Richmond + the 5 with the best ruck
others = sorted([t for t in teams if t!="Richmond" and best(t,"RUC")], key=lambda t:-best(t,"RUC")[0]["o"])[:5]
ruck_teams = ["Richmond"]+others
picked, taken = [], set()
def choose(t,pos,i):
    c = [r for r in best(t,pos) if r["player"] not in taken]
    ph = [r for r in c[:8] if r["img"]]
    r = ph[0] if ph else c[:3][i % min(3,len(c))]
    taken.add(r["player"]); picked.append((t,pos,r))
for i,t in enumerate(teams):
    choose(t,"MID",i)
    if t in ruck_teams:
        choose(t,"RUC",i); choose(t,"DEF" if i%2==0 else "FWD",i+1)
    else:
        choose(t,"DEF",i+1); choose(t,"FWD",i+2)
cards = [[r["first"]+" "+r["last"], CODES[t], pos, r["o"], [int(r[c]) for c in cols], r["img"]] for t,pos,r in picked]
cards.sort(key=lambda c:-c[3])
Path(ROOT/"cards.js").write_text("window.ST="+json.dumps(cols)+";\nwindow.CARDS="+json.dumps(cards,ensure_ascii=False)+";\n", encoding="utf-8")
from collections import Counter
print(len(cards), Counter(c[2] for c in cards), Counter(c[1] for c in cards).most_common(2), "photos", sum(1 for c in cards if c[5]))
print([c[0]+" "+str(c[3]) for c in cards[:6]], [c[0] for c in cards if c[5]])
