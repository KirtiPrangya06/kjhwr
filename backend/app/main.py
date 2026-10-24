from __future__ import annotations

from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import config, core

app = FastAPI(title="Wind Forecast Decision Portal API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def _data():
    try:
        return core.load_forecasts(), core.load_actuals()
    except FileNotFoundError:
        raise HTTPException(503, "Data files missing. Run `python -m app.ingest` first.")


def _check_cutoff(cutoff: str) -> str:
    try:
        core.parse_cutoff(cutoff)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return cutoff


def _check_range(start: date | None, end: date | None):
    if start and end and start > end:
        raise HTTPException(422, "start must be <= end")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def get_config():
    return {
        "window_start": config.WINDOW_START.isoformat(),
        "window_end": config.WINDOW_END.isoformat(),
        "default_cutoff": config.DEFAULT_CUTOFF,
        "timezone": "Europe/London",
        "sign_convention": "error = forecast - actual; positive = over-forecast (buyer short)",
    }


@app.get("/api/forecast")
def forecast(delivery_date: date, cutoff: str = config.DEFAULT_CUTOFF):
    """Latest forecast available at the day-ahead cutoff, vs actual (where known)."""
    _check_cutoff(cutoff)
    if not (config.WINDOW_START <= delivery_date <= config.WINDOW_END):
        raise HTTPException(422, f"delivery_date must be within {config.WINDOW_START}..{config.WINDOW_END}")
    fc, act = _data()
    # Build the whole month so the bias estimate can use earlier delivery days.
    month = core.add_bias_adjustment(
        core.decision_view(fc, act, cutoff, config.WINDOW_START, config.WINDOW_END))
    v = month[month["delivery_date"] == delivery_date]
    bias_est = v["bias_est"].dropna() if "bias_est" in v else v["forecast"].iloc[0:0]
    return {
        "delivery_date": delivery_date.isoformat(),
        "cutoff": cutoff,
        "cutoff_utc": core.cutoff_ts(delivery_date, cutoff).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latest_publish_time": (v["publishTime"].max().strftime("%Y-%m-%dT%H:%M:%SZ") if len(v) else None),
        "points": core.to_records(v, ["startTime", "publishTime", "horizon_h", "forecast", "forecast_adj", "actual", "error"]),
        "summary": core.summarize(v),
        "bias_estimate_mw": float(bias_est.iloc[0]) if len(bias_est) else None,
    }


@app.get("/api/metrics")
def metrics(start: date = config.WINDOW_START, end: date = config.WINDOW_END,
            cutoff: str = config.DEFAULT_CUTOFF):
    """Accuracy of the decision-time forecast over a range of delivery days."""
    _check_cutoff(cutoff)
    _check_range(start, end)
    fc, act = _data()
    v = core.decision_view(fc, act, cutoff, start, end)
    full = core.add_bias_adjustment(core.decision_view(fc, act, cutoff, config.WINDOW_START, config.WINDOW_END))
    adjusted = core.summarize_adjusted(full[(full["delivery_date"] >= start) & (full["delivery_date"] <= end)])
    hour_local = v["startTime"].dt.tz_convert(config.TZ).dt.hour if len(v) else v["startTime"]
    return {
        "cutoff": cutoff,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "overall": core.summarize(v),
        "bias_adjusted": adjusted,
        "by_day": core.by_group(v, v["delivery_date"], "delivery_date") if len(v) else [],
        "by_hour": core.by_group(v, hour_local, "hour") if len(v) else [],
    }


@app.get("/api/horizon")
def horizon(start: date = config.WINDOW_START, end: date = config.WINDOW_END):
    """Error as a function of forecast age, across all published revisions."""
    _check_range(start, end)
    fc, act = _data()
    return {"start": start.isoformat(), "end": end.isoformat(),
            "buckets": core.horizon_profile(fc, act, start, end)}


@app.get("/api/cutoff-sensitivity")
def cutoff_sensitivity(start: date = config.WINDOW_START, end: date = config.WINDOW_END):
    """Overall error for a range of candidate cutoffs, so the buyer sees what timing costs."""
    _check_range(start, end)
    fc, act = _data()
    rows = []
    for hh in (6, 8, 9, 10, 12, 15, 18, 21):
        c = f"{hh:02d}:00"
        s = core.summarize(core.decision_view(fc, act, c, start, end))
        rows.append({"cutoff": c, **s})
    return {"start": start.isoformat(), "end": end.isoformat(), "rows": rows}
