"""Option tables.

Single source of truth for what the widgets offer and what the save / load layer validates against (BUILD_CATALOGUE)."""

from artifacts import ARTIFACTS_BONUSES
from weapons import WEAPON_STATS

# Constants & options
CHARACTERS = ["Select Character", "Mizuki", "Aether", "Odette", "Anastasya", "Faruzan", "Sucrose", "Diona"]

LEVEL_OPTIONS = [60, 70, 80, 90, 95, 100]

CHARACTER_WEAPONS = {
    "Mizuki": [
        ("Sacrificial Fragments", [4, 5]),        
        ("The Widsith (Average)", [1, 2, 3, 4, 5]),
        ("The Widsith (All EM)", [1, 2, 3, 4, 5]),
        ("Sunny Morning Sleep-In", [1, 2, 3, 4, 5]),
        ("Sacrificial Jade", [1, 2, 3, 4, 5]),
        ("Starsealed Edict", [1, 2, 3, 4, 5]),
        ("Starcaller's Watch", [1, 2, 3, 4, 5]),
        ("A Thousand Floating Dreams", [1, 2, 3, 4, 5]),
        ("Wandering Evenstar", [1, 2, 3, 4, 5]),
        ("Thrilling Tales of Dragon Slayers", [1, 2, 3, 4, 5]),        
    ],
    "Aether": [
        ("Exaiphanes Blade", [1, 2, 3, 4, 5]),
        ("New Bough", [1, 2, 3, 4, 5]),
        ("Silver Light", [1, 2, 3, 4, 5]),        
        ("Whitelake Frostfeather", [1, 2, 3, 4, 5]),
        ("Finale Of The Deep", [1, 2, 3, 4, 5]),
        ("Azurelight", [1, 2, 3, 4, 5]),
        ("Aquila Favonia", [1, 2, 3, 4, 5]),
    ],
    "Odette": [
        ("Silver Light", [1, 2, 3, 4, 5]),
        ("New Bough", [1, 2, 3, 4, 5]),
        ("Whitelake Frostfeather", [1, 2, 3, 4, 5]),
        ("Exaiphanes Blade", [1, 2, 3, 4, 5]),        
        ("Finale Of The Deep", [1, 2, 3, 4, 5]),
        ("Azurelight", [1, 2, 3, 4, 5]),
        ("Aquila Favonia", [1, 2, 3, 4, 5]),
    ],
    "Anastasya": [
        ("Silverdawn", [1, 2, 3, 4, 5]),
        ("Breezeborne Refrain", [1, 2, 3, 4, 5]),
        ("Favonius Warbow", [1, 2, 3, 4, 5]),
        ("Sacrificial Bow", [1, 2, 3, 4, 5]),        
        ("Elegy for the End", [1, 2, 3, 4, 5]),        
        ("Rainbow Serpent's Rain Bow", [1, 2, 3, 4, 5]),
        ("Jade Vista", [1, 2, 3, 4, 5]),
    ],
    "Faruzan": [
        ("Favonius Warbow", [1, 2, 3, 4, 5]),
        ("Breezeborne Refrain", [1, 2, 3, 4, 5]),
        ("Sacrificial Bow", [1, 2, 3, 4, 5]),        
        ("Elegy for the End", [1, 2, 3, 4, 5]),
        ("Silverdawn", [1, 2, 3, 4, 5]),
        ("Rainbow Serpent's Rain Bow", [1, 2, 3, 4, 5]),
        ("Jade Vista", [1, 2, 3, 4, 5]),
    ],
    "Sucrose": [
        ("Sacrificial Fragments", [1, 2, 3, 4, 5]),
        ("A Thousand Floating Dreams", [1, 2, 3, 4, 5]),
        ("Thrilling Tales of Dragon Slayers", [1, 2, 3, 4, 5]),
        ("The Widsith (Average)", [1, 2, 3, 4, 5]),
        ("The Widsith (All EM)", [1, 2, 3, 4, 5]),        
        ("Sacrificial Jade", [1, 2, 3, 4, 5]),
        ("Sunny Morning Sleep-In", [1, 2, 3, 4, 5]),
        ("Starcaller's Watch", [1, 2, 3, 4, 5]),        
        ("Wandering Evenstar", [1, 2, 3, 4, 5]),        
        ("Starsealed Edict", [1, 2, 3, 4, 5]),
    ],
    "Diona": [
        ("Breezeborne Refrain", [1, 2, 3, 4, 5]),
        ("Favonius Warbow", [1, 2, 3, 4, 5]),
        ("Sacrificial Bow", [1, 2, 3, 4, 5]),        
        ("Elegy for the End", [1, 2, 3, 4, 5]),
        ("Silverdawn", [1, 2, 3, 4, 5]),
        ("Rainbow Serpent's Rain Bow", [1, 2, 3, 4, 5]),
        ("Jade Vista", [1, 2, 3, 4, 5]),
    ],
}

