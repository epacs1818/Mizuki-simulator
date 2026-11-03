import copy
from typing import Dict, Tuple, Optional, Union
from models import AttackType
from models import ActionCategory
from models import StatRef
from models import Hit, Ability, FieldSequence
from skill_scalings import CHARACTER_SKILLS


def get_ability_motion_value(character: str, category: str, sub_ability: str, level: int) -> float:
    skill_entry = CHARACTER_SKILLS[character][category][sub_ability]
    
    # 1. Get the base scaled value for the specific level (Level 10 -> index 9)
    # Divided by 100 if your calculator expects decimals (e.g., 91.68% -> 0.9168)
    base_value = skill_entry["scaling"][level - 1] / 100.0
    
    # 2. Check for an optional mv_increase using .get()
    mv_increase = skill_entry.get("mv_increase")
    
    if mv_increase is not None:
        if isinstance(mv_increase, (int, float)):
            # e.g., Aether's Charged Attack (mv_increase = 1.4)
            return base_value * mv_increase
        elif isinstance(mv_increase, list):
            # e.g., Aether's Burst Frostglow bonus list pre-multiplied by 8
            bonus_value = mv_increase[level - 1] / 100.0
            return base_value * (1.0 + bonus_value)
            
    # If mv_increase is None or not present, just return the base scaled value
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

aether_ecq = FieldSequence("AetherECQ", "Aether", swap_out_time=3.631)
aether_ecq.add_ability(0.601, aether_skill)
aether_ecq.add_ability(1.2, aether_n1ca)
aether_ecq.add_ability(3.061, aether_burst_enhanced)

aether_en1 = FieldSequence("AetherEN1", "Aether", swap_out_time=1.23)
aether_en1.add_ability(0.601, aether_skill)
aether_en1.add_ability(1.2, aether_n1)

aether_cq = FieldSequence("AetherCQ", "Aether", swap_out_time=2.941)
aether_cq.add_ability(0.51, aether_n1ca)
aether_cq.add_ability(2.371, aether_burst_enhanced)

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

odette_ee = FieldSequence("OdetteEE", "Odette", swap_out_time=2.371)
odette_ee.add_ability(0.660, odette_cast)
odette_ee.add_ability(1.170, odette_recast)

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

faruzan_collapse_ability = Ability(
    name="Pressurized Collapse",
    character="Faruzan",
    talent_level=13,
    talent_type="skill_talent",
    hits=[
        Hit(
            "Pressurized_Collapse", 
            0.000, 
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

faruzan_q = FieldSequence("FaruzanQSwap", "Faruzan", swap_out_time=1.410)
faruzan_q.add_ability(1.200, faruzan_burst)

# --- Mizuki ---
mizuki_skill = Ability(
    name="Mizuki Skill",
    character="Mizuki",
    cooldown=15.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Cast",   0.301, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Skill DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Skill DMG")),
        Hit("Tick1",  1.230, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick2",  1.920, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick3",  2.940, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick4",  3.601, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick5",  4.291, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick6",  5.101, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick7",  5.791, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick8",  6.570, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick9",  7.290, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick10", 7.980, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick11", 8.790, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick12", 9.480, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick13", 10.17, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
    ]
)

mizuki_burstless_pull_out = FieldSequence("BurstlessPullOut", "Mizuki", swap_out_time=10.0)
mizuki_burstless_pull_out.add_ability(0.000, mizuki_skill)

mizuki_sacfrag_skill = Ability(
    name="Mizuki Skill (SacFrag)",
    character="Mizuki",
    cooldown=0.0,
    talent_level=10,
    talent_type="skill_talent",
    hits=[
        Hit("Cast",  0.301, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Skill DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Skill DMG")),
        Hit("Tick1", 1.230, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
        Hit("Tick2", 1.920, element="Anemo",                     category=ActionCategory.STANDARD_DMG, stat_ref=StatRef.ATK, motion_value=get_ability_motion_value("Mizuki", "Skill", "Continuous Attack DMG", 10), attack_type=AttackType.SKILL, scaling_key=("Mizuki", "Skill", "Continuous Attack DMG")),
    ]
)

mizuki_sacfrag_fill = FieldSequence("SacFragFill", "Mizuki", swap_out_time=1.75)
mizuki_sacfrag_fill.add_ability(0.000, mizuki_sacfrag_skill)

mizuki_nuke_hit = Hit("Mizuki Nuke Hit", 0.500, element="Anemo", category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.EM, motion_value=10.00)
mizuki_c1_mini_nuke_hit = Hit("Mizuki C1 Mini Nuke", 0.0, element="Anemo", category=ActionCategory.STELLAR_DMG, stat_ref=StatRef.EM, motion_value=4.00)


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
