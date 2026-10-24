import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { mw } from "../format.js";

const axis = { stroke: "#5b6b73" };
const fmtMW = (v) => mw(v);

function Wrap({ title, caption, state, children }) {
  return (
    <figure className="chart-figure">
      <h3>{title}</h3>
      {state.error ? <p className="notice error" role="alert">{state.error.message}</p>
        : !state.data ? <p className="notice">Loading…</p> : children}
      <figcaption>{caption}</figcaption>
    </figure>
  );
}

export function HourChart({ metrics }) {
  const rows = (metrics.data?.by_hour ?? []).map((r) => ({
    hour: `${String(r.hour).padStart(2, "0")}:00`, mae: r.mae_mw, bias: r.bias_mw,
  }));
  return (
    <Wrap title="Error by hour of day" state={metrics}
          caption="Bars: average miss. Line: direction (above zero = forecast too high). UK local time.">
      <div role="img" aria-label="Average forecast error by hour of delivery day">
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#d5dde1" vertical={false} />
            <XAxis dataKey="hour" interval={2} {...axis} />
            <YAxis {...axis} />
            <Tooltip formatter={fmtMW} />
            <Legend verticalAlign="top" height={28} />
            <ReferenceLine y={0} stroke="#16242c" />
            <Bar dataKey="mae" name="Average miss" fill="#1f7a8c" isAnimationActive={false} />
            <Line dataKey="bias" name="Direction (bias)" stroke="#b4432c" strokeWidth={2} dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Wrap>
  );
}

export function HorizonChart({ horizon }) {
  const rows = (horizon.data?.buckets ?? []).map((r) => ({
    bucket: r.horizon_bucket, mae: r.mae_mw, p90: r.p90_abs_error_mw,
  }));
  return (
    <Wrap title="Error by forecast age" state={horizon}
          caption="How far ahead of delivery the forecast was published, across all revisions in January.">
      <div role="img" aria-label="Forecast error by hours between publication and delivery">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#d5dde1" vertical={false} />
            <XAxis dataKey="bucket" {...axis} />
            <YAxis {...axis} />
            <Tooltip formatter={fmtMW} />
            <Legend verticalAlign="top" height={28} />
            <Bar dataKey="mae" name="Average miss" fill="#1f7a8c" isAnimationActive={false} />
            <Bar dataKey="p90" name="9 in 10 within" fill="#9fc6d0" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Wrap>
  );
}
