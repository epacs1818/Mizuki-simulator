"""Tab 4: simulation results, charts and history."""

import pandas as pd
import plotly.express as px
import streamlit as st

from build_io import document_to_json, suggested_file_name
from ui.cards import render_party_card
from ui.paths import ASSETS
from ui.style import blend_chart, style_timeline_dataframe
from ui.table import build_timeline_dataframe


def render() -> None:
    st.header("Simulation Results & History")
    
    if "history" not in st.session_state or not st.session_state["history"]:
        st.info("No simulation history available yet. Run a trial in **Rotation Setup** to review results here.")
    else:
        if st.button("Clear All History", type="secondary"):
            st.session_state["history"] = []
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        history = st.session_state["history"]
        for i, entry in enumerate(reversed(history)):
            real_idx = len(history) - 1 - i
            
            # Ensure a default sim name exists
            if "sim_name" not in entry:
                entry["sim_name"] = f"Simulation #{real_idx + 1}"
            
            with st.expander(f"[{entry['timestamp']}] {entry['sim_name']}", expanded=(i == 0)):
    
                # 1. RENAME CONTROLS & DELETE
                col_name_input, col_info = st.columns([3, 1], vertical_alignment="bottom")
                with col_name_input:
                    new_name = st.text_input(
                        "Rename Simulation", 
                        value=entry["sim_name"], 
                        key=f"rename_sim_{real_idx}"
                    )
                    if new_name != entry["sim_name"]:
                        entry["sim_name"] = new_name
                        st.rerun()
                with col_info:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Delete Entry", key=f"del_hist_{real_idx}", use_container_width=True):
                        st.session_state["history"].pop(real_idx)
                        st.rerun()

                st.markdown("---")

                # 2. SIDE-BY-SIDE VISUAL CARDS (Party Cards & Enemy Target Card)
                party_cards_col, enemy_card_col = st.columns([2.2, 1], gap="medium")

                # Left: Party Character Cards
                with party_cards_col:
                    st.markdown("##### Party Setup")
                    snapshot_party = entry.get("snapshot_party", {})
                    if snapshot_party:
                        card_cols = st.columns(max(len(snapshot_party), 1))
                        for col, (char_name, data) in zip(card_cols, snapshot_party.items()):
                            with col:
                                with st.container(border=True):
                                    # Same card as Tab 1 (element, talents, gear, substat
                                    # standard), only more compact: the column is narrow.
                                    render_party_card(char_name, data, image_width=60,
                                                      font_size="0.75rem", column_gap=8)

                # Right: Enemy Target Card
                with enemy_card_col:
                    st.markdown("##### Target Overview")
                    snapshot_enemy = entry.get("snapshot_enemy", {})
                    if snapshot_enemy:
                        with st.container(border=True):
                            head_img, head_text = st.columns([1, 2], vertical_alignment="center")
                            with head_img:
                                enemy_img_path = ASSETS / "enemy" / "target.webp"
                                if enemy_img_path.exists():
                                    st.image(str(enemy_img_path), width=70)
                            with head_text:
                                st.markdown(f"**Level {snapshot_enemy.get('enemy_lv', 100)} Target**")
                                st.caption("Elemental & Physical Resistances")

                            st.markdown("---")
                            elements = ["pyro", "cryo", "hydro", "electro", "anemo", "geo", "dendro", "physical"]
                            rows = [
                                (elem.capitalize(), f"{snapshot_enemy.get(f'{elem}_res', 0.1) * 100:.1f}")
                                for elem in elements
                            ]
                            # Every resistance, matching the Tab 1 enemy card.
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

                # 3. SINGLE LINE TRIAL ROTATION SUMMARY
                st.markdown(f"**Trial Rotation Executed:** `{entry['field_sequences']}`")

                st.markdown("---")
                st.subheader("Performance Calculations & Analytics")
                analytics = entry.get("analytics") or {}

                if analytics:
                    # 1. Key Metrics Summary Cards
                    m1, m2, m3 = st.columns(3)
                    with m1:
                        st.metric("Total Damage", f"{analytics.get('total_damage', 0):,.1f}")
                    with m2:
                        st.metric("Overall DPS", f"{analytics.get('overall_dps', 0):,.1f} DMG/s")
                    with m3:
                        st.metric("Trial Duration", f"{analytics.get('trial_duration', 0):.1f}s")
                    
                    st.markdown("---")
                    
                    # 2. Three Pie Charts (Element, Hit Type, Damage Owner)
                    chart_col1, chart_col2, chart_col3 = st.columns(3)
                    
                    with chart_col1:
                        elem_data = analytics.get("element_breakdown", {})
                        if elem_data:
                            fig_elem = px.pie(
                                names=list(elem_data.keys()), 
                                values=list(elem_data.values()), 
                                title="Damage by Element",
                                hole=0.3
                            )
                            st.plotly_chart(blend_chart(fig_elem), use_container_width=True)
                            
                    with chart_col2:
                        hit_data = analytics.get("hit_type_breakdown", {})
                        if hit_data:
                            fig_hit = px.pie(
                                names=list(hit_data.keys()), 
                                values=list(hit_data.values()), 
                                title="Damage by Hit Type",
                                hole=0.3
                            )
                            st.plotly_chart(blend_chart(fig_hit), use_container_width=True)
                            
                    with chart_col3:
                        owner_data = analytics.get("owner_damage_share", {})
                        if owner_data:
                            fig_owner = px.pie(
                                names=list(owner_data.keys()), 
                                values=list(owner_data.values()), 
                                title="Damage Share by Character (Excl. Reactions)",
                                hole=0.3
                            )
                            st.plotly_chart(blend_chart(fig_owner), use_container_width=True)

                    st.markdown("---")

                    # 3. Per-Second DPS Histogram / Timeline Bar Chart
                    dps_timeline_data = analytics.get("dps_timeline", [])
                    if dps_timeline_data:
                        df_dps = pd.DataFrame(dps_timeline_data)
                        fig_dps = px.bar(
                            df_dps, 
                            x="Second", 
                            y="DPS", 
                            title="DPS Track Throughout Timeline (Per-Second Breakdown)",
                            labels={"Second": "Timeline Second (s)", "DPS": "Damage Per Second (DMG/s)"},
                            color_discrete_sequence=["#3b82f6"]
                        )
                        st.plotly_chart(blend_chart(fig_dps), use_container_width=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Timeline Dataframe Table
                if "timeline_events" in entry and entry["timeline_events"]:
                    st.markdown("##### Rotation Timeline Table")
                    sim_party = entry.get("snapshot_party") or st.session_state.get("my_party", {})
                    df_timeline = build_timeline_dataframe(
                        entry["timeline_events"],
                        party=sim_party,
                    )
                    show_advanced = st.checkbox("Show detailed columns", value=False, key=f"show_detail_{real_idx}")
                    if show_advanced:
                        view = df_timeline
                    else:
                        preview_order = [
                            "Time (s)", "Active", "Owner", "Action",
                            "Elemental App", "Aura", "Reaction", "Average DMG",
                        ]
                        view = df_timeline[[c for c in preview_order if c in df_timeline.columns]]
                    st.dataframe(style_timeline_dataframe(view), use_container_width=True, hide_index=True)

                    st.markdown("<br><hr>", unsafe_allow_html=True)
                                        
                    # 2. EXPORT CONFIGURATION FOR THIS SPECIFIC RUN
                    st.subheader("Export Run")
                    st.markdown(
                        "Save the exact gear, team, trial and custom setups used for this run. "
                        "The file loads again in **Team & Gear Setup → Save / Load Build** and "
                        "stays fully editable."
                    )

                    run_doc = entry["snapshot_build"]
                    run_doc["simulation_name"] = entry["sim_name"]
                    st.download_button(
                        label=f"Export JSON Config for '{entry['sim_name']}'",
                        data=document_to_json(run_doc),
                        file_name=suggested_file_name(run_doc),
                        mime="application/json",
                        key=f"export_hist_{real_idx}",
                        use_container_width=True
                    )
