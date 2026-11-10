import copy
from typing import Dict, Tuple, Optional, Union
from models import AttackType
from models import ActionCategory
from models import StatRef
from models import Hit, Ability, FieldSequence
from skill_scalings import CHARACTER_SKILLS


def get_ability_motion_value(character: str, category: str, sub_ability: str, level: int, stacks: Optional[int] = None) -> float:
    """
    Resolves a hit's motion value at a given talent level.

    stacks (optional) is used for per-stack mv increases (e.g. Aether's Burst
    Frostglow scaling). When omitted, per-stack entries fall back to their full
    stack count so legacy call-sites keep working unchanged.
    """
    skill_entry = CHARACTER_SKILLS[character][category][sub_ability]
    
    # 1. Get the base scaled value for the specific level (Level 10 -> index 9)
    # Divided by 100 if your calculator expects decimals (e.g., 91.68% -> 0.9168)
    base_value = skill_entry["scaling"][level - 1] / 100.0
    
    # 2. Check for an optional mv_increase using .get()
    mv_increase = skill_entry.get("mv_increase")
    if mv_increase is not None:
        if isinstance(mv_increase, (int, float)):
            # e.g., Aether's Charged Attack (mv_increase = 1.4): the increase is ADDED to the
            # decimal MV, i.e. final MV = base_value + mv_increase (not base * mv_increase).
            return base_value + mv_increase
        elif isinstance(mv_increase, list):
            # e.g., Aether's Burst Frostglow bonus list pre-multiplied by 8
            bonus_value = mv_increase[level - 1] / 100.0
            return base_value * (1.0 + bonus_value)
        return base_value

    # 3. Per-stack mv increase (e.g. Aether's Burst, scales with Frostglow stacks)
    mv_per_stack = skill_entry.get("mv_per_stack")
    if mv_per_stack is not None:
        n = stacks if stacks is not None else 8  # default = full stacks for legacy calls
        bonus_value = mv_per_stack[level - 1] / 100.0 * n
        return base_value * (1.0 + bonus_value)

    # If no mv modifier is present, just return the base scaled value
    return base_value


def update_ability_talent_level(ability: Ability, level: int):
    """
    Updates the ability's talent level and recalculates motion_value for all hits
    that have a defined scaling_key in CHARACTER_SKILLS.
    """
    ability.talent_level = level
    for hit in ability.hits:
        if hit.scaling_key:
            char_key, cat_key, sub_key = hit.scaling_key
            hit.motion_value = get_ability_motion_value(char_key, cat_key, sub_key, level)


# ==========================================
# 3. CHARACTER ABILITIES & FIELD SEQUENCES
# ==========================================

# --- Aether ---
aether_n1 = Ability(
    "N1",
    "Aether",
    talent_level=10,
    talent_type = "normal_talent",
    hits=[
        Hit(
            "N1_Hit", 0.000, element="Physical", category=ActionCategory.STANDARD_DMG,
            stat_ref=StatRef.ATK,
            motion_value=get_ability_motion_value("Aether", "Normal Attack", "N1", 10),
            attack_type=AttackType.NORMAL,
            scaling_key=("Aether", "Normal Attack", "N1")
        )
    ]
)

aether_n1ca = Ability(
    "Charged Attack",
    "Aether",
    talent_level=10,
    talent_type="normal_talent",
    hits=[
        Hit(
            "N1", 0.000, element="Physical", category=ActionCategory.STANDARD_DMG,
            stat_ref=StatRef.ATK,
            motion_value=get_ability_motion_value("Aether", "Normal Attack", "N1", 10),
            attack_type=AttackType.NORMAL,
            scaling_key=("Aether", "Normal Attack", "N1")
        ),
        Hit(
            "C1_Hit", 0.510, element="Cryo", category=ActionCategory.STELLAR_DMG,
            stat_ref=StatRef.ATK,
            motion_value=get_ability_motion_value("Aether", "Charged Attack", "C1_Hit", 10),
            attack_type=AttackType.NORMAL,
            scaling_key=("Aether", "Charged Attack", "C1_Hit")
        ),
        Hit(
            "C2_Hit", 0.720, element="Cryo", category=ActionCategory.STELLAR_DMG,
            stat_ref=StatRef.ATK,
            motion_value=get_ability_motion_value("Aether", "Charged Attack", "C2_Hit", 10),
            attack_type=AttackType.NORMAL,
            scaling_key=("Aether", "Charged Attack", "C2_Hit")
        )
    ]
)

