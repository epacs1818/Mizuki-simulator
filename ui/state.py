"""Session-state helpers shared by every tab: tab jumps, the toast queue and the run-cache invalidation."""

import streamlit as st


# Callback functions for seamless programmatic tab switching
def go_to_enemy_tab():
    st.session_state["main_tabs"] = "Enemy Configuration"

def go_to_rotation_tab():
    st.session_state["main_tabs"] = "Rotation Setup"

def go_to_results_tab():
    st.session_state["main_tabs"] = "Simulation Results"


def invalidate_last_run():
    """Drop the "Trial simulation complete!" state: the inputs it ran on are stale.

    Called by every party/gear change and by every trial-editor mutation, so the
    confirmation (and the results shortcut) can never outlive the inputs that
    produced it.
    """
    st.session_state.pop("trial_finished", None)


def toast(message: str) -> None:
    """Queue a bottom toast for the next run.

    Most editor actions are followed by st.rerun(); a toast emitted in the same run
    would be discarded with the rest of that run's output, so the message is queued
    and shown at the top of the next run (the same click, one instant later).
    """
    st.session_state["_pending_toast"] = message
