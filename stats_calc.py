# stats_calc.py
from characters import CHARACTER_BASE_STATS, get_level_stat
from weapons import WEAPON_STATS
from artifacts import ARTIFACTS_BONUSES
from buffs import (
    CONDITIONAL_CONSTANT_BUFFS,
    CONDITIONAL_NON_CONSTANT_BUFFS,
    PERMANENT_BUFFS,
    STACK_BUFFS,
    TEAM_SHARE_BUFFS,
)
from skill_scalings import CHARACTER_SKILLS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_refinement_val(value, refinement: int):
    """Return the correct value for a given refinement rank (1-5).
    If value is a list it is assumed to be indexed [R1 … R5]."""
    if isinstance(value, list):
        return value[max(0, min(refinement - 1, len(value) - 1))]
    return value


def _target_applies(target: str, char_name: str, active_character: str,
                    caster_name=None) -> bool:
    """
    Decide whether a buff whose 'target' scope is *target* actually applies
    to the character *char_name* being evaluated.

    target scopes:
        "User" / "Self" – only the caster character
        "Party"         – every member of the party
        "Active"        – whoever is currently on-field
        "Others"        – everyone except the caster
        "<Name>"        – a specific character (e.g. "Mizuki", "Odette")
    """
    if not target or target == "Party":
        return True
    t = target.strip()
    if t in ("User", "Self"):
        return caster_name == char_name
    if t == "Active":
        return char_name == active_character
    if t == "Others":
        return caster_name != char_name
    # Named target (e.g. "Mizuki")
    return char_name == t


# ---------------------------------------------------------------------------
# build_initial_stats
# ---------------------------------------------------------------------------

def build_initial_stats(char_name, level, weapon_full_name, artifact_set_name,
                        main_stats_total, subs_total, refinement=1):
    """
    Combines Character Base + Weapon + Artifacts into a clean initial_stats
    dictionary separating base, percentages, and flats for future buff injection.

    `refinement` resolves list-valued weapon secondaries (R1..R5) via get_weapon_stat,
    e.g. Exaiphanes Blade's refinement-keyed crit_damage.
    """
    raw_char_base = CHARACTER_BASE_STATS.get(char_name, {
        "base_hp": 10000.0, "base_atk": 250.0, "base_def": 700.0,
        "crit_rate": 0.05, "crit_dmg": 0.50, "er": 1.0
    })

    # Resolve lists/scalars based on user-selected level
    char_base = {k: get_level_stat(v, level) for k, v in raw_char_base.items()}

    weapon_key  = weapon_full_name.split(" (")[0] if weapon_full_name and " (" in weapon_full_name else (weapon_full_name or "Select Weapon")
    weapon_base = WEAPON_STATS.get(weapon_key, WEAPON_STATS.get("Select Weapon", {"base_atk": 510.0}))

    artifact_bonus = ARTIFACTS_BONUSES.get(artifact_set_name, {})

    base_atk = char_base["base_atk"] + weapon_base["base_atk"]
    base_hp = char_base["base_hp"]
    base_def = char_base["base_def"]
    
    # 4. Build Percentage Pools
    hp_percent = char_base.get("hp_percent", 0.0) + get_weapon_stat(weapon_base, "hp_percent", refinement) + artifact_bonus.get("hp_percent", 0.0) + main_stats_total.get("hp_percent", 0.0) + subs_total.get("hp_percent", 0.0)
    atk_percent = char_base.get("atk_percent", 0.0) + get_weapon_stat(weapon_base, "atk_percent", refinement) + artifact_bonus.get("atk_percent", 0.0) + main_stats_total.get("atk_percent", 0.0) + subs_total.get("atk_percent", 0.0)
    def_percent = char_base.get("def_percent", 0.0) + get_weapon_stat(weapon_base, "def_percent", refinement) + artifact_bonus.get("def_percent", 0.0) + main_stats_total.get("def_percent", 0.0) + subs_total.get("def_percent", 0.0)
    
    # 5. Build Flat Pools
    hp_flat =  get_weapon_stat(weapon_base, "hp_flat", refinement) + main_stats_total.get("hp_flat", 0.0) + subs_total.get("hp_flat", 0.0)
    atk_flat = get_weapon_stat(weapon_base, "atk_flat", refinement) + main_stats_total.get("atk_flat", 0.0) + subs_total.get("atk_flat", 0.0)
    def_flat = get_weapon_stat(weapon_base, "def_flat", refinement) + subs_total.get("def_flat", 0.0)
    
    # 6. Secondary Stats (EM, Crit, ER, Bonus Dmg)
    em = char_base.get("em", 0.0) + get_weapon_stat(weapon_base, "em", refinement) + artifact_bonus.get("em", 0.0) + main_stats_total.get("em", 0.0) + subs_total.get("em", 0.0)
    crit_rate = char_base.get("crit_rate") + get_weapon_stat(weapon_base, "crit_rate", refinement) + main_stats_total.get("crit_rate", 0.0) + subs_total.get("crit_rate", 0.0)
    # Some weapons store crit damage under "crit_damage" (e.g. Exaiphanes Blade,
    # refinement-keyed). Prefer "crit_damage" if present, else fall back to "crit_dmg".
    weapon_crit_dmg = get_weapon_stat(weapon_base, "crit_dmg", refinement)
    if weapon_base.get("crit_damage", None) is not None:
        weapon_crit_dmg = get_weapon_stat(weapon_base, "crit_damage", refinement)
    crit_dmg = char_base.get("crit_dmg") + weapon_crit_dmg + main_stats_total.get("crit_dmg", 0.0) + subs_total.get("crit_dmg", 0.0)
    er = char_base.get("er") + get_weapon_stat(weapon_base, "er", refinement) + main_stats_total.get("er", 0.0) + subs_total.get("er", 0.0)
        
    physical_bonus = char_base.get("physical_bonus", 0.0) + get_weapon_stat(weapon_base, "physical_bonus", refinement) + main_stats_total.get("physical_bonus", 0.0)
    pyro_bonus = char_base.get("pyro_bonus", 0.0) + main_stats_total.get("pyro_bonus", 0.0)
    cryo_bonus = char_base.get("cryo_bonus", 0.0) + main_stats_total.get("cryo_bonus", 0.0)
    geo_bonus = char_base.get("geo_bonus", 0.0) + main_stats_total.get("geo_bonus", 0.0)
    electro_bonus = char_base.get("electro_bonus", 0.0) + main_stats_total.get("electro_bonus", 0.0)
    dendro_bonus = char_base.get("dendro_bonus", 0.0) + main_stats_total.get("dendro_bonus", 0.0)
    hydro_bonus = char_base.get("hydro_bonus", 0.0) + main_stats_total.get("hydro_bonus", 0.0)
    anemo_bonus = char_base.get("anemo_bonus", 0.0) + main_stats_total.get("anemo_bonus", 0.0)


    initial_stats = {
        "base_hp": base_hp, "base_atk": base_atk, "base_def": base_def,
        "hp_percent": hp_percent, "hp_flat": hp_flat,
        "atk_percent": atk_percent, "atk_flat": atk_flat,
        "def_percent": def_percent, "def_flat": def_flat,
        "em": em, "crit_rate": crit_rate, "crit_dmg": crit_dmg,
        "er": er,
        "physical_bonus": physical_bonus, "pyro_bonus": pyro_bonus, "cryo_bonus": cryo_bonus, "geo_bonus": geo_bonus, "electro_bonus": electro_bonus, "dendro_bonus": dendro_bonus, "hydro_bonus": hydro_bonus, "anemo_bonus": anemo_bonus
    }
    return initial_stats


