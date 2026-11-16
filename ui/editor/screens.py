"""The three screens: Trial, Rotation, Field sequence.

Each screen is library + form + ordered list on the left, strip + numbers +
warnings on the right, hit log underneath. Widgets write through mutations.py, so
a preset stays read-only and every rule lives in one place.
"""

from __future__ import annotations

import streamlit as st

from ui.editor import (catalog, mutations, payloads, publish, results, store,
                        strips, validate)
from ui.state import toast

PIXELS_PER_SEC = 14.0
TRIAL_STRIP = "editor_trial_strip"
ROTATION_STRIP = "editor_rotation_strip"
SEQUENCE_STRIP = "editor_sequence_strip"
SELECTION_KEY = "editor_selected"


def _try(fn) -> None:
    """Apply a mutation from inside the run; a refusal becomes a visible message."""
    try:
        fn()
    except ValueError as exc:
        store.fail(str(exc))
    else:
        store.after_change()


def _apply(fn, success: str = "") -> None:
    """Apply a mutation, then redraw from scratch (used by plain buttons)."""
    try:
        fn()
    except ValueError as exc:
        store.fail(str(exc))
    else:
        store.after_change()
        if success:
            toast(success)
    st.rerun()


def _party_visible(ids, owners) -> list:
    """Ids the current party has a stake in (the trial list uses this).

    An entry nobody owns is always visible; with no party at all nothing is hidden,
    because the party is the thing being configured elsewhere.
    """
    party = set(store.party_ids())
    if not party:
        return list(ids)
    out = []
    for item_id in ids:
        owned = owners(item_id)
        if not owned or owned & party:
            out.append(item_id)
    return out


def _unique_labels(ids, labels) -> list:
    """Display strings that map back to exactly one id."""
    counts = {}
    for item_id in ids:
        label = labels.get(item_id, item_id)
        counts[label] = counts.get(label, 0) + 1
    seen = {}
    out = []
    for item_id in ids:
        label = labels.get(item_id, item_id)
        if counts[label] > 1:
            seen[label] = seen.get(label, 0) + 1
            label = "%s #%d" % (label, seen[label])
        out.append(label)
    return out


def _library(title: str, ids, labels: dict, current: str, *, key: str,
             on_pick=None, empty: str = "Nothing here yet.") -> str:
    """Pick one id from the list, with the caller's state deciding what is shown.

    The widget is keyed and the pick is written through ``on_change``: Streamlit
    runs callbacks before the body, so by the time the widget is drawn the caller's
    target already equals the pick and its index agrees with it. Without that, the
    element is rendered with the *previous* index and visibly snaps back until the
    run after - which is why a pick used to need doing twice.

    The key is dropped only when the app itself moved the target (a new entry, a
    delete, a party change), so the widget re-reads the index then. A pick by hand
    never trips that, because its callback has already set the target.
    """
    if not ids:
        st.info(empty)
        return ""
    options = _unique_labels(ids, labels)
    mapping = dict(zip(options, ids))
    index = ids.index(current) if current in ids else 0

    def remember() -> None:
        picked = st.session_state.get(key)
        if on_pick is not None and picked in mapping:
            on_pick(mapping[picked])

    stored = st.session_state.get(key)
    if stored is not None and stored != options[index]:
        st.session_state.pop(key, None)
    picked = st.selectbox(title, options, index=index, key=key, on_change=remember,
                          label_visibility="collapsed")
    return mapping.get(picked, current)



def _trial_labels(spec: dict, ids) -> dict:
    """Display name plus the team it was authored for: three presets share a name."""
    characters = spec["catalog"]["characters"]
    labels = {}
    for trial_id in ids:
        trial = spec["trials"][trial_id]
        team = [characters[cid]["name"] for cid in trial.get("required_party") or []
                if cid in characters]
        labels[trial_id] = trial["name"] + (" - " + ", ".join(team) if team else "")
    return labels


TRIAL_FORM_KEYS = ("ed_trial_name", "ed_trial_desc", "ed_trial_mode",
                    "ed_trial_time", "ed_trial_party")


