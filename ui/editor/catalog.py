"""The editor catalog: our engine data, shaped for the UI.

Nothing here duplicates game data - every entry is read from abilities.py,
presets.py and characters.py at import time, so the editor can only ever show
what the app can actually run.

Ids are stable strings built from the registry keys, because display names
repeat: three trials share one display name.
"""

from __future__ import annotations

import re

import abilities as ab
import characters as chars
import presets

_LOOK = {
    "Mizuki": ("#e0a13a", "M"),
    "Aether": ("#6fb8d9", "A"),
    "Odette": ("#a78bfa", "O"),
    "Faruzan": ("#4dbfa0", "F"),
    "Sucrose": ("#7cc4a5", "S"),
    "Diona": ("#8fb3d9", "D"),
    "Anastasya": ("#d98fb3", "N"),
}
_FALLBACK = "#9aa4b2"


def slug(text: str) -> str:
    """Lower-case, underscore-separated id fragment."""
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")


def character_id(name: str) -> str:
    return slug(name)


def ability_id(character: str, name: str) -> str:
    return character_id(character) + "__" + slug(name)


def sequence_id(character: str, name: str) -> str:
    return character_id(character) + "__" + slug(name)


def _first_delay(ability) -> float:
    return min((h.relative_delay for h in (ability.hits or ())), default=0.0)


def _category(ability) -> str:
    if ability.name in ab.ENGINE_INTERNAL_ABILITIES:
        return "triggered"
    kind = getattr(ability.hits[0].attack_type, "name", "") if ability.hits else ""
    if kind in ("NORMAL", "CHARGED"):
        return "basic"
    if kind == "BURST":
        return "ultimate"
    return "skill"


def _ability(ability) -> dict:
    hits = ability.hits or ()
    base = _first_delay(ability)
    return {
        "id": ability_id(ability.character, ability.name),
        "name": ability.name,
        "character": character_id(ability.character),
        "category": _category(ability),
        "cooldown": float(getattr(ability, "cooldown", 0.0) or 0.0),
        # The pre-flight keys cooldowns on (character, cooldown_family): both
        # Mizuki forms and Diona's tap/hold must clash with each other, while
        # Odette's cast/recast must not.
        "cooldown_family": ability.cooldown_family or ability.name,
        # Stocked charges (Sucrose: 2). The pre-flight keeps one ChargePool per
        # (character, family), so its warnings match the engine charge for charge.
        "ability_max_charges": int(getattr(ability, "ability_max_charges", 1) or 1),
        # Interruptible skill forms are cut by the swap-out: the strip and the issue
        # list must show the hits that really happen, not the full hit table.
        "interrupt_on_swap_out": bool(getattr(ability, "interrupt_on_swap_out", False)),
        "hits": [{"offset": round(h.relative_delay - base, 6)} for h in hits],
    }


def characters_payload() -> dict:
    out = {}
    for name in chars.CHARACTER_BASE_STATS:
        color, initial = _LOOK.get(name, (_FALLBACK, name[:1].upper()))
        cid = character_id(name)
        out[cid] = {"id": cid, "name": name, "color": color, "initial": initial}
    return out


def abilities_payload() -> dict:
    out = {}
    for names in ab.ABILITY_REGISTRY.values():
        for ability in names.values():
            payload = _ability(ability)
            out[payload["id"]] = payload
    return out


_CATEGORY_ORDER = {"skill": 0, "ultimate": 1, "basic": 2, "triggered": 3}


def abilities_of(character: str) -> list:
    """Ability ids belonging to one character, skills first.

    A field sequence is one character's time on field, so an ability from somebody
    else's kit can never belong in it: the sequence screen only offers these.
    """
    wanted = character_id(character)
    rows = []
    for names in ab.ABILITY_REGISTRY.values():
        for ability in names.values():
            if character_id(ability.character) != wanted:
                continue
            rows.append((_CATEGORY_ORDER.get(_category(ability), 9), ability.name,
                         ability_id(ability.character, ability.name)))
    return [ability_id for _order, _name, ability_id in sorted(rows)]


def field_sequences_payload() -> dict:
    out = {}
    for seq in presets.FIELD_SEQUENCE_REGISTRY.values():
        sid = sequence_id(seq.character, seq.name)
        placements = []
        for index, call in enumerate(seq.calls):
            base = _first_delay(call.ability)
            owner = getattr(call.ability, "character", seq.character) or seq.character
            placements.append({
                "id": sid + "~" + str(index) + "~" + slug(call.ability.name),
                "ability": ability_id(owner, call.ability.name),
                "first_hit": round(call.start_time + base, 6),
            })
        out[sid] = {"id": sid, "name": seq.name, "character": character_id(seq.character),
                    "field_time": float(seq.swap_out_time), "placements": placements,
                    "preset": True}
    return out


def _rotation_payload(key: str, rotation, sequences: dict) -> dict:
    blocks = []
    for seq in rotation.sequences:
        sid = sequence_id(seq.character, seq.name)
        if sid in sequences:
            blocks.append(sid)
    return {"id": slug(key), "name": rotation.name, "blocks": blocks,
            "repeat": int(rotation.repetitions), "preset": True}


_ROTATION_KEYS = {id(rot): slug(key) for key, rot in presets.STANDARD_ROTATIONS.items()}


def rotations_payload(sequences: dict) -> dict:
    return {slug(key): _rotation_payload(key, rot, sequences)
            for key, rot in presets.STANDARD_ROTATIONS.items()}


def trials_payload(rotations: dict, sequences: dict) -> dict:
    out = {}
    for key, trial in presets.STANDARD_TRIALS.items():
        tid = slug(key)
        slots = []
        for index, rotation in enumerate(trial.rotations):
            rid = _ROTATION_KEYS.get(id(rotation))
            if rid is None:
                rid = slug(rotation.name)
                rotations.setdefault(rid, _rotation_payload(rid, rotation, sequences))
            slots.append({"id": tid + "~" + str(index), "rotation": rid,
                          "repeat": int(rotation.repetitions)})
        out[tid] = {
            "id": tid,
            "name": trial.name,
            "description": trial.description or "",
            "end_mode": trial.end_mode,
            "end_time": float(trial.end_time),
            "required_party": [character_id(name) for name in (trial.required_party or [])],
            "slots": slots,
            "preset": True,
        }
    return out


def preset_spec(party_names=None) -> dict:
    """A fresh editor spec seeded from the shipped presets."""
    sequences = field_sequences_payload()
    rotations = rotations_payload(sequences)
    trials = trials_payload(rotations, sequences)
    party = {character_id(name) for name in (party_names or [])}
    active = None
    for tid, trial in trials.items():
        required = set(trial["required_party"])
        if not required or required <= party:
            active = tid
            break
    return {
        "catalog": {"characters": characters_payload(),
                    "abilities": abilities_payload()},
        "field_seqs": sequences,
        "rotations": rotations,
        "trials": trials,
        "active_trial": active or next(iter(trials)),
    }
