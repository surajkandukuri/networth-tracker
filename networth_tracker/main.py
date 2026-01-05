from __future__ import annotations

from networth_tracker.template import build_email_html

def run() -> None:
    html = build_email_html()
    print("=== NETWORTH TRACKER OUTPUT START ===")
    print(html)
    print("=== NETWORTH TRACKER OUTPUT END ===")
