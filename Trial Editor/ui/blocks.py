"""Editor widgets for the trial (block list) and a field sequence (focus mode).

Both screens follow the same rule: native widgets for precision, the timeline
component for spatial editing, and *one* source of truth (the dict store).

Widget state trick
------------------
Each numeric input that the timeline can also change uses
`key="..." + st.session_state.setdefault(key, model_value)`. That makes the
widget read from session state (deterministic) and lets the timeline's callback
write into the same key before the widget is instantiated.
"""

from __future__ import annotations

import streamlit as st

import ui.state as state


# --------------------------------------------------------------------------
# trial: the block list
# --------------------------------------------------------------------------


def render_trial_blocks(spec: dict, result: dict) -> None:
    slots = state.active_trial(spec)["slots"]
    rotations = spec["rotations"]
    names = {rid: rot["name"] for rid, rot in rotations.items()}

    left, right = st.columns([1.0, 1.0], vertical_alignment="bottom")
    with left:
        st.markdown("**Rotations in this trial**")
    with right:
        st.caption(f"{len(slots)} block(s), runs back to back")

    if not slots:
        st.info("No rotations yet. Add one below to start building the trial.")

    for index, slot in enumerate(slots):
        prefix = f"{slot['id']}~"
        damage = sum(
            result["by_block"].get(block["id"], 0.0)
            for block in result["blocks"]
            if block["id"].startswith(prefix)
        )
        rot_duration = state.rotation_duration(spec, slot["rotation"])
        total_duration = rot_duration * slot["repeat"]

        cols = st.columns([0.8, 2.0, 0.7, 1.4, 1.1], vertical_alignment="center")

        with cols[0]:
            with st.container(horizontal=True, gap="small"):
                st.button(
                    "",
                    icon=":material/arrow_upward:",
                    key=f"up_{slot['id']}",
                    disabled=index == 0,
                    on_click=state.move_slot,
                    args=(index, -1),
                    help="Move earlier",
                )
                st.button(
                    "",
                    icon=":material/arrow_downward:",
                    key=f"dn_{slot['id']}",
                    disabled=index == len(slots) - 1,
                    on_click=state.move_slot,
                    args=(index, 1),
                    help="Move later",
                )

        with cols[1]:
            key = f"rot_{slot['id']}"
            if st.session_state.get(key) not in names:
                st.session_state[key] = slot["rotation"] if slot["rotation"] in names else next(iter(names))
            st.selectbox(
                "Rotation",
                list(names),
                key=key,
                format_func=lambda rid: names.get(rid, rid),
                label_visibility="collapsed",
                on_change=_apply_rotation,
                args=(index, key),
            )

        with cols[2]:
            key = f"rep_{slot['id']}"
            st.session_state.setdefault(key, int(slot["repeat"]))
            st.number_input(
                "Repeat",
                min_value=1,
                max_value=99,
                step=1,
                key=key,
                label_visibility="collapsed",
                on_change=_apply_repeat,
                args=(index, key),
            )

        with cols[3]:
            st.caption(f"{total_duration:.1f}s · {damage:,.0f} dmg")

        with cols[4]:
            choice = st.menu_button(
                "Actions",
                ["Open rotation", "Delete"],
                icon=":material/more_vert:",
                key=f"menu_{slot['id']}",
                width="content",
            )
            if choice == "Open rotation":
                state.request_view("rot", rot=slot["rotation"])
                st.rerun()
            elif choice == "Delete":
                state.delete_slot(index)
                st.rerun()

    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.button("Add rotation", icon=":material/add:", on_click=state.add_slot, args=(None,))


def _apply_rotation(index: int, key: str) -> None:
    state.set_slot_rotation(index, st.session_state[key])


def _apply_repeat(index: int, key: str) -> None:
    state.set_slot_repeat(index, int(st.session_state[key]))


# --------------------------------------------------------------------------
# field sequence: focus-mode editor (rendered into the left column)
# --------------------------------------------------------------------------


def next_free_time(fs: dict, abilities: dict) -> float:
    """Where a newly added ability should land: right after the last one."""
    end = 0.0
    for placement in fs["placements"]:
        ability = abilities.get(placement["ability"])
        if ability:
            end = max(
                end,
                placement["first_hit"] + max((h["offset"] for h in ability["hits"]), default=0.0),
            )
    return round(end, 2)


def field_sequence_stats(result: dict, fs_id: str) -> dict:
    blocks = [b for b in result["blocks"] if b["field_seq"] == fs_id]
    damage = sum(result["by_block"].get(b["id"], 0.0) for b in blocks)
    return {"damage": damage, "occurrences": len(blocks)}


