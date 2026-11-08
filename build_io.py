"""Build documents — the save/load format for a full simulator configuration.

A "build document" is a plain JSON dict describing everything the user configured:
the four party slots (character, level, constellation, weapon + refinement, talents,
artifact set and every piece's main stat / rarity / substats), the enemy, the selected
trial and the custom field sequences / rotations / trials.

Keeping the file layout in one framework-free module means:

  * the Streamlit UI saves and restores a build without knowing the format,
  * a loaded file stays EDITABLE — the importer also writes the widget state, so the
    artifact editors show the imported pieces instead of empty boxes, and the party
    composition can be changed afterwards,
  * the same document is produced by "Export current build" and by every history run.

Nothing here imports Streamlit: the functions take any mutable mapping (a Streamlit
`session_state` or a plain dict), which keeps them unit-testable.
"""

import copy
import datetime
import json

from abilities import ABILITY_REGISTRY, FIELD_SEQUENCE_REGISTRY
from characters import get_character_element
from models import FieldSequence, Rotation, Trial
from presets import STANDARD_FIELD_SEQUENCES, STANDARD_TRIALS
from stats_calc import (
    apply_weapon_party_stats,
    build_initial_stats,
    compute_card_stats,
)
from substats_standards import CARRIES, build_kqm_build, build_recommended_subs

APP_NAME = "Yumemizuki Mizuki's Rotation Damage Calculator"

# 2.0: `party` is a LIST of slots that carries raw gear (mains/substats).
# 1.0: `party` was a dict of cooked character data with no gear at all.
SCHEMA_VERSION = "2.0"

PIECES = ("Flower", "Feather", "Sands", "Goblet", "Circlet")
LOCKED_MAIN_PIECES = ("Flower", "Feather")

# Order matters: it is the key order used by the Enemy tab's signature tuple.
ELEMENTS = ("pyro", "cryo", "hydro", "electro", "anemo", "geo", "dendro", "physical")

SUBSTAT_STANDARDS = ("Manual", "100% RV (Crit Value)", "KQM Standards (40 rolls)")

# Mapping from UI display names to standardized backend keys
STAT_KEY_MAP = {
    "Flat HP": "hp_flat",
    "Flat ATK": "atk_flat",
    "Flat DEF": "def_flat",
    "HP%": "hp_percent",
    "ATK%": "atk_percent",
    "DEF%": "def_percent",
    "EM": "em",
    "ER%": "er",
    "Crit Rate%": "crit_rate",
    "Crit Damage%": "crit_dmg",
    "Healing Bonus%": "healing_bonus",
    "Physical Bonus%": "physical_bonus",
    "Pyro Bonus%": "pyro_bonus",
    "Hydro Bonus%": "hydro_bonus",
    "Geo Bonus%": "geo_bonus",
    "Anemo Bonus%": "anemo_bonus",
    "Electro Bonus%": "electro_bonus",
    "Dendro Bonus%": "dendro_bonus",
    "Cryo Bonus%": "cryo_bonus",
}

# Substats that are stored as percentages and must be divided by 100.
PERCENT_KEYS = ("hp_percent", "atk_percent", "def_percent", "crit_rate", "crit_dmg", "er")

# A 5★ / 4★ artifact piece at +20 contributes exactly one maxed main stat.
STANDARD_MAIN_STATS = {
    "hp_flat": 4780, "atk_flat": 311, "hp_percent": 0.466, "atk_percent": 0.466,
    "def_percent": 0.583, "em": 186.5, "er": 0.518, "crit_rate": 0.311,
    "crit_dmg": 0.622, "healing_bonus": 0.359, "physical_bonus": 0.583,
    "pyro_bonus": 0.466, "hydro_bonus": 0.466, "geo_bonus": 0.466,
    "anemo_bonus": 0.466, "electro_bonus": 0.466, "dendro_bonus": 0.466, "cryo_bonus": 0.466
}

STANDARD_4STAR_MAIN_STATS = {
    "hp_flat": 3571, "atk_flat": 232, "hp_percent": 0.348, "atk_percent": 0.348,
    "def_percent": 0.435, "em": 139.3, "er": 0.387, "crit_rate": 0.232,
    "crit_dmg": 0.464, "healing_bonus": 0.268, "physical_bonus": 0.435,
    "pyro_bonus": 0.348, "hydro_bonus": 0.348, "geo_bonus": 0.348,
    "anemo_bonus": 0.348, "electro_bonus": 0.348, "dendro_bonus": 0.348, "cryo_bonus": 0.348
}