# ---------------------------------------------------------------------------
# compute_card_stats  (unchanged – simple resolution for UI display)
# ---------------------------------------------------------------------------

def compute_card_stats(initial_stats, standard_mode=False):
    """
    Resolves initial_stats into formatted final values for the user-facing card.
    No buffs applied - pure gear stats.

    When standard_mode is True the build uses the 100% RV / KQM Crit-Value model:
    CR and CD are not meaningful on their own, so the card reports a single CV
    line (CV = 2*CR + CD, 1 decimal) instead of separate CR and CD rows.
    """
    card_hp = (initial_stats["base_hp"] * (1.0 + initial_stats["hp_percent"])) + initial_stats["hp_flat"]
    card_atk = (initial_stats["base_atk"] * (1.0 + initial_stats["atk_percent"])) + initial_stats["atk_flat"]
    card_def = (initial_stats["base_def"] * (1.0 + initial_stats["def_percent"])) + initial_stats["def_flat"]

    card_stats_calculated = {
        "HP": round(card_hp, 1),
        "ATK": round(card_atk, 1),
        "DEF": round(card_def, 1),
        "EM": round(initial_stats["em"], 1),
    }
    if standard_mode:
        cv = 2.0 * initial_stats.get("crit_rate", 0.0) + initial_stats.get("crit_dmg", 0.0)
        # CV is expressed in points: 1 point = 1% Crit DMG = 0.5% Crit Rate.
        card_stats_calculated["CV"] = f"{round(cv * 100, 1)}"
    else:
        card_stats_calculated["CR"] = f"{round(initial_stats['crit_rate'] * 100, 1)}%"
        card_stats_calculated["CD"] = f"{round(initial_stats['crit_dmg'] * 100, 1)}%"
    card_stats_calculated["ER"] = f"{round(initial_stats['er'] * 100, 1)}%"

    for elem in ["physical", "pyro", "cryo", "geo", "electro", "dendro", "hydro", "anemo"]:
        val = initial_stats.get(f"{elem}_bonus", 0.0)
        if val > 0.0:
            card_stats_calculated[f"{elem.capitalize()} DMG"] = f"{round(val * 100, 1)}%"

    return card_stats_calculated


# ---------------------------------------------------------------------------
# apply_permanent_buffs  (unchanged)
# ---------------------------------------------------------------------------

def apply_permanent_buffs(initial_stats, char_name):
    """
    Applies permanent character passives or quest buffs to the initial_stats
    working copy.  Called once per character before any timeline logic.
    """
    char_permanent_buffs = PERMANENT_BUFFS.get(char_name, {})
    for buff_name, stat_dict in char_permanent_buffs.items():
        for stat_key, value in stat_dict.items():
            initial_stats[stat_key] = initial_stats.get(stat_key, 0.0) + value
    return initial_stats


