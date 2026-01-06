from __future__ import annotations

from bisect import bisect_right
from datetime import date, timedelta
from typing import List

import pandas as pd

from .pricing import fetch_close_price_panel


def get_quarter_bounds(dt: date) -> tuple[date, date]:
    quarter = (dt.month - 1) // 3 + 1
    start_month = (quarter - 1) * 3 + 1
    start_date = date(dt.year, start_month, 1)
    if start_month + 3 > 12:
        end_date = date(dt.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(dt.year, start_month + 3, 1) - timedelta(days=1)
    return start_date, end_date


def list_wednesdays(start: date, end: date) -> List[date]:
    if start > end:
        return []
    days_to_wed = (2 - start.weekday()) % 7
    current = start + timedelta(days=days_to_wed)
    wednesdays: List[date] = []
    while current <= end:
        wednesdays.append(current)
        current += timedelta(days=7)
    return wednesdays


def fetch_trading_days(
    start: date,
    end: date,
    ticker: str = "SPY",
    buffer_days: int = 7,
) -> list[date]:
    if start > end:
        return []

    today = date.today()

    # 🔑 FUTURE QUARTER: do NOT call Yahoo
    if start > today:
        return [
            d.date()
            for d in pd.bdate_range(start=start, end=end)
        ]

    price_end = end + timedelta(days=buffer_days)
    panel = fetch_close_price_panel([ticker], start, price_end)
    if panel.empty:
        raise ValueError(
            f"No trading data returned for {ticker} between {start} and {price_end}."
        )
    return sorted(panel.index)


def shift_wednesdays_to_trading_days(
    wednesdays: List[date],
    trading_days: List[date],
) -> List[date]:
    if not wednesdays:
        return []
    if not trading_days:
        raise ValueError("No trading days available to shift Wednesday dates.")

    trading_set = set(trading_days)
    shifted: List[date] = []
    for wed in wednesdays:
        if wed in trading_set:
            shifted.append(wed)
            continue
        idx = bisect_right(trading_days, wed)
        if idx >= len(trading_days):
            raise ValueError(f"No trading day after {wed}.")
        shifted.append(trading_days[idx])
    return shifted
