from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .chart import make_simple_line_chart
from .config import Config
from .gmail_api import send_email_html_with_inline_image
from .market_fetch import (
    get_ccad_market_by_address,
    get_ccad_market_by_point,
    get_dallas_mkt_value_by_address,
)
from .template import build_email_html


SNAPSHOT_DIR = Path("snapshots")
SNAPSHOT_DIR.mkdir(exist_ok=True)


def _quarter_label(dt: datetime) -> str:
    q = (dt.month - 1) // 3 + 1
    return f"Q{q} {dt.year}"


def _load_latest_snapshot() -> dict | None:
    latest = SNAPSHOT_DIR / "latest.json"
    if not latest.exists():
        return None
    return json.loads(latest.read_text(encoding="utf-8"))


def _save_snapshot(snapshot: dict) -> None:
    ts = snapshot["timestamp"].replace(":", "").replace("-", "")
    fname = SNAPSHOT_DIR / f"snapshot_{ts}.json"
    fname.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    (SNAPSHOT_DIR / "latest.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def run():
    cfg = Config.load("config.yaml")
    now = datetime.now(timezone.utc)
    quarter = _quarter_label(now)

    # 1) Fetch the 3 real-estate market values (free public endpoints)
    re_cfg = cfg.raw["real_estate"]

    primary_home = get_ccad_market_by_address(
        re_cfg["primary_home"]["ccad_address"]["street_num"],
        re_cfg["primary_home"]["ccad_address"]["street_name_like"],
        re_cfg["primary_home"]["ccad_address"]["city"],
    )

    cedar_hill = get_dallas_mkt_value_by_address(
        re_cfg["cedar_hill_commercial"]["dallas_address"]["street_num"],
        re_cfg["cedar_hill_commercial"]["dallas_address"]["street_name_like"],
        re_cfg["cedar_hill_commercial"]["dallas_address"]["city"],
    )

    celina = get_ccad_market_by_point(
        re_cfg["celina_land"]["ccad_point"]["lat"],
        re_cfg["celina_land"]["ccad_point"]["lon"],
    )

    # 2) Build/update snapshot (stores values so next quarter chart has 2 points automatically)
    prev = _load_latest_snapshot()
    # For now, portfolio totals in the chart are taken from the SAMPLE email numbers.
    # We'll wire securities APIs next without changing format.
    parents_total = 1_821_800  # from sample
    kid1_total = 94_000
    kid2_total = 78_000

    snapshot = {
        "timestamp": now.isoformat(),
        "quarter": quarter,
        "real_estate": {
            "primary_home": primary_home,
            "cedar_hill_commercial": cedar_hill,
            "celina_land": celina,
        },
        "totals_for_chart": {
            "parents_dca": parents_total,
            "kid1": kid1_total,
            "kid2": kid2_total,
        },
    }

    _save_snapshot(snapshot)

    # 3) Build chart (two points: previous snapshot -> current snapshot). If no previous, duplicate current.
    prev_quarter = prev["quarter"] if prev else quarter
    quarters = [prev_quarter, quarter]

    prev_totals = prev["totals_for_chart"] if prev else snapshot["totals_for_chart"]

    chart_series_cfg = cfg.raw["chart"]["series"]
    series = [
        {"name": "Parents DCA", "target_year": chart_series_cfg[0]["target_year"], "values": [prev_totals["parents_dca"], parents_total]},
        {"name": "Kid 1", "target_year": chart_series_cfg[1]["target_year"], "values": [prev_totals["kid1"], kid1_total]},
        {"name": "Kid 2", "target_year": chart_series_cfg[2]["target_year"], "values": [prev_totals["kid2"], kid2_total]},
    ]

    chart_path = "networth_chart.png"
    make_simple_line_chart(quarters, series, chart_path)

    # 4) Build frozen Email #2 (injecting fetched real estate values)
    html = build_email_html(
        qoq_growth="+3.1%",
        yoy_growth="N/A (need 4 quarters)",
        since_start="+6.6%",
        chart_cid="chart",
        primary_home_value=primary_home,
        cedar_hill_value=cedar_hill,
        celina_land_value=celina,
    )

    dry_run = bool(cfg.raw.get("run", {}).get("dry_run", False)) or os.environ.get("DRY_RUN") == "1"
    if dry_run:
        Path("out_email.html").write_text(html, encoding="utf-8")
        print("DRY RUN: wrote out_email.html (no email sent).")
        return

    # 5) Send via Gmail API (OAuth token flow)
    to_addr = cfg.env_email_to()
    subject = cfg.raw["email"]["subject"]
    sender = cfg.raw["email"]["from"]

    res = send_email_html_with_inline_image(
        subject=subject,
        sender=sender,
        to=to_addr,
        html_body=html,
        inline_png_path=chart_path,
        inline_cid="chart",
    )
    print("Email sent. Gmail response id:", res.get("id"))


if __name__ == "__main__":
    run()
