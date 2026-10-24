"""Thin client for the Elexon Insights stream endpoints.

Stream endpoints return a plain JSON array. Window size limits vary by dataset,
so `fetch_windowed` splits a window in half and retries if the API rejects it.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Callable

import requests

from .config import ELEXON_BASE

FUELHH_PATH = "/datasets/FUELHH/stream"
WINDFOR_PATH = "/datasets/WINDFOR/stream"


class ElexonError(RuntimeError):
    pass


def _get_json(session: requests.Session, path: str, params: dict, retries: int = 3) -> list[dict]:
    url = f"{ELEXON_BASE}{path}"
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, timeout=60, headers={"Accept": "application/json"})
            if r.status_code == 400:
                # Bad window / params: not retryable, caller may split the window.
                raise ElexonError(f"400 from {r.url}: {r.text[:300]}")
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and "data" in data:  # non-stream shape, just in case
                data = data["data"]
            if not isinstance(data, list):
                raise ElexonError(f"Unexpected payload type {type(data)} from {r.url}")
            return data
        except ElexonError:
            raise
        except Exception as e:  # network / 5xx
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise ElexonError(f"Failed after {retries} attempts: {last}")


def fetch_windowed(
    session: requests.Session,
    path: str,
    start: datetime,
    end: datetime,
    build_params: Callable[[datetime, datetime], dict],
    chunk: timedelta,
    min_chunk: timedelta = timedelta(hours=6),
) -> list[dict]:
    """Fetch [start, end) in chunks; halve a chunk if the API rejects it."""
    out: list[dict] = []
    cur = start
    while cur < end:
        nxt = min(cur + chunk, end)
        out.extend(_fetch_with_split(session, path, cur, nxt, build_params, min_chunk))
        cur = nxt
    return out


def _fetch_with_split(session, path, a, b, build_params, min_chunk) -> list[dict]:
    try:
        return _get_json(session, path, build_params(a, b))
    except ElexonError:
        if (b - a) <= min_chunk:
            raise
        mid = a + (b - a) / 2
        return _fetch_with_split(session, path, a, mid, build_params, min_chunk) + \
               _fetch_with_split(session, path, mid, b, build_params, min_chunk)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


# Parameter names confirmed against the Elexon API docs (Swagger "Parameters" tables):
#   FUELHH/stream: publishDateTimeFrom/To, settlementDateFrom/To, settlementPeriod[], fuelType[]
#   WINDFOR/stream: publishDateTimeFrom/To
# Response fields: FUELHH {dataset, publishTime, startTime, settlementDate, settlementPeriod,
# fuelType, generation}; WINDFOR {dataset, publishTime, startTime, generation}.

def fetch_actual_wind(session, start: datetime, end: datetime) -> list[dict]:
    """FUELHH half-hourly outturn, WIND only, filtered by settlement date."""
    def params(a, b):
        return {
            "settlementDateFrom": a.strftime("%Y-%m-%d"),
            "settlementDateTo": (b - timedelta(seconds=1)).strftime("%Y-%m-%d"),
            "fuelType": "WIND",
        }
    rows = fetch_windowed(session, FUELHH_PATH, start, end, params,
                          chunk=timedelta(days=7), min_chunk=timedelta(days=1))
    # Defensive client-side filter in case the server ignores the fuelType filter.
    return [r for r in rows if str(r.get("fuelType", "WIND")).upper() == "WIND"]


def fetch_wind_forecasts(session, publish_from: datetime, publish_to: datetime) -> list[dict]:
    """WINDFOR: every forecast revision published within the window."""
    def params(a, b):
        return {"publishDateTimeFrom": _iso(a), "publishDateTimeTo": _iso(b)}
    return fetch_windowed(session, WINDFOR_PATH, publish_from, publish_to, params,
                          chunk=timedelta(days=3), min_chunk=timedelta(hours=6))
