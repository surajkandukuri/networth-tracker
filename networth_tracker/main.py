# networth_tracker/main.py
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from networth_tracker.config import load_config
from networth_tracker.template import build_email_html
from networth_tracker.chart import build_simple_line_chart
from networth_tracker.gmail_api import send_email_html_with_inline_image


SNAPSHOT_DIR = Path("snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
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
    notes: str = ""


def _safe_float(x: Any, default: Optional[float] = 0.0) -> Optional[float]:
    """
    Converts values to float safely. If default=None, returns None on failure.
    """
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_latest_snapshot() -> Dict[str, Any]:
    if not LATEST_SNAPSHOT_PATH.exists():
        return {}
    try:
        return json.loads(LATEST_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_latest_snapshot(snapshot: Dict[str, Any]) -> None:
    LATEST_SNAPSHOT_PATH.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _get_assumptions(cfg: Dict[str, Any]) -> Tuple[float, float]:
    """
    Returns (inflation_qoq_pct, hpi_qoq_pct). No external API calls.
    """
    assumptions = cfg.get("assumptions", {}) or {}
    inflation_qoq_pct = _safe_float(assumptions.get("inflation_qoq_pct", 0.5), 0.5) or 0.5
    hpi_qoq_pct = _safe_float(assumptions.get("hpi_qoq_pct", 0.0), 0.0) or 0.0
    return float(inflation_qoq_pct), float(hpi_qoq_pct)


def _apply_mode_adjustment(mode: str, base_value: float, cfg: Dict[str, Any]) -> float:
    """
    No API calls. Deterministic adjustments based on config assumptions.
    """
    inflation_qoq_pct, hpi_qoq_pct = _get_assumptions(cfg)
    mode = (mode or "").strip()

    if mode in ("fallback_only", "fallback_value", ""):
        return base_value

    if mode == "inflation_ish":
        return base_value * (1.0 + inflation_qoq_pct / 100.0)

    if mode == "cad_times_hpi":
        # No HPI API: use configured drift only.
        return base_value * (1.0 + hpi_qoq_pct / 100.0)

    # Unknown mode -> do nothing
    return base_value


def _label_for_key(key: str) -> str:
    if key == "primary_home":
        return "Primary Home"
    if key == "cedar_hill_commercial":
        return "Cedar Hill Commercial Property"
    if key == "celina_land":
        return "Celina Land"
    return key.replace("_", " ").title()


def _compute_real_estate(cfg: Dict[str, Any]) -> Dict[str, RealEstateValue]:
    re_cfg = cfg.get("real_estate", {}) or {}
    out: Dict[str, RealEstateValue] = {}

    for key, obj in re_cfg.items():
        if not isinstance(obj, dict):
            continue

        county = str(obj.get("county", "")).strip()
        mode = str(obj.get("mode", "fallback_only")).strip()
        ownership_pct = _safe_float(obj.get("ownership_pct", 1.0), 1.0) or 1.0
        fallback_value = _safe_float(obj.get("fallback_value", 0.0), 0.0) or 0.0
        notes = str(obj.get("notes", "") or "").strip()

        adjusted = _apply_mode_adjustment(mode, float(fallback_value), cfg)
        owned = float(adjusted) * float(ownership_pct)

        out[key] = RealEstateValue(
            key=key,
            label=_label_for_key(key),
            mode=mode,
            county=county,
            ownership_pct=float(ownership_pct),
            fallback_value=float(fallback_value),
            adjusted_value=float(adjusted),
            owned_value=float(owned),
            notes=notes,
        )

    return out


def _compute_qoq_changes(real_estate: Dict[str, RealEstateValue], latest_snapshot: Dict[str, Any]) -> Dict[str, float]:
    prev_re = {}
    if isinstance(latest_snapshot, dict):
        prev_re = latest_snapshot.get("real_estate", {}) or {}
    if not isinstance(prev_re, dict):
        prev_re = {}

    qoq_changes: Dict[str, float] = {}
    for k, v in real_estate.items():
        prev_val = _safe_float(prev_re.get(k), None)
        if prev_val is None:
            qoq_changes[k] = 0.0
        else:
            qoq_changes[k] = float(v.owned_value) - float(prev_val)

    return qoq_changes


def _owned_value(real_estate: Dict[str, RealEstateValue], key: str) -> float:
    val = real_estate.get(key)
    if isinstance(val, RealEstateValue):
        return float(val.owned_value)
    return 0.0


def run() -> None:
    cfg_obj = load_config("config.yaml")
    cfg = cfg_obj.raw

    # 0) Dry-run flag
    dry_run = bool((cfg.get("run", {}) or {}).get("dry_run", False))

    # 1) Load previous snapshot (for QoQ + chart)
    latest_snapshot = _load_latest_snapshot()

    # 2) Compute real estate values (CONFIG ONLY — no API)
    real_estate = _compute_real_estate(cfg)

    # 3) Compute QoQ deltas (based on last snapshot)
    qoq_changes = _compute_qoq_changes(real_estate, latest_snapshot)

    # 4) Save new snapshot for next run
    snapshot_payload: Dict[str, Any] = {
        "generated_at_utc": _now_utc_iso(),
        "real_estate": {k: v.owned_value for k, v in real_estate.items()},
    }
    _save_latest_snapshot(snapshot_payload)

    # 5) Build chart image (should use snapshot history logic inside your chart module)
    chart_path = build_simple_line_chart(cfg, latest_snapshot)

    # 6) Render frozen email HTML (inject real estate values + QoQ deltas)
    email_html = build_email_html(
        qoq_growth="+3.1%",
        yoy_growth="*N/A (need 4 quarters)*",
        since_start="+6.6%",
        chart_cid="networth_chart",
        primary_home_value=_owned_value(real_estate, "primary_home"),
        cedar_hill_value=_owned_value(real_estate, "cedar_hill_commercial"),
        celina_land_value=_owned_value(real_estate, "celina_land"),
    )

    if dry_run:
        # In dry-run mode, do not send email. Keep artifact for debugging if needed.
        debug_path = SNAPSHOT_DIR / "last_email_preview.html"
        debug_path.write_text(email_html, encoding="utf-8")
        print(f"[DRY RUN] Email rendered. Preview saved to: {debug_path}")
        print(f"[DRY RUN] Chart saved to: {chart_path}")
        return

    # 7) Send email
    subject = cfg["email"]["subject"]
    from_addr = cfg["email"]["from"]
    to_addr = cfg_obj.env_email_to()

    send_email_html_with_inline_image(
        subject=subject,
        sender=from_addr,
        to=to_addr,
        html_body=email_html,
        inline_png_path=chart_path,
        inline_cid="networth_chart",
    )
