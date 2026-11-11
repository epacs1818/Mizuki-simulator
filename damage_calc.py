import itertools
import numpy as np

# Attack-type DMG bonuses (artifacts can grant e.g. "burst_bonus"). They are
# STANDARD-damage only: they never enter stellar or stellar-reaction damage.
_ATTACK_TYPE_BONUS_KEYS = {
    "Normal Attack": "normal_bonus",
    "Charged Attack": "charged_bonus",
    "Plunging Attack": "plunging_bonus",
    "Elemental Skill": "skill_bonus",
    "Elemental Burst": "burst_bonus",
}


class HitDamageContext:
    """Adapter to normalize Hit dataclasses or event dictionaries from timeline.py."""
    def __init__(self, obj):
        if isinstance(obj, dict):
            self.category = obj.get("category", "standard")
            self.stat_ref = obj.get("stat_ref", "ATK")
            self.motion_value = float(obj.get("motion_value", 0.0) or 0.0)
            self.element = obj.get("element", "Physical")
            self.attack_type = obj.get("attack_type")
            self.character = obj.get("character")
            self.swirl_metadata = obj.get("swirl_metadata")
            self.vortex_metadata = obj.get("vortex_metadata")
            self.c1_quill = bool(obj.get("c1_quill", False))
            self.action = obj.get("action", "")
            self.name = obj.get("hit_name", obj.get("action", ""))
        else:
            self.category = getattr(obj, "category", "standard")
            self.stat_ref = getattr(obj, "stat_ref", "ATK")
            self.motion_value = float(getattr(obj, "motion_value", 0.0) or 0.0)
            self.element = getattr(obj, "element", "Physical")
            self.attack_type = getattr(obj, "attack_type", None)
            self.character = getattr(obj, "character", None)
            self.swirl_metadata = getattr(obj, "swirl_metadata", None)
            self.vortex_metadata = getattr(obj, "vortex_metadata", None)
            self.c1_quill = bool(getattr(obj, "c1_quill", False))
            self.action = getattr(obj, "name", "")
            self.name = getattr(obj, "name", "")

DEFAULT_ENEMY_STATS = {
    'enemy_lv': 100,
    'pyro_res': 0.1,
    'cryo_res': 0.1,
    'hydro_res': 0.1,
    'electro_res': 0.1,
    'anemo_res': 0.1,
    'geo_res': 0.1,
    'dendro_res': 0.1,
    'physical_res': 0.1
}
enemy_stats = DEFAULT_ENEMY_STATS


def crit_mult_from_crit_value(cr: float, cd: float) -> float:
    """Crit multiplier under the '100% RV' model.

    A carry's crit is modeled as a single Crit Value CV = 2*CR + CD (decimal).
    With the optimal crit split this is the damage multiplier:
        crit_mult = 1 + CV^2/8            for CV <= 4.0
        crit_mult = CV - 1                for CV >  4.0
    The two branches are continuous at CV = 4.0 (both equal 3.0).
    """
    cv = 2.0 * cr + cd
    if cv <= 4.0:
        return 1.0 + cv * cv / 8.0
    return cv - 1.0


def calculate_damage(hit, final_stats, enemy_stats=None, quill_damage=0.0, char_level=90, party_dict=None):
    """
    Dispatcher function that routes damage calculation based on the damage category.
    """
    if enemy_stats is None:
        enemy_stats = DEFAULT_ENEMY_STATS

    ctx = HitDamageContext(hit) if not isinstance(hit, HitDamageContext) else hit

    cat = ctx.category
    cat_str = cat.name if hasattr(cat, "name") else (cat.value if hasattr(cat, "value") else str(cat))
    cat_str_upper = cat_str.upper()

    if "STANDARD" in cat_str_upper:
        return calculate_standard_damage(ctx, final_stats, enemy_stats, quill_damage=quill_damage, char_level=char_level)
    elif "STELLAR_REACTION" in cat_str_upper or "REACTION" in cat_str_upper:
        return calculate_stellar_reaction_damage(ctx, final_stats, enemy_stats, party_dict=party_dict, quill_damage=quill_damage)
    elif "STELLAR" in cat_str_upper:
        return calculate_stellar_damage(ctx, final_stats, enemy_stats, quill_damage=quill_damage)
    else:
        raise ValueError(f"Unknown damage category: {ctx.category}")

