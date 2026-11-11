# buff_registry.py
"""Central catalogue of every optional party / gear effect the timeline flags.

timeline.evaluate_timeline() writes one audit key per effect into each event
(e.g. vv_state).  This module maps each key to a stable, technical label plus
the owner that must be present for the effect to exist at all:

    key                raw event key
    label              technical table header (e.g. "Mizuki DDS")
    group              Character | Weapon | Artifact | Team
    owner              character / weapon / artifact-set / resonance name
    min_constellation  minimum owner constellation (0 = always available)
    team_requirement   ("element", "Cryo", 2) for resonance auras

Buff columns are ordered characters (party order, then registry order), then
weapons, then artifacts, then team auras.  visible_buffs() drops every effect
whose owner is not equipped, so a table only shows effects that exist in the party.
"""

from characters import get_character_element, party_element_counts


GROUP_ORDER = ("Character", "Weapon", "Artifact", "Team")

BUFFS = [
    # --- Characters --------------------------------------------------------
    {"key": "dreamdrifter_state", "label": "Mizuki DDS", "group": "Character", "owner": "Mizuki"},
    {"key": "mizuki_a4_state", "label": "Mizuki A4 EM", "group": "Character", "owner": "Mizuki"},
    {"key": "vbtd_state", "label": "Mizuki VBTD EM", "group": "Character", "owner": "Mizuki"},
    {"key": "c1_debuff_state", "label": "Mizuki C1 Shred", "group": "Character", "owner": "Mizuki", "min_constellation": 1},
    {"key": "faruzan_buff_state", "label": "Faruzan C6 CD (Anemo)", "group": "Character", "owner": "Faruzan", "min_constellation": 6},
    {"key": "faruzan_debuff_state", "label": "Faruzan C6 Anemo Shred", "group": "Character", "owner": "Faruzan", "min_constellation": 6},
    {"key": "aether_c2_state", "label": "Aether C2 EM", "group": "Character", "owner": "Aether", "min_constellation": 2},
    {"key": "aether_c2_enhanced_state", "label": "Aether C2 EM (Amp)", "group": "Character", "owner": "Aether", "min_constellation": 2},
    {"key": "frostglow_stacks", "label": "Aether Frostglow", "group": "Character", "owner": "Aether"},
    {"key": "aether_c6_state", "label": "Aether C6 Stellar", "group": "Character", "owner": "Aether", "min_constellation": 6},
    {"key": "marvelous_stacks", "label": "Odette Marvelous", "group": "Character", "owner": "Odette"},
    {"key": "odette_shadow_state", "label": "Odette Shadow", "group": "Character", "owner": "Odette"},
    {"key": "odette_ssd_state", "label": "Odette SSD", "group": "Character", "owner": "Odette"},
    {"key": "odette_c2_state", "label": "Odette C2 Shred", "group": "Character", "owner": "Odette", "min_constellation": 2},
    {"key": "sucrose_a1_state", "label": "Sucrose A1 EM", "group": "Character", "owner": "Sucrose"},
    {"key": "sucrose_a4_state", "label": "Sucrose A4 EM", "group": "Character", "owner": "Sucrose"},
    {"key": "sucrose_c6_state", "label": "Sucrose C6 Cryo DMG", "group": "Character", "owner": "Sucrose", "min_constellation": 6},
    {"key": "anastasya_burst_state", "label": "Anastasya Burst Stellar", "group": "Character", "owner": "Anastasya"},
    {"key": "anastasya_accolades_state", "label": "Anastasya Accolades", "group": "Character", "owner": "Anastasya"},
    {"key": "anastasya_sealed_state", "label": "Anastasya Sealed", "group": "Character", "owner": "Anastasya"},
    {"key": "anastasya_love_state", "label": "Anastasya Love", "group": "Character", "owner": "Anastasya", "min_constellation": 2},
    {"key": "anastasya_a4_state", "label": "Anastasya A4 Jubilee", "group": "Character", "owner": "Anastasya"},
    {"key": "anastasya_triumph_ready", "label": "Anastasya Triumph", "group": "Character", "owner": "Anastasya"},
    {"key": "diona_ct_state", "label": "Diona Choice Treasures", "group": "Character", "owner": "Diona"},
    {"key": "diona_c6_state", "label": "Diona C6 Buff", "group": "Character", "owner": "Diona", "min_constellation": 6},
    # --- Weapons -----------------------------------------------------------
    {"key": "exaiphanes_blade_state", "label": "Exaiphanes ATK%", "group": "Weapon", "owner": "Exaiphanes Blade"},
    {"key": "silver_light_stacks", "label": "Silver Light EM Stacks", "group": "Weapon", "owner": "Silver Light"},
    # Widsith: both variants share one flag, so the column exists for either one.
    {"key": "widsith_state", "label": "Widsith Buff", "group": "Weapon",
     "owner": ("The Widsith (Average)", "The Widsith (All EM)")},
    {"key": "sacrificial_jade_state", "label": "Sacrificial Jade", "group": "Weapon", "owner": "Sacrificial Jade"},
    {"key": "sunny_swirl_state", "label": "Sunny Swirl EM", "group": "Weapon", "owner": "Sunny Morning Sleep-In"},
    {"key": "sunny_skill_state", "label": "Sunny Skill EM", "group": "Weapon", "owner": "Sunny Morning Sleep-In"},
    {"key": "sunny_burst_state", "label": "Sunny Burst EM", "group": "Weapon", "owner": "Sunny Morning Sleep-In"},
    {"key": "evenstar_stacks", "label": "Evenstar Stacks", "group": "Weapon", "owner": "Wandering Evenstar"},
    {"key": "ttds_state", "label": "TTDS ATK%", "group": "Weapon", "owner": "Thrilling Tales of Dragon Slayers"},
    {"key": "starsealed_state", "label": "Starsealed EM", "group": "Weapon", "owner": "Starsealed Edict"},
    {"key": "starsealed_stacks", "label": "Starsealed Stacks", "group": "Weapon", "owner": "Starsealed Edict"},
    {"key": "whitlake_stacks", "label": "Whitelake Stacks", "group": "Weapon", "owner": "Whitelake Frostfeather"},
    {"key": "whitlake_max_state", "label": "Whitelake 3-Stack Crit", "group": "Weapon", "owner": "Whitelake Frostfeather"},
    {"key": "finale_state", "label": "Finale ATK%", "group": "Weapon", "owner": "Finale Of The Deep"},
    {"key": "breezeborne_sigils", "label": "Breezeborne Sigils", "group": "Weapon", "owner": "Breezeborne Refrain"},
    {"key": "breezeborne_state", "label": "Breezeborne Buff", "group": "Weapon", "owner": "Breezeborne Refrain"},
    {"key": "elegy_sigils", "label": "Elegy Sigils", "group": "Weapon", "owner": "Elegy for the End"},
    {"key": "elegy_state", "label": "Elegy Buff", "group": "Weapon", "owner": "Elegy for the End"},
    {"key": "newbough_stacks", "label": "New Bough Stacks", "group": "Weapon", "owner": "New Bough"},
    {"key": "silverdawn_state", "label": "Silverdawn Buff", "group": "Weapon", "owner": "Silverdawn"},
    {"key": "silverdawn_extensions", "label": "Silverdawn Ext", "group": "Weapon", "owner": "Silverdawn"},
    # --- Artifact sets -----------------------------------------------------
    {"key": "hotf_state", "label": "HotF Stellar", "group": "Artifact", "owner": "Heart Of The Furnace"},
    {"key": "vv_state", "label": "VV Elemental Shred", "group": "Artifact", "owner": "Viridescent Venerer"},
    {"key": "instructor_state", "label": "Instructor EM", "group": "Artifact", "owner": "Instructor"},
    {"key": "gilded_state", "label": "Gilded Dreams", "group": "Artifact", "owner": "Gilded Dreams"},
    {"key": "noblesse_state", "label": "Noblesse ATK%", "group": "Artifact", "owner": "Noblesse Oblige"},
    {"key": "tenacity_state", "label": "Tenacity ATK%", "group": "Artifact", "owner": "Tenacity Of The Millelith"},
    {"key": "risingwinds_state", "label": "Rising Winds ATK%", "group": "Artifact", "owner": "A Day Carved From Rising Winds"},
    {"key": "scarlet_state", "label": "Scarlet Proof", "group": "Artifact", "owner": "Scarlet Proof"},
    {"key": "tsaritsa_stacks", "label": "Tsaritsa Stacks", "group": "Artifact", "owner": "New Tsaritsa set"},
    {"key": "tsaritsa_state", "label": "Tsaritsa Cryo CR", "group": "Artifact", "owner": "New Tsaritsa set"},
    {"key": "tsaritsa_stellar_state", "label": "Tsaritsa Stellar CR", "group": "Artifact", "owner": "New Tsaritsa set"},
    # --- Team auras --------------------------------------------------------
    {"key": "cryo_resonance_state", "label": "Cryo Resonance CR", "group": "Team", "owner": "Cryo Resonance", "team_requirement": ("element", "Cryo", 2)},
]


