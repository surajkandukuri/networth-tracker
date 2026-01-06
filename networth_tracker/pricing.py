from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List

import pandas as pd
import yfinance as yf


TICKER_ALIASES = {
    "BRKB": "BRK-B",
}


@dataclass(frozen=True)
class PricingResult:
    prices: Dict[str, float]
    source_dates: Dict[str, date]


def normalize_ticker(ticker: str) -> str:
    cleaned = ticker.strip()
    return TICKER_ALIASES.get(cleaned, cleaned)


def _parse_valuation_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid valuation_date '{value}'. Use YYYY-MM-DD or a date object."
        ) from exc


def _dedupe_and_strip(values: Iterable[str]) -> List[str]:
    seen = set()
    output = []
    for raw in values:
        cleaned = str(raw).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        output.append(cleaned)
    return output


def fetch_close_prices(
    tickers: list[str],
    valuation_date: str | date | datetime,
) -> PricingResult:
    unique_tickers = _dedupe_and_strip(tickers)
    if not unique_tickers:
        raise ValueError("No tickers provided for pricing.")

    normalized = [normalize_ticker(t) for t in unique_tickers]
    valuation_dt = _parse_valuation_date(valuation_date)
    next_day = valuation_dt + timedelta(days=1)

    data = yf.download(
        tickers=sorted(set(normalized)),
        start=valuation_dt.isoformat(),
        end=next_day.isoformat(),
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="column",
    )

    if data.empty:
        raise ValueError(
            f"No price data returned for {valuation_dt.isoformat()} from Yahoo."
        )

    prices_by_normalized: Dict[str, float] = {}
    source_dates: Dict[str, date] = {}

    if isinstance(data, pd.Series):
        close_series = data.dropna()
        if not close_series.empty:
            only_ticker = normalized[0]
            prices_by_normalized[only_ticker] = float(close_series.iloc[-1])
            source_dates[only_ticker] = close_series.index[-1].date()
    elif isinstance(data.columns, pd.MultiIndex):
        if "Close" not in data.columns.get_level_values(0):
            raise ValueError("Yahoo response missing Close column for multi-ticker request.")
        close_frame = data["Close"]
        for ticker in close_frame.columns:
            series = close_frame[ticker].dropna()
            if series.empty:
                continue
            prices_by_normalized[str(ticker)] = float(series.iloc[-1])
            source_dates[str(ticker)] = series.index[-1].date()
    else:
        if "Close" not in data.columns:
            raise ValueError("Yahoo response missing Close column for single-ticker request.")
        close_series = data["Close"].dropna()
        if not close_series.empty:
            only_ticker = normalized[0]
            prices_by_normalized[only_ticker] = float(close_series.iloc[-1])
            source_dates[only_ticker] = close_series.index[-1].date()

    missing_normalized = sorted(set(normalized) - set(prices_by_normalized.keys()))
    if missing_normalized:
        raise ValueError(
            "Missing close prices for valuation date "
            f"{valuation_dt.isoformat()}: {', '.join(missing_normalized)}"
        )

    prices: Dict[str, float] = {}
    resolved_dates: Dict[str, date] = {}
    for original, mapped in zip(unique_tickers, normalized):
        prices[original] = prices_by_normalized[mapped]
        resolved_dates[original] = source_dates[mapped]

    return PricingResult(prices=prices, source_dates=resolved_dates)


def fetch_close_price_panel(
    tickers: list[str],
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    unique_tickers = _dedupe_and_strip(tickers)
    if not unique_tickers:
        raise ValueError("No tickers provided for price panel.")

    normalized = [normalize_ticker(t) for t in unique_tickers]
    end_with_buffer = end_date + timedelta(days=1)

    data = yf.download(
        tickers=sorted(set(normalized)),
        start=start_date.isoformat(),
        end=end_with_buffer.isoformat(),
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="column",
    )

    if data.empty:
        raise ValueError(
            f"No price data returned for window {start_date} to {end_date} from Yahoo."
        )

    if isinstance(data, pd.Series):
        close_series = data.dropna()
        if close_series.empty:
            raise ValueError("Yahoo response missing Close data for price panel.")
        df = close_series.to_frame(name=normalized[0])
    elif isinstance(data.columns, pd.MultiIndex):
        if "Close" not in data.columns.get_level_values(0):
            raise ValueError("Yahoo response missing Close column for multi-ticker request.")
        df = data["Close"].copy()
    else:
        if "Close" not in data.columns:
            raise ValueError("Yahoo response missing Close column for single-ticker request.")
        df = data[["Close"]].copy()
        df.columns = [normalized[0]]

    df.index = [idx.date() for idx in df.index]
    return df
