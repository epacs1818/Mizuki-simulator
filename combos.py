from models import ActionCategory
from models import Hit, Ability, Combo

# ==========================================
# 3. CHARACTER ABILITIES & COMBOS
# ==========================================

# --- Aether ---
aether_n1 = Ability("N1", hits=[Hit("N1_Hit", 0.000)])
aether_n1ca = Ability("Charged Attack", hits=[Hit("N1", 0.000), Hit("C1_Hit", 0.510), Hit("C2_Hit", 0.720)])
aether_skill = Ability(
    name="Elemental Skill",
    cooldown=15.0,
    hits=[
        Hit("Skill_Initial", 0.000, "1U", element="Cryo"),
        Hit("Skill_Proc1", 3.149, "1U", element="Cryo"),
        Hit("Skill_Proc2", 6.149, "1U", element="Cryo"),
        Hit("Skill_Proc3", 9.149, "1U", element="Cryo"),
        Hit("Skill_Proc4", 12.149, "1U", element="Cryo"),
    ]
)
aether_burst = Ability(
    name="Elemental Burst",
    cooldown=18.0,
    hits=[
        Hit("Burst_Cast", 0.000, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
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
        Hit("Skill_Cast", 0.000, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_1", 2.220, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_Stellar_1", 2.220, category=ActionCategory.STELLAR_DMG),
        Hit("Wing_1", 4.080, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Wing_Stellar_1", 4.080, category=ActionCategory.STELLAR_DMG),
        Hit("Plume_2", 6.180, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_Stellar_2", 6.180, category=ActionCategory.STELLAR_DMG),
        Hit("Wing_2", 8.010, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Wing_Stellar_2", 8.010, category=ActionCategory.STELLAR_DMG),
        Hit("Plume_3", 10.110, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_Stellar_3", 10.110, category=ActionCategory.STELLAR_DMG),
        Hit("Wing_3", 11.940, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Wing_Stellar_3", 11.940, category=ActionCategory.STELLAR_DMG),
        Hit("Plume_4", 14.040, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_Stellar_4", 14.040, category=ActionCategory.STELLAR_DMG),
        Hit("Wing_4", 15.901, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Wing_Stellar_4", 15.901, category=ActionCategory.STELLAR_DMG),
        Hit("Plume_5", 17.940, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_Stellar_5", 17.940, category=ActionCategory.STELLAR_DMG),
        Hit("Wing_5", 19.800, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Wing_Stellar_5", 19.800, category=ActionCategory.STELLAR_DMG),
    ]
)
odette_recast = Ability(
    name="Skill Recast",
    cooldown=0.0,
    hits=[
        Hit("Skill_Recast1", 0.000, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Skill_Recast2", 0.180, category=ActionCategory.STANDARD_DMG),
        Hit("Skill_Recast3", 0.300, category=ActionCategory.STANDARD_DMG),
        Hit("Skill_Stellar", 0.871, category=ActionCategory.STELLAR_DMG),
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
        Hit("Burst_Cast", 0.000, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG)
    ]
)
faruzan_collapse_hit = Hit("Pressurized Collapse", relative_delay=0.0, elemental_app="1U", element="Anemo", category=ActionCategory.STANDARD_DMG)
faruzan_q = Combo("FaruzanQSwap", "Faruzan", swap_out_time=1.410)
faruzan_q.add_ability(1.200, faruzan_burst)

# --- Mizuki ---
mizuki_skill = Ability(
    name="Mizuki Skill",
    cooldown=15.0,
    hits=[
        Hit("Cast", 0.301, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick1", 1.230, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick2", 1.920, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick3", 2.940, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick4", 3.601, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick5", 4.291, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick6", 5.101, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick7", 5.791, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick8", 6.570, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick9", 7.290, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick10", 7.980, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick11", 8.790, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick12", 9.480, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick13", 10.17, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
    ]
)
mizuki_burstless_pull_out = Combo("BurstlessPullOut", "Mizuki", swap_out_time=10.0)
mizuki_burstless_pull_out.add_ability(0.000, mizuki_skill)

mizuki_sacfrag_skill = Ability(
    name="Mizuki Skill (SacFrag)",
    cooldown=0.0,
    hits=[
        Hit("Cast", 0.301, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick1", 1.230, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick2", 1.920, element="Anemo", category=ActionCategory.STANDARD_DMG),
    ]
)
mizuki_sacfrag_fill = Combo("SacFragFill", "Mizuki", swap_out_time=1.75)
mizuki_sacfrag_fill.add_ability(0.000, mizuki_sacfrag_skill)
