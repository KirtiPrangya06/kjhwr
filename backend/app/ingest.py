"""Download January 2026 wind actuals + forecasts from Elexon into data/*.csv.

    python -m app.ingest            # defaults to the challenge window
"""
from __future__ import annotations

import argparse
from datetime import datetime, time, timedelta, timezone

import pandas as pd
import requests

from . import config, elexon


def _utc(d, t=time(0, 0)):
    return datetime.combine(d, t, tzinfo=timezone.utc)


def run(lookback_days: int = 7) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    start = _utc(config.WINDOW_START)
    end = _utc(config.WINDOW_END + timedelta(days=1))

    with requests.Session() as s:
        print(f"Fetching FUELHH WIND {start:%F} -> {end:%F} ...")
        actual_rows = elexon.fetch_actual_wind(s, start, end)
        # Forecasts for early-January targets are published in late December, and
        # we keep revisions up to the end of the window for horizon analysis.
        print("Fetching WINDFOR revisions ...")
        fc_rows = elexon.fetch_wind_forecasts(s, start - timedelta(days=lookback_days), end)

    act = pd.DataFrame(actual_rows)
    fc = pd.DataFrame(fc_rows)
    if act.empty or fc.empty:
        raise SystemExit("No data returned. Run scripts/probe_elexon.py to inspect the API.")

    if "publishTime" in act:  # keep the most recent outturn value per half-hour
        act = act.sort_values("publishTime")
    act = act[["startTime", "generation"]].copy()
    act["startTime"] = pd.to_datetime(act["startTime"], utc=True)
    act = (act.drop_duplicates("startTime", keep="last").sort_values("startTime")
              .query("@start <= startTime < @end"))

    fc = fc[["publishTime", "startTime", "generation"]].copy()
    fc["publishTime"] = pd.to_datetime(fc["publishTime"], utc=True)
    fc["startTime"] = pd.to_datetime(fc["startTime"], utc=True)
    fc = (fc.drop_duplicates(["publishTime", "startTime"])
            .sort_values(["startTime", "publishTime"])
            .query("@start <= startTime < @end"))

    act.to_csv(config.ACTUALS_CSV, index=False)
    fc.to_csv(config.FORECASTS_CSV, index=False)
    print(f"actuals: {len(act)} rows -> {config.ACTUALS_CSV}")
    print(f"forecasts: {len(fc)} rows -> {config.FORECASTS_CSV}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback-days", type=int, default=7)
    run(ap.parse_args().lookback_days)