def calculate_standard_damage(hit, final_stats, enemy_stats, quill_damage=0.0, char_level=90):
    """
    Calculates Standard Damage using 6 multipliers:
    1. Base Damage (+ Quills)
    2. Bonus Multiplier
    3. Crit Multiplier
    4. DEF Multiplier
    5. RES Multiplier
    """
    # 1. Base Damage and Quills
    stat_ref_key = hit.stat_ref.value if hasattr(hit.stat_ref, "value") else str(hit.stat_ref)
    stat_value = final_stats.get(stat_ref_key, final_stats.get("ATK", 0.0))
    base_damage = stat_value * hit.motion_value

    total_base = base_damage + quill_damage

    # 2. Bonus Multipliers
    element_key = f"{hit.element.lower()}_bonus" if hit.element else "physical_bonus"
    element_bonus = final_stats.get(element_key, 0.0)

    attack_type_bonus = 0.0
    if hit.attack_type:
        at_str = hit.attack_type.value if hasattr(hit.attack_type, "value") else str(hit.attack_type).lower()
        bonus_key = _ATTACK_TYPE_BONUS_KEYS.get(at_str)
        if bonus_key:
            attack_type_bonus = final_stats.get(bonus_key, 0.0)
        else:
            attack_type_bonus = final_stats.get(f"{at_str}_bonus", final_stats.get(at_str, 0.0))

    standard_damage_bonus = final_stats.get("standard_damage_bonus", 0.0)

    # Bonus multiplier starts at 1.0 (100% base damage) + sum of additive bonuses
    bonus_mult = 1.0 + element_bonus + attack_type_bonus + standard_damage_bonus

    # 3. Crit Multipliers
    crit_rate = final_stats.get("CR", final_stats.get("crit_rate", 0.05))
    crit_dmg = final_stats.get("CD", final_stats.get("crit_dmg", 0.50))

    if final_stats.get("rv_mode"):
        # 100% RV mode: single Crit Value, no crit/non-crit variance.
        crit_mult = crit_mult_from_crit_value(crit_rate, crit_dmg)
        crit_mult_average = crit_mult
        crit_mult_absolute = crit_mult
    else:
        crit_mult_average = 1.0 + min(crit_rate, 1.0) * crit_dmg
        crit_mult_absolute = 1.0 + crit_dmg

    # 4. DEF Multiplier
    enemy_lv = enemy_stats.get("enemy_lv", 100)
    enemy_def = 500 + enemy_lv * 5
    def_dmg_mitigation = enemy_def / (enemy_def + 500 + char_level * 5)
    def_mult = 1.0 - def_dmg_mitigation

    # 5. RES Multiplier
    elem_lower = hit.element.lower() if hit.element else "physical"
    enemy_res = enemy_stats.get(f"{elem_lower}_res", 0.1)
    res_shred = final_stats.get(f"{elem_lower}_shred", 0.0)
    net_res = enemy_res - res_shred

    if net_res < 0:
        res_mult = 1.0 - net_res / 2.0
    elif 0 <= net_res < 0.75:
        res_mult = 1.0 - net_res
    else:
        res_mult = 1.0 / (1.0 + 4.0 * net_res)

    # 6. Final Standard Damage Calculations
    if final_stats.get("rv_mode"):
        # 100% RV: deterministic (no crit variance) using the Crit Value crit_mult.
        non_crit = total_base * bonus_mult * crit_mult_average * def_mult * res_mult
        crit_damage = non_crit
        average_damage = non_crit
        effective_average_damage = total_base * bonus_mult * crit_mult_average * def_mult
    else:
        non_crit = total_base * bonus_mult * def_mult * res_mult
        crit_damage = total_base * bonus_mult * crit_mult_absolute * def_mult * res_mult
        average_damage = total_base * bonus_mult * crit_mult_average * def_mult * res_mult
        effective_average_damage = total_base * bonus_mult * crit_mult_average * def_mult

    return {
        "base_damage": base_damage,
        "quill_damage": quill_damage,
        "bonus_mult": bonus_mult,
        "elevation_mult": None,  # Standard damage has no elevation multiplier.
        "crit_mult_average": crit_mult_average,
        "crit_mult_absolute": crit_mult_absolute,
        "def_mult": def_mult,
        "res_mult": res_mult,
        "non_crit": non_crit,
        "crit_damage": crit_damage,
        "average_damage": average_damage,
        "effective_average_damage": effective_average_damage,
    }

