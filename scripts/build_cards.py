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
# ---- Foundation set: every club gets one TOP, one MID and one LOW rated player ----
SETS = [{"id":"FND","name":"Foundation Series","scale":0.90}]
SCALE = SETS[0]["scale"]
BUCKET = {"top":(82,99,88),"mid":(66,81,73),"low":(0,65,57)}   # real-rating range + target
ORDER = [["top","mid","low"],["mid","low","top"],["low","top","mid"]]
picked, taken = [], set()
def pick(t,pos,bucket):
    lo,hi,tg = BUCKET[bucket]
    c = [r for r in by[t] if r["group"]==pos and r["player"] not in taken]
    inb = [r for r in c if lo<=r["o"]<=hi]
    pool = inb or sorted(c,key=lambda r:abs(r["o"]-tg))[:3]
    ph = [r for r in pool if r["img"]]
    r = (ph or sorted(pool,key=lambda r:abs(r["o"]-tg)))[0] if not inb else (ph[0] if ph else sorted(pool,key=lambda r:abs(r["o"]-tg))[0])
    taken.add(r["player"]); return r
def bucket_of(o): return "top" if o>=82 else "mid" if o>=66 else "low"
for i,t in enumerate(teams):
    slots = ["MID","RUC","DEF" if i%2==0 else "FWD"] if t in ruck_teams else ["MID","DEF","FWD"]
    need = ORDER[i%3][:]; chosen = {}
    # photo players first: they fix their own bucket
    for pos in slots:
        ph = [r for r in best(t,pos)[:10] if r["img"] and r["player"] not in taken]
        if ph and len(chosen) < len(slots)-1:
            r = ph[0]; taken.add(r["player"]); bk = bucket_of(r["o"]); need.remove(bk if bk in need else need[0]); chosen[pos] = r
    for pos in slots:
        if pos in chosen: continue
        bk = need.pop(0) if need else "mid"
        chosen[pos] = pick(t,pos,bk)
    for pos in slots: picked.append((t,pos,chosen[pos]))
sc = lambda v: max(20,min(99,round(int(v)*SCALE)))
cards = [[r["first"]+" "+r["last"], CODES[t], pos, sc(r["o"]), [sc(r[c]) for c in cols], r["img"], "FND"] for t,pos,r in picked]
cards.sort(key=lambda c:-c[3])
Path(ROOT/"cards.js").write_text("window.ST="+json.dumps(cols)+";\nwindow.SETS="+json.dumps(SETS)+";\nwindow.CARDS="+json.dumps(cards,ensure_ascii=False)+";\n", encoding="utf-8")
from collections import Counter
print(len(cards), Counter(c[2] for c in cards), Counter(c[1] for c in cards).most_common(2), "photos", sum(1 for c in cards if c[5]))
print("ovr bands", {k:sum(1 for c in cards if lo<=c[3]<=hi) for k,(lo,hi) in {"80+":(80,99),"70-79":(70,79),"60-69":(60,69),"<60":(0,59)}.items()}, "max",cards[0][3],"min",cards[-1][3])
print("photos:",[c[0]+" "+str(c[3]) for c in cards if c[5]])
print("RUC:",[c[0]+" "+str(c[3]) for c in cards if c[2]=="RUC"])