# ---------------------------------------------------------------------------
# get_weapon_stat helper
# ---------------------------------------------------------------------------

def get_weapon_stat(weapon_base, stat_key, refinement=1):
    val = weapon_base.get(stat_key)
    if isinstance(val, list):
        return val[refinement - 1]
    return val if val is not None else 0.0


# ---------------------------------------------------------------------------
# FLAG_TO_BUFFS  –  maps event_flag keys to lists of buff descriptors
# ---------------------------------------------------------------------------
# Buff target scope and caster rules are defined here so buffs.py remains pure data:
#   { "type":       "constant" | "non_constant" | "stack",
#     "key":        <key into the corresponding BUFF dict in buffs.py>,
#     "target":     "Party" | "Active" | "User" | "Others" | "<CharName>",
#     "caster":     <char_name of buff owner, "user" for receiver's own weapon/buff,
#                    or the sentinel "hotf_holder">,
#     "stack_flag": <event_flags key to read stack count from>  (stack only)
#   }

FLAG_TO_BUFFS = {
    # ---- Artifact / team-wide conditions -----------------------------------
    "vv_state": [
        {"type": "constant",     "key": "Viridescent Venerer",          "target": "Party",  "caster": None},
    ],
    "instructor_state": [
        {"type": "constant",     "key": "Instructor",                    "target": "Party",  "caster": None},
    ],
    "cryo_resonance_state": [
        {"type": "constant",     "key": "Cryo Resonance",                "target": "Party",  "caster": None},
    ],
    "hotf_state": [
        {"type": "constant",     "key": "Heart Of The Furnace (Self)",   "target": "User",   "caster": "hotf_holder"},
        {"type": "constant",     "key": "Heart Of The Furnace (Party)",  "target": "Party",  "caster": "hotf_holder"},
    ],

    # ---- Faruzan -----------------------------------------------------------
    # Buff (crit_dmg + talent-scaled anemo_bonus) is gated to ANEMO hits in the
    # timeline, and applies to the whole party (so off-field collapse hits get it).
    "faruzan_buff_state": [
        {"type": "constant",     "key": "Faruzan C6 Buff",               "target": "Party", "caster": "Faruzan"},
        {"type": "non_constant", "key": "Faruzan C6 Anemo Bonus",        "target": "Party", "caster": "Faruzan"},
    ],
    # Faruzan debuff (anemo_shred) is party-wide for the duration of the debuff window.
    "faruzan_debuff_state": [
        {"type": "constant",     "key": "Faruzan C6 Debuff",             "target": "Party", "caster": "Faruzan"},
    ],

    # ---- Aether C2 ---------------------------------------------------------
    # C2 Basic (+60 EM) arms for the active character on a skill TICK.
    # C2 Enhanced (+60 EM, cumulative) arms additionally when that active
    # character deals Stellar DMG or triggers a swirl.
    "aether_c2_state": [
        {"type": "constant",     "key": "Aether C2 Buff Initial",        "target": "Active", "caster": "Aether"},
    ],
    "aether_c2_enhanced_state": [
        {"type": "constant",     "key": "Aether C2 Buff Enhanced",       "target": "Active", "caster": "Aether"},
    ],

    # ---- Permanent / always-on dynamic buffs -------------------------------
    # These are always active and recomputed per event (e.g. Odette A4 mv_increase,
    # Odette Jubilee). A plus over conditional flags: no timeline flag needed.
    "always_on": [
        {"type": "non_constant", "key": "Odette A4",                     "target": "Self",   "caster": "Odette"},
        {"type": "non_constant", "key": "Odette_jubilee",                "target": "Party",  "caster": "Odette"},
        {"type": "non_constant", "key": "Aether A4",                     "target": "Self",   "caster": "Aether"},
        {"type": "non_constant", "key": "Aether_jubilee",                "target": "Party",  "caster": "Aether"},
    ],

    # Odette Burst: 6s self stellar_bonus buff (target Self so it only helps her).
    "odette_burst_state": [
        {"type": "non_constant", "key": "Odette Burst",                  "target": "Self",   "caster": "Odette"},
    ],

    # ---- Odette Marvelous Stacks -------------------------------------------
    "marvelous_stacks": [
        {"type": "stack",        "key": "Odette A1",                     "target": "Party",  "caster": "Odette", "stack_flag": "marvelous_stacks"},
        # C2: the holder's ATK also scales +7% per stack (only if Odette is C2).
        {"type": "stack",        "key": "Odette C2",                     "target": "Party",  "caster": "Odette", "stack_flag": "marvelous_stacks", "min_constellation": 2},
    ],

    # ---- Mizuki Dreamdrifter active (skill on-field) -----------------------
    "dreamdrifter_state": [
        {"type": "non_constant", "key": "Mizuki Skill",                  "target": "Party",  "caster": "Mizuki"},
        {"type": "non_constant", "key": "Mizuki VBTD EM Share",          "target": "Party",  "caster": "Mizuki"},
        {"type": "constant",     "key": "Mizuki C2",                     "target": "Party",  "caster": "Mizuki"},
        {"type": "non_constant", "key": "Mizuki C2 Pyro",                "target": "Party",  "caster": "Mizuki"},
        {"type": "non_constant", "key": "Mizuki C2 Hydro",               "target": "Party",  "caster": "Mizuki"},
        {"type": "non_constant", "key": "Mizuki C2 Cryo",                "target": "Party",  "caster": "Mizuki"},
        {"type": "non_constant", "key": "Mizuki C2 Electro",             "target": "Party",  "caster": "Mizuki"},
    ],
    "mizuki_a4_state": [
        {"type": "constant",     "key": "Mizuki A4",                     "target": "Mizuki", "caster": "Mizuki"},
    ],

    # ---- Weapon passive state flags ----------------------------------------
    "exaiphanes_blade_state": [
        {"type": "constant",     "key": "Exaiphanes Blade",                 "target": "User",   "caster": "user"},
    ],
    "widsith_average_state": [
        {"type": "constant",     "key": "The Widsith (Average)",             "target": "User",   "caster": "user"},
    ],
    "widsith_em_state": [
        {"type": "constant",     "key": "The Widsith (All EM)",              "target": "User",   "caster": "user"},
    ],
    "breezeborne_state": [
        {"type": "constant",     "key": "Breezeborne Refrain",               "target": "User",   "caster": "user"},
    ],
    "ttds_state": [
        {"type": "constant",     "key": "Thrilling Tales of Dragon Slayers", "target": "Active", "caster": "Sucrose"},
    ],
    "wandering_evenstar_state": [
        {"type": "non_constant", "key": "Wandering Evenstar Self",           "target": "User",   "caster": "user"},
        {"type": "non_constant", "key": "Wandering Evenstar Party",          "target": "Party",  "caster": "user"},
    ],
    "atfd_state": [
        {"type": "constant",     "key": "A Thousand Floating Dreams",        "target": "Party",  "caster": "user"},
    ],
    "noblesse_state": [
        {"type": "constant",     "key": "Noblesse Oblige",                   "target": "Party",  "caster": None},
    ],
    "tenacity_state": [
        {"type": "constant",     "key": "Tenacity Of The Millelith",         "target": "Party",  "caster": None},
    ],
    # Silver Light (sword): +1 stack per skill cast/recast, EM per stack (12s each).
    # Targets the USER (holder) via the `silver_light_stacks` stack count.
    "silver_light_stacks": [
        {"type": "stack",        "key": "Silver Light",                      "target": "User",   "caster": "user", "stack_flag": "silver_light_stacks"},
    ],
    # ---- Sucrose -----------------------------------------------------------
    "sucrose_a1_state": [
        # A1: +50 EM to non-Anemo party members for 8s after Sucrose triggers swirl.
        {"type": "constant",     "key": "Sucrose A1",                        "target": "Party",  "caster": "Sucrose", "exclude_elements": ["Anemo"]},
    ],
    # A4: 8s window sharing 20% of Sucrose's flat EM to the OTHERS.
    "sucrose_a4_state": [
        {"type": "non_constant", "key": "Sucrose A4 Share",                  "target": "Others", "caster": "Sucrose"},
    ],
    "sucrose_c6_state": [
        {"type": "constant",     "key": "Sucrose C6",                        "target": "Party",  "caster": "Sucrose"},
    ],
    "diona_c6_state": [
        {"type": "constant",     "key": "Diona C6",                          "target": "Active", "caster": "Diona"},
    ],
    "aether_a4_state": [
        {"type": "non_constant", "key": "Aether A4",                        "target": "User",   "caster": "Aether"},
    ],
    # Aether C6 is a timed (15s) stack buff: each Frostglow stack consumed by
    # Burst adds +5% party stellar_bonus (0.05/stack via STACK_BUFFS).
    "aether_c6_state": [
        {"type": "stack",        "key": "Aether C6",                        "target": "Party",  "caster": "Aether", "stack_flag": "aether_c6_stacks"},
    ],
    "odette_c2_state": [
        # C2 party shred (20s window set on her skill/burst cast), gated to C2+.
        {"type": "constant",     "key": "Odette C2",                        "target": "Party",  "caster": "Odette", "min_constellation": 2},
    ],
}


