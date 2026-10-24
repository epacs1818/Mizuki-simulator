from core import Ability, Hit, Combo, ActionCategory

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