BY_KEY = {entry["key"]: entry for entry in BUFFS}


def _party_info(party):
    """Normalise a party dict into the lookups the availability checks need."""
    order = {}
    constellations = {}
    weapons = set()
    artifacts = set()
    for name, data in (party or {}).items():
        data = data or {}
        char = data.get("character", name)
        if not char or char in ("None", "Select Character"):
            continue
        if char not in order:
            order[char] = len(order)
        constellations[char] = int(data.get("constellation", 0) or 0)
        weapon = data.get("weapon")
        if weapon and weapon not in ("Select Weapon", "None"):
            weapons.add(weapon)
        pieces = data.get("artifacts")
        artifact = data.get("artifact_set")
        if not artifact and isinstance(pieces, dict):
            artifact = pieces.get("Set")
        if artifact and artifact not in ("Select Set", "None"):
            artifacts.add(artifact)
    return {"order": order, "constellations": constellations,
             "weapons": weapons, "artifacts": artifacts, "elements": party_element_counts(order)}


def _is_available(entry, info):
    group = entry["group"]
    if group == "Character":
        owner = entry["owner"]
        if owner not in info["order"]:
            return False
        return info["constellations"].get(owner, 0) >= entry.get("min_constellation", 0)
    if group == "Weapon":
        owners = entry["owner"] if isinstance(entry["owner"], (list, tuple, set)) else [entry["owner"]]
        return any(owner in info["weapons"] for owner in owners)
    if group == "Artifact":
        return entry["owner"] in info["artifacts"]
    if group == "Team":
        req = entry.get("team_requirement")
        if not req:
            return True
        _kind, element, count = req
        return info["elements"].get(element, 0) >= count
    return False


def visible_buffs(party):
    """Registry entries whose owner/gear/resonance exists in this party,
    ordered: characters (party order) -> weapons -> artifacts -> team."""
    info = _party_info(party)
    registry_index = {entry["key"]: i for i, entry in enumerate(BUFFS)}
    available = [entry for entry in BUFFS if _is_available(entry, info)]
    available.sort(key=lambda entry: (
        GROUP_ORDER.index(entry["group"]),
        info["order"].get(entry.get("owner"), 99) if entry["group"] == "Character" else 0,
        registry_index[entry["key"]],
    ))
    return available

