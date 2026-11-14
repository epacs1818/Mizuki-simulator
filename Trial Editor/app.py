"""Rotation / damage calculator - Streamlit shell.

    streamlit run app.py

Layout: sidebar (undo, import/export) -> header metrics -> one of two focus
screens (Trial / Field sequence) -> results. Authored state lives in
`st.session_state.store` (ui/state.py); everything on screen is computed from it.
"""

from __future__ import annotations

import streamlit as st

import ui.state as state
import ui.timeline as timeline
from core.validate import validate, validate_rotation
from ui import blocks, results

st.set_page_config(
    page_title="Rotation calculator",
    page_icon=":material/timeline:",
    layout="wide",
)

state.init()
# Seed the view switch before any queued intent is applied: a widget that has
# both a `default=` and a Session State value logs a warning, so we seed here and
# mount the switch with `key=` only.
st.session_state.setdefault("mode_sw", "Trial")
# Apply a queued "open this screen" intent before the view switch is built.
state.consume_pending()

# A share link (#?t=<token>) is applied on arrival, then removed from the URL so
# later edits don't sit under a link that claims to be someone else's build.
_shared = st.query_params.get("t")
if _shared and st.session_state.get("share_applied") != _shared:
    _share_error = state.load_share_token(_shared)
    st.session_state.share_applied = _shared
    st.session_state.share_banner = (
        ("error", _share_error) if _share_error else ("ok", "Loaded the shared trial.")
    )
    try:
        del st.query_params["t"]
    except KeyError:
        pass

# One fixed density for the rotation and trial strips: detailed enough that hits
# stay separate, at the cost of horizontal scrolling on a long trial. The field
# sequence strip always fits its content instead.
DETAIL_PX_PER_SEC = 40.0
FIT = 0.0


# --------------------------------------------------------------------------
# timeline intents -> store mutations
#
# Component callbacks run before the script body, so this is the one place
# where touching session state is unambiguously safe. Triggers reset after
# every rerun, so we only act on a fresh value.
# --------------------------------------------------------------------------


def _trigger(name: str):
    component_state = st.session_state.get(state.TIMELINE_KEY)
    if component_state is None:
        return None
    return getattr(component_state, name, None)


def _on_select() -> None:
    payload = _trigger("select")
    if not payload:
        return
    view = state.view()
    view["cursor"] = payload.get("t")
    if payload.get("kind") == "hit":
        view["selected"] = ("hit", payload.get("t"))
    else:
        view["selected"] = (payload.get("kind"), payload.get("id"))


def _on_seek() -> None:
    payload = _trigger("seek")
    if payload:
        state.view()["cursor"] = payload.get("t")


def _on_moved() -> None:
    payload = _trigger("moved")
    if payload and payload.get("kind") == "placement":
        state.move_placement(payload["id"], float(payload["value"]))


def _on_retimed() -> None:
    payload = _trigger("retimed")
    if payload:
        state.set_field_time(state.view()["fs"], float(payload["value"]))


# --------------------------------------------------------------------------
# derived data
# --------------------------------------------------------------------------

# Switching trial is a widget change; apply it before the spec is read so the
# numbers on screen belong to the trial you just picked.
_requested_trial = st.session_state.get("trial_pick")
if _requested_trial and _requested_trial != state.store()["active_trial"]:
    if _requested_trial in state.store()["trials"]:
        state.set_active_trial(_requested_trial)
        st.session_state.pop("trial_duration", None)

spec = state.store()
result = state.simulate_cached(spec)
issues = validate(spec, result)
view = state.view()
previous_total = st.session_state.prev_damage

# A row selected in the event table drives the playhead. The table lives below
# the timeline, so we read its *previous* run's state at the top of the script.
_selected_rows = None
_table_state = st.session_state.get("events_table")
if _table_state is not None:
    try:
        _selected_rows = _table_state.selection.rows
    except AttributeError:
        _selected_rows = None
