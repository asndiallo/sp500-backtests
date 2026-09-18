"""Static matplotlib charts for REPORT.md. One fixed colour per scenario everywhere."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import pandas as pd  # noqa: E402

COLORS = {"baseline_hold": "#1f77b4", "trailing_stop_25": "#ff7f0e", "buy_the_dip_25_50": "#2ca02c",
          "index": "#222222", "top10": "#9467bd"}
LABELS = {"baseline_hold": "Baseline hold", "trailing_stop_25": "25% trailing stop → index",
          "buy_the_dip_25_50": "Buy the dip −25%/−50%", "index": "Index leg (S&P 500 TR)",
          "top10": "Top-10 equal-weight, baseline hold"}
EVENT_MARKERS = {"trailing_stop_sell": ("v", "trailing_stop_25"), "add_25": ("^", "buy_the_dip_25_50"),
                 "add_50": ("^", "buy_the_dip_25_50")}


def _money(ax):
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v / 1e6:,.1f}M" if v >= 1e6
                                                     else f"${v / 1e3:,.0f}k"))


def _save(fig, path: Path):
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def growth_chart(values: dict[str, pd.DataFrame], window: str, path: Path, contributions: pd.Series):
    """values: rule -> daily frame with 'strategy' and 'index_leg' columns."""
    fig, ax = plt.subplots(figsize=(11, 6))
    for rule, df in values.items():
        ax.plot(df.index, df["strategy"], color=COLORS[rule], lw=1.4, label=f"#1 stock leg — {LABELS[rule]}")
    any_df = next(iter(values.values()))
    ax.plot(any_df.index, any_df["index_leg"], color=COLORS["index"], lw=1.6, ls="--", label=LABELS["index"])
    ax.plot(contributions.index, contributions.values, color="#999999", lw=1, ls=":",
            label="Cumulative $500/quarter contributions")
    ax.set_yscale("log")
    _money(ax)
    ax.set_title(f"Growth of $500/quarter, {window} (fresh DCA from the window start, log scale)")
    ax.grid(alpha=0.3, which="both")
    ax.legend(loc="upper left", fontsize=9)
    _save(fig, path)


def drawdown_chart(dd: dict[str, pd.Series], events: dict[str, pd.DataFrame], window: str, path: Path):
    """dd: rule -> daily drawdown of the stock leg's time-weighted unit value (plus 'index').
    Top panel: weekly drawdown lines. Bottom strip: when each rule fired (ticker x lots)."""
    fig, (ax, axe) = plt.subplots(2, 1, figsize=(12, 7.5), sharex=True, gridspec_kw={"height_ratios": [3.2, 1]})
    for rule, s in dd.items():
        w = s.resample("W-FRI").min()
        ax.plot(w.index, w.values, color=COLORS[rule], lw=1.8 if rule == "index" else 1.3,
                ls="--" if rule == "index" else "-",
                label=f"{LABELS[rule]}{'' if rule == 'index' else ' (stock leg)'} — max {s.min():.0%} "
                      f"({s.idxmin():%Y-%m})")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_title(f"Drawdown from peak of each leg's time-weighted unit value, {window}\n"
                 "(contributions stripped out; weekly lows)")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left", fontsize=8)
    lanes = {"trailing_stop_25": (1.0, ["trailing_stop_sell"]), "buy_the_dip_25_50": (0.0, ["add_25", "add_50"])}
    for rule, (y, acts) in lanes.items():
        ev = events[rule][events[rule].action.isin(acts)]
        for i, (d, g) in enumerate(ev.groupby("date")):
            marker, ck = EVENT_MARKERS[g.action.iloc[0]]
            axe.scatter([d], [y], marker=marker, s=25 + 6 * len(g), color=COLORS[ck], edgecolor="black",
                        linewidths=0.4, zorder=5)
            label = " ".join(f"{t}×{n}" for t, n in g.groupby("ticker").size().items())
            step = 9 + 12 * (i % 2)  # stagger neighbouring labels
            axe.annotate(label, (d, y), xytext=(0, step if y else -step - 6), textcoords="offset points",
                         fontsize=6.5, ha="center", color=COLORS[ck])
    axe.set_yticks([1, 0], ["trailing-stop\nsales ▼", "dip\ntop-ups ▲"], fontsize=8)
    axe.set_ylim(-1.6, 2.6)
    axe.grid(axis="x", alpha=0.3)
    axe.set_title("When the rules fired (quarterly checks; label = ticker × lots)", fontsize=9)
    _save(fig, path)


def xirr_bars(table: pd.DataFrame, path: Path):
    """table: rows for the three rules x two windows, plus the top-10 row."""
    rules = ["baseline_hold", "trailing_stop_25", "buy_the_dip_25_50"]
    windows = ["1975–2026", "1995–2026"]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12, 5.5), gridspec_kw={"width_ratios": [3, 1]})
    width = 0.36
    for i, rule in enumerate(rules):
        for j, win in enumerate(windows):
            r = table[(table.rule == rule) & (table.window == win)].iloc[0]
            x = i + (j - 0.5) * width
            ax.bar(x, r.stock_leg_xirr, width, color=COLORS[rule], alpha=1.0 if j == 0 else 0.55,
                   hatch="" if j == 0 else "//", edgecolor="black", linewidth=0.5)
            ax.text(x, max(r.stock_leg_xirr, r.index_leg_xirr) + 0.003, f"{r.stock_leg_xirr:.1%}",
                    ha="center", fontsize=8, fontweight="bold")
            ax.hlines(r.index_leg_xirr, x - width / 2, x + width / 2, color=COLORS["index"], lw=2.2)
    ax.set_xticks(range(len(rules)), [LABELS[r] for r in rules], fontsize=9)
    ax.bar(0, 0, color="white", edgecolor="black", label="1975–2026 (solid)")
    ax.bar(0, 0, color="white", edgecolor="black", hatch="//", label="1995–2026 (hatched)")
    ax.hlines([], 0, 0, color=COLORS["index"], lw=2.2, label="index-leg XIRR, same window")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_ylim(0, max(table.stock_leg_xirr.max(), table.index_leg_xirr.max()) * 1.18)
    ax.set_title("#1 stock-leg XIRR by rule and window (black bar = index leg)")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    t = table[table.rule == "top10"].iloc[0]
    ax2.bar(0, t.stock_leg_xirr, 0.5, color=COLORS["top10"], edgecolor="black", linewidth=0.5)
    ax2.text(0, max(t.stock_leg_xirr, t.index_leg_xirr) + 0.003, f"{t.stock_leg_xirr:.1%}", ha="center",
             fontsize=8, fontweight="bold")
    ax2.hlines(t.index_leg_xirr, -0.25, 0.25, color=COLORS["index"], lw=2.2)
    ax2.set_xticks([0], [f"Top-10 EW\n({t.window} only)"], fontsize=9)
    ax2.set_xlim(-0.8, 0.8)
    ax2.set_ylim(ax.get_ylim())
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax2.set_title("Different window —\nnot comparable to the left", fontsize=10)
    ax2.grid(axis="y", alpha=0.3)
    _save(fig, path)


def event_timeline(values: dict[str, pd.DataFrame], events: dict[str, pd.DataFrame], window: str, path: Path):
    """Growth curves of the two active rules with markers where they fired, plus
    a per-year count of lots affected."""
    fig, (ax, axb) = plt.subplots(2, 1, figsize=(12, 7.5), sharex=True, gridspec_kw={"height_ratios": [3, 1.2]})
    for rule in ("trailing_stop_25", "buy_the_dip_25_50"):
        df, ev = values[rule], events[rule]
        ax.plot(df.index, df["strategy"], color=COLORS[rule], lw=1.3, label=f"#1 stock leg — {LABELS[rule]}")
        ev = ev[ev.action.isin(EVENT_MARKERS)]
        for (d, action), g in ev.groupby(["date", "action"]):
            y = df["strategy"].reindex(df.index.union([d])).ffill().loc[d]
            marker, ck = EVENT_MARKERS[action]
            ax.scatter([d], [y], marker=marker, s=16 + 4 * len(g), color=COLORS[ck], edgecolor="black",
                       linewidths=0.4, zorder=5)
    base = values["baseline_hold"]
    ax.plot(base.index, base["strategy"], color=COLORS["baseline_hold"], lw=1, alpha=0.6,
            label=f"#1 stock leg — {LABELS['baseline_hold']} (reference)")
    ax.plot(base.index, base["index_leg"], color=COLORS["index"], ls="--", lw=1.2, label=LABELS["index"])
    ax.set_yscale("log")
    _money(ax)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8, loc="upper left")
    ax.set_title(f"When the rules fired, {window}  (▼ trailing-stop sale, ▲ dip top-up; marker size = lots)")
    counts = {}
    for rule, act in (("trailing_stop_25", ["trailing_stop_sell"]), ("buy_the_dip_25_50", ["add_25", "add_50"])):
        ev = events[rule]
        counts[rule] = ev[ev.action.isin(act)].groupby(ev.date.dt.year).size()
    years = sorted(set().union(*[c.index for c in counts.values()]))
    for k, rule in enumerate(counts):
        c = counts[rule].reindex(years, fill_value=0)
        xs = [pd.Timestamp(f"{y}-07-01") + pd.Timedelta(days=(k - 0.5) * 120) for y in years]
        axb.bar(xs, c.values, width=110, color=COLORS[rule], label=LABELS[rule])
    axb.set_ylabel("lots / year")
    axb.grid(alpha=0.3)
    axb.legend(fontsize=8)
    _save(fig, path)
