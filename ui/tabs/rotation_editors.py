"""Tab 3, part 2: the [Advanced] Trial Editor.

The editor itself is the ui.editor package; this module keeps the section header
(the runner above and the results tab below read as siblings) and hands over.
"""

import streamlit as st

from ui.editor import importer, open_trial, store
from ui.editor import render as editor_preview


def render(trial_obj=None) -> None:
    """Draw the [Advanced] Trial Editor.

    *trial_obj* is accepted for the runner call site; the editor keeps its own
    selection, because a preset trial and a spec trial are different objects.
    """
    st.header("[Advanced] Trial Editor")
    st.write(
        "Abilities represent character actions and talents triggered via button presses. "
        "Field Sequences define a character's active window on the field through a specific "
        "sequence of abilities and swaps. A Rotation groups multiple Field Sequences together "
        "to form a looping combat sequence. A Trial defines the overall simulation framework, "
        "combining rotations from start to finish based on either a custom duration or the end "
        "of the final rotation."
    )
    st.markdown("<br>", unsafe_allow_html=True)
    _open_selected(trial_obj)
    editor_preview()


def _open_selected(trial_obj) -> None:
    """Hand the trial the runner selected to the editor - the reverse of publish.

    A trial the editor already knows is reused: a preset opens as that preset
    (read-only), a trial created here opens as the trial that was created, so this
    never silently makes a second copy of the same trial.
    """
    if trial_obj is None:
        return
    if not st.button("Open \u201c%s\u201d in the editor" % trial_obj.name,
                     key="editor_open_trial",
                     help="Load the trial selected above into the editor to inspect or "
                          "change it. Presets open read-only - duplicate them to edit."):
        return
    try:
        trial_id = importer.trial_to_spec(store.spec(), trial_obj)
    except ValueError as exc:
        store.fail(str(exc))
        return
    open_trial(trial_id)
