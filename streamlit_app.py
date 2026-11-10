import streamlit as st
import pandas as pd
import buffs
import copy
import datetime
import hashlib
import plotly.express as px
from pathlib import Path
from timeline import RotationTimeline
from abilities import ABILITY_REGISTRY, abilities_for
from presets import field_sequences_for

# Ensure TEAM_BUFFS exists on buffs module for stats_calc
if not hasattr(buffs, "TEAM_BUFFS"):
    buffs.TEAM_BUFFS = getattr(buffs, "STATIC_BUFFS", {})

from artifacts import ARTIFACTS_BONUSES
from weapons import WEAPON_STATS
# Gear -> stat math now lives in build_io (shared by the UI and file loading).
from substats_standards import CARRIES, standard_piece_mains
import buff_registry
from build_io import (
    apply_build_document,
    assemble_party,
    build_party_from_document,
    collect_build_document,
    collect_slot,
    crit_model_label,
    document_lacks_gear,
    document_to_json,
    legacy_build_document,
    load_trial_into_editor,
    parse_document,
    party_rv_summary,
    suggested_file_name,
)

# Callback functions for seamless programmatic tab switching
def go_to_enemy_tab():
    st.session_state["main_tabs"] = "Enemy Configuration"

def go_to_rotation_tab():
    st.session_state["main_tabs"] = "Rotation Setup"

def go_to_results_tab():
    st.session_state["main_tabs"] = "Simulation Results"

# Safe aliases for weapons and artifact sets to prevent KeyError
WEAPON_STATS.setdefault("Select Weapon", {"base_atk": 0.0})

# Set page layout to wide
# Note: st.set_page_config may only be called once per app run.
st.set_page_config(page_title="Yumemizuki Mizuki's Rotation Damage Calculator", layout="wide")

import base64