# ---------------------------------------------------------------------------
# Small value helpers
# ---------------------------------------------------------------------------

def parse_stat_value(val) -> float:
    """'40' / '3.5%' -> 40.0 / 3.5 (anything unparseable becomes 0.0)."""
    if val is None:
        return 0.0
    text = str(val).strip()
    if not text:
        return 0.0
    try:
        return float(text.replace("%", ""))
    except ValueError:
        return 0.0


def constellation_int(value) -> int:
    """0 / 'C2' / 'c6' -> 0 / 2 / 6."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value or "").strip().upper().replace("C", "")
    try:
        return int(text)
    except ValueError:
        return 0


def refinement_int(value) -> int:
    """1 / 'R5' -> 1 / 5."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value) if int(value) > 0 else 1
    text = str(value or "").strip().upper().replace("R", "")
    try:
        return int(text) or 1
    except ValueError:
        return 1


def talent_levels_from_text(text) -> list:
    """'1/13/13' -> [1, 13, 13]; anything else falls back to [1, 1, 1]."""
    parts = [part.strip() for part in str(text or "").split("/")]
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        levels = [int(part) for part in parts]
        if all(1 <= level <= 13 for level in levels):
            return levels
    return [1, 1, 1]


# ---------------------------------------------------------------------------
# Gear -> stats
# ---------------------------------------------------------------------------

def _stats_or_empty(value):
    return value if isinstance(value, dict) else {}


def _as_list(value):
    return value if isinstance(value, list) else []


def _iter_payloads(value, name_key="name"):
    """Yield dict payloads from either a list (2.0) or a {key: dict} mapping (1.0)."""
    if isinstance(value, dict):
        for key, payload in value.items():
            if isinstance(payload, dict):
                merged = dict(payload)
                merged.setdefault(name_key, key)
                yield merged
    else:
        for payload in _as_list(value):
            if isinstance(payload, dict):
                yield payload


def stat_name_is_valid(name) -> bool:
    return bool(name) and name != "None"


def slot_stats_from_pieces(char_name, pieces, standard_mode="Manual"):
    """(main_stats_total, subs_total) for one slot.

    Single implementation of "artifact pieces -> stat pools": the UI confirm button
    and the build importer both go through it, so a loaded build is numerically
    identical to one typed in by hand.
    """
    if standard_mode == "100% RV (Crit Value)":
        # 100% RV: auto mains + substats per the carry standard (5★ defaults).
        return build_recommended_subs(char_name)
    if standard_mode == "KQM Standards (40 rolls)":
        # KQM: same locked mains, 40-roll substat standard.
        return build_kqm_build(char_name)

    main_stats_total = {}
    subs_total = {}
    for piece_name, piece_info in _stats_or_empty(pieces).items():
        piece_info = _stats_or_empty(piece_info)
        main_stat = piece_info.get("main_stat", "")
        piece_rarity = piece_info.get("rarity", "5★")
        active_stats = (STANDARD_4STAR_MAIN_STATS if piece_rarity == "4★"
                        else STANDARD_MAIN_STATS)

        if main_stat:
            stat_key = STAT_KEY_MAP.get(main_stat)
            if stat_key and stat_key in active_stats:
                main_stats_total[stat_key] = main_stats_total.get(stat_key, 0.0) + active_stats[stat_key]

        for sub in _as_list(piece_info.get("substats")):
            if not isinstance(sub, dict):
                continue
            sub_name = sub.get("stat")
            if not stat_name_is_valid(sub_name):
                continue
            sub_key = STAT_KEY_MAP.get(sub_name, str(sub_name).lower().replace(" ", "_"))
            numeric_val = parse_stat_value(sub.get("value"))
            if "%" in str(sub_name) or sub_key in PERCENT_KEYS:
                numeric_val = numeric_val / 100.0
            subs_total[sub_key] = subs_total.get(sub_key, 0.0) + numeric_val

    return main_stats_total, subs_total


