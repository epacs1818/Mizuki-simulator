import streamlit as st
import pandas as pd
import buffs
import datetime
from timeline import RotationTimeline
from abilities import (
    aether_en1,
    aether_cq,
    faruzan_q,
    odette_ee,
    mizuki_sacfrag_fill,
    mizuki_burstless_pull_out,
)

# Ensure TEAM_BUFFS exists on buffs module for stats_calc
if not hasattr(buffs, "TEAM_BUFFS"):
    buffs.TEAM_BUFFS = getattr(buffs, "STATIC_BUFFS", {})

from artifacts import ARTIFACTS_BONUSES
from weapons import WEAPON_STATS
from stats_calc import build_initial_stats, compute_card_stats

# Callback functions for seamless programmatic tab switching
def go_to_enemy_tab():
    st.session_state["main_tabs"] = "Enemy Configuration"

def go_to_rotation_tab():
    st.session_state["main_tabs"] = "Rotation Setup"

# Safe aliases for weapons and artifact sets to prevent KeyError
WEAPON_STATS.setdefault("Select Weapon", {"base_atk": 0.0})

# Set page layout to wide
st.set_page_config(page_title="Yumemizuki Mizuki's Rotation Damage Calculator", layout="wide")

# Set page layout to wide
st.set_page_config(page_title="Genshin Rotation Simulator", layout="wide")

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
CHARACTERS = ["Select Character", "Mizuki", "Aether", "Odette", "Faruzan", "Sucrose", "Diona"]

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
    "Faruzan": [
        ("Favonius Warbow", [1, 2, 3, 4, 5]),
        ("Sacrificial Bow", [1, 2, 3, 4, 5]),
        ("Breezeborne Refrain", [1, 2, 3, 4, 5]),
        ("Elegy for the End", [1, 2, 3, 4, 5]),
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
    ],
}

CHARACTER_CONSTELLATIONS = {
    "Select Character": ["C0"],
    "Faruzan": ["C6"],  # Only C6 available
    "Diona": ["C6"],    # Only C6 available
    "Mizuki": [f"C{j}" for j in range(7)],
    "Aether": [f"C{j}" for j in range(7)],
    "Odette": [f"C{j}" for j in range(7)],
    "Sucrose": [f"C{j}" for j in range(7)],
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
    ],
    "Aether": [
        "Select Set",
        "2p/2p ATK",
        "A Day Carved From Rising Winds",
        "Heart Of The Furnace",
        "Tenacity Of The Millelith",
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

# Mapping from UI display names to standardized backend keys
STAT_KEY_MAP = {
    "Flat HP": "hp_flat",
    "Flat ATK": "atk_flat",
    "Flat DEF": "def_flat",
    "HP%": "hp_percent",
    "ATK%": "atk_percent",
    "DEF%": "def_percent",
    "EM": "em",
    "ER%": "er",
    "Crit Rate%": "crit_rate",
    "Crit Damage%": "crit_dmg",
    "Healing Bonus%": "healing_bonus",
    "Physical Bonus%": "physical_bonus",
    "Pyro Bonus%": "pyro_bonus",
    "Hydro Bonus%": "hydro_bonus",
    "Geo Bonus%": "geo_bonus",
    "Anemo Bonus%": "anemo_bonus",
    "Electro Bonus%": "electro_bonus",
    "Dendro Bonus%": "dendro_bonus",
    "Cryo Bonus%": "cryo_bonus",
}

AVAILABLE_FIELD_SEQUENCES = {
    "AetherEN1   (Aether – Skill N1)":           "aether_en1",
    "AetherCQ    (Aether – Charged + Burst)":    "aether_cq",
    "FaruzanQ    (Faruzan – Burst Swap)":        "faruzan_q",
    "OdetteEE    (Odette – Skill Double E)":     "odette_ee",
    "SacFragFill (Mizuki – Skill Fill)":         "mizuki_sacfrag_fill",
    "BurstlessPO (Mizuki – Burstless Pull-Out)": "mizuki_burstless_pull_out",
}

FIELD_SEQUENCE_OBJ_MAP = {
    "aether_en1": aether_en1,
    "aether_cq": aether_cq,
    "faruzan_q": faruzan_q,
    "odette_ee": odette_ee,
    "mizuki_sacfrag_fill": mizuki_sacfrag_fill,
    "mizuki_burstless_pull_out": mizuki_burstless_pull_out,
}

def build_timeline_dataframe(timeline_events):
    if not timeline_events:
        return pd.DataFrame()
    
    rows = []
    for event in timeline_events:
        nc = event.get("non_crit")
        cd = event.get("crit_damage")
        avg = event.get("average_damage")
        eff = event.get("effective_average_damage")
        
        row = {
            "Time (s)": round(event["global_time"], 3),
            "Active": event.get("active_character", "None"),
            "Owner": event.get("character", ""),
            "Action": event.get("action", ""),
            "Cryo Aura": event.get("cryo_aura", "-"),
            "Reaction": event.get("reaction", "-"),
            "Non-Crit DMG": f"{nc:.1f}" if nc is not None else "-",
            "Crit DMG": f"{cd:.1f}" if cd is not None else "-",
            "Average DMG": f"{avg:.1f}" if avg is not None else "-",
            "Effective Avg DMG": f"{eff:.1f}" if eff is not None else "-",
            "Fanz Buff": event.get("faruzan_buff_state", "OFF"),
            "Fanz Debuff": event.get("faruzan_debuff_state", "OFF"),
            "Aether C2": event.get("aether_c2_state", "OFF"),
            "Marvelous Stacks": event.get("marvelous_stacks", 0),
            "HotF": event.get("hotf_state", "OFF"),
            "Dream": event.get("dreamdrifter_state", "OFF"),
            "VV": event.get("vv_state", "OFF"),
            "Instructor": event.get("instructor_state", "OFF"),
            "Cryo Res": event.get("cryo_resonance_state", "OFF"),
        }
        rows.append(row)
    
    return pd.DataFrame(rows)

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

team_data = {}

# ---------------------------------------------------------
# TAB NAVIGATION STRUCTURE
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Team & Gear Setup", 
    "Enemy Configuration", 
    "Rotation Setup", 
    "History & Simulation Results"
], key="main_tabs", on_change="rerun")

