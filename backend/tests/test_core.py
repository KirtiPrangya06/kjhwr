import pandas as pd
import pytest

from app import core


def ts(s):
    return pd.Timestamp(s, tz="UTC")


@pytest.fixture
def frames():
    # Two target times on 2026-01-15, three revisions each.
    fc = pd.DataFrame({
        "publishTime": [ts("2026-01-14 06:00"), ts("2026-01-14 08:59"), ts("2026-01-14 09:30"),
                        ts("2026-01-14 06:00"), ts("2026-01-14 08:59"), ts("2026-01-14 09:30")],
        "startTime":   [ts("2026-01-15 12:00")] * 3 + [ts("2026-01-15 12:30")] * 3,
        "forecast":    [1000, 1200, 1500, 2000, 2200, 2500],
    })
    act = pd.DataFrame({"startTime": [ts("2026-01-15 12:00"), ts("2026-01-15 12:30")],
                        "actual": [1100, 2000]})
    return fc, act


def test_picks_latest_revision_at_or_before_cutoff(frames):
    fc, act = frames
    v = core.decision_view(fc, act, "09:00")
    assert v["forecast"].tolist() == [1200, 2200]          # 08:59 revision, not 09:30
    assert v["publishTime"].iloc[0] == ts("2026-01-14 08:59")


def test_revision_published_after_cutoff_is_excluded(frames):
    fc, act = frames
    v = core.decision_view(fc, act, "07:00")
    assert v["forecast"].tolist() == [1000, 2000]          # only the 06:00 revision


def test_cutoff_inclusive(frames):
    fc, act = frames
    v = core.decision_view(fc, act, "09:30")
    assert v["forecast"].tolist() == [1500, 2500]


def test_error_sign_and_horizon(frames):
    fc, act = frames
    v = core.decision_view(fc, act, "09:00")
    assert v["error"].tolist() == [100, 200]               # forecast - actual
    assert v["horizon_h"].iloc[0] == pytest.approx(27 + 1 / 60)


def test_no_forecast_before_cutoff_returns_empty(frames):
    fc, act = frames
    assert core.decision_view(fc, act, "05:00").empty


def test_summarize_known_values(frames):
    fc, act = frames
    s = core.summarize(core.decision_view(fc, act, "09:00"))
    assert s["n"] == 2
    assert s["mae_mw"] == pytest.approx(150)
    assert s["bias_mw"] == pytest.approx(150)
    assert s["rmse_mw"] == pytest.approx(((100**2 + 200**2) / 2) ** 0.5)
    assert s["wmape_pct"] == pytest.approx(100 * 300 / 3100)
    assert s["over_forecast_share_pct"] == 100


def test_missing_actual_kept_but_excluded_from_metrics(frames):
    fc, act = frames
    v = core.decision_view(fc, act.iloc[:1], "09:00")
    assert len(v) == 2 and v["actual"].isna().sum() == 1
    assert core.summarize(v)["n"] == 1


def test_bad_cutoff():
    with pytest.raises(ValueError):
        core.parse_cutoff("9am")


def test_horizon_profile_buckets(frames):
    fc, act = frames
    rows = core.horizon_profile(fc, act)
    got = {r["horizon_bucket"]: r["n"] for r in rows}
    # 06:00 revisions are 30h / 30.5h ahead; the other four are 26.5-27.5h ahead
    assert got == {"24-30h": 4, "30-36h": 2}


def test_bias_adjustment_uses_only_known_days():
    from datetime import date, timedelta
    import numpy as np
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(12)]
    v = pd.DataFrame({"delivery_date": np.repeat(days, 2), "forecast": 1100.0,
                      "actual": 1000.0, "error": 100.0})
    out = core.add_bias_adjustment(v)
    by_day = out.groupby("delivery_date")["bias_est"].first()
    assert by_day.iloc[:4].isna().all()            # < 3 days of history ending at D-2
    assert by_day.iloc[5] == pytest.approx(100.0)  # sees days 0..3 only
    assert out[out["delivery_date"] == days[5]]["error_adj"].abs().max() == pytest.approx(0.0)
    s = core.summarize_adjusted(out)
    assert s["raw"]["mae_mw"] == pytest.approx(100.0) and s["adjusted"]["mae_mw"] == pytest.approx(0.0)


def test_bias_estimate_ignores_future_days():
    from datetime import date, timedelta
    import numpy as np
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(10)]
    err = np.repeat([100.0] * 8 + [9999.0, 9999.0], 2)   # last two days are wild
    v = pd.DataFrame({"delivery_date": np.repeat(days, 2), "forecast": 0.0, "actual": 0.0, "error": err})
    out = core.add_bias_adjustment(v)
    # day index 7 (D-2 = day 5) must not be influenced by days 8, 9
    assert out[out["delivery_date"] == days[7]]["bias_est"].iloc[0] == pytest.approx(100.0)
