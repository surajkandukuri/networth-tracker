# networth_tracker/market_fetch.py
"""
No external API calls in v1.

This module is kept only for backward compatibility so older imports
won't crash. Real estate values are now read from config.yaml only.
"""

from __future__ import annotations


class MarketFetchDisabled(RuntimeError):
    pass


def get_ccad_market_by_address(*args, **kwargs):
    raise MarketFetchDisabled("Market fetch disabled: using config.yaml fallback values only.")


def get_ccad_market_by_point(*args, **kwargs):
    raise MarketFetchDisabled("Market fetch disabled: using config.yaml fallback values only.")
