"""Character cards and talent-input validation."""

import streamlit as st

from build_io import crit_model_label
from characters import get_character_element
from ui.paths import ASSETS


def validate_talents(talent_str):
    if not talent_str or not isinstance(talent_str, str) or not talent_str.strip():
        return False, "Talent levels cannot be empty.", None

    parts = [p.strip() for p in talent_str.strip().split("/")]
    if len(parts) != 3:
        return False, f"'{talent_str}' is invalid. Talent levels must follow the format 'int/int/int' (e.g. 1/13/13).", None

    levels = []
    for p in parts:
        if not p.isdigit():
            return False, f"'{talent_str}' contains non-integer values. Talent levels must follow the format 'int/int/int' (e.g. 1/13/13).", None
        lvl = int(p)
        if lvl > 13:
            return False, f"Talent level {lvl} in '{talent_str}' is bigger than 13. Values must be between 1 and 13 (e.g. 1/13/13).", None
        if lvl < 1:
            return False, f"Talent level {lvl} in '{talent_str}' must be at least 1 (e.g. 1/13/13).", None
        levels.append(lvl)

    return True, None, levels


def talents_label(data: dict) -> str:
    """Talent levels as the user typed them ("10/13/13"), for the party cards."""
    talents = data.get("talents")
    if isinstance(talents, str) and talents.strip():
        return talents.strip()
    levels = data.get("talent_levels")
    if isinstance(levels, (list, tuple)) and len(levels) == 3:
        return "/".join(str(int(level)) for level in levels)
    return "—"


def card_element(char_name: str, data: dict) -> str:
    """Element shown next to the level: the stored one, else the character table."""
    element = data.get("element")
    if element:
        return element
    return get_character_element(char_name) or "?"


def render_party_card(char_name: str, data: dict, *, image_width: int = 74,
                      font_size: str = "0.82rem", column_gap: int = 12) -> None:
    """One character card: portrait, identity lines, then the gear stat grid.

    Shared by the Tab 1 party cards and the Tab 4 result snapshots, so both always
    show the same fields.
    """
    img_col, id_col = st.columns([1, 1.7], vertical_alignment="center")
    with img_col:
        img_path = ASSETS / "characters" / f"{char_name.lower()}.webp"
        if img_path.exists():
            st.image(str(img_path), width=image_width)
    with id_col:
        st.markdown(f"**{char_name}** `C{data.get('constellation', 0)}`")
        st.caption(f"Lv {data.get('level', 90)} · {card_element(char_name, data)}")
        st.caption(f"{data.get('weapon') or 'No weapon'} R{data.get('refinement', 1)}")
        st.caption(f"Talents: {talents_label(data)}")
        st.caption(f"{data.get('artifact_set') or data.get('artifact') or 'None'}")
        # Substat standard: an RV/KQM build carries crit as one Crit Value (CV) line in
        # the grid below, a manual build carries CR / CD. Same options, new label.
        model_label = crit_model_label(data)
        st.caption(f"Substats: **{model_label}**" if model_label != "Manual"
                   else "Substats: Manual (CR / CD)")

    rows = "".join(
        f"<div style='opacity:0.85'>{label}</div>"
        f"<div style='text-align:right;font-weight:600'>{value}</div>"
        for label, value in (data.get("card_stats") or {}).items()
    )
    st.markdown(
        "<div style='display:grid;grid-template-columns:auto auto;"
        f"column-gap:{column_gap}px;font-size:{font_size};line-height:1.45;margin-top:4px'>"
        f"{rows}</div>",
        unsafe_allow_html=True,
    )


def render_character_cards(my_party: dict) -> None:
    """Compact off-field stat cards for the current party.

    Shown directly under the team section header so the party stays visible while the
    slots/artifacts below are edited. A thumbnail portrait sits next to the identity
    block, then the gear stats as a two-column grid; every card is drawn by
    render_party_card().
    """
    st.markdown("##### Character Cards (Off-Field Stats)")
    card_cols = st.columns(max(len(my_party), 1))
    for col, (char_name, data) in zip(card_cols, my_party.items()):
        with col:
            with st.container(border=True):
                render_party_card(char_name, data)
    st.markdown("")