if _selected_rows:
    position = _selected_rows[0]
    if isinstance(position, int) and 0 <= position < len(result["events"]):
        view["cursor"] = result["events"][position]["t"]

# --------------------------------------------------------------------------
# header
# --------------------------------------------------------------------------

st.title(":material/timeline: Rotation calculator", anchor=False)
st.caption(
    "Trial → rotations → field sequences → abilities. "
    "Drag ability blocks on the timeline, or type exact values; totals update on every change."
)

_banner = st.session_state.pop("share_banner", None)
if _banner:
    _kind, _text = _banner
    if _kind == "error":
        st.error(_text, icon=":material/link_off:")
    else:
        st.success(_text, icon=":material/link:")

results.render_metrics(result, previous_total)

# --------------------------------------------------------------------------
# sidebar
# --------------------------------------------------------------------------

def _share_url() -> str:
    """Absolute link to this build. The token is zlib+base64 of the authored spec."""
    try:
        base = (st.context.url or "").split("?")[0]
    except Exception:  # no request context (bare mode / tests)
        base = ""
    token = state.share_token()
    return f"{base}?t={token}" if base else token


with st.sidebar:
    st.markdown("**Recent runs**")
    st.button(
        "Record current numbers",
        icon=":material/bookmark_add:",
        width="stretch",
        on_click=state.record_run,
        args=(result,),
        help="Bookmark the totals on screen. The delta is against the previous bookmark.",
    )
    _runs = state.runs()
    if _runs:
        for _entry in reversed(_runs):
            _delta = _entry["delta"]
            _suffix = f" · {_delta:+.1f}%" if _delta is not None else ""
            st.caption(f"`{_entry['at']}` · {_entry['total']:,.0f}{_suffix}")
        st.button("Clear", icon=":material/delete_sweep:", width="stretch", on_click=state.clear_runs)
    else:
        st.caption("Nothing recorded yet.")

    st.divider()
    st.markdown("**Share**")
    st.download_button(
        "Export trial",
        data=state.export_json(),
        file_name="trial.json",
        mime="application/json",
        icon=":material/download:",
        width="stretch",
    )
    st.caption("Link to this build:")
    st.code(_share_url(), language=None, wrap_lines=True)
    upload = st.file_uploader("Import trial", type=["json"], label_visibility="collapsed")
    if upload is not None and st.session_state.get("imported_file") != upload.name:
        error = state.import_json(upload.getvalue().decode("utf-8"))
        st.session_state.imported_file = upload.name
        if error:
            st.error(error, icon=":material/error:")
        else:
            st.rerun()

    st.divider()
    st.button("Reset demo data", icon=":material/restart_alt:", width="stretch", on_click=state.reset)


# --------------------------------------------------------------------------
# screens
# --------------------------------------------------------------------------


def _apply_duration() -> None:
    state.set_duration(float(st.session_state["trial_duration"]))


def _apply_trial_name(trial_id: str, key: str) -> None:
    state.rename_trial(trial_id, st.session_state[key])


def _new_trial() -> None:
    tid = state.add_trial()
    st.session_state["trial_pick"] = tid


def _delete_trial() -> None:
    state.delete_trial(state.store()["active_trial"])
    st.session_state.pop("trial_pick", None)


