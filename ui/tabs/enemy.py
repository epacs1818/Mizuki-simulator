"""Tab 2: enemy configuration."""

import streamlit as st

from ui.paths import ASSETS
from ui.state import go_to_rotation_tab


def render() -> None:
    if not st.session_state.get("party_created"):
        st.warning("⚠️ Please configure and create your party first in the **Team & Gear Setup** tab.")
    else:
        st.header("Enemy Configuration")
        
        is_confirmed = st.session_state.get("enemy_confirmed", False)
        
        # Always maintain a 2-column structure so the configuration inputs stay fixed on the left
        col_inputs, col_card = st.columns([1.3, 0.7], gap="large")

        with col_inputs:
            enemy_lv = st.number_input(
                "Enemy Level",
                min_value=1,
                max_value=150,
                value=st.session_state.get("enemy_lv", 100),
                step=1,
                key="input_enemy_lv"
            )
            
            st.markdown("##### Enemy Elemental & Physical Resistances (%)")
            elements = ["pyro", "cryo", "hydro", "electro", "anemo", "geo", "dendro", "physical"]
            
            enemy_res_inputs = {}
            
            # Row 1 of resistances (First 4 elements)
            res_cols1 = st.columns(4)
            for i, elem in enumerate(elements[:4]):
                with res_cols1[i]:
                    res_val = st.number_input(
                        f"{elem.capitalize()}",
                        value=float(st.session_state.get(f"input_{elem}_res", 10.0)),
                        step=1.0,
                        format="%.1f",
                        key=f"input_{elem}_res"
                    )
                    enemy_res_inputs[f"{elem}_res"] = res_val / 100.0

            # Row 2 of resistances (Last 4 elements)
            res_cols2 = st.columns(4)
            for i, elem in enumerate(elements[4:]):
                with res_cols2[i]:
                    res_val = st.number_input(
                        f"{elem.capitalize()}",
                        value=float(st.session_state.get(f"input_{elem}_res", 10.0)),
                        step=1.0,
                        format="%.1f",
                        key=f"input_{elem}_res"
                    )
                    enemy_res_inputs[f"{elem}_res"] = res_val / 100.0

            # Track changes to automatically un-confirm if values are modified
            current_enemy_signature = (enemy_lv, tuple(enemy_res_inputs.values()))
            if "last_enemy_signature" in st.session_state and st.session_state["last_enemy_signature"] != current_enemy_signature:
                st.session_state["enemy_confirmed"] = False

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Confirm Enemy Configuration", type="primary", key="confirm_enemy_btn"):
                enemy_stats = {
                    "enemy_lv": int(enemy_lv),
                    **enemy_res_inputs
                }
                st.session_state["enemy_stats"] = enemy_stats
                st.session_state["enemy_confirmed"] = True
                st.session_state["last_enemy_signature"] = current_enemy_signature
                st.success("Enemy configuration confirmed!")
                st.rerun()

        # Enemy summary card: a small thumbnail next to the level, then a two-column
        # resistance grid.
        with col_card:
            st.markdown("### Target Overview")
            if is_confirmed:
                with st.container(border=True):
                    head_img, head_text = st.columns([1, 2], vertical_alignment="center")
                    with head_img:
                        enemy_img_path = ASSETS / "enemy" / "target.webp"
                        if enemy_img_path.exists():
                            st.image(str(enemy_img_path), width=88)
                    with head_text:
                        st.markdown(f"**Level {enemy_lv} Target**")
                        st.caption("Elemental & Physical Resistances")

                    st.markdown("---")
                    rows = [
                        (elem.capitalize(), f"{enemy_res_inputs.get(f'{elem}_res', 0.1) * 100:.1f}")
                        for elem in elements
                    ]
                    grid = "".join(
                        f"<div style='opacity:0.85'>{name}</div>"
                        f"<div style='text-align:right;font-weight:600'>{value}%</div>"
                        for name, value in rows
                    )
                    st.markdown(
                        "<div style='display:grid;grid-template-columns:auto auto;"
                        "column-gap:14px;font-size:0.86rem;line-height:1.5'>"
                        f"{grid}</div>",
                        unsafe_allow_html=True,
                    )

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.button(
                        "Proceed to Rotation Setup", 
                        type="primary", 
                        use_container_width=True, 
                        key="proceed_to_rot", 
                        on_click=go_to_rotation_tab
                    )
            
