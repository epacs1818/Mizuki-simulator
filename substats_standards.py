# substats_standards.py
"""'100% RV (Crit Value)' — auto-optimized artifact substats for carries.

When enabled for a carry, the manual substat rows are ignored and the build is
computed from per-carry averages:

  * Flower / Feather (locked Flat HP / Flat ATK mains): 7 crit + 1 utility roll.
  * Sands / Goblet take the carry's scaling stat as their MAIN, so (Genshin's
    same-stat rule) they cannot roll it as a substat -> they become pure crit
    (7 crit rolls each, no utility roll).
  * Circlet (crit main): realistic 3 crit + 3 utility rolls (the non-main crit
    substat is hard to roll well).

The carry's crit is then carried as a single Crit Value (CV = 2*CR + CD), stored
into `crit_dmg`, and the damage engine computes crit_mult from CV instead of
1 + CR*CD (see damage_calc.crit_mult_from_crit_value).

Supports (Sucrose, Faruzan) are not carries, so they get no RV option.
"""

# Average substat roll values (5-star defaults only — the standards always use
# these; 4-star pieces are not supported for auto-substats). `crit_cv` is the
# Crit Value of one crit roll (2*CR or CD); with the CR and CD rolls below, both
# equal the same CV (5★: 2*3.31% == 6.62% == CD 6.62%). Percentages are decimals.
AVG_ROLL = {
    "crit_cv": 6.62,       # Crit Value per crit roll
    "hp_percent": 0.0496,
    "atk_percent": 0.0496,
    "def_percent": 0.0620,
    "em": 19.82,
    "er": 0.0551,
    "hp_flat": 253.94,
    "atk_flat": 16.54,
    "def_flat": 19.68,
    "crit_rate": 0.0331,
    "crit_dmg": 0.0662,
}

# Substat roll budgets
NON_CIRCLET_CRIT_ROLLS = 7      # pure-crit rolls on Flower/Feather/Sands/Goblet
CIRCLET_CRIT_ROLLS = 3          # crit rolls on the Circlet (non-main crit sub)
CIRCLET_UTILITY_ROLLS = 3       # utility rolls on the Circlet
FLOWER_FEATHER_UTILITY_ROLLS = 1

# Characters that get the 100% RV option (carries). Supports (Sucrose, Faruzan)
# are excluded by design; the user can still fill their substats manually.
CARRIES = ("Aether", "Odette", "Mizuki", "Anastasya")

# Canonical main-stat values (5-star / 4-star). These mirror the app's
# STANDARD_MAIN_STATS / STANDARD_4STAR_MAIN_STATS so the auto-mains feed the same
# build_initial_stats path.
MAIN_STAT_VALUES = {
    "5★": {"hp_flat": 4780.0, "atk_flat": 311.0, "atk_percent": 0.466, "em": 186.5, "crit_dmg": 0.622},
    "4★": {"hp_flat": 3571.0, "atk_flat": 232.0, "atk_percent": 0.348, "em": 139.3, "crit_dmg": 0.464},
}

# Per-carry standards: which stat substitutes for ATK% (the "utility" stat), and
# the recommended Sands / Goblet / Circlet mains.
CARRY_STANDARDS = {
    "Aether": {"utility":       "atk_percent", "goblet_main": "atk_percent",    "circlet_main": "crit_dmg"},
    "Odette": {"utility":       "atk_percent", "goblet_main": "atk_percent",    "circlet_main": "crit_dmg"},
    "Mizuki": {"utility":       "em",          "goblet_main": "em",             "circlet_main": "crit_dmg"},
    "Anastasya": {"utility":    "atk_percent", "goblet_main": "atk_percent",    "circlet_main": "crit_dmg"},
}


def build_recommended_subs(char_name: str):
    """Return (mains_total, subs_total) for a carry under the 100% RV standard,
    always using 5-star default mains + substat rolls.

    The dicts use the same stat keys build_initial_stats() expects, so they can
    drop straight into the current stats pipeline unchanged.
    """
    std = CARRY_STANDARDS[char_name]
    mains = MAIN_STAT_VALUES["5★"]
    rolls = AVG_ROLL
    utility = std["utility"]

    # --- Main stats ----------------------------------------------------------
    # Flower (Flat HP) + Feather (Flat ATK) are always present; Sands + Goblet
    # take the utility/scaling stat; Circlet takes crit (carried as CV).
    mains_total = {
        "hp_flat": mains["hp_flat"],
        "atk_flat": mains["atk_flat"],
        "crit_dmg": mains["crit_dmg"],
    }
    if utility == "atk_percent":
        mains_total["atk_percent"] = mains["atk_percent"] * 2.0  # Sands + Goblet
    else:
        mains_total["em"] = mains["em"] * 2.0  # Sands + Goblet

    # --- Substats ------------------------------------------------------------
    crit_rolls = NON_CIRCLET_CRIT_ROLLS * 4 + CIRCLET_CRIT_ROLLS  # 7*4 + 3 = 31
    subs_total = {"crit_dmg": (crit_rolls * rolls["crit_cv"]) / 100.0}
    utility_rolls = FLOWER_FEATHER_UTILITY_ROLLS * 2 + CIRCLET_UTILITY_ROLLS  # 1*2 + 3 = 5
    if utility == "atk_percent":
        subs_total["atk_percent"] = utility_rolls * rolls["atk_percent"]
    else:
        subs_total["em"] = utility_rolls * rolls["em"]

    return mains_total, subs_total