def _sync_owner(owner, keys) -> None:
    """Point the form widgets at *owner* so a stale value cannot leak across items."""
    if st.session_state.get("ed_owner") != owner:
        st.session_state["ed_owner"] = owner
        for key in keys:
            st.session_state.pop(key, None)


def _trial_actions(spec: dict, trial_id: str) -> None:
    trial = spec["trials"].get(trial_id) or {}
    columns = st.columns(4)
    if columns[0].button("New trial", key="ed_new_trial", use_container_width=True):
        def make() -> None:
            store.select(mutations.new_trial(spec, "New trial",
                                             next(iter(spec["rotations"]), None)))
        _apply(make, "Trial created.")
    if columns[1].button("Duplicate", key="ed_dup_trial", use_container_width=True,
                         disabled=not trial):
        def twin() -> None:
            store.select(mutations.duplicate(spec, "trials", trial_id))
        _apply(twin, "Trial duplicated.")
    if columns[2].button("Delete", key="ed_del_trial", use_container_width=True,
                         disabled=bool(trial.get("preset", True))):
        _apply(lambda: mutations.delete(spec, "trials", trial_id), "Trial deleted.")
    if columns[3].button("Create trial", key="ed_create_trial",
                         use_container_width=True, type="primary", disabled=not trial,
                         help="Publish this trial to the runner."):
        _apply(lambda: publish.publish(spec, trial_id),
               "Trial created and selected in the runner.")


def _trial_form(spec: dict, trial_id: str) -> None:
    trial = spec["trials"].get(trial_id)
    if trial is None:
        return
    locked = bool(trial.get("preset"))
    if locked:
        st.caption("Preset - read-only. Duplicate it to edit.")
    _sync_owner(("trials", trial_id), TRIAL_FORM_KEYS)
    st.text_input("Name", value=trial["name"], key="ed_trial_name", disabled=locked)
    st.text_input("Description", value=trial.get("description", ""),
                  key="ed_trial_desc", disabled=locked)
    mode = st.radio("End", ["time", "last_swap"],
                    index=0 if trial.get("end_mode") == "time" else 1,
                    format_func=lambda m: "Fixed duration" if m == "time" else "At the last swap",
                    horizontal=True, key="ed_trial_mode", disabled=locked)
    st.number_input("Duration (s)", min_value=1.0, max_value=3600.0, step=1.0,
                    value=float(trial.get("end_time") or 30.0), key="ed_trial_time",
                    disabled=locked or mode != "time")
    characters = spec["catalog"]["characters"]
    st.multiselect("Required party", list(characters),
                   default=[cid for cid in trial.get("required_party") or [] if cid in characters],
                   format_func=lambda cid: characters[cid]["name"],
                   key="ed_trial_party", disabled=locked,
                   help="Empty means any team. Otherwise the runner only offers this trial to that team.")
    if not locked and st.button("Apply changes", key="ed_apply_trial",
                               use_container_width=True):
        def apply() -> None:
            mutations.set_trial_text(spec, trial_id,
                                     name=st.session_state["ed_trial_name"],
                                     description=st.session_state["ed_trial_desc"])
            mutations.set_trial_end(spec, trial_id, st.session_state["ed_trial_mode"],
                                    st.session_state["ed_trial_time"])
            mutations.set_trial_party(spec, trial_id, st.session_state["ed_trial_party"])
        _apply(apply, "Trial updated.")


