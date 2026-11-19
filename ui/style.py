"""Page styling: the wallpaper loader, the page stylesheet and the audit-table colours."""
import base64
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from ui.paths import ASSETS

CSS_FILE = Path(__file__).with_name("page.css")


def get_base64_image(image_path):
    """Base64 payload of an image file (the wallpaper is inlined into the CSS)."""
    with open(image_path, "rb") as handle:
        return base64.b64encode(handle.read()).decode()


def page_css() -> str:
    """The page stylesheet with the wallpaper substituted in.

    Read on every run (a few KB) so CSS edits show up without restarting Streamlit;
    the base64 wallpaper stays out of the file behind the __WALLPAPER__ placeholder.
    """
    wallpaper = get_base64_image(ASSETS / "wallpaper.jpg")
    return CSS_FILE.read_text(encoding="utf-8").replace("__WALLPAPER__", wallpaper)


AUDIT_BLOCKS = {
    "time": {"Time (s)"},
    "desc": {"Active", "Owner", "Action"},
    "reaction": {"Elemental App", "Aura", "Reaction"},
    "stats": {"HP", "ATK", "DEF", "EM", "CR%", "CD%", "CV"},
    "mult": {"Base DMG", "Quills", "Bonus Mult", "Elev Mult", "Crit Mult", "DEF Mult", "Res Mult"},
    "output": {"Average DMG", "Non-Crit DMG", "Crit DMG", "Effective Avg DMG"},
}

# ---------------------------------------------------------------------------
# st.column_config for the audit table
# ---------------------------------------------------------------------------
# One simple line per FIXED column, in the same shape the Streamlit docs use
# (st.column_config.NumberColumn("name", format=..., help=...)). `format` is display
# only: the values stay numbers, so a header click still sorts by value, and
# column_config formatting takes precedence over pandas.Styler formatting - which is
# why style_timeline_dataframe() only paints colours.
# Columns that are NOT listed (the buff columns) keep the type Streamlit infers from
# their dtype: a checkbox for the boolean flags, a plain number for the stack counters.
AUDIT_COLUMN_CONFIG = {
    "Time (s)": st.column_config.NumberColumn(
        "Time (s)", format="%.3f", help="Event time in seconds (3 decimals).", pinned=True),
    "Active": st.column_config.TextColumn(
        "Active", help="Character on field when this event resolved.", pinned=True),
    "Owner": st.column_config.TextColumn(
        "Owner", help="Character credited with the hit or proc.", pinned=True),
    # The 4th column is pinned: the row's action stays visible while scrolling right.
    "Action": st.column_config.TextColumn(
        "Action", help="Hit / ability name, or the audit row (swap, proc).",
        pinned=True),
    "Aura": st.column_config.NumberColumn(
        "Aura", format="%.2f U",
        help="Cryo aura on the target *before* this hit applies its element."),
    "Elemental App": st.column_config.NumberColumn(
        "Elemental App", format="%.0f U", help="Elemental gauge this hit applied."),
    "Reaction": st.column_config.TextColumn(
        "Reaction", help="Reaction this hit triggered (Stellar Swirl / Vortex)."),
    "HP": st.column_config.NumberColumn(
        "HP", format="%d", help="Owner's HP at this instant, with buffs."),
    "ATK": st.column_config.NumberColumn(
        "ATK", format="%d", help="Owner's ATK at this instant, with buffs."),
    "DEF": st.column_config.NumberColumn(
        "DEF", format="%d", help="Owner's DEF at this instant, with buffs."),
    "EM": st.column_config.NumberColumn(
        "EM", format="%d", help="Owner's Elemental Mastery at this instant."),
    "CR%": st.column_config.NumberColumn(
        "CR%", format="%.1f",
        help="Crit Rate (hidden in a 100% RV / KQM build: crit is one CV)."),
    "CD%": st.column_config.NumberColumn(
        "CD%", format="%.1f",
        help="Crit DMG (hidden in a 100% RV / KQM build: crit is one CV)."),
    "CV": st.column_config.NumberColumn(
        "CV", format="%.1f", help="Crit Value = 2 x CR + CD."),
    "Base DMG": st.column_config.NumberColumn(
        "Base DMG", format="%.1f",
        help="Scaling stat x motion value, before any multiplier."),
    "Quills": st.column_config.NumberColumn(
        "Quills", format="%.1f",
        help="Flat damage added after the bonus multiplier (Faruzan quill, VBTD)."),
    "Bonus Mult": st.column_config.NumberColumn(
        "Bonus Mult", format="%.3f",
        help="Element / attack-type / stellar bonus multiplier (quills excluded)."),
    "Elev Mult": st.column_config.NumberColumn(
        "Elev Mult", format="%.3f",
        help="Elevation multiplier - stellar damage only, never reactions."),
    "Crit Mult": st.column_config.NumberColumn(
        "Crit Mult", format="%.3f",
        help="Expected crit multiplier (1 + CR x CD at this instant)."),
    "DEF Mult": st.column_config.NumberColumn(
        "DEF Mult", format="%.3f", help="Enemy DEF mitigation (standard damage only)."),
    "Res Mult": st.column_config.NumberColumn(
        "Res Mult", format="%.3f", help="Enemy RES multiplier after shred."),
    "Average DMG": st.column_config.NumberColumn(
        "Average DMG", format="%.1f", help="Damage weighted by crit chance."),
    "Non-Crit DMG": st.column_config.NumberColumn(
        "Non-Crit DMG", format="%.1f", help="Damage with no crit."),
    "Crit DMG": st.column_config.NumberColumn(
        "Crit DMG", format="%.1f", help="Damage with a guaranteed crit."),
    "Effective Avg DMG": st.column_config.NumberColumn(
        "Effective Avg DMG", format="%.1f",
        help="Average damage before the RES multiplier."),
}