# ---------------------------------------------------------------------------
# compute_flat_em  –  generalized flat-EM basis (Mizuki C6-2/VBTD2, Sucrose A4)
# ---------------------------------------------------------------------------

def compute_flat_em(char_name, event_flags, active_character, party, char_initial_stats_map, refinement=1):
    """
    Returns a character's *flat* EM basis = base + weapon + artifact EM +
    strictly-flat EM buffs (CONSTANT and STACK buffs only).

    Percentage-derived EM sources are intentionally excluded, as they do not belong
    to the "after flat buffs, before percentage buffs" tier:
      - Mizuki VBTD2 10% self-share (non_constant)
      - Sucrose A4 20% share (non_constant)
      - Aether A4 (8% of ATK -> EM conversion)

    Percentages never feed into one another (no infinite Sucrose/Mizuki EM loop).
    Used as the basis for Mizuki's VBTD2 share & C6-2 and Sucrose's A4 share.
    """
    stats = char_initial_stats_map.get(char_name) or {}
    if not stats:
        return 0.0

    em = stats.get("em", 0.0)
    mizuki_const = (party or {}).get("Mizuki", {}).get("constellation", 0)

    for flag_key, descriptors in FLAG_TO_BUFFS.items():
        flag_val = event_flags.get(flag_key)
        if flag_val in (None, "OFF", 0, False):
            continue
        for desc in descriptors:
            btype = desc["type"]
            if btype not in ("constant", "stack"):
                continue
            bkey = desc.get("key", "")

            # Legacy name-based gates (Mizuki C1/C2/C6) check Mizuki's own const,
            # regardless of which character is being evaluated.
            if ("Mizuki C1" in bkey and mizuki_const < 1) or \
               ("Mizuki C2" in bkey and mizuki_const < 2) or \
               ("Mizuki C6" in bkey and mizuki_const < 6):
                continue
            # Generic caster gate.
            min_c = desc.get("min_constellation")
            if min_c is not None and (party or {}).get(desc.get("caster"), {}).get("constellation", 0) < int(min_c):
                continue

            if not _target_applies(desc.get("target", "Party"), char_name, active_character, desc.get("caster")):
                continue
            # Element-exclusion filter (mirrors resolve_active_buffs), e.g. Sucrose's
            # A1 never boosts Anemo chars (incl. Sucrose herself -> no feedback loop).
            excluded = desc.get("exclude_elements")
            if excluded:
                char_elem = CHARACTER_BASE_STATS.get(char_name, {}).get("element", "")
                if char_elem in excluded:
                    continue

            if btype == "constant":
                buff_def = CONDITIONAL_CONSTANT_BUFFS.get(bkey) or {}
                for stat, raw_val in buff_def.items():
                    if stat == "em":
                        em += _get_refinement_val(raw_val, refinement)
            else:  # stack
                stack_count = int(event_flags.get(desc.get("stack_flag", flag_key), 0))
                if stack_count <= 0:
                    continue
                buff_def = STACK_BUFFS.get(bkey) or {}
                for stat, raw_val in buff_def.items():
                    if stat == "em":
                        em += _get_refinement_val(raw_val, refinement) * stack_count

    return em