def _slot_list(spec: dict, trial_id: str) -> None:
    trial = spec["trials"].get(trial_id)
    if trial is None:
        return
    locked = bool(trial.get("preset"))
    rotations = spec["rotations"]
    st.markdown("**Rotations in this trial**")
    slots = list(trial["slots"])
    if not slots:
        st.caption("No rotations yet - add one below.")
    for index, slot in enumerate(slots):
        rotation = rotations.get(slot["rotation"]) or {"name": "(missing rotation)"}
        columns = st.columns([0.52, 0.15, 0.09, 0.09, 0.09])
        columns[0].markdown("%d. %s" % (index + 1, rotation["name"]))
        repeat = columns[1].number_input("x", min_value=1, max_value=999,
                                         value=int(slot["repeat"]),
                                         key="ed_slot_repeat_" + slot["id"],
                                         label_visibility="collapsed", disabled=locked)
        if repeat != int(slot["repeat"]):
            _try(lambda: mutations.set_slot_repeat(spec, trial_id, slot["id"], repeat))
        if columns[2].button("\u2191", key="ed_slot_up_" + slot["id"],
                             disabled=locked or index == 0):
            _try(lambda: mutations.move_slot(spec, trial_id, slot["id"], -1))
        if columns[3].button("\u2193", key="ed_slot_down_" + slot["id"],
                             disabled=locked or index == len(slots) - 1):
            _try(lambda: mutations.move_slot(spec, trial_id, slot["id"], 1))
        if columns[4].button("\u2715", key="ed_slot_del_" + slot["id"], disabled=locked):
            _try(lambda: mutations.remove_slot(spec, trial_id, slot["id"]))
    if locked:
        return
    options = list(rotations)
    if not options:
        st.caption("No rotations in the library yet.")
        return
    picker, adder = st.columns([0.7, 0.3])
    picked = picker.selectbox("Add rotation", options,
                              format_func=lambda r: rotations[r]["name"],
                              key="ed_add_slot_pick", label_visibility="collapsed")
    if adder.button("Add", key="ed_add_slot", use_container_width=True):
        _try(lambda: mutations.add_slot(spec, trial_id, picked))


def _jump_label(spec: dict, where) -> str:
    """The button label for a click-through target."""
    kind, item_id = where
    if kind == "fs":
        name = (spec["field_seqs"].get(item_id) or {}).get("name", "field sequence")
    elif kind == "rotation":
        name = (spec["rotations"].get(item_id) or {}).get("name", "rotation")
    else:
        name = (spec["trials"].get(item_id) or {}).get("name", "trial")
    return "\u2197 %s" % name


def _block_of_hit(result: dict, pick: dict):
    """The block a clicked tick belongs to: exact match on ability and time."""
    ability, when = pick.get("id"), float(pick.get("t") or 0.0)
    for hit in result.get("hits") or []:
        if hit["ability"] == ability and abs(float(hit["t"]) - when) < 1e-6:
            return hit["block"]
    return None


def _trial_preview(spec: dict, trial_id: str) -> None:
    trial = spec["trials"].get(trial_id)
    if trial is None:
        return
    if not store.current_party():
        st.info("Pick your team in **Team & Gear Setup** first: the preview runs the "
                "trial against that party.")
        return
    try:
        result = store.result(trial_id)
    except Exception as exc:  # a broken spec must not take the whole page down
        st.error("The preview could not run: %s" % exc)
        return
    st.markdown("#### " + trial["name"])
    if trial.get("description"):
        st.caption(trial["description"])
    payload = payloads.trial_payload(spec, trial_id, result, px_per_sec=PIXELS_PER_SEC)
    strips.render(payload, key=TRIAL_STRIP)
    pick = strips.event("select", key=TRIAL_STRIP)
    if pick:
        block_id = pick.get("id") if pick.get("kind") == "block" else _block_of_hit(result, pick)
        block = next((item for item in result["blocks"] if item["id"] == block_id), None)
        if block is not None and block["rotation"] in spec["rotations"]:
            store.focus(("rotation", block["rotation"]))
            st.rerun()
    results.metrics(result["totals"])
    lines = results.slot_damage_lines(spec, trial, result)
    if len(lines) > 1:
        st.caption("Per rotation: " + "  |  ".join(lines))
    issues = validate.trial_issues(spec, trial_id, store.party_ids()) + result["warnings"]
    results.render_issues(issues, key="ed_trial_issues", on_jump=store.focus,
                          label=lambda where: _jump_label(spec, where))
    if st.toggle("Show details", key="ed_trial_hits",
                 help="The hit log of this trial: time, who was on field, owner, action, "
                      "application, reaction, damage."):
        results.render_hits(spec, result, key="editor_hits_trial")


