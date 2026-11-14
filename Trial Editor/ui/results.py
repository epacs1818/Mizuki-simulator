"""Result widgets: the metric row, the event log, and the three library tables.

The editor renders all of these from the live trial, so a change to a rotation is
visible in the numbers on the same rerun. Nothing here mutates the model.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

SEVERITY_ICON = {
    "error": ":material/error:",
    "warning": ":material/warning:",
    "info": ":material/info:",
}


def render_metrics(result: dict, prev_damage: float | None = None) -> None:
    """DPS / total damage / trial duration / hits. Delta is vs the previous rerun."""
    totals = result["totals"]
    delta = None
    if prev_damage and abs(prev_damage) > 1e-9:
        delta = f"{(totals['damage'] - prev_damage) / prev_damage * 100:+.1f}%"

    cols = st.columns(4)
    cols[0].metric("DPS", f"{totals['dps']:,.0f}")
    cols[1].metric("Total damage", f"{totals['damage']:,.0f}", delta=delta, delta_color="normal")
    cols[2].metric("Trial duration", f"{totals['duration']:.1f}s")
    cols[3].metric("Hits", f"{totals['hits']:,}")


def render_issues(issues: list[dict], *, limit: int = 6) -> None:
    if not issues:
        st.success("Nothing to flag here.", icon=":material/check_circle:")
        return
    for issue in issues[:limit]:
        renderer = {"error": st.error, "warning": st.warning, "info": st.info}[issue["severity"]]
        renderer(issue["message"], icon=SEVERITY_ICON[issue["severity"]])
    if len(issues) > limit:
        st.caption(f"+ {len(issues) - limit} more warning(s) hidden.")


def event_frame(result: dict, spec: dict) -> pd.DataFrame:
    chars = spec["catalog"]["characters"]
    kind_label = {
        "swap_in": "swap in",
        "swap_out": "swap out",
        "hit": "hit",
        "crit": "crit",
        "trigger": "triggered",
        "buff_end": "buff end",
    }
    rows = []
    for event in result["events"]:
        rows.append(
            {
                "t": round(event["t"], 2),
                "kind": kind_label.get(event["kind"], event["kind"]),
                "character": chars[event["character"]]["name"] if event["character"] else "",
                "event": event["label"],
                "damage": event["damage"],
                "source": event["source"],
            }
        )
    return pd.DataFrame(rows, columns=["t", "kind", "character", "event", "damage", "source"])


def render_event_table(result: dict, spec: dict, *, key: str = "events_table", height: int = 380) -> dict | None:
    """Native, virtualised table. Row selection is the link back to the timeline."""
    df = event_frame(result, spec)
    if df.empty:
        st.info("No events yet - add a rotation to the trial.")
        return None

    table = st.dataframe(
        df,
        key=key,
        hide_index=True,
        height=height,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "t": st.column_config.NumberColumn("Time", format="%.2f s", width="small"),
            "kind": st.column_config.TextColumn("Kind", width="small"),
            "character": st.column_config.TextColumn("Character", width="small"),
            "event": st.column_config.TextColumn("Event", width="large"),
            "damage": st.column_config.NumberColumn("Damage", format="localized", width="small"),
            "source": st.column_config.TextColumn("Source", width="small"),
        },
        alt="Event log of the trial with timestamps and damage",
    )

    selection = table.selection.rows if table and table.selection else []
    if not selection:
        return None
    position = selection[0]
    if 0 <= position < len(df):
        return result["events"][df.index[position]]
    return None


def _rotation_seconds(spec: dict, rotation: dict | None) -> float:
    """One pass through a rotation: the sum of its blocks' field times."""
    return sum(
        float(spec["field_seqs"][block]["field_time"])
        for block in (rotation or {}).get("blocks", [])
        if block in spec["field_seqs"]
    )


def render_rotation_table(
    spec: dict, totals: dict[str, dict], *, active: str | None = None, sort: str = "DPS"
) -> None:
    """The rotation library, measured in the active trial rather than in isolation."""
    rotations = spec["rotations"]
    if not rotations:
        st.info("No rotations in the library yet.")
        return

    rows = []
    for rotation_id, rotation in rotations.items():
        measured = totals.get(rotation_id)
        rows.append(
            {
                "Rotation": rotation["name"],
                "Focused": rotation_id == active,
                "Occurrences": measured["count"] if measured else 0,
                "Duration (s)": round(measured["duration"] if measured else 0.0, 2),
                "Damage": round(measured["damage"]) if measured else None,
                "DPS": round(measured["dps"]) if measured else None,
            }
        )

    key = {"DPS": "DPS", "Damage": "Damage", "Duration": "Duration (s)"}.get(sort, "DPS")
    rows.sort(key=lambda row: (row[key] is None, -(row[key] or 0.0)))

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Focused": st.column_config.CheckboxColumn(width="small"),
            "Occurrences": st.column_config.NumberColumn(width="small"),
            "Duration (s)": st.column_config.NumberColumn(format="%.2f", width="small"),
            "Damage": st.column_config.NumberColumn(format="localized"),
            "DPS": st.column_config.NumberColumn(format="localized"),
        },
        alt="Damage and DPS of every rotation, measured in the active trial",
    )
    st.caption(
        "Measured in the active trial, so a rotation that runs later inherits the buffs of the one "
        "before it. Rotations the trial does not use show no numbers."
    )