# ---------------------------------------------------------------------------
# resolve_active_buffs  –  full implementation
# ---------------------------------------------------------------------------

def resolve_active_buffs(
    initial_stats: dict,
    event_flags: dict,
    *,
    char_name: str = "",
    active_character: str = "",
    party: dict = None,
    char_initial_stats_map: dict = None,
    refinement: int = 1,
    # Legacy positional shim: old callers sometimes passed party/refinement positionally
    **_kwargs,
) -> dict:
    """
    Reads event_flags produced by the timeline and resolves every active buff
    from all buff dictionaries, returning a flat {stat: total_modifier} dict.

    Buff resolution order
    ---------------------
    1. CONDITIONAL_CONSTANT_BUFFS  – flat stat values, optionally per-refinement
    2. CONDITIONAL_NON_CONSTANT_BUFFS – lambda-computed values based on *initial_stats*
    3. STACK_BUFFS  – per-stack values multiplied by the stack count flag
    4. TEAM_SHARE_BUFFS  – percentage of a caster's stat shared to party members

    Parameters
    ----------
    initial_stats         : base + gear stats for this character
    event_flags           : dict of timeline state flags
    char_name             : name of the character whose stats are being built
    active_character      : who is currently on-field at this event
    party                 : {char: {constellation, weapon, artifact, …}} for
                            all party members
    char_initial_stats_map: {char_name: initial_stats} for all party members;
                            needed by TEAM_SHARE_BUFFS
    refinement            : weapon refinement (1-5) for this character
    """
    party = party or {}
    char_initial_stats_map = char_initial_stats_map or {}
    applied_buffs: dict = {}

    def add(stat, val):
        applied_buffs[stat] = applied_buffs.get(stat, 0.0) + val

    # ------------------------------------------------------------------
    # Resolve the "hotf_holder" sentinel: whoever has Heart of the Furnace
    # ------------------------------------------------------------------
    hotf_holder = next(
        (c for c, d in party.items()
         if d.get("weapon") in ("Heart of the Furnace", "Heart Of The Furnace")
         or d.get("artifact") in ("Heart of the Furnace", "Heart Of The Furnace")),
        None,
    )

    def resolve_caster(caster_field):
        if caster_field == "hotf_holder":
            return hotf_holder
        if caster_field == "user":
            return char_name
        return caster_field

    # Retrieve Mizuki party info for constellation & talent checks
    mizuki_data = party.get("Mizuki", {})
    mizuki_constellation = mizuki_data.get("constellation", 0)

    # C6 Part 1: while she is in Dreamdrifter state, every party member's
    # STELLAR damage and STELLAR reaction damage gets bonus crit (resolved as
    # dedicated stellar_crit_rate / stellar_crit_dmg stats, consumed in damage_calc).
    if event_flags.get("dreamdrifter_state") == "ON" and mizuki_constellation >= 6:
        add("stellar_crit_rate", 0.10)
        add("stellar_crit_dmg", 0.20)

    mizuki_talents = mizuki_data.get("talents") or mizuki_data.get("talent_levels", [1, 10, 1])
    if isinstance(mizuki_talents, str):
        mizuki_skill_lvl = int(mizuki_talents.split("/")[1])
    elif isinstance(mizuki_talents, (list, tuple)) and len(mizuki_talents) > 1:
        mizuki_skill_lvl = mizuki_talents[1]
    else:
        mizuki_skill_lvl = 10

    # Mizuki's flat EM basis (base + gear + strictly-flat EM adds). This
    # intentionally excludes percentage-derived EM sources (her own VBTD2 10%
    # self-share, Sucrose A4 share, Aether A4 conversion). It is the basis for
    # both VBTD2's 10% party share and Mizuki's C6-2 crit scaling.
    mizuki_flat_em = compute_flat_em(
        "Mizuki", event_flags, active_character, party, char_initial_stats_map, refinement
    )

    # Odette talent levels (skill = index 1, burst = index 2 of N/S/B config).
    odette_data = party.get("Odette", {})
    odette_talents = odette_data.get("talents") or odette_data.get("talent_levels", [1, 10, 1])
    if isinstance(odette_talents, str):
        _parts = odette_talents.split("/")
        odette_skill_lvl = int(_parts[1]) if len(_parts) > 1 else 10
        odette_burst_lvl = int(_parts[2]) if len(_parts) > 2 else 10
    elif isinstance(odette_talents, (list, tuple)) and len(odette_talents) >= 3:
        odette_skill_lvl = int(odette_talents[1])
        odette_burst_lvl = int(odette_talents[2])
    else:
        odette_skill_lvl = 10
        odette_burst_lvl = 10

    # Faruzan talent levels (skill = index 1, burst = index 2 of N/S/B config).
    faruzan_data = party.get("Faruzan", {})
    faruzan_talents = faruzan_data.get("talents") or faruzan_data.get("talent_levels", [1, 10, 1])
    if isinstance(faruzan_talents, str):
        _fp = faruzan_talents.split("/")
        faruzan_skill_lvl = int(_fp[1]) if len(_fp) > 1 else 10
        faruzan_burst_lvl = int(_fp[2]) if len(_fp) > 2 else 10
    elif isinstance(faruzan_talents, (list, tuple)) and len(faruzan_talents) >= 3:
        faruzan_skill_lvl = int(faruzan_talents[1])
        faruzan_burst_lvl = int(faruzan_talents[2])
    else:
        faruzan_skill_lvl = 10
        faruzan_burst_lvl = 10

    # ------------------------------------------------------------------
    # 1–3. Iterate over FLAG_TO_BUFFS dispatch table
    # ------------------------------------------------------------------
    for flag_key, buff_descriptors in FLAG_TO_BUFFS.items():
        if flag_key == "always_on":
            # Permanent/dynamic buffs have no event gate; always resolve them.
            active = True
        else:
            flag_val = event_flags.get(flag_key)
            # Treat "OFF", 0, None, False as inactive
            active = flag_val not in (None, "OFF", 0, False)
        if not active:
            continue

        for desc in buff_descriptors:
            btype  = desc["type"]
            bkey   = desc["key"]
            target = desc.get("target", "Party")
            caster = resolve_caster(desc.get("caster"))

            # Systematic Constellation Gatekeeping
            # Generic gate: buff only applies if its CASTER is at the required
            # constellation (e.g. Odette C2 must be C2+). Future characters can
            # declare "min_constellation" on any descriptor.
            min_c = desc.get("min_constellation")
            if min_c is not None:
                gate_const = (party or {}).get(caster, {}).get("constellation", 0) if caster else 0
                if gate_const < int(min_c):
                    continue

            # Element-exclusion filter (e.g. Sucrose A1 -> non-Anemo allies only).
            excluded = desc.get("exclude_elements")
            if excluded:
                char_elem = CHARACTER_BASE_STATS.get(char_name, {}).get("element", "")
                if char_elem in excluded:
                    continue

            # Legacy name-based gates (Mizuki C1/C2/C6).
            if "Mizuki C1" in bkey and mizuki_constellation < 1:
                continue
            if "Mizuki C2" in bkey and mizuki_constellation < 2:
                continue
            if "Mizuki C6" in bkey and mizuki_constellation < 6:
                continue

            # Check if this buff applies to char_name
            if not _target_applies(target, char_name, active_character, caster):
                continue

            # ---- 1. CONDITIONAL CONSTANT buffs ---------------------------
            if btype == "constant":
                buff_def = CONDITIONAL_CONSTANT_BUFFS.get(bkey)
                if buff_def is None:
                    continue
                for stat, raw_val in buff_def.items():
                    if stat in ("target", "caster"):
                        continue
                    add(stat, _get_refinement_val(raw_val, refinement))

            # ---- 2. CONDITIONAL NON-CONSTANT buffs (lambdas) -------------
            elif btype == "non_constant":
                buff_def = CONDITIONAL_NON_CONSTANT_BUFFS.get(bkey)
                if buff_def is None:
                    continue
                target_stat = buff_def.get("target_stat")
                if not target_stat:
                    continue

                # Whose stats are extracted to compute the bonus?
                # If the buff specifies a caster (or desc specified caster), extract that character's stats
                buff_caster = buff_def.get("caster") or caster
                resolved_buff_caster = resolve_caster(buff_caster)
                
                if resolved_buff_caster and resolved_buff_caster != char_name:
                    source_stats = char_initial_stats_map.get(resolved_buff_caster, initial_stats)
                else:
                    source_stats = initial_stats

                if bkey == "Mizuki Skill":
                    # Single source of truth lives in skill_scalings.CHARACTER_SKILLS.
                    scaling_list = CHARACTER_SKILLS["Mizuki"]["Skill"]["Elemental Mastery-Based Swirl DMG Increase"]["scaling"]
                    scaling_val = scaling_list[max(0, min(mizuki_skill_lvl - 1, len(scaling_list) - 1))]
                    factor = scaling_val / 1000.0  # swirl bonus = 4.5% of EM as a decimal (0.00045 * EM)
                    # Swirl-bonus EM basis = Mizuki's buffed FLAT EM (permanent + gear +
                    # flat buffs like Aether C2/C2E and her A4). Her OWN VBTD2 self-share
                    # does NOT feed this conversion (test note: 4.5% * 1180 * 1% = 0.531).
                    em_basis = mizuki_flat_em
                    computed = buff_def["compute"]({**source_stats, "em": em_basis}, refinement, factor)
                elif bkey == "Mizuki VBTD EM Share":
                    # VBTD2 share = 10% of Mizuki's flat EM basis
                    # ("after flat buffs, before percentage buffs").
                    computed = mizuki_flat_em * 0.10
                elif bkey == "Odette Burst":
                    # 6s self stellar_bonus buff, talent-scaled from skill_scalings.
                    od_sc = CHARACTER_SKILLS["Odette"]["Burst"]["Snow Swan's Dream Stellar Glimmer Reaction DMG Bonus"]["scaling"]
                    sv = od_sc[max(0, min(odette_burst_lvl - 1, len(od_sc) - 1))]
                    computed = sv / 100.0
                elif bkey == "Faruzan C6 Anemo Bonus":
                    # Talent-scaled party anemo_bonus from skill_scalings (burst talent).
                    fa_sc = CHARACTER_SKILLS["Faruzan"]["Burst"]["Anemo DMG Bonus"]["scaling"]
                    sv = fa_sc[max(0, min(faruzan_burst_lvl - 1, len(fa_sc) - 1))]
                    computed = sv / 100.0
                elif bkey == "Sucrose A4 Share":
                    # 20% of Sucrose's FLAT EM shared to the others (8s window).
                    # Percentage-derived EM never feeds into itself, so this basis
                    # excludes VBTD2/A4 etc. (no infinite Sucrose/Mizuki loop).
                    computed = 0.20 * compute_flat_em("Sucrose", event_flags, active_character, party, char_initial_stats_map, refinement)
                else:
                    computed = buff_def["compute"](source_stats, refinement)
                add(target_stat, computed)

            # ---- 3. STACK buffs ------------------------------------------
            elif btype == "stack":
                stack_count = int(event_flags.get(desc.get("stack_flag", flag_key), 0))
                if stack_count <= 0:
                    continue
                buff_def = STACK_BUFFS.get(bkey)
                if not buff_def:
                    continue
                for stat, raw_val_per_stack in buff_def.items():
                    if stat in ("target", "caster"):
                        continue
                    val_per_stack = _get_refinement_val(raw_val_per_stack, refinement)
                    add(stat, val_per_stack * stack_count)

    # ------------------------------------------------------------------
    # 4. TEAM_SHARE_BUFFS (e.g. Sucrose A4 Share, Mizuki Vast Share)
    # ------------------------------------------------------------------
    for buff_name, share_def in TEAM_SHARE_BUFFS.items():
        buff_caster  = share_def.get("caster")
        target_stat  = share_def.get("target_stat")
        if not target_stat:
            continue

        # The caster must be in the party
        if buff_caster not in party:
            continue

        # Target scope: Sucrose A4 is 'others', Mizuki Vast Share is 'everyone' (or Party)
        # Check by name or optional target_scope if defined
        target_scope = share_def.get("target_scope")
        if not target_scope:
            if "Others" in buff_name or "Sucrose" in buff_name:
                target_scope = "Others"
            else:
                target_scope = "Party"

        if not _target_applies(target_scope, char_name, active_character, buff_caster):
            continue

        caster_stats = char_initial_stats_map.get(buff_caster, {})
        if not caster_stats:
            continue

        shared_val = share_def["compute"](caster_stats)
        add(target_stat, shared_val)

    # Systematic C6 Part 2 application for Mizuki (always on, recomputed per event).
    # Uses her FLAT EM basis only (excludes %-derived EM sources), per design notes.
    if char_name == "Mizuki" and mizuki_constellation >= 6:
        mb = max(mizuki_flat_em - 500.0, 0.0)
        add("crit_rate", min(mb * 0.0004, 0.20))
        add("crit_dmg",  min(mb * 0.0016, 0.80))

    return applied_buffs