def trial_screen(spec: dict) -> None:
    trials = spec["trials"]
    shown = _party_visible(list(trials), lambda tid: set(trials[tid]["required_party"]))
    current = store.active_trial(spec)
    if current and current not in shown:
        shown = [current] + shown
    labels = _trial_labels(spec, shown)
    left, right = st.columns([0.95, 1.5], gap="large")
    with left:
        picked = _library("Trial", shown, labels, current, key="ed_trial_list",
                          on_pick=store.select)
        if picked and picked != current:
            store.select(picked)
            current = picked
        _trial_actions(spec, current)
        _trial_form(spec, current)
        _slot_list(spec, current)
    with right:
        _trial_preview(spec, current)


def _rotation_actions(spec: dict, rotation_id: str) -> None:
    """New / Duplicate / Delete; either way the result belongs to this party."""
    rotation = spec["rotations"].get(rotation_id) or {}
    party = store.party_ids()
    columns = st.columns(3)
    if columns[0].button("New rotation", key="ed_new_rotation", use_container_width=True):
        def make() -> None:
            store.select_rotation(mutations.new_rotation(spec, "New rotation", party))
        _apply(make, "Rotation created.")
    if columns[1].button("Duplicate", key="ed_dup_rotation", use_container_width=True,
                         disabled=not rotation):
        def twin() -> None:
            new_id = mutations.duplicate(spec, "rotations", rotation_id)
            mutations.set_rotation_party(spec, new_id, party)
            store.select_rotation(new_id)
        _apply(twin, "Rotation duplicated.")
    if columns[2].button("Delete", key="ed_del_rotation", use_container_width=True,
                         disabled=bool(rotation.get("preset", True))):
        _apply(lambda: mutations.delete(spec, "rotations", rotation_id), "Rotation deleted.")


def _rotation_form(spec: dict, rotation_id: str) -> None:
    """The name, with a key of its own per rotation. Apply sits below the blocks:
    the two halves are one set of settings."""
    rotation = spec["rotations"].get(rotation_id)
    if rotation is None:
        return
    locked = bool(rotation.get("preset"))
    if locked:
        st.caption("Preset - read-only. Duplicate it to edit.")
    st.text_input("Name", value=rotation["name"], key="ed_rot_name_" + rotation_id,
                  disabled=locked)


def _rotation_apply(spec: dict, rotation_id: str) -> None:
    rotation = spec["rotations"].get(rotation_id)
    if rotation is None or rotation.get("preset"):
        return
    if not st.button("Apply changes", key="ed_apply_rotation", use_container_width=True):
        return

    def apply() -> None:
        mutations.set_rotation_text(spec, rotation_id,
                                    name=st.session_state["ed_rot_name_" + rotation_id])
    _apply(apply, "Rotation updated.")


