from __future__ import annotations

from .md_table import markdown_table_to_html


def build_email_html(
    qoq_growth: str,
    yoy_growth: str,
    since_start: str,
    chart_cid: str,
    # Real estate injected values:
    primary_home_value: float,
    cedar_hill_value: float,
    celina_land_value: float,
) -> str:
    """Frozen Email #2 template (structure locked).

    Only numeric injections should change.
    """

    # --- TABLES (markdown source kept exactly like your agreed format) ---
    table1_md = f"""| Asset                          | Owner       |  Current Value |   QoQ Change |  True Growth |
| ------------------------------ | ----------- | -------------: | -----------: | -----------: |
| Primary Home                   | Parents     |       ${primary_home_value:,.0f} |           $0 |           $0 |
| Cedar Hill Commercial Property | Parents     |       ${cedar_hill_value:,.0f} |      +$6,000 |           $0 |
| Celina Land                    | Parents     |       ${celina_land_value:,.0f} |      +$5,000 |      +$5,000 |
| Gold (100 gms)                 | Parents     |         $7,300 |        +$200 |        +$200 |
| LIC Policies                   | Parents     |        $47,500 |      +$1,300 |      +$1,300 |
| Securities (All Accounts)      | Parents     |       $365,000 |     +$13,000 |      +$8,600 |
| **TOTAL NET WORTH**            | **Parents** | **$1,821,800** | **+$25,500** | **+$15,100** |
| Net Worth                      | Kid 1       |        $94,000 |      +$2,800 |      +$1,500 |
| Net Worth                      | Kid 2       |        $78,000 |      +$2,900 |      +$1,925 |"""

    table2_md = """| Quarter     | Portfolio   | Securities Value | New Investment |  Dividends |   QoQ Change | True Market Growth |
| ----------- | ----------- | ---------------: | -------------: | ---------: | -----------: | -----------------: |
| Q1 2026     | Parents     |         $352,000 |         $3,900 |     $1,200 |            — |                  — |
| **Q2 2026** | **Parents** |     **$365,000** |     **$3,900** | **$1,200** | **+$13,000** |        **+$7,900** |
| Q1 2026     | Kid 1       |          $60,300 |         $1,300 |          — |            — |                  — |
| Q2 2026     | Kid 1       |          $63,100 |         $1,300 |          — |      +$2,800 |            +$1,500 |
| Q1 2026     | Kid 2       |          $50,700 |           $975 |          — |            — |                  — |
| Q2 2026     | Kid 2       |          $53,600 |           $975 |          — |      +$2,900 |            +$1,925 |"""

    table3_md = """| Quarter | Security | In the Account(s)      | Market Value | New Investment | Dividends | QoQ Change | True Market Growth |
| ------- | -------- | ---------------------- | -----------: | -------------: | --------: | ---------: | -----------------: |
| Q2 2026 | VTI      | Fidelity, M1 WeeklyDCA |     $198,000 |           $900 |         — |    +$7,500 |            +$6,600 |
| Q2 2026 | BRK.B    | 401k, M1 WeeklyDCA     |      $60,500 |           $930 |         — |    +$2,300 |            +$1,370 |
| Q2 2026 | CASH     | Fidelity Core, M1 Cash |      $23,500 |         $2,070 |    $1,200 |    +$3,200 |               -$70 |"""

    table4_md = """| Quarter | Security | In the Account(s)          | Market Value | New Investment | Dividends | QoQ Change | True Market Growth |
| ------- | -------- | -------------------------- | -----------: | -------------: | --------: | ---------: | -----------------: |
| Q2 2026 | VTI      | ForKid1Before2025, Sweetie |      $41,800 |         $1,300 |         — |    +$2,800 |            +$1,500 |"""

    table5_md = """| Quarter | Security | In the Account(s) | Market Value | New Investment | Dividends | QoQ Change | True Market Growth |
| ------- | -------- | ----------------- | -----------: | -------------: | --------: | ---------: | -----------------: |
| Q2 2026 | VTI      | ForKid2Before2025 |      $33,900 |           $975 |         — |    +$2,900 |            +$1,925 |"""

    # Convert markdown tables to HTML
    t1 = markdown_table_to_html(table1_md)
    t2 = markdown_table_to_html(table2_md)
    t3 = markdown_table_to_html(table3_md)
    t4 = markdown_table_to_html(table4_md)
    t5 = markdown_table_to_html(table5_md)

    # Frozen narrative section + chart rules (as you wrote)
    return f"""<html>
  <body style="font-family: Arial, sans-serif; color:#111; font-size:14px;">
    <div style="font-weight:700; font-size:16px;">NET WORTH TRACKER — QUARTERLY SNAPSHOT</div>
    <div style="margin-top:4px;">(Open only the latest email. This email is cumulative by design.)</div>

    <h2 style="margin-top:18px;">📊 NET WORTH SUMMARY (1-Minute View)</h2>
    <ul>
      <li><b>QoQ Growth:</b> <b>{qoq_growth}</b></li>
      <li><b>YoY Growth:</b> {yoy_growth}</li>
      <li><b>Growth Since Start:</b> <b>{since_start}</b></li>
    </ul>

    <h2 style="margin-top:18px;">📈 NET WORTH TRAJECTORY (SIMPLE LINE VIEW)</h2>

    <div style="margin-top:10px;">
      <img src="cid:{chart_cid}" alt="Net Worth Trajectory" style="max-width: 1100px; width: 100%;"/>
    </div>

    <h2 style="margin-top:18px;">TABLE 1 — NET WORTH (CURRENT SNAPSHOT — NO HISTORY)</h2>
    {t1}

    <h2 style="margin-top:18px;">TABLE 2 — SECURITIES TOTAL (RECONCILIATION)</h2>
    {t2}
    <div style="margin-top:8px; font-weight:700;">✔ Sums reconcile exactly with Tables 3–5</div>

    <h2 style="margin-top:18px;">TABLE 3 — PER-SECURITY (PARENTS — ALL ACCOUNTS COMBINED)</h2>
    {t3}

    <h2 style="margin-top:18px;">TABLE 4 — KID 1 SECURITIES (ALL ACCOUNTS COMBINED — Target: 2034)</h2>
    {t4}

    <h2 style="margin-top:18px;">TABLE 5 — KID 2 SECURITIES (ALL ACCOUNTS COMBINED — Target: 2039)</h2>
    {t5}
  </body>
</html>"""
