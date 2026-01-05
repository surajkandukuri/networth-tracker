from __future__ import annotations

from html import escape

def markdown_table_to_html(md: str) -> str:
    """Convert a GitHub-flavored markdown table to a simple HTML table.

    Assumptions:
    - Table rows are pipe-separated.
    - Second row is a separator row containing dashes and colons.
    - Cells may have alignment colons, but we keep it simple.
    """
    lines = [ln.strip() for ln in md.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return f"<pre>{escape(md)}</pre>"

    # Remove leading/trailing pipes for each line
    def split_row(row: str) -> list[str]:
        row = row.strip()
        if row.startswith("|"):
            row = row[1:]
        if row.endswith("|"):
            row = row[:-1]
        return [c.strip() for c in row.split("|")]

    header = split_row(lines[0])
    # skip separator
    body_rows = [split_row(ln) for ln in lines[2:]]

    html = []
    html.append('<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; font-family:Arial, sans-serif; font-size: 13px;">')
    html.append("<thead><tr>")
    for h in header:
        html.append(f"<th style='text-align:left; background:#f2f2f2;'>{escape(h)}</th>")
    html.append("</tr></thead>")
    html.append("<tbody>")
    for r in body_rows:
        html.append("<tr>")
        for c in r:
            # keep original formatting like **TOTAL** by stripping markdown bold
            c_clean = c.replace("**", "")
            html.append(f"<td>{escape(c_clean)}</td>")
        html.append("</tr>")
    html.append("</tbody></table>")
    return "".join(html)
