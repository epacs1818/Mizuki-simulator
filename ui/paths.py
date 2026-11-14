"""Repo-root anchors.

Resolved from this file instead of the working directory, so the app behaves the same however Streamlit was started."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
MANUAL_FILE = ROOT / "user_manual.txt"