def _block_list(spec: dict, rotation_id: str) -> None:
    rotation = spec["rotations"].get(rotation_id)
    if rotation is None:
        return
    locked = bool(rotation.get("preset"))
    sequences = spec["field_seqs"]
    blocks = list(rotation["blocks"])
    st.markdown("**Field sequences in this rotation**")
    if not blocks:
        st.caption("Empty loop - add a field sequence below.")
    for index, block_id in enumerate(blocks):
        sequence = sequences.get(block_id) or {"name": "(missing sequence)"}
        columns = st.columns([0.61, 0.09, 0.09, 0.09])
        columns[0].markdown("%d. %s" % (index + 1, sequence["name"]))
        if columns[1].button("\u2191", key="ed_block_up_%d_%s" % (index, block_id),
                             disabled=locked or index == 0):
            _try(lambda: mutations.move_block(spec, rotation_id, index, -1))
            # The rows were drawn before this click, so redraw the editor only.
            st.rerun(scope="fragment")
        if columns[2].button("\u2193", key="ed_block_down_%d_%s" % (index, block_id),
                             disabled=locked or index == len(blocks) - 1):
            _try(lambda: mutations.move_block(spec, rotation_id, index, 1))
            st.rerun(scope="fragment")
        if columns[3].button("\u2715", key="ed_block_del_%d_%s" % (index, block_id),
                             disabled=locked):
            _try(lambda: mutations.remove_block(spec, rotation_id, index))
            st.rerun(scope="fragment")
    if locked or not sequences:
        return
    party = set(store.party_ids())

    def label(sequence_id: str) -> str:
        sequence = sequences[sequence_id]
        character = spec["catalog"]["characters"].get(sequence["character"], {})
        return "%s (%s)" % (sequence["name"], character.get("name", "?"))

    # A rotation belongs to a party, so only that party's sequences can go in it.
    options = [sequence_id for sequence_id in sequences
               if not party or sequences[sequence_id]["character"] in party]
    if not options:
        st.caption("This party has no field sequences yet.")
        return
    picker, adder = st.columns([0.7, 0.3])
    picked = picker.selectbox("Add field sequence", options, format_func=label,
                              key="ed_add_block_pick_" + rotation_id,
                              label_visibility="collapsed")
    if adder.button("Add", key="ed_add_block", use_container_width=True):
        _try(lambda: mutations.add_block(spec, rotation_id, picked))
        st.rerun(scope="fragment")


def _rotation_preview(spec: dict, rotation_id: str) -> None:
    if not store.current_party():
        st.info("Pick your team in **Team & Gear Setup** first: the preview runs the "
                "loop against that party.")
        return
    if not rotation_id:
        st.caption("Create a rotation for this party to see its loop here.")
        return
    try:
        preview = store.rotation_result(rotation_id)
    except Exception as exc:
        st.error("The preview could not run: %s" % exc)
        return
    # Fitted to the column like the field-sequence strip: a fixed 14px/s drew a
    # three second loop 42px wide.
    payload = payloads.rotation_payload(spec, rotation_id, preview, px_per_sec=0)
    strips.render(payload, key=ROTATION_STRIP)
    pick = strips.event("select", key=ROTATION_STRIP)
    if pick and pick.get("kind") == "block" and pick.get("id"):
        block = next((item for item in preview["blocks"] if item["id"] == pick["id"]), None)
        if block is not None and block["field_seq"] in spec["field_seqs"]:
            store.focus(("fs", block["field_seq"]))
            st.rerun(scope="fragment")
    # A rotation's damage depends on where it sits in a trial, so only the loop's
    # own two numbers are shown here; damage belongs to the trial view.
    results.metrics(results.loop_totals(spec, rotation_id, preview),
                    fields=("duration", "hits"))
    # A preview the engine refused (a cooldown clash on the second loop) would
    # otherwise draw an empty strip with no explanation, so its issues are shown.
    results.render_issues(validate.rotation_issues(spec, rotation_id)
                          + preview.get("warnings", []), key="ed_rotation_issues")


def _rotation_party(spec: dict, rotation: dict) -> set:
    """The team a rotation belongs to: its own tag, or whoever its blocks belong to."""
    tagged = set(rotation.get("required_party") or [])
    if tagged:
        return tagged
    out = set()
    for block in rotation.get("blocks") or []:
        sequence = spec["field_seqs"].get(block)
        if sequence:
            out.add(sequence["character"])
    return out


def rotation_screen(spec: dict) -> None:
    rotations = spec["rotations"]
    party = set(store.party_ids())
    # A rotation is authored for a team, so only the loops this team can play are
    # offered: tagged with its own required_party, or owned by its blocks.
    shown = [rotation_id for rotation_id in rotations
             if not party or _rotation_party(spec, rotations[rotation_id]) <= party]
    current = store.active_rotation(spec)
    if current not in shown:
        current = shown[0] if shown else ""
        if current:
            store.select_rotation(current)
    labels = {rid: rotations[rid]["name"] for rid in shown}
    left, right = st.columns([0.9, 1.7], gap="large")
    with left:
        picked = _library("Rotation", shown, labels, current, key="ed_rotation_list",
                          on_pick=store.select_rotation,
                          empty="No rotation is authored for this party yet - "
                                "create one below.")
        if picked and picked != current:
            store.select_rotation(picked)
            current = picked
        _rotation_actions(spec, current)
        _rotation_form(spec, current)
        _block_list(spec, current)
        _rotation_apply(spec, current)
    with right:
        _rotation_preview(spec, current)


