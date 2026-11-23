"""Turn the raw AFL Tables pages into CSV files."""
import io
import sys
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
OUT = Path("data")


def tables(path):
    return pd.read_html(io.StringIO(path.read_text(encoding="utf-8", errors="ignore")))


def flat(df):
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[-1]) for c in df.columns]
    df.columns = [str(c).strip() for c in df.columns]
    return df


def player_totals(name, out):
    path = RAW / name
    if not path.exists():
        print("missing", name)
        return
    found = [flat(t) for t in tables(path)]
    found = [t for t in found if "Player" in t.columns and "GM" in t.columns]
    if not found:
        print("no player table in", name)
        return
    df = found[0]
    df.to_csv(OUT / out, index=False)
    print(out, len(df), "rows", list(df.columns))


def club_lists(name, out):
    """stats/2026.html has one player table per club."""
    path = RAW / name
    if not path.exists():
        print("missing", name)
        return
    rows = []
    for t in tables(path):
        t = flat(t)
        if "Player" in t.columns and "GM" in t.columns:
            rows.append(t)
    if rows:
        pd.concat(rows, ignore_index=True).to_csv(OUT / out, index=False)
        print(out, sum(len(r) for r in rows), "rows in", len(rows), "tables")


player_totals("stats_2026a.html", "players_2026_totals.csv")
player_totals("stats_2025a.html", "players_2025_totals.csv")
club_lists("stats_2026.html", "club_lists_2026_raw.csv")