def assemble_party(slots) -> dict:
    """Build the `my_party` mapping (initial_stats + card_stats) from slot specs.

    A slot spec is the plain description of one party member:
        character, level, constellation (int or "C#"), weapon, refinement,
        talents ("10/13/13"), talent_levels ([10, 13, 13]), artifact_set,
        standard_mode, pieces {Flower: {main_stat, rarity, substats}}
    """
    my_party = {}
    for slot in _as_list(slots):
        slot = _stats_or_empty(slot)
        char_name = slot.get("character")
        if not char_name or char_name == "Select Character":
            continue

        standard_mode = slot.get("standard_mode") or "Manual"
        if char_name not in CARRIES:
            standard_mode = "Manual"

        artifact_set = slot.get("artifact_set") or "Select Set"
        refinement = refinement_int(slot.get("refinement", 1))
        talent_text = str(slot.get("talents") or "").strip()

        main_stats_total, subs_total = slot_stats_from_pieces(
            char_name, slot.get("pieces"), standard_mode
        )
        initial_stats = build_initial_stats(
            char_name,
            slot.get("level", 90),
            slot.get("weapon"),
            artifact_set,
            main_stats_total,
            subs_total,
            refinement=refinement,
        )

        my_party[char_name] = {
            "constellation": constellation_int(slot.get("constellation", 0)),
            "level": slot.get("level", 90),
            "weapon": slot.get("weapon"),
            "refinement": refinement,
            "talents": talent_text or "10/13/13",
            "talent_levels": slot.get("talent_levels") or talent_levels_from_text(talent_text),
            "artifact_set": artifact_set if artifact_set != "Select Set" else "None",
            "element": get_character_element(char_name),
            "standard_mode": standard_mode,
            "initial_stats": initial_stats,
            "card_stats": {},
        }

    # Permanent, party-composition-dependent weapon stats (e.g. A Thousand Floating
    # Dreams) depend on the whole party, so this is a second pass. Idempotent.
    apply_weapon_party_stats(
        {name: data["initial_stats"] for name, data in my_party.items()}, my_party
    )
    for data in my_party.values():
        data["card_stats"] = compute_card_stats(
            data["initial_stats"],
            standard_mode=(data.get("standard_mode", "Manual") != "Manual"),
        )
    return my_party



# ---------------------------------------------------------------------------
# Field sequences / rotations / trials  <->  payloads
# ---------------------------------------------------------------------------

def _ability_for(ability_name, character=None):
    """Resolve an ability name to the LIVE Ability object (so numbers stay current).

    The owning character is tried first, because shared names exist (e.g. every
    character has an "Elemental Burst").
    """
    if not ability_name:
        return None
    if character and ability_name in ABILITY_REGISTRY.get(character, {}):
        return ABILITY_REGISTRY[character][ability_name]
    for ability_map in ABILITY_REGISTRY.values():
        if ability_name in ability_map:
            return ability_map[ability_name]
    return None


def field_sequence_payload(seq) -> dict:
    """FieldSequence -> plain dict (fully self-contained, no name lookups needed)."""
    return {
        "name": seq.name,
        "character": seq.character,
        "swap_out_time": seq.swap_out_time,
        "calls": [
            {
                "start_time": call.start_time,
                "ability_name": call.ability.name,
                "ability_character": getattr(call.ability, "character", seq.character),
            }
            for call in seq.calls
        ],
    }


def sequence_from_payload(payload, warnings=None) -> FieldSequence:
    """Plain dict -> FieldSequence. Abilities are re-resolved by name; a vanished
    ability is reported instead of silently dropping the whole sequence."""
    warnings = warnings if warnings is not None else []
    name = payload.get("name") or "Unnamed Sequence"
    character = payload.get("character") or ""
    seq = FieldSequence(name=name, character=character,
                        swap_out_time=float(payload.get("swap_out_time", 1.0) or 1.0))
    for call in _as_list(payload.get("calls")):
        if not isinstance(call, dict):
            continue
        ability = _ability_for(call.get("ability_name"),
                               call.get("ability_character") or character)
        if ability is None:
            warnings.append(
                f"Field sequence '{name}': ability '{call.get('ability_name')}' no longer "
                f"exists in abilities.py — that call was skipped."
            )
            continue
        seq.add_ability(float(call.get("start_time", 0.0) or 0.0), ability)
    return seq


def rotation_payload(rot) -> dict:
    """Rotation -> plain dict. Sequences are embedded so the file stands alone."""
    return {
        "name": rot.name,
        "repetitions": rot.repetitions,
        "description": rot.description or "",
        "sequences": [field_sequence_payload(seq) for seq in rot.sequences],
    }