def _render_trial() -> None:
    left, right = st.columns([0.44, 0.56], gap="large")

    with left:
        st.markdown("### Trial")
        trials = spec["trials"]
        ids = list(trials)
        if st.session_state.get("trial_pick") not in trials:
            st.session_state["trial_pick"] = spec["active_trial"]
        picked_trial = st.selectbox(
            "Trial",
            ids,
            key="trial_pick",
            format_func=lambda tid: trials[tid].get("name", tid),
        )

        name_key = f"tname_{picked_trial}"
        st.session_state.setdefault(name_key, trials[picked_trial].get("name", picked_trial))
        st.text_input(
            "Rename trial",
            key=name_key,
            on_change=_apply_trial_name,
            args=(picked_trial, name_key),
            help="Press Enter to apply.",
        )

        with st.container(horizontal=True, vertical_alignment="bottom"):
            st.button("New trial", icon=":material/add:", on_click=_new_trial)
            st.button(
                "Delete trial",
                icon=":material/delete:",
                on_click=_delete_trial,
                disabled=len(trials) <= 1,
                help="A trial is always needed, so the last one cannot be deleted.",
            )

        st.session_state.setdefault("trial_duration", float(trials[picked_trial]["duration"]))
        st.number_input(
            "Trial duration (s)",
            min_value=1.0,
            max_value=3600.0,
            step=1.0,
            key="trial_duration",
            on_change=_apply_duration,
            help="Anything past this point is truncated, and flagged under Warnings.",
        )
        blocks.render_trial_blocks(spec, result)

    with right:
        st.caption("Bands are field time, ticks are hits, bars are active buffs. Drag the ruler to scrub.")
        payload = timeline.trial_payload(
            spec,
            result,
            cursor=view["cursor"],
            selected=view["selected"],
            px_per_sec=DETAIL_PX_PER_SEC,
        )
        timeline.render(
            payload,
            key=state.TIMELINE_KEY,
            on_select=_on_select,
            on_seek=_on_seek,
            on_moved=_on_moved,
            on_retimed=_on_retimed,
        )

        st.markdown("#### Warnings")
        results.render_issues([i for i in issues if not (i["where"] and i["where"][0] == "fs")])
        fs_notes = [i for i in issues if i["where"] and i["where"][0] == "fs"]
        if fs_notes:
            st.caption(
                f"+ {len(fs_notes)} warning(s) that belong to a single field sequence "
                "(open one to see them)."
            )

        st.markdown("#### All trials")
        results.render_trial_table(spec, result, active=spec["active_trial"])

    st.divider()
    st.markdown("#### Event log")
    results.render_event_table(result, spec)


def _render_rotation() -> None:
    rotations = spec["rotations"]
    if not rotations:
        st.info("No rotations in the library yet.")
        return
    if view["rot"] not in rotations:
        view["rot"] = next(iter(rotations))
    # The widget key is authoritative: if it is missing or stale, seed it from the
    # focused rotation. Creating a rotation sets both, so the new one is selected
    # on the same run instead of falling back to whatever the dropdown had.
    if st.session_state.get("rot_pick") not in rotations:
        st.session_state["rot_pick"] = view["rot"]

    ids = list(rotations)
    left, right = st.columns([0.44, 0.56], gap="large")

    with left:
        picked = st.selectbox(
            "Rotation",
            ids,
            key="rot_pick",
            format_func=lambda rid: rotations[rid]["name"],
        )
        view["rot"] = picked

    preview = state.rotation_preview_cached(spec, picked)
    rotation_time = state.rotation_duration(spec, picked)
    measured = state.rotation_totals(result).get(picked)

    with left:
        blocks.render_rotation_editor(spec, picked)

    with right:
        cols = st.columns(3)
        cols[0].metric("Rotation duration", f"{rotation_time:.2f}s")
        cols[1].metric(
            "Damage in trial",
            f"{measured['damage']:,.0f}" if measured else "not used",
            help="Measured inside the active trial, so it includes buffs inherited from earlier rotations.",
        )
        cols[2].metric(
            "DPS in trial",
            f"{measured['dps']:,.0f}" if measured else "—",
            help="Damage in the trial divided by the time this rotation occupied it.",
        )

        st.caption(
            "One rotation, plus whatever resolves after it ends. Bands are field time, ticks are hits, "
            "bars are active buffs."
        )
        payload = timeline.rotation_payload(
            spec,
            picked,
            preview,
            cursor=view["cursor"],
            selected=view["selected"],
            px_per_sec=DETAIL_PX_PER_SEC,
            tail=state.rotation_tail(spec, picked),
        )
        timeline.render(
            payload,
            key=state.TIMELINE_KEY,
            on_select=_on_select,
            on_seek=_on_seek,
            on_moved=_on_moved,
            on_retimed=_on_retimed,
        )

        st.markdown("#### Warnings")
        results.render_issues(validate_rotation(spec, picked), limit=5)

        st.markdown("#### All rotations")
        sort_key = st.segmented_control(
            "Sort by", ["DPS", "Damage", "Duration"], default="DPS", key="rot_sort"
        ) or "DPS"
        rotation_totals = state.rotation_totals(result)
        results.render_rotation_table(spec, rotation_totals, active=picked, sort=sort_key)
        if measured and measured["name"]:
            results.render_per_occurrence(measured, name=measured["name"])