# Helper to load and encode the local image permanently
def get_base64_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# Get the base64 string (change to "assets/wallpaper.png" or "webp" if your file format differs)
img_base64 = get_base64_image("assets/wallpaper.jpg")

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpeg;base64,{img_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    /* Dark overlay to contrast the wallpaper */
    .stApp::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(14, 17, 23, 0.4); 
        z-index: 0;
        pointer-events: none;
    }}
    
    /* Main application container */
    .main .block-container {{
        position: relative;
        z-index: 1;
        background-color: rgba(15, 23, 42, 0.88) !important;
        color: #ffffff !important;
        padding: 2.5rem 3rem !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 35px rgba(0, 0, 0, 0.5) !important;
        margin-top: 2rem !important;
        margin-bottom: 2rem !important;
    }}

    /* --- ADD TEXT SHADOW TO INTERFACE TEXT --- */
    .main .block-container h1, 
    .main .block-container h2, 
    .main .block-container h3, 
    .main .block-container h4, 
    .main .block-container h5, 
    .main .block-container h6, 
    .main .block-container p, 
    .main .block-container span, 
    .main .block-container label,
    .main .block-container .stMarkdown,
    .main .block-container .stAlert {{
        color: #ffffff !important;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.6) !important;
    }}

    /* --- TAB CLOUD / CURVED RECTANGLE STYLING --- */
    div[data-baseweb="tab-list"] {{
        background-color: rgba(30, 41, 59, 0.95) !important;
        padding: 10px 15px !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
        gap: 8px !important;
        margin-bottom: 20px !important;
    }}

    div[data-baseweb="tab"] {{
        border-radius: 10px !important;
        color: #cbd5e1 !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
        transition: all 0.3s ease !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5) !important;
    }}

    div[data-baseweb="tab"]:hover {{
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: #ffffff !important;
    }}

    button[data-baseweb="tab"][aria-selected="true"] {{
        background-color: #3b82f6 !important;
        color: #ffffff !important;
        border-radius: 10px !important;
    }}

    /* Tab Panel Content Box */
    div[data-baseweb="tab-panel"] {{
        background-color: rgba(30, 41, 59, 0.6) !important;
        padding: 20px 25px !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        margin-top: 10px !important;
        color: #ffffff !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Yumemizuki Mizuki's Rotation Damage Calculator")
st.markdown("---")

# Constants & Options defined by your specifications
CHARACTERS = ["Select Character", "Mizuki", "Aether", "Odette", "Anastasya", "Faruzan", "Sucrose", "Diona"]

LEVEL_OPTIONS = [60, 70, 80, 90, 95, 100]

CHARACTER_WEAPONS = {
    "Mizuki": [
        ("The Widsith (Average)", [1, 2, 3, 4, 5]),
        ("The Widsith (All EM)", [1, 2, 3, 4, 5]),
        ("Sacrificial Fragments", [4, 5]),
        ("Sacrificial Jade", [1, 2, 3, 4, 5]),
        ("Sunny Morning Sleep-In", [1, 2, 3, 4, 5]),
        ("Starcaller's Watch", [1, 2, 3, 4, 5]),
        ("A Thousand Floating Dreams", [1, 2, 3, 4, 5]),
        ("Wandering Evenstar", [1, 2, 3, 4, 5]),
        ("Thrilling Tales of Dragon Slayers", [1, 2, 3, 4, 5]),
        ("Starsealed Edict", [1, 2, 3, 4, 5]),
    ],
    "Aether": [
        ("New Bough", [1, 2, 3, 4, 5]),
        ("Silver Light", [1, 2, 3, 4, 5]),
        ("Exaiphanes Blade", [1, 2, 3, 4, 5]),
        ("Whitelake Frostfeather", [1, 2, 3, 4, 5]),
        ("Finale Of The Deep", [1, 2, 3, 4, 5]),
        ("Azurelight", [1, 2, 3, 4, 5]),
        ("Aquila Favonia", [1, 2, 3, 4, 5]),
    ],
    "Odette": [
        ("New Bough", [1, 2, 3, 4, 5]),
        ("Silver Light", [1, 2, 3, 4, 5]),
        ("Exaiphanes Blade", [1, 2, 3, 4, 5]),
        ("Whitelake Frostfeather", [1, 2, 3, 4, 5]),
        ("Finale Of The Deep", [1, 2, 3, 4, 5]),
        ("Azurelight", [1, 2, 3, 4, 5]),
        ("Aquila Favonia", [1, 2, 3, 4, 5]),
    ],
    "Anastasya": [
        ("Favonius Warbow", [1, 2, 3, 4, 5]),
        ("Sacrificial Bow", [1, 2, 3, 4, 5]),
        ("Breezeborne Refrain", [1, 2, 3, 4, 5]),
        ("Elegy for the End", [1, 2, 3, 4, 5]),
        ("Silverdawn", [1, 2, 3, 4, 5]),
    ],
    "Faruzan": [
        ("Favonius Warbow", [1, 2, 3, 4, 5]),
        ("Sacrificial Bow", [1, 2, 3, 4, 5]),
        ("Breezeborne Refrain", [1, 2, 3, 4, 5]),
        ("Elegy for the End", [1, 2, 3, 4, 5]),
        ("Silverdawn", [1, 2, 3, 4, 5]),
    ],
    "Sucrose": [
        ("The Widsith (Average)", [1, 2, 3, 4, 5]),
        ("The Widsith (All EM)", [1, 2, 3, 4, 5]),
        ("Sacrificial Fragments", [1, 2, 3, 4, 5]),
        ("Sacrificial Jade", [1, 2, 3, 4, 5]),
        ("Sunny Morning Sleep-In", [1, 2, 3, 4, 5]),
        ("Starcaller's Watch", [1, 2, 3, 4, 5]),
        ("A Thousand Floating Dreams", [1, 2, 3, 4, 5]),
        ("Wandering Evenstar", [1, 2, 3, 4, 5]),
        ("Thrilling Tales of Dragon Slayers", [1, 2, 3, 4, 5]),
        ("Starsealed Edict", [1, 2, 3, 4, 5]),
    ],
    "Diona": [
        ("Favonius Warbow", [1, 2, 3, 4, 5]),
        ("Sacrificial Bow", [1, 2, 3, 4, 5]),
        ("Breezeborne Refrain", [1, 2, 3, 4, 5]),
        ("Elegy for the End", [1, 2, 3, 4, 5]),
        ("Silverdawn", [1, 2, 3, 4, 5]),
    ],
}

CHARACTER_CONSTELLATIONS = {
    "Select Character": ["C0"],
    "Faruzan": ["C6"],  # Only C6 available
    "Diona": ["C6"],    # Only C6 available
    "Mizuki": ["C0", "C1", "C2", "C3", "C4", "C5", "C6"],
    "Aether": ["C4", "C5", "C6"],
    "Odette": ["C0"],
    "Anastasya": ["C0"],
    "Sucrose": ["C0", "C1", "C2", "C3", "C4", "C5", "C6"],
}

CHARACTER_ARTIFACT_SETS = {
    "Select Character": ["Select Set"],
    "Mizuki": [
        "Select Set",
        "2p/2p EM",
        "Gilded Dreams",
        "Heart Of The Furnace",
        "Instructor",
        "Scarlet Proof",
        "Viridescent Venerer",
    ],
    "Odette": [
        "Select Set",
        "2p/2p ATK",
        "A Day Carved From Rising Winds",
        "Heart Of The Furnace",
        "Tenacity Of The Millelith",
        "New Tsaritsa set",
    ],
    "Anastasya": [
        "Select Set",
        "Heart Of The Furnace",
        "2p/2p ATK",
        "New Tsaritsa set",
    ],
    "Aether": [
        "Select Set",
        "2p/2p ATK",
        "A Day Carved From Rising Winds",
        "Heart Of The Furnace",
        "Tenacity Of The Millelith",
        "New Tsaritsa set",
    ],
    "Faruzan": [
        "Select Set",
        "Instructor",
        "Noblesse Oblige",
        "Tenacity Of The Millelith",
        "Viridescent Venerer",
    ],
    "Sucrose": [
        "Select Set",
        "2p/2p EM",
        "Gilded Dreams",
        "Instructor",
        "Viridescent Venerer",
    ],
    "Diona": [
        "Select Set",
        "Noblesse Oblige",
        "Tenacity Of The Millelith",
    ],
}

# Strict fallback for unselected placeholders (let actual missing keys crash)
WEAPON_STATS.setdefault("Select Weapon", {"base_atk": 0.0})
ARTIFACTS_BONUSES.setdefault("Select Set", {})

# Main Stat Options per piece type
SANDS_MAINS = ["ATK%", "HP%", "DEF%", "EM", "ER%"]
GOBLET_MAINS = ["ATK%", "HP%", "DEF%", "EM", "Physical Bonus%", "Pyro Bonus%", "Hydro Bonus%", "Geo Bonus%", "Anemo Bonus%", "Electro Bonus%", "Dendro Bonus%", "Cryo Bonus%"]
CIRCLET_MAINS = ["ATK%", "HP%", "DEF%", "EM", "Crit Rate%", "Crit Damage%", "Healing Bonus%"]

# Substat Options (including DEF% and Flat DEF)
SUBSTAT_OPTIONS = ["None", "Flat ATK", "Flat HP", "Flat DEF", "ATK%", "HP%", "DEF%", "Crit Rate%", "Crit Damage%", "ER%", "EM"]

# Everything the import/export layer validates widget values against. Kept here so
# build_io never has to know about the UI's own tables.
BUILD_CATALOGUE = {
    "characters": CHARACTERS,
    "levels": LEVEL_OPTIONS,
    "weapons": CHARACTER_WEAPONS,
    "constellations": CHARACTER_CONSTELLATIONS,
    "artifact_sets": CHARACTER_ARTIFACT_SETS,
    "substat_options": SUBSTAT_OPTIONS,
    "mains": {"Sands": SANDS_MAINS, "Goblet": GOBLET_MAINS, "Circlet": CIRCLET_MAINS},
    "rarities": ["5★", "4★"],
    "standards": ["Manual", "100% RV (Crit Value)", "KQM Standards (40 rolls)"],
}

# --- Editor catalogues -------------------------------------------------------
# Everything the editors offer comes from the catalogues: field sequences from
# presets.py (FIELD_SEQUENCE_REGISTRY) and abilities from abilities.py
# (ABILITY_REGISTRY), so a new definition shows up automatically and never has to be
# listed twice. Availability is gated by the CURRENT PARTY: only sequences/abilities
# whose owner is actually in the team are offered.

def _party_characters() -> list:
    """Character names selected in the current party (order preserved)."""
    party = st.session_state.get("my_party") or {}
    return [name for name in party.keys()
            if name and name not in ("Select Character", "None")]


def _available_field_sequences() -> dict:
    """{label: FieldSequence} — abilities.py sequences for this party + custom ones."""
    options = {}
    for name, seq in field_sequences_for(_party_characters()).items():
        options[f"{name} ({seq.character})"] = seq
    for name, seq in (st.session_state.get("custom_field_sequences") or {}).items():
        options[f"{name} ({seq.character}) [custom]"] = seq
    return options


def _available_abilities(character: str) -> dict:
    """{ability name: Ability} owned by *character* (empty when not in the party)."""
    if character not in _party_characters():
        return {}
    return abilities_for(character)


def _select_trial_label(key: str, trial) -> str:
    """Trial dropdown label: preset trials show their team so duplicates stay clear."""
    if trial.required_party:
        return f"{trial.name}  [{' / '.join(trial.required_party)}]"
    return key


_BUFF_GROUP_TAG = {"Character": "", "Weapon": "[W] ", "Artifact": "[A] ", "Team": "[T] "}


def _buff_is_active(value):
    """True when a buff audit cell is not OFF / 0 / empty."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in ("", "OFF", "-")
    return value != 0


def build_timeline_dataframe(timeline_events, party=None):
    """Flat audit table ordered by block:
        time -> description (active/owner/action) -> reaction (app/aura/reaction)
        -> stats (HP/ATK/DEF/EM/CR/CD) -> multipliers -> output damage -> buffs.

    Buff columns come from buff_registry: only effects whose owner character,
    weapon, artifact set or resonance is present, AND that actually trigger
    somewhere in this run, are ever built into the table.
    """
    if not timeline_events:
        return pd.DataFrame()

    buff_entries = [
        entry for entry in buff_registry.visible_buffs(party or {})
        if any(_buff_is_active(ev.get(entry["key"])) for ev in timeline_events)
    ]

    rows = []
    for event in timeline_events:
        nc = event.get("non_crit")
        cd = event.get("crit_damage")
        avg = event.get("average_damage")
        eff = event.get("effective_average_damage")

        row = {}
        row["Time (s)"] = f"{event['global_time']:.3f}"
        row["Active"] = event.get("active_character", "None")
        row["Owner"] = event.get("character", "")
        row["Action"] = event.get("action", "")
        # Aura comes BEFORE the elemental application it reacts with: it is the state
        # the hit was resolved against, so it only changes on the following row.
        row["Aura"] = event.get("cryo_aura", "-")
        row["Elemental App"] = event.get("elem_app", "-")
        row["Reaction"] = event.get("reaction", "-")
        row["HP"] = f"{event['stat_hp']:.0f}" if event.get("stat_hp") is not None else "-"
        row["ATK"] = f"{event['stat_atk']:.0f}" if event.get("stat_atk") is not None else "-"
        row["DEF"] = f"{event['stat_def']:.0f}" if event.get("stat_def") is not None else "-"
        row["EM"] = f"{event['stat_em']:.0f}" if event.get("stat_em") is not None else "-"
        # Crit display depends on the build standard: a 100% RV / KQM build carries
        # crit as ONE Crit Value (CV = 2*CR + CD) and lets the engine re-split it, so
        # CR% / CD% are internal storage there. Those rows show the CV instead, which
        # is the number the damage formula actually uses.
        stat_cr = event.get("stat_cr")
        stat_cr_val = stat_cr if stat_cr is not None else 0.0
        stat_cd = event.get("stat_cd")
        stat_cd_val = stat_cd if stat_cd is not None else 0.0
        is_rv_hit = bool(event.get("rv_mode"))
        if stat_cr is None or stat_cd is None:
            row["CR%"] = "-"
            row["CD%"] = "-"
            row["CV"] = "-"
        else:
            row["CR%"] = "-" if is_rv_hit else f"{stat_cr_val * 100:.1f}"
            row["CD%"] = "-" if is_rv_hit else f"{stat_cd_val * 100:.1f}"
            row["CV"] = f"{(2.0 * stat_cr_val + stat_cd_val) * 100:.1f}"
        row["Base DMG"] = f"{event['base_damage']:.1f}" if event.get("base_damage") is not None else "-"
        row["Quills"] = f"{event['quills_total']:.1f}" if event.get("quills_total") is not None else "-"
        row["Bonus Mult"] = f"{event['bonus_mult']:.3f}" if event.get("bonus_mult") is not None else "-"
        row["Elev Mult"] = f"{event['elevation_mult']:.3f}" if event.get("elevation_mult") is not None else "-"
        row["Crit Mult"] = f"{event['crit_mult_avg']:.3f}" if event.get("crit_mult_avg") is not None else "-"
        row["DEF Mult"] = f"{event['def_mult']:.3f}" if event.get("def_mult") is not None else "-"
        row["Res Mult"] = f"{event['res_mult']:.3f}" if event.get("res_mult") is not None else "-"
        row["Average DMG"] = f"{avg:.1f}" if avg is not None else "-"
        row["Non-Crit DMG"] = f"{nc:.1f}" if nc is not None else "-"
        row["Crit DMG"] = f"{cd:.1f}" if cd is not None else "-"
        row["Effective Avg DMG"] = f"{eff:.1f}" if eff is not None else "-"
        for entry in buff_entries:
            label = _BUFF_GROUP_TAG.get(entry["group"], "") + entry["label"]
            row[label] = event.get(entry["key"], "OFF")

        rows.append(row)

    return pd.DataFrame(rows)

_AUDIT_BLOCKS = {
    "time": {"Time (s)"},
    "desc": {"Active", "Owner", "Action"},
    "reaction": {"Elemental App", "Aura", "Reaction"},
    "stats": {"HP", "ATK", "DEF", "EM", "CR%", "CD%", "CV"},
    "mult": {"Base DMG", "Quills", "Bonus Mult", "Elev Mult", "Crit Mult", "DEF Mult", "Res Mult"},
    "output": {"Average DMG", "Non-Crit DMG", "Crit DMG", "Effective Avg DMG"},
}

# One dark tint per party member: consecutive characters get different row colours.
_OWNER_BG = ("#0b3d2e", "#1e3a8a", "#4c1d95", "#7c2d12", "#0f766e", "#831843", "#3f6212", "#1e40af")

def _column_block(column):
    """Map an audit-table column to its block (buff = everything not core)."""
    for block, columns in _AUDIT_BLOCKS.items():
        if column in columns:
            return block
    return "buff"


def style_timeline_dataframe(df):
    """Colour-code the audit table for st.dataframe.

    Each party member gets its own dark row tint, so consecutive characters are
    visually separated. Buff cells are muted grey when OFF/0 and highlighted
    green when the effect is active.
    """
    owners = list(dict.fromkeys(df["Owner"].tolist())) if "Owner" in df.columns else []
    owner_bg = {owner: _OWNER_BG[i % len(_OWNER_BG)] for i, owner in enumerate(owners)}
    columns = list(df.columns)

    def _paint(row):
        background = owner_bg.get(row.get("Owner"), "#111827")
        cells = []
        for column in columns:
            css = [f"background-color: {background}", "color: #f8fafc"]
            if _column_block(column) == "buff":
                value = str(row.get(column, "")).strip()
                if value in ("OFF", "0", "", "-", "None", "nan"):
                    css.append("color: #64748b")
                else:
                    css.append("color: #86efac; font-weight: 600")
            cells.append("; ".join(css))
        return cells

    return df.style.apply(_paint, axis=1)


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


def render_character_cards(my_party: dict) -> None:
    """Compact off-field stat cards for the current party.

    Shown directly under the team section header so the party stays visible while the
    slots/artifacts below are edited. Deliberately small: a thumbnail portrait next to
    the identity block, then the gear stats as a two-column grid.
    """
    st.markdown("##### Character Cards (Off-Field Stats)")
    card_cols = st.columns(max(len(my_party), 1))
    for col, (char_name, data) in zip(card_cols, my_party.items()):
        with col:
            with st.container(border=True):
                img_col, id_col = st.columns([1, 1.7], vertical_alignment="center")
                with img_col:
                    img_path = Path(f"assets/characters/{char_name.lower()}.webp")
                    if img_path.exists():
                        st.image(str(img_path), width=74)
                with id_col:
                    st.markdown(f"**{char_name}** `C{data['constellation']}`")
                    st.caption(f"Lv {data.get('level', 90)} · {data.get('element') or '?'}")
                    st.caption(f"{data['weapon']} R{data['refinement']}")
                    st.caption(f"{data['artifact_set']}")
                    # Which crit model the party actually uses: an RV/KQM carry shows a
                    # single CV line below, a manual one shows CR / CD.
                    model_label = crit_model_label(data)
                    st.caption(f"Crit model: **{model_label}**" if model_label != "Manual"
                               else "Crit model: Manual (CR / CD)")

                rows = "".join(
                    f"<div style='opacity:0.85'>{label}</div>"
                    f"<div style='text-align:right;font-weight:600'>{value}</div>"
                    for label, value in (data.get("card_stats") or {}).items()
                )
                st.markdown(
                    "<div style='display:grid;grid-template-columns:auto auto;"
                    "column-gap:12px;font-size:0.82rem;line-height:1.45;margin-top:4px'>"
                    f"{rows}</div>",
                    unsafe_allow_html=True,
                )
    st.markdown("")


def render_build_io_panel() -> None:
    """Save / Load: download the current build, or restore one from a file.

    The importer is idempotent: the uploaded bytes are hashed and a file is applied
    only once. (It used to re-apply on every rerun, which silently reverted every
    edit made after loading.)
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
            "⬇ Export current build (.json)",
            data=document_to_json(current_doc),
            file_name=suggested_file_name(current_doc),
            mime="application/json",
            key="export_current_build",
            use_container_width=True,
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
    if document_lacks_gear(document):
        st.warning(
            "This file was saved by an older version and carries no artifact substats: "
            "the party is restored, but the piece inputs start empty."
        )
    for warning in warnings:
        st.warning(warning)


team_data = {}


# ---------------------------------------------------------
# TAB NAVIGATION STRUCTURE
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Team & Gear Setup", 
    "Enemy Configuration", 
    "Rotation Setup", 
    "Simulation Results"
], key="main_tabs", on_change=st.rerun)

