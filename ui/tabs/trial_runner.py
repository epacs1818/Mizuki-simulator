"""Tab 3, part 1: trial selection, the run button and the history entry."""
import copy
import datetime

import streamlit as st

from build_io import (assemble_party, collect_build_document, collect_slot,
                      party_rv_summary)
from timeline import CooldownError, RotationTimeline
from ui.editors import (party_characters, rotation_field_time,
                        select_trial_label, trial_field_time)
from ui.state import go_to_results_tab, invalidate_last_run


def render():
    """Draw the trial runner; return the selected trial (None if none fits)."""
    # --- SECTION A: TRIAL RUNNER ---
    # A preset trial is only offered when the selected team matches exactly the
    # team it was authored for; user-made trials have no such requirement.
    party_chars = party_characters()
    trial_pool = st.session_state["active_trial_pool"]
    trial_options = [k for k, t in trial_pool.items() if t.matches_party(party_chars)]
    trial_labels = {k: select_trial_label(k, trial_pool[k]) for k in trial_options}

    # Drop a stale widget value when the selected trial is no longer offered.
    if st.session_state.get("trial_selector") not in trial_options:
        st.session_state.pop("trial_selector", None)

    selected_trial_key = None
    trial_obj = None
    if trial_options:
        selected_trial_key = st.selectbox(
            "Select Trial",
            trial_options,
            format_func=lambda k: trial_labels.get(k, k),
            key="trial_selector"
        )
        trial_obj = trial_pool[selected_trial_key]
    else:
        st.warning(
            "No trial is available for this team. "
            "Please build a custom trial using the **Trial Editor** below."
        )

    if trial_obj is not None:
        with st.expander("Trial Breakdown", expanded=False):
            st.write(f"**Description:** {trial_obj.description}")
            end_label = trial_obj.end_mode.replace("_", " ").capitalize()
            if trial_obj.end_mode == "last_swap":
                duration_text = (f"{trial_field_time(trial_obj):.3f}s "
                                 f"(auto: ends at the last swap-out)")
            else:
                duration_text = f"{trial_obj.end_time:.3f}s"
            st.write(f"**End Mode:** {end_label} | **Duration:** {duration_text}")

            for r_idx, rotation in enumerate(trial_obj.rotations):
                st.markdown(
                    f"**Rotation #{r_idx + 1}: {rotation.name} "
                    f"[{rotation_field_time(rotation):.3f}s]** "
                    f"(Repeated {rotation.repetitions}x)"
                )
                for s_idx, seq in enumerate(rotation.sequences):
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ Step {s_idx + 1}: `{seq.name}` (*{seq.character}* — {seq.swap_out_time}s field time)")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Run Trial Simulation", type="primary", key="run_trial_btn", use_container_width=True):
            # Rebuild the party from the current widgets: the confirmed party may be older
            # than the inputs (a gear or substat-standard change does not re-confirm
            # itself). Rebuilding is cheap; only the simulation is expensive.
            rebuilt_party = assemble_party(
                [collect_slot(st.session_state, slot_num) for slot_num in range(1, 5)]
            )
            party = rebuilt_party or st.session_state.get("my_party", {})
            st.session_state["my_party"] = party
            st.session_state["party_created"] = bool(party)
            enemy = st.session_state.get("enemy_stats", {"enemy_lv": 100, "cryo_res": 0.1, "anemo_res": 0.1})

            try:
                timeline = RotationTimeline(party=party, enemy_stats=enemy)
                trial_duration = timeline.add_trial(trial_obj)
                timeline.evaluate_timeline()
            except CooldownError as exc:
                # A custom trial can schedule an ability before its CD is up. Show a
                # readable message instead of a traceback, and drop the stale
                # "Trial simulation complete!" so it cannot sit next to the error.
                invalidate_last_run()
                st.error(
                    f"Cooldown Error! {exc.character}'s '{exc.ability_name}' is on "
                    f"CD until {exc.until:.3f}s. Please edit your trial!"
                )
            else:
                analytics = timeline.get_analytics_summary(trial_duration)

                char_summary = ", ".join(
                    f"{name} Lv{data.get('level', 90)} C{data['constellation']} {data['talents']} "
                    f"{data['weapon']} R{data.get('refinement', 1)}"
                    for name, data in party.items()
                )
                enemy_summary = f"Lv{enemy.get('enemy_lv','?')} | Cryo Res {int(enemy.get('cryo_res',0.1)*100)}% | Anemo Res {int(enemy.get('anemo_res',0.1)*100)}%"
                # Substat standard used by THIS run (empty when every member is Manual),
                # so an old manual entry can never be confused with an RV/KQM one.
                standards = party_rv_summary(party)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

                entry = {
                    "timestamp": timestamp,
                    "sim_name": trial_labels.get(selected_trial_key, selected_trial_key),
                    "chars": char_summary,
                    "standards": standards,
                    "field_sequences": selected_trial_key,
                    "enemy": enemy_summary,
                    "trial_duration": trial_duration,
                    "analytics": analytics,
                    "timeline_events": timeline.global_events,
                    "snapshot_party": copy.deepcopy(party),
                    "snapshot_enemy": copy.deepcopy(enemy),
                    "snapshot_custom_fs": copy.deepcopy(st.session_state.get("custom_field_sequences", {})),
                    "snapshot_custom_rots": copy.deepcopy(st.session_state.get("custom_rotations", {})),
                    # Full, gear-complete build document for THIS run: the per-run
                    # export writes it, so the run can be re-imported and tweaked.
                    "snapshot_build": collect_build_document(
                        st.session_state,
                        trial_labels.get(selected_trial_key, selected_trial_key),
                    ),
                }

                if "history" not in st.session_state:
                    st.session_state["history"] = []
                st.session_state["history"].append(entry)
                st.session_state["trial_finished"] = True

    # Result of the last run. Rendered outside the button branch so the message and
    # the shortcut to the results stay available after the run.
    if st.session_state.get("trial_finished"):
        st.success("Trial simulation complete!")
        st.button(
            "View Simulation Results",
            type="primary",
            use_container_width=True,
            key="view_results_btn",
            on_click=go_to_results_tab,
            help="Go to the Simulation Results tab.",
        )


    st.markdown("<br><hr><br>", unsafe_allow_html=True)             
