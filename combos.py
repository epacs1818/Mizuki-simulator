from models import AttackType
from models import ActionCategory
from models import Hit, Ability, Combo

# ==========================================
# 3. CHARACTER ABILITIES & COMBOS
# ==========================================

# --- Aether ---
aether_n1 = Ability("N1", hits=[Hit("N1_Hit", 0.000, element="Physical", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.NORMAL)])
aether_n1ca = Ability(
    "Charged Attack", hits=[
        Hit("N1", 0.000, element="Physical", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.NORMAL),
        Hit("C1_Hit", 0.510, element="Cryo", category=ActionCategory.STELLAR_DMG),
        Hit("C2_Hit", 0.720, element="Cryo", category=ActionCategory.STELLAR_DMG)
        ])
aether_skill = Ability(
    name="Elemental Skill",
    cooldown=15.0,
    hits=[
        Hit("Skill_Initial", 0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Proc1",   3.149, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Proc2",   3.329, element="Cryo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Proc3",   6.030, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Proc4",   6.269, element="Cryo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Proc5",   8.969, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Proc6",   9.179, element="Cryo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Proc7",  11.880, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Proc8",  12.090, element="Cryo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Proc9",  14.880, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Proc10", 15.090, element="Cryo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
    ]
)
aether_burst = Ability(
    name="Elemental Burst",
    cooldown=15.0,
    hits=[
        Hit("Burst_Cast",  0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STELLAR_DMG),
        Hit("Burst_Tick1", 0.550, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
        Hit("Burst_Tick2", 0.550, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
        Hit("Burst_Tick3", 0.660, element="Cryo", elemental_app="1U", category=ActionCategory.STELLAR_DMG),
        Hit("Burst_Tick4", 0.780, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
    ]
)

aether_en1 = Combo("AetherEN1", "Aether", swap_out_time=4.0)
aether_en1.add_ability(0.000, aether_skill)
aether_en1.add_ability(1.2, aether_n1)

aether_cq = Combo("AetherCQ", "Aether", swap_out_time=2.941)
aether_cq.add_ability(0.51, aether_n1ca)
aether_cq.add_ability(2.371, aether_burst)

# --- Odette ---
odette_cast = Ability(
    name="Skill Cast",
    cooldown=15.0,
    hits=[
        Hit("Cast",            0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Plume_1",         2.220, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Plume_Stellar_1", 2.220, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
        Hit("Wing_1",          4.080, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Wing_Stellar_1",  4.080, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
        Hit("Plume_2",         6.180, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Plume_Stellar_2", 6.180, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
        Hit("Wing_2",          8.010, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Wing_Stellar_2",  8.010, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
        Hit("Plume_3",        10.110, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Plume_Stellar_3",10.110, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
        Hit("Wing_3",         11.940, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Wing_Stellar_3", 11.940, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
        Hit("Plume_4",        14.040, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Plume_Stellar_4",14.040, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
        Hit("Wing_4",         15.901, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Wing_Stellar_4", 15.901, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
        Hit("Plume_5",        17.940, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Plume_Stellar_5",17.940, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
        Hit("Wing_5",         19.800, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Wing_Stellar_5", 19.800, element="Cryo",                     category=ActionCategory.STELLAR_DMG),
    ]
)
odette_recast = Ability(
    name="Skill Recast",
    cooldown=0.0,
    hits=[
        Hit("Skill_Recast1", 0.000, element="Cryo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Recast2", 0.180, element="Cryo", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Recast3", 0.300, element="Cryo", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Skill_Stellar", 0.871, element="Cryo", category=ActionCategory.STELLAR_DMG),
    ]
)
odette_ee = Combo("OdetteEE", "Odette", swap_out_time=2.371)
odette_ee.add_ability(0.660, odette_cast)
odette_ee.add_ability(1.170, odette_recast)

# --- Faruzan ---
faruzan_burst = Ability(
    name="Elemental Burst",
    cooldown=19.0,
    hits=[
        Hit("Burst_Cast", 0.000, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.BURST)
    ]
)
faruzan_collapse_hit = Hit("Pressurized Collapse", 0.0, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL)
faruzan_q = Combo("FaruzanQSwap", "Faruzan", swap_out_time=1.410)
faruzan_q.add_ability(1.200, faruzan_burst)

# --- Mizuki ---
mizuki_skill = Ability(
    name="Mizuki Skill",
    cooldown=15.0,
    hits=[
        Hit("Cast",   0.301, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick1",  1.230, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick2",  1.920, element="Anemo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick3",  2.940, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick4",  3.601, element="Anemo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick5",  4.291, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick6",  5.101, element="Anemo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick7",  5.791, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick8",  6.570, element="Anemo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick9",  7.290, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick10", 7.980, element="Anemo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick11", 8.790, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick12", 9.480, element="Anemo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick13", 10.17, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
    ]
)
mizuki_burstless_pull_out = Combo("BurstlessPullOut", "Mizuki", swap_out_time=10.0)
mizuki_burstless_pull_out.add_ability(0.000, mizuki_skill)

mizuki_sacfrag_skill = Ability(
    name="Mizuki Skill (SacFrag)",
    cooldown=0.0,
    hits=[
        Hit("Cast",  0.301, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick1", 1.230, element="Anemo", elemental_app="1U", category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
        Hit("Tick2", 1.920, element="Anemo",                     category=ActionCategory.STANDARD_DMG, attack_type=AttackType.SKILL),
    ]
)
mizuki_sacfrag_fill = Combo("SacFragFill", "Mizuki", swap_out_time=1.75)
mizuki_sacfrag_fill.add_ability(0.000, mizuki_sacfrag_skill)