def _sequence_actions(spec: dict, sequence_id: str, owner: str) -> None:
    """New / Duplicate / Delete; a new sequence belongs to the character on the pills."""
    sequence = spec["field_seqs"].get(sequence_id) or {}
    columns = st.columns(3)
    if columns[0].button("New sequence", key="ed_new_sequence", use_container_width=True):
        def make() -> None:
            store.select_sequence(mutations.new_sequence(spec, "New sequence", owner))
        _apply(make, "Field sequence created.")
    if columns[1].button("Duplicate", key="ed_dup_sequence", use_container_width=True,
                         disabled=not sequence):
        def twin() -> None:
            store.select_sequence(mutations.duplicate(spec, "field_seqs", sequence_id))
        _apply(twin, "Field sequence duplicated.")
    if columns[2].button("Delete", key="ed_del_sequence", use_container_width=True,
                         disabled=bool(sequence.get("preset", True))):
        _apply(lambda: mutations.delete(spec, "field_seqs", sequence_id),
               "Field sequence deleted.")


def _sequence_form(spec: dict, sequence_id: str) -> None:
    """Name and field time, with widget keys of their own per sequence.

    A keyed widget keeps its own value and ignores ``value=``, so two sequences
    sharing a key is exactly how one sequence's name ends up shown for another.
    Per-sequence keys make that impossible and need no resynchronising.
    """
    sequence = spec["field_seqs"].get(sequence_id)
    if sequence is None:
        return
    locked = bool(sequence.get("preset"))
    if locked:
        st.caption("Preset - read-only. Duplicate it to edit.")
    st.text_input("Name", value=sequence["name"], key="ed_seq_name_" + sequence_id,
                  disabled=locked)
    st.number_input("Field time (s)", min_value=0.1, max_value=300.0, step=0.1,
                    value=float(sequence["field_time"]), format="%0.3f", key="ed_seq_time_" + sequence_id,
                    disabled=locked,
                    help="Swap-in to swap-out.")


def _sequence_apply(spec: dict, sequence_id: str) -> None:
    sequence = spec["field_seqs"].get(sequence_id)
    if sequence is None or sequence.get("preset"):
        return
    if not st.button("Apply changes", key="ed_apply_sequence",
                     use_container_width=True):
        return

    def apply() -> None:
        mutations.set_sequence_text(spec, sequence_id,
                                    name=st.session_state["ed_seq_name_" + sequence_id])
        mutations.set_field_time(spec, sequence_id,
                                 st.session_state["ed_seq_time_" + sequence_id])
    _apply(apply, "Field sequence updated.")


