from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, List, Tuple

import pandas as pd

from .dca import build_dca_schedule
from .pricing import fetch_close_price_panel, normalize_ticker


@dataclass(frozen=True)
class QuarterQuantityResult:
    df: pd.DataFrame
    quarter_start: date
    quarter_end: date


def _collect_investment_dates(schedule_df: pd.DataFrame) -> List[date]:
    dates: List[date] = []
    for items in schedule_df["investment_dates"]:
        dates.extend(items)
    return sorted(set(dates))


def _find_missing_prices(
    price_panel: pd.DataFrame,
    tickers: Iterable[str],
    dates: Iterable[date],
) -> List[Tuple[str, date]]:
    missing: List[Tuple[str, date]] = []
    for ticker in tickers:
        if ticker not in price_panel.columns:
            for dt in dates:
                missing.append((ticker, dt))
            continue
        for dt in dates:
            if dt not in price_panel.index or pd.isna(price_panel.at[dt, ticker]):
                missing.append((ticker, dt))
    return missing


def compute_quarter_quantities(
    securities_df: pd.DataFrame,
    quarter_start: date,
    quarter_end: date,
) -> QuarterQuantityResult:
    schedule_result = build_dca_schedule(securities_df, quarter_start, quarter_end)
    schedule_df = schedule_result.df

    investment_dates = _collect_investment_dates(schedule_df)
    if investment_dates:
        price_start = min(investment_dates)
        price_end = max(investment_dates)
        tickers = [normalize_ticker(t) for t in schedule_df["security"].tolist()]
        price_panel = fetch_close_price_panel(tickers, price_start, price_end)
    else:
        price_panel = pd.DataFrame()

    computed_rows = []
    for _, row in schedule_df.iterrows():
        row_type = row["type"]
        security = str(row["security"]).strip()
        normalized = normalize_ticker(security)
        dates = row["investment_dates"]
        starting_quantity = float(row["starting_quantity"])
        invested_dollars = float(row["invested_dollars"])

        if row_type == "Active":
            missing = _find_missing_prices(price_panel, [normalized], dates)
            if missing:
                formatted = ", ".join(f"{t}@{d.isoformat()}" for t, d in missing)
                raise ValueError(f"Missing close prices for: {formatted}")

            shares_added = 0.0
            for dt in dates:
                close_price = float(price_panel.at[dt, normalized])
                shares_added += float(row["weekly_investment_dollars"]) / close_price

            ending_quantity = starting_quantity + shares_added
            avg_purchase_price = (
                invested_dollars / shares_added if shares_added else None
            )
        else:
            shares_added = 0.0
            ending_quantity = starting_quantity
            avg_purchase_price = None

        computed = row.to_dict()
        computed["shares_added"] = shares_added
        computed["ending_quantity"] = ending_quantity
        computed["avg_purchase_price"] = avg_purchase_price
        computed_rows.append(computed)

    result_df = pd.DataFrame(computed_rows)
    return QuarterQuantityResult(
        df=result_df, quarter_start=quarter_start, quarter_end=quarter_end
    )
