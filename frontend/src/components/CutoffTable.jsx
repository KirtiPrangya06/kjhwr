import { mw, pct } from "../format.js";

export default function CutoffTable({ sensitivity, selected, onPick }) {
  if (sensitivity.error) return <p className="notice error" role="alert">{sensitivity.error.message}</p>;
  const rows = sensitivity.data?.rows;
  if (!rows) return <p className="notice">Loading…</p>;
  const max = Math.max(...rows.map((r) => r.mae_mw ?? 0));

  return (
    <div className="table-wrap">
      <table>
        <caption className="visually-hidden">Forecast accuracy by decision cutoff</caption>
        <thead>
          <tr><th scope="col">Decide by</th><th scope="col" className="r">Average miss</th><th scope="col" className="bars" />
              <th scope="col" className="r">9 in 10 within</th><th scope="col" className="r">Bias</th><th scope="col" className="r">Error / output</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.cutoff} className={r.cutoff === selected ? "sel" : ""}>
              <th scope="row">
                <button type="button" className="link" onClick={() => onPick(r.cutoff)}
                        aria-pressed={r.cutoff === selected}>{r.cutoff}</button>
              </th>
              <td className="r num">{mw(r.mae_mw)}</td>
              <td className="bars" aria-hidden="true"><span style={{ width: `${(100 * (r.mae_mw ?? 0)) / max}%` }} /></td>
              <td className="r num">{mw(r.p90_abs_error_mw)}</td>
              <td className="r num">{r.bias_mw != null && r.bias_mw >= 0 ? "+" : ""}{mw(r.bias_mw)}</td>
              <td className="r num">{pct(r.wmape_pct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
