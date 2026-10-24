import { dayLong, hhmm, mw, num } from "../format.js";

function Status({ state }) {
  if (state.error) return <p className="notice error" role="alert">{state.error.message}</p>;
  return <p className="notice" aria-busy="true">Loading forecast…</p>;
}

export default function DecisionStatement({ date, cutoff, forecast, metrics }) {
  if (forecast.loading || forecast.error || !forecast.data) return <Status state={forecast} />;
  const { points, latest_publish_time, summary } = forecast.data;
  if (!points.length) {
    return (
      <p className="notice">
        No forecast had been published by {cutoff} on the day before {dayLong(date)}. Try a later cutoff.
      </p>
    );
  }

  const vals = points.map((p) => p.forecast);
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
  const peakIdx = vals.indexOf(Math.max(...vals));
  const lowIdx = vals.indexOf(Math.min(...vals));
  const p90 = metrics.data?.overall?.p90_abs_error_mw;
  const hasActual = summary.n > 0;

  return (
    <div className="statement">
      <p className="headline">
        As of {cutoff} the day before, wind for {dayLong(date)} was forecast to average{" "}
        <b>{mw(avg)}</b>, peaking at <b>{mw(vals[peakIdx])}</b> around {hhmm(Date.parse(points[peakIdx].startTime))}{" "}
        and dipping to <b>{mw(vals[lowIdx])}</b> around {hhmm(Date.parse(points[lowIdx].startTime))}.
      </p>
      {p90 != null && (
        <p className="plan">
          Across January, nine in ten forecast hours landed within <b>{mw(p90)}</b> of the forecast made at
          this cutoff. Plan thermal cover with that margin in mind.
        </p>
      )}
      {hasActual && (
        <p className="outturn">
          What happened: wind averaged <b>{mw(summary.mean_actual_mw)}</b>. The forecast was{" "}
          {summary.bias_mw >= 0 ? "higher" : "lower"} by <b>{mw(Math.abs(summary.bias_mw))}</b> on average
          ({summary.bias_mw >= 0 ? "you would have been short" : "you would have over-bought"}), with a typical
          hourly miss of {mw(summary.mae_mw)}.
        </p>
      )}
      <p className="meta">
        Latest revision used was published {hhmm(Date.parse(latest_publish_time))} UTC. {num(points.length)} hourly forecasts shown.
      </p>
    </div>
  );
}