# =========================================================
# TAB 1: TEAM & GEAR SETUP
# =========================================================

from pathlib import Path

with tab1:
    st.subheader("1. Team, Characters and Weapon Configuration")

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


            st.markdown("")
            pieces_data = {}
            f_col, fe_col, s_col, g_col, c_col = st.columns(5)
            
            def render_piece_inputs(piece_name, main_stat_widget):
                st.markdown(f"**{piece_name}**")
                
                if main_stat_widget == "locked_hp":
                    st.text_input("Main Stat", value="Flat HP", key=f"main_{piece_name}_{slot_num}", disabled=True)
                    main_stat = "Flat HP"
                elif main_stat_widget == "locked_atk":
                    st.text_input("Main Stat", value="Flat ATK", key=f"main_{piece_name}_{slot_num}", disabled=True)
                    main_stat = "Flat ATK"
                else:
                    main_stat = st.selectbox("Main Stat", main_stat_widget, key=f"main_{piece_name}_{slot_num}")

                rarity = st.radio(
                    "Artifact Rarity",
                    options=["5★", "4★"],
                    horizontal=True,
                    key=f"rarity_{piece_name}_{slot_num}"
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
                            label_visibility="collapsed"
                        )
                    is_pct = "%" in sub_type
                    with sub_col2:
                        sub_val = st.text_input(
                            f"Val {sub_idx}", 
                            placeholder="%" if is_pct else "Value", 
                            key=f"sub_val_{piece_name}_{slot_num}_{sub_idx}",
                            label_visibility="collapsed"
                        )
                    with sub_col3:
                        if is_pct:
                            st.markdown("**%**")

                    if sub_type != "None":
                        substats_list.append({"stat": sub_type, "value": sub_val})
                        
                return {
                    "main_stat": main_stat,
                    "rarity": rarity,
                    "substats": substats_list
                }

            with f_col:
                pieces_data["Flower"] = render_piece_inputs("Flower", "locked_hp")
            with fe_col:
                pieces_data["Feather"] = render_piece_inputs("Feather", "locked_atk")
            with s_col:
                pieces_data["Sands"] = render_piece_inputs("Sands", SANDS_MAINS)
            with g_col:
                pieces_data["Goblet"] = render_piece_inputs("Goblet", GOBLET_MAINS)
            with c_col:
                pieces_data["Circlet"] = render_piece_inputs("Circlet", CIRCLET_MAINS)
                
            team_data[f"Slot {slot_num}"]["artifacts"] = {
                "Set": selected_set,
                "Pieces": pieces_data
            }

    
    STANDARD_MAIN_STATS = {
        "hp_flat": 4780, "atk_flat": 311, "hp_percent": 0.466, "atk_percent": 0.466,
        "def_percent": 0.583, "em": 186.5, "er": 0.518, "crit_rate": 0.311,
        "crit_dmg": 0.622, "healing_bonus": 0.359, "physical_bonus": 0.583,
        "pyro_bonus": 0.466, "hydro_bonus": 0.466, "geo_bonus": 0.466,
        "anemo_bonus": 0.466, "electro_bonus": 0.466, "dendro_bonus": 0.466, "cryo_bonus": 0.466
    }

    STANDARD_4STAR_MAIN_STATS = {
        "hp_flat": 3571, "atk_flat": 232, "hp_percent": 0.348, "atk_percent": 0.348,
        "def_percent": 0.435, "em": 139.3, "er": 0.387, "crit_rate": 0.232,
        "crit_dmg": 0.464, "healing_bonus": 0.268, "physical_bonus": 0.435,
        "pyro_bonus": 0.348, "hydro_bonus": 0.348, "geo_bonus": 0.348,
        "anemo_bonus": 0.348, "electro_bonus": 0.348, "dendro_bonus": 0.348, "cryo_bonus": 0.348
    }

    def parse_val(val_str):
        if not val_str:
            return 0.0
        val_str = str(val_str).strip()
        try:
            if "%" in val_str:
                return float(val_str.replace("%", ""))
            return float(val_str)
        except ValueError:
            return 0.0

    # Build a signature of current team inputs to detect changes
    current_signature = []
    for s_num in range(1, 5):
        sd = team_data[f"Slot {s_num}"]
        current_signature.append((
            sd["character"], sd["level"], sd["constellation"],
            sd["weapon"], sd["refinement"], sd["talents"],
            sd.get("artifacts", {}).get("Set")
        ))
    
    # If settings changed since last party creation, reset confirmation
    if "last_team_signature" in st.session_state and st.session_state["last_team_signature"] != current_signature:
        st.session_state["party_created"] = False


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
                my_party = {}
                for idx, (slot, data) in enumerate(team_data.items()):
                    char_name = data["character"]
                    if char_name == "Select Character":
                        continue # Skip empty slots if any slip through
                        
                    slot_num = idx + 1
                    const_val = int(data["constellation"].replace("C", "")) if data["constellation"] else 0
                    weapon = data["weapon"]
                    artifact_set = data.get("artifacts", {}).get("Set", "Select Set")
                    pieces = data.get("artifacts", {}).get("Pieces", {})
                    
                    main_stats_total = {}
                    subs_total = {}
                    
                    for piece_name, piece_info in pieces.items():
                        main_stat = piece_info.get("main_stat", "")
                        substats = piece_info.get("substats", [])
                        piece_rarity = piece_info.get("rarity", "5★")

                        active_stats_dict = STANDARD_4STAR_MAIN_STATS if piece_rarity == "4★" else STANDARD_MAIN_STATS
                        
                        if main_stat:
                            stat_key = STAT_KEY_MAP.get(main_stat)
                            if stat_key and stat_key in active_stats_dict:
                                main_stats_total[stat_key] = main_stats_total.get(stat_key, 0.0) + active_stats_dict[stat_key]
                        
                        for sub in substats:
                            sub_type = sub.get("stat")
                            numeric_val = parse_val(sub.get("value"))
                            if sub_type and sub_type != "None":
                                sub_key = STAT_KEY_MAP.get(sub_type, sub_type.lower().replace(" ", "_"))
                                if "%" in sub_type or sub_key in ["hp_percent", "atk_percent", "def_percent", "crit_rate", "crit_dmg", "er"]:
                                    numeric_val = numeric_val / 100.0
                                subs_total[sub_key] = subs_total.get(sub_key, 0.0) + numeric_val

                    initial_stats = build_initial_stats(char_name, weapon, artifact_set, main_stats_total, subs_total)
                    card_stats = compute_card_stats(initial_stats)

                    my_party[char_name] = {
                        "constellation": const_val,
                        "level": data.get("level", 90),
                        "weapon": weapon,
                        "refinement": data["refinement"],
                        "talents": data["talents"] if data["talents"] else "10/13/13",
                        "talent_levels": parsed_talents[slot_num],
                        "artifact_set": artifact_set if artifact_set != "Select Set" else "None",
                        "initial_stats": initial_stats,  
                        "card_stats": card_stats         
                    }

                st.session_state["party_created"] = True
                st.session_state["last_team_signature"] = current_signature
                st.session_state["my_party"] = my_party
                st.success("Party successfully created!")

    # Show stats cards inside tab1 if party is created
    if st.session_state.get("party_created") and "my_party" in st.session_state:
        my_party = st.session_state["my_party"]
        st.markdown("---")
        st.header("Character Cards (Off-Field Stats)")
        card_cols = st.columns(4)
        
        for idx, (char_name, data) in enumerate(my_party.items()):
            with card_cols[idx]:
                with st.container(height=1000, border=True):

                    char_img_path = Path(f"assets/characters/{char_name.lower()}.webp")
                    if char_img_path.exists():
                        st.image(str(char_img_path), use_container_width=True)                    

                    st.subheader(f"{char_name} (C{data['constellation']})")
                    st.caption(f"**Level:** {data.get('level', 90)}")
                    st.caption(f"**Weapon:** {data['weapon']} R{data['refinement']} (Lv 90)")
                    st.caption(f"**Talents:** {data['talents']}")
                    st.caption(f"**Artifacts:** {data['artifact_set']}")
                    st.markdown("---")
                    
                    for stat_name, stat_val in data["card_stats"].items():
                        st.text(f"{stat_name:<13}: {stat_val}")

        st.markdown("<br>", unsafe_allow_html=True)
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

        # Right column holds either the live target overview card or a placeholder prompt
        with col_card:
            st.markdown("### Target Overview")
            if is_confirmed:
                with st.container(border=True):

                    enemy_img_path = Path("assets/enemy/target.webp")
                    if enemy_img_path.exists():
                        st.image(str(enemy_img_path), use_container_width=True)

                    st.subheader(f"Level {enemy_lv} Target")
                    st.markdown("---")
                    st.caption("**Current Resistances:**")
                    
                    for elem in elements:
                        res_pct = enemy_res_inputs.get(f"{elem}_res", 0.1) * 100
                        st.text(f"{elem.capitalize():<10}: {res_pct:.1f}%")
                    
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
        st.header("Field Sequence Setup")
        st.write("Add field sequences in order to define your rotation timeline.")

        FIELD_SEQUENCE_CHAR_MAP = {
            "aether_en1":               "Aether",
            "aether_cq":                "Aether",
            "faruzan_q":                "Faruzan",
            "odette_ee":                "Odette",
            "mizuki_sacfrag_fill":      "Mizuki",
            "mizuki_burstless_pull_out":"Mizuki",
        }

        if "field_sequence" not in st.session_state:
            st.session_state["field_sequence"] = []

        add_col, btn_col = st.columns([3, 1])
        with add_col:
            selected_label = st.selectbox(
                "Pick a field sequence to add",
                list(AVAILABLE_FIELD_SEQUENCES.keys()),
                key="field_sequence_picker"
            )
        with btn_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Add Field Sequence", key="add_field_sequence_btn", use_container_width=True):
                st.session_state["field_sequence"].append(AVAILABLE_FIELD_SEQUENCES[selected_label])
                st.rerun()

        if st.session_state["field_sequence"]:
            st.markdown("##### Current Rotation Sequence")
            for idx, field_sequence_key in enumerate(st.session_state["field_sequence"]):
                row_c1, row_c2, row_c3 = st.columns([0.5, 3, 1])
                with row_c1:
                    st.markdown(f"**{idx + 1}.**")
                with row_c2:
                    label = next((lbl for lbl, k in AVAILABLE_FIELD_SEQUENCES.items() if k == field_sequence_key), field_sequence_key)
                    owner = FIELD_SEQUENCE_CHAR_MAP.get(field_sequence_key, "?")
                    st.markdown(f"`{label}` — *{owner}*")
                with row_c3:
                    if st.button("🗑️ Remove", key=f"rm_field_sequence_{idx}"):
                        st.session_state["field_sequence"].pop(idx)
                        st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            action_col1, action_col2 = st.columns([1, 3])
            with action_col1:
                if st.button("🧹 Clear All Field Sequences", key="clear_field_sequences_btn", use_container_width=True):
                    st.session_state["field_sequence"] = []
                    st.rerun()
            with action_col2:
                if st.button("Run Simulation & Save", type="primary", key="save_config_btn", use_container_width=True):
                    party = st.session_state.get("my_party", {})
                    enemy = st.session_state.get("enemy_stats", {"enemy_lv": 100, "cryo_res": 0.1, "anemo_res": 0.1})
                    field_sequence_seq = st.session_state.get("field_sequence", [])

                    timeline = RotationTimeline(party=party, enemy_stats=enemy)
                    current_time = 0.0
                    for field_sequence_key in field_sequence_seq:
                        field_sequence_obj = FIELD_SEQUENCE_OBJ_MAP.get(field_sequence_key)
                        if field_sequence_obj:
                            current_time = timeline.add_field_sequence(field_sequence_obj, swap_in_time=current_time)
                    timeline.evaluate_timeline()

                    char_summary = ", ".join(
                        f"{name} Lv{data.get('level',90)} C{data['constellation']} {data['weapon']} T{data['talents']}"
                        for name, data in party.items()
                    )
                    field_sequence_summary = " → ".join(field_sequence_seq) if field_sequence_seq else "no field sequences"
                    enemy_summary = f"Lv{enemy.get('enemy_lv','?')} | Cryo {int(enemy.get('cryo_res',0.1)*100)}% | Anemo {int(enemy.get('anemo_res',0.1)*100)}%"
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

                    entry = {
                        "timestamp": timestamp,
                        "chars": char_summary,
                        "field_sequences": field_sequence_summary,
                        "enemy": enemy_summary,
                        "timeline_events": timeline.global_events,
                    }

                    if "history" not in st.session_state:
                        st.session_state["history"] = []
                    st.session_state["history"].append(entry)
                    st.success("Simulation complete! Check the **History & Simulation Results** tab.")
        else:
            st.info("No field sequences added yet. Pick a field sequence above and click ➕ Add Field Sequence.")


