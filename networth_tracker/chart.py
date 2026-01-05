from __future__ import annotations

import matplotlib.pyplot as plt


def _fmt_money_short(x: float) -> str:
    if x >= 1_000_000_000:
        return f"{x/1_000_000_000:.2f}B"
    if x >= 1_000_000:
        return f"{x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"{x/1_000:.0f}K"
    return f"{x:.0f}"


def make_simple_line_chart(
    quarters: list[str],
    series: list[dict],
    outfile: str,
):
    """Simple line chart: no legend, no clutter, end-of-line labels only."""
    fig = plt.figure()
    ax = fig.add_subplot(111)

    for s in series:
        ax.plot(quarters, s["values"])
        x_last = quarters[-1]
        y_last = s["values"][-1]
        label = f'{s["name"]} — ${_fmt_money_short(y_last)} (Target: {s["target_year"]})'
        ax.annotate(label, (x_last, y_last), xytext=(6, 0), textcoords="offset points", va="center")

    ax.set_xlabel("Quarter")
    ax.set_ylabel("Portfolio Value ($)")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    fig.savefig(outfile, dpi=200)
    plt.close(fig)
