"""The numbers under the strip: metrics, warnings and the rotation log.

The full audit table (ui/table.py) stays in the results tab. What belongs here is
what the trial being edited can say about itself: its four totals, its warnings,
and one row per rotation with what that rotation actually did *inside this trial*.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

LOG_COLUMNS = ["Rotation", "Starts", "Duration", "Damage", "DPS"]


def render_issues(issues: list, *, limit: int = 8) -> None:
    """Errors, then warnings, then notes - one box each, never eight boxes."""
    for severity, show in (("error", st.error), ("warning", st.warning), ("info", st.info)):
        lines = [issue["message"] for issue in issues if issue["severity"] == severity]
        if not lines:
            continue
        body = "".join("- " + line + chr(10) for line in lines[:limit])
        if len(lines) > limit:
            body += "- and %d more" % (len(lines) - limit)
        show(body)


METRICS = (("damage", "Damage", lambda value: format(value, ",.0f")),
           ("dps", "DPS", lambda value: format(value, ",.0f")),
           ("duration", "Duration", lambda value: "%.3f s" % value),
           ("hits", "Hits", lambda value: value))


def metrics(totals: dict, *, fields=("damage", "dps", "duration", "hits")) -> None:
    """The metric row, or the subset a screen asks for.

    A rotation's damage depends on where it sits in a trial, so its own screen
    shows the loop's duration and hits only; damage belongs to the trial view.
    """
    chosen = [entry for entry in METRICS if entry[0] in fields]
    columns = st.columns(len(chosen))
    for column, (name, label, show) in zip(columns, chosen):
        column.metric(label, show(totals[name]))


def loop_totals(spec: dict, rotation_id: str, preview: dict) -> dict:
    """Numbers for one loop of a rotation, taken from the two-loop preview.

    A hit that resolves after the seam still belongs to the loop that cast it, and
    preview blocks carry their loop in the id, so the first loop is the set of
    blocks that start before the seam.
    """
    loop_time = 0.0
    rotation = spec["rotations"].get(rotation_id) or {}
    for block in rotation.get("blocks", []):
        sequence = spec["field_seqs"].get(block)
        if sequence:
            loop_time += float(sequence["field_time"])
    blocks = [b for b in preview["blocks"] if b["start"] < loop_time - 1e-9]
    ids = {b["id"] for b in blocks}
    damage = sum(preview["by_block"].get(block_id, 0.0) for block_id in ids)
    hits = sum(1 for hit in preview["hits"] if hit["block"] in ids)
    return {
        "damage": damage,
        "dps": damage / loop_time if loop_time else 0.0,
        "duration": loop_time,
        "hits": hits,
    }


def rotation_rows(spec: dict, result: dict) -> list:
    """One row per *pass* through a rotation - one per repetition, one per slot use.

    A trial plays a slot ``repeat`` times, and the same rotation can sit in several
    slots: every one of those passes is its own row, in playing order. Damage comes
    from ``by_block`` and the window from the blocks that pass actually ran, so a
    pass the trial truncated is reported truncated, and the column still adds up to
    the trial's total.
    """
    rows: dict = {}
    for block in result.get("blocks") or []:
        row = rows.setdefault(block["occurrence"], {
            "id": block["occurrence"],
            "name": (spec["rotations"].get(block["rotation"]) or {}).get(
                "name", block["rotation_name"]),
            "start": float(block["start"]),
            "damage": 0.0, "duration": 0.0, "hits": 0,
        })
        row["start"] = min(row["start"], float(block["start"]))
        row["damage"] += result["by_block"].get(block["id"], 0.0)
        row["duration"] += max(0.0, float(block["end"]) - float(block["start"]))
    occurrence_of = {block["id"]: block["occurrence"]
                     for block in result.get("blocks") or []}
    for hit in result.get("hits") or []:
        row = rows.get(occurrence_of.get(hit["block"]))
        if row is not None:
            row["hits"] += 1
    out = sorted(rows.values(), key=lambda row: row["start"])
    for row in out:
        row["dps"] = row["damage"] / row["duration"] if row["duration"] else 0.0
    return out


def render_rotation_log(spec: dict, result: dict, *,
                        key: str = "editor_rotation_log", height: int = 260) -> None:
    """The trial's rotation log: start, span, damage and DPS per rotation.

    Every number stays a number so the headers sort the way the browser expects;
    the column_config does the formatting. Damage is the trial's own by_block, so
    the column adds up to the total the metric row prints, truncation included.
    """
    rows = rotation_rows(spec, result)
    if not rows:
        st.caption("This trial has no rotations yet.")
        return
    frame = pd.DataFrame([{
        "Rotation": row["name"],
        "Starts": round(float(row["start"]), 3),
        "Duration": round(float(row["duration"]), 3),
        "Damage": round(float(row["damage"]), 1),
        "DPS": round(float(row["dps"]), 1),
    } for row in rows], columns=LOG_COLUMNS)
    st.dataframe(
        frame, key=key, hide_index=True, width="stretch", height=height,
        column_config={
            "Rotation": st.column_config.TextColumn("Rotation", width="large"),
            "Starts": st.column_config.NumberColumn("Starts", format="%.3f s", width="small"),
            "Duration": st.column_config.NumberColumn("Duration", format="%.3f s", width="small"),
            "Damage": st.column_config.NumberColumn("Damage", format="localized", width="small"),
            "DPS": st.column_config.NumberColumn("DPS", format="localized", width="small"),
        },
        alt="Damage per rotation, measured inside the trial",
    )