# A stack counter reads as "empty" when it is zero / missing. Only the STACK buff
# columns are painted (see style_timeline_dataframe): the boolean flags render as
# checkboxes, which the grid draws with its own theme colours, so styling them here
# would have no effect (and would only risk leaking a colour into the cell).
INACTIVE_CELLS = ("", "-", "OFF", "0", "None", "nan")


def _is_inactive(value) -> bool:
    if value is None or value is pd.NA:
        return True
    # pandas hands row values back as numpy scalars (numpy.bool_ is NOT a bool, and
    # numpy ints are not Python ints), so the numpy base classes are tested too.
    if isinstance(value, (bool, np.bool_)):
        return not bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return value != value or value == 0   # NaN or a zero count
    return str(value).strip() in INACTIVE_CELLS

# One dark tint per party member: consecutive characters get different row colours.
OWNER_BG = ("#0b3d2e", "#1e3a8a", "#4c1d95", "#7c2d12", "#0f766e", "#831843", "#3f6212", "#1e40af")

def column_block(column):
    """Map an audit-table column to its block (buff = everything not core)."""
    for block, columns in AUDIT_BLOCKS.items():
        if column in columns:
            return block
    return "buff"


def blend_chart(fig):
    """Make a Plotly figure sit on the dark glass panels instead of a white rectangle.

    px.pie / px.bar draw Plotly's plain white canvas by default, which looked like a
    bright block on the wallpaper UI (and its dark tick/label colours were unreadable
    once the card behind it is translucent). Transparent paper/plot + light text keeps
    the series colours untouched.
    """
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e6e8ef"),
        title_font=dict(color="#e6e8ef"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#e6e8ef")),
        margin=dict(l=12, r=12, t=52, b=12),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.12)",
                     zerolinecolor="rgba(255,255,255,0.20)",
                     linecolor="rgba(255,255,255,0.25)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.12)",
                     zerolinecolor="rgba(255,255,255,0.20)",
                     linecolor="rgba(255,255,255,0.25)")
    return fig


def _stack_columns(df):
    """Buff columns that carry STACK COUNTS - the only cells this table paints."""
    return [column for column in df.columns
            if column_block(column) == "buff"
            and not pd.api.types.is_bool_dtype(df[column])
            and pd.api.types.is_integer_dtype(df[column])]


def _cell_css(column, value, background, stack_columns):
    """CSS for one audit cell: the owner's row tint, plus the stack highlight."""
    css = [f"background-color: {background}", "color: #f8fafc"]
    if column in stack_columns:
        if _is_inactive(value):
            css.append("color: #64748b")
        else:
            css.append("color: #86efac; font-weight: 600")
    return "; ".join(css)


def style_timeline_dataframe(df):
    """Colour the audit table for st.dataframe (colours only - no formatting).

    Only two things are painted:
      * the per-owner row tint, on every cell (consecutive characters differ);
      * the STACK counter columns, grey while a stack is 0/empty and green + bold
        while it has at least one stack. Boolean flags are checkboxes drawn by the
        grid itself, so they are left alone; every other cell keeps the theme colour.

    Formats, the pinned Action column and the header tooltips live in
    AUDIT_COLUMN_CONFIG (results.py passes them to st.dataframe); MISSING cells are
    rendered by the dataframe's own placeholder (placeholder="-"), so every empty cell
    looks the same.
    """
    owners = list(dict.fromkeys(df["Owner"].tolist())) if "Owner" in df.columns else []
    owner_bg = {owner: OWNER_BG[i % len(OWNER_BG)] for i, owner in enumerate(owners)}
    columns = list(df.columns)
    stack_columns = set(_stack_columns(df))

    def _paint(row):
        background = owner_bg.get(row.get("Owner"), "#111827")
        return [_cell_css(column, row.get(column), background, stack_columns)
                for column in columns]

    return df.style.apply(_paint, axis=1)
