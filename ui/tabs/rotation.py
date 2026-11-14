"""Tab 3: rotation / trial setup and the run button."""
import streamlit as st

from presets import STANDARD_TRIALS
from ui.tabs import rotation_editors, trial_runner


def render() -> None:
    if not st.session_state.get("party_created"):
        st.warning("⚠️ Please configure and create your party first in the **Team & Gear Setup** tab.")
    elif not st.session_state.get("enemy_confirmed"):
        st.warning("⚠️ Please confirm your enemy configuration first in the **Enemy Configuration** tab.")
    else:
        # Display lingering success notification from previous action
        if st.session_state.get("toast_msg"):
            st.success(st.session_state["toast_msg"])
            st.session_state["toast_msg"] = None

        st.header("Trial Setup")

        # Initialize session state pools for custom advanced building if missing
        if "custom_field_sequences" not in st.session_state:
            st.session_state["custom_field_sequences"] = {}
        if "custom_rotations" not in st.session_state:
            st.session_state["custom_rotations"] = {}
        if "active_trial_pool" not in st.session_state:
            st.session_state["active_trial_pool"] = STANDARD_TRIALS.copy()
        if "temp_trial_rot_entries" not in st.session_state:
            st.session_state["temp_trial_rot_entries"] = []

        # A trial published by the editor is queued the same way: the selectbox key
        # can only be written before the widget exists.
        pending_selection = st.session_state.pop("_pending_trial_selection", None)
        if pending_selection in st.session_state["active_trial_pool"]:
            st.session_state["trial_selector"] = pending_selection

        selected_trial = trial_runner.render()
        rotation_editors.render(selected_trial)