# ---------------------------------------------------------------------------
# build_snapshot_stats
# ---------------------------------------------------------------------------

def build_snapshot_stats(
    initial_stats: dict,
    event_flags: dict,
    party: dict = None,
    refinement: int = 1,
    *,
    char_name: str = "",
    active_character: str = "",
    char_initial_stats_map: dict = None,
) -> dict:
    """
    Returns a buffed copy of initial_stats with all active buffs applied.
    Resolution is purely additive (matches Genshin's additive stacking model).
    """
    final_stats = initial_stats.copy()

    active_buffs = resolve_active_buffs(
        initial_stats,
        event_flags,
        char_name=char_name,
        active_character=active_character,
        party=party,
        char_initial_stats_map=char_initial_stats_map,
        refinement=refinement,
    )

    for stat, val in active_buffs.items():
        final_stats[stat] = final_stats.get(stat, 0.0) + val

    return final_stats


# ---------------------------------------------------------------------------
# compute_final_stats
# ---------------------------------------------------------------------------

def compute_final_stats(snapshot_stats: dict) -> dict:
    """
    Computes final resolved values from a snapshot_stats dict.
    Returns raw unrounded decimals ready for damage calculations.
    """
    final_hp  = (snapshot_stats["base_hp"]  * (1.0 + snapshot_stats["hp_percent"]))  + snapshot_stats["hp_flat"]
    final_atk = (snapshot_stats["base_atk"] * (1.0 + snapshot_stats["atk_percent"])) + snapshot_stats["atk_flat"]
    final_def = (snapshot_stats["base_def"] * (1.0 + snapshot_stats["def_percent"])) + snapshot_stats["def_flat"]

    res = dict(snapshot_stats)
    res.update({
        "HP":             final_hp,
        "ATK":            final_atk,
        "DEF":            final_def,
        "EM":             snapshot_stats.get("em",             0.0),
        "CR":             snapshot_stats.get("crit_rate",      0.05),
        "CD":             snapshot_stats.get("crit_dmg",       0.50),
        "ER":             snapshot_stats.get("er",             1.0),
        "Physical Bonus": snapshot_stats.get("physical_bonus", 0.0),
        "Pyro Bonus":     snapshot_stats.get("pyro_bonus",     0.0),
        "Cryo Bonus":     snapshot_stats.get("cryo_bonus",     0.0),
        "Geo Bonus":      snapshot_stats.get("geo_bonus",      0.0),
        "Electro Bonus":  snapshot_stats.get("electro_bonus",  0.0),
        "Dendro Bonus":   snapshot_stats.get("dendro_bonus",   0.0),
        "Hydro Bonus":    snapshot_stats.get("hydro_bonus",    0.0),
        "Anemo Bonus":    snapshot_stats.get("anemo_bonus",    0.0),
        "Stellar Bonus":  snapshot_stats.get("stellar_bonus",  0.0),
        "Jubilee Mult":   snapshot_stats.get("jubilee_mult",   0.0),
        "Elevation Mult": snapshot_stats.get("elevation_mult", 0.0),
        "Stellar CR":     snapshot_stats.get("stellar_crit_rate", 0.0),
        "Stellar CD":     snapshot_stats.get("stellar_crit_dmg",  0.0),
    })
    return res