def _lookup_sequence(name, custom_sequences=None):
    """Fallback lookup for files that only stored sequence NAMES (schema 1.0)."""
    for pool in (custom_sequences or {}, STANDARD_FIELD_SEQUENCES, FIELD_SEQUENCE_REGISTRY):
        if name in pool:
            return pool[name]
    return None


def rotation_from_payload(payload, warnings=None, custom_sequences=None) -> Rotation:
    warnings = warnings if warnings is not None else []
    name = payload.get("name") or "Unnamed Rotation"
    sequences = []
    for seq_payload in _iter_payloads(payload.get("sequences")):
        sequences.append(sequence_from_payload(seq_payload, warnings))
    if not sequences:
        # Schema 1.0 files stored `sequence_keys` (names) instead of definitions.
        for seq_name in _as_list(payload.get("sequence_keys")):
            seq = _lookup_sequence(seq_name, custom_sequences)
            if seq is None:
                warnings.append(
                    f"Rotation '{name}': field sequence '{seq_name}' is unknown — skipped."
                )
                continue
            sequences.append(seq)
    return Rotation(
        name=name,
        sequences=sequences,
        repetitions=int(payload.get("repetitions", 1) or 1),
        description=payload.get("description") or "",
    )


def trial_payload(trial) -> dict:
    return {
        "name": trial.name,
        "end_mode": trial.end_mode,
        "end_time": trial.end_time,
        "description": trial.description or "",
        "rotations": [
            {"rotation_name": rot.name, "repetitions": rot.repetitions}
            for rot in trial.rotations
        ],
    }



def restore_custom_pools(doc, state, warnings=None) -> dict:
    """Rebuild the editor pools (sequences, rotations, trials) from a document.

    Every rotation used by a custom trial is re-registered in `custom_rotations`,
    which is what makes an imported trial editable instead of read-only.
    """
    warnings = warnings if warnings is not None else []

    custom_sequences = {}
    for payload in _iter_payloads(doc.get("custom_field_sequences")):
        seq = sequence_from_payload(payload, warnings)
        if seq.name:
            custom_sequences[seq.name] = seq

    custom_rotations = {}
    for payload in _iter_payloads(doc.get("custom_rotations")):
        rot = rotation_from_payload(payload, warnings, custom_sequences)
        if rot.name:
            custom_rotations[rot.name] = rot

    trial_pool = dict(STANDARD_TRIALS)
    custom_trial_names = []
    for payload in _iter_payloads(doc.get("custom_trials")):
        trial_name = payload.get("name") or "Imported Trial"
        rotations = []
        for entry in _iter_payloads(payload.get("rotations")):
            rot_name = entry.get("rotation_name") or entry.get("name")
            base_rotation = custom_rotations.get(rot_name)
            if base_rotation is None:
                warnings.append(
                    f"Trial '{trial_name}': rotation '{rot_name}' is missing from the "
                    f"file — that rotation was skipped."
                )
                continue
            rot_copy = copy.deepcopy(base_rotation)
            rot_copy.repetitions = int(entry.get("repetitions", 1) or 1)
            rotations.append(rot_copy)
        if not rotations:
            warnings.append(f"Trial '{trial_name}' has no usable rotations — not loaded.")
            continue
        trial_pool[trial_name] = Trial(
            name=trial_name,
            rotations=rotations,
            end_mode=payload.get("end_mode", "time"),
            end_time=float(payload.get("end_time", 30.0) or 30.0),
            description=payload.get("description") or "",
        )
        custom_trial_names.append(trial_name)

    state["custom_field_sequences"] = custom_sequences
    state["custom_rotations"] = custom_rotations
    state["active_trial_pool"] = trial_pool
    return {
        "custom_trial_names": custom_trial_names,
        "custom_rotations": custom_rotations,
        "custom_field_sequences": custom_sequences,
    }


def load_trial_into_editor(trial, state) -> str:
    """Make an existing (preset or imported) trial editable.

    Every rotation of the trial is copied into `custom_rotations` — so it appears in
    the editor's "Select Rotation" dropdown and can be re-used in a new trial — and
    the trial's rotation queue is pre-filled with it.
    """
    sequences = state.get("custom_field_sequences") or {}
    if not isinstance(sequences, dict):
        sequences = {}
    rotations = state.get("custom_rotations") or {}
    if not isinstance(rotations, dict):
        rotations = {}

    for rotation in trial.rotations:
        for seq in rotation.sequences:
            if seq.name not in STANDARD_FIELD_SEQUENCES and seq.name not in sequences:
                sequences[seq.name] = copy.deepcopy(seq)
        rotations[rotation.name] = copy.deepcopy(rotation)

    state["custom_field_sequences"] = sequences
    state["custom_rotations"] = rotations
    state["temp_trial_rot_entries"] = [
        {"rotation_name": rot.name, "repetitions": rot.repetitions}
        for rot in trial.rotations
    ]
    # Widget keys can only be written before the widget is created, so the name and
    # description are queued and applied at the top of the Rotation tab.
    state["editor_prefill"] = {"name": trial.name,
                               "description": trial.description or ""}
    return trial.name



