# P/E Ratio Dashboard

This FastAPI application exposes an API and lightweight front-end for exploring the daily price-to-earnings (P/E) ratio of large-cap technology companies. P/E values are derived by pairing daily adjusted close prices from Yahoo Finance with trailing-twelve-month EPS built from quarterly earnings releases.

## Features

- Fetches 25 years of price history and quarterly EPS for the default ticker set (NVDA, MSFT, GOOG, AMZN, META, AVGO, ORCL, TLSA, AAPL).
- Interactive client powered by Chart.js allows you to:
  - Toggle individual companies on or off.
  - Switch between a combined multi-series chart and individual charts for selected companies.
  - Adjust the date window.
- Backend caching to avoid redundant Yahoo Finance requests during a session.

## Running locally

1. Install dependencies (Python 3.10+ recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt -r pe_dashboard/requirements.txt
   ```

2. Start the development server:

   ```bash
   uvicorn pe_dashboard.app:app --reload
   ```

3. Open <http://127.0.0.1:8000> in your browser to use the dashboard.

> **Note:** The app relies on live requests to Yahoo Finance via `yfinance`. Ensure outbound HTTPS access is permitted from your environment. If you encounter rate limiting, reloading after a short pause typically resolves the issue.

> Tesla is listed as `TLSA` in the UI to mirror the original request; the backend transparently maps the symbol to Yahoo Finance's `TSLA` ticker when fetching data.

## Project structure

```
pe_dashboard/
├── README.md
├── app.py           # FastAPI application & routing
├── pe_data.py       # Data retrieval and P/E computation helpers
└── static/
    ├── app.js       # Front-end logic & chart rendering
    ├── index.html   # Client entry point
    └── style.css    # Styling for the dashboard
```