def _placement_list(spec: dict, sequence_id: str) -> None:
    sequence = spec["field_seqs"].get(sequence_id)
    if sequence is None:
        return
    locked = bool(sequence.get("preset"))
    abilities = spec["catalog"]["abilities"]
    st.markdown("**Abilities list. Adjust when their first hit lands.**")
    placements = list(sequence["placements"])
    if not placements:
        st.caption("Nothing placed yet - add an ability below.")
    for placement in placements:
        ability = abilities.get(placement["ability"]) or {"name": "(missing ability)", "hits": []}
        columns = st.columns([0.5, 0.24, 0.12])
        columns[0].markdown("%s <span style='opacity:.6'>%d hit(s)</span>"
                            % (ability["name"], len(ability.get("hits") or ())),
                            unsafe_allow_html=True)
        when = columns[1].number_input("First hit time (s)", min_value=0.0, max_value=300.0, step=0.01,
                                       value=float(placement["first_hit"]),
                                       format="%0.3f",
                                       key="ed_place_time_" + placement["id"],
                                       label_visibility="collapsed", disabled=locked,
                                       help="Adjust when the first hit lands.")
        if abs(when - float(placement["first_hit"])) > 1e-9:
            _try(lambda: mutations.move_placement(spec, sequence_id,
                                                  placement["id"], when))
        if columns[2].button("\u2715", key="ed_place_del_" + placement["id"],
                             disabled=locked):
            _try(lambda: mutations.remove_placement(spec, sequence_id, placement["id"]))
            # The list is drawn above the adder, so without this the deleted row
            # stays on screen until the next unrelated click. Fragment scope keeps
            # the redraw inside the editor.
            st.rerun(scope="fragment")
    if locked:
        return
    options = catalog.abilities_of(sequence["character"])
    if not options:
        st.caption("This character has no abilities in the catalogue.")
        return
    picker, adder = st.columns([0.7, 0.3])
    picked = picker.selectbox("Add ability", options,
                              format_func=lambda a: "%s - %s" % (abilities[a]["name"],
                                                                 abilities[a]["category"]),
                              key="ed_add_placement_pick_" + sequence_id,
                              label_visibility="collapsed")
    if adder.button("Add", key="ed_add_placement", use_container_width=True):
        _try(lambda: mutations.add_placement(spec, sequence_id, picked))
        st.rerun(scope="fragment")


def _sequence_preview(spec: dict, sequence_id: str) -> None:
    """The strip is a picture: the field time is set by the number box only."""
    sequence = spec["field_seqs"].get(sequence_id)
    if sequence is None:
        return
    selected = st.session_state.get(SELECTION_KEY)
    # px_per_sec=0 asks the strip to fit the column: at the shared 14px/s a 3.6s
    # sequence was drawn 71px wide and every band sat on top of its neighbour.
    payload = payloads.field_sequence_payload(spec, sequence_id, selected=selected,
                                              px_per_sec=0)
    strips.render(payload, key=SEQUENCE_STRIP)
    pick = strips.event("select", key=SEQUENCE_STRIP)
    if pick and pick.get("kind") == "placement" and pick.get("id"):
        st.session_state[SELECTION_KEY] = ("placement", pick["id"])
    results.render_issues(validate.sequence_issues(spec, sequence_id))


def _character_pills(spec: dict, current: str) -> str:
    """The owner selector: one pill per party slot, one of them always selected.

    The pill decides whose sequences the screen is about, so it is required - a
    click on the selected pill does nothing - and it starts on the first slot.
    """
    characters = spec["catalog"]["characters"]
    slots = [cid for cid in store.party_ids() if cid in characters]
    if not slots:
        owner = (spec["field_seqs"].get(current) or {}).get("character")
        slots = [owner] if owner in characters else [next(iter(characters))]
    if st.session_state.get("ed_sequence_owner") not in slots:
        st.session_state.pop("ed_sequence_owner", None)
    picked = st.pills("Character", slots, selection_mode="single", required=True,
                      default=slots[0], format_func=lambda cid: characters[cid]["name"],
                      key="ed_sequence_owner", label_visibility="collapsed")
    return picked or slots[0]


def sequence_screen(spec: dict) -> None:
    sequences = spec["field_seqs"]
    current = store.active_sequence(spec)
    left, right = st.columns([0.9, 1.7], gap="large")
    with left:
        owner = _character_pills(spec, current)
        mine = [sid for sid in sequences if sequences[sid]["character"] == owner]
        if current not in mine:
            # The pill owns the screen: the sequence follows it, never the other way.
            current = mine[0] if mine else ""
            if current:
                store.select_sequence(current)
        labels = {sid: sequences[sid]["name"] for sid in mine}
        picked = _library("Field sequence", mine, labels, current, key="ed_sequence_list",
                          on_pick=store.select_sequence)
        if picked and picked != current:
            store.select_sequence(picked)
            current = picked
        _sequence_actions(spec, current, owner)
        _sequence_form(spec, current)
        _placement_list(spec, current)
        _sequence_apply(spec, current)
    with right:
        _sequence_preview(spec, current)
