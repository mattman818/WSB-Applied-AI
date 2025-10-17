from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .pe_data import DEFAULT_TICKERS, DataUnavailableError, compute_pe_timeseries


def _parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {value}. Use YYYY-MM-DD.") from exc


app = FastAPI(
    title="P/E Ratio Dashboard",
    description="Daily price-to-earnings time series for selected equities.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def read_index() -> FileResponse:
    """Serve the client application entry point."""
    return FileResponse(static_dir / "index.html")


@app.get("/api/pe")
def pe_endpoint(
    tickers: str = Query(
        ",".join(DEFAULT_TICKERS),
        description="Comma separated list of ticker symbols to include in the response.",
    ),
    start: str | None = Query(None, description="Start date in YYYY-MM-DD format."),
    end: str | None = Query(None, description="End date in YYYY-MM-DD format."),
) -> Dict[str, List[Dict[str, float]]]:
    """Return the P/E ratio time series for the requested tickers."""

    requested: List[str] = [symbol.strip().upper() for symbol in tickers.split(",") if symbol.strip()]
    if not requested:
        raise HTTPException(status_code=400, detail="At least one ticker symbol is required.")

    today = date.today()
    default_start = today - timedelta(days=365 * 25)

    start_date = _parse_date(start, default_start)
    end_date = _parse_date(end, today)

    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date.")

    try:
        series = compute_pe_timeseries(requested, start_date, end_date)
    except (ValueError, DataUnavailableError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - surface unexpected issues gracefully
        raise HTTPException(status_code=502, detail=f"Failed to retrieve data: {exc}") from exc

    payload: Dict[str, List[Dict[str, float]]] = {}
    for symbol, frame in series.items():
        payload[symbol] = [
            {"date": idx.strftime("%Y-%m-%d"), "pe": round(value, 4)}
            for idx, value in frame.items()
        ]

    return payload
