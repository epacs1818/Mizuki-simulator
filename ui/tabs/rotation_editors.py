"""Tab 3, part 2: the [Advanced] trial / rotation / field-sequence editors."""
import copy

import streamlit as st

from build_io import load_trial_into_editor
from models import FieldSequence, Rotation, Trial
from presets import STANDARD_TRIALS
from ui.constants import CHARACTERS
from ui.editors import (available_abilities, available_field_sequences,
                        party_characters)
from ui.state import invalidate_last_run, toast


def render(trial_obj) -> None:
    """Draw the advanced editors for the trial selected in the runner."""
    all_available_sequences = available_field_sequences()

    # --- SECTION B: [ADVANCED] TRIAL EDITOR (Open Section) ---
    st.header("[Advanced] Trial Editor")
    st.write(
        "Abilities represent character actions and talents triggered via button presses. "
        "Field Sequences define a character's active window on the field through a specific sequence of abilities and swaps. "
        "A Rotation groups multiple Field Sequences together to form a looping combat sequence. "
        "A Trial defines the overall simulation framework, combining rotations from start to finish "
        "based on either a custom duration or the end of the final rotation."
    )
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- TRIAL ASSEMBLY (Placed at the very top of Advanced Editor) ---
    trial_col_left, trial_col_right = st.columns(2, gap="large")

    with trial_col_left:
        trial_name = st.text_input("Trial Name", placeholder="e.g. 'Mizuki Faruzan Sac Frag 120s'", key="adv_trial_name")
        trial_desc = st.text_input("Trial Description", placeholder="e.g. 'Using the pull out tech'", key="adv_trial_desc")            
        end_at_last_swap = st.checkbox("End at last rotation (auto-terminate at final swap out)", value=False, key="adv_end_swap_toggle")
        manual_end_time = st.number_input(
            "Trial Duration (s)", 
            min_value=1.0, 
            value=120.0, 
            step=1.0, 
            disabled=end_at_last_swap,
            key="adv_trial_duration"
        )

        # Makes any trial editable — including the shipped presets and trials
        # restored from a file: its rotations are copied into the editor pools.
        if trial_obj is not None:
            if st.button("⤵ Load selected trial into editor",
                         key="load_trial_into_editor_btn",
                         use_container_width=True,
                         help="Copies this trial's rotations into the editor so they "
                              "can be tweaked and re-used in a new trial."):
                load_trial_into_editor(trial_obj, st.session_state)
                toast(f"Trial '{trial_obj.name}' loaded into the editor.")
                invalidate_last_run()
                st.rerun()

    with trial_col_right:
        if st.session_state["custom_rotations"]:
            chosen_rot_key = st.selectbox("Select Rotation", list(st.session_state["custom_rotations"].keys()), key="adv_trial_rot_select")
            rot_reps_input = st.number_input("Repetitions", min_value=1, max_value=20, value=1, key="adv_trial_rot_reps")
            
            if st.button("➕ Add Rotation to Trial", key="adv_add_rot_to_trial_btn", use_container_width=True):
                st.session_state["temp_trial_rot_entries"].append({"rotation_name": chosen_rot_key, "repetitions": rot_reps_input})
                toast(f"Added {chosen_rot_key} ({rot_reps_input}x) to trial queue.")
                invalidate_last_run()
                st.rerun()

            if st.session_state["temp_trial_rot_entries"]:
                st.markdown("**Current Rotations:**")
                for entry_idx, entry in enumerate(st.session_state["temp_trial_rot_entries"]):
                    rc1, rc2 = st.columns([4, 1], vertical_alignment="center")
                    with rc1:
                        st.text(f"{entry_idx + 1}. {entry['rotation_name']} ({entry['repetitions']}x)")
                    with rc2:
                        if st.button("✕", key=f"rm_trial_rot_{entry_idx}"):
                            st.session_state["temp_trial_rot_entries"].pop(entry_idx)
                            invalidate_last_run()
                            st.rerun()
        else:
            st.info("No custom rotations created yet.")

    # Option to delete custom trials if any exist
    if st.session_state["active_trial_pool"]:
        custom_trials_to_delete = [k for k in st.session_state["active_trial_pool"].keys() if k not in STANDARD_TRIALS]
        if custom_trials_to_delete:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("Manage / Delete Custom Trials"):
                del_trial_key = st.selectbox("Select Custom Trial to Delete", custom_trials_to_delete, key="del_trial_select")
                if st.button("Delete Selected Trial", key="del_trial_btn"):
                    del st.session_state["active_trial_pool"][del_trial_key]
                    toast(f"Custom trial '{del_trial_key}' deleted.")
                    invalidate_last_run()
                    st.rerun()

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # --- EXPANDER 1: CUSTOM ROTATION BUILDER ---
    with st.expander("Create Custom Rotation", expanded=False):
        rot_name = st.text_input("Rotation Name", placeholder="e.g. 'No Burst Starter'", key="adv_rot_name")

        # The order matters and a sequence may appear more than once (e.g. a
        # "burst every other loop" rotation that contains both variants).
        if "temp_rot_seqs" not in st.session_state:
            st.session_state["temp_rot_seqs"] = []
        available_seq_keys = list(all_available_sequences.keys())
        st.session_state["temp_rot_seqs"] = [
            key for key in st.session_state["temp_rot_seqs"]
            if key in all_available_sequences
        ]

        seq_to_add = None
        pick_col, add_col = st.columns([4, 1], vertical_alignment="bottom")
        with pick_col:
            if available_seq_keys:
                if st.session_state.get("adv_rot_seq_pick") not in available_seq_keys:
                    st.session_state.pop("adv_rot_seq_pick", None)
                seq_to_add = st.selectbox("Select Field Sequence",
                                          available_seq_keys, key="adv_rot_seq_pick")
            else:
                st.info("No field sequence is available for this party.")
        with add_col:
            if st.button("➕ Add", key="adv_rot_add_seq_btn",
                         use_container_width=True, disabled=seq_to_add is None):
                st.session_state["temp_rot_seqs"].append(seq_to_add)
                invalidate_last_run()
                st.rerun()

        if st.session_state["temp_rot_seqs"]:
            st.markdown("**Sequence order** (a sequence may be added more than once):")
            for seq_idx, seq_key in enumerate(list(st.session_state["temp_rot_seqs"])):
                label_col, up_col, down_col, remove_col = st.columns(
                    [7, 1, 1, 1], vertical_alignment="center")
                with label_col:
                    st.text(f"{seq_idx + 1}. {seq_key}")
                with up_col:
                    if st.button("↑", key=f"rot_seq_up_{seq_idx}",
                                 disabled=seq_idx == 0):
                        seqs = st.session_state["temp_rot_seqs"]
                        seqs[seq_idx - 1], seqs[seq_idx] = seqs[seq_idx], seqs[seq_idx - 1]
                        invalidate_last_run()
                        st.rerun()
                with down_col:
                    if st.button("↓", key=f"rot_seq_down_{seq_idx}",
                                 disabled=seq_idx == len(st.session_state["temp_rot_seqs"]) - 1):
                        seqs = st.session_state["temp_rot_seqs"]
                        seqs[seq_idx + 1], seqs[seq_idx] = seqs[seq_idx], seqs[seq_idx + 1]
                        invalidate_last_run()
                        st.rerun()
                with remove_col:
                    if st.button("✕", key=f"rot_seq_remove_{seq_idx}"):
                        st.session_state["temp_rot_seqs"].pop(seq_idx)
                        invalidate_last_run()
                        st.rerun()

        col_rot_save, col_rot_del = st.columns([4, 1], vertical_alignment="bottom")
        with col_rot_save:
            if st.button("Save Rotation", key="adv_save_rot_btn", type="secondary", use_container_width=True):
                rotation_seqs = st.session_state["temp_rot_seqs"]
                if rot_name and rotation_seqs:
                    seq_list = [all_available_sequences[k] for k in rotation_seqs]
                    new_rot = Rotation(name=rot_name, sequences=seq_list, repetitions=1)
                    st.session_state["custom_rotations"][rot_name] = new_rot
                    st.session_state["temp_rot_seqs"] = []
                    toast(f"Rotation '{rot_name}' saved successfully!")
                    invalidate_last_run()
                    st.rerun()
                else:
                    st.error("Please provide a rotation name and add at least one field sequence.")
        
        # Management/Deletion for custom rotations
        if st.session_state["custom_rotations"]:
            with st.expander("Manage / Delete Custom Rotations"):
                del_rot_key = st.selectbox("Select Custom Rotation to Delete", list(st.session_state["custom_rotations"].keys()), key="del_rot_select")
                if st.button("✕ Delete Rotation", key="del_rot_btn"):
                    del st.session_state["custom_rotations"][del_rot_key]
                    toast(f"Rotation '{del_rot_key}' deleted.")
                    invalidate_last_run()
                    st.rerun()

    # --- EXPANDER 2: CUSTOM FIELD SEQUENCE BUILDER ---
    with st.expander("Create Custom Field Sequence", expanded=False):
        seq_col_left, seq_col_right = st.columns(2, gap="large")

        with seq_col_left:
            seq_name = st.text_input("Field Sequence Name", placeholder="e.g. 'Aether ECQ'", key="adv_seq_name")
            # Only characters that are in the party can have a field sequence.
            seq_char_options = party_characters() or list(CHARACTERS[1:])
            if st.session_state.get("adv_seq_char") not in seq_char_options:
                st.session_state.pop("adv_seq_char", None)
            seq_char = st.selectbox("Character", seq_char_options, key="adv_seq_char")
            seq_swap_time = st.number_input("Field Time / Swap-Out Time (s)", min_value=0.1, value=3.0, step=1.0, key="adv_swap_time")

        with seq_col_right:
            # Every ability defined in abilities.py for that character (no
            # hardcoded list here: new abilities appear automatically).
            avail_abilities = available_abilities(seq_char)

            if "temp_seq_calls" not in st.session_state:
                st.session_state["temp_seq_calls"] = []

            if avail_abilities:
                if st.session_state.get("adv_abil_picker") not in avail_abilities:
                    st.session_state.pop("adv_abil_picker", None)
                chosen_abil_key = st.selectbox("Select Ability to Add", list(avail_abilities.keys()), key="adv_abil_picker")
                abil_start_time = st.number_input("Ability Insertion Time(s) (relative to Swap In)", min_value=0.0, value=0.0, step=0.1, key="adv_abil_time")
                
                if st.button("➕ Add Ability to Sequence", key="adv_add_abil_btn", use_container_width=True):
                    st.session_state["temp_seq_calls"].append((abil_start_time, avail_abilities[chosen_abil_key]))
                    toast(f"Added {chosen_abil_key} at {abil_start_time}s")
                    invalidate_last_run()
                    st.rerun()

        # Queued abilities list arranged horizontally below the two divided columns
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state["temp_seq_calls"]:
            st.markdown("**Queued Ability Calls:**")
            badges_html = "".join(
                f"<span style='background-color: #3b82f6; color: white; padding: 6px 12px; border-radius: 12px; margin-right: 8px; font-size: 14px; display: inline-block; margin-bottom: 6px;'> [{st_time}s] {ab_obj.name}</span>"
                for st_time, ab_obj in st.session_state["temp_seq_calls"]
            )
            st.markdown(f"<div style='display: flex; flex-wrap: wrap; gap: 4px; align-items: center;'>{badges_html}</div>", unsafe_allow_html=True)
            
            if st.button("Clear Abilities", key="clear_seq_calls_btn"):
                st.session_state["temp_seq_calls"] = []
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Save Field Sequence", key="adv_save_seq_btn", type="secondary", use_container_width=True):
            if seq_name:
                new_fs = FieldSequence(name=seq_name, character=seq_char, swap_out_time=seq_swap_time)
                for st_time, ab_obj in st.session_state["temp_seq_calls"]:
                    new_fs.add_ability(st_time, ab_obj)
                st.session_state["custom_field_sequences"][seq_name] = new_fs
                st.session_state["temp_seq_calls"] = []
                toast(f"Field Sequence '{seq_name}' saved successfully!")
                invalidate_last_run()
                st.rerun()
            else:
                st.error("Please provide a name for the field sequence.")

        # Management/Deletion for custom field sequences
        if st.session_state["custom_field_sequences"]:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("Manage / Delete Custom Field Sequences"):
                del_fs_key = st.selectbox("Select Custom Field Sequence to Delete", list(st.session_state["custom_field_sequences"].keys()), key="del_fs_select")
                if st.button("✕ Delete Field Sequence", key="del_fs_btn"):
                    del st.session_state["custom_field_sequences"][del_fs_key]
                    toast(f"Field Sequence '{del_fs_key}' deleted.")
                    invalidate_last_run()
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Create Trial", type="primary", key="adv_create_trial_btn", use_container_width=True):
        if trial_name and st.session_state["temp_trial_rot_entries"]:
            rot_list = []
            for entry in st.session_state["temp_trial_rot_entries"]:
                base_rot = st.session_state["custom_rotations"][entry["rotation_name"]]
                rot_copy = copy.deepcopy(base_rot)
                rot_copy.repetitions = entry["repetitions"]
                rot_list.append(rot_copy)

            mode = "last_swap" if end_at_last_swap else "time"
            new_trial = Trial(
                name=trial_name,
                rotations=rot_list,
                end_mode=mode,
                end_time=manual_end_time,
                description=trial_desc
            )

            st.session_state["active_trial_pool"][trial_name] = new_trial
            st.session_state["temp_trial_rot_entries"] = []
            st.session_state["toast_msg"] = f"Trial '{trial_name}' successfully created and added to the selection dropdown!"
            invalidate_last_run()
            st.rerun()
        else:
            st.error("Please enter a trial name and add at least one rotation.")
