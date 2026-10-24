from core import Ability, Hit, Combo, ActionCategory

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