def _render_field_sequence() -> None:
    field_seqs = spec["field_seqs"]
    chars = spec["catalog"]["characters"]
    char_ids = list(chars)

    if view["fs"] not in field_seqs:
        view["fs"] = next(iter(field_seqs), None)

    # The character selector drives everything on this screen, so seed it from
    # whichever field sequence was focused when you arrived.
    if st.session_state.get("fs_char") not in chars:
        focused = field_seqs.get(view["fs"])
        st.session_state["fs_char"] = focused["character"] if focused else char_ids[0]

    left, right = st.columns([0.44, 0.56], gap="large")

    with left:
        character = st.selectbox(
            "Character",
            char_ids,
            key="fs_char",
            format_func=lambda cid: chars[cid]["name"],
        )
        ids = [fid for fid, fs in field_seqs.items() if fs["character"] == character]

        if not ids:
            st.caption(f"{chars[character]['name']} has no field sequences yet.")
            st.button("New field sequence", icon=":material/add:", on_click=_new_field_sequence)
        else:
            if st.session_state.get("fs_pick") not in ids:
                # Respect an incoming focus (e.g. "Edit this field sequence") when
                # it belongs to the selected character.
                st.session_state["fs_pick"] = view["fs"] if view["fs"] in ids else ids[0]
            picked = st.selectbox(
                "Field sequence",
                ids,
                key="fs_pick",
                format_func=lambda fid: field_seqs[fid]["name"],
            )
            view["fs"] = picked
            blocks.render_field_sequence_editor(spec, result, picked)

    if not ids:
        with right:
            st.caption("Pick a character that has field sequences, or create one on the left.")
        return

    with right:
        st.caption(
            "Field time fills the strip; anything resolving later sits past the right edge. "
            "Drag a block to move that ability's first hit, or the red handle to change the field time "
            "(Alt while dropping = no snapping)."
        )
        payload = timeline.field_sequence_payload(
            spec,
            picked,
            cursor=view["cursor"],
            selected=view["selected"],
            px_per_sec=FIT,
        )
        timeline.render(
            payload,
            key=state.TIMELINE_KEY,
            on_select=_on_select,
            on_seek=_on_seek,
            on_moved=_on_moved,
            on_retimed=_on_retimed,
        )

        st.markdown("#### Warnings")
        results.render_issues(
            [i for i in issues if i["where"] and i["where"][0] == "fs" and i["where"][1] == picked],
            limit=4,
        )

        st.markdown("#### Field sequence library")
        results.render_field_sequence_table(spec, result, active=picked, character=character)


# --------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------

with st.container(horizontal=True, vertical_alignment="center"):
    mode = st.segmented_control(
        "View",
        ["Trial", "Rotation", "Field sequence"],
        key="mode_sw",
    )
    st.button(
        "Undo",
        icon=":material/undo:",
        disabled=not state.can_undo(),
        on_click=state.undo,
        help="Step back through your edits.",
    )
st.divider()

if mode == "Rotation":
    view["mode"] = "rot"
    _render_rotation()
elif mode == "Field sequence":
    view["mode"] = "fs"
    _render_field_sequence()
else:
    view["mode"] = "trial"
    _render_trial()

st.session_state.prev_damage = result["totals"]["damage"]

