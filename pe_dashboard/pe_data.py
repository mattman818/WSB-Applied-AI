from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from typing import Dict, Iterable, List

import pandas as pd
import yfinance as yf

DEFAULT_TICKERS: List[str] = [
    "NVDA",
    "MSFT",
    "GOOG",
    "AMZN",
    "META",
    "AVGO",
    "ORCL",
    "TLSA",
    "AAPL",
]

TICKER_ALIASES = {
    "TLSA": "TSLA",
}


class DataUnavailableError(RuntimeError):
    """Raised when underlying market data cannot be retrieved."""


@lru_cache(maxsize=32)
def _download_price_history(symbol: str, start: date, end: date) -> pd.Series:
    """Retrieve the adjusted close price history for a single symbol."""

    history = yf.download(
        symbol,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        progress=False,
        auto_adjust=True,
        threads=False,
    )
    if history.empty:
        raise DataUnavailableError(f"No price history returned for {symbol}.")

    price_column = "Adj Close" if "Adj Close" in history.columns else "Close"
    series = history[price_column].copy()
    series.index = pd.to_datetime(series.index).tz_localize(None)
    return series


@lru_cache(maxsize=32)
def _download_earnings(symbol: str, end: date) -> pd.DataFrame:
    """Load historical quarterly EPS actuals for a symbol."""

    ticker = yf.Ticker(symbol)
    earnings = ticker.get_earnings_dates(limit=200)
    if earnings is None or earnings.empty:
        raise DataUnavailableError(f"No earnings history returned for {symbol}.")

    earnings = earnings.copy()
    earnings.index = pd.to_datetime(earnings.index).tz_localize(None)
    earnings = earnings[earnings.index <= pd.Timestamp(end)]

    eps_column = next((col for col in earnings.columns if col.lower() == "epsactual"), None)
    if eps_column is None:
        raise DataUnavailableError(f"Earnings data for {symbol} does not contain EPS actuals.")

    earnings = earnings[[eps_column]].rename(columns={eps_column: "eps_actual"})
    earnings = earnings.dropna()
    if earnings.empty:
        raise DataUnavailableError(f"No EPS actuals available for {symbol}.")

    earnings = earnings.sort_index()
    earnings["ttm_eps"] = earnings["eps_actual"].rolling(window=4).sum()
    earnings = earnings.dropna(subset=["ttm_eps"])
    if earnings.empty:
        raise DataUnavailableError(f"Insufficient EPS history to compute trailing twelve months for {symbol}.")

    earnings = earnings[earnings["ttm_eps"] > 0]
    if earnings.empty:
        raise DataUnavailableError(f"Trailing EPS for {symbol} is non-positive, cannot compute P/E.")

    return earnings[["ttm_eps"]]


def compute_pe_timeseries(symbols: Iterable[str], start: date, end: date) -> Dict[str, pd.Series]:
    """Compute the daily P/E ratio for each requested symbol."""

    results: Dict[str, pd.Series] = {}
    for raw_symbol in symbols:
        symbol = TICKER_ALIASES.get(raw_symbol, raw_symbol)
        price_history = _download_price_history(symbol, start, end)
        earnings = _download_earnings(symbol, end)

        ttm_eps = earnings["ttm_eps"]
        ttm_eps = ttm_eps.reindex(price_history.index, method="ffill")
        merged = pd.DataFrame({"price": price_history, "ttm_eps": ttm_eps})
        mask = (merged.index >= pd.Timestamp(start)) & (merged.index <= pd.Timestamp(end))
        merged = merged.loc[mask]
        merged = merged.dropna(subset=["price", "ttm_eps"])
        if merged.empty:
            raise DataUnavailableError(f"Unable to align price and EPS history for {symbol}.")

        pe = (merged["price"] / merged["ttm_eps"]).dropna().sort_index()
        results[raw_symbol] = pe

    return results
