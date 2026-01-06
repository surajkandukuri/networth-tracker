from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List

import pandas as pd

from .calendar_utils import (
    fetch_trading_days,
    list_wednesdays,
    shift_wednesdays_to_trading_days,
)


@dataclass(frozen=True)
class DcaScheduleResult:
    df: pd.DataFrame
    quarter_start: date
    quarter_end: date


def build_dca_schedule(
    securities_df: pd.DataFrame,
    quarter_start: date,
    quarter_end: date,
) -> DcaScheduleResult:
    required = {
        "owner_bucket",
        "account_name",
        "security",
        "type",
        "starting_quantity",
        "weekly_investment_dollars",
    }
    missing = sorted(required - set(securities_df.columns))
    if missing:
        raise ValueError(f"Missing required columns for DCA: {', '.join(missing)}")

    wednesdays = list_wednesdays(quarter_start, quarter_end)
    trading_days = fetch_trading_days(
        start=min(wednesdays),
        end=max(wednesdays),
    ) if wednesdays else []
    adjusted = shift_wednesdays_to_trading_days(wednesdays, trading_days)

    df = securities_df.copy()
    df["type"] = df["type"].astype(str).str.strip()
    df["weekly_investment_dollars"] = pd.to_numeric(
        df["weekly_investment_dollars"], errors="coerce"
    )

    schedule_dates: List[List[date]] = []
    num_investments: List[int] = []
    invested_dollars: List[float] = []

    for _, row in df.iterrows():
        row_type = row["type"]
        if row_type == "Active":
            dates = list(adjusted)
            count = len(dates)
            weekly = row["weekly_investment_dollars"]
            if pd.isna(weekly):
                raise ValueError("weekly_investment_dollars must be numeric for Active rows.")
            invested = float(weekly) * count
        elif row_type == "NoMoreFunding":
            dates = []
            count = 0
            invested = 0.0
        else:
            raise ValueError(f"Invalid type value for DCA schedule: {row_type}")

        schedule_dates.append(dates)
        num_investments.append(count)
        invested_dollars.append(invested)

    result = df[
        [
            "owner_bucket",
            "account_name",
            "security",
            "type",
            "starting_quantity",
            "weekly_investment_dollars",
        ]
    ].copy()
    result["investment_dates"] = schedule_dates
    result["num_investments"] = num_investments
    result["invested_dollars"] = invested_dollars

    return DcaScheduleResult(df=result, quarter_start=quarter_start, quarter_end=quarter_end)
