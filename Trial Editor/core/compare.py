"""Comparison maths: the current trial versus a pinned baseline.

Pure functions over two `simulate()` results, so this is testable without
Streamlit and reusable across whatever you want to diff (a patch, another
rotation, a teammate's build).

Abilities are matched by id, not by position, so reordering a field sequence or
renaming a rotation does not look like "everything changed".
"""

from __future__ import annotations

from typing import Any

EPS = 1e-9


def _metric(current: float, baseline: float) -> dict:
    pct = (current - baseline) / baseline if abs(baseline) > EPS else None
    return {
        "current": current,
        "baseline": baseline,
        "delta": current - baseline,
        "pct": pct,
    }


def diff_results(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    current_totals = current["totals"]
    baseline_totals = baseline["totals"]

    abilities: dict[str, dict] = {}
    for source, key in ((current, "current"), (baseline, "baseline")):
        for ability_id, info in source["by_ability"].items():
            row = abilities.setdefault(
                ability_id,
                {
                    "ability": ability_id,
                    "name": info["name"],
                    "character": info["character"],
                    "current": 0.0,
                    "baseline": 0.0,
                },
            )
            row[key] = info["damage"]

    rows: list[dict] = []
    for row in abilities.values():
        delta = row["current"] - row["baseline"]
        rows.append(
            {
                **row,
                "delta": delta,
                "pct": (delta / row["baseline"]) if abs(row["baseline"]) > EPS else None,
            }
        )
    rows.sort(key=lambda item: abs(item["delta"]), reverse=True)

    return {
        "totals": {
            "damage": _metric(current_totals["damage"], baseline_totals["damage"]),
            "dps": _metric(current_totals["dps"], baseline_totals["dps"]),
            "hits": _metric(current_totals["hits"], baseline_totals["hits"]),
        },
        "abilities": rows,
        "changed": any(abs(row["delta"]) > 1e-6 for row in rows),
    }


def format_delta(delta: float, *, digits: int = 0) -> str:
    """`+1,234` / `-98` / `0`, for `st.metric(delta=...)`."""
    if abs(delta) < 0.5:
        return "0"
    return f"{delta:+,.{digits}f}"