# ---------------------------------------------------------------------------
# Collect (UI state -> document)
# ---------------------------------------------------------------------------

def collect_enemy(state) -> dict:
    """Enemy block: prefers the live widgets, falls back to the confirmed stats."""
    stored = _stats_or_empty(state.get("enemy_stats"))
    level = state.get("input_enemy_lv")
    if level is None:
        level = stored.get("enemy_lv", 100)
    enemy = {"enemy_lv": int(level or 100)}
    for elem in ELEMENTS:
        raw = state.get(f"input_{elem}_res")
        if raw is None:
            raw = float(stored.get(f"{elem}_res", 0.1) or 0.0) * 100.0
        enemy[f"{elem}_res"] = round(float(raw) / 100.0, 6)
    return enemy


def collect_slot(state, slot_num) -> dict:
    """One party slot (widgets -> plain dict, including every piece's substats)."""
    character = state.get(f"char_{slot_num}") or "Select Character"
    standard_mode = (state.get(f"std_{slot_num}", "Manual")
                     if character in CARRIES else "Manual")

    pieces = {}
    for piece in PIECES:
        rarity = (state.get(f"rarity_locked_{piece}_{slot_num}")
                  or state.get(f"rarity_{piece}_{slot_num}") or "5★")
        if piece == "Flower":
            main_stat = "Flat HP"
        elif piece == "Feather":
            main_stat = "Flat ATK"
        else:
            main_stat = state.get(f"main_{piece}_{slot_num}")

        substats = []
        if standard_mode == "Manual":
            for sub_idx in range(1, 5):
                sub_type = state.get(f"sub_type_{piece}_{slot_num}_{sub_idx}", "None")
                if stat_name_is_valid(sub_type):
                    substats.append({
                        "stat": sub_type,
                        "value": str(state.get(f"sub_val_{piece}_{slot_num}_{sub_idx}", "") or ""),
                    })
        pieces[piece] = {"main_stat": main_stat, "rarity": rarity, "substats": substats}

    return {
        "slot": slot_num,
        "character": character,
        "level": state.get(f"level_{slot_num}", 90),
        "constellation": constellation_int(state.get(f"const_{slot_num}", 0)),
        "weapon": (state.get(f"weapon_{slot_num}")
                   or state.get(f"weapon_locked_{slot_num}") or "Select Weapon"),
        "refinement": refinement_int(state.get(f"ref_{slot_num}", 1)),
        "talents": str(state.get(f"talents_{slot_num}", "") or ""),
        "substat_standard": standard_mode,
        "artifact_set": state.get(f"art_set_{slot_num}", "Select Set"),
        "pieces": pieces,
    }


def collect_build_document(state, simulation_name=None) -> dict:
    """Snapshot the whole configuration as a JSON-ready document."""
    pool = state.get("active_trial_pool") or {}
    custom_trials = {name: trial for name, trial in pool.items()
                     if name not in STANDARD_TRIALS}

    # Rotations needed by a custom trial are exported too, so the trial stays
    # editable even if it was assembled from rotations no longer in the pool.
    rotation_payloads = {}
    for name, rot in (state.get("custom_rotations") or {}).items():
        rotation_payloads[rot.name or name] = rotation_payload(rot)
    for trial in custom_trials.values():
        for rot in trial.rotations:
            rotation_payloads.setdefault(rot.name, rotation_payload(rot))

    custom_sequences = [
        field_sequence_payload(seq)
        for seq in (state.get("custom_field_sequences") or {}).values()
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "app": APP_NAME,
        "exported_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "simulation_name": simulation_name or state.get("imported_sim_name") or "",
        "party": [collect_slot(state, slot_num) for slot_num in range(1, 5)],
        "enemy": collect_enemy(state),
        "selected_trial": state.get("trial_selector"),
        "custom_field_sequences": custom_sequences,
        "custom_rotations": list(rotation_payloads.values()),
        "custom_trials": [trial_payload(trial) for trial in custom_trials.values()],
    }