def render_field_sequence_editor(spec: dict, result: dict, fs_id: str) -> None:
    cat = spec["catalog"]
    chars, abilities = cat["characters"], cat["abilities"]
    fs = spec["field_seqs"][fs_id]
    owner = chars[fs["character"]]

    st.markdown(f"**{owner['name']}** · field sequence")

    name_key = f"fname_{fs_id}"
    st.session_state.setdefault(name_key, fs["name"])
    st.text_input(
        "Rename field sequence",
        key=name_key,
        on_change=_apply_field_sequence_name,
        args=(fs_id, name_key),
        help="Press Enter to apply.",
    )

    ft_key = f"ft_{fs_id}"
    st.session_state.setdefault(ft_key, float(fs["field_time"]))
    st.number_input(
        "Field time (s)",
        min_value=0.5,
        max_value=120.0,
        step=0.1,
        key=ft_key,
        on_change=_apply_field_time,
        args=(fs_id, ft_key),
        help="The character swaps out here. Later hits still resolve - drag the red handle "
        "on the timeline to change this.",
    )

    stats = field_sequence_stats(result, fs_id)
    st.caption(f"{stats['occurrences']} use(s) in the trial · {stats['damage']:,.0f} damage")

    st.markdown("**Abilities**")
    if not fs["placements"]:
        st.caption("Empty. Add one below.")

    for placement in fs["placements"]:
        ability = abilities.get(placement["ability"])
        if ability is None:
            continue
        last = max((h["offset"] for h in ability["hits"]), default=0.0)

        cols = st.columns([1.9, 0.9, 0.45], vertical_alignment="center")
        with cols[0]:
            st.markdown(f"{ability['name']}")
            st.caption(f"{len(ability['hits'])} hits · ends {placement['first_hit'] + last:.2f}s")
        with cols[1]:
            key = f"ph_{placement['id']}"
            st.session_state.setdefault(key, float(placement["first_hit"]))
            st.number_input(
                "First hit",
                min_value=0.0,
                max_value=120.0,
                step=0.05,
                format="%.2f",
                key=key,
                label_visibility="collapsed",
                on_change=_apply_first_hit,
                args=(placement["id"], key),
            )
        with cols[2]:
            st.button(
                "",
                icon=":material/close:",
                key=f"rm_{placement['id']}",
                on_click=state.remove_placement,
                args=(placement["id"],),
                help="Remove from this field sequence",
            )

    st.divider()
    st.markdown("**Add an ability**")
    options: dict[str, str] = {}
    for ability_id, ability in abilities.items():
        if ability["character"] == fs["character"] and ability["category"] != "triggered":
            options.setdefault(ability["name"], ability_id)

    picked = st.pills("Pick an ability", list(options), key=f"pick_{fs_id}")

    at_key = f"newat_{fs_id}"
    st.session_state.setdefault(at_key, next_free_time(fs, abilities))
    st.number_input("First hit at (s)", min_value=0.0, max_value=120.0, step=0.1, key=at_key)

    st.button(
        "Add to field sequence",
        icon=":material/add:",
        width="stretch",
        disabled=not picked,
        on_click=_add_placement,
        args=(fs_id, options.get(picked), at_key),
    )

    triggered = [
        a for a in abilities.values() if a["character"] == fs["character"] and a["category"] == "triggered"
    ]
    if triggered:
        st.caption(
            "Auto: "
            + ", ".join(f"{a['name']} ({a['trigger'].get('on')})" for a in triggered)
            + " — never placed by hand."
        )

    st.divider()
    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.button("New field sequence", icon=":material/add:", on_click=_new_field_sequence)
        st.button(
            "Delete field sequence",
            icon=":material/delete:",
            on_click=_delete_field_sequence,
            args=(fs_id,),
            help="Also removes it from every rotation that uses it.",
        )


def _apply_field_sequence_name(fs_id: str, key: str) -> None:
    state.rename_field_sequence(fs_id, st.session_state[key])


def _new_field_sequence() -> None:
    """New sequences belong to the character chosen on that screen."""
    that_spec = state.store()
    character = st.session_state.get("fs_char")
    if character not in that_spec["catalog"]["characters"]:
        current = st.session_state.get("fs_pick") or state.view()["fs"]
        character = that_spec["field_seqs"].get(current, {}).get("character")
    if character is None:
        character = next(iter(that_spec["catalog"]["characters"]))
    fs_id = state.add_field_sequence(character)
    st.session_state["fs_pick"] = fs_id


def _delete_field_sequence(fs_id: str) -> None:
    state.delete_field_sequence(fs_id)
    st.session_state.pop("fs_pick", None)


def _apply_field_time(fs_id: str, key: str) -> None:
    state.set_field_time(fs_id, float(st.session_state[key]))


def _apply_first_hit(placement_id: str, key: str) -> None:
    state.move_placement(placement_id, float(st.session_state[key]))


