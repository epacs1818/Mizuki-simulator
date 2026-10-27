# stats_calculator.py
from characters import CHARACTER_BASE_STATS
from weapons import WEAPON_STATS

def compute_character_stats(char_name, weapon_full_name, main_stats_total, subs_total):
    """
    Computes off-field character stats based on Base + Weapon + Artifacts.
    """
    # 1. Base Stats (Level 90)
    base_char = CHARACTER_BASE_STATS.get(char_name, {
        "base_hp": 10000.0, "base_atk": 200.0, "base_def": 600.0,
        "atk_percent": 0.0, "hp_percent": 0.0, "def_percent": 0.0,
        "atk_flat": 0.0, "hp_flat": 0.0, "def_flat": 0.0,
        "em": 0.0, "crit_rate": 0.05, "crit_dmg": 0.50, "er": 1.0, "Bonus Damage": 0.0
    })
    
    # 2. Weapon Stats Extraction (strip out refinement for lookup)
    weapon_key = weapon_full_name.split(" (")[0] if " (" in weapon_full_name else weapon_full_name
    base_weapon = WEAPON_STATS.get(weapon_key, {"base_atk": 454.0, "secondary_stat": None, "secondary_value": 0.0})
    
    # 3. Aggregate Percentages and Flats
    # Combine character ascension/base percents, artifact main stats, and substats
    total_hp_percent = base_char["hp_percent"] + (main_stats_total.get("hp%", 0.0) / 100.0) + (subs_total.get("hp%", 0.0) / 100.0)
    total_hp_flat = base_char["hp_flat"] + main_stats_total.get("flat_hp", 0.0) + subs_total.get("flat_hp", 0.0) + main_stats_total.get("hp", 0.0) + subs_total.get("hp", 0.0)
    
    total_atk_percent = base_char["atk_percent"] + (main_stats_total.get("atk%", 0.0) / 100.0) + (subs_total.get("atk%", 0.0) / 100.0)
    # Add weapon secondary if it's ATK%
    if base_weapon["secondary_stat"] == "atk_percent":
        total_atk_percent += base_weapon["secondary_value"]
        
    total_atk_flat = base_char["atk_flat"] + main_stats_total.get("flat_atk", 0.0) + subs_total.get("flat_atk", 0.0) + main_stats_total.get("atk", 0.0) + subs_total.get("atk", 0.0)
    
    total_def_percent = base_char["def_percent"] + (main_stats_total.get("def%", 0.0) / 100.0) + (subs_total.get("def%", 0.0) / 100.0)
    total_def_flat = base_char["def_flat"] + main_stats_total.get("flat_def", 0.0) + subs_total.get("flat_def", 0.0)
    
    # EM
    total_em = base_char["em"] + main_stats_total.get("em", 0.0) + subs_total.get("em", 0.0)
    if base_weapon["secondary_stat"] == "em":
        total_em += base_weapon["secondary_value"]
        
    # Crit Rate & Crit Damage
    total_cr = base_char["crit_rate"] + (main_stats_total.get("crit_rate%", 0.0) / 100.0) + (subs_total.get("crit_rate%", 0.0) / 100.0)
    if base_weapon["secondary_stat"] == "crit_rate":
        total_cr += base_weapon["secondary_value"]
        
    total_cd = base_char["crit_dmg"] + (main_stats_total.get("crit_damage%", 0.0) / 100.0) + (subs_total.get("crit_damage%", 0.0) / 100.0)
    if base_weapon["secondary_stat"] == "crit_dmg":
        total_cd += base_weapon["secondary_value"]
        
    # Energy Recharge (Base is 100% / 1.0)
    total_er = base_char["er"] + (main_stats_total.get("er%", 0.0) / 100.0) + (subs_total.get("er%", 0.0) / 100.0)
    if base_weapon["secondary_stat"] == "er%":
        total_er += base_weapon["secondary_value"]
        
    # Bonus Damage (Goblet elemental bonus, etc.)
    total_bonus_dmg = base_char["Bonus Damage"] + (main_stats_total.get("elemental_bonus%", 0.0) / 100.0)

    # --- FINAL CALCULATIONS ---
    final_hp = (base_char["base_hp"] * (1.0 + total_hp_percent)) + total_hp_flat
    
    combined_base_atk = base_char["base_atk"] + base_weapon["base_atk"]
    final_atk = (combined_base_atk * (1.0 + total_atk_percent)) + total_atk_flat
    
    final_def = (base_char["base_def"] * (1.0 + total_def_percent)) + total_def_flat

    # Return Off-Field Dictionary (Formatted for UI display)
    off_field_display = {
        "HP": round(final_hp, 1),
        "ATK": round(final_atk, 1),
        "DEF": round(final_def, 1),
        "EM": round(total_em, 1),
        "CR": f"{round(total_cr * 100, 1)}%",
        "CD": f"{round(total_cd * 100, 1)}%",
        "ER": f"{round(total_er * 100, 1)}%",
        "Bonus Damage": f"{round(total_bonus_dmg * 100, 1)}%"
    }

    # Return On-Field Dictionary (Raw floats for math/combat simulator engines)
    on_field_combat_state = {
        "hp": final_hp,
        "atk": final_atk,
        "def": final_def,
        "em": total_em,
        "crit_rate": total_cr,
        "crit_dmg": total_cd,
        "er": total_er,
        "bonus_damage": total_bonus_dmg
    }

    return off_field_display, on_field_combat_state