# stats_calculator.py
from characters import CHARACTER_BASE_STATS
from weapons import WEAPON_STATS
from buffs import PERMANENT_BUFFS, TEAM_BUFFS

def build_initial_stats(char_name, weapon_full_name, main_stats_total, subs_total):
    """
    Combines Character Base + Weapon + Artifacts into a clean initial_stats 
    dictionary separating base, percentages, and flats for future buff injection.
    """
    # 1. Base Stats (Level 90)
    base_char = CHARACTER_BASE_STATS.get(char_name, {
        "base_hp": 10000.0, "base_atk": 200.0, "base_def": 600.0,
        "atk_percent": 0.0, "hp_percent": 0.0, "def_percent": 0.0,
        "atk_flat": 0.0, "hp_flat": 0.0, "def_flat": 0.0,
        "em": 0.0, "crit_rate": 0.05, "crit_dmg": 0.50, "er": 1.0, "Bonus Damage": 0.0
    })
    
    # 2. Weapon Stats Extraction
    weapon_key = weapon_full_name.split(" (")[0] if " (" in weapon_full_name else weapon_full_name
    base_weapon = WEAPON_STATS.get(weapon_key, {"base_atk": 454.0, "secondary_stat": None, "secondary_value": 0.0})
    
    # 3. Build Base Attributes
    base_hp = base_char["base_hp"]
    base_atk = base_char["base_atk"] + base_weapon["base_atk"] 
    base_def = base_char["base_def"]
    
    # 4. Build Percentage Pools
    hp_percent = base_char.get("hp_percent", 0.0) + (main_stats_total.get("hp%", 0.0) / 100.0) + (subs_total.get("hp%", 0.0) / 100.0)
    
    atk_percent = base_char.get("atk_percent", 0.0) + (main_stats_total.get("atk%", 0.0) / 100.0) + (subs_total.get("atk%", 0.0) / 100.0)
    if base_weapon.get("secondary_stat") == "atk_percent":
        atk_percent += base_weapon["secondary_value"]
        
    def_percent = base_char.get("def_percent", 0.0) + (main_stats_total.get("def%", 0.0) / 100.0) + (subs_total.get("def%", 0.0) / 100.0)
    
    # 5. Build Flat Pools
    hp_flat = base_char.get("hp_flat", 0.0) + main_stats_total.get("flat_hp", 0.0) + subs_total.get("flat_hp", 0.0) + main_stats_total.get("hp", 0.0) + subs_total.get("hp", 0.0)
    atk_flat = base_char.get("atk_flat", 0.0) + main_stats_total.get("flat_atk", 0.0) + subs_total.get("flat_atk", 0.0) + main_stats_total.get("atk", 0.0) + subs_total.get("atk", 0.0)
    def_flat = base_char.get("def_flat", 0.0) + main_stats_total.get("flat_def", 0.0) + subs_total.get("flat_def", 0.0)
    
    # 6. Secondary Stats (EM, Crit, ER, Bonus Dmg)
    em = base_char.get("em", 0.0) + main_stats_total.get("em", 0.0) + subs_total.get("em", 0.0)
    if base_weapon.get("secondary_stat") == "em":
        em += base_weapon["secondary_value"]
        
    crit_rate = base_char.get("crit_rate", 0.05) + (main_stats_total.get("crit_rate%", 0.0) / 100.0) + (subs_total.get("crit_rate%", 0.0) / 100.0)
    if base_weapon.get("secondary_stat") == "crit_rate":
        crit_rate += base_weapon["secondary_value"]
        
    crit_dmg = base_char.get("crit_dmg", 0.50) + (main_stats_total.get("crit_damage%", 0.0) / 100.0) + (subs_total.get("crit_damage%", 0.0) / 100.0)
    if base_weapon.get("secondary_stat") == "crit_dmg":
        crit_dmg += base_weapon["secondary_value"]
        
    er = base_char.get("er", 1.0) + (main_stats_total.get("er%", 0.0) / 100.0) + (subs_total.get("er%", 0.0) / 100.0)
    if base_weapon.get("secondary_stat") == "er%":
        er += base_weapon["secondary_value"]
        
    bonus_damage = base_char.get("Bonus Damage", 0.0) + (main_stats_total.get("elemental_bonus%", 0.0) / 100.0)

    initial_stats = {
        "base_hp": base_hp, "base_atk": base_atk, "base_def": base_def,
        "hp_percent": hp_percent, "hp_flat": hp_flat,
        "atk_percent": atk_percent, "atk_flat": atk_flat,
        "def_percent": def_percent, "def_flat": def_flat,
        "em": em, "crit_rate": crit_rate, "crit_dmg": crit_dmg,
        "er": er, "bonus_damage": bonus_damage
    }

    return initial_stats


