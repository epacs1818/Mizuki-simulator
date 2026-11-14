"""Save / Load build panel: export the current build, restore a saved file."""

import hashlib

import streamlit as st

from build_io import (apply_build_document, build_party_from_document,
                      collect_build_document, document_to_json,
                      parse_document, suggested_file_name)
from ui.constants import BUILD_CATALOGUE
from ui.paths import MANUAL_FILE


def render_build_io_panel() -> None:
    """Save / Load: download the current build, or restore one from a file.

    The importer is idempotent: the uploaded bytes are hashed and a file is applied
    only once, so re-runs never revert edits made after loading.
    """
    st.subheader("Save / Load Build")
    upload_col, download_col = st.columns([1, 1], gap="large")

    with upload_col:
        uploaded_file = st.file_uploader(
            "Upload a previously saved build JSON file",
            type=["json"],
            key="config_importer",
            help="Restores the party, gear (mains + substats), enemy and custom trials.",
        )

    with download_col:
        st.markdown("<br>", unsafe_allow_html=True)
        current_doc = collect_build_document(st.session_state)
        st.download_button(
            "Export current build (.json)",
            data=document_to_json(current_doc),
            file_name=suggested_file_name(current_doc),
            mime="application/json",
            key="export_current_build",
            use_container_width=True,
        )
        # Read the file on every run, so edits to it are served immediately.
        manual_path = MANUAL_FILE
        manual_text = (manual_path.read_text(encoding="utf-8")
                       if manual_path.exists()
                       else "The user manual (user_manual.txt) is missing.")
        st.download_button(
            "User manual (.txt)",
            data=manual_text,
            file_name="user_manual.txt",
            mime="text/plain",
            key="download_user_manual",
            help="How to set up the party, build rotations and read the results.",
        )

    if uploaded_file is None:
        # Removing the file re-arms the importer, so the same file can be re-applied.
        st.session_state.pop("_imported_digest", None)
        return

    payload = uploaded_file.getvalue()
    digest = hashlib.sha1(payload).hexdigest()
    if st.session_state.get("_imported_digest") == digest:
        st.info(
            f"Build **{st.session_state.get('imported_sim_name') or uploaded_file.name}** is "
            "loaded. Every input below is editable — re-upload the file to reset to it."
        )
        return

    try:
        document = parse_document(payload)
    except Exception as exc:
        st.session_state["_imported_digest"] = digest
        st.error(f"Could not read '{uploaded_file.name}': {exc}")
        return

    warnings = apply_build_document(document, st.session_state, BUILD_CATALOGUE)
    st.session_state["my_party"] = build_party_from_document(document)
    st.session_state["party_created"] = bool(st.session_state["my_party"])
    # A stale signature would immediately mark the imported party as "changed".
    st.session_state.pop("last_team_signature", None)
    st.session_state["_imported_digest"] = digest

    st.success(
        f"Loaded **{document.get('simulation_name') or uploaded_file.name}** — "
        f"{len(st.session_state['my_party'])} characters, gear and trials restored. "
        "Tweak anything below, then press **Confirm party configuration**."
    )
    for warning in warnings:
        st.warning(warning)