CHARACTER_CONSTELLATIONS = {
    "Select Character": ["C0"],
    "Faruzan": ["C6"],  # Only C6 available
    "Diona": ["C6"],    # Only C6 available
    "Mizuki": ["C0", "C1", "C2", "C3", "C4", "C5", "C6"],
    "Aether": ["C4", "C5", "C6"],
    "Odette": ["C0", "C1", "C2", "C3", "C4", "C5", "C6"],  # C3/C5 only change talent levels (user-entered)
    "Anastasya": ["C0", "C1", "C2", "C3", "C4", "C5", "C6"],  # C3/C5 only change talent levels (user-entered)
    "Sucrose": ["C0", "C1", "C2", "C3", "C4", "C5", "C6"],
}

CHARACTER_ARTIFACT_SETS = {
    "Select Character": ["Select Set"],
    "Mizuki": [
        "Select Set",
        "2p/2p EM",
        "Gilded Dreams",
        "Scarlet Proof",
        "Heart Of The Furnace",
        "Instructor",
        "Viridescent Venerer",
    ],
    "Odette": [
        "Select Set",
        "Heart Of The Furnace",
        "New Tsaritsa set",
        "Tenacity Of The Millelith",
        "2p/2p ATK",
        "A Day Carved From Rising Winds"
    ],
    "Anastasya": [
        "Select Set",
        "Heart Of The Furnace",
        "New Tsaritsa set",
        "2p/2p ATK",
        "A Day Carved From Rising Winds",
        "Tenacity Of The Millelith"        
    ],
    "Aether": [
        "Select Set",
        "2p/2p ATK",
        "A Day Carved From Rising Winds",
        "Heart Of The Furnace",
        "Tenacity Of The Millelith",
        "New Tsaritsa set"
    ],
    "Faruzan": [
        "Select Set",
        "Instructor",
        "Noblesse Oblige",
        "Tenacity Of The Millelith",
        "Viridescent Venerer",
    ],
    "Sucrose": [
        "Select Set",
        "Viridescent Venerer",
        "Instructor",
        "2p/2p EM",
        "Gilded Dreams",
    ],
    "Diona": [
        "Select Set",
        "Noblesse Oblige",
        "Tenacity Of The Millelith",
    ],
}

# Strict fallback for unselected placeholders (let actual missing keys crash)
WEAPON_STATS.setdefault("Select Weapon", {"base_atk": 0.0})
ARTIFACTS_BONUSES.setdefault("Select Set", {})

# Main Stat Options per piece type
SANDS_MAINS = ["ATK%", "HP%", "DEF%", "EM", "ER%"]
GOBLET_MAINS = ["ATK%", "HP%", "DEF%", "EM", "Physical Bonus%", "Pyro Bonus%", "Hydro Bonus%", "Geo Bonus%", "Anemo Bonus%", "Electro Bonus%", "Dendro Bonus%", "Cryo Bonus%"]
CIRCLET_MAINS = ["ATK%", "HP%", "DEF%", "EM", "Crit Rate%", "Crit Damage%", "Healing Bonus%"]

# Substat Options (including DEF% and Flat DEF)
SUBSTAT_OPTIONS = ["None", "Flat ATK", "Flat HP", "Flat DEF", "ATK%", "HP%", "DEF%", "Crit Rate%", "Crit Damage%", "ER%", "EM"]

# Everything the import/export layer validates widget values against. Kept here so
# build_io never has to know about the UI's own tables.
BUILD_CATALOGUE = {
    "characters": CHARACTERS,
    "levels": LEVEL_OPTIONS,
    "weapons": CHARACTER_WEAPONS,
    "constellations": CHARACTER_CONSTELLATIONS,
    "artifact_sets": CHARACTER_ARTIFACT_SETS,
    "substat_options": SUBSTAT_OPTIONS,
    "mains": {"Sands": SANDS_MAINS, "Goblet": GOBLET_MAINS, "Circlet": CIRCLET_MAINS},
    "rarities": ["5★", "4★"],
    "standards": ["Manual", "100% RV (Crit Value)", "KQM Standards (40 rolls)"],
}
