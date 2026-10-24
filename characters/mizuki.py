from core import Ability, Hit, Combo, ActionCategory

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