def legacy_party_to_slots(party) -> list:
    """Schema 1.0 party (dict of cooked characters, no gear) -> slot list."""
    slots = []
    for index, (name, data) in enumerate(_stats_or_empty(party).items()):
        if not name or name == "Select Character":
            continue
        data = _stats_or_empty(data)
        slots.append({
            "slot": index + 1,
            "character": name,
            "level": data.get("level", 90),
            "constellation": constellation_int(data.get("constellation", 0)),
            "weapon": data.get("weapon"),
            "refinement": refinement_int(data.get("refinement", 1)),
            "talents": data.get("talents", ""),
            "substat_standard": data.get("standard_mode", "Manual"),
            "artifact_set": data.get("artifact_set", "Select Set"),
            "pieces": {},
        })
    return slots



def legacy_build_document(entry):
    """Best-effort document for history runs recorded before schema 2.0."""
    entry = entry or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": "",
        "simulation_name": entry.get("sim_name", ""),
        "party": legacy_party_to_slots(entry.get("snapshot_party")),
        "enemy": entry.get("snapshot_enemy") or {},
        "selected_trial": None,
        "custom_field_sequences": [
            field_sequence_payload(seq)
            for seq in (entry.get("snapshot_custom_fs") or {}).values()
        ],
        "custom_rotations": [
            rotation_payload(rot)
            for rot in (entry.get("snapshot_custom_rots") or {}).values()
        ],
        "custom_trials": [],
    }


def normalise_document(doc) -> dict:
    """Accept 2.0 documents as-is and migrate 1.0 files to the new shape."""
    if not isinstance(doc, dict):
        raise ValueError("The file does not contain a JSON object.")
    if str(doc.get("schema_version", "")).startswith("2"):
        return doc
    # Schema 1.0: named party without gear, name-only rotations, no custom trials.
    return {
        "schema_version": "1.0 (upgraded)",
        "exported_at": doc.get("exported_at", ""),
        "simulation_name": doc.get("simulation_name", ""),
        "party": legacy_slot_list(doc.get("party")),
        "enemy": doc.get("enemy") or doc.get("enemy_stats") or {},
        "selected_trial": doc.get("selected_trial"),
        "custom_field_sequences": list(_iter_payloads(doc.get("custom_field_sequences_raw"))),
        "custom_rotations": list(_iter_payloads(doc.get("custom_rotations_raw"))),
        "custom_trials": list(_iter_payloads(doc.get("custom_trials_raw"))),
    }


def legacy_slot_list(payload) -> list:
    """`party` is a list in 2.0 and a {name: data} mapping in 1.0."""
    if isinstance(payload, list):
        return [slot for slot in payload if isinstance(slot, dict)]
    return legacy_party_to_slots(payload)


def document_lacks_gear(doc) -> bool:
    """True when no slot carries artifact pieces (i.e. a schema 1.0 file)."""
    party = (doc or {}).get("party")
    if not isinstance(party, list):
        return True
    return not any((slot or {}).get("pieces") for slot in party if isinstance(slot, dict))



# ---------------------------------------------------------------------------
# Apply (document -> UI widget state)
# ---------------------------------------------------------------------------

def _apply_enemy(enemy, state, warnings):
    enemy = _stats_or_empty(enemy)
    try:
        level = int(enemy.get("enemy_lv", 100) or 100)
    except (TypeError, ValueError):
        level = 100
    state["input_enemy_lv"] = level

    fractions = {}
    for elem in ELEMENTS:
        try:
            fraction = float(enemy.get(f"{elem}_res", 0.1))
        except (TypeError, ValueError):
            fraction = 0.1
        percent = round(fraction * 100.0, 2)
        state[f"input_{elem}_res"] = percent
        fractions[elem] = percent / 100.0

    state["enemy_stats"] = {"enemy_lv": level,
                            **{f"{elem}_res": fractions[elem] for elem in ELEMENTS}}
    state["enemy_confirmed"] = True
    # Keeps the Enemy tab from treating the restored values as a change.
    state["last_enemy_signature"] = (level, tuple(fractions[elem] for elem in ELEMENTS))


