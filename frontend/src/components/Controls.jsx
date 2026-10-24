export default function Controls({ date, cutoff, cutoffs, onDate, onPrev, onNext, onCutoff }) {
  return (
    <div className="controls" role="group" aria-label="Choose delivery day and cutoff">
      <div className="field">
        <label htmlFor="date">Delivery day</label>
        <div className="date-row">
          <button type="button" onClick={onPrev} disabled={date <= "2026-01-01"} aria-label="Previous day">‹</button>
          <input id="date" type="date" min="2026-01-01" max="2026-01-31" value={date}
                 onChange={(e) => onDate(e.target.value)} />
          <button type="button" onClick={onNext} disabled={date >= "2026-01-31"} aria-label="Next day">›</button>
        </div>
      </div>
      <div className="field">
        <label htmlFor="cutoff">Decide by (UK time, day before)</label>
        <select id="cutoff" value={cutoff} onChange={(e) => onCutoff(e.target.value)}>
          {cutoffs.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
    </div>
  );
}
