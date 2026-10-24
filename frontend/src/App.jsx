import { useState } from "react";
import { api } from "./api.js";
import { useAsync } from "./useAsync.js";
import { addDays, dayLong } from "./format.js";
import Controls from "./components/Controls.jsx";
import DecisionStatement from "./components/DecisionStatement.jsx";
import ForecastChart from "./components/ForecastChart.jsx";
import AccuracyTable from "./components/AccuracyTable.jsx";
import { HorizonChart, HourChart } from "./components/ErrorCharts.jsx";
import CutoffTable from "./components/CutoffTable.jsx";

export const CUTOFFS = ["06:00", "08:00", "09:00", "10:00", "12:00", "15:00", "18:00", "21:00"];

export default function App() {
  const [date, setDate] = useState("2026-01-15");
  const [cutoff, setCutoff] = useState("09:00");

  const forecast = useAsync(() => api.forecast(date, cutoff), [date, cutoff]);
  const metrics = useAsync(() => api.metrics(cutoff), [cutoff]);
  const horizon = useAsync(() => api.horizon(), []);
  const sensitivity = useAsync(() => api.sensitivity(), []);

  return (
    <div className="page">
      <header className="masthead">
        <h1>GB wind generation: what the forecast said, and how far off it runs</h1>
        <p className="sub">
          National wind output from Elexon (WINDFOR forecasts, FUELHH outturn), for day-ahead purchases
          made in January 2026.
        </p>
      </header>

      <Controls
        date={date}
        cutoff={cutoff}
        cutoffs={CUTOFFS}
        onDate={(d) => d && setDate(d)}
        onPrev={() => setDate(addDays(date, -1))}
        onNext={() => setDate(addDays(date, 1))}
        onCutoff={setCutoff}
      />

      <main>
        <section aria-labelledby="decision-h">
          <h2 id="decision-h" className="visually-hidden">Forecast for {dayLong(date)}</h2>
          <DecisionStatement date={date} cutoff={cutoff} forecast={forecast} metrics={metrics} />
          <ForecastChart forecast={forecast} metrics={metrics} />
        </section>

        <section aria-labelledby="acc-h">
          <h2 id="acc-h">How accurate has this forecast been?</h2>
          <p className="lede">
            Every forecast hour of January, using the forecast that was available at {cutoff} the day before
            delivery. Error is forecast minus actual: a positive error means less wind arrived than
            planned for, so the shortfall has to be bought later.
          </p>
          <AccuracyTable metrics={metrics} cutoff={cutoff} />
        </section>

        <section aria-labelledby="when-h">
          <h2 id="when-h">When does the error occur?</h2>
          <div className="two-col">
            <HourChart metrics={metrics} />
            <HorizonChart horizon={horizon} />
          </div>
        </section>

        <section aria-labelledby="cut-h">
          <h2 id="cut-h">What does the buying deadline cost?</h2>
          <p className="lede">
            The same accuracy measures if the cutoff were earlier or later. Later cutoffs see fresher
            forecasts. Confirm the actual gate closure for the market you trade in.
          </p>
          <CutoffTable sensitivity={sensitivity} selected={cutoff} onPick={setCutoff} />
        </section>
      </main>

      <footer>
        Data: Elexon Insights Solution (BMRS), used under the BMRS Data Licence. Wind only, national level.
        Built with AI assistance (Claude).
      </footer>
    </div>
  );
}
