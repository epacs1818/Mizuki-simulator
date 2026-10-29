import streamlit as st
import buffs
# Ensure TEAM_BUFFS exists on buffs module for stats_calc
if not hasattr(buffs, "TEAM_BUFFS"):
    buffs.TEAM_BUFFS = getattr(buffs, "STATIC_BUFFS", {})

from artifacts import ARTIFACTS_BONUSES
from weapons import WEAPON_STATS
from stats_calc import build_initial_stats, compute_card_stats

# Safe aliases for weapons and artifact sets to prevent KeyError
WEAPON_STATS.setdefault("Fav Bow", WEAPON_STATS.get("Favonius Warbow", {"base_atk": 454.0, "er": 0.613}))
WEAPON_STATS.setdefault("Favonius Warbow", {"base_atk": 454.0, "er": 0.613})
WEAPON_STATS.setdefault("Tttds", {"base_atk": 401.0, "hp_percent": 0.352})
WEAPON_STATS.setdefault("Select Weapon", {"base_atk": 0.0})
WEAPON_STATS.setdefault("Favonius Sword", {"base_atk": 454.0, "er": 0.613})
WEAPON_STATS.setdefault("The Catch", {"base_atk": 510.0, "er": 0.459})

# Set page layout to wide
st.set_page_config(page_title="Genshin Rotation Simulator", layout="wide")

st.title("⚔️ Genshin Impact Rotation Simulator")
st.subheader("Advanced Team & Artifact Setup")

st.markdown("---")

# Constants & Options defined by your specifications
CHARACTERS = ["Select Character", "Mizuki", "Aether", "Odette", "Faruzan", "Sucrose", "Diona"]

CHARACTER_WEAPONS = {
    "Faruzan": [("Favonius Warbow", [5])],  # R5 Locked
    "Mizuki": [("The Widsith", [1, 2, 3, 4, 5]), ("Sacrificial Fragments", [5])],
    "Sucrose": [("Tttds", [1, 2, 3, 4, 5]), ("Sacrificial Fragments", [5])],
    "Odette": [("New Bough", [1, 2, 3, 4, 5]), ("Silver Light", [5])],
    "Aether": [("Exaiphanes Blade", [1, 2, 3, 4, 5])],
}

CHARACTER_ARTIFACT_SETS = {
    "Mizuki": ["Select Set", "2p/2p EM", "Gilded Dreams", "Scarlet Proof"],
    "Odette": ["Select Set", "Heart Of The Furnace", "2p/2p ATK"],
    "Aether": ["Select Set", "2p/2p ATK", "Tenacity Of The Millelith", "A Day Carved From Rising Winds"],
}
DEFAULT_ARTIFACT_SETS = ["Select Set", "Emblem of Severed Fate", "Gladiator's Finale", "Noblesse Oblige", "Viridescent Venerer", "Deepwood Memories"]

# Register all sets with fallbacks in ARTIFACTS_BONUSES so ARTIFACTS_BONUSES[set] never throws KeyError
for set_key in list(DEFAULT_ARTIFACT_SETS) + ["Select Set", "None", "", "2p/2p Em", "Heart of the furnace", "2p/2p Atk"]:
    ARTIFACTS_BONUSES.setdefault(set_key, ARTIFACTS_BONUSES.get(set_key.title(), {}))

# Main Stat Options per piece type
SANDS_MAINS = ["ER%", "ATK%", "HP%", "DEF%", "EM"]
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

team_data = {}

# ---------------------------------------------------------
# SECTION 1: Team, Constellation & Weapon Configuration
# ---------------------------------------------------------
st.header("1. Team, Weapon & Refinement Configuration")

cols = st.columns(4)

for i, col in enumerate(cols):
    slot_num = i + 1
    with col:
        st.markdown(f"### Slot {slot_num}")
        
        char = st.selectbox("Character", CHARACTERS, key=f"char_{slot_num}")
        
        # Constellation Rules
        if char in ["Diona", "Faruzan"]:
            st.info(f"🔒 {char} is locked to C6")
            const = "C6"
        elif char in ["Mizuki", "Aether", "Odette", "Sucrose"]:
            const_options = [f"C{j}" for j in range(7)]
            const = st.selectbox("Constellation", const_options, key=f"const_{slot_num}")
        else:
            const = "C0"
            st.selectbox("Constellation", ["C0"], key=f"const_dummy_{slot_num}", disabled=True)
            
        # Weapon & Refinement Rules
        if char in CHARACTER_WEAPONS:
            available_weapons_list = CHARACTER_WEAPONS[char]
            weapon_names = [w[0] for w in available_weapons_list]
            
            chosen_weapon = st.selectbox("Weapon", weapon_names, key=f"weapon_{slot_num}")
            valid_refines = [w[1] for w in available_weapons_list if w[0] == chosen_weapon][0]
            
            if len(valid_refines) == 1:
                st.caption(f"Refinement locked to R{valid_refines[0]}")
                refinement_val = valid_refines[0]
            else:
                refine_choice = st.selectbox("Refinement", [f"R{r}" for r in valid_refines], key=f"ref_{slot_num}")
                refinement_val = int(refine_choice.replace("R", ""))
        else:
            chosen_weapon = st.selectbox("Weapon", ["Select Weapon", "Favonius Sword", "The Catch"], key=f"weapon_fallback_{slot_num}")
            refine_choice = st.selectbox("Refinement", ["R1", "R2", "R3", "R4", "R5"], key=f"ref_fallback_{slot_num}")
            refinement_val = int(refine_choice.replace("R", ""))
            
        team_data[f"Slot {slot_num}"] = {
            "character": char,
            "constellation": const,
            "weapon": chosen_weapon,
            "refinement": refinement_val,
            "artifacts": {}
        }