# =========================================================
# TAB 1: TEAM & GEAR SETUP
# =========================================================

with tab1:
    render_build_io_panel()

    st.subheader("1. Team, Characters and Weapon Configuration")

    # Placeholder for the party cards: they are drawn HERE, right under the section
    # header, but they are FILLED at the bottom of the tab — after "Confirm party
    # configuration" has rebuilt the party — so they always show the current party.
    cards_slot = st.container()

    cols = st.columns(4)

    current_selections = {}
    for s in range(1, 5):
        val = st.session_state.get(f"char_{s}")
        if val and val != "Select Character":
            current_selections[s] = val

    for i, col in enumerate(cols):
        slot_num = i + 1
        with col:
            st.markdown(f"### Slot {slot_num}")
            
            chosen_in_other_slots = {char_val for s, char_val in current_selections.items() if s != slot_num}
            slot_char_options = [c for c in CHARACTERS if c == "Select Character" or c not in chosen_in_other_slots]
            
            curr_char = st.session_state.get(f"char_{slot_num}", "Select Character")
            if curr_char not in slot_char_options:
                curr_char = "Select Character"
                st.session_state[f"char_{slot_num}"] = "Select Character"
                
            char_idx = slot_char_options.index(curr_char)
            char = st.selectbox("Character", slot_char_options, index=char_idx, key=f"char_{slot_num}")

            # Level defaults to 90
            curr_lv = st.session_state.get(f"level_{slot_num}", 90)
            lv_idx = LEVEL_OPTIONS.index(curr_lv) if curr_lv in LEVEL_OPTIONS else LEVEL_OPTIONS.index(90)
            char_level = st.selectbox("Level", LEVEL_OPTIONS, index=lv_idx, key=f"level_{slot_num}")

            # Constellations (driven by CHARACTER_CONSTELLATIONS dictionary)
            const_options = CHARACTER_CONSTELLATIONS.get(char, ["C0"])
            if f"const_{slot_num}" in st.session_state and st.session_state[f"const_{slot_num}"] not in const_options:
                st.session_state[f"const_{slot_num}"] = const_options[0]
            const = st.selectbox("Constellation", const_options, key=f"const_{slot_num}")
                
            # Weapon & Refinement
            if char in CHARACTER_WEAPONS:
                available_weapons_list = CHARACTER_WEAPONS[char]
                weapon_names = [w[0] for w in available_weapons_list]
                
                if f"weapon_{slot_num}" in st.session_state and st.session_state[f"weapon_{slot_num}"] not in weapon_names:
                    st.session_state[f"weapon_{slot_num}"] = weapon_names[0]
                    
                chosen_weapon = st.selectbox("Weapon", weapon_names, key=f"weapon_{slot_num}")
                valid_refines = [w[1] for w in available_weapons_list if w[0] == chosen_weapon][0]
                
                refine_options = [f"R{r}" for r in valid_refines]
                if f"ref_{slot_num}" in st.session_state and st.session_state[f"ref_{slot_num}"] not in refine_options:
                    st.session_state[f"ref_{slot_num}"] = refine_options[0]
                refine_choice = st.selectbox("Refinement", refine_options, key=f"ref_{slot_num}")
                refinement_val = int(refine_choice.replace("R", ""))
            else:
                chosen_weapon = "Select Weapon"
                st.selectbox("Weapon", ["Select Weapon"], key=f"weapon_locked_{slot_num}", disabled=True)
                refinement_val = 1
                st.selectbox("Refinement", ["R1"], key=f"ref_locked_{slot_num}", disabled=True)

            talent_input = st.text_input(
                "Talent Levels",
                placeholder="10/13/13",
                key=f"talents_{slot_num}"
            )
                
            team_data[f"Slot {slot_num}"] = {
                "character": char,
                "level": char_level,
                "constellation": const,
                "weapon": chosen_weapon,
                "refinement": refinement_val,
                "talents": talent_input.strip() if talent_input else "",
                "artifacts": {}
            }
    
    st.markdown("---")

    # Artifacts Entry Section
    st.subheader("2. Artifact Sets & Piece Stats")
    st.write("Configure the set bonus, main stats, and substats for each piece.")

    for slot_num in range(1, 5):
        char_name = team_data[f"Slot {slot_num}"]["character"]
        label_name = char_name if char_name != "Select Character" else f"Character {slot_num}"
        
        with st.expander(f"Artifacts for {label_name} (Slot {slot_num})", expanded=False):
            set_options = CHARACTER_ARTIFACT_SETS.get(char_name, ["Select Set"])
                
            if f"art_set_{slot_num}" in st.session_state and st.session_state[f"art_set_{slot_num}"] not in set_options:
                st.session_state[f"art_set_{slot_num}"] = set_options[0]

            selected_set = st.selectbox(
                f"Main Artifact Set for {label_name}",
                set_options,
                key=f"art_set_{slot_num}"
            )

            # Substat standard selector (carries only). The options are mutually
            # exclusive by construction: RV and KQM both lock mains AND substats,
            # because neither matters once a standard is selected.
            standard_mode = "Manual"
            locked_mains = None
            if char_name in CARRIES:
                standard_mode = st.radio(
                    "Substat standard",
                    options=["Manual", "100% RV (Crit Value)", "KQM Standards (40 rolls)"],
                    index=0,
                    horizontal=True,
                    key=f"std_{slot_num}",
                    help="RV/KQM lock mains + substats and model crit as a single Crit Value (CV).",
                )
                if standard_mode != "Manual":
                    locked_mains = standard_piece_mains(char_name)
            subs_locked = standard_mode != "Manual"
            mains_locked = subs_locked

            st.markdown("")
            pieces_data = {}
            f_col, fe_col, s_col, g_col, c_col = st.columns(5)
            
            def render_piece_inputs(piece_name, main_stat_widget, disable_subs=False, locked_main=None):
                st.markdown(f"**{piece_name}**")
                
                if main_stat_widget == "locked_hp":
                    st.text_input("Main Stat", value="Flat HP", key=f"main_{piece_name}_{slot_num}", disabled=True)
                    main_stat = "Flat HP"
                elif main_stat_widget == "locked_atk":
                    st.text_input("Main Stat", value="Flat ATK", key=f"main_{piece_name}_{slot_num}", disabled=True)
                    main_stat = "Flat ATK"
                elif locked_main is not None:
                    st.text_input("Main Stat", value=locked_main, key=f"main_locked_{piece_name}_{slot_num}", disabled=True)
                    main_stat = locked_main
                else:
                    main_stat = st.selectbox("Main Stat", main_stat_widget, key=f"main_{piece_name}_{slot_num}")

                rarity = st.radio(
                    "Artifact Rarity",
                    options=["5★", "4★"],
                    index=0 if disable_subs else None,
                    horizontal=True,
                    key=(f"rarity_locked_{piece_name}_{slot_num}" if disable_subs else f"rarity_{piece_name}_{slot_num}"),
                    disabled=disable_subs,
                )
                    
                st.markdown("---")
                st.caption("Substats")
                
                substats_list = []
                for sub_idx in range(1, 5):
                    sub_col1, sub_col2, sub_col3 = st.columns([1.4, 1.1, 0.3], vertical_alignment="center")
                    with sub_col1:
                        sub_type = st.selectbox(
                            f"Sub {sub_idx}", 
                            SUBSTAT_OPTIONS, 
                            key=f"sub_type_{piece_name}_{slot_num}_{sub_idx}",
                            label_visibility="collapsed",
                            disabled=disable_subs
                        )
                    is_pct = "%" in sub_type
                    with sub_col2:
                        sub_val = st.text_input(
                            f"Val {sub_idx}", 
                            placeholder="%" if is_pct else "Value", 
                            key=f"sub_val_{piece_name}_{slot_num}_{sub_idx}",
                            label_visibility="collapsed",
                            disabled=disable_subs
                        )
                    with sub_col3:
                        if is_pct:
                            st.markdown("**%**")

                    if not disable_subs and sub_type != "None":
                        substats_list.append({"stat": sub_type, "value": sub_val})
                        
                return {
                    "main_stat": main_stat,
                    "rarity": rarity,
                    "substats": substats_list
                }

            with f_col:
                pieces_data["Flower"] = render_piece_inputs("Flower", "locked_hp", disable_subs=subs_locked, locked_main=(locked_mains["Flower"] if locked_mains else None))
            with fe_col:
                pieces_data["Feather"] = render_piece_inputs("Feather", "locked_atk", disable_subs=subs_locked, locked_main=(locked_mains["Feather"] if locked_mains else None))
            with s_col:
                pieces_data["Sands"] = render_piece_inputs("Sands", SANDS_MAINS, disable_subs=subs_locked, locked_main=(locked_mains["Sands"] if locked_mains else None))
            with g_col:
                pieces_data["Goblet"] = render_piece_inputs("Goblet", GOBLET_MAINS, disable_subs=subs_locked, locked_main=(locked_mains["Goblet"] if locked_mains else None))
            with c_col:
                pieces_data["Circlet"] = render_piece_inputs("Circlet", CIRCLET_MAINS, disable_subs=subs_locked, locked_main=(locked_mains["Circlet"] if locked_mains else None))
                
            team_data[f"Slot {slot_num}"]["artifacts"] = {
                "Set": selected_set,
                "Pieces": pieces_data
            }

    
    # Build a signature of current team inputs to detect changes. It must cover EVERY
    # input that feeds the party stats - gear (mains / rarity / substats) and the
    # substat standard included - otherwise editing them leaves the previously
    # confirmed party in place and the app silently keeps simulating the old build.
    current_signature = []
    for s_num in range(1, 5):
        sd = team_data[f"Slot {s_num}"]
        pieces = (sd.get("artifacts") or {}).get("Pieces") or {}
        gear_signature = tuple(
            (
                piece,
                (pieces.get(piece) or {}).get("main_stat"),
                (pieces.get(piece) or {}).get("rarity"),
                tuple(
                    ((sub or {}).get("stat"), str((sub or {}).get("value") or ""))
                    for sub in ((pieces.get(piece) or {}).get("substats") or [])
                ),
            )
            for piece in ("Flower", "Feather", "Sands", "Goblet", "Circlet")
        )
        current_signature.append((
            sd["character"], sd["level"], sd["constellation"],
            sd["weapon"], sd["refinement"], sd["talents"],
            sd.get("artifacts", {}).get("Set"),
            st.session_state.get(f"std_{s_num}", "Manual"),
            gear_signature,
        ))
    
    # If settings changed since last party creation, reset confirmation
    if "last_team_signature" in st.session_state and st.session_state["last_team_signature"] != current_signature:
        st.session_state["party_created"] = False
        st.warning(
            "Gear, substats or the substat standard changed since the party was "
            "confirmed — press **Confirm party configuration** to rebuild it. "
            "(Running a trial always uses the current inputs.)"
        )


    # Button renamed and validation relaxed to ONLY require characters
    if st.button("Confirm party configuration", type="primary"):
        has_empty_characters = False
        for slot_num in range(1, 5):
            s_data = team_data[f"Slot {slot_num}"]
            c = s_data["character"]
            
            # Only check if character selection is empty / default
            if not c or c == "Select Character":
                has_empty_characters = True
                break

        if has_empty_characters:
            st.session_state["party_created"] = False
            st.error("Please select characters for all slots.")
        else:
            # Talent validation still runs if talents are filled, 
            # or you can allow empty talents if desired. 
            # Keeping your existing talent validation structure:
            talent_errors = []
            parsed_talents = {}
            for slot_num in range(1, 5):
                s_data = team_data[f"Slot {slot_num}"]
                c = s_data["character"]
                t = s_data["talents"]
                
                # If talents are left empty, default them or validate
                if not t:
                    parsed_talents[slot_num] = [1, 1, 1] # Safe default if skipped
                else:
                    is_valid, err_msg, levels = validate_talents(t)
                    if not is_valid:
                        talent_errors.append(f"Slot {slot_num} ({c}): {err_msg}")
                    else:
                        parsed_talents[slot_num] = levels
                    
            if talent_errors:
                st.session_state["party_created"] = False
                for err in talent_errors:
                    st.error(f"Format error: {err}")
            else:
                slot_specs = []
                for slot_num in range(1, 5):
                    data = team_data[f"Slot {slot_num}"]
                    if data["character"] == "Select Character":
                        continue  # Skip empty slots if any slip through
                    slot_specs.append({
                        "character": data["character"],
                        "level": data.get("level", 90),
                        "constellation": data.get("constellation", "C0"),
                        "weapon": data["weapon"],
                        "refinement": data["refinement"],
                        "talents": data["talents"],
                        "talent_levels": parsed_talents[slot_num],
                        "artifact_set": data.get("artifacts", {}).get("Set", "Select Set"),
                        "standard_mode": (st.session_state.get(f"std_{slot_num}", "Manual")
                                          if data["character"] in CARRIES else "Manual"),
                        "pieces": data.get("artifacts", {}).get("Pieces", {}),
                    })

                # Gear -> stat pools lives in build_io, so a party restored from a file
                # is built by exactly the same code as one typed in here.
                st.session_state["my_party"] = assemble_party(slot_specs)
                st.session_state["party_created"] = True
                st.session_state["last_team_signature"] = current_signature
                st.success("Party successfully created!")

    # Party cards are written into the placeholder created under the section header,
    # so they appear at the top of the tab while still reflecting this run's party.
    if st.session_state.get("party_created") and st.session_state.get("my_party"):
        with cards_slot:
            render_character_cards(st.session_state["my_party"])

        st.markdown("---")
        col_proceed1, col_proceed2, col_proceed3 = st.columns([1, 2, 1])
        with col_proceed2:
            st.button(
                "Proceed to Enemy Configuration",
                type="primary",
                use_container_width=True,
                on_click=go_to_enemy_tab
            )


