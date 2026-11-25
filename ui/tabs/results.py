"""Tab 4: simulation results, charts and history."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dps_curve import (DEFAULT_SIGMA, DEFAULT_TRUNCATION, auto_params,
                       gaussian_dps, hit_series)
from ui.cards import render_party_card
from ui.paths import ASSETS
from ui.style import (AUDIT_COLUMN_CONFIG, blend_chart, buff_column_config,
                      style_timeline_dataframe)
from ui.table import build_timeline_dataframe


def _dps_figure(grid, curve, *, duration, overall_dps):
    """Smoothed damage rate as one filled line on the dark glass theme.

    A burst reads as a peak and a quiet phase as a dip. The raw-hit rug that used
    to sit at y=0 is gone: individual hits are invisible next to the smoothed
    spikes, and the Rotation Timeline table below already lists every one of them.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=grid, y=curve, mode="lines", name="Damage Rate",
        line=dict(color="#60a5fa", width=2),
        fill="tozeroy", fillcolor="rgba(96,165,250,0.22)",
        hovertemplate="%{y:,.0f} DMG/s<extra></extra>",
    ))
    fig.add_hline(
        y=overall_dps, line_dash="dash", line_color="rgba(230,232,239,0.45)",
        annotation_text=f"Overall DPS {overall_dps:,.0f}",
        annotation_position="top right", annotation_font_color="#e6e8ef",
    )
    fig.update_layout(hovermode="x unified", showlegend=False)
    fig.update_xaxes(title_text="Time (s)", range=[0, duration])
    fig.update_yaxes(title_text="DMG/s", rangemode="tozero")
    fig = blend_chart(fig)
    # The title lives in the section heading now, so blend_chart's 52px title
    # margin would be dead space at the top of the plot.
    fig.update_layout(margin=dict(l=12, r=12, t=24, b=12))
    return fig


def _render_dps_chart(entry: dict, analytics: dict, real_idx: int) -> None:
    """Gaussian-smoothed damage rate for one history entry, rebuilt from its hit rows.

    Only the curve is recomputed, so nothing is re-simulated (~11 ms for a 587-hit
    trial). real_idx only feeds the commented tuning widgets below.
    """
    st.markdown("##### Damage Rate Throughout Timeline")

    times, damages = hit_series(entry.get("timeline_events") or [])
    duration = float(analytics.get("trial_duration")
                     or entry.get("trial_duration") or 0.0)
    if times.size == 0 or duration <= 0:
        st.caption("This run has no damaging hits, so there is no DPS curve to draw.")
        return

    # The chart ships with the library defaults (0.70 s sigma, 2.20 s window).
    sigma = DEFAULT_SIGMA
    truncation = DEFAULT_TRUNCATION

    # --- TUNING WIDGETS (hidden from the user: the chart should be read from the
    # picture alone). Uncomment this block and the sliders replace the two values
    # above; nothing else needs to change.
    # col_sigma, col_trunc = st.columns(2)
    # with col_sigma:
    #     sigma = st.slider(
    #         "Gaussian sigma (s)", 0.05, 1.0, DEFAULT_SIGMA, 0.05,
    #         key=f"dps_sigma_{real_idx}",
    #         help="Width of each hit's bell: small = spiky, large = rolling average.",
    #     )
    # with col_trunc:
    #     truncation = st.slider(
    #         "Truncation (s)", 0.5, 3.0, DEFAULT_TRUNCATION, 0.1,
    #         key=f"dps_trunc_{real_idx}",
    #         help="How far each bell is evaluated. Needs >= max_gap/2 so "
    #              "neighbouring windows overlap instead of leaving a dead zone.",
    #     )

    # dt follows the sigma that is actually drawn (>= 4 samples per bell), so the
    # rendered width can never disagree with the bell it is drawn from.
    dt = auto_params(times, duration, sigma=sigma)["dt"]
    grid, curve = gaussian_dps(times, damages, sigma=sigma, truncation=truncation,
                               dt=dt, duration=duration)

    # --- DIAGNOSTICS (hidden with the widgets): peak, curve area and hit gaps.
    # gaps = auto_params(times, duration)["gaps"]
    # area = float(curve.sum() * dt)
    # total_damage = float(analytics.get("total_damage") or 0.0)
    # if total_damage > 0:
    #     area_note = (f"{area:,.0f} damage ({100.0 * area / total_damage:.1f}% of "
    #                  f"the total; tails outside the trial window are clipped)")
    # else:
    #     area_note = f"{area:,.0f} damage"
    # st.caption(f"Peak {curve.max():,.0f} DMG/s - window +/-{max(truncation, sigma):.2f} s"
    #            f" - curve area {area_note}")
    # st.caption(f"Hit gaps: median {gaps['median']:.2f} s - p99 {gaps['p99']:.2f} s - "
    #            f"max {gaps['max']:.2f} s -> truncation >= {gaps['max'] / 2:.2f} s "
    #            f"keeps neighbouring windows overlapping.")
    st.plotly_chart(
        _dps_figure(grid, curve, duration=duration,
                    overall_dps=float(analytics.get("overall_dps") or 0.0)),
        use_container_width=True,
    )


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
                        st.metric("Trial Duration", f"{analytics.get('trial_duration', 0):.3f}s")
                    
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

                    # 3. Gaussian-smoothed damage-rate curve (replaces the
                    #    per-second bars: a hit is spread over its own bell
                    #    instead of being folded into second N).
                    _render_dps_chart(entry, analytics, real_idx)

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
                    st.dataframe(style_timeline_dataframe(view),
                                 column_config={
                                     **{name: config for name, config
                                        in AUDIT_COLUMN_CONFIG.items()
                                        if name in view.columns},
                                     **buff_column_config(sim_party, view),
                                 },
                                 width="stretch", hide_index=False, placeholder="-")

