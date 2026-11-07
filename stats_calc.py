# stats_calc.py
from characters import CHARACTER_BASE_STATS, get_level_stat, get_character_element
from weapons import WEAPON_STATS, resolve_weapon_key, get_weapon_entry
from artifacts import ARTIFACTS_BONUSES
from buffs import (
    CONDITIONAL_CONSTANT_BUFFS,
    CONDITIONAL_NON_CONSTANT_BUFFS,
    PERMANENT_BUFFS,
    STACK_BUFFS,
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


# Stats composed explicitly by build_initial_stats out of character + weapon +
# artifact MAIN stats + substats. Any other key found on a weapon / main / sub is
# folded generically, so unusual stats are never dropped. (Artifact SET bonuses are
# always folded generically: a set may grant any stat.)
_POOL_STATS = {
    "base_hp", "base_atk", "base_def",
    "hp_percent", "hp_flat", "atk_percent", "atk_flat", "def_percent", "def_flat",
    "em", "crit_rate", "crit_dmg", "crit_damage", "er",
    "physical_bonus", "pyro_bonus", "hydro_bonus", "cryo_bonus", "electro_bonus",
    "anemo_bonus", "geo_bonus", "dendro_bonus",
}


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

    weapon_key  = resolve_weapon_key(weapon_full_name)
    weapon_base = WEAPON_STATS.get(weapon_key, WEAPON_STATS.get("Select Weapon", {"base_atk": 510.0}))

    artifact_bonus = ARTIFACTS_BONUSES.get(artifact_set_name, {})

    base_atk = char_base["base_atk"] + weapon_base["base_atk"]
    base_hp = char_base["base_hp"]
    base_def = char_base["base_def"]
    
    # 4. Build Percentage Pools
    #    (character + weapon + artifact mains + substats; the ARTIFACT SET is folded
    #     generically in step 7 because a set may grant any stat at all)
    hp_percent = char_base.get("hp_percent", 0.0) + get_weapon_stat(weapon_base, "hp_percent", refinement) + main_stats_total.get("hp_percent", 0.0) + subs_total.get("hp_percent", 0.0)
    atk_percent = char_base.get("atk_percent", 0.0) + get_weapon_stat(weapon_base, "atk_percent", refinement) + main_stats_total.get("atk_percent", 0.0) + subs_total.get("atk_percent", 0.0)
    def_percent = char_base.get("def_percent", 0.0) + get_weapon_stat(weapon_base, "def_percent", refinement) + main_stats_total.get("def_percent", 0.0) + subs_total.get("def_percent", 0.0)
    
    # 5. Build Flat Pools
    hp_flat =  get_weapon_stat(weapon_base, "hp_flat", refinement) + main_stats_total.get("hp_flat", 0.0) + subs_total.get("hp_flat", 0.0)
    atk_flat = get_weapon_stat(weapon_base, "atk_flat", refinement) + main_stats_total.get("atk_flat", 0.0) + subs_total.get("atk_flat", 0.0)
    def_flat = get_weapon_stat(weapon_base, "def_flat", refinement) + subs_total.get("def_flat", 0.0)
    
    # 6. Secondary Stats (EM, Crit, ER, Bonus Dmg)
    em = char_base.get("em", 0.0) + get_weapon_stat(weapon_base, "em", refinement) + main_stats_total.get("em", 0.0) + subs_total.get("em", 0.0)
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

    # 7. ARTIFACT SET bonuses: a set is not limited to the pools above, it may grant
    #    element bonuses, stellar_bonus, skill/burst/charged_bonus, crit_*, er, ...
    #    so its whole dict is folded additively. These values stay in initial_stats
    #    (and in the saved party JSON) and are deliberately NOT printed on the card.
    for stat, raw_val in artifact_bonus.items():
        val = _get_refinement_val(raw_val, refinement)
        if isinstance(val, (int, float)):
            initial_stats[stat] = initial_stats.get(stat, 0.0) + val

    # 8. Residual pass for weapon / main / sub keys the pools above do not handle,
    #    so an unusual stat is never silently dropped.
    for source in (weapon_base, main_stats_total, subs_total):
        for stat, raw_val in source.items():
            if stat in _POOL_STATS:
                continue
            val = _get_refinement_val(raw_val, refinement)
            if isinstance(val, (int, float)):
                initial_stats[stat] = initial_stats.get(stat, 0.0) + val

    return initial_stats


# ---------------------------------------------------------------------------
# apply_weapon_party_stats  –  permanent, party-composition-dependent stats
# ---------------------------------------------------------------------------
PARTY_STAT_MARKER = "_party_weapon_stats"


def party_element_split(party, holder):
    """(same_element_allies, different_element_allies) for *holder*.

    The holder itself is never counted. Shared by party-composition effects:
    A Thousand Floating Dreams' permanent stats and Gilded Dreams' buff.
    """
    party = party or {}
    holder_element = get_character_element(holder)
    others = [char for char in party if char != holder]
    same = [char for char in others if get_character_element(char) == holder_element]
    different = [char for char in others if get_character_element(char) != holder_element]
    return same, different


def apply_weapon_party_stats(stats_map, party):
    """(Re)apply permanent weapon stats that depend on the PARTY COMPOSITION.

    They are permanent (they belong in initial_stats, so they show up in the card
    stats and feed every flat-EM basis), but they cannot live in WEAPON_STATS as a
    plain value because they count the OTHER party members. A weapon opts in with a
    "party_stats" block:

        em_per_other_element   holder EM per ally whose element differs from the holder's
        elem_bonus_per_same    holder's OWN element bonus per ally sharing that element
        em_to_others           flat EM granted to every other party member

    The holder is never counted in either ally tally.

    Idempotent: the previously applied delta is removed first, so the UI (card
    stats) and the timeline (simulation) can both call this without double counting.
    """
    stats_map = stats_map or {}
    party = party or {}

    # 1. Undo any contribution from a previous call.
    for stats in stats_map.values():
        previous = stats.pop(PARTY_STAT_MARKER, None)
        if previous:
            for stat, value in previous.items():
                stats[stat] = stats.get(stat, 0.0) - value

    # 2. Recompute from the current party composition.
    deltas = {char: {} for char in stats_map}

    def add(char, stat, value):
        if char in deltas and value:
            deltas[char][stat] = deltas[char].get(stat, 0.0) + value

    for holder, data in party.items():
        if holder not in stats_map:
            continue
        data = data or {}
        weapon = get_weapon_entry(data.get("weapon"))
        party_stats = weapon.get("party_stats")
        if not party_stats:
            continue

        refinement = int(data.get("refinement", 1) or 1)
        holder_element = get_character_element(holder)
        same, different = party_element_split(party, holder)

        em_per_other = _get_refinement_val(party_stats.get("em_per_other_element", 0.0), refinement)
        elem_per_same = _get_refinement_val(party_stats.get("elem_bonus_per_same", 0.0), refinement)
        em_to_others = _get_refinement_val(party_stats.get("em_to_others", 0.0), refinement)

        add(holder, "em", em_per_other * len(different))
        if holder_element:
            add(holder, f"{holder_element.lower()}_bonus", elem_per_same * len(same))
        for other in [char for char in party if char != holder]:
            add(other, "em", em_to_others)

    # 3. Write the new contribution back and remember it for the next call.
    for char, delta in deltas.items():
        if not delta:
            continue
        stats = stats_map[char]
        for stat, value in delta.items():
            stats[stat] = stats.get(stat, 0.0) + value
        stats[PARTY_STAT_MARKER] = delta

    return stats_map


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
        {"type": "non_constant", "key": "Odette_jubilee",                "target": "Party",  "caster": "Odette", "require_party": True},
        {"type": "non_constant", "key": "Aether A4",                     "target": "Self",   "caster": "Aether"},
        {"type": "non_constant", "key": "Aether_jubilee",                "target": "Party",  "caster": "Aether", "require_party": True},
        # Anastasya: jubilee passive (party) + A4 reaction-only jubilee (party).
        {"type": "non_constant", "key": "Anastasya_jubilee",             "target": "Party",  "caster": "Anastasya", "require_party": True},
        {"type": "constant",     "key": "Anastasya A4",                  "target": "Party",  "caster": "Anastasya", "require_party": True},
        # Mizuki C6 part 2: crit rate/dmg from her FLAT EM above 500, C6+ only.
        # Always recomputed (never "permanent"), because the EM basis changes per event.
        {"type": "non_constant", "key": "Mizuki C6 EM CR",               "target": "Self",   "caster": "Mizuki", "min_constellation": 6},
        {"type": "non_constant", "key": "Mizuki C6 EM CD",               "target": "Self",   "caster": "Mizuki", "min_constellation": 6},
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
    # C2 effects carry their own constellation gate, so no name-matching is needed.
    "dreamdrifter_state": [
        {"type": "non_constant", "key": "Mizuki Skill",                  "target": "Party",  "caster": "Mizuki"},
        {"type": "non_constant", "key": "Mizuki VBTD EM Share",          "target": "Party",  "caster": "Mizuki"},
        {"type": "constant",     "key": "Mizuki C2",                     "target": "Party",  "caster": "Mizuki", "min_constellation": 2},
        {"type": "non_constant", "key": "Mizuki C2 Pyro",                "target": "Party",  "caster": "Mizuki", "min_constellation": 2},
        {"type": "non_constant", "key": "Mizuki C2 Hydro",               "target": "Party",  "caster": "Mizuki", "min_constellation": 2},
        {"type": "non_constant", "key": "Mizuki C2 Cryo",                "target": "Party",  "caster": "Mizuki", "min_constellation": 2},
        {"type": "non_constant", "key": "Mizuki C2 Electro",             "target": "Party",  "caster": "Mizuki", "min_constellation": 2},
    ],
    "mizuki_a4_state": [
        {"type": "constant",     "key": "Mizuki A4",                     "target": "Mizuki", "caster": "Mizuki"},
    ],

    # ---- Weapon passive state flags ----------------------------------------
    # Only flags that timeline.evaluate_timeline() actually emits belong here.
    # Weapon / set passives whose trigger is not modelled yet are deliberately
    # NOT registered (no phantom buffs): they are tracked in
    # text/Implementation_Backlog.md and will be added together with their
    # timeline trigger. Their raw values stay in buffs.py for reference.
    #
    # "caster": "holder:<Weapon Name>" resolves to the party member equipping that
    # weapon (None if unequipped), so weapon buffs are holder-only by construction
    # and a value variant that is not equipped is skipped automatically.
    "exaiphanes_blade_state": [
        {"type": "constant",     "key": "Exaiphanes Blade",                 "target": "User",   "caster": "holder:Exaiphanes Blade"},
    ],
    # Silver Light (sword): +1 stack per skill cast/recast, EM per stack (12s each).
    # Targets the USER (holder) via the `silver_light_stacks` stack count.
    "silver_light_stacks": [
        {"type": "stack",        "key": "Silver Light",                      "target": "User",   "caster": "holder:Silver Light", "stack_flag": "silver_light_stacks"},
    ],
    # The Widsith: 10s roll buff on taking the field, 30s cooldown from the trigger.
    # Both variants share this one flag; the unequipped variant resolves to None.
    "widsith_state": [
        {"type": "constant",     "key": "The Widsith (Average)",             "target": "User",   "caster": "holder:The Widsith (Average)"},
        {"type": "constant",     "key": "The Widsith (All EM)",              "target": "User",   "caster": "holder:The Widsith (All EM)"},
    ],
    # Sacrificial Jade: passive is up while off-field; >10s on-field removes it,
    # >=5s off-field brings it back. Toggles are resolved by the timeline.
    "sacrificial_jade_state": [
        {"type": "constant",     "key": "Sacrificial Jade",                  "target": "User",   "caster": "holder:Sacrificial Jade"},
    ],
    # Sunny Morning Sleep-In: three independent self windows (swirl / skill / burst).
    "sunny_swirl_state": [
        {"type": "constant",     "key": "Sunny Morning Sleep-In Swirl",      "target": "User",   "caster": "holder:Sunny Morning Sleep-In"},
    ],
    "sunny_skill_state": [
        {"type": "constant",     "key": "Sunny Morning Sleep-In Skill",      "target": "User",   "caster": "holder:Sunny Morning Sleep-In"},
    ],
    "sunny_burst_state": [
        {"type": "constant",     "key": "Sunny Morning Sleep-In Burst",      "target": "User",   "caster": "holder:Sunny Morning Sleep-In"},
    ],
    # Wandering Evenstar: periodic 10s/12s ATK-from-flat-EM buff, stacking to 2.
    # The value is basis-scaled, so both entries are dynamic (resolved per stack).
    "evenstar_stacks": [
        {"type": "stack",        "key": "Wandering Evenstar Self",           "target": "User",   "caster": "holder:Wandering Evenstar", "stack_flag": "evenstar_stacks"},
        {"type": "stack",        "key": "Wandering Evenstar Party",          "target": "Others", "caster": "holder:Wandering Evenstar", "stack_flag": "evenstar_stacks"},
    ],
    # Thrilling Tales: the NEXT character to take the field gets ATK% for 10s.
    # The timeline tracks who that is and only flags the window while they are active.
    "ttds_state": [
        {"type": "constant",     "key": "Thrilling Tales of Dragon Slayers", "target": "Active", "caster": "holder:Thrilling Tales of Dragon Slayers"},
    ],
    # Starsealed Edict: 20s EM window opened by the holder's skill CAST, plus EM
    # stacks that grow with every stellar swirl while the window is up.
    "starsealed_state": [
        {"type": "constant",     "key": "Starsealed Edict Constant",         "target": "User",   "caster": "holder:Starsealed Edict"},
    ],
    "starsealed_stacks": [
        {"type": "stack",        "key": "Starsealed Edict Stacks",           "target": "User",   "caster": "holder:Starsealed Edict", "stack_flag": "starsealed_stacks"},
    ],
    # Whitelake Frostfeather: ATK% per stack (max 3, 8s each) and STELLAR crit DMG
    # only at the maximum 3 stacks.
    "whitlake_stacks": [
        {"type": "stack",        "key": "Whitelake Frostfeather",            "target": "User",   "caster": "holder:Whitelake Frostfeather", "stack_flag": "whitlake_stacks"},
    ],
    "whitlake_max_state": [
        {"type": "constant",     "key": "Whitelake Frostfeather (3 stacks)", "target": "User",   "caster": "holder:Whitelake Frostfeather"},
    ],
    # Finale Of The Deep: 15s ATK% window opened by a standard skill hit (10s CD).
    "finale_state": [
        {"type": "constant",     "key": "Finale Of The Deep",                "target": "User",   "caster": "holder:Finale Of The Deep"},
    ],
    # Breezeborne Refrain: 3 sigils -> party stellar_bonus for 12s.
    "breezeborne_state": [
        {"type": "constant",     "key": "Breezeborne Refrain",               "target": "Party",  "caster": "holder:Breezeborne Refrain"},
    ],
    # Elegy for the End: 4 sigils -> party ATK% + EM for 12s.
    "elegy_state": [
        {"type": "constant",     "key": "Elegy for the End",                 "target": "Party",  "caster": "holder:Elegy for the End"},
    ],
    # New Bough: ATK% + stellar_bonus per stack (max 3, inside a 12s window).
    "newbough_stacks": [
        {"type": "stack",        "key": "New Bough",                         "target": "User",   "caster": "holder:New Bough", "stack_flag": "newbough_stacks"},
    ],
    # Silverdawn: self ATK% + STELLAR crit DMG for a window that swirls/stellar
    # hits keep extending.
    "silverdawn_state": [
        {"type": "constant",     "key": "Silverdawn",                        "target": "User",   "caster": "holder:Silverdawn"},
    ],
    # --- Anastasya -----------------------------------------------------------
    # Burst cast: whole party gains stellar_bonus (talent-scaled).
    "anastasya_burst_state": [
        {"type": "non_constant", "key": "Anastasya Burst",                   "target": "Party",  "caster": "Anastasya"},
    ],
    # A1: her skill cast gives the OTHERS 16% crit DMG for 19s.
    "anastasya_a1_state": [
        {"type": "constant",     "key": "Anastasya A1",                      "target": "Others", "caster": "Anastasya"},
    ],
    # --- Artifact set buffs (phase 1) --------------------------------------
    # Instructor / VV already exist above; the rest are holder-gated with the same
    # "holder:<Set Name>" sentinel (it matches an artifact set as well as a weapon).
    "gilded_state": [
        {"type": "non_constant", "key": "Gilded Dreams ATK",                 "target": "User",   "caster": "holder:Gilded Dreams"},
        {"type": "non_constant", "key": "Gilded Dreams EM",                  "target": "User",   "caster": "holder:Gilded Dreams"},
    ],
    "noblesse_state": [
        {"type": "constant",     "key": "Noblesse Oblige",                   "target": "Party",  "caster": "holder:Noblesse Oblige"},
    ],
    "tenacity_state": [
        {"type": "constant",     "key": "Tenacity Of The Millelith",         "target": "Party",  "caster": "holder:Tenacity Of The Millelith"},
    ],
    "risingwinds_state": [
        {"type": "constant",     "key": "A Day Carved From Rising Winds",    "target": "User",   "caster": "holder:A Day Carved From Rising Winds"},
    ],
    "scarlet_state": [
        {"type": "constant",     "key": "Scarlet Proof",                     "target": "User",   "caster": "holder:Scarlet Proof"},
    ],
    "tsaritsa_state": [
        {"type": "constant",     "key": "New Tsaritsa set CR",               "target": "User",   "caster": "holder:New Tsaritsa set"},
    ],
    "tsaritsa_stellar_state": [
        {"type": "constant",     "key": "New Tsaritsa set Stellar CR",       "target": "User",   "caster": "holder:New Tsaritsa set"},
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
        # C6: party cryo_bonus for the lifetime of one burst field. The timeline
        # flag is already C6-gated; min_constellation here is defence in depth.
        {"type": "constant",     "key": "Sucrose C6",                        "target": "Party",  "caster": "Sucrose", "min_constellation": 6},
    ],
    # Aether A4 is resolved through the "always_on" table below (no timeline flag).
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

    # Refinement-keyed EM values (weapon passives) must resolve against the
    # CASTER's own refinement, not whichever character's snapshot is being built.
    refinement = (party or {}).get(char_name, {}).get("refinement", refinement)

    em = stats.get("em", 0.0)

    for flag_key, descriptors in FLAG_TO_BUFFS.items():
        flag_val = event_flags.get(flag_key)
        if flag_val in (None, "OFF", 0, False):
            continue
        for desc in descriptors:
            btype = desc["type"]
            if btype not in ("constant", "stack"):
                continue
            bkey = desc.get("key", "")

            # Generic caster gate: the buff only applies when its CASTER is at the
            # required constellation (replaces the old name-matching gates).
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
# Talent helpers  –  one generic reader for every talent-scaled buff
# ---------------------------------------------------------------------------

# Party talents are stored as "N/S/B" (or a 3-item list), e.g. "1/13/13".
_TALENT_INDEX = {"Normal": 0, "Skill": 1, "Burst": 2}


def get_talent_level(party, char_name, category="Skill", default=10):
    """Talent level of *char_name* for *category* (Normal / Skill / Burst)."""
    data = (party or {}).get(char_name) or {}
    talents = data.get("talents") or data.get("talent_levels")
    idx = _TALENT_INDEX.get(category, 1)
    if isinstance(talents, str):
        parts = talents.split("/")
        try:
            return int(parts[idx])
        except (IndexError, ValueError):
            return default
    if isinstance(talents, (list, tuple)) and len(talents) > idx:
        return int(talents[idx])
    return default


def get_talent_value(party, path, divisor=100.0):
    """CHARACTER_SKILLS[char][category][key] scaling at the current talent level,
    divided by *divisor* (100 -> percent form, 1000 -> ratio form)."""
    char, category, key = path
    scaling = CHARACTER_SKILLS[char][category][key]["scaling"]
    level = get_talent_level(party, char, category)
    return scaling[max(0, min(level - 1, len(scaling) - 1))] / divisor


# ---------------------------------------------------------------------------
# evaluate_dynamic_buff  –  the "basis" vocabulary for non-constant buffs
# ---------------------------------------------------------------------------
# buffs.CONDITIONAL_NON_CONSTANT_BUFFS is pure DATA: every entry declares what
# its value scales from instead of carrying a lambda, so the arithmetic lives in
# exactly one place (here) and a dead/broken entry cannot hide behind a closure.
#
#   basis = "em"       the caster's initial EM (base + weapon + artifacts + permanent)
#   basis = "flat_em"  the caster's FLAT EM basis (never % shares; see compute_flat_em)
#   basis = "atk"      the caster's resolved ATK from the initial stats
#   basis = "talent"   the value IS a talent scaling (ratio / floor / cap unused)
#
#   value = min(floor + ratio * max(basis - offset, 0), cap)     (cap optional)
#
# `ratio` may be a refinement list ([R1..R5]); `ratio_from_talent` derives the
# ratio from a talent scaling instead (e.g. Mizuki's swirl bonus = talent/1000).
BASIS_NAMES = ("em", "flat_em", "atk", "talent", "allies_same_element", "allies_diff_element")


def evaluate_dynamic_buff(
    descriptor,
    *,
    basis_stats=None,
    basis_char="",
    party=None,
    char_initial_stats_map=None,
    event_flags=None,
    active_character="",
    refinement=1,
):
    """Resolve one declarative non-constant buff descriptor into a flat value."""
    basis_stats = basis_stats or {}
    party = party or {}
    basis = descriptor.get("basis", "em")
    if basis not in BASIS_NAMES:
        raise ValueError(f"Unknown buff basis {basis!r} in {descriptor}")

    # A caster-owned effect (e.g. a weapon buff) is keyed by the CASTER's
    # refinement, not by the refinement of whoever's snapshot is being built.
    if basis_char in party:
        try:
            refinement = int((party[basis_char] or {}).get("refinement", refinement) or refinement)
        except (TypeError, ValueError):
            pass

    # basis = "talent": the buff value itself is a talent scaling.
    if basis == "talent":
        return get_talent_value(party, descriptor["path"],
                                descriptor.get("divisor", 100.0))

    if basis == "flat_em":
        basis_value = compute_flat_em(
            basis_char, event_flags or {}, active_character,
            party, char_initial_stats_map or {}, refinement,
        )
    elif basis in ("allies_same_element", "allies_diff_element"):
        # Party composition: how many OTHER members share / differ from the
        # caster's element (the caster itself is never counted).
        same, different = party_element_split(party, basis_char)
        basis_value = float(len(same) if basis == "allies_same_element" else len(different))
    elif basis == "atk":
        basis_value = (basis_stats.get("base_atk", 0.0)
                       * (1.0 + basis_stats.get("atk_percent", 0.0))
                       + basis_stats.get("atk_flat", 0.0))
    else:  # "em"
        basis_value = basis_stats.get("em", 0.0)

    if "ratio_from_talent" in descriptor:
        spec = descriptor["ratio_from_talent"]
        ratio = get_talent_value(party, spec["path"], spec.get("divisor", 1000.0))
    else:
        ratio = _get_refinement_val(descriptor.get("ratio", 1.0), refinement)

    value = descriptor.get("floor", 0.0) + ratio * max(
        basis_value - descriptor.get("offset", 0.0), 0.0)
    cap = descriptor.get("cap")
    return min(value, cap) if cap is not None else value


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
    1. CONDITIONAL_CONSTANT_BUFFS      – flat stat values, optionally per-refinement
    2. CONDITIONAL_NON_CONSTANT_BUFFS  – declarative, resolved by evaluate_dynamic_buff()
                                         (basis "em" / "flat_em" / "atk" / "talent")
    3. STACK_BUFFS                     – per-stack values x the stack-count flag

    Parameters
    ----------
    initial_stats         : base + gear stats for this character
    event_flags           : dict of timeline state flags
    char_name             : name of the character whose stats are being built
    active_character      : who is currently on-field at this event
    party                 : {char: {constellation, weapon, artifact, …}} for
                            all party members
    char_initial_stats_map: {char_name: initial_stats} for all party members;
                            the source of every non-constant buff's basis
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
        # "holder:<Weapon Name>" -> whoever in the party equips that weapon.
        # Returns None when nobody does, which makes every target check fail, so a
        # weapon buff can never reach a non-holder or an unequipped variant.
        if isinstance(caster_field, str) and caster_field.startswith("holder:"):
            key = resolve_weapon_key(caster_field.split(":", 1)[1])
            return next((c for c, d in party.items()
                         if resolve_weapon_key(d.get("weapon")) == key
                         or (d.get("artifact_set") or d.get("artifact")) == key), None)
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

    # NOTE: talent levels are no longer parsed per character here. Every
    # talent-scaled effect declares its path in buffs.py and is resolved by
    # get_talent_value() through evaluate_dynamic_buff().

    def basis_source(buff_def, fallback_caster):
        """(basis_char, basis_stats) for a dynamic effect descriptor.

        The basis always comes from the buff's CASTER ("user" = the character
        being evaluated, "holder:<weapon>" = whoever equips it), falling back to
        the evaluated character when that caster is not in the party.
        """
        buff_caster = buff_def.get("caster") or fallback_caster
        basis_char = resolve_caster(buff_caster)
        if basis_char not in char_initial_stats_map:
            basis_char = char_name
        return basis_char, char_initial_stats_map.get(basis_char, initial_stats)

    def caster_refinement(name):
        """Refinement of a buff's CASTER.

        Weapon passives are keyed by the HOLDER's refinement: an R5 Evenstar must
        still give its R5 value to an ally who is on R1. Falls back to the
        evaluated character's refinement when the caster is unknown.
        """
        data = (party or {}).get(name) or {}
        try:
            return int(data.get("refinement", refinement) or refinement)
        except (TypeError, ValueError):
            return refinement

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

            # Optional gate: the buff's caster must actually be in the party.
            # Passive/always_on buffs of an absent character must never leak.
            if desc.get("require_party") and caster not in (party or {}):
                continue

            # Element-exclusion filter (e.g. Sucrose A1 -> non-Anemo allies only).
            excluded = desc.get("exclude_elements")
            if excluded:
                char_elem = CHARACTER_BASE_STATS.get(char_name, {}).get("element", "")
                if char_elem in excluded:
                    continue

            # Check if this buff applies to char_name
            if not _target_applies(target, char_name, active_character, caster):
                continue

            # ---- 1. CONDITIONAL CONSTANT buffs ---------------------------
            if btype == "constant":
                buff_def = CONDITIONAL_CONSTANT_BUFFS.get(bkey)
                if buff_def is None:
                    continue
                # Weapon values are keyed by the CASTER's refinement.
                buff_ref = caster_refinement(caster)
                for stat, raw_val in buff_def.items():
                    if stat in ("target", "caster"):
                        continue
                    add(stat, _get_refinement_val(raw_val, buff_ref))

            # ---- 2. CONDITIONAL NON-CONSTANT buffs (declarative bases) ---
            elif btype == "non_constant":
                buff_def = CONDITIONAL_NON_CONSTANT_BUFFS.get(bkey)
                if buff_def is None:
                    continue
                target_stat = buff_def.get("target_stat")
                if not target_stat:
                    continue

                # Whose stats feed the basis? The buff's CASTER (see basis_source).
                basis_char, basis_stats = basis_source(buff_def, caster)

                add(target_stat, evaluate_dynamic_buff(
                    buff_def,
                    basis_stats=basis_stats,
                    basis_char=basis_char,
                    party=party,
                    char_initial_stats_map=char_initial_stats_map,
                    event_flags=event_flags,
                    active_character=active_character,
                    refinement=refinement,
                ))

            # ---- 3. STACK buffs ------------------------------------------
            elif btype == "stack":
                stack_count = int(event_flags.get(desc.get("stack_flag", flag_key), 0))
                if stack_count <= 0:
                    continue

                # 3a. Constant per-stack values (Silver Light, Aether C6, ...).
                buff_def = STACK_BUFFS.get(bkey)
                if buff_def:
                    buff_ref = caster_refinement(caster)
                    for stat, raw_val_per_stack in buff_def.items():
                        if stat in ("target", "caster"):
                            continue
                        val_per_stack = _get_refinement_val(raw_val_per_stack, buff_ref)
                        add(stat, val_per_stack * stack_count)
                    continue

                # 3b. Basis-scaled per-stack values (Wandering Evenstar): the dynamic
                # effect is resolved once, then multiplied by the stack count.
                dynamic_def = CONDITIONAL_NON_CONSTANT_BUFFS.get(bkey)
                if not dynamic_def or not dynamic_def.get("target_stat"):
                    continue
                basis_char, basis_stats = basis_source(dynamic_def, caster)
                per_stack = evaluate_dynamic_buff(
                    dynamic_def,
                    basis_stats=basis_stats,
                    basis_char=basis_char,
                    party=party,
                    char_initial_stats_map=char_initial_stats_map,
                    event_flags=event_flags,
                    active_character=active_character,
                    refinement=refinement,
                )
                add(dynamic_def["target_stat"], per_stack * stack_count)

    # NOTE: team shares (Mizuki VBTD2, Sucrose A4) and Mizuki's C6 part 2 are now
    # ordinary declarative effects (see CONDITIONAL_NON_CONSTANT_BUFFS + FLAG_TO_BUFFS
    # "always_on"), so there is no special-case code left here.
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