def calculate_stellar_damage(hit, final_stats, enemy_stats, quill_damage=0.0):
    """
    Calculates Stellar Damage using 5 multipliers (Bonus Multiplier does not apply to quills):
    1. Base Damage (+ Quills)
    2. Bonus Multiplier (Excludes Quills)
    3. Elevation Multiplier
    4. Crit Multiplier
    5. RES Multiplier (No DEF multiplier)
    """
    # 1. Base Damage
    stat_ref_key = hit.stat_ref.value if hasattr(hit.stat_ref, "value") else str(hit.stat_ref)
    stat_value = final_stats.get(stat_ref_key, final_stats.get("ATK", 0.0))
    base_damage = stat_value * hit.motion_value

    # 1.5) Odette A4: mv increase multiplier on her stellar attack motion values
    #      (Skill_stellar / plume_stellar / wing_stellar); default 1.0 for everyone.
    smv = final_stats.get("stellar_mv_mult", 1.0) or 1.0
    base_damage *= smv

    # 2. Bonus Multiplier (Excludes Quills)
    em = final_stats.get("EM", final_stats.get("em", 0.0))
    em_bonus = (6.0 * em) / (2000.0 + em)
    
    jubilee_mult = final_stats.get("jubilee_mult", final_stats.get("Jubilee Mult", 0.0))
    stellar_bonus = final_stats.get("stellar_bonus", final_stats.get("Stellar Bonus", 0.0))
    
    bonus_mult = (1.0 + jubilee_mult) * (1.0 + em_bonus + stellar_bonus)

    # 3. Elevation Multiplier
    elevation_val = final_stats.get("elevation_mult", final_stats.get("Elevation Mult", 0.0))
    # Handles both raw percentage adders and pre-resolved multipliers safely
    elevation_mult = elevation_val if elevation_val >= 1.0 else (1.0 + elevation_val)

    # 4. Crit Multipliers
    crit_rate = final_stats.get("CR", final_stats.get("crit_rate", 0.05))
    crit_dmg = final_stats.get("CD", final_stats.get("crit_dmg", 0.50))

    # Systematic C6 Part 1 Stellar Crit: applied via dedicated stellar crit stats,
    # which are resolved for every party member during Mizuki's Dreamdrifter state.
    crit_rate += final_stats.get("stellar_crit_rate", 0.0)
    crit_dmg += final_stats.get("stellar_crit_dmg", 0.0)

    if final_stats.get("rv_mode"):
        # 100% RV mode: single Crit Value, no crit/non-crit variance.
        crit_mult = crit_mult_from_crit_value(crit_rate, crit_dmg)
        crit_mult_average = crit_mult
        crit_mult_absolute = crit_mult
    else:
        crit_mult_average = 1.0 + min(crit_rate, 1.0) * crit_dmg
        crit_mult_absolute = 1.0 + crit_dmg

    # 5. RES Multiplier (No DEF multiplier for Stellar Damage)
    elem_lower = hit.element.lower() if hit.element else "physical"
    enemy_res = enemy_stats.get(f"{elem_lower}_res", 0.1)
    res_shred = final_stats.get(f"{elem_lower}_shred", 0.0)
    net_res = enemy_res - res_shred

    if net_res < 0:
        res_mult = 1.0 - net_res / 2.0
    elif 0 <= net_res < 0.75:
        res_mult = 1.0 - net_res
    else:
        res_mult = 1.0 / (1.0 + 4.0 * net_res)

    # Final Stellar Damage Calculations (Bonus multiplier does not apply to quills)
    if final_stats.get("rv_mode"):
        # 100% RV: deterministic (no crit variance) using the Crit Value crit_mult.
        non_crit = (base_damage * bonus_mult + quill_damage) * elevation_mult * res_mult * crit_mult_average
        crit_damage = non_crit
        average_damage = non_crit
        effective_average_damage = (base_damage * bonus_mult + quill_damage) * elevation_mult * crit_mult_average
    else:
        non_crit = (base_damage * bonus_mult + quill_damage) * elevation_mult * res_mult
        crit_damage = (base_damage * bonus_mult + quill_damage) * elevation_mult * crit_mult_absolute * res_mult
        average_damage = (base_damage * bonus_mult + quill_damage) * elevation_mult * crit_mult_average * res_mult
        effective_average_damage = (base_damage * bonus_mult + quill_damage) * elevation_mult * crit_mult_average

    return {
        "base_damage": base_damage,
        "quill_damage": quill_damage,
        "em_bonus": em_bonus,
        "bonus_mult": bonus_mult,
        "elevation_mult": elevation_mult,
        "crit_mult_average": crit_mult_average,
        "crit_mult_absolute": crit_mult_absolute,
        "def_mult": None,  # Stellar damage has no DEF multiplier.
        "res_mult": res_mult,
        "non_crit": non_crit,
        "crit_damage": crit_damage,
        "average_damage": average_damage,
        "effective_average_damage": effective_average_damage,
    }


