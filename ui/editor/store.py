"""Editor session state: one spec per session, seeded from the presets.

No general undo stack on purpose - every mutation is a single small change the
user just made, and the strips redraw on the same rerun. The ability-timing table
is the one exception: Apply/Reset snapshot the spec so they can be undone.
"""

from __future__ import annotations

import copy

import streamlit as st

from build_io import assemble_party, collect_slot
from ui.editor import catalog, engine, payloads
from ui.state import invalidate_last_run

SPEC_KEY = "trial_editor_spec"
TRIAL_KEY = "trial_editor_trial"
TIMINGS_KEY = "ability_timings"
UNDO_KEY = "timing_undo"
TIMING_REV_KEY = "timing_rev"
MAX_UNDO = 20


def current_party() -> dict:
    """The party the app would run, rebuilt from the live widgets."""
    rebuilt = assemble_party([collect_slot(st.session_state, slot) for slot in range(1, 5)])
    return rebuilt or st.session_state.get("my_party", {}) or {}


def current_enemy() -> dict:
    return st.session_state.get("enemy_stats",
                                {"enemy_lv": 100, "cryo_res": 0.1, "anemo_res": 0.1})


def spec() -> dict:
    """The session spec, seeded from the presets on first use."""
    document = st.session_state.get(SPEC_KEY)
    if document is None or document.get("catalog_version") != catalog.CATALOG_VERSION:
        timings = st.session_state.get(TIMINGS_KEY) or {}
        st.session_state[SPEC_KEY] = catalog.preset_spec(
            list(current_party().keys()), timings)
        clear_timing_state()
    return st.session_state[SPEC_KEY]


def reset() -> None:
    """Throw the session spec away; the next spec() call re-seeds it."""
    st.session_state.pop(SPEC_KEY, None)
    st.session_state.pop(TIMINGS_KEY, None)
    clear_timing_state()


def timing_snapshot(spec: dict) -> dict:
    """The parts a timing edit can change, copied for Undo."""
    return {"ability_timings": copy.deepcopy(spec.get("ability_timings") or {}),
            "catalog_abilities": copy.deepcopy(spec["catalog"]["abilities"])}


def push_timing_undo(snapshot: dict) -> None:
    stack = st.session_state.setdefault(UNDO_KEY, [])
    stack.append(snapshot)
    del stack[:-MAX_UNDO]


def pop_timing_undo():
    stack = st.session_state.get(UNDO_KEY) or []
    return stack.pop() if stack else None


def restore_timing_undo(spec: dict, snapshot: dict) -> None:
    spec["ability_timings"] = snapshot["ability_timings"]
    spec["catalog"]["abilities"] = snapshot["catalog_abilities"]


def bump_timing_revision() -> None:
    """Give the timing table a new widget identity so it re-seeds from the spec."""
    st.session_state[TIMING_REV_KEY] = st.session_state.get(TIMING_REV_KEY, 0) + 1


def clear_timing_state() -> None:
    """Drop the timing drafts and the undo stack (the spec is the source)."""
    st.session_state.pop(UNDO_KEY, None)
    bump_timing_revision()
    for key in [key for key in st.session_state
                if isinstance(key, str) and key.startswith("ed_hits_")]:
        st.session_state.pop(key, None)


def active_trial(spec_doc: dict | None = None) -> str:
    doc = spec_doc or spec()
    picked = st.session_state.get(TRIAL_KEY)
    return picked if picked in doc["trials"] else doc["active_trial"]


def select(trial_id: str) -> None:
    st.session_state[TRIAL_KEY] = trial_id


@st.cache_data(show_spinner=False, max_entries=24)
def _run(spec_doc: dict, trial_id: str, party: dict, enemy: dict) -> dict:
    return engine.simulate(spec_doc, trial_id, party, enemy)


@st.cache_data(show_spinner=False, max_entries=16)
def _run_rotation(spec_doc: dict, rotation_id: str, party: dict, enemy: dict) -> dict:
    return payloads.rotation_preview(spec_doc, rotation_id, party, enemy)


def result(trial_id: str | None = None) -> dict:
    """Cached simulation of a trial against the live party and enemy."""
    doc = spec()
    return _run(doc, trial_id or active_trial(doc), current_party(), current_enemy())


def rotation_result(rotation_id: str) -> dict:
    """Cached two-loop preview of a rotation."""
    return _run_rotation(spec(), rotation_id, current_party(), current_enemy())


def party_ids() -> list:
    return [catalog.character_id(name) for name in current_party()]



ROTATION_KEY = "trial_editor_rotation"
SEQUENCE_KEY = "trial_editor_sequence"
ERROR_KEY = "trial_editor_error"

SCREEN_KEY = "editor_screen"
SCREENS = ("Trial", "Rotation", "Field sequence")
FOCUS_KEY = "editor_focus"


def show_screen(name: str) -> None:
    st.session_state[SCREEN_KEY] = name


def focus(where) -> None:
    """Queue a jump to the object an issue or a strip click points at.

    Nothing is written directly: the screen switch is a widget, and Streamlit
    refuses to let a value be written after it exists. The host applies the queued
    (kind, id) at the top of the next run, before the switch is created - the same
    deferred-request pattern the reference editor used.
    """
    if where and len(where) > 1 and where[1]:
        st.session_state[FOCUS_KEY] = (where[0], where[1])


def take_focus():
    return st.session_state.pop(FOCUS_KEY, None)


def apply_focus(where) -> None:
    """Land on the object *where* names, if it still exists."""
    kind, item_id = where[0], where[1]
    doc = spec()
    if kind == "fs" and item_id in doc["field_seqs"]:
        select_sequence(item_id)
        show_screen("Field sequence")
    elif kind == "rotation" and item_id in doc["rotations"]:
        select_rotation(item_id)
        show_screen("Rotation")
    elif kind == "trial" and item_id in doc["trials"]:
        select(item_id)
        show_screen("Trial")


def active_rotation(spec_doc: dict | None = None) -> str:
    doc = spec_doc or spec()
    picked = st.session_state.get(ROTATION_KEY)
    if picked in doc["rotations"]:
        return picked
    return next(iter(doc["rotations"]), "")


def active_sequence(spec_doc: dict | None = None) -> str:
    doc = spec_doc or spec()
    picked = st.session_state.get(SEQUENCE_KEY)
    if picked in doc["field_seqs"]:
        return picked
    return next(iter(doc["field_seqs"]), "")


def select_rotation(rotation_id: str) -> None:
    st.session_state[ROTATION_KEY] = rotation_id


def select_sequence(sequence_id: str) -> None:
    st.session_state[SEQUENCE_KEY] = sequence_id


def after_change() -> None:
    """A mutation changed the spec, so the last run no longer describes it."""
    st.session_state.pop(ERROR_KEY, None)
    invalidate_last_run()


def fail(message: str) -> None:
    st.session_state[ERROR_KEY] = message


def take_error() -> str:
    """Pop the pending editor error: it is shown once, above the screen."""
    return st.session_state.pop(ERROR_KEY, "")
