from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .config import Config


REQUIRED_COLUMNS = {
    "owner_bucket",
    "account_name",
    "security",
    "type",
    "starting_quantity",
    "weekly_investment_dollars",
}

ALLOWED_TYPES = {"Active", "NoMoreFunding"}

ALIAS_MAP = {
    "for": "owner_bucket",
    "category": "type",                  # <-- funding status (Active / NoMoreFunding)
    "type": "account_name",              # <-- account type (Rollover 401k, Roth IRA, etc)
    "symbol": "security",
    "quantity": "starting_quantity",
    "weekly_investment_in_dollars": "weekly_investment_dollars",
}



@dataclass(frozen=True)
class SecuritiesMasterResult:
    df: pd.DataFrame
    source_path: str


def _normalize_column(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _apply_aliases(df: pd.DataFrame) -> pd.DataFrame:
    normalized_columns = [_normalize_column(c) for c in df.columns]
    df = df.copy()
    df.columns = normalized_columns

    rename_map = {src: dst for src, dst in ALIAS_MAP.items() if src in df.columns}
    df = df.rename(columns=rename_map)

    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(
            "Missing required columns in Securities_Master.xlsx after aliasing: "
            + ", ".join(missing)
        )

    return df[list(REQUIRED_COLUMNS)]


def _strip_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("owner_bucket", "account_name", "security", "type"):
        df[col] = df[col].astype(str).str.strip()
    return df


def _validate_required_values(df: pd.DataFrame) -> None:
    errors: list[str] = []

    # 1) Required non-empty text columns
    for col in ("owner_bucket", "account_name", "security", "type"):
        blank_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        if blank_mask.any():
            rows = _one_based_rows(blank_mask)
            errors.append(f"Blank values in '{col}' at rows: {rows}")

    # If we already have missing "type", don't try further type-dependent checks
    # but we can still validate numeric fields safely.
    df["type"] = df["type"].astype(str).str.strip()

    # 2) Validate type values
    bad_type_mask = ~df["type"].isin(ALLOWED_TYPES)
    if bad_type_mask.any():
        rows = _one_based_rows(bad_type_mask)
        errors.append(
            "Invalid 'type' values (expected Active or NoMoreFunding) at rows: "
            f"{rows}"
        )

    # 3) starting_quantity must always be numeric
    df["starting_quantity"] = pd.to_numeric(df["starting_quantity"], errors="coerce")
    bad_qty_mask = df["starting_quantity"].isna()
    if bad_qty_mask.any():
        rows = _one_based_rows(bad_qty_mask)
        errors.append(f"Non-numeric values in 'starting_quantity' at rows: {rows}")

    # 4) weekly_investment_dollars: numeric REQUIRED only for Active
    df["weekly_investment_dollars"] = pd.to_numeric(
        df["weekly_investment_dollars"], errors="coerce"
    )

    active_mask = df["type"] == "Active"
    bad_weekly_active_mask = active_mask & df["weekly_investment_dollars"].isna()
    if bad_weekly_active_mask.any():
        rows = _one_based_rows(bad_weekly_active_mask)
        errors.append(
            "Non-numeric/blank values in 'weekly_investment_dollars' for Active rows at rows: "
            f"{rows}"
        )

    if errors:
        raise ValueError(
            "Securities_Master.xlsx validation failed:\n- " + "\n- ".join(errors)
        )



def _one_based_rows(mask: Iterable[bool]) -> str:
    return ", ".join(str(i + 2) for i, is_bad in enumerate(mask) if is_bad)


def read_securities_master(config_path: str = "config.yaml") -> SecuritiesMasterResult:
    config = Config.load(config_path)
    inputs = config.raw.get("inputs", {})
    path = inputs.get("securities_master_path")
    if not path:
        raise ValueError("Missing config key inputs.securities_master_path in config.yaml.")

    df = pd.read_excel(path, dtype=object)
    df = _apply_aliases(df)
    df = _strip_string_columns(df)
    _validate_required_values(df)

    return SecuritiesMasterResult(df=df, source_path=path)