# =========================================================
# TAB 2: ENEMY CONFIGURATION
# =========================================================
with tab2:
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

        # Enemy summary card: deliberately compact — a small thumbnail next to the level,
        # then a two-column resistance grid. (A full-width image used to dominate here.)
        with col_card:
            st.markdown("### Target Overview")
            if is_confirmed:
                with st.container(border=True):
                    head_img, head_text = st.columns([1, 2], vertical_alignment="center")
                    with head_img:
                        enemy_img_path = Path("assets/enemy/target.webp")
                        if enemy_img_path.exists():
                            st.image(str(enemy_img_path), width=88)
                    with head_text:
                        st.markdown(f"**Level {enemy_lv} Target**")
                        st.caption("Damage target · off-field buffs apply")

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
            

# =========================================================
# TAB 3: ROTATION SETUP
# =========================================================
with tab3:
    if not st.session_state.get("party_created"):
        st.warning("⚠️ Please configure and create your party first in the **Team & Gear Setup** tab.")
    elif not st.session_state.get("enemy_confirmed"):
        st.warning("⚠️ Please confirm your enemy configuration first in the **Enemy Configuration** tab.")
    else:
        # Display lingering success notification from previous action
        if st.session_state.get("toast_msg"):
            st.success(st.session_state["toast_msg"])
            st.session_state["toast_msg"] = None

        # Values queued by "Load selected trial into editor". Widget keys can only be
        # written before the widget itself is created, so they are queued and applied
        # here, at the top of the tab.
        editor_prefill = st.session_state.pop("editor_prefill", None)
        if editor_prefill:
            st.session_state["adv_trial_name"] = editor_prefill.get("name", "")
            st.session_state["adv_trial_desc"] = editor_prefill.get("description", "")

        st.header("Trial Setup")
        
        from presets import STANDARD_TRIALS
        from models import FieldSequence, TimedAbilityCall, Rotation, Trial
        import copy

        # Initialize session state pools for custom advanced building if missing
        if "custom_field_sequences" not in st.session_state:
            st.session_state["custom_field_sequences"] = {}
        if "custom_rotations" not in st.session_state:
            st.session_state["custom_rotations"] = {}
        if "active_trial_pool" not in st.session_state:
            st.session_state["active_trial_pool"] = STANDARD_TRIALS.copy()
        if "temp_trial_rot_entries" not in st.session_state:
            st.session_state["temp_trial_rot_entries"] = []

        # Combine standard and custom field sequences for reference
        all_available_sequences = _available_field_sequences()

        # --- SECTION A: TRIAL RUNNER ---
        # A preset trial is only offered when the selected team matches exactly the
        # team it was authored for; user-made trials have no such requirement.
        party_characters = _party_characters()
        trial_pool = st.session_state["active_trial_pool"]
        trial_options = [k for k, t in trial_pool.items() if t.matches_party(party_characters)]
        trial_labels = {k: _select_trial_label(k, trial_pool[k]) for k in trial_options}

        # Drop a stale widget value when the selected trial is no longer offered.
        if st.session_state.get("trial_selector") not in trial_options:
            st.session_state.pop("trial_selector", None)

        selected_trial_key = None
        trial_obj = None
        if trial_options:
            selected_trial_key = st.selectbox(
                "Select Trial",
                trial_options,
                format_func=lambda k: trial_labels.get(k, k),
                key="trial_selector"
            )
            trial_obj = trial_pool[selected_trial_key]
        else:
            st.warning(
                "⚠️ No trial is available for this team. Preset trials are only offered "
                "for their exact team — build a custom trial below, or change the party "
                "in **Team & Gear Setup**."
            )

        if trial_obj is not None:
            with st.expander("Trial Breakdown", expanded=False):
                st.write(f"**Description:** {trial_obj.description}")
                st.write(f"**End Mode:** {trial_obj.end_mode.capitalize()} | **Duration:** {trial_obj.end_time}s")

                for r_idx, rotation in enumerate(trial_obj.rotations):
                    st.markdown(f"**Rotation #{r_idx + 1}: {rotation.name}** (Repeated {rotation.repetitions}x)")
                    for s_idx, seq in enumerate(rotation.sequences):
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ Step {s_idx + 1}: `{seq.name}` (*{seq.character}* — {seq.swap_out_time}s field time)")

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("Run Trial Simulation", type="primary", key="run_trial_btn", use_container_width=True):
                # ALWAYS simulate the current inputs. The confirmed party can be older
                # than the widgets (changing the substat standard or the gear does not
                # re-confirm itself), which used to make an RV/KQM build silently run on
                # the old manual stats. Rebuilding here is cheap - only the simulation is
                # expensive - and it makes a stale party impossible.
                rebuilt_party = assemble_party(
                    [collect_slot(st.session_state, slot_num) for slot_num in range(1, 5)]
                )
                party = rebuilt_party or st.session_state.get("my_party", {})
                st.session_state["my_party"] = party
                st.session_state["party_created"] = bool(party)
                enemy = st.session_state.get("enemy_stats", {"enemy_lv": 100, "cryo_res": 0.1, "anemo_res": 0.1})

                timeline = RotationTimeline(party=party, enemy_stats=enemy)
                timeline.add_trial(trial_obj)
                timeline.evaluate_timeline()

                trial_duration = trial_obj.end_time
                analytics = timeline.get_analytics_summary(trial_duration)

                char_summary = ", ".join(
                    f"{name} Lv{data.get('level', 90)} C{data['constellation']} {data['talents']} "
                    f"{data['weapon']} R{data.get('refinement', 1)}"
                    for name, data in party.items()
                )
                enemy_summary = f"Lv{enemy.get('enemy_lv','?')} | Cryo Res {int(enemy.get('cryo_res',0.1)*100)}% | Anemo Res {int(enemy.get('anemo_res',0.1)*100)}%"
                # Crit model used by THIS run (empty when every member is Manual), so an
                # old manual entry can never be confused with an RV/KQM one.
                standards = party_rv_summary(party)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

                entry = {
                    "timestamp": timestamp,
                    "sim_name": trial_labels.get(selected_trial_key, selected_trial_key),
                    "chars": char_summary,
                    "standards": standards,
                    "field_sequences": selected_trial_key,
                    "enemy": enemy_summary,
                    "timeline_events": timeline.global_events,
                    "snapshot_party": copy.deepcopy(party),
                    "snapshot_enemy": copy.deepcopy(enemy),
                    "snapshot_custom_fs": copy.deepcopy(st.session_state.get("custom_field_sequences", {})),
                    "snapshot_custom_rots": copy.deepcopy(st.session_state.get("custom_rotations", {})),
                    # Full, gear-complete build document for THIS run: the per-run
                    # export writes it, so the run can be re-imported and tweaked.
                    "snapshot_build": collect_build_document(
                        st.session_state,
                        trial_labels.get(selected_trial_key, selected_trial_key),
                    ),
                }

                if "history" not in st.session_state:
                    st.session_state["history"] = []
                st.session_state["history"].append(entry)
                st.session_state["trial_finished"] = True

        # Result of the last run. Rendered outside the button branch so the message and
        # the shortcut to the results stay available after the run.
        if st.session_state.get("trial_finished"):
            st.success("Trial simulation complete!")
            st.button(
                "View Simulation Results",
                type="primary",
                use_container_width=True,
                key="view_results_btn",
                on_click=go_to_results_tab,
                help="Go to the Simulation Results tab.",
            )


        st.markdown("<br><hr><br>", unsafe_allow_html=True)             

        # --- SECTION B: [ADVANCED] TRIAL EDITOR (Open Section) ---
        st.header("[Advanced] Trial Editor")
        st.write(
            "Abilities represent character actions and talents triggered via button presses. "
            "Field Sequences define a character's active window on the field through a specific sequence of abilities and swaps. "
            "A Rotation groups multiple Field Sequences together to form a looping combat sequence. "
            "A Trial defines the overall simulation framework, combining rotations from start to finish "
            "based on either a custom duration or the end of the final rotation."
        )
        
        st.markdown("<br>", unsafe_allow_html=True)

        # --- TRIAL ASSEMBLY (Placed at the very top of Advanced Editor) ---
        trial_col_left, trial_col_right = st.columns(2, gap="large")

        with trial_col_left:
            trial_name = st.text_input("Trial Name", placeholder="e.g. 'Mizuki Faruzan Sac Frag 120s'", key="adv_trial_name")
            trial_desc = st.text_input("Trial Description", placeholder="e.g. 'Using the pull out tech'", key="adv_trial_desc")            
            end_at_last_swap = st.checkbox("End at last rotation (auto-terminate at final swap out)", value=False, key="adv_end_swap_toggle")
            manual_end_time = st.number_input(
                "Trial Duration (s)", 
                min_value=1.0, 
                value=120.0, 
                step=1.0, 
                disabled=end_at_last_swap,
                key="adv_trial_duration"
            )

            # Makes any trial editable — including the shipped presets and trials
            # restored from a file: its rotations are copied into the editor pools.
            if trial_obj is not None:
                if st.button("⤵ Load selected trial into editor",
                             key="load_trial_into_editor_btn",
                             use_container_width=True,
                             help="Copies this trial's rotations into the editor so they "
                                  "can be tweaked and re-used in a new trial."):
                    load_trial_into_editor(trial_obj, st.session_state)
                    st.session_state["toast_msg"] = f"Trial '{trial_obj.name}' loaded into the editor."
                    st.rerun()

        with trial_col_right:
            if st.session_state["custom_rotations"]:
                chosen_rot_key = st.selectbox("Select Rotation", list(st.session_state["custom_rotations"].keys()), key="adv_trial_rot_select")
                rot_reps_input = st.number_input("Repetitions", min_value=1, max_value=20, value=1, key="adv_trial_rot_reps")
                
                if st.button("➕ Add Rotation to Trial", key="adv_add_rot_to_trial_btn", use_container_width=True):
                    st.session_state["temp_trial_rot_entries"].append({"rotation_name": chosen_rot_key, "repetitions": rot_reps_input})
                    st.session_state["toast_msg"] = f"Added {chosen_rot_key} ({rot_reps_input}x) to trial queue."
                    st.rerun()

                if st.session_state["temp_trial_rot_entries"]:
                    st.markdown("**Current Rotations:**")
                    for entry_idx, entry in enumerate(st.session_state["temp_trial_rot_entries"]):
                        rc1, rc2 = st.columns([4, 1], vertical_alignment="center")
                        with rc1:
                            st.text(f"{entry_idx + 1}. {entry['rotation_name']} ({entry['repetitions']}x)")
                        with rc2:
                            if st.button("✕", key=f"rm_trial_rot_{entry_idx}"):
                                st.session_state["temp_trial_rot_entries"].pop(entry_idx)
                                st.rerun()
            else:
                st.info("No custom rotations created yet.")

        # Option to delete custom trials if any exist
        if st.session_state["active_trial_pool"]:
            custom_trials_to_delete = [k for k in st.session_state["active_trial_pool"].keys() if k not in STANDARD_TRIALS]
            if custom_trials_to_delete:
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("Manage / Delete Custom Trials"):
                    del_trial_key = st.selectbox("Select Custom Trial to Delete", custom_trials_to_delete, key="del_trial_select")
                    if st.button("Delete Selected Trial", key="del_trial_btn"):
                        del st.session_state["active_trial_pool"][del_trial_key]
                        st.session_state["toast_msg"] = f"Custom trial '{del_trial_key}' deleted."
                        st.rerun()

        st.markdown("<br><hr><br>", unsafe_allow_html=True)

        # --- EXPANDER 1: CUSTOM ROTATION BUILDER ---
        with st.expander("Create Custom Rotation", expanded=False):
            rot_name = st.text_input("Rotation Name", placeholder="e.g. 'No Burst Starter'", key="adv_rot_name")
            
            chosen_seq_keys = st.multiselect(
                "Select Field Sequences in Order",
                options=list(all_available_sequences.keys()),
                key="adv_rot_seq_picker"
            )

            col_rot_save, col_rot_del = st.columns([4, 1], vertical_alignment="bottom")
            with col_rot_save:
                if st.button("Save Rotation", key="adv_save_rot_btn", type="secondary", use_container_width=True):
                    if rot_name and chosen_seq_keys:
                        seq_list = [all_available_sequences[k] for k in chosen_seq_keys]
                        new_rot = Rotation(name=rot_name, sequences=seq_list, repetitions=1)
                        st.session_state["custom_rotations"][rot_name] = new_rot
                        st.session_state["toast_msg"] = f"Rotation '{rot_name}' saved successfully!"
                        st.rerun()
                    else:
                        st.error("Please provide a rotation name and pick at least one field sequence.")
            
            # Management/Deletion for custom rotations
            if st.session_state["custom_rotations"]:
                with st.expander("Manage / Delete Custom Rotations"):
                    del_rot_key = st.selectbox("Select Custom Rotation to Delete", list(st.session_state["custom_rotations"].keys()), key="del_rot_select")
                    if st.button("✕ Delete Rotation", key="del_rot_btn"):
                        del st.session_state["custom_rotations"][del_rot_key]
                        st.session_state["toast_msg"] = f"Rotation '{del_rot_key}' deleted."
                        st.rerun()

        # --- EXPANDER 2: CUSTOM FIELD SEQUENCE BUILDER ---
        with st.expander("Create Custom Field Sequence", expanded=False):
            seq_col_left, seq_col_right = st.columns(2, gap="large")

            with seq_col_left:
                seq_name = st.text_input("Field Sequence Name", placeholder="e.g. 'Aether ECQ'", key="adv_seq_name")
                # Only characters that are in the party can have a field sequence.
                seq_char_options = _party_characters() or list(CHARACTERS[1:])
                if st.session_state.get("adv_seq_char") not in seq_char_options:
                    st.session_state.pop("adv_seq_char", None)
                seq_char = st.selectbox("Character", seq_char_options, key="adv_seq_char")
                seq_swap_time = st.number_input("Field Time / Swap-Out Time (s)", min_value=0.1, value=3.0, step=1.0, key="adv_swap_time")

            with seq_col_right:
                # Every ability defined in abilities.py for that character (no
                # hardcoded list here: new abilities appear automatically).
                avail_abilities = _available_abilities(seq_char)

                if "temp_seq_calls" not in st.session_state:
                    st.session_state["temp_seq_calls"] = []

                if avail_abilities:
                    if st.session_state.get("adv_abil_picker") not in avail_abilities:
                        st.session_state.pop("adv_abil_picker", None)
                    chosen_abil_key = st.selectbox("Select Ability to Add", list(avail_abilities.keys()), key="adv_abil_picker")
                    abil_start_time = st.number_input("Ability Insertion Time(s) (relative to Swap In)", min_value=0.0, value=0.0, step=0.1, key="adv_abil_time")
                    
                    if st.button("➕ Add Ability to Sequence", key="adv_add_abil_btn", use_container_width=True):
                        st.session_state["temp_seq_calls"].append((abil_start_time, avail_abilities[chosen_abil_key]))
                        st.session_state["toast_msg"] = f"Added {chosen_abil_key} at {abil_start_time}s"
                        st.rerun()

            # Queued abilities list arranged horizontally below the two divided columns
            st.markdown("<br>", unsafe_allow_html=True)
            if st.session_state["temp_seq_calls"]:
                st.markdown("**Queued Ability Calls:**")
                badges_html = "".join(
                    f"<span style='background-color: #3b82f6; color: white; padding: 6px 12px; border-radius: 12px; margin-right: 8px; font-size: 14px; display: inline-block; margin-bottom: 6px;'> [{st_time}s] {ab_obj.name}</span>"
                    for st_time, ab_obj in st.session_state["temp_seq_calls"]
                )
                st.markdown(f"<div style='display: flex; flex-wrap: wrap; gap: 4px; align-items: center;'>{badges_html}</div>", unsafe_allow_html=True)
                
                if st.button("Clear Abilities", key="clear_seq_calls_btn"):
                    st.session_state["temp_seq_calls"] = []
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Save Field Sequence", key="adv_save_seq_btn", type="secondary", use_container_width=True):
                if seq_name:
                    new_fs = FieldSequence(name=seq_name, character=seq_char, swap_out_time=seq_swap_time)
                    for st_time, ab_obj in st.session_state["temp_seq_calls"]:
                        new_fs.add_ability(st_time, ab_obj)
                    st.session_state["custom_field_sequences"][seq_name] = new_fs
                    st.session_state["temp_seq_calls"] = []
                    st.session_state["toast_msg"] = f"Field Sequence '{seq_name}' saved successfully!"
                    st.rerun()
                else:
                    st.error("Please provide a name for the field sequence.")

            # Management/Deletion for custom field sequences
            if st.session_state["custom_field_sequences"]:
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("Manage / Delete Custom Field Sequences"):
                    del_fs_key = st.selectbox("Select Custom Field Sequence to Delete", list(st.session_state["custom_field_sequences"].keys()), key="del_fs_select")
                    if st.button("✕ Delete Field Sequence", key="del_fs_btn"):
                        del st.session_state["custom_field_sequences"][del_fs_key]
                        st.session_state["toast_msg"] = f"Field Sequence '{del_fs_key}' deleted."
                        st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Create Trial", type="primary", key="adv_create_trial_btn", use_container_width=True):
            if trial_name and st.session_state["temp_trial_rot_entries"]:
                rot_list = []
                for entry in st.session_state["temp_trial_rot_entries"]:
                    base_rot = st.session_state["custom_rotations"][entry["rotation_name"]]
                    rot_copy = copy.deepcopy(base_rot)
                    rot_copy.repetitions = entry["repetitions"]
                    rot_list.append(rot_copy)

                mode = "last_swap" if end_at_last_swap else "time"
                new_trial = Trial(
                    name=trial_name,
                    rotations=rot_list,
                    end_mode=mode,
                    end_time=manual_end_time,
                    description=trial_desc
                )

                st.session_state["active_trial_pool"][trial_name] = new_trial
                st.session_state["temp_trial_rot_entries"] = []
                st.session_state["toast_msg"] = f"Trial '{trial_name}' successfully created and added to the selection dropdown!"
                st.rerun()
            else:
                st.error("Please enter a trial name and add at least one rotation.")


