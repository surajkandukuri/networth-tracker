# networth_tracker/main.py
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from networth_tracker.config import load_config
from networth_tracker.template import render_email_html  # your existing renderer
from networth_tracker.chart import build_simple_line_chart  # your existing chart builder
from networth_tracker.gmail_api import send_email_with_inline_image  # your existing gmail sender


SNAPSHOT_DIR = Path("snapshots")
SNAPSHOT_DIR.mkdir(exist_ok=True)
LATEST_SNAPSHOT_PATH = SNAPSHOT_DIR / "latest.json"


@dataclass
class RealEstateValue:
    key: str
    label: str
    mode: str
    county: str
    ownership_pct: float
    fallback_value: float
    adjusted_value: float
    owned_value: float


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _load_latest_snapshot() -> Dict[str, Any]:
    if not LATEST_SNAPSHOT_PATH.exists():
        return {}
    try:
        return json.loads(LATEST_SNAPSHOT_PATH.read_text())
    except Exception:
        return {}


def _save_latest_snapshot(snapshot: Dict[str, Any]) -> None:
    LATEST_SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True))


def _apply_mode_adjustment(mode: str, base_value: float, cfg: Dict[str, Any]) -> float:
    """
    No API calls. Only deterministic, config-driven adjustments.
    """
    assumptions = cfg.get("assumptions", {}) or {}
    inflation_qoq_pct = _safe_float(assumptions.get("inflation_qoq_pct", 0.5), 0.5)
    hpi_qoq_pct = _safe_float(assumptions.get("hpi_qoq_pct", 0.0), 0.0)

    if mode == "fallback_only":
        return base_value

    if mode == "inflation_ish":
        return base_value * (1.0 + inflation_qoq_pct / 100.0)

    if mode == "cad_times_hpi":
        # No HPI API. Use configured drift % (default 0.0).
        return base_value * (1.0 + hpi_qoq_pct / 100.0)

    # Unknown mode -> do nothing
    return base_value


def _compute_real_estate(cfg: Dict[str, Any]) -> Dict[str, RealEstateValue]:
    re_cfg = cfg.get("real_estate", {}) or {}
    out: Dict[str, RealEstateValue] = {}

    for key, obj in re_cfg.items():
        county = str(obj.get("county", "")).strip()
        mode = str(obj.get("mode", "fallback_only")).strip()
        ownership_pct = _safe_float(obj.get("ownership_pct", 1.0), 1.0)
        fallback_value = _safe_float(obj.get("fallback_value", 0.0), 0.0)

        adjusted = _apply_mode_adjustment(mode, fallback_value, cfg)
        owned = adjusted * ownership_pct

        # Nice labels for email
        if key == "primary_home":
            label = "Primary Home"
        elif key == "cedar_hill_commercial":
            label = "Cedar Hill Commercial Property"
        elif key == "celina_land":
            label = "Celina Land"
        else:
            label = key.replace("_", " ").title()

        out[key] = RealEstateValue(
            key=key,
            label=label,
            mode=mode,
            county=county,
            ownership_pct=ownership_pct,
            fallback_value=fallback_value,
            adjusted_value=adjusted,
            owned_value=owned,
        )

    return out


def run() -> None:
    cfg = load_config("config.yaml")

    # 1) Compute values (no API)
    latest_snapshot = _load_latest_snapshot()
    real_estate = _compute_real_estate(cfg)

    # 2) Build a minimal snapshot payload for QoQ (only things we can do now)
    #    We keep it future-proof so later we can add securities auto-fetch without changing email structure.
    now = datetime.utcnow().isoformat()
    snapshot_payload: Dict[str, Any] = {
        "generated_at_utc": now,
        "real_estate": {k: v.owned_value for k, v in real_estate.items()},
    }

    # 3) Compute QoQ deltas for real estate (if previous exists)
    prev_re = (latest_snapshot.get("real_estate", {}) or {}) if isinstance(latest_snapshot, dict) else {}
    qoq_changes: Dict[str, float] = {}
    for k, v in real_estate.items():
        prev_val = _safe_float(prev_re.get(k, None), None) if prev_re else None
        if prev_val is None:
            qoq_changes[k] = 0.0
        else:
            qoq_changes[k] = v.owned_value - float(prev_val)

    # 4) Save snapshot for next run
    _save_latest_snapshot(snapshot_payload)

    # 5) Build chart (your existing 2-point simple line view)
    chart_cfg = cfg.get("chart", {}) or {}
    # Your chart code likely expects two points. Use snapshot + current.
    # If no previous snapshot, draw a flat start point from current (so it still works).
    chart_data = []
    for series in chart_cfg.get("series", []):
        name = series["name"]
        # For now, we only have totals; you already hard-code securities totals in template.
        # Keep chart data based on the same totals you already use in template logic.
        # If your chart module already takes precomputed totals, keep that contract.
        chart_data.append({"name": name})

    # NOTE: If your existing chart builder already reads a snapshot file, keep it.
    chart_path = build_simple_line_chart(cfg, latest_snapshot)

    # 6) Render email HTML using existing frozen template logic
    #    We only inject real-estate owned values + QoQ deltas.
    email_html = render_email_html(cfg, real_estate, qoq_changes)

    # 7) Send email
    subject = cfg["email"]["subject"]
    from_addr = cfg["email"]["from"]
    to_addr_env = cfg["email"]["to_env"]

    # gmail_api.py likely reads EMAIL_TO from env (as you designed). Keep that.
    send_email_with_inline_image(
        subject=subject,
        html_body=email_html,
        inline_image_path=chart_path,
        from_addr=from_addr,
    )
