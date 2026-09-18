"""Scenario summary metrics shared by scripts/run_scenarios.py and the notebook."""
from __future__ import annotations

from .engine import SimResult


def summarize(res: SimResult, name: str = "scenario", **meta) -> dict:
    """Invested, ending value, money-weighted multiple and XIRR (actual cashflow
    dates) for the strategy leg, the index leg and the combined portfolio."""
    led = res.ledger.groupby("leg").amount.sum()
    stock_in = led.filter(like="stock").sum()
    index_in = led.get("index", 0.0)
    ev = res.events
    return {
        **meta, "scenario": name, "valued_at": res.end.date(),
        "contributions": int((res.ledger.leg == "stock").sum()),
        "strategy_invested": stock_in, "dip_add_invested": led.get("stock_dip_add", 0.0),
        "index_invested": index_in, "total_invested": stock_in + index_in,
        "strategy_value": res.final["strategy_value"], "index_leg_value": res.final["index_leg_value"],
        "total_value": res.final["total"],
        "strategy_multiple": res.final["strategy_value"] / stock_in,
        "index_multiple": res.final["index_leg_value"] / index_in,
        "total_multiple": res.final["total"] / (stock_in + index_in),
        "strategy_xirr": res.xirr("stock"), "index_xirr": res.xirr("index"), "total_xirr": res.xirr(),
        "stop_outs": int((ev.action == "trailing_stop_sell").sum()) if len(ev) else 0,
        "dip_adds": int(ev.action.str.startswith("add_").sum()) if len(ev) else 0,
    }