# ---------------------------------------------------------------------------
# compute_snapshot_card_stats
# ---------------------------------------------------------------------------

def compute_snapshot_card_stats(snapshot_stats: dict) -> dict:
    """
    Resolves snapshot_stats into formatted card strings for buff-aware UI display.
    """
    card_hp = (snapshot_stats["base_hp"] * (1.0 + snapshot_stats["hp_percent"])) + snapshot_stats["hp_flat"]
    card_atk = (snapshot_stats["base_atk"] * (1.0 + snapshot_stats["atk_percent"])) + snapshot_stats["atk_flat"]
    card_def = (snapshot_stats["base_def"] * (1.0 + snapshot_stats["def_percent"])) + snapshot_stats["def_flat"]

    formatted = {
        "HP":  round(card_hp,  1),
        "ATK": round(card_atk, 1),
        "DEF": round(card_def, 1),
        "EM":  round(snapshot_stats.get("em", 0.0), 1),
        "CR":  f"{round(snapshot_stats.get('crit_rate', 0.05) * 100, 1)}%",
        "CD":  f"{round(snapshot_stats.get('crit_dmg',  0.50) * 100, 1)}%",
        "ER":  f"{round(snapshot_stats.get('er',        1.0)  * 100, 1)}%",
    }

    for elem in ["physical", "pyro", "cryo", "geo", "electro", "dendro", "hydro", "anemo"]:
        val = snapshot_stats.get(f"{elem}_bonus", 0.0)
        if val > 0.0:
            formatted[f"{elem.capitalize()} DMG"] = f"{round(val * 100, 1)}%"

    for extra, label in [
        ("stellar_bonus",  "Stellar Bonus"),
        ("jubilee_mult",   "Jubilee Mult"),
        ("elevation_mult", "Elevation Mult"),
    ]:
        val = snapshot_stats.get(extra, 0.0)
        if val > 0.0:
            formatted[label] = f"{round(val * 100, 1)}%"

    return formatted