# =========================================================
# TAB 4: HISTORY & SIMULATION RESULTS
# =========================================================
with tab4:
    st.header("Configuration History & Timeline Simulation")
    
    if not st.session_state.get("history"):
        st.info("No saved configurations yet. Set up your party, enemy, and field_sequence rotation in the previous tabs and click **Run Simulation & Save**.")
    else:
        st.write("Each entry below reflects a saved configuration complete with its detailed Streamlit rotation timeline table.")

        history = st.session_state["history"]
        for i, entry in enumerate(reversed(history)):
            real_idx = len(history) - 1 - i
            with st.expander(f"[{entry['timestamp']}] Entry #{real_idx + 1}", expanded=(i == 0)):
                st.markdown(f"**Characters:** {entry['chars']}")
                st.markdown(f"**Field Sequences:** `{entry['field_sequences']}`")
                st.markdown(f"**Enemy:** {entry['enemy']}")
                
                if "timeline_events" in entry and entry["timeline_events"]:
                    st.markdown("##### ⏱Rotation Timeline Table")
                    df_timeline = build_timeline_dataframe(entry["timeline_events"])
                    st.dataframe(df_timeline, use_container_width=True)

                if st.button("Delete entry", key=f"del_hist_{real_idx}"):
                    st.session_state["history"].pop(real_idx)
                    st.rerun()