# =========================================================
# TAB 4: SIMULATION RESULTS & HISTORY
# =========================================================
with tab4:
    st.header("Simulation Results & History")
    
    if "history" not in st.session_state or not st.session_state["history"]:
        st.info("No simulation history available yet. Run a trial in Tab 3 to review results here.")
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
                
                # 1. RENAME CONTROLS
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

                st.markdown(f"**Characters:** {entry['chars']}")
                st.markdown(f"**Enemy Setup:** {entry['enemy']}")
                st.markdown(f"**Trial Executed:** `{entry['field_sequences']}`")
                # Which crit model this run used. Missing on old entries: they ran before
                # the column existed, i.e. every carry was Manual.
                st.markdown(f"**Crit Model:** {entry.get('standards') or 'Manual (CR / CD)'}")
                
                st.markdown("---")
                st.subheader("Performance Calculations & Analytics")

                # --- FALLBACK: Compute analytics on-the-fly for old history entries ---
                analytics = entry.get("analytics", {})
                if not analytics and "timeline_events" in entry and entry["timeline_events"]:
                    from timeline import RotationTimeline
                    temp_timeline = RotationTimeline(
                        party=entry.get("snapshot_party", {}), 
                        enemy_stats=entry.get("snapshot_enemy", {})
                    )
                    temp_timeline.global_events = entry["timeline_events"]
                    max_t = max((ev["global_time"] for ev in entry["timeline_events"]), default=30.0)
                    analytics = temp_timeline.get_analytics_summary(max_t)
                    entry["analytics"] = analytics # Cache it back into the entry

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
                            st.plotly_chart(fig_elem, use_container_width=True)
                            
                    with chart_col2:
                        hit_data = analytics.get("hit_type_breakdown", {})
                        if hit_data:
                            fig_hit = px.pie(
                                names=list(hit_data.keys()), 
                                values=list(hit_data.values()), 
                                title="Damage by Hit Type",
                                hole=0.3
                            )
                            st.plotly_chart(fig_hit, use_container_width=True)
                            
                    with chart_col3:
                        owner_data = analytics.get("owner_damage_share", {})
                        if owner_data:
                            fig_owner = px.pie(
                                names=list(owner_data.keys()), 
                                values=list(owner_data.values()), 
                                title="Damage Share by Character (Excl. Reactions)",
                                hole=0.3
                            )
                            st.plotly_chart(fig_owner, use_container_width=True)

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
                        st.plotly_chart(fig_dps, use_container_width=True)

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

                    # Runs recorded before schema 2.0 have no full document saved, so the
                    # best possible one is rebuilt from their snapshots.
                    run_doc = entry.get("snapshot_build") or legacy_build_document(entry)
                    run_doc["simulation_name"] = entry["sim_name"]
                    st.download_button(
                        label=f"Export JSON Config for '{entry['sim_name']}'",
                        data=document_to_json(run_doc),
                        file_name=suggested_file_name(run_doc),
                        mime="application/json",
                        key=f"export_hist_{real_idx}",
                        use_container_width=True
                    )
