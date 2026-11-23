"""Ability hit-timing editor: one long table for the character on the pills.

The table is a DRAFT. Nothing reaches the spec until "Apply changes", so the strip
and every preview keep showing the committed timings while the user experiments.
Overrides live in the spec, never on the shipped Ability objects in abilities.py,
so a timing experiment can never leak into another preset or session.

Undo is a snapshot stack kept in session state: each Apply/Reset pushes the old
`ability_timings` and catalogue, and Undo restores both.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.editor import catalog, mutations, store

HEIGHT_MAX = 560
ROW_PX = 32
HEADER_PX = 38
TIMING_COLUMN = "Timing (s)"
TOAST_KEY = "timing_toast"


def _frame(rows: list) -> pd.DataFrame:
    """The editor's DataFrame, indexed by the stable row number.

    The index is hidden but survives sorting, so an edit can always be matched back
    to the ability/hit it belongs to.
    """
    frame = pd.DataFrame({
        "Ability": [row["ability"] for row in rows],
        "Hit": [row["hit"] for row in rows],
        TIMING_COLUMN: [row["timing"] for row in rows],
    })
    frame.index = [row["row"] for row in rows]
    return frame


def _changes(rows: list, edited) -> dict | None:
    """{ability id: [timings]} for the rows the user changed, or None if invalid."""
    if not isinstance(edited, pd.DataFrame):
        return None
    by_ability: dict = {}
    for row in rows:
        try:
            cell = edited.loc[row["row"], TIMING_COLUMN]
        except KeyError:
            return None
        if pd.isna(cell):
            return None
        by_ability.setdefault(row["ability_id"], {})[row["hit_index"]] = round(float(cell), 6)

    changes = {}
    for aid, values in by_ability.items():
        current = [float(row["timing"]) for row in rows if row["ability_id"] == aid]
        if all(abs(values[index] - current[index]) <= 1e-9 for index in values):
            continue
        resolved = list(current)
        for index, value in values.items():
            resolved[index] = value
        changes[aid] = resolved
    return changes


def _queue_toast(kind: str, message: str) -> None:
    """Queue one toast for the next fragment render."""
    st.session_state[TOAST_KEY] = (kind, message)


def _apply(spec: dict, changes: dict) -> None:
    snapshot = store.timing_snapshot(spec)
    try:
        mutations.apply_ability_timings(spec, changes)
    except ValueError as exc:
        # The spec was not written (apply_ability_timings validates first), so
        # the new widget key restores the table to its previous state.
        _queue_toast("error", str(exc))
    else:
        store.push_timing_undo(snapshot)
        _queue_toast("success", "Ability timings updated.")
        store.after_change()
    store.bump_timing_revision()
    st.rerun(scope="fragment")


def _reset(spec: dict, character_id: str) -> None:
    snapshot = store.timing_snapshot(spec)
    if mutations.reset_character_timings(spec, character_id):
        store.push_timing_undo(snapshot)
        _queue_toast("success", "Timings reset to the shipped values.")
        store.after_change()
        store.bump_timing_revision()
    st.rerun(scope="fragment")


def _undo(spec: dict) -> None:
    snapshot = store.pop_timing_undo()
    if snapshot is None:
        return
    store.restore_timing_undo(spec, snapshot)
    _queue_toast("success", "Timing change undone.")
    store.after_change()
    store.bump_timing_revision()
    st.rerun(scope="fragment")


def render(spec: dict, sequence_id: str, character_id: str) -> None:
    """Draw the timing table for the character selected by the pills."""
    if spec["field_seqs"].get(sequence_id) is None:
        return
    rows = catalog.timing_rows(spec, character_id)
    if not rows:
        return
    for index, row in enumerate(rows):
        row["row"] = index

    character = spec["catalog"]["characters"].get(character_id, {}).get("name", character_id)
    st.markdown("**Ability hit timings**")
    st.caption("Timing is the delay from the cast. Changes affect every sequence and trial "
               "that casts these abilities. Unapplied edits are lost when you switch characters.")

    key = "ed_hits_%s_%d" % (character_id,
                             st.session_state.get(store.TIMING_REV_KEY, 0))
    edited = st.data_editor(
        _frame(rows),
        key=key,
        hide_index=True,
        num_rows="fixed",
        height=min(HEIGHT_MAX, HEADER_PX + ROW_PX * len(rows)),
        disabled=["Ability", "Hit"],
        column_config={
            "Ability": st.column_config.TextColumn("Ability", width="medium", pinned=True),
            "Hit": st.column_config.TextColumn("Hit", width="medium"),
            TIMING_COLUMN: st.column_config.NumberColumn(
                TIMING_COLUMN, min_value=0.0, max_value=300.0, step=0.001,
                format="%.3f", required=True, width="small",
                help="Time from the cast."),
        },
        alt="Ability hit timings for " + character,
    )

    changes = _changes(rows, edited)
    queued = st.session_state.pop(TOAST_KEY, None)
    if queued:
        kind, message = queued
        icon = {"success": ":material/check_circle:",
                "error": ":material/error:",
                "info": ":material/info:"}.get(kind)
        st.toast(message, icon=icon,
                 duration="long" if kind == "error" else "short")
    if changes is None:
        st.warning("Every hit needs a number.")

    apply_col, reset_col, undo_col = st.columns(3)
    if apply_col.button("Apply changes", key="ed_timing_apply", type="primary",
                        width="stretch", disabled=not changes):
        _apply(spec, changes)
    if reset_col.button("Reset timings", key="ed_timing_reset", width="stretch",
                        disabled=not catalog.character_has_timing_overrides(spec, character_id)):
        _reset(spec, character_id)
    if undo_col.button("Undo", key="ed_timing_undo", width="stretch",
                       disabled=not st.session_state.get(store.UNDO_KEY)):
        _undo(spec)
