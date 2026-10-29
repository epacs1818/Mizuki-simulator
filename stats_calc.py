# stats_calculator.py
from characters import CHARACTER_BASE_STATS
from weapons import WEAPON_STATS
from artifacts import ARTIFACTS_BONUSES
from buffs import CONDITIONAL_CONSTANT_BUFFS, CONDITIONAL_NON_CONSTANT_BUFFS, PERMANENT_BUFFS, STACK_BUFFS

def build_initial_stats(char_name, weapon_full_name, artifact_set_name, main_stats_total, subs_total):
    """
    Combines Character Base + Weapon + Artifacts into a clean initial_stats 
    dictionary separating base, percentages, and flats for future buff injection.
    """
    # 1. Base Stats (Level 90)
    char_base = CHARACTER_BASE_STATS[char_name]
    
    # 2. Weapon Stats Extraction
    weapon_key = weapon_full_name.split(" (")[0] if " (" in weapon_full_name else weapon_full_name
    weapon_base = WEAPON_STATS[weapon_key]

    artifact_bonus = ARTIFACTS_BONUSES[artifact_set_name]

    base_atk = char_base["base_atk"] + weapon_base["base_atk"]
    base_hp = char_base["base_hp"]
    base_def = char_base["base_def"]
    
    # 4. Build Percentage Pools
    hp_percent = char_base.get("hp_percent", 0.0) + weapon_base.get("hp_percent", 0.0) + artifact_bonus.get("hp_percent", 0.0) + main_stats_total.get("hp_percent", 0.0) + subs_total.get("hp_percent", 0.0)
    atk_percent = char_base.get("atk_percent", 0.0) + weapon_base.get("atk_percent", 0.0) + artifact_bonus.get("atk_percent", 0.0) + main_stats_total.get("atk_percent", 0.0) + subs_total.get("atk_percent", 0.0)
    def_percent = char_base.get("def_percent", 0.0) + weapon_base.get("def_percent", 0.0) + artifact_bonus.get("def_percent", 0.0) + main_stats_total.get("def_percent", 0.0) + subs_total.get("def_percent", 0.0)
    
    # 5. Build Flat Pools
    hp_flat =  weapon_base.get("hp_flat", 0.0) + main_stats_total.get("hp_flat", 0.0) + subs_total.get("hp_flat", 0.0)
    atk_flat = weapon_base.get("atk_flat", 0.0) + main_stats_total.get("atk_flat", 0.0) + subs_total.get("atk_flat", 0.0)
    def_flat = weapon_base.get("def_flat", 0.0) + subs_total.get("def_flat", 0.0)
    
    # 6. Secondary Stats (EM, Crit, ER, Bonus Dmg)
    em = char_base.get("em", 0.0) + weapon_base.get("em", 0.0) + artifact_bonus.get("em", 0.0) + main_stats_total.get("em", 0.0) + subs_total.get("em", 0.0)
    crit_rate = char_base.get("crit_rate") + weapon_base.get("crit_rate", 0.0) + main_stats_total.get("crit_rate", 0.0) + subs_total.get("crit_rate", 0.0)
    crit_dmg = char_base.get("crit_dmg") + weapon_base.get("crit_dmg", 0.0) + main_stats_total.get("crit_dmg", 0.0) + subs_total.get("crit_dmg", 0.0)
    er = char_base.get("er") + weapon_base.get("er", 0.0) + main_stats_total.get("er", 0.0) + subs_total.get("er", 0.0)
        
    physical_bonus =char_base.get("physical_bonus", 0.0) + main_stats_total.get("physical_bonus", 0.0)
    pyro_bonus = char_base.get("pyro_bonus", 0.0) + main_stats_total.get("pyro_bonus", 0.0)
    cryo_bonus = char_base.get("cryo_bonus", 0.0) + main_stats_total.get("cryo_bonus", 0.0)
    geo_bonus = char_base.get("geo_bonus", 0.0) + main_stats_total.get("geo_bonus", 0.0)
    electro_bonus = char_base.get("electro_bonus", 0.0) + main_stats_total.get("electro_bonus", 0.0)
    dendro_bonus = char_base.get("dendro_bonus", 0.0) + main_stats_total.get("dendro_bonus", 0.0)
    hydro_bonus = char_base.get("hydro_bonus", 0.0) + main_stats_total.get("hydro_bonus", 0.0)
    anemo_bonus = char_base.get("anemo_bonus", 0.0) + main_stats_total.get("anemo_bonus", 0.0)


    initial_stats = {
        "base_hp": base_hp, "base_atk": base_atk, "base_def": base_def,
        "hp_percent": hp_percent, "hp_flat": hp_flat,
        "atk_percent": atk_percent, "atk_flat": atk_flat,
        "def_percent": def_percent, "def_flat": def_flat,
        "em": em, "crit_rate": crit_rate, "crit_dmg": crit_dmg,
        "er": er,
        "physical_bonus": physical_bonus, "pyro_bonus": pyro_bonus, "cryo_bonus": cryo_bonus, "geo_bonus": geo_bonus, "electro_bonus": electro_bonus, "dendro_bonus": dendro_bonus, "hydro_bonus": hydro_bonus, "anemo_bonus": anemo_bonus
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
    }

    elements = ["physical", "pyro", "cryo", "geo", "electro", "dendro", "hydro", "anemo"]
    for elem in elements:
        key = f"{elem}_bonus"
        val = initial_stats.get(key, 0.0)
        if val > 0.0:
            display_name = f"{elem.capitalize()} DMG"
            card_stats_calculated[display_name] = f"{round(val * 100, 1)}%"

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

