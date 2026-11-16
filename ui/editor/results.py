"""The tables under the strip: the slim hit log and the per-slot summary.

The full audit table (ui/table.py) stays in the results tab; this one exists so a
rotation can be read while it is being edited: time, who was on field, who owns
the hit, what it was, the application, the reaction, the damage.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.editor import catalog

COLUMNS = ["Time", "Active", "Owner", "Action", "App", "Reaction", "Damage"]
JUMP_LABELS = {"fs": "field sequence", "rotation": "rotation", "trial": "trial"}
SORTS = ("DPS", "Damage", "Duration")


def _name(spec: dict, cid: str) -> str:
    return spec["catalog"]["characters"].get(cid, {}).get("name", "-")


def slim_frame(spec: dict, result: dict) -> pd.DataFrame:
    """One row per hit, seven columns, nothing else."""
    rows = []
    for event in result.get("events") or []:
        if event.get("event_type") != "HIT":
            continue
        rows.append({
            "Time": round(float(event.get("global_time") or 0.0), 2),
            "Active": _name(spec, catalog.character_id(event.get("active_character") or "")),
            "Owner": _name(spec, catalog.character_id(event.get("character") or "")),
            "Action": event.get("action") or event.get("hit_name") or "",
            "App": event.get("elem_app") or "-",
            "Reaction": event.get("reaction") or "-",
            "Damage": round(float(event.get("average_damage") or 0.0), 1),
        })
    return pd.DataFrame(rows, columns=COLUMNS)


def render_hits(spec: dict, result: dict, *, key: str = "editor_hits",
                height: int = 340) -> None:
    frame = slim_frame(spec, result)
    if frame.empty:
        st.caption("No hits yet.")
        return
    st.dataframe(
        frame,
        key=key,
        hide_index=True,
        height=height,
        width="stretch",
        column_config={
            "Time": st.column_config.NumberColumn("Time", format="%.2f s", width="small"),
            "Active": st.column_config.TextColumn("Active", width="small"),
            "Owner": st.column_config.TextColumn("Owner", width="small"),
            "Action": st.column_config.TextColumn("Action", width="large"),
            "App": st.column_config.TextColumn("App", width="small"),
            "Reaction": st.column_config.TextColumn("Reaction", width="medium"),
            "Damage": st.column_config.NumberColumn("Damage", format="localized", width="small"),
        },
        alt="Hit log of the trial being edited",
    )


def slot_damage(result: dict) -> dict:
    """Damage per rotation slot: one occurrence of one rotation in the trial."""
    totals: dict = {}
    for block in result.get("blocks") or []:
        key = block["occurrence"]
        totals[key] = totals.get(key, 0.0) + result["by_block"].get(block["id"], 0.0)
    return totals


def render_issues(issues: list, *, limit: int = 8, key: str = "issues",
                  on_jump=None, label=None) -> None:
    """Errors, then warnings, then notes - one box each, never eight boxes.

    When *on_jump* is given, every object a warning points at gets one button under
    the boxes, so a warning can be clicked through instead of hunted for.
    """
    for severity, show in (("error", st.error), ("warning", st.warning), ("info", st.info)):
        lines = [issue["message"] for issue in issues if issue["severity"] == severity]
        if not lines:
            continue
        body = "".join("- " + line + chr(10) for line in lines[:limit])
        if len(lines) > limit:
            body += "- and %d more" % (len(lines) - limit)
        show(body)
    if on_jump is None:
        return
    targets = []
    for issue in issues:
        where = tuple(issue.get("where") or ())
        if len(where) == 2 and where[1] and where not in targets:
            targets.append(where)
    if not targets:
        return
    columns = st.columns(min(len(targets), 4))
    for index, where in enumerate(targets[:4]):
        text = label(where) if label else "Open the %s" % JUMP_LABELS.get(where[0], "object")
        if columns[index].button(text, key="%s_jump_%s_%s" % (key, where[0], where[1]),
                                 help="Open what this warning is about."):
            on_jump(where)
            st.rerun()


METRICS = (("damage", "Damage", lambda value: format(value, ",.0f")),
           ("dps", "DPS", lambda value: format(value, ",.0f")),
           ("duration", "Duration", lambda value: "%.2f s" % value),
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


def slot_damage_lines(spec: dict, trial: dict, result: dict) -> list:
    """One line per rotation slot: how much damage that slot is worth."""
    damages = slot_damage(result)
    lines = []
    for slot in trial["slots"]:
        rotation = spec["rotations"].get(slot["rotation"]) or {"name": "(missing)"}
        total = 0.0
        for repeat in range(max(1, int(slot["repeat"]))):
            total += damages.get(slot["id"] + "~" + str(repeat), 0.0)
        lines.append("%s x%d - %s" % (rotation["name"], int(slot["repeat"]), format(total, ",.0f")))
    return lines


def rotation_rows(spec: dict, result: dict) -> list:
    """One row per rotation, measured *inside the trial* - never from a loop alone.

    Damage comes from ``by_block``, so a rotation inherits whatever buffs carried
    over into it; duration is the field time the trial actually spent there.
    """
    rows: dict = {}
    for block in result.get("blocks") or []:
        row = rows.setdefault(block["rotation"], {
            "id": block["rotation"],
            "name": (spec["rotations"].get(block["rotation"]) or {}).get(
                "name", block["rotation_name"]),
            "damage": 0.0, "duration": 0.0, "hits": 0, "uses": set(),
        })
        row["damage"] += result["by_block"].get(block["id"], 0.0)
        row["duration"] += max(0.0, float(block["end"]) - float(block["start"]))
        row["uses"].add(block["occurrence"])
    rotation_of = {block["id"]: block["rotation"] for block in result.get("blocks") or []}
    for hit in result.get("hits") or []:
        row = rows.get(rotation_of.get(hit["block"]))
        if row is not None:
            row["hits"] += 1
    out = []
    for row in rows.values():
        row["uses"] = len(row["uses"])
        row["dps"] = row["damage"] / row["duration"] if row["duration"] else 0.0
        out.append(row)
    return out


def occurrence_rows(spec: dict, result: dict, rotation_id: str) -> list:
    """One row per pass through a rotation: the ramp the expander shows."""
    rows: dict = {}
    for block in result.get("blocks") or []:
        if block["rotation"] != rotation_id:
            continue
        row = rows.setdefault(block["occurrence"], {
            "occurrence": block["occurrence"], "start": float(block["start"]),
            "damage": 0.0, "duration": 0.0, "hits": 0,
        })
        row["start"] = min(row["start"], float(block["start"]))
        row["damage"] += result["by_block"].get(block["id"], 0.0)
        row["duration"] += max(0.0, float(block["end"]) - float(block["start"]))
    occurrence_of = {block["id"]: block["occurrence"]
                     for block in result.get("blocks") or []
                     if block["rotation"] == rotation_id}
    for hit in result.get("hits") or []:
        row = rows.get(occurrence_of.get(hit["block"]))
        if row is not None:
            row["hits"] += 1
    out = sorted(rows.values(), key=lambda row: row["start"])
    for row in out:
        row["dps"] = row["damage"] / row["duration"] if row["duration"] else 0.0
    return out


def render_rotation_table(spec: dict, result: dict, *,
                          key: str = "editor_rotation_table") -> None:
    """Sortable per-rotation numbers for the whole trial, with the ramp per pass.

    Kept off the rotation screen on purpose: a rotation's damage only exists inside
    a trial, so this belongs next to the trial's own numbers.
    """
    rows = rotation_rows(spec, result)
    if not rows:
        st.caption("This trial has no rotations yet.")
        return
    sort = st.radio("Sort by", list(SORTS), horizontal=True, key=key + "_sort",
                    label_visibility="collapsed")
    order = {"DPS": "dps", "Damage": "damage", "Duration": "duration"}[sort]
    rows.sort(key=lambda row: row[order], reverse=True)
    frame = pd.DataFrame([{
        "Rotation": row["name"],
        "Damage": round(row["damage"], 1),
        "DPS": round(row["dps"], 1),
        "Duration": round(row["duration"], 2),
        "Hits": row["hits"],
        "Passes": row["uses"],
    } for row in rows])
    st.dataframe(
        frame, key=key, hide_index=True, width="stretch",
        column_config={
            "Rotation": st.column_config.TextColumn("Rotation", width="large"),
            "Damage": st.column_config.NumberColumn("Damage", format="localized", width="small"),
            "DPS": st.column_config.NumberColumn("DPS", format="localized", width="small"),
            "Duration": st.column_config.NumberColumn("Duration", format="%.2f s", width="small"),
            "Hits": st.column_config.NumberColumn("Hits", width="small"),
            "Passes": st.column_config.NumberColumn("Passes", width="small"),
        },
        alt="Damage per rotation, measured inside the trial",
    )
    _render_passes(spec, result, rows, key)


def _render_passes(spec: dict, result: dict, rows: list, key: str) -> None:
    """One collapsed expander per rotation: damage, DPS and hits pass by pass."""
    for row in rows:
        with st.expander("%s \u00b7 per occurrence" % row["name"]):
            passes = occurrence_rows(spec, result, row["id"])
            if not passes:
                st.caption("This rotation does not run in the trial.")
                continue
            st.dataframe(
                pd.DataFrame([{
                    "Pass": index + 1,
                    "Starts": round(pass_row["start"], 2),
                    "Damage": round(pass_row["damage"], 1),
                    "DPS": round(pass_row["dps"], 1),
                    "Duration": round(pass_row["duration"], 2),
                    "Hits": pass_row["hits"],
                } for index, pass_row in enumerate(passes)]),
                key="%s_pass_%s" % (key, row["id"]), hide_index=True, width="stretch",
                column_config={
                    "Pass": st.column_config.NumberColumn("#", width="small"),
                    "Starts": st.column_config.NumberColumn("Starts", format="%.2f s",
                                                            width="small"),
                    "Damage": st.column_config.NumberColumn("Damage", format="localized",
                                                            width="small"),
                    "DPS": st.column_config.NumberColumn("DPS", format="localized",
                                                         width="small"),
                    "Duration": st.column_config.NumberColumn("Duration", format="%.2f s",
                                                              width="small"),
                    "Hits": st.column_config.NumberColumn("Hits", width="small"),
                },
                alt="One pass through %s" % row["name"],
            )


