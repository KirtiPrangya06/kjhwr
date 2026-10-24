import { mw, pct } from "../format.js";

export default function AccuracyTable({ metrics, cutoff }) {
  if (metrics.error) return <p className="notice error" role="alert">{metrics.error.message}</p>;
  const o = metrics.data?.overall;
  if (!o || !o.n) return <p className="notice">Loading accuracy…</p>;

  const rows = [
    ["Average miss", mw(o.mae_mw), "Mean absolute error (MAE): the typical size of a miss, ignoring direction."],
    ["Larger misses weigh more", mw(o.rmse_mw), "Root mean square error (RMSE): like the average miss, but penalises big errors."],
    ["Direction of error", `${o.bias_mw >= 0 ? "+" : ""}${mw(o.bias_mw)}`, o.bias_mw >= 0
      ? "Bias: on average the forecast is higher than what arrived, so the buyer runs short."
      : "Bias: on average the forecast is lower than what arrived, so the buyer over-buys."],
    ["Error as share of output", pct(o.wmape_pct), "Total absolute error divided by total actual generation (wMAPE)."],
    ["9 in 10 forecast hours within", mw(o.p90_abs_error_mw), "90th percentile of absolute error."],
    ["99 in 100 within", mw(o.p99_abs_error_mw), "99th percentile: the margin for rare large misses."],
    ["Worst forecast hour", mw(o.max_abs_error_mw), "Largest absolute error in the month (WINDFOR is published hourly)."],
    ["Over-forecast share", pct(o.over_forecast_share_pct, 0), "Share of forecast hours where the forecast was higher than actual."],
  ];

  return (
    <div className="table-wrap">
      <table>
        <caption className="visually-hidden">Forecast accuracy at the {cutoff} cutoff, January 2026</caption>
        <thead><tr><th scope="col">Measure</th><th scope="col" className="r">Value</th><th scope="col">What it means</th></tr></thead>
        <tbody>
          {rows.map(([k, v, d]) => (
            <tr key={k}><th scope="row">{k}</th><td className="r num">{v}</td><td className="desc">{d}</td></tr>
          ))}
        </tbody>
        <tfoot>
          {metrics.data?.bias_adjusted?.n > 0 && (() => {
            const a = metrics.data.bias_adjusted;
            return (
              <tr><td colSpan="3">
                Correcting for the average error of the previous {a.lookback_days} days (known at decision time)
                cuts the average miss from <b>{mw(a.raw.mae_mw)}</b> to <b>{mw(a.adjusted.mae_mw)}</b> and the
                9-in-10 margin from <b>{mw(a.raw.p90_abs_error_mw)}</b> to <b>{mw(a.adjusted.p90_abs_error_mw)}</b>,
                over the {a.days} days with enough history.
              </td></tr>
            );
          })()}<tr><td colSpan="3">Based on {o.n.toLocaleString("en-GB")} forecast hours with both a forecast and an actual.</td></tr></tfoot>
      </table>
    </div>
  );
}