def _add_placement(fs_id: str, ability_id: str | None, at_key: str) -> None:
    if not ability_id:
        return
    state.add_placement(fs_id, ability_id, float(st.session_state.get(at_key, 0.0)))
    spec = state.store()
    st.session_state[at_key] = next_free_time(spec["field_seqs"][fs_id], spec["catalog"]["abilities"])


# --------------------------------------------------------------------------
# rotation: reorderable block list
# --------------------------------------------------------------------------


def render_rotation_editor(spec: dict, rotation_id: str) -> None:
    cat = spec["catalog"]
    chars, field_seqs = cat["characters"], spec["field_seqs"]
    rotation = spec["rotations"][rotation_id]
    blocks = rotation["blocks"]

    name_key = f"rname_{rotation_id}"
    # Seeded once per rotation: the key is per-object, so switching selection
    # already shows the right name. (The old force-sync here re-stamped the box on
    # every rerun and erased whatever you were typing.)
    st.session_state.setdefault(name_key, rotation["name"])
    st.text_input(
        "Rename rotation",
        key=name_key,
        on_change=_apply_rotation_name,
        args=(rotation_id, name_key),
        help="Press Enter to apply.",
    )

    rotation_time = state.rotation_duration(spec, rotation_id)
    st.caption(f"{len(blocks)} block(s) · {rotation_time:.2f}s per rotation, played back to back")

    if not blocks:
        st.info("No blocks yet. Add a field sequence below.")

    for index, fs_id in enumerate(blocks):
        fs = field_seqs.get(fs_id)
        cols = st.columns([0.7, 2.9, 0.42, 0.42], vertical_alignment="center")

        with cols[0]:
            with st.container(horizontal=True, gap="small"):
                st.button(
                    "",
                    icon=":material/arrow_upward:",
                    key=f"bup_{rotation_id}_{index}",
                    disabled=index == 0,
                    on_click=state.move_rotation_block,
                    args=(rotation_id, index, -1),
                    help="Move earlier in the rotation",
                )
                st.button(
                    "",
                    icon=":material/arrow_downward:",
                    key=f"bdn_{rotation_id}_{index}",
                    disabled=index == len(blocks) - 1,
                    on_click=state.move_rotation_block,
                    args=(rotation_id, index, 1),
                    help="Move later in the rotation",
                )

        with cols[1]:
            if fs is None:
                st.markdown(f"**Missing block** · `{fs_id}`")
            else:
                st.markdown(f"**{index + 1}. {fs['name']}**")
                st.caption(
                    f"{chars[fs['character']]['name']} · {fs['field_time']:.2f}s · "
                    f"{len(fs['placements'])} abilities"
                )

        with cols[2]:
            if fs is not None:
                st.button(
                    "",
                    icon=":material/open_in_new:",
                    key=f"bedit_{rotation_id}_{index}",
                    on_click=_open_field_sequence,
                    args=(fs_id,),
                    help="Edit this field sequence",
                )

        with cols[3]:
            st.button(
                "",
                icon=":material/close:",
                key=f"brm_{rotation_id}_{index}",
                on_click=state.remove_rotation_block,
                args=(rotation_id, index),
                help="Remove block",
            )

    st.divider()
    st.markdown("**Add a block**")
    if not field_seqs:
        st.caption("No field sequences exist yet.")
    else:
        pick_key = f"newblk_{rotation_id}"
        if st.session_state.get(pick_key) not in field_seqs:
            st.session_state.pop(pick_key, None)
        picked = st.selectbox(
            "Field sequence to append",
            list(field_seqs),
            key=pick_key,
            label_visibility="collapsed",
            format_func=lambda fid: f"{field_seqs[fid]['name']} · {chars[field_seqs[fid]['character']]['name']}",
        )
        st.button(
            "Append to loop",
            icon=":material/add:",
            width="stretch",
            on_click=state.add_rotation_block,
            args=(rotation_id, picked),
        )

    st.divider()
    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.button("New rotation", icon=":material/add:", on_click=_new_rotation)
        st.button(
            "Delete rotation",
            icon=":material/delete:",
            on_click=_delete_rotation,
            args=(rotation_id,),
        )


def _apply_rotation_name(rotation_id: str, key: str) -> None:
    state.set_rotation_name(rotation_id, st.session_state[key])


def _open_field_sequence(fs_id: str) -> None:
    state.request_view("fs", fs=fs_id)


def _new_rotation() -> None:
    rotation_id = state.add_rotation()
    state.request_view("rot", rot=rotation_id)


def _delete_rotation(rotation_id: str) -> None:
    state.delete_rotation(rotation_id)
    remaining = list(state.store()["rotations"])
    if remaining:
        state.request_view("rot", rot=remaining[0])


