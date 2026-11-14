"""Streamlit entry point: page configuration, wallpaper and the four tabs.

All page content lives in the `ui` package: ui.<module> for the shared pieces and
ui.tabs.<tab> for the four tabs, each exposing render(). This file must stay the
first thing that calls st.*, because st.set_page_config() has to run before any
other Streamlit command.
"""
import streamlit as st

from weapons import WEAPON_STATS

from ui.style import page_css
from ui.tabs import enemy, results, rotation, team

# Safe aliases for weapons and artifact sets to prevent KeyError
WEAPON_STATS.setdefault("Select Weapon", {"base_atk": 0.0})

# st.set_page_config must be the first Streamlit call and may run only once.
st.set_page_config(page_title="Yumemizuki Mizuki's Rotation Damage Calculator", layout="wide")

# ui/page.css, with the wallpaper inlined (see ui.style.page_css).
st.markdown(page_css(), unsafe_allow_html=True)

st.title("Yumemizuki Mizuki's Rotation Damage Calculator")

# Toast queued by the previous run (ui.state.toast): shown once, at the top of the
# app, so the editor acknowledgements survive the st.rerun() that follows.
_pending_toast = st.session_state.pop("_pending_toast", None)
if _pending_toast:
    st.toast(_pending_toast)

tab1, tab2, tab3, tab4 = st.tabs([
    "Team & Gear Setup",
    "Enemy Configuration",
    "Rotation Setup",
    "Simulation Results"
], key="main_tabs", on_change=st.rerun)

with tab1:
    team.render()

with tab2:
    enemy.render()

with tab3:
    rotation.render()

with tab4:
    results.render()
