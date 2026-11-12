import re

WEAPON_STATS = {
    #Catalysts
    "The Widsith (Average)": {
        "base_atk": 510.0,
        "crit_dmg": 0.551
    },
    "The Widsith (All EM)": {
        "base_atk": 510.0,
        "crit_dmg": 0.551
    },
    "Sacrificial Fragments": {
        "base_atk": 454.0,
        "em": 221.0
    },
     "Sacrificial Jade":{
        "base_atk": 454.0,
        "crit_rate": 0.368
    },
    "Sunny Morning Sleep-In": {
        "base_atk": 542.0,
        "em": 265.0
    },
    "Starcaller's Watch": {
        "base_atk": 542.0,
        "em": [265.0 + 100.0, 265.0 + 125.0, 265.0 + 150.0, 265.0 + 175.0, 265.0 + 200.0]
    },
    # A Thousand Floating Dreams / Jade Vista: the description effect depends on the
    # PARTY COMPOSITION, so it is not a fixed value list. stats_calc.
    # apply_weapon_party_stats() reads this "party_stats" block:
    #   em_per_same                   -> holder EM per ally sharing the holder's element
    #   elem_bonus_per_other_element  -> holder's OWN element bonus per ally of a DIFFERENT element
    #   atk_percent_per_other_element -> holder ATK% per ally of a different element
    #   em_to_others                  -> flat EM granted to every other party member
    # The holder itself never counts in either ally tally.
    "A Thousand Floating Dreams":{
        "base_atk": 542.0,
        "em": 265.0,
        "party_stats": {
            "em_per_same":                  [32.0, 40.0, 48.0, 56.0, 64.0],
            "elem_bonus_per_other_element": [0.10, 0.14, 0.18, 0.22, 0.26],
            "em_to_others":                 [40.0, 42.0, 44.0, 46.0, 48.0],
        },
    },
    "Wandering Evenstar":{
        "base_atk": 510.0,
        "em": 165.0
    },
    "Thrilling Tales of Dragon Slayers":{
        "base_atk": 401.0,
        "hp_percent": 0.352
    },
    "Starsealed Edict": {
        "base_atk": 542.0,
        "crit_dmg": [0.882 + 0.240, 0.882 + 0.300, 0.882 + 0.360, 0.882 + 0.420, 0.882 + 0.480]
    },

    #Swords
    "New Bough": {
        "base_atk": 510.0,
        "crit_dmg": 0.551
    },
    "Silver Light": {
        "base_atk": 510.0,
        "atk_percent": 0.413
    },
    "Exaiphanes Blade": {
        "base_atk": 608.0,
        "crit_rate": 0.331,
        "crit_damage": [0.0, 0.42, 0.42, 0.42, 0.42]
    },
    "Whitelake Frostfeather":{
        "base_atk": 674.0,
        "crit_rate": 0.221
    },
    "Finale Of The Deep":{
        "base_atk": 565.0,
        "atk_percent": 0.276
    },
    "Azurelight":{
        "base_atk": 674.0,
        "crit_rate": 0.221,
        # Description effect is permanent: refinement-dependent ATK%.
        "atk_percent": [0.24, 0.30, 0.36, 0.42, 0.48]
    },
    "Aquila Favonia":{
        "base_atk": 674.0,
        "physical_bonus": 0.413,
        "atk_percent": [0.20, 0.25, 0.30, 0.35, 0.40]
    },

    #Bows
     "Favonius Warbow": {
        "base_atk": 454.0,
        "er": 0.613
    },
      "Sacrificial Bow": {
        "base_atk": 565.0,
        "er": 0.306
    },
     "Breezeborne Refrain":{
        "base_atk": 510.0,
        "crit_rate": 0.276,
        "er": [0.20, 0.25, 0.30, 0.35, 0.40]
    },
    "Elegy for the End":{
        "base_atk": 608.0,
        "er": 0.551,
        "em":  [60.0, 75.0, 90.0, 105.0, 120.0]
    },
    "Silverdawn":{
        "base_atk": 674.0,
        "crit_rate": 0.441
    },
    "Rainbow Serpent's Rain Bow": {
        "base_atk": 510.0,
        "er": 0.459
    },
    "Jade Vista": {
        "base_atk": 510.0,
        "crit_rate": 0.276,
        "party_stats": {
            "em_per_same":                   [64.0, 80.0, 96.0, 112.0, 128.0],
            "atk_percent_per_other_element": [0.12, 0.15, 0.18, 0.21, 0.24],
        },
    }
}


# ---------------------------------------------------------------------------
# Weapon key helpers
# ---------------------------------------------------------------------------
# Weapon labels can carry a UI refinement suffix ("Silver Light (R5)"), but a
# weapon's own name may also contain parentheses ("The Widsith (Average)").
# Only a trailing "(R<digit>)" is stripped; everything else is kept verbatim.
_REFINEMENT_SUFFIX = re.compile(r"\s*\(R\d+\)\s*$")


def resolve_weapon_key(weapon_full_name):
    """Canonical WEAPON_STATS key for a weapon label ('' -> 'Select Weapon')."""
    name = _REFINEMENT_SUFFIX.sub("", (weapon_full_name or "").strip())
    return name or "Select Weapon"


def get_weapon_entry(weapon_full_name):
    """WEAPON_STATS entry for a weapon label (empty dict when unknown)."""
    return WEAPON_STATS.get(resolve_weapon_key(weapon_full_name), {})

