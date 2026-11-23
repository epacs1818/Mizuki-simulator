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
    # Element-specific crit (Faruzan anemo_crit_dmg, Tsaritsa cryo_crit_rate)
    # is defined by the buff itself, not gated in the timeline.
    elem_lower = hit.element.lower() if hit.element else "physical"
    crit_rate += final_stats.get(f"{elem_lower}_crit_rate", 0.0)
    crit_dmg += final_stats.get(f"{elem_lower}_crit_dmg", 0.0)

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
    elem_lower = hit.element.lower() if hit.element else "physical"
    crit_rate += final_stats.get(f"{elem_lower}_crit_rate", 0.0)
    crit_dmg += final_stats.get(f"{elem_lower}_crit_dmg", 0.0)

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

def _res_multiplier(enemy_res, shred):
    """Enemy RES multiplier for one element (shared by all damage paths)."""
    net = enemy_res - shred
    if net < 0:
        return 1.0 - net / 2.0
    if net < 0.75:
        return 1.0 - net
    return 1.0 / (1.0 + 4.0 * net)


def _elevation(info):
    """One contributor's elevation multiplier (raw adders are converted)."""
    val = float(info.get("elevation_mult", info.get("Elevation Mult", 0.0)))
    return val if val >= 1.0 else 1.0 + val


def _crit_stats(info, element):
    """(CR, CD) for one contributor: base + stellar crit + element crit."""
    rate = float(info.get("CR", info.get("crit_rate", 0.05)))
    dmg = float(info.get("CD", info.get("crit_dmg", 0.50)))
    rate += float(info.get("stellar_crit_rate", info.get("Stellar CR", 0.0)))
    dmg += float(info.get("stellar_crit_dmg", info.get("Stellar CD", 0.0)))
    rate += float(info.get(f"{element}_crit_rate", 0.0))
    dmg += float(info.get(f"{element}_crit_dmg", 0.0))
    return min(max(rate, 0.0), 1.0), dmg


