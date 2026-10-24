# Wind forecast decision portal

## Run order

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/probe_elexon.py     # 1. confirm Elexon params/fields match assumptions
python -m app.ingest               # 2. writes data/actuals.csv and data/forecasts.csv
python -m pytest -q                # 3. unit tests
uvicorn app.main:app --reload      # 4. API at http://localhost:8000/docs
```

## Endpoints

- `GET /api/forecast?delivery_date=2026-01-15&cutoff=09:00`: latest forecast available at the cutoff vs actual
- `GET /api/metrics?start=&end=&cutoff=`: overall, by-day and by-hour accuracy
- `GET /api/horizon`: error vs forecast age (all revisions)
- `GET /api/cutoff-sensitivity`: error for candidate cutoffs
- `GET /api/config`, `GET /api/health`

## Conventions and assumptions

- error = forecast - actual; positive = over-forecast (buyer short).
- Decision cutoff = `cutoff` UK-local time on D-1 (default 09:00, **confirm gate closure**).
- Elexon query params and response fields confirmed from the API docs; `probe_elexon.py` re-checks them live.

## AI usage

Built with assistance from Claude.

## Frontend (React + Vite + Recharts)

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173, proxies /api to :8000
```

## Docker (after `python -m app.ingest` has produced backend/data/\*.csv)

```bash
docker compose up --build   # app at http://localhost:8080
```

## Data notes

- WINDFOR forecasts are hourly (`startTime` step 60 min) and revised roughly every 3 hours; FUELHH actuals are half-hourly.
  Accuracy is measured at the hourly timestamps where both exist (about 24 points per delivery day).
- Some WINDFOR rows have publishTime after startTime (negative horizon); they never qualify for a D-1 decision and are excluded from the horizon chart.

## Deploy to Vercel

The repo root is the Vercel project: `frontend/` builds to static files, `api/index.py` serves the FastAPI app,
and `backend/data/*.csv` is bundled into the function (see `vercel.json`). No environment variables are needed.

1. Run `python -m app.ingest` so `backend/data/actuals.csv` and `forecasts.csv` exist, and commit them.
2. Push the repo to GitHub, then in Vercel choose Add New, Project, import the repo (root directory: repo root).
3. Deploy, then open the URL in an incognito window and check `/api/health` and the dashboard.

Live app: https://kjhwr-six.vercel.app/

## Bias correction

The diagnostics show the WINDFOR forecast runs about 1.85 GW above FUELHH outturn in January 2026 at every forecast age.
`add_bias_adjustment` subtracts the mean daily error of delivery days D-8..D-2 (all known at the D-1 cutoff), so no future data is used.
It is shown beside the raw forecast and reported on the same rows. `scripts/diagnose.py` reproduces the checks.
