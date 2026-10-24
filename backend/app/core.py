"""Pure analysis logic: no web framework, no I/O besides CSV loading. Easy to unit-test.

Sign convention (important for a buyer):
    error = forecast - actual
    error > 0  -> OVER-forecast: less wind arrived than expected, buyer is short and
                  must cover the gap in a later (usually pricier) market.
    error < 0  -> UNDER-forecast: more wind than expected, buyer over-bought thermal.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

from . import config


# ---------- loading ----------

@lru_cache(maxsize=1)
def load_actuals() -> pd.DataFrame:
    df = pd.read_csv(config.ACTUALS_CSV, parse_dates=["startTime"])
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return df.rename(columns={"generation": "actual"})


@lru_cache(maxsize=1)
def load_forecasts() -> pd.DataFrame:
    df = pd.read_csv(config.FORECASTS_CSV, parse_dates=["publishTime", "startTime"])
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return df.rename(columns={"generation": "forecast"})


def clear_cache() -> None:
    load_actuals.cache_clear()
    load_forecasts.cache_clear()


# ---------- decision-time logic ----------

def parse_cutoff(cutoff: str) -> time:
    try:
        hh, mm = cutoff.split(":")
        return time(int(hh), int(mm))
    except Exception as e:
        raise ValueError(f"cutoff must be 'HH:MM', got {cutoff!r}") from e


def cutoff_ts(delivery_date: date, cutoff: str) -> pd.Timestamp:
    """UTC instant of the decision cutoff: `cutoff` UK-local time on D-1."""
    local = datetime.combine(delivery_date - timedelta(days=1), parse_cutoff(cutoff), tzinfo=config.TZ)
    return pd.Timestamp(local).tz_convert("UTC")


def _with_delivery_date(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["delivery_date"] = df["startTime"].dt.tz_convert(config.TZ).dt.date
    return df


def decision_view(forecasts: pd.DataFrame, actuals: pd.DataFrame, cutoff: str,
                  start: date | None = None, end: date | None = None) -> pd.DataFrame:
    """For every WINDFOR target time (hourly), the LATEST forecast published at/before the cutoff on D-1.

    Returns columns: startTime, delivery_date, publishTime, horizon_h, forecast, actual,
    error, abs_error. Targets with no forecast available at cutoff are dropped;
    targets with no actual yet keep NaN actual/error.
    """
    fc = _with_delivery_date(forecasts)
    if start:
        fc = fc[fc["delivery_date"] >= start]
    if end:
        fc = fc[fc["delivery_date"] <= end]
    if fc.empty:
        return _empty_view()

    cut_map = {d: cutoff_ts(d, cutoff) for d in fc["delivery_date"].unique()}
    fc = fc[fc["publishTime"] <= fc["delivery_date"].map(cut_map)]
    if fc.empty:
        return _empty_view()

    latest = (fc.sort_values(["startTime", "publishTime"])
                .groupby("startTime", as_index=False).tail(1))
    out = latest.merge(actuals[["startTime", "actual"]], on="startTime", how="left")
    out["horizon_h"] = (out["startTime"] - out["publishTime"]).dt.total_seconds() / 3600
    out["error"] = out["forecast"] - out["actual"]
    out["abs_error"] = out["error"].abs()
    return out.sort_values("startTime").reset_index(drop=True)


def _empty_view() -> pd.DataFrame:
    return pd.DataFrame(columns=["startTime", "delivery_date", "publishTime", "forecast",
                                 "actual", "horizon_h", "error", "abs_error"])


# ---------- metrics ----------

def summarize(df: pd.DataFrame) -> dict:
    """Error statistics for rows that have both forecast and actual."""
    d = df.dropna(subset=["forecast", "actual"])
    n = len(d)
    if n == 0:
        return {"n": 0}
    e = d["error"].to_numpy(dtype=float)
    a = d["actual"].to_numpy(dtype=float)
    ae = np.abs(e)
    return {
        "n": int(n),
        "mean_actual_mw": float(a.mean()),
        "mae_mw": float(ae.mean()),
        "rmse_mw": float(np.sqrt((e ** 2).mean())),
        "bias_mw": float(e.mean()),                       # + = over-forecast on average
        "wmape_pct": float(100 * ae.sum() / a.sum()) if a.sum() > 0 else None,
        "p50_abs_error_mw": float(np.percentile(ae, 50)),
        "p90_abs_error_mw": float(np.percentile(ae, 90)),
        "p99_abs_error_mw": float(np.percentile(ae, 99)),
        "max_abs_error_mw": float(ae.max()),
        "over_forecast_share_pct": float(100 * (e > 0).mean()),
    }


def by_group(df: pd.DataFrame, key: pd.Series, name: str) -> list[dict]:
    d = df.dropna(subset=["forecast", "actual"]).copy()
    d[name] = key.loc[d.index]
    rows = []
    for k, g in d.groupby(name, observed=True, sort=True):
        rows.append({name: k if not isinstance(k, (date, pd.Timestamp)) else str(k), **summarize(g)})
    return rows


def horizon_profile(forecasts: pd.DataFrame, actuals: pd.DataFrame,
                    start: date | None = None, end: date | None = None) -> list[dict]:
    """Error vs forecast age, using EVERY revision (not just the decision-time one).

    Answers: 'how much better does the forecast get as the delivery time approaches?',
    which tells the buyer how much the cutoff choice matters.
    """
    fc = _with_delivery_date(forecasts)
    if start:
        fc = fc[fc["delivery_date"] >= start]
    if end:
        fc = fc[fc["delivery_date"] <= end]
    d = fc.merge(actuals[["startTime", "actual"]], on="startTime", how="inner")
    d["horizon_h"] = (d["startTime"] - d["publishTime"]).dt.total_seconds() / 3600
    d = d[d["horizon_h"] >= 0]
    d["error"] = d["forecast"] - d["actual"]
    bins = config.HORIZON_BINS_H
    labels = [f"{bins[i]}-{bins[i+1]}h" if bins[i + 1] < 1000 else f">{bins[i]}h" for i in range(len(bins) - 1)]
    d["bucket"] = pd.cut(d["horizon_h"], bins=bins, labels=labels, right=False)
    rows = []
    for lab in labels:
        g = d[d["bucket"] == lab]
        if len(g):
            rows.append({"horizon_bucket": lab, **summarize(g)})
    return rows


# ---------- serialisation ----------

def to_records(df: pd.DataFrame, cols: list[str]) -> list[dict]:
    out = df[cols].copy()
    for c in out.columns:
        if str(out[c].dtype).startswith("datetime64"):
            out[c] = out[c].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        elif c == "delivery_date":
            out[c] = out[c].astype(str)
    out = out.astype(object).where(out.notna(), None)
    return out.to_dict(orient="records")


# ---------- walk-forward bias correction ----------

def add_bias_adjustment(v: pd.DataFrame, lookback_days: int = 7, lag_days: int = 2,
                        min_days: int = 3) -> pd.DataFrame:
    """Adds a bias-corrected forecast that only uses information known at decision time.

    For delivery day D the bias estimate is the mean daily error of delivery days
    D-lag_days-lookback_days+1 .. D-lag_days. lag_days=2 because at the cutoff on D-1
    the outcome of D-2 is complete but D-1 is still in progress. With fewer than
    `min_days` days of history the estimate is NaN (no correction applied).
    """
    out = v.copy()
    known = out.dropna(subset=["actual"])
    daily = known.groupby("delivery_date")["error"].mean()
    daily.index = pd.to_datetime(daily.index)

    def estimate(d) -> float:
        d = pd.Timestamp(d)
        lo = d - pd.Timedelta(days=lag_days + lookback_days - 1)
        hi = d - pd.Timedelta(days=lag_days)
        w = daily[(daily.index >= lo) & (daily.index <= hi)]
        return float(w.mean()) if len(w) >= min_days else np.nan

    est = {d: estimate(d) for d in out["delivery_date"].unique()}
    out["bias_est"] = out["delivery_date"].map(est)
    out["forecast_adj"] = out["forecast"] - out["bias_est"]
    out["error_adj"] = out["forecast_adj"] - out["actual"]
    return out


def summarize_adjusted(v: pd.DataFrame, lookback_days: int = 7) -> dict:
    """Raw vs bias-corrected accuracy on exactly the same rows."""
    if "bias_est" not in v:
        return {"n": 0}
    sub = v.dropna(subset=["actual", "bias_est"])
    if sub.empty:
        return {"n": 0}
    adj = sub.copy()
    adj["error"] = adj["error_adj"]
    adj["abs_error"] = adj["error_adj"].abs()
    return {"n": int(len(sub)), "days": int(sub["delivery_date"].nunique()),
            "lookback_days": lookback_days, "raw": summarize(sub), "adjusted": summarize(adj)}
