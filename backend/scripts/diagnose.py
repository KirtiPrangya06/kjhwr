"""Why is the forecast so biased? Run:  python scripts/diagnose.py

Checks (1) timestamp alignment, (2) point vs hour-averaged actuals, (3) bias vs wind level,
(4) bias at short lead times, using the 09:00 decision-time forecast.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from app import core

fc, act = core.load_forecasts(), core.load_actuals()
a = act.set_index("startTime")["actual"]
v = core.decision_view(fc, act, "09:00").dropna(subset=["actual"])
f = v["forecast"].to_numpy()
t = v["startTime"]
step = pd.Timedelta(minutes=30)

print(f"n={len(v)}  mean forecast={f.mean():.0f} MW  mean actual={v['actual'].mean():.0f} MW  "
      f"corr={np.corrcoef(f, v['actual'])[0, 1]:.3f}")

print("\n1) Alignment: forecast at T vs actual at T+lag (MAE / bias, MW). A clear minimum away from 0 = timestamp offset")
for lag in range(-4, 5):
    s = a.reindex(t + lag * step).to_numpy()
    ok = ~np.isnan(s)
    e = f[ok] - s[ok]
    print(f"   lag {lag * 30:+4d} min: MAE {np.abs(e).mean():6.0f}   bias {e.mean():+6.0f}")

print("\n2) Actual as the average of the hour (T and T+30min) vs the single value at T")
hr = (a.reindex(t).to_numpy() + a.reindex(t + step).to_numpy()) / 2
ok = ~np.isnan(hr)
e = f[ok] - hr[ok]
print(f"   hour-average: MAE {np.abs(e).mean():.0f}   bias {e.mean():+.0f}")

print("\n3) Bias by actual wind level (curtailment would show as larger bias when wind is high)")
q = pd.qcut(v["actual"], 4, labels=["lowest 25%", "25-50%", "50-75%", "highest 25%"])
print(v.groupby(q, observed=True).agg(mean_actual=("actual", "mean"), mean_forecast=("forecast", "mean"),
                                       bias=("error", "mean"), mae=("abs_error", "mean")).round(0).to_string())

print("\n4) Bias by forecast age, all revisions (does it vanish close to delivery?)")
for r in core.horizon_profile(fc, act)[:5]:
    print(f"   {r['horizon_bucket']:>7}: MAE {r['mae_mw']:.0f}   bias {r['bias_mw']:+.0f}   n={r['n']}")

print("\n5) Days with the largest average over-forecast")
d = v.groupby("delivery_date")["error"].mean().sort_values(ascending=False)
print(d.head(5).round(0).to_string(), "\n...\n", d.tail(3).round(0).to_string())
