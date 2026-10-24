import {
  Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { hhmm, mw } from "../format.js";

const C = { forecast: "#1f7a8c", actual: "#16242c", over: "#b4432c", under: "#2f6fa3" };

function Tip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="tip">
      <strong>{hhmm(p.t)}</strong>
      <div>Forecast: {mw(p.forecast)}</div>
      {p.adj != null && <div>Bias-corrected: {mw(p.adj)}</div>}
      <div>Actual: {mw(p.actual)}</div>
      {p.error != null && (
        <div style={{ color: p.error >= 0 ? C.over : C.under }}>
          Error: {p.error >= 0 ? "+" : ""}{mw(p.error)} {p.error >= 0 ? "(short)" : "(long)"}
        </div>
      )}
    </div>
  );
}

export default function ForecastChart({ forecast, metrics }) {
  if (!forecast.data?.points?.length) return null;
  const p90 = metrics.data?.overall?.p90_abs_error_mw ?? null;
  const data = forecast.data.points.map((p) => ({
    t: Date.parse(p.startTime),
    forecast: p.forecast,
    adj: p.forecast_adj,
    actual: p.actual,
    error: p.error,
    band: p90 == null ? null : [Math.max(0, p.forecast - p90), p.forecast + p90],
  }));

  return (
    <figure className="chart-figure">
      <div role="img" aria-label="Line chart of forecast and actual wind generation by hour">
        <ResponsiveContainer width="100%" height={340}>
          <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#d5dde1" vertical={false} />
            <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]}
                   tickFormatter={hhmm} tickCount={9} stroke="#5b6b73" />
            <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} stroke="#5b6b73"
                   label={{ value: "MW", angle: -90, position: "insideLeft", fill: "#5b6b73" }} />
            <Tooltip content={<Tip />} />
            <Legend verticalAlign="top" height={30} />
            {p90 != null && (
              <Area dataKey="band" name="Forecast ± 90% margin" stroke="none" fill={C.forecast}
                    fillOpacity={0.14} isAnimationActive={false} />
            )}
            <Line dataKey="forecast" name="Forecast at cutoff" stroke={C.forecast} strokeWidth={2.5}
                  dot={false} isAnimationActive={false} />
            {data.some((d) => d.adj != null) && (
              <Line dataKey="adj" name="Bias-corrected forecast" stroke="#b4432c" strokeWidth={2}
                    dot={false} isAnimationActive={false} connectNulls={false} />
            )}
            <Line dataKey="actual" name="Actual" stroke={C.actual} strokeWidth={2} dot={false}
                  strokeDasharray="5 3" connectNulls={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <figcaption>
        The shaded band is the margin that covered 90% of January forecast hours at this cutoff (same width all
        day). The red line removes the average over-forecast of the previous week (known at decision time). Times are UK local.
      </figcaption>
    </figure>
  );
}
