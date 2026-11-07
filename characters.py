LEVEL_INDEX_MAP = {60: 0, 70: 1, 80: 2, 90: 3, 95: 4, 100: 5}

def get_level_stat(stat_value, level):
    """Consults the ordered position of the base stat based on the user level. 
    If it's a scalar value, returns it as-is (constant for all levels)."""
    if isinstance(stat_value, list):
        idx = LEVEL_INDEX_MAP.get(level, 3)
        return stat_value[idx]
    return stat_value

CHARACTER_BASE_STATS = {
    "Mizuki": {
        "element": "Anemo",
        "base_hp": [8865.69, 9744.11, 11236.46, 12735.75, 13187.85, 13640.94],
        "base_atk": [149.85, 164.70, 189.92, 215.26, 239.48, 263.69],
        "base_def": [526.99, 579.20, 667.91, 757.03, 783.90, 810.83],
        "crit_rate": 0.05,
        "crit_dmg": 0.50,
        "er": 1.0,
        "em": [57.6, 57.6, 86.4, 115.2, 115.2, 115.2]
    },
    "Odette": {
        "element": "Cryo",
        "base_hp": [9036.18, 9931.50, 11452.55, 12980.67, 13441.46, 13903.27],
        "base_atk": [233.10, 256.19, 295.43, 334.85, 372.52, 410.19],
        "base_def": [547.85, 602.13, 694.35, 787.00, 814.94, 842.94],
        "crit_rate": 0.05,
        "crit_dmg": [0.692, 0.692, 0.788, 0.884, 0.884, 0.884],
        "er": 1.0
    },
    "Aether": {
        "element": "Cryo",
        "base_hp": [7648.45, 8400.68, 9637.80, 10874.91, 11250.57, 11627.14],
        "base_atk": [149.38, 164.07, 188.24, 212.40, 239.48, 266.59],
        "base_def": [480.03, 527.24, 604.88, 682.52, 706.10, 729.73],
        "crit_rate": 0.05,
        "crit_dmg": 0.50,
        "er": 1.0,
        "atk_percent": [0.12, 0.12, 0.18, 0.24, 0.24, 0.24]
    },
    "Faruzan": {
        "element": "Anemo",
        "base_hp": [6730.64, 7392.60, 8481.26, 9569.93, 9900.50, 10231.89],
        "base_atk": [138.18, 151.77, 174.12, 196.47, 221.52, 246.59],
        "base_def": [441.62, 485.06, 556.49, 627.92, 649.61, 671.35],
        "crit_rate": 0.05,
        "crit_dmg": 0.50,
        "er": 1.0,
        "atk_percent": [0.12, 0.12, 0.18, 0.24, 0.24, 0.24]
    },
    "Sucrose": {
        "element": "Anemo",
        "base_hp": [6501.18, 7140.58, 8192.13, 9243.68, 9562.99, 9883.07],
        "base_atk": [119.51, 131.26, 150.59, 169.92, 191.59, 213.27],
        "base_def": [494.43, 543.05, 623.03, 703.00, 727.28, 751.62],
        "crit_rate": 0.05,
        "crit_dmg": 0.50,
        "er": 1.0,
        "anemo_bonus": [0.12, 0.12, 0.18, 0.24, 0.24, 0.24]
    },
    "Diona": {
        "element": "Cryo",
        "base_hp": [6730.64, 7392.60, 8481.26, 9569.93, 9900.50, 10231.89],
        "base_atk": [149.38, 164.07, 188.24, 212.40, 239.48, 266.59],
        "base_def": [422.42, 463.97, 532.29, 600.62, 621.37, 642.16],
        "crit_rate": 0.05,
        "crit_dmg": 0.50,
        "er": 1.0,
        "cryo_bonus": [0.12, 0.12, 0.18, 0.24, 0.24, 0.24]
    },
    "Anastasya":{
        "element": "Cryo",
        "base_hp": [9036.18, 9931.50, 11452.55, 12980.67, 13441.46, 13903.27],
        "base_atk": [233.10, 256.19, 295.43, 356.00, 372.52, 410.19],
        "base_def": [547.85, 602.13, 694.35, 787.00, 814.94, 842.94],
        "crit_rate": [0.146, 0.146, 0.194, 0.242, 0.242, 0.242],
        "crit_dmg": 0.500,
        "er": 1.0
    }
}
# ---------------------------------------------------------------------------
# Element helpers -- used by the buff registry to gate team auras/resonances.
# ---------------------------------------------------------------------------
def get_character_element(char_name: str) -> str:
    """Return the Vision/element of a character (empty string when unknown)."""
    return CHARACTER_BASE_STATS.get(char_name, {}).get("element", "")


# Resonance requirements: element -> minimum number of matching characters.
RESONANCE_REQUIREMENTS = {
    "Cryo": 2,
}


def party_element_counts(party):
    """Count party members per element (accepts a list of names or a party dict)."""
    names = party.keys() if isinstance(party, dict) else party
    counts = {}
    for name in names:
        element = get_character_element(name)
        if element:
            counts[element] = counts.get(element, 0) + 1
    return counts


def has_element_resonance(party, element: str) -> bool:
    """True when the party has enough members of element for its resonance."""
    required = RESONANCE_REQUIREMENTS.get(element, 2)
    return party_element_counts(party).get(element, 0) >= required