def _apply_slot(slot, slot_num, state, catalogue, warnings):
    slot = _stats_or_empty(slot)

    character = slot.get("character") or "Select Character"
    characters = catalogue.get("characters") or []
    if characters and character not in characters:
        warnings.append(f"Slot {slot_num}: character '{character}' is not available — "
                        f"the slot was cleared.")
        character = "Select Character"
    state[f"char_{slot_num}"] = character

    levels = catalogue.get("levels") or [90]
    level = slot.get("level", 90)
    if level not in levels:
        fallback = 90 if 90 in levels else levels[0]
        warnings.append(f"Slot {slot_num}: level {level} is not offered — using {fallback}.")
        level = fallback
    state[f"level_{slot_num}"] = level

    const_options = (catalogue.get("constellations") or {}).get(character) or ["C0"]
    const_label = f"C{constellation_int(slot.get('constellation', 0))}"
    if const_label not in const_options:
        warnings.append(f"Slot {slot_num}: {character} has no {const_label} — "
                        f"using {const_options[0]}.")
        const_label = const_options[0]
    state[f"const_{slot_num}"] = const_label

    weapon_table = (catalogue.get("weapons") or {}).get(character)
    if weapon_table:
        weapon_names = [entry[0] for entry in weapon_table]
        weapon = slot.get("weapon")
        if weapon not in weapon_names:
            warnings.append(f"Slot {slot_num}: weapon '{weapon}' is not available for "
                            f"{character} — using {weapon_names[0]}.")
            weapon = weapon_names[0]
        state[f"weapon_{slot_num}"] = weapon

        valid_refines = [entry[1] for entry in weapon_table if entry[0] == weapon][0]
        refinement = refinement_int(slot.get("refinement", 1))
        if refinement not in valid_refines:
            warnings.append(f"Slot {slot_num}: {weapon} has no R{refinement} — "
                            f"using R{valid_refines[0]}.")
            refinement = valid_refines[0]
        state[f"ref_{slot_num}"] = f"R{refinement}"

    state[f"talents_{slot_num}"] = str(slot.get("talents") or "")

    set_options = (catalogue.get("artifact_sets") or {}).get(character) or ["Select Set"]
    artifact_set = slot.get("artifact_set") or "Select Set"
    if artifact_set in ("None", ""):
        artifact_set = "Select Set"
    if artifact_set not in set_options:
        warnings.append(f"Slot {slot_num}: artifact set '{artifact_set}' is not offered for "
                        f"{character} — using {set_options[0]}.")
        artifact_set = set_options[0]
    state[f"art_set_{slot_num}"] = artifact_set

    standards = catalogue.get("standards") or list(SUBSTAT_STANDARDS)
    standard_mode = slot.get("substat_standard") or slot.get("standard_mode") or "Manual"
    if character not in CARRIES or standard_mode not in standards:
        standard_mode = "Manual"
    if character in CARRIES:
        state[f"std_{slot_num}"] = standard_mode

    locked = standard_mode != "Manual"
    mains = catalogue.get("mains") or {}
    rarities = catalogue.get("rarities") or ["5★", "4★"]
    substat_options = catalogue.get("substat_options") or []


    for piece in PIECES:
        info = _stats_or_empty((slot.get("pieces") or {}).get(piece))
        rarity = info.get("rarity") or "5★"
        if rarity not in rarities:
            rarity = "5★"
        rarity_key = (f"rarity_locked_{piece}_{slot_num}" if locked
                      else f"rarity_{piece}_{slot_num}")
        state[rarity_key] = rarity

        if not locked and piece not in LOCKED_MAIN_PIECES:
            allowed = mains.get(piece) or []
            main_stat = info.get("main_stat")
            if main_stat and main_stat in allowed:
                state[f"main_{piece}_{slot_num}"] = main_stat
            elif main_stat and allowed:
                warnings.append(f"Slot {slot_num} {piece}: main stat '{main_stat}' is not "
                                f"valid for that piece — left empty.")

        if locked:
            # Mains/substats are derived from the substat standard, so nothing to restore.
            continue

        substats = _as_list(info.get("substats"))[:4]
        for sub_idx in range(1, 5):
            sub = _stats_or_empty(substats[sub_idx - 1]) if sub_idx - 1 < len(substats) else {}
            sub_type = sub.get("stat") or "None"
            if substat_options and sub_type not in substat_options:
                warnings.append(f"Slot {slot_num} {piece} sub {sub_idx}: '{sub_type}' is not "
                                f"a valid substat — cleared.")
                sub_type = "None"
            state[f"sub_type_{piece}_{slot_num}_{sub_idx}"] = sub_type
            state[f"sub_val_{piece}_{slot_num}_{sub_idx}"] = str(sub.get("value") or "")


