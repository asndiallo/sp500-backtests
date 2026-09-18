"""Scenario-family configs (``scenarios/<id>.toml``) and the manifest (``scenarios/index.csv``).

A family file looks like::

    id = "top1_core"
    title = "..."
    [defaults]                     # merged into every run
    picker = "top1"
    rule = "baseline_hold"
    start = "1975-01-01"
    [[runs]]
    id = "top1_trailing_stop_25"
    rule = { name = "trailing_stop", stop = 0.25 }
    [[analyses]]                   # optional post-processing hooks (sp500bt.analyses)
    name = "window_reconciliation"
    params = { ... }

TOML (stdlib ``tomllib``) is used instead of YAML: no extra dependency, and unlike
JSON it allows comments to document every assumption next to its parameter.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .config import ROOT

SCENARIOS_DIR = ROOT / "scenarios"
INDEX_CSV = SCENARIOS_DIR / "index.csv"
RUN_KEYS = {"id", "picker", "rule", "start", "end", "contrib", "freq", "corp_actions", "group", "label",
            "outputs", "tax", "check_freq", "rebuy"}


def spec_label(spec) -> str:
    """Stable label for a picker/rule spec: 'trailing_stop' + stop=0.25 -> 'trailing_stop_25'."""
    if isinstance(spec, str):
        return spec
    parts = [spec["name"]]
    for k, v in spec.items():
        if k in ("name", "label"):
            continue
        vals = v if isinstance(v, (list, tuple)) else [v]
        parts += [f"{x * 100:g}" if isinstance(x, float) and x < 1 else str(x) for x in vals]
    return spec.get("label", "_".join(parts))


def _expand(run: dict) -> list[dict]:
    """``rules = [...]`` expands one entry into a run per rule; ``{rule}`` in the id
    is replaced by the rule label (else the label is appended)."""
    if "rules" not in run:
        return [run]
    base = {k: v for k, v in run.items() if k != "rules"}
    out = []
    for rule in run["rules"]:
        label = spec_label(rule)
        rid = base["id"].format(rule=label) if "{rule}" in base["id"] else f"{base['id']}_{label}"
        out.append({**base, "id": rid, "rule": rule})
    return out


@dataclass
class Family:
    id: str
    title: str
    path: Path
    runs: list[dict]
    analyses: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def results_dir(self) -> Path:
        return ROOT / "results" / self.id

    @property
    def charts_dir(self) -> Path:
        return ROOT / "charts" / self.id


def load_family(family_id: str) -> Family:
    path = SCENARIOS_DIR / f"{family_id}.toml"
    if not path.exists():
        raise FileNotFoundError(f"no scenario config {path}")
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    if raw.get("id") != family_id:
        raise ValueError(f"{path}: id {raw.get('id')!r} must match the file name")
    defaults = raw.get("defaults", {})
    runs = []
    for r in raw.get("runs", []):
        for run in _expand({**defaults, **r}):
            unknown = set(run) - RUN_KEYS
            if unknown:
                raise ValueError(f"{path}: run {run.get('id')!r} has unknown keys {sorted(unknown)}")
            runs.append(run)
    ids = [r["id"] for r in runs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate run ids")
    return Family(family_id, raw.get("title", family_id), path, runs, raw.get("analyses", []), raw)


def family_ids() -> list[str]:
    return sorted(p.stem for p in SCENARIOS_DIR.glob("*.toml") if not p.stem.startswith("_"))


def load_index() -> pd.DataFrame:
    return pd.read_csv(INDEX_CSV, dtype=str).fillna("")


def check_index() -> list[str]:
    """Every config needs a manifest row; done / in-progress rows need a config
    (blocked / planned rows may exist before one is written)."""
    idx = load_index()
    cfg = set(family_ids())
    problems = [f"config without index.csv row: {x}" for x in sorted(cfg - set(idx.id))]
    active = set(idx[idx.status.isin(["done", "in-progress"])].id)
    problems += [f"index.csv row marked done/in-progress without config: {x}" for x in sorted(active - cfg)]
    return problems
