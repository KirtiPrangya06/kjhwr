"""Central configuration. Everything tunable lives here or in env vars."""
import os
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
ACTUALS_CSV = DATA_DIR / "actuals.csv"
FORECASTS_CSV = DATA_DIR / "forecasts.csv"

# Elexon Insights API (open, no key required)
ELEXON_BASE = os.getenv("ELEXON_BASE", "https://data.elexon.co.uk/bmrs/api/v1")

# Scope of the challenge: purchase decisions for delivery days in January 2026
WINDOW_START = date(2026, 1, 1)
WINDOW_END = date(2026, 1, 31)

# Market-local timezone. The day-ahead decision is made in UK local time.
TZ = ZoneInfo("Europe/London")

# Day-ahead decision cutoff, as UK local time on D-1 ("HH:MM").
# ASSUMPTION: the exact gate closure should be confirmed against the exchange
# rules (EPEX / N2EX). It is a query parameter everywhere so the client can change it.
DEFAULT_CUTOFF = os.getenv("DEFAULT_CUTOFF", "09:00")

# Forecast-horizon buckets (hours between publishTime and startTime)
HORIZON_BINS_H = [0, 3, 6, 12, 18, 24, 30, 36, 48, 72, 10_000]