def _clear_slot(slot_num, state, catalogue):
    """Reset a slot the imported document does not use.

    Without this, loading a 2-character build onto a page that currently holds a
    4-character team leaves the old characters in the trailing slots (which also trips
    the "character already picked in another slot" guard).
    """
    levels = catalogue.get("levels") or [90]
    default_level = 90 if 90 in levels else levels[0]
    mains = catalogue.get("mains") or {}
    rarities = catalogue.get("rarities") or ["5★"]
    substat_options = catalogue.get("substat_options") or []
    empty_sub = substat_options[0] if substat_options else "None"

    state[f"char_{slot_num}"] = "Select Character"
    state[f"level_{slot_num}"] = default_level
    state[f"const_{slot_num}"] = "C0"
    state[f"talents_{slot_num}"] = ""
    state[f"art_set_{slot_num}"] = "Select Set"
    state[f"std_{slot_num}"] = "Manual"

    for piece in PIECES:
        state[f"rarity_{piece}_{slot_num}"] = rarities[0]
        allowed_mains = mains.get(piece) or []
        if allowed_mains and piece not in LOCKED_MAIN_PIECES:
            state[f"main_{piece}_{slot_num}"] = allowed_mains[0]
        for sub_idx in range(1, 5):
            state[f"sub_type_{piece}_{slot_num}_{sub_idx}"] = empty_sub
            state[f"sub_val_{piece}_{slot_num}_{sub_idx}"] = ""


def apply_build_document(doc, state, catalogue, warnings=None) -> list:
    """Write a document into the widget state so every input matches the file.

    Restoring the *widget keys* (not just the finished party) is what keeps a loaded
    build editable: the slot selectors, the artifact expanders and the trial editor
    all show the imported configuration instead of starting empty.
    """
    warnings = warnings if warnings is not None else []
    doc = normalise_document(doc)
    catalogue = catalogue or {}

    _apply_enemy(doc.get("enemy"), state, warnings)
    party_slots = legacy_slot_list(doc.get("party"))[:4]
    for index, slot in enumerate(party_slots):
        _apply_slot(slot, index + 1, state, catalogue, warnings)
    # Slots the file does not fill are emptied instead of keeping stale characters.
    for slot_num in range(len(party_slots) + 1, 5):
        _clear_slot(slot_num, state, catalogue)

    restore_custom_pools(doc, state, warnings)

    selected = doc.get("selected_trial")
    pool = state.get("active_trial_pool") or {}
    if selected and selected in pool:
        state["trial_selector"] = selected
    elif selected:
        warnings.append(f"Saved trial '{selected}' is not part of this build — "
                        f"select a trial manually.")

    state["imported_sim_name"] = doc.get("simulation_name") or ""
    return warnings


def build_party_from_document(doc) -> dict:
    """Document -> the same `my_party` mapping the confirm button produces."""
    doc = normalise_document(doc)
    slots = []
    for slot in legacy_slot_list(doc.get("party"))[:4]:
        slot = _stats_or_empty(slot)
        character = slot.get("character")
        if not character or character == "Select Character":
            continue
        slots.append({
            "character": character,
            "level": slot.get("level", 90),
            "constellation": slot.get("constellation", 0),
            "weapon": slot.get("weapon"),
            "refinement": slot.get("refinement", 1),
            "talents": slot.get("talents", ""),
            "artifact_set": slot.get("artifact_set", "Select Set"),
            "standard_mode": (slot.get("substat_standard")
                              or slot.get("standard_mode") or "Manual"),
            "pieces": slot.get("pieces") or {},
        })
    return assemble_party(slots)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def document_to_json(doc) -> str:
    return json.dumps(doc, indent=2)


def parse_document(text) -> dict:
    """JSON text -> document (schema 1.0 files are upgraded transparently)."""
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    return normalise_document(json.loads(text))


def suggested_file_name(doc) -> str:
    """File name for a download button, based on the build's own name."""
    doc = doc or {}
    name = (doc.get("simulation_name") or "").strip()
    if not name:
        name = "mizuki_build_" + datetime.datetime.now().strftime("%Y%m%d_%H%M")
    safe = "".join(ch if ch.isalnum() or ch in " -_" else "_" for ch in name).strip()
    return (safe or "mizuki_build").replace(" ", "_") + ".json"