import itertools
import numpy as np

def get_base_damage_for_level(level: int) -> float:
    """Returns the base reaction damage for a given character level."""
    level_table = {
        60: 492.88489,
        70: 765.640231,
        80: 1077.443668,
        90: 1446.853458,
        95: 1561.468,
        100: 1674.8092
    }
    if level in level_table:
        return level_table[level]
    available_levels = sorted(level_table.keys())
    closest_level = min(available_levels, key=lambda x: abs(x - level))
    return level_table[closest_level]

def calculate_stellar_reaction_damage(hit, final_stats, enemy_stats, party_dict=None, quill_damage=0.0):
    """
    Calculates Stellar Reaction Damage by computing individual contributor stats,
    evaluating all 2^n crit scenarios using pre-sort damages, applying shares, 
    and returning the final expected damage and effective expected damage.
    """
    party_dict = party_dict or {}

    # 1. Extract contributors and reaction coefficient from metadata
    swirl_meta = getattr(hit, "swirl_metadata", None)
    vortex_meta = getattr(hit, "vortex_metadata", None)

    contributors = []
    reaction_coef = 0.75  # Default for standard stellar swirls

    if vortex_meta:
        level = vortex_meta.get("level", 1)
        reaction_coef = 2.0 if level == 1 else 3.0
        anemo_list = vortex_meta.get("anemo_contributors", [])
        cryo_list = vortex_meta.get("cryo_contributors", [])
        contributors = [c for c in set(anemo_list + cryo_list) if c]
    elif swirl_meta:
        reaction_coef = 0.75
        anemo_char = swirl_meta.get("anemo_contributor")
        cryo_list = swirl_meta.get("cryo_contributors", [])
        raw_contribs = ([anemo_char] if anemo_char else []) + [c for c in cryo_list if c and c != anemo_char]
        contributors = [c for c in raw_contribs if c]

    # Fallback if no metadata contributors are found
    if not contributors:
        fallback_char = getattr(hit, "character", None) or "Mizuki"
        contributors = [fallback_char]

    n = len(contributors)

    # 2. Compute individual global multipliers (Bonus, Elevation, RES, Quills)
    em = final_stats.get("EM", final_stats.get("em", 0.0))
    em_bonus = (6.0 * em) / (2000.0 + em)
    stellar_bonus = final_stats.get("stellar_bonus", final_stats.get("Stellar Bonus", 0.0))
    jubilee_mult = final_stats.get("jubilee_mult", final_stats.get("Jubilee Mult", 0.0))
    # Anastasya A4: extra jubilee that applies to STELLAR SWIRL REACTIONS only
    # (never to plain stellar damage).
    reaction_jubilee = final_stats.get("reaction_jubilee_mult", 0.0)
    # The team Jubilee (Aether + Odette) multiplies the swirl reaction bonus too.
    bonus_mult = (1.0 + jubilee_mult + reaction_jubilee) * (1.0 + em_bonus + stellar_bonus)
    quill_damage = quill_damage or final_stats.get("quill_damage", 0.0) or (hit.get("quill_damage", 0.0) if isinstance(hit, dict) else getattr(hit, "quill_damage", 0.0))

    elevation_val = final_stats.get("elevation_mult", final_stats.get("Elevation Mult", 0.0))
    elevation_mult = elevation_val if elevation_val >= 1.0 else (1.0 + elevation_val)

    # RES Multiplier
    elem_lower = hit.element.lower() if hit.element else "physical"
    enemy_res = enemy_stats.get(f"{elem_lower}_res", 0.1)
    res_shred = final_stats.get(f"{elem_lower}_shred", 0.0)
    net_res = enemy_res - res_shred

    if net_res < 0:
        res_mult = 1.0 - net_res / 2.0
    elif 0 <= net_res < 0.75:
        res_mult = 1.0 - net_res
    else:
        res_mult = 1.0 / (1.0 + 4.0 * net_res)

    # 3. Build per-contributor dictionaries for tracking
    contrib_base_damage = {}
    contrib_bonus_mult = {}
    contrib_elevation_mult = {}
    contrib_crit_mult_average = {}
    contrib_crit_mult_absolute = {}
    contrib_res_mult = {}
    contrib_non_crit = {}
    contrib_crit_damage = {}
    contrib_average_damage = {}

    # Internal lists for the scenario loop
    non_crit_damages_list = []
    crit_damages_list = []
    crit_rates_list = []

    for char_name in contributors:
        char_info = party_dict.get(char_name, {})
        char_level = char_info.get("level", 90)
        
        # Base damage for this contributor
        b_val = get_base_damage_for_level(char_level) * reaction_coef
        contrib_base_damage[char_name] = b_val
        # em_bonus uses THIS contributor's EM at the event moment; the swirl-wide
        # stellar_bonus and team Jubilee stay constant across contributors.
        em_c = float(char_info.get("EM", char_info.get("em", em)))
        em_bonus_c = (6.0 * em_c) / (2000.0 + em_c)
        bonus_mult_c = (1.0 + jubilee_mult + reaction_jubilee) * (1.0 + em_bonus_c + stellar_bonus)
        contrib_bonus_mult[char_name] = bonus_mult_c
        contrib_elevation_mult[char_name] = elevation_mult
        contrib_res_mult[char_name] = res_mult

        # Crit stats
        c_rate = char_info.get("CR", char_info.get("crit_rate", final_stats.get("CR", final_stats.get("crit_rate", 0.05))))
        c_dmg = char_info.get("CD", char_info.get("crit_dmg", final_stats.get("CD", final_stats.get("crit_dmg", 0.50))))

        # Systematic C6 Part 1 Stellar Crit for Reactions: party-wide during DDS.
        c_rate = float(c_rate) + final_stats.get("stellar_crit_rate", 0.0)
        c_dmg = float(c_dmg) + final_stats.get("stellar_crit_dmg", 0.0)

        c_rate = min(max(c_rate, 0.0), 1.0)
        c_dmg = float(c_dmg)
        crit_rates_list.append(c_rate)

        if party_dict.get(char_name, {}).get("rv_mode"):
            # 100% RV contributor: single Crit Value, no crit/non-crit variance.
            crit_mult = crit_mult_from_crit_value(c_rate, c_dmg)
            contrib_crit_mult_average[char_name] = crit_mult
            contrib_crit_mult_absolute[char_name] = crit_mult
        else:
            contrib_crit_mult_average[char_name] = 1.0 + c_rate * c_dmg
            contrib_crit_mult_absolute[char_name] = 1.0 + c_dmg

        # Contributor pre-share metrics. The quill is NOT folded in here: it is applied
        # once at the AGGREGATE level, after the contribution weighting (see below).
        q_base = b_val * bonus_mult_c

        # non_crit: base with 0% crit (crit factor = 1.0)
        nc_val = q_base * elevation_mult * res_mult
        contrib_non_crit[char_name] = nc_val
        non_crit_damages_list.append(nc_val)

        # crit_damage: base with 100% crit (crit factor = 1 + CD)
        cd_val = q_base * (1.0 + c_dmg) * elevation_mult * res_mult
        contrib_crit_damage[char_name] = cd_val
        crit_damages_list.append(cd_val)

        # average_damage (useful for inspection/returning)
        avg_val = q_base * (1.0 + c_rate * c_dmg) * elevation_mult * res_mult
        contrib_average_damage[char_name] = avg_val

    non_crit_arr = np.array(non_crit_damages_list, dtype=float)
    crit_damages_arr = np.array(crit_damages_list, dtype=float)
    crit_rates_arr = np.array(crit_rates_list, dtype=float)

    # 100% RV / KQM contributors are DETERMINISTIC: their crit is one Crit Value, so
    # their scenario collapses to a single outcome that carries the CV multiplier
    # (probability 1) instead of the 1 + CR*CD branches built above. This keeps the
    # expected-value loop, the crit/non-crit aggregates and the audit dicts aligned
    # with the standard/stellar paths (which already use crit_mult_from_crit_value).
    for idx, contributor in enumerate(contributors):
        if not party_dict.get(contributor, {}).get("rv_mode"):
            continue
        rv_mult = contrib_crit_mult_average[contributor]
        rv_value = non_crit_damages_list[idx] * rv_mult
        non_crit_arr[idx] = rv_value
        crit_damages_arr[idx] = rv_value
        crit_rates_arr[idx] = 1.0
        contrib_non_crit[contributor] = rv_value
        contrib_crit_damage[contributor] = rv_value
        contrib_average_damage[contributor] = rv_value

    # 4. Determine share weights dynamically based on contributor count
    if n >= 4:
        weights = np.array([0.6, 0.3, 0.05, 0.05])
    elif n == 3:
        weights = np.array([0.6, 0.3, 0.1])
    elif n == 2:
        weights = np.array([0.6, 0.3])
    else:
        weights = np.array([0.6])

    # 5. Statistical Expected Value loop over all 2^n crit combinations
    expected_damage = 0.0

    for scenario in itertools.product([0, 1], repeat=n):
        scenario = np.array(scenario)  # 1 = crit (uses crit_damage), 0 = non-crit (uses non_crit)

        # Probability of this specific combination of crits occurring
        prob = np.prod(np.where(scenario == 1, crit_rates_arr, 1.0 - crit_rates_arr))

        # Select corresponding pre-share value for each contributor based on scenario (crit vs non-crit)
        scenario_values = np.where(scenario == 1, crit_damages_arr, non_crit_arr)

        # Sort values in descending order (highest to lowest damage) *before* applying shares
        sorted_values = np.sort(scenario_values)[::-1]

        # Apply share weights
        current_weights = weights[:len(sorted_values)]
        scenario_score = np.dot(sorted_values, current_weights)

        # Accumulate probability-weighted score into total expected damage
        expected_damage += prob * scenario_score

    # Quill added POST-contribution: applied once to the aggregate. It skips
    # bonus_mult but keeps elevation, res and an expected crit factor (share-weighted
    # average over the contributors).
    w1 = weights[:n]
    wsum = float(w1.sum()) or 1.0
    exp_crit = float(np.dot(np.array([contrib_crit_mult_average[c] for c in contributors]), w1) / wsum)
    exp_abs = float(np.dot(np.array([contrib_crit_mult_absolute[c] for c in contributors]), w1) / wsum)
    if getattr(hit, "c1_quill", False):
        mizuki_em_at_event = float(party_dict.get("Mizuki", {}).get("EM", 0.0) or 0.0)
        quill_damage = 5.5 * mizuki_em_at_event
    quill_crit = contrib_crit_mult_average.get("Mizuki", exp_crit)
    q_nc = quill_damage * res_mult * quill_crit

    expected_damage += q_nc
    effective_expected_damage = expected_damage / res_mult if res_mult > 0 else expected_damage

    non_crit = float(np.dot(np.sort(non_crit_arr)[::-1], weights[:len(non_crit_arr)])) + q_nc
    crit_damage = float(np.dot(np.sort(crit_damages_arr)[::-1], weights[:len(crit_damages_arr)])) + q_nc
    average_damage = float(expected_damage)
    effective_average_damage = float(effective_expected_damage)

    return {
        "contributor_base_damage": contrib_base_damage,
        "contributor_bonus_mult": contrib_bonus_mult,
        "contributor_elevation_mult": contrib_elevation_mult,
        "contributor_crit_mult_average": contrib_crit_mult_average,
        "contributor_crit_mult_absolute": contrib_crit_mult_absolute,
        "contributor_res_mult": contrib_res_mult,
        "contributor_non_crit": contrib_non_crit,
        "contributor_crit_damage": contrib_crit_damage,
        "contributor_average_damage": contrib_average_damage,
        "expected_damage": expected_damage,
        "effective_expected_damage": effective_expected_damage,
        "non_crit": non_crit,
        "crit_damage": crit_damage,
        "average_damage": average_damage,
        "effective_average_damage": effective_average_damage,
    }