st.markdown("---")
st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# SECTION 2: Artifact Sets & Structured Pieces Entry
# ---------------------------------------------------------
st.header("2. Artifact Sets & Piece Stats")
st.write("Configure the set bonus, locked/selectable main stats, and up to 4 substats with values for each piece.")

for slot_num in range(1, 5):
    char_name = team_data[f"Slot {slot_num}"]["character"]
    label_name = char_name if char_name != "Select Character" else f"Character {slot_num}"
    
    with st.expander(f"📦 Artifacts for {label_name} (Slot {slot_num})", expanded=False):
        
        # Major dropdown for Artifact Set
        if char_name in CHARACTER_ARTIFACT_SETS:
            set_options = CHARACTER_ARTIFACT_SETS[char_name]
        else:
            set_options = DEFAULT_ARTIFACT_SETS
            
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
                
            st.markdown("---")
            st.caption("Substats (Stat & Value)")
            
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

st.markdown("---")

# ---------------------------------------------------------
# SECTION 3: Summary & Output (Dictionary Format)
# ---------------------------------------------------------
# Standard 5-star max-level main stat values for Genshin Impact
STANDARD_MAIN_STATS = {
    "hp_flat": 4780,
    "atk_flat": 311,
    "hp_percent": 0.466,
    "atk_percent": 0.466,
    "def_percent": 0.583,
    "em": 187.5,
    "er": 0.518,
    "crit_rate": 0.311,
    "crit_dmg": 0.622,
    "healing_bonus": 0.359,
    "physical_bonus": 0.466,
    "pyro_bonus": 0.466,
    "hydro_bonus": 0.466,
    "geo_bonus": 0.466,
    "anemo_bonus": 0.466,
    "electro_bonus": 0.466,
    "dendro_bonus": 0.466,
    "cryo_bonus": 0.466
}

def parse_val(val_str):
    """Helper to convert user string inputs (e.g., '12.5%', '4000') into numbers."""
    if not val_str:
        return 0.0
    val_str = str(val_str).strip()
    try:
        if "%" in val_str:
            return float(val_str.replace("%", ""))
        return float(val_str)
    except ValueError:
        return 0.0

if st.button("Confirm", type="primary"):
    my_party = {}
    
    st.header("Character Card Comparison (Off-Field Stats)")
    card_cols = st.columns(4)
    
    for idx, (slot, data) in enumerate(team_data.items()):
        char_name = data["character"]
        if char_name == "Select Character":
            continue
            
        const_val = int(data["constellation"].replace("C", "")) if data["constellation"] else 0
        weapon = data["weapon"]
        artifact_set = data.get("artifacts", {}).get("Set", "None")
        pieces = data.get("artifacts", {}).get("Pieces", {})
        
        main_stats_total = {}
        subs_total = {}
        
        # Parse main stats and substats totals
        for piece_name, piece_info in pieces.items():
            main_stat = piece_info.get("main_stat", "")
            substats = piece_info.get("substats", [])
            
            if main_stat:
                stat_key = STAT_KEY_MAP.get(main_stat)
                if stat_key and stat_key in STANDARD_MAIN_STATS:
                    main_stats_total[stat_key] = main_stats_total.get(stat_key, 0.0) + STANDARD_MAIN_STATS[stat_key]
            
            for sub in substats:
                sub_type = sub.get("stat")
                numeric_val = parse_val(sub.get("value"))
                if sub_type and sub_type != "None":
                    sub_key = STAT_KEY_MAP.get(sub_type, sub_type.lower().replace(" ", "_"))
                    # If this substat is entered as a percentage, divide by 100 to store as decimal
                    if "%" in sub_type or sub_key in ["hp_percent", "atk_percent", "def_percent", "crit_rate", "crit_dmg", "er"]:
                        numeric_val = numeric_val / 100.0
                    subs_total[sub_key] = subs_total.get(sub_key, 0.0) + numeric_val

        # 1. Build the backend initial_stats dictionary (uncalculated pools)
        initial_stats = build_initial_stats(char_name, weapon, artifact_set, main_stats_total, subs_total)
        
        # 2. Derive the user-facing card display stats from initial_stats
        card_stats = compute_card_stats(initial_stats)

        # Store in party profile structure
        my_party[char_name] = {
            "constellation": const_val,
            "weapon": weapon,
            "refinement": data["refinement"],
            "artifact_set": artifact_set,
            "initial_stats": initial_stats,  
            "card_stats": card_stats         
        }

        # Render the Character Card UI
        with card_cols[idx]:
            with st.container(border=True):
                st.subheader(f"{char_name} ({data['constellation']})")
                st.caption(f"**Level:** 90")
                st.caption(f"**Weapon:** {weapon} R{data['refinement']} (Lv 90)")
                st.caption(f"**Artifacts:** {artifact_set}")
                st.markdown("---")
                
                for stat_name, stat_val in card_stats.items():
                    st.text(f"{stat_name:<13}: {stat_val}")

    st.markdown("---")
    st.subheader("Party Dictionary Output (Backend Ready)")
    st.code(f"my_party = {my_party}", language="python")