# ---------------------------------------------------------------------------
# KQM Standards —— a more forgiving, overall-worse standard: exactly 40 rolls.
#
#   20 constant rolls: 2 of each of the available substats
#      (flat & percent HP / ATK / DEF, then EM, Crit Rate, Crit DMG, ER).
#   20 flexible rolls: chosen for the character. For carries we max crit first
#      (18 additional Crit-Value rolls), then the utility stat (2 ATK%/EM rolls).
#
# Crit is carried as a single Crit Value (folded into crit_dmg), so the same
# "100% RV" CV damage path applies. Note: treating crit as one combined CV stat
# lets the 18 flexible crit rolls coexist with "max 2 per substat" (CR/CD caps
# don't apply to a merged CV stat). The fixed 20 still look like real piece subs.
# ---------------------------------------------------------------------------
KQM_FIXED_PER_STAT = 2       # 2 of each fixed stat (10 stats -> 20 rolls)
KQM_FLEX_CRIT_ROLLS = 18     # flexible crit (CV) rolls for carries
KQM_FLEX_UTILITY_ROLLS = 2   # flexible ATK%/EM rolls for carries

_FIXED_FLAT = ("hp_flat", "atk_flat", "def_flat")
_FIXED_PCT = ("hp_percent", "atk_percent", "def_percent")


def build_kqm_subs(char_name: str) -> dict:
    """Substats for the KQM Standards 40-roll build (carries only), using 5-star
    default rolls.

    Returns a `subs_total` dict in the same stat keys `build_initial_stats`
    expects. Mains are left to the user's selection (only substats are locked).
    """
    std = CARRY_STANDARDS[char_name]
    utility = std["utility"]
    rolls = AVG_ROLL

    subs = {}
    # Fixed 20: flat + percent HP/ATK/DEF, EM, ER.
    for k in _FIXED_FLAT:
        subs[k] = rolls[k] * KQM_FIXED_PER_STAT
    for k in _FIXED_PCT:
        subs[k] = rolls[k] * KQM_FIXED_PER_STAT
    subs["em"] = rolls["em"] * KQM_FIXED_PER_STAT
    subs["er"] = rolls["er"] * KQM_FIXED_PER_STAT

    # Crit: the 4 fixed CR/CD rolls + the 18 flexible CV rolls, all as Crit Value.
    total_cv = (4 + KQM_FLEX_CRIT_ROLLS) * rolls["crit_cv"]
    subs["crit_dmg"] = total_cv / 100.0

    # Flexible utility rolls (2).
    if utility == "atk_percent":
        subs["atk_percent"] = subs.get("atk_percent", 0.0) + rolls["atk_percent"] * KQM_FLEX_UTILITY_ROLLS
    else:
        subs["em"] = subs.get("em", 0.0) + rolls["em"] * KQM_FLEX_UTILITY_ROLLS

    return subs

# UI labels for locked main stats (mirrors the app selectbox wording).
_MAIN_LABELS = {
    "hp_flat": "Flat HP",
    "atk_flat": "Flat ATK",
    "atk_percent": "ATK%",
    "em": "EM",
    "crit_dmg": "Crit Damage%",
}


def build_standard_mains(char_name: str) -> dict:
    """Mains shared by every standard (100% RV and KQM): flat HP + flat ATK,
    the carry recommended Sands/Goblet and a Crit Damage% circlet."""
    return build_recommended_subs(char_name)[0]


def standard_piece_mains(char_name: str) -> dict:
    """Locked main-stat labels per piece, for the artifact UI."""
    std = CARRY_STANDARDS[char_name]
    return {
        "Flower": "Flat HP",
        "Feather": "Flat ATK",
        "Sands": _MAIN_LABELS[std["utility"]],
        "Goblet": _MAIN_LABELS.get(std["goblet_main"], "ATK%"),
        "Circlet": _MAIN_LABELS.get(std["circlet_main"], "Crit Damage%"),
    }


def build_kqm_build(char_name: str):
    """(mains_total, subs_total) for the KQM standard. Mains are locked to the
    same recommended set as 100% RV because mains stop mattering once a
    standard is selected."""
    return build_standard_mains(char_name), build_kqm_subs(char_name)

