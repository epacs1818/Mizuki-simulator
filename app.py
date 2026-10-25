import streamlit as st

# Set page layout to wide
st.set_page_config(page_title="Genshin Rotation Simulator", layout="wide")

st.title("⚔️ Genshin Impact Rotation Simulator")
st.subheader("Advanced Team & Artifact Setup")

st.markdown("---")

# Constants & Options defined by your specifications
CHARACTERS = ["Select Character", "Mizuki", "Aether", "Odette", "Faruzan", "Sucrose", "Diona"]

CHARACTER_WEAPONS = {
    "Faruzan": [("Fav Bow", [5])],  # R5 Locked
    "Mizuki": [("The Widsith", [1, 2, 3, 4, 5]), ("Sacrificial Fragments", [5])],
    "Sucrose": [("Tttds", [1, 2, 3, 4, 5]), ("Sacrificial Fragments", [5])],
    "Odette": [("New Bough", [1, 2, 3, 4, 5]), ("Silver Light", [5])],
    "Aether": [("Exaiphanes Blade", [1, 2, 3, 4, 5])],
}

CHARACTER_ARTIFACT_SETS = {
    "Mizuki": ["Select Set", "2p/2p Em", "Gilded Dreams", "Scarlet Proof"],
    "Odette": ["Select Set", "Heart of the furnace", "2p/2p Atk"],
}
DEFAULT_ARTIFACT_SETS = ["Select Set", "Emblem of Severed Fate", "Gladiator's Finale", "Noblesse Oblige", "Viridescent Venerer", "Deepwood Memories"]

# Main Stat Options per piece type
SANDS_MAINS = ["ER%", "ATK%", "HP%", "DEF%", "EM"]
GOBLET_MAINS = ["ATK%", "HP%", "DEF%", "EM", "Elemental Bonus%"]
CIRCLET_MAINS = ["ATK%", "HP%", "DEF%", "EM", "Crit Rate%", "Crit Damage%", "Healing Bonus%"]

# Substat Options
SUBSTAT_OPTIONS = ["None", "Flat ATK", "Flat HP", "ATK%", "HP%", "Crit Rate%", "Crit Damage%", "ER%", "EM"]

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
                st.caption(f"🔒 Refinement locked to R{valid_refines[0]}")
                refinement = f"R{valid_refines[0]}"
            else:
                refine_choice = st.selectbox("Refinement", [f"R{r}" for r in valid_refines], key=f"ref_{slot_num}")
                refinement = refine_choice
        else:
            chosen_weapon = st.selectbox("Weapon", ["Select Weapon", "Favonius Sword", "The Catch"], key=f"weapon_fallback_{slot_num}")
            refinement = st.selectbox("Refinement", ["R1", "R2", "R3", "R4", "R5"], key=f"ref_fallback_{slot_num}")
            
        team_data[f"Slot {slot_num}"] = {
            "character": char,
            "constellation": const,
            "weapon": f"{chosen_weapon} ({refinement})",
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
                sub_col1, sub_col2 = st.columns([1.2, 1])
                with sub_col1:
                    sub_type = st.selectbox(
                        f"Sub {sub_idx}", 
                        SUBSTAT_OPTIONS, 
                        key=f"sub_type_{piece_name}_{slot_num}_{sub_idx}",
                        label_visibility="collapsed"
                    )
                with sub_col2:
                    sub_val = st.text_input(
                        f"Val {sub_idx}", 
                        placeholder="Value", 
                        key=f"sub_val_{piece_name}_{slot_num}_{sub_idx}",
                        label_visibility="collapsed"
                    )
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
    "flat hp": 4780,
    "flat atk": 311,
    "hp%": 46.6,
    "atk%": 46.6,
    "def%": 58.3,
    "em": 187.5,
    "er%": 51.8,
    "elemental bonus%": 46.6,
    "crit rate%": 31.1,
    "crit damage%": 62.2,
    "healing bonus%": 35.9
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
    
    for slot, data in team_data.items():
        char_name = data["character"]
        if char_name == "Select Character":
            continue
            
        const_val = int(data["constellation"].replace("C", "")) if data["constellation"] else 0
        artifacts = data.get("artifacts", {})
        pieces = artifacts.get("Pieces", {})
        
        main_stats_total = {}
        subs_total = {}
        character_pieces_data = {}
        
        # Process each artifact piece
        for piece_name, piece_info in pieces.items():
            p_key = piece_name.lower()
            main_stat = piece_info.get("main_stat", "")
            substats = piece_info.get("substats", [])
            
            # Store individual piece main stat
            character_pieces_data[f"{p_key}_main"] = {main_stat: STANDARD_MAIN_STATS.get(main_stat.lower(), 0)}
            
            # Aggregate Main Stats using standard values
            if main_stat:
                stat_key = main_stat.lower().replace(" ", "_")
                stat_value = STANDARD_MAIN_STATS.get(stat_key, 0)
                main_stats_total[stat_key] = main_stats_total.get(stat_key, 0.0) + stat_value
            
            # Process Substats for this piece
            for idx, sub in enumerate(substats, start=1):
                sub_type = sub.get("stat")
                sub_val_raw = sub.get("value")
                numeric_val = parse_val(sub_val_raw)
                
                # Store individual substat
                character_pieces_data[f"{p_key}_sub{idx}"] = {sub_type: sub_val_raw}
                
                # Aggregate Substats Total
                if sub_type and sub_type != "None":
                    sub_key = sub_type.lower().replace(" ", "_")
                    subs_total[sub_key] = subs_total.get(sub_key, 0.0) + numeric_val

        # Compile everything into the final character profile matching your requested structure
        my_party[char_name] = {
            "constellation": const_val,
            "weapon": data["weapon"],
            "artifact_set": artifacts.get("Set", "None"),
            "pieces_breakdown": character_pieces_data,
            f"{char_name.lower()}_mainstats_total": main_stats_total,
            f"{char_name.lower()}_subs_total": subs_total
        }
        
    st.header("📊 Party Dictionary Output with Stats")
    st.write("Here is the structured dictionary representation of your party, main stats, and subtotal calculations:")
    st.code(f"my_party = {my_party}", language="python")
