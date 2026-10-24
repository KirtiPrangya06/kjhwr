"""Run this FIRST. Confirms the Elexon endpoints/params/fields match what the app assumes.

    python scripts/probe_elexon.py
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests
from app import elexon

s = requests.Session()
a = datetime(2026, 1, 10, tzinfo=timezone.utc)
b = a + timedelta(days=1)

print("\n== FUELHH (WIND) for 2026-01-10 ==")
rows = elexon.fetch_actual_wind(s, a, b)
print("rows:", len(rows), "(expect 48)")
print("keys:", sorted(rows[0].keys()) if rows else None)
print("sample:", rows[:2])
missing = {"startTime", "generation"} - set(rows[0]) if rows else {"<no rows>"}
print("MISSING FIELDS:", missing or "none")

print("\n== WINDFOR published 2026-01-09 ==")
rows = elexon.fetch_wind_forecasts(s, a - timedelta(days=1), a)
print("rows:", len(rows))
print("keys:", sorted(rows[0].keys()) if rows else None)
print("sample:", rows[:2])
missing = {"startTime", "publishTime", "generation"} - set(rows[0]) if rows else {"<no rows>"}
print("MISSING FIELDS:", missing or "none")
if rows:
    import pandas as pd
    df = pd.DataFrame(rows)
    df["h"] = (pd.to_datetime(df.startTime) - pd.to_datetime(df.publishTime)).dt.total_seconds() / 3600
    print(f"distinct publishTimes: {df.publishTime.nunique()}  horizon range (h): {df.h.min():.1f} .. {df.h.max():.1f}")
    print("target-time step (min):", pd.to_datetime(df.startTime).drop_duplicates().sort_values().diff().dropna().dt.total_seconds().div(60).mode().tolist())
