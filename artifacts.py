ARTIFACTS_BONUSES = {
    "2p/2p EM": {
        "em": 160.0
    },
    "2p/2p ATK": {
        "atk_percent": 2 * 0.180
    },
    "Gilded Dreams": {
        "em": 80.0
    },
    "Heart Of The Furnace": {
        "atk_percent": 0.180
    },
    "Instructor" : {
        "em" : 80.0
    },
    "Noblesse Oblige": {
        "burst_bonus": 0.200
    },
    "Tenacity Of The Millelith": {
        "hp_percent": 0.200
    },
    "A Day Carved From Rising Winds":{
        "atk_percent": 0.180
    },
    "Scarlet Proof": {
        "atk_percent": 0.180
    }
}

# Artifact aliases and safe defaults to prevent KeyError
ARTIFACTS_BONUSES.setdefault("Noblesse", ARTIFACTS_BONUSES.get("Noblesse Oblige", {"burst_bonus": 0.200}))
ARTIFACTS_BONUSES.setdefault("Tenacity", ARTIFACTS_BONUSES.get("Tenacity Of The Millelith", {"hp_percent": 0.200}))
ARTIFACTS_BONUSES.setdefault("Viridescent", ARTIFACTS_BONUSES.get("Viridescent Venerer", {}))
ARTIFACTS_BONUSES.setdefault("Viridescent Venerer", {})
ARTIFACTS_BONUSES.setdefault("Blizzard Strayer", {"cryo_bonus": 0.15})
ARTIFACTS_BONUSES.setdefault("Select Set", {})
ARTIFACTS_BONUSES.setdefault("None", {})