def render_per_occurrence(measured: dict | None, *, name: str) -> None:
    """The ramp, made explicit: the same rotation at each position in the trial."""
    if not measured or len(measured.get("per_occurrence") or []) < 2:
        return
    with st.expander(f"{name} · per occurrence", expanded=False):
        st.dataframe(
            pd.DataFrame(
                [
                    {"#": index + 1, "Starts at (s)": round(item["at"], 2), "Damage": round(item["damage"])}
                    for index, item in enumerate(measured["per_occurrence"])
                ]
            ),
            hide_index=True,
            width="stretch",
            column_config={
                "#": st.column_config.NumberColumn(width="small"),
                "Starts at (s)": st.column_config.NumberColumn(format="%.2f", width="small"),
                "Damage": st.column_config.NumberColumn(format="localized"),
            },
            alt="Damage of each occurrence of this rotation inside the trial",
        )


def render_trial_table(spec: dict, result: dict, *, active: str | None = None) -> None:
    """The trial library. Only the active trial has been simulated."""
    trials = spec["trials"]
    if not trials:
        st.info("No trials yet.")
        return

    rows = []
    for trial_id, trial in trials.items():
        content = sum(
            _rotation_seconds(spec, spec["rotations"].get(slot["rotation"])) * int(slot["repeat"])
            for slot in trial["slots"]
        )
        is_active = trial_id == active
        rows.append(
            {
                "Trial": trial.get("name", trial_id),
                "Focused": is_active,
                "Rotations": len(trial["slots"]),
                "Duration (s)": round(float(trial["duration"]), 1),
                "Content (s)": round(content, 1),
                "Damage": round(result["totals"]["damage"]) if is_active else None,
                "DPS": round(result["totals"]["dps"]) if is_active else None,
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Focused": st.column_config.CheckboxColumn(width="small"),
            "Rotations": st.column_config.NumberColumn(width="small"),
            "Duration (s)": st.column_config.NumberColumn(format="%.1f", width="small"),
            "Content (s)": st.column_config.NumberColumn(format="%.1f", width="small"),
            "Damage": st.column_config.NumberColumn(format="localized"),
            "DPS": st.column_config.NumberColumn(format="localized"),
        },
        alt="Every trial, with the numbers of the active one",
    )


def render_field_sequence_table(
    spec: dict, result: dict, *, active: str | None = None, character: str | None = None
) -> None:
    """The field-sequence library, scoped to one character."""
    field_seqs = spec["field_seqs"]
    if not field_seqs:
        st.info("No field sequences yet.")
        return

    chars = spec["catalog"]["characters"]
    usage: dict[str, int] = {}
    for rotation in spec["rotations"].values():
        for block in rotation["blocks"]:
            usage[block] = usage.get(block, 0) + 1

    damage: dict[str, float] = {}
    for block in result["blocks"]:
        damage[block["field_seq"]] = damage.get(block["field_seq"], 0.0) + result["by_block"].get(block["id"], 0.0)

    rows = [
        {
            "Field sequence": fs["name"],
            "Focused": fs_id == active,
            "Character": chars[fs["character"]]["name"],
            "Field time": round(float(fs["field_time"]), 2),
            "Abilities": len(fs["placements"]),
            "In rotations": usage.get(fs_id, 0),
            "Trial damage": round(damage.get(fs_id, 0.0)),
        }
        for fs_id, fs in field_seqs.items()
        if character is None or fs["character"] == character
    ]
    if not rows:
        st.info("No field sequences for this character yet.")
        return
    rows.sort(key=lambda row: row["Trial damage"], reverse=True)

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Focused": st.column_config.CheckboxColumn(width="small"),
            "Character": st.column_config.TextColumn(width="small"),
            "Field time": st.column_config.NumberColumn(format="%.2f", width="small"),
            "Abilities": st.column_config.NumberColumn(width="small"),
            "In rotations": st.column_config.NumberColumn(width="small"),
            "Trial damage": st.column_config.NumberColumn(format="localized"),
        },
        alt="Every field sequence with its usage and damage in the current trial",
    )

