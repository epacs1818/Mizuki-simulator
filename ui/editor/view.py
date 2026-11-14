"""The editor host: three screens behind one switch, inside a fragment.

The switch is a segmented control rather than nested tabs: it is one widget, so it
is testable, and it reads as a tab bar under the page CSS. The fragment keeps an
editor interaction from re-running the rest of the page.
"""

from __future__ import annotations

import streamlit as st

from ui.editor import screens, store

# The screen switch and its key live in store.py, because the screens and the
# warning click-through need to change them too.
SCREEN_KEY = store.SCREEN_KEY
SCREENS = store.SCREENS


@st.fragment
def body() -> None:
    """Draw the active screen; mutations inside it rerun the app on purpose."""
    pending = store.take_focus()
    if pending:
        store.apply_focus(pending)
    spec = store.spec()
    error = store.take_error()
    if error:
        st.error(error)
    picked = st.segmented_control("Screen", list(SCREENS), default=SCREENS[0],
                                  key=SCREEN_KEY, label_visibility="collapsed")
    if picked == "Rotation":
        screens.rotation_screen(spec)
    elif picked == "Field sequence":
        screens.sequence_screen(spec)
    else:
        screens.trial_screen(spec)


def open_trial(trial_id: str) -> None:
    """Show *trial_id* on the Trial screen (the "Open in editor" landing point)."""
    store.focus(("trial", trial_id))


def render() -> None:
    """Mount the editor: tab 3, under the [Advanced] Trial Editor header."""
    body()