aether_skill = Ability(
    name="Elemental Skill",
    character="Aether",
    cooldown=15.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Skill_Initial", 0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Skill", "Cast", 10), attack_type=AttackType.SKILL, scaling_key=("Aether", "Skill", "Cast")),
        Hit("Skill_Proc1",   3.149, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Skill", "Skill Proc", 10), attack_type=AttackType.SKILL, scaling_key=("Aether", "Skill", "Skill Proc")),
        Hit("Skill_Proc2",   3.329, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Skill", "Skill Proc", 10), attack_type=AttackType.SKILL, scaling_key=("Aether", "Skill", "Skill Proc")),
        Hit("Skill_Proc3",   6.030, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Skill", "Skill Proc", 10), attack_type=AttackType.SKILL, scaling_key=("Aether", "Skill", "Skill Proc")),
        Hit("Skill_Proc4",   6.269, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Skill", "Skill Proc", 10), attack_type=AttackType.SKILL, scaling_key=("Aether", "Skill", "Skill Proc")),
        Hit("Skill_Proc5",   8.969, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Skill", "Skill Proc", 10), attack_type=AttackType.SKILL, scaling_key=("Aether", "Skill", "Skill Proc")),
        Hit("Skill_Proc6",   9.179, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Skill", "Skill Proc", 10), attack_type=AttackType.SKILL, scaling_key=("Aether", "Skill", "Skill Proc")),
        Hit("Skill_Proc7",  11.880, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Skill", "Skill Proc", 10), attack_type=AttackType.SKILL, scaling_key=("Aether", "Skill", "Skill Proc")),
        Hit("Skill_Proc8",  12.090, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Skill", "Skill Proc", 10), attack_type=AttackType.SKILL, scaling_key=("Aether", "Skill", "Skill Proc")),
        Hit("Skill_Proc9",  14.880, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Skill", "Skill Proc", 10), attack_type=AttackType.SKILL, scaling_key=("Aether", "Skill", "Skill Proc")),
        Hit("Skill_Proc10", 15.090, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Skill", "Skill Proc", 10), attack_type=AttackType.SKILL, scaling_key=("Aether", "Skill", "Skill Proc")),
    ]
)

aether_burst_enhanced = Ability(
    name="Elemental Burst",
    character="Aether",
    cooldown=15.0,
    talent_level=13,
    talent_type="burst_talent",
    hits=[
        Hit("Burst_Tick1", 0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG", 13), attack_type=AttackType.BURST, scaling_key=("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG")),
        Hit("Burst_Tick2", 0.550, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG", 13), attack_type=AttackType.BURST, scaling_key=("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG")),
        Hit("Burst_Tick3", 0.550, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG", 13), attack_type=AttackType.BURST, scaling_key=("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG")),
        Hit("Burst_Tick4", 0.660, element="Cryo", elemental_app="1U", category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG", 13), attack_type=AttackType.BURST, scaling_key=("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG")),
        Hit("Burst_Tick5", 0.780, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG", 13), attack_type=AttackType.BURST, scaling_key=("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG")),
    ]
)

aether_burst_standard = Ability(
    name="Elemental Burst",
    character="Aether",
    cooldown=15.0,
    talent_level=13,
    talent_type="burst_talent",
    hits=[
        Hit("Burst_Tick1", 0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG", 13), attack_type=AttackType.BURST, scaling_key=("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG")),
        Hit("Burst_Tick2", 0.550, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG", 13), attack_type=AttackType.BURST, scaling_key=("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG")),
        Hit("Burst_Tick3", 0.550, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG", 13), attack_type=AttackType.BURST, scaling_key=("Aether", "Burst (Stellar Swirl)", "Ice Javelin Single Strike DMG")),
    ]
)

# --- Odette ---
odette_cast = Ability(
    name="Skill Cast",
    character="Odette",
    cooldown=15.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Cast",            0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Skill DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Skill DMG")),
        Hit("Plume_1",         2.220, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Plume Dance Move DMG")),
        Hit("Plume_Stellar_1", 2.220, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG")),
        Hit("Wing_1",          4.080, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Wing Dance Move DMG")),
        Hit("Wing_Stellar_1",  4.080, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG")),
        Hit("Plume_2",         6.180, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Plume Dance Move DMG")),
        Hit("Plume_Stellar_2", 6.180, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG")),
        Hit("Wing_2",          8.010, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Wing Dance Move DMG")),
        Hit("Wing_Stellar_2",  8.010, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG")),
        Hit("Plume_3",        10.110, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Plume Dance Move DMG")),
        Hit("Plume_Stellar_3",10.110, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG")),
        Hit("Wing_3",         11.940, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Wing Dance Move DMG")),
        Hit("Wing_Stellar_3", 11.940, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG")),
        Hit("Plume_4",        14.040, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Plume Dance Move DMG")),
        Hit("Plume_Stellar_4",14.040, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG")),
        Hit("Wing_4",         15.901, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Wing Dance Move DMG")),
        Hit("Wing_Stellar_4", 15.901, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG")),
        Hit("Plume_5",        17.940, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Plume Dance Move DMG")),
        Hit("Plume_Stellar_5",17.940, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG")),
        Hit("Wing_5",         19.800, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Wing Dance Move DMG")),
        Hit("Wing_Stellar_5", 19.800, element="Cryo",                     category=ActionCategory.STELLAR_DMG,  stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG")),
    ]
)

odette_recast = Ability(
    name="Skill Recast",
    character="Odette",
    cooldown=0.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Skill_Recast1", 0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Coda at Dawn's Tolling DoT", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Coda at Dawn's Tolling DoT")),
        Hit("Skill_Recast2", 0.180, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Coda at Dawn's Tolling DoT", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Coda at Dawn's Tolling DoT")),
        Hit("Skill_Recast3", 0.300, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Coda at Dawn's Tolling DoT", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Coda at Dawn's Tolling DoT")),
        Hit("Skill_Stellar", 0.871, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Coda at Dawn's Tolling Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Coda at Dawn's Tolling Stellar Swirl DMG")),
    ]
)

odette_recast_c1 = Ability(
    name="Skill Recast",
    character="Odette",
    cooldown=0.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Skill_Recast1", 0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Coda at Dawn's Tolling DoT", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Coda at Dawn's Tolling DoT")),
        Hit("Skill_Recast2", 0.180, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Coda at Dawn's Tolling DoT", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Coda at Dawn's Tolling DoT")),
        Hit("Skill_Recast3", 0.300, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Coda at Dawn's Tolling DoT", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Coda at Dawn's Tolling DoT")),
        Hit("Skill_Stellar", 0.871, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Coda at Dawn's Tolling Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Coda at Dawn's Tolling Stellar Swirl DMG")),
        Hit("Skill_Stellar_c1", 0.875, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=4.500)
    ]
)

odette_burst = Ability(
    name="Odette Burst",
    character="Odette",
    cooldown=15.0,
    talent_level=10,
    talent_type="burst_talent",
    hits=[
        Hit("Burst_tick1", 0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Burst", "Slash DMG (Per Hit)", 10), attack_type=AttackType.BURST, scaling_key=("Odette", "Burst", "Slash DMG (Per Hit)")),
        Hit("Burst_tick2", 0.301, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Burst", "Slash DMG (Per Hit)", 10), attack_type=AttackType.BURST, scaling_key=("Odette", "Burst", "Slash DMG (Per Hit)")),
        Hit("Burst_tick3", 0.421, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Burst", "Slash DMG (Per Hit)", 10), attack_type=AttackType.BURST, scaling_key=("Odette", "Burst", "Slash DMG (Per Hit)")),
        Hit("Burst_final_hit", 0.51, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Burst", "Final Slash DMG", 10), attack_type=AttackType.BURST, scaling_key=("Odette", "Burst", "Final Slash DMG")),
        Hit("Plume_1",         2.220, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Plume Dance Move DMG")),
        Hit("Plume_Stellar_1", 2.220, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG")),
        Hit("Wing_1",          4.080, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Wing Dance Move DMG")),
        Hit("Wing_Stellar_1",  4.080, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG")),
        Hit("Plume_2",         6.180, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Plume Dance Move DMG")),
        Hit("Plume_Stellar_2", 6.180, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG")),
        Hit("Wing_2",          8.010, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Wing Dance Move DMG")),
        Hit("Wing_Stellar_2",  8.010, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG")),
        Hit("Plume_3",        10.110, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Plume Dance Move DMG")),
        Hit("Plume_Stellar_3",10.110, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG")),
        Hit("Wing_3",         11.940, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Wing Dance Move DMG")),
        Hit("Wing_Stellar_3", 11.940, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG")),
        Hit("Plume_4",        14.040, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Plume Dance Move DMG")),
        Hit("Plume_Stellar_4",14.040, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG")),
        Hit("Wing_4",         15.901, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Wing Dance Move DMG")),
        Hit("Wing_Stellar_4", 15.901, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG")),
        Hit("Plume_5",        17.940, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Plume Dance Move DMG")),
        Hit("Plume_Stellar_5",17.940, element="Cryo",                     category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Plume Dance Move Stellar Swirl DMG")),
        Hit("Wing_5",         19.800, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Odette", "Skill", "Wing Dance Move DMG")),
        Hit("Wing_Stellar_5", 19.800, element="Cryo",                     category=ActionCategory.STELLAR_DMG,  stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG", 10), scaling_key=("Odette", "Skill", "Wing Dance Move Stellar Swirl DMG")),
    ]
)


# --- Faruzan ---
faruzan_burst = Ability(
    name="Elemental Burst",
    character="Faruzan",
    cooldown=19.0,
    talent_level=13,
    talent_type="burst_talent",
    hits=[
        Hit("Burst_Cast", 0.000, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Faruzan", "Burst", "Skill DMG", 13), attack_type=AttackType.BURST, scaling_key=("Faruzan", "Burst", "Skill DMG"))
    ]
)

faruzan_skill_cast = Ability(
    name="Skill Cast",
    character="Faruzan",
    talent_level=13,
    talent_type="skill_talent",
    hits=[
        Hit(
            "Skill Cast", 
            0.000, 
            element="Anemo", 
            elemental_app="1U", 
            category=ActionCategory.STANDARD_DMG, 
            stat_ref=StatRef.ATK, 
            motion_value=get_ability_motion_value("Faruzan", "Skill", "Skill DMG", 13), 
            attack_type=AttackType.SKILL, 
            # scaling_key is exactly (character, category, sub ability): the talent
            # LEVEL is never part of it (update_ability_talent_level resolves it).
            scaling_key=("Faruzan", "Skill", "Skill DMG")
        )
    ]
)


# TRIGGERED ABILITY. Her skill cast and her Pressurized Collapse are two different
# abilities: the cast is a plain hit that only procs the collapse when the collapse's
# own trigger conditions are met (burst cast / while her C6 window is up, 3.0s CD).
# Triggered abilities are injected by timeline.evaluate_timeline() and are listed in
# ENGINE_INTERNAL_ABILITIES, so they never appear in the field-sequence editor.
# Their FIRST hit's relative_delay IS the trigger delay: the engine always schedules
# them at trigger_time + hit.relative_delay (0.0 is a valid, explicit value).
faruzan_pressurized_collapse = Ability(
    name="Pressurized Collapse",
    character="Faruzan",
    talent_level=13,
    talent_type="skill_talent",
    hits=[
        Hit(
            "Pressurized_Collapse", 
            0.720,   # trigger delay: the collapse lands 0.72s after its trigger
            element="Anemo", 
            elemental_app="1U", 
            category=ActionCategory.STANDARD_DMG, 
            stat_ref=StatRef.ATK, 
            motion_value=get_ability_motion_value("Faruzan", "Skill", "Pressurized Collapse Vortex DMG", 13), 
            attack_type=AttackType.SKILL, 
            scaling_key=("Faruzan", "Skill", "Pressurized Collapse Vortex DMG")
        )
    ]
)

# --- Mizuki ---

mizuki_n1 = Ability(
    name="N1",
    character="Mizuki",
    cooldown=0.0,
    talent_level=10,
    talent_type="normal_talent",
    hits=[
        Hit("N1", 0.000, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Normal Attack", "1-Hit DMG", 10), attack_type=AttackType.NORMAL, scaling_key=("Mizuki", "Normal Attack", "1-Hit DMG"))
    ]
)

mizuki_charged = Ability(
    name="Charged Attack",
    character="Mizuki",
    cooldown=0.0,
    talent_level=10,
    talent_type="normal_talent",
    hits=[
        Hit("Charged Attack", 0.000, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Charged Attack", "Charged Attack DMG", 10), attack_type=AttackType.CHARGED, scaling_key=("Mizuki", "Charged Attack", "Charged Attack DMG"))
    ]
)

mizuki_pullout_13 = Ability(
    name="Mizuki Skill [13 Ticks]",
    character="Mizuki",
    cooldown=15.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Cast",   0.000, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Skill DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Skill DMG")),
        Hit("Tick1",  0.929, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick2",  1.619, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick3",  2.639, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick4",  3.300, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick5",  3.990, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick6",  4.800, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick7",  5.490, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick8",  6.269, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick9",  6.989, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick10", 7.679, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick11", 8.489, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick12", 9.179, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick13", 9.869, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
    ]
)

mizuki_pullout_2 = Ability(
    name="Mizuki Skill [2 Ticks]",
    character="Mizuki",
    cooldown=0.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Cast",  0.000, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Skill DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Skill DMG")),
        Hit("Tick1", 0.929, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick2", 1.619, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
    ]
)

mizuki_pullout_9 = Ability(
    name="Mizuki Skill [9 Ticks]",
    character="Mizuki",
    cooldown=15.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Cast",   0.000, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Skill DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Skill DMG")),
        Hit("Tick1",  0.929, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick2",  1.619, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick3",  2.639, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick4",  3.300, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick5",  3.990, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick6",  4.800, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick7",  5.490, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick8",  6.269, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick9",  6.989, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
    ]
)

mizuki_pullout_5 = Ability(
    name="Mizuki Skill [5 Ticks]",
    character="Mizuki",
    cooldown=15.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Cast",   0.000, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Skill DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Skill DMG")),
        Hit("Tick1",  0.929, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick2",  1.619, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick3",  2.639, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick4",  3.300, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick5",  3.990, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
    ]
)

mizuki_burst = Ability(
    name="Mizuki Burst",
    character="Mizuki",
    cooldown=15.0,
    talent_level=10,
    talent_type="burst_talent",
    hits=[
        # The cast hit is "Burst_Cast", NOT "Cast": the timeline enters DDS on a "Cast"
        # skill hit, so naming it "Cast" would make her burst switch the skill stance on.
        Hit("Burst_Cast", 0.000, element="Anemo", elemental_app="2U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Burst", "Skill DMG", 10), attack_type=AttackType.BURST, scaling_key=("Mizuki", "Burst", "Skill DMG")),
        Hit("Shock 1",  1.800, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Burst", "Munen Shockwave DMG", 10), attack_type=AttackType.BURST, scaling_key=("Mizuki", "Burst", "Munen Shockwave DMG")),
        Hit("Shock 2",  3.300, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Burst", "Munen Shockwave DMG", 10), attack_type=AttackType.BURST, scaling_key=("Mizuki", "Burst", "Munen Shockwave DMG")),
        Hit("Shock 3",  4.800, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Burst", "Munen Shockwave DMG", 10), attack_type=AttackType.BURST, scaling_key=("Mizuki", "Burst", "Munen Shockwave DMG")),
        Hit("Shock 4",  6.300, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Burst", "Munen Shockwave DMG", 10), attack_type=AttackType.BURST, scaling_key=("Mizuki", "Burst", "Munen Shockwave DMG")),
        Hit("Shock 5",  7.800, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Burst", "Munen Shockwave DMG", 10), attack_type=AttackType.BURST, scaling_key=("Mizuki", "Burst", "Munen Shockwave DMG")),
        Hit("Shock 6",  9.300, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Burst", "Munen Shockwave DMG", 10), attack_type=AttackType.BURST, scaling_key=("Mizuki", "Burst", "Munen Shockwave DMG")),
        Hit("Shock 7",  10.800, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Burst", "Munen Shockwave DMG", 10), attack_type=AttackType.BURST, scaling_key=("Mizuki", "Burst", "Munen Shockwave DMG")),
        Hit("Shock 8",  12.300, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Burst", "Munen Shockwave DMG", 10), attack_type=AttackType.BURST, scaling_key=("Mizuki", "Burst", "Munen Shockwave DMG")),
    ]
)

# TRIGGERED HIT TEMPLATES (not castable, so they are bare Hits and never enter
# ABILITY_REGISTRY). Their relative_delay IS the delay from the trigger: the timeline
# schedules them at trigger_time + relative_delay, so the value can be tuned here only.
mizuki_nuke_hit = Hit("Mizuki Nuke Hit", 0.500, element="Anemo", category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.EM, motion_value=10.00)
mizuki_c1_mini_nuke_hit = Hit("Mizuki C1 Mini Nuke", 0.0, element="Anemo", category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.EM, motion_value=4.00)

#Sucrose

sucrose_n1 = Ability(
    name="N1",
    character="Sucrose",
    cooldown=0.0,
    talent_level=10,
    talent_type="normal_talent",
    hits=[
        Hit("N1", 0.000, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Sucrose", "Normal Attack", "1-Hit DMG", 10), attack_type=AttackType.NORMAL, scaling_key=("Sucrose", "Normal Attack", "1-Hit DMG"))
    ]
),

sucrose_n2 = Ability(
    name="N2",
    character="Sucrose",
    cooldown=0.0,
    talent_level=10,
    talent_type="normal_talent",
    hits=[
        Hit("N2", 0.000, element="Anemo", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Sucrose", "Normal Attack", "2-Hit DMG", 10), attack_type=AttackType.NORMAL, scaling_key=("Sucrose", "Normal Attack", "2-Hit DMG"))
    ]
)

sucrose_skill = Ability(
    name="Sucrose Skill",
    character="Sucrose",
    cooldown=15.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Cast",  0.000, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Sucrose", "Skill", "Skill DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Sucrose", "Skill", "Skill DMG")),
    ]
)

sucrose_burst = Ability(
    name="Sucrose Burst",
    character="Sucrose",
    cooldown=20.0,
    talent_level=10,
    talent_type="burst_talent",
    hits=[
        Hit("DoT",  0.000, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Sucrose", "Burst", "DoT", 10), attack_type=AttackType.BURST, scaling_key=("Sucrose", "Burst", "DoT")),
        Hit("Absorption",  0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Sucrose", "Burst", "Additional Elemental DMG", 10), attack_type=AttackType.BURST, scaling_key=("Sucrose", "Burst", "Additional Elemental DMG")),
        Hit("DoT",  1.889, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Sucrose", "Burst", "DoT", 10), attack_type=AttackType.BURST, scaling_key=("Sucrose", "Burst", "DoT")),
        Hit("Absorption",  1.889, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Sucrose", "Burst", "Additional Elemental DMG", 10), attack_type=AttackType.BURST, scaling_key=("Sucrose", "Burst", "Additional Elemental DMG")),
        Hit("DoT",  3.869, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Sucrose", "Burst", "DoT", 10), attack_type=AttackType.BURST, scaling_key=("Sucrose", "Burst", "DoT")),
        Hit("Absorption",  3.869, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Sucrose", "Burst", "Additional Elemental DMG", 10), attack_type=AttackType.BURST, scaling_key=("Sucrose", "Burst", "Additional Elemental DMG")),
        Hit("DoT",  5.729, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Sucrose", "Burst", "DoT", 10), attack_type=AttackType.BURST, scaling_key=("Sucrose", "Burst", "DoT")),
        Hit("Absorption",  5.729, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Sucrose", "Burst", "Additional Elemental DMG", 10), attack_type=AttackType.BURST, scaling_key=("Sucrose", "Burst", "Additional Elemental DMG")),
    ]
)

# -- Diona ---
diona_skill_tap = Ability(
    name="Diona Skill [Tap]",
    character="Diona",
    cooldown=6.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Icy Paw [1]",  0.000, element="Cryo", elemental_app="1U",    category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Skill", "Icy Paw DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Diona", "Skill", "Icy Paw DMG")),
        Hit("Icy Paw [2]",  0.030, element="Cryo",                        category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Skill", "Icy Paw DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Diona", "Skill", "Icy Paw DMG")),
    ]
)

diona_skill_hold = Ability(
    name="Diona Skill [Hold]",
    character="Diona",
    cooldown=15.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Icy Paw [1]",  0.000, element="Cryo", elemental_app="1U",  category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Skill", "Icy Paw DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Diona", "Skill", "Icy Paw DMG")),
        Hit("Icy Paw [2]",  0.000, element="Cryo",                      category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Skill", "Icy Paw DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Diona", "Skill", "Icy Paw DMG")),
        Hit("Icy Paw [3]",  0.031, element="Cryo",                      category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Skill", "Icy Paw DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Diona", "Skill", "Icy Paw DMG")),
        Hit("Icy Paw [4]",  0.031, element="Cryo", elemental_app="1U",  category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Skill", "Icy Paw DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Diona", "Skill", "Icy Paw DMG")),
        Hit("Icy Paw [5]",  0.031, element="Cryo",                      category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Skill", "Icy Paw DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Diona", "Skill", "Icy Paw DMG"))
    ]
)

diona_burst = Ability(
    name="Diona Burst",
    character="Diona",
    cooldown=20.0,
    talent_level=10,
    talent_type="burst_talent",
    hits=[
        Hit("Burst Cast", 0.000, element="Cryo",    elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Burst", "Skill DMG", 10), attack_type=AttackType.BURST, scaling_key=("Diona", "Burst", "Skill DMG")),
        Hit("Burst Tick 1", 1.980, element="Cryo",                      category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Burst", "Continuous Field DMG", 10), attack_type=AttackType.BURST, scaling_key=("Diona", "Burst", "Continuous Field DMG")),
        Hit("Burst Tick 2", 3.931, element="Cryo",  elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Burst", "Continuous Field DMG", 10), attack_type=AttackType.BURST, scaling_key=("Diona", "Burst", "Continuous Field DMG")),
        Hit("Burst Tick 3", 5.881, element="Cryo",                      category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Burst", "Continuous Field DMG", 10), attack_type=AttackType.BURST, scaling_key=("Diona", "Burst", "Continuous Field DMG")),
        Hit("Burst Tick 4", 7.831, element="Cryo",  elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Burst", "Continuous Field DMG", 10), attack_type=AttackType.BURST, scaling_key=("Diona", "Burst", "Continuous Field DMG")),
        Hit("Burst Tick 5", 9.810, element="Cryo",                      category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Burst", "Continuous Field DMG", 10), attack_type=AttackType.BURST, scaling_key=("Diona", "Burst", "Continuous Field DMG")),
        Hit("Burst Tick 6", 11.730, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Burst", "Continuous Field DMG", 10), attack_type=AttackType.BURST, scaling_key=("Diona", "Burst", "Continuous Field DMG")),
    ]
)

# TRIGGERED ABILITY. Diona's Choice Treasures state is opened by her tap/hold skill
# hits (20s, refreshed) and every Stellar Swirl triggered by ANY character while it is
# up fires this Icy Paw volley 0.270s after the trigger (3.5s CD, measured from the
# trigger). The first hit's relative_delay IS the trigger delay; the following hits are
# their own delays from the SAME trigger. Injected by timeline.evaluate_timeline(),
# never insertable in the field-sequence editor.
diona_choice_treasures = Ability(
    name="Diona Choice Treasures",
    character="Diona",
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Choice Treasures [Tick 1]", 0.270, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Skill", "Icy Paw DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Diona", "Skill", "Icy Paw DMG")),
        Hit("Choice Treasures [Tick 2]", 0.360, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Skill", "Icy Paw DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Diona", "Skill", "Icy Paw DMG")),
        Hit("Choice Treasures [Tick 3]", 0.360, element="Cryo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Diona", "Skill", "Icy Paw DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Diona", "Skill", "Icy Paw DMG")),
    ]
    
)


def configure_field_sequence_talents(field_sequence: FieldSequence, talents: Union[str, Tuple[int, int, int], list]) -> FieldSequence:
    """
    Returns a copy of the field_sequence with ability talent levels updated according to
    the character's talent levels (Normal / Skill / Burst) mapped via talent_type.
    talents can be a string like '1/13/13' or a list/tuple of ints [na, skill, burst].
    """
    if isinstance(talents, str):
        levels = [int(p.strip()) for p in talents.split("/")]
    else:
        levels = list(talents)

    # Map the ordered int/int/int sequence to talent type nicknames
    talent_map = {
        "normal_talent": levels[0],
        "skill_talent": levels[1],
        "burst_talent": levels[2]
    }

    # Deepcopy to avoid modifying the template field_sequence
    new_field_sequence = copy.deepcopy(field_sequence)
    for call in new_field_sequence.calls:
        ability = call.ability
        # Safely obtain the correct value corresponding to the specific ability's talent_type
        target_level = talent_map.get(ability.talent_type, levels[1])
        update_ability_talent_level(ability, target_level)

    return new_field_sequence

#--- Anastasya -------------------------------------------------------------
# Her skill mirrors Odette's "dance" timing pattern: one cast hit, then ten beats
# (2.220 / 4.080 / 6.180 / 8.010 / 10.110 / 11.940 / 14.040 / 15.901 / 17.940 /
# 19.800). Each beat pairs a Palestar Crown cryo hit with its stellar swirl hit;
# the enhanced variant adds the burst's "extra stellar swirl" hit on every beat.
_ANASTASYA_BEATS = ((1, 2.220), (2, 4.080), (3, 6.180), (4, 8.010), (5, 10.110),
                    (6, 11.940), (7, 14.040), (8, 15.901), (9, 17.940), (10, 19.800))

_SKILL_TAP = ("Anastasya", "Skill", "Instantaneous Tap DMG")
_PALESTAR = ("Anastasya", "Skill", "Palestar Crown Cryo DMG")
_PALESTAR_STELLAR = ("Anastasya", "Skill", "Palestar Crown Stellar Swirl DMG")
_PALESTAR_EXTRA = ("Anastasya", "Burst", "Palestar Crown Extra Stellar Swirl DMG")
_NEW_WORLD = ("Anastasya", "Burst", "To the New World Instantaneous DMG")


def _anastasya_cast_hit() -> Hit:
    return Hit("Cast", 0.000, element="Cryo", elemental_app="1U",
               category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK,
               motion_value=get_ability_motion_value(*_SKILL_TAP, 10),
               attack_type=AttackType.SKILL, scaling_key=_SKILL_TAP)


def _anastasya_palestar_hits():
    """Palestar Crown beats on Odette's skill timings (cryo + stellar per beat).

    The "extra" stellar hit is NOT part of the ability: the timeline injects it on
    every stellar beat while her burst buff is up (see anastasya_extra_stellar).
    """
    hits = []
    for index, offset in _ANASTASYA_BEATS:
        hits.append(Hit(f"Palestar Crown {index}", offset, element="Cryo",
                        elemental_app="1U", category=ActionCategory.STANDARD_DMG,
                        stat_ref=StatRef.ATK,
                        motion_value=get_ability_motion_value(*_PALESTAR, 10),
                        attack_type=AttackType.SKILL, scaling_key=_PALESTAR))
        hits.append(Hit(f"Palestar Crown Stellar {index}", offset, element="Cryo",
                        category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK,
                        motion_value=get_ability_motion_value(*_PALESTAR_STELLAR, 10),
                        scaling_key=_PALESTAR_STELLAR))
    return hits


anastasya_tap = Ability(
    name="Skill Tap",
    character="Anastasya",
    cooldown=15.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[_anastasya_cast_hit(), *_anastasya_palestar_hits()],
)

anastasya_burst = Ability(
    name="To the New World",
    character="Anastasya",
    cooldown=15.0,
    talent_level=13,
    talent_type="burst_talent",
    hits=[
        Hit("Burst_Cast", 0.000, element="Cryo", elemental_app="1U",
            category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK,
            motion_value=get_ability_motion_value(*_NEW_WORLD, 13),
            attack_type=AttackType.BURST, scaling_key=_NEW_WORLD),
    ],
)

_TRUMPH = ("Anastasya", "Burst", "Triumph Stellar Swirl DMG")
anastasya_triumph = Ability(
    name="Triumph",
    character="Anastasya",
    cooldown=15.0,
    talent_level=13,
    talent_type="burst_talent",
    hits=[
        Hit("Triumph", 0.000, element="Cryo",
            category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK,
            motion_value=get_ability_motion_value(*_TRUMPH, 13),
            attack_type=AttackType.BURST, scaling_key=_TRUMPH),
    ],
)

# Conditional hit: injected by the timeline on every stellar beat of her skill
# while her burst buff is active. Kept as a one-hit ability so the motion value
# stays data-driven. TRIGGERED: its relative_delay is the delay after the beat.
anastasya_extra_stellar = Ability(
    name="Palestar Crown Extra Stellar",
    character="Anastasya",
    talent_level=10,
    talent_type="burst_talent",
    hits=[
        Hit("Palestar Crown Extra Stellar", 0.000, element="Cryo",
            category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.ATK,
            motion_value=get_ability_motion_value(*_PALESTAR_EXTRA, 10),
            scaling_key=_PALESTAR_EXTRA),
    ],
)

# ---------------------------------------------------------------------------
# Ability registry (read by the editors)
# ---------------------------------------------------------------------------
# Renames are translated, not dropped: exported builds/trials saved before a rename
# still reference the old display names, so build_io maps them back on load.
LEGACY_ABILITY_NAMES = {
}

# Pairs that share a display name on purpose: the engine substitutes the right variant
# (Aether's burst by Frostglow stacks, Odette's recast by her constellation), so a shared
# name is not a mistake there.
VARIANT_ABILITY_NAMES = {"Elemental Burst", "Skill Recast"}

# The UI offers exactly what exists in this module: every Ability is collected
# programmatically, so a new ability never has to be registered anywhere else.
# Field sequences are deliberately NOT here: a sequence is composition (which ability,
# cast when, how long you stay), not character data. They live in presets.py, which
# owns FIELD_SEQUENCE_REGISTRY and field_sequences_for().
def _collect_ability_registry():
    abilities = {}
    for value in list(globals().values()):
        if isinstance(value, Ability):
            abilities.setdefault(value.character, {})
            abilities[value.character].setdefault(value.name, value)
    return abilities


ABILITY_REGISTRY = _collect_ability_registry()

# Abilities the timeline injects on its own (conditional procs). They stay in
# ABILITY_REGISTRY for completeness, but must never be insertable by hand or they
# would double count.
#
# TRIGGERED vs ACTIVE: an ability that can only happen on a condition (a proc, a
# passive, a state the engine tracks) is a TRIGGERED ability. It lives here and is
# never referenced by a FieldSequence, because a sequence can only hold abilities the
# user actively casts. If one day an ability can happen BOTH ways, add two entries to
# this module: the active one (castable, in presets) and the triggered one (listed
# below), exactly like Faruzan's "Skill Cast" and "Pressurized Collapse".
#
# A triggered ability's delay is its FIRST hit's relative_delay, always read by the
# engine as `trigger_time + hit.relative_delay` (0.0 included, so the delay can be
# changed later without touching timeline.py).
ENGINE_INTERNAL_ABILITIES = {
    "Palestar Crown Extra Stellar",   # injected while Anastasya's burst buff is up
    "Triumph",                        # injected on her next swap-in after the burst
    "Pressurized Collapse",           # Faruzan: burst cast / her C6 window, 3.0s CD
    "Diona Choice Treasures",         # Diona: any Stellar Swirl in her 20s state, 3.5s CD
}


def abilities_for(character: str) -> dict:
    """{ability name: Ability} that *character* can be told to cast in a sequence."""
    return {name: ab for name, ab in ABILITY_REGISTRY.get(character, {}).items()
            if name not in ENGINE_INTERNAL_ABILITIES}