def get_weapon_stat(weapon_base, stat_key, refinement=1):
    val = weapon_base.get(stat_key)
    if isinstance(val, list):
        # Refinement is 1-indexed (1-5), list is 0-indexed (0-4)
        return val[refinement - 1]
    return val if val is not None else 0.0

def resolve_active_buffs(initial_stats, event_flags, party=None, refinement=1):
    """
    Takes initial stats and timeline flags, computes and applies 
    all active static, stack, and dynamic buffs.
    """
    applied_buffs = {}
    party = party or {}
    
    # 1. Process  Constant Buffs (Booleans from Timeline)
    if event_flags.get("instructor_state") == "ON":
        for stat, val in CONDITIONAL_CONSTANT_BUFFS["Instructor"].items():
            applied_buffs[stat] = applied_buffs.get(stat, 0.0) + val

    if event_flags.get("cryo_resonance_state") == "ON":
        for stat, val in CONDITIONAL_CONSTANT_BUFFS["Cryo Resonance"].items():
            applied_buffs[stat] = applied_buffs.get(stat, 0.0) + val

    if event_flags.get("exaiphanes_blade_state") == "ON":
        buff_def = CONDITIONAL_CONSTANT_BUFFS["Exaiphanes Blade Passive"]
        for stat, values in buff_def.items():
            if isinstance(values, list):
                val = values[refinement - 1]
            else:
                val = values
            applied_buffs[stat] = applied_buffs.get(stat, 0.0) + val

    ## 2. Process Stack Buffs (Integers from Timeline)
    marvelous_stacks = event_flags.get("marvelous_stacks", 0)
    if marvelous_stacks > 0:
        # 1. Odette A1 (Always applies if stacks > 0 and Odette is present)
        a1_buff = STACK_BUFFS.get("Odette A1", {})
        for stat, val_per_stack in a1_buff.items():
            applied_buffs[stat] = applied_buffs.get(stat, 0.0) + (val_per_stack * marvelous_stacks)

        # 2. Odette C2 (Only applies if Odette is C2+)
        odette_data = party.get("Odette", {})
        odette_const = odette_data if isinstance(odette_data, int) else odette_data.get("constellation", 0)
        if odette_const >= 2:
            c2_buff = STACK_BUFFS.get("Odette C2", {})
            for stat, val_per_stack in c2_buff.items():
                applied_buffs[stat] = applied_buffs.get(stat, 0.0) + (val_per_stack * marvelous_stacks)

    # 3. Process Non Static Buffs (Stat-scaling functions)
    #if event_flags.get("dreamdrifter_state") == "ON":
    #    buff_def = CONDITIONAL_NON_CONSTANT_BUFFS["Mizuki Skill Bonus"]
    #    stat = buff_def["stat"]
    #    val = buff_def["compute"](initial_stats)
    #    applied_buffs[stat] = applied_buffs.get(stat, 0.0) + val

    return applied_buffs

def build_snapshot_stats(initial_stats, event_flags, party=None, refinement=1):

    final_stats = initial_stats.copy()
    
    # Call your centralized resolver function here
    active_buffs = resolve_active_buffs(final_stats, event_flags, party=party, refinement=refinement)
    
    # Apply all resolved stat modifiers in one clean loop
    for stat, val in active_buffs.items():
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
        "Physical Bonus": snapshot_stats["physical_bonus"],
        "Pyro Bonus": snapshot_stats["pyro_bonus"],
        "Cryo Bonus": snapshot_stats["cryo_bonus"],
        "Geo Bonus": snapshot_stats["geo_bonus"],
        "Electro Bonus": snapshot_stats["electro_bonus"],
        "Dendro Bonus": snapshot_stats["dendro_bonus"],
        "Hydro Bonus": snapshot_stats["hydro_bonus"],
        "Anemo Bonus": snapshot_stats["anemo_bonus"]
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
    }
    
    elements = ["physical", "pyro", "cryo", "geo", "electro", "dendro", "hydro", "anemo"]
    for elem in elements:
        key = f"{elem}_bonus"
        val = snapshot_stats.get(key, 0.0)
        if val > 0.0:
            display_name = f"{elem.capitalize()} DMG"
            snapshot_card_formatted[display_name] = f"{round(val * 100, 1)}%"

    return snapshot_card_formatted