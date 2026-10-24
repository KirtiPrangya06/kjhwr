# Wind forecast decision portal

Web app for a GB energy buyer's day-ahead desk. It shows the latest wind-generation forecast available at the
day-ahead decision time (Elexon WINDFOR) and measures how accurate it has been against actual output (Elexon FUELHH),
for delivery days in January 2026.

**Live app:** https://kjhwr-six.vercel.app/

**Main finding (January 2026, 09:00 cutoff):** the published forecast ran about 1.85 GW above actual wind, in 85% of
forecast hours (average miss 2,127 MW, 18.4% of output). A bias correction that uses only data known at decision time
cuts the average miss by about 20% (2,054 to 1,648 MW over the 27 days with enough history). The cause of the gap
between the two datasets is not established.

## Stack

React 18 + Vite + Recharts (frontend), Python FastAPI + pandas (backend), Docker, Vercel (deployment).

## Files and directories

```
.
├── api/index.py              Vercel entry point: exposes the FastAPI app as a serverless function
├── backend/
│   ├── app/
│   │   ├── config.py         Window dates, timezone, default cutoff, paths
│   │   ├── elexon.py         Elexon Insights API client (FUELHH and WINDFOR stream endpoints)
│   │   ├── ingest.py         Downloads January 2026 data into backend/data/*.csv
│   │   ├── core.py           Analysis: decision-time forecast, error metrics, horizon profile, bias correction
│   │   └── main.py           FastAPI routes (/api/...)
│   ├── data/                 actuals.csv and forecasts.csv (pre-ingested, bundled into the deployment)
│   ├── scripts/
│   │   ├── probe_elexon.py   Checks the live API parameters and fields
│   │   └── diagnose.py       Diagnostics behind the bias finding
│   ├── tests/test_core.py    Unit tests for the analysis logic
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/                  React app (App.jsx, api.js, components/, styles.css)
│   ├── Dockerfile, nginx.conf
│   └── package.json, vite.config.js, index.html
├── docker-compose.yml        Runs frontend and backend together
├── vercel.json               Vercel build, routing and data-file bundling
├── requirements.txt          Python runtime dependencies for the Vercel function
└── README.md
```

## How to start the application

### Option 1: Docker

```bash
docker compose up --build        # app at http://localhost:8080
```

### Option 2: run locally

Backend (terminal 1):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload    # API docs at http://localhost:8000/docs
```

Frontend (terminal 2):

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173 (proxies /api to port 8000)
```

The January 2026 data is already in `backend/data/`. To re-download it from Elexon:

```bash
cd backend && python scripts/probe_elexon.py && python -m app.ingest
```

Run the tests with `python -m pytest -q` inside `backend`.

## API

- `GET /api/forecast?delivery_date=2026-01-15&cutoff=09:00`: latest forecast available at the cutoff vs actual, plus bias-corrected forecast
- `GET /api/metrics?cutoff=09:00`: overall, by-day and by-hour accuracy, and raw vs bias-corrected comparison
- `GET /api/horizon`: error by forecast age (all revisions)
- `GET /api/cutoff-sensitivity`: accuracy for different decision cutoffs
- `GET /api/config`, `GET /api/health`

## Method and assumptions

- **Decision-time forecast:** for each target hour, the latest WINDFOR revision published at or before the cutoff (UK local time) on the day before delivery. Default cutoff 09:00; the actual gate-closure time should be confirmed for the market in use.
- **Error** = forecast minus actual. Positive means over-forecast, so the buyer is short.
- **Data:** WINDFOR is hourly and revised roughly every 3 hours; FUELHH is half-hourly. Accuracy is measured at the hourly timestamps where both exist.
- **Bias correction:** subtracts the mean daily error of delivery days D-8 to D-2 (all known at the cutoff), so no future data is used.
- **Limits:** one month of data, national wind only, no demand data, and the shaded margin on the chart is measured on the same month it is shown for.

## Deployment

Deployed on Vercel from the repository root: `frontend/` builds to static files and `api/index.py` serves the backend,
with `backend/data/*.csv` bundled into the function (see `vercel.json`). Docker is provided for local runs, since Vercel does not run containers.

## AI usage

This project was built with assistance from Claude (Anthropic) for code, analysis and documentation.

## Data source

Elexon Insights Solution (BMRS), used under the BMRS Data Licence.