def compute_card_stats(initial_stats):
    """
    Resolves initial_stats into formatted final values just for the user-facing card display.
    """
    card_hp = (initial_stats["base_hp"] * (1.0 + initial_stats["hp_percent"])) + initial_stats["hp_flat"]
    card_atk = (initial_stats["base_atk"] * (1.0 + initial_stats["atk_percent"])) + initial_stats["atk_flat"]
    card_def = (initial_stats["base_def"] * (1.0 + initial_stats["def_percent"])) + initial_stats["def_flat"]
    
    card_stats_calculated = {
        "HP": round(card_hp, 1),
        "ATK": round(card_atk, 1),
        "DEF": round(card_def, 1),
        "EM": round(initial_stats["em"], 1),
        "CR": f"{round(initial_stats['crit_rate'] * 100, 1)}%",
        "CD": f"{round(initial_stats['crit_dmg'] * 100, 1)}%",
        "ER": f"{round(initial_stats['er'] * 100, 1)}%",
        "Bonus Damage": f"{round(initial_stats['bonus_damage'] * 100, 1)}%"
    }

    return card_stats_calculated


def apply_permanent_buffs(initial_stats, char_name):
    """
    Applies permanent character passives or quest buffs to the backend initial_stats working copy.
    """
    char_permanent_buffs = PERMANENT_BUFFS.get(char_name, {})
    for buff_name, stat_dict in char_permanent_buffs.items():
        for stat_key, value in stat_dict.items():
            initial_stats[stat_key] = initial_stats.get(stat_key, 0.0) + value
    return initial_stats


def get_snapshot_stats(initial_stats, event_flags):
    """
    Takes initial_stats and a dictionary of active event states,
    returns a deep-copied final_stats dictionary with active team buffs applied.
    """
    final_stats = initial_stats.copy()
    
    # Check Instructor Buff
    if event_flags.get("instructor_state") == "ON":
        instructor_buffs = TEAM_BUFFS.get("Instructor", {})
        for stat, val in instructor_buffs.items():
            final_stats[stat] = final_stats.get(stat, 0.0) + val
            
    # Check Cryo Resonance
    if event_flags.get("cryo_resonance_state") == "ON":
        resonance_buffs = TEAM_BUFFS.get("Cryo Resonance", {})
        for stat, val in resonance_buffs.items():
            final_stats[stat] = final_stats.get(stat, 0.0) + val
            
    # Check Heart of the Furnace (HotF)
    if event_flags.get("hotf_state") == "ON":
        hotf_buffs = TEAM_BUFFS.get("Heart of the Furnace", {})
        for stat, val in hotf_buffs.items():
            final_stats[stat] = final_stats.get(stat, 0.0) + val

    return final_stats


def compute_final_stats(snapshot_stats):
    """
    Computes final resolved values (HP, ATK, DEF, EM, CR, CD, ER, Bonus Damage) 
    from a snapshot stats dictionary, returning raw unrounded/decimal floats 
    ready for damage calculations.
    """
    final_hp = (snapshot_stats["base_hp"] * (1.0 + snapshot_stats["hp_percent"])) + snapshot_stats["hp_flat"]
    final_atk = (snapshot_stats["base_atk"] * (1.0 + snapshot_stats["atk_percent"])) + snapshot_stats["atk_flat"]
    final_def = (snapshot_stats["base_def"] * (1.0 + snapshot_stats["def_percent"])) + snapshot_stats["def_flat"]
    
    final_stats_resolved = {
        "HP": final_hp,
        "ATK": final_atk,
        "DEF": final_def,
        "EM": snapshot_stats["em"],
        "CR": snapshot_stats["crit_rate"],       # Kept as raw decimal (e.g., 0.65 for 65%)
        "CD": snapshot_stats["crit_dmg"],        # Kept as raw decimal (e.g., 1.20 for 120%)
        "ER": snapshot_stats["er"],              # Kept as raw decimal (e.g., 1.45 for 145%)
        "Bonus Damage": snapshot_stats["bonus_damage"] # Kept as raw decimal
    }

    return final_stats_resolved

def compute_snapshot_card_stats(snapshot_stats):
    """
    Resolves snapshot_stats into formatted card strings (matching compute_card_stats) 
    so you can display real-time buff-aware stats on the UI if desired.
    """
    card_hp = (snapshot_stats["base_hp"] * (1.0 + snapshot_stats["hp_percent"])) + snapshot_stats["hp_flat"]
    card_atk = (snapshot_stats["base_atk"] * (1.0 + snapshot_stats["atk_percent"])) + snapshot_stats["atk_flat"]
    card_def = (snapshot_stats["base_def"] * (1.0 + snapshot_stats["def_percent"])) + snapshot_stats["def_flat"]
    
    snapshot_card_formatted = {
        "HP": round(card_hp, 1),
        "ATK": round(card_atk, 1),
        "DEF": round(card_def, 1),
        "EM": round(snapshot_stats["em"], 1),
        "CR": f"{round(snapshot_stats['crit_rate'] * 100, 1)}%",
        "CD": f"{round(snapshot_stats['crit_dmg'] * 100, 1)}%",
        "ER": f"{round(snapshot_stats['er'] * 100, 1)}%",
        "Bonus Damage": f"{round(snapshot_stats['bonus_damage'] * 100, 1)}%"
    }

    return snapshot_card_formatted