def calculate_stellar_reaction_damage(hit, final_stats, enemy_stats,
                                      party_dict=None, quill_damage=0.0):
    """Stellar reaction damage with PER-CONTRIBUTOR multipliers.

    Each contributor's share uses their own final stats: EM, stellar_bonus,
    jubilee, reaction jubilee, elevation, RES shred, CR/CD, stellar crit and
    the reaction element's crit. A Cryo contributor's share of an Anemo swirl
    therefore gets Faruzan's anemo_crit_dmg if their snapshot has that buff.
    Shares are 0.6 / 0.3 / 0.05 / 0.05 by descending pre-share damage; the
    expected value covers all 2^n crit scenarios. The effective value ignores
    RES. Multiplier audit columns stay null for reactions.
    """
    party_dict = party_dict or {}

    swirl_meta = getattr(hit, "swirl_metadata", None)
    vortex_meta = getattr(hit, "vortex_metadata", None)
    contributors = []
    reaction_coef = 0.75
    if vortex_meta:
        level = vortex_meta.get("level", 1)
        reaction_coef = 2.0 if level == 1 else 3.0
        anemo_list = vortex_meta.get("anemo_contributors", [])
        cryo_list = vortex_meta.get("cryo_contributors", [])
        contributors = [c for c in set(anemo_list + cryo_list) if c]
    elif swirl_meta:
        anemo_char = swirl_meta.get("anemo_contributor")
        cryo_list = swirl_meta.get("cryo_contributors", [])
        raw = [anemo_char] if anemo_char else []
        raw += [c for c in cryo_list if c and c != anemo_char]
        contributors = [c for c in raw if c]
    if not contributors:
        contributors = [getattr(hit, "character", None) or "Mizuki"]

    element = (hit.element or "physical").lower()
    enemy_res = enemy_stats.get(f"{element}_res", 0.1)
    n = len(contributors)

    contrib = {}
    non_crit_values, crit_values = [], []
    eff_non_crit, eff_crit, crit_rates = [], [], []
    for name in contributors:
        info = party_dict.get(name, {})
        base = get_base_damage_for_level(info.get("level", 90)) * reaction_coef
        em = float(info.get("EM", info.get("em", 0.0)))
        em_bonus = (6.0 * em) / (2000.0 + em)
        stellar = float(info.get("stellar_bonus", info.get("Stellar Bonus", 0.0)))
        jub = float(info.get("jubilee_mult", info.get("Jubilee Mult", 0.0)))
        rjub = float(info.get("reaction_jubilee_mult", 0.0))
        bonus = (1.0 + jub + rjub) * (1.0 + em_bonus + stellar)
        elev = _elevation(info)
        shred = float(info.get(f"{element}_shred", 0.0))
        res = _res_multiplier(enemy_res, shred)
        rate, dmg = _crit_stats(info, element)
        if info.get("rv_mode"):
            crit_mult = crit_mult_from_crit_value(rate, dmg)
            nc = cd = avg = base * bonus * elev * res * crit_mult
            nc_eff = cd_eff = base * bonus * elev * crit_mult
            rate = 1.0
        else:
            nc = base * bonus * elev * res
            cd = base * bonus * (1.0 + dmg) * elev * res
            avg = base * bonus * (1.0 + rate * dmg) * elev * res
            nc_eff = base * bonus * elev
            cd_eff = base * bonus * (1.0 + dmg) * elev
        contrib[name] = {"base_damage": base, "bonus_mult": bonus,
                         "elevation_mult": elev, "res_mult": res,
                         "crit_rate": rate, "crit_dmg": dmg,
                         "non_crit": nc, "crit_damage": cd,
                         "average_damage": avg}
        crit_rates.append(rate)
        non_crit_values.append(nc)
        crit_values.append(cd)
        eff_non_crit.append(nc_eff)
        eff_crit.append(cd_eff)

    if n >= 4:
        weights = np.array([0.6, 0.3, 0.05, 0.05])
    elif n == 3:
        weights = np.array([0.6, 0.3, 0.1])
    elif n == 2:
        weights = np.array([0.6, 0.3])
    else:
        weights = np.array([0.6])

    nc_arr = np.array(non_crit_values, dtype=float)
    cd_arr = np.array(crit_values, dtype=float)
    eff_nc = np.array(eff_non_crit, dtype=float)
    eff_cd = np.array(eff_crit, dtype=float)
    rates = np.array(crit_rates, dtype=float)

    expected = 0.0
    expected_eff = 0.0
    for scenario in itertools.product([0, 1], repeat=n):
        scenario = np.array(scenario)
        prob = np.prod(np.where(scenario == 1, rates, 1.0 - rates))
        values = np.where(scenario == 1, cd_arr, nc_arr)
        values_eff = np.where(scenario == 1, eff_cd, eff_nc)
        expected += prob * np.dot(np.sort(values)[::-1], weights[:n])
        expected_eff += prob * np.dot(np.sort(values_eff)[::-1], weights[:n])

    # Quill: once after the shares, no bonus_mult, owner's elevation/RES/crit.
    if getattr(hit, "c1_quill", False):
        owner_info = party_dict.get("Mizuki", {})
        quill_damage = 5.5 * float(
            owner_info.get("EM", owner_info.get("em", 0.0)) or 0.0)
    else:
        owner_info = party_dict.get(
            getattr(hit, "character", None) or contributors[0], {})
    if quill_damage:
        q_rate, q_dmg = _crit_stats(owner_info, element)
        q_elev = _elevation(owner_info)
        q_shred = float(owner_info.get(f"{element}_shred", 0.0))
        q_res = _res_multiplier(enemy_res, q_shred)
        if owner_info.get("rv_mode"):
            q_crit = crit_mult_from_crit_value(q_rate, q_dmg)
        else:
            q_crit = 1.0 + q_rate * q_dmg
        q_value = quill_damage * q_elev * q_res * q_crit
        q_value_eff = quill_damage * q_elev * q_crit
    else:
        q_value = q_value_eff = 0.0

    non_crit = float(np.dot(np.sort(nc_arr)[::-1], weights[:n])) + q_value
    crit_damage = float(np.dot(np.sort(cd_arr)[::-1], weights[:n])) + q_value
    average = float(expected + q_value)
    effective = float(expected_eff + q_value_eff)
    return {
        "contributor_stats": contrib,
        "contributor_non_crit": {c: contrib[c]["non_crit"] for c in contributors},
        "contributor_crit_damage": {c: contrib[c]["crit_damage"] for c in contributors},
        "contributor_average_damage": {c: contrib[c]["average_damage"] for c in contributors},
        "expected_damage": average,
        "effective_expected_damage": effective,
        "quill_damage": quill_damage,
        "non_crit": non_crit,
        "crit_damage": crit_damage,
        "average_damage": average,
        "effective_average_damage": effective,
    }
