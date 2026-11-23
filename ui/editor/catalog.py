"""The editor catalog: our engine data, shaped for the UI.

Nothing here duplicates game data - every entry is read from abilities.py,
presets.py and characters.py at import time, so the editor can only ever show
what the app can actually run.

Ids are stable strings built from the registry keys, because display names
repeat: three trials share one display name.
"""

from __future__ import annotations

import math
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

# Bump when the spec catalogue's payload shape changes: store.spec() re-seeds an
# older session spec instead of feeding the editor stale hit tables.
CATALOG_VERSION = 3


def slug(text: str) -> str:
    """Lower-case, underscore-separated id fragment."""
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")


def character_id(name: str) -> str:
    return slug(name)


def ability_id(character: str, name: str) -> str:
    return ab.ability_key(character, name)


def sequence_id(character: str, name: str) -> str:
    return character_id(character) + "__" + slug(name)


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
    base = min((h.relative_delay for h in hits), default=0.0)
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
        # The press-to-first-hit gap; each hit's delay is measured from the press.
        "first_hit_delay": round(base, 6),
        "hits": [{"name": h.name, "delay": round(h.relative_delay, 6)} for h in hits],
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


def _ability_ids(character: str, *, include_engine_procs: bool = True) -> list:
    wanted = character_id(character)
    rows = []
    for names in ab.ABILITY_REGISTRY.values():
        for ability in names.values():
            if character_id(ability.character) != wanted:
                continue
            if not include_engine_procs and ability.name in ab.ENGINE_INTERNAL_ABILITIES:
                continue
            rows.append((_CATEGORY_ORDER.get(_category(ability), 9), ability.name,
                         ability_id(ability.character, ability.name)))
    return [aid for _order, _name, aid in sorted(rows)]


def abilities_of(character: str) -> list:
    """Ability ids belonging to one character, skills first."""
    return _ability_ids(character)


def castable_abilities_of(character: str) -> list:
    """Ability ids the user can place and time: no engine-injected procs."""
    return _ability_ids(character, include_engine_procs=False)


def timing_rows(spec: dict, cid: str) -> list:
    """One row per hit for every castable ability of character *cid*.

    Long format: the ability name repeats on each row (a data editor cannot merge
    cells), the hit name is the shipped one, and ``timing`` is the delay from the
    cast.
    """
    abilities = spec["catalog"]["abilities"]
    ordered = []
    for aid, payload in abilities.items():
        if payload.get("character") != cid:
            continue
        if payload.get("category") == "triggered":
            continue
        ordered.append((_CATEGORY_ORDER.get(payload.get("category"), 9),
                        payload.get("name", ""), aid, payload))
    rows = []
    for _order, _name, aid, payload in sorted(ordered):
        for index, hit in enumerate(payload.get("hits") or ()):
            rows.append({"ability_id": aid,
                         "ability": payload.get("name", ""),
                         "hit_index": index,
                         "hit": hit.get("name", ""),
                         "timing": float(hit.get("delay", 0.0))})
    return rows


def baseline_ability(aid: str):
    """A fresh catalogue payload for *aid* straight from abilities.py."""
    for names in ab.ABILITY_REGISTRY.values():
        for ability in names.values():
            if ability_id(ability.character, ability.name) == aid:
                return _ability(ability)
    return None


def apply_timings_to_payload(payload: dict, delays) -> dict:
    """A COPY of *payload* with new hit timings.

    Timings are delays from the cast and must be non-decreasing, so the first row
    stays the earliest hit and ``first_hit_delay`` is its delay.
    """
    hits = list(payload.get("hits") or ())
    ability_name = payload.get("name", "This ability")
    try:
        values = [float(value) for value in delays]
    except (TypeError, ValueError):
        raise ValueError("%s: timings must be numbers." % ability_name) from None
    if len(values) != len(hits):
        raise ValueError("%s: every hit needs one timing." % ability_name)
    for hit, value in zip(hits, values):
        if not math.isfinite(value) or value < 0:
            raise ValueError("%s: %s needs a timing of zero or more."
                             % (ability_name, hit.get("name", "hit")))
    for index in range(1, len(values)):
        if values[index] + 1e-9 < values[index - 1]:
            raise ValueError(
                "%s: %s (%.3fs) cannot be earlier than %s (%.3fs); "
                "keep the timings in hit order."
                % (ability_name,
                   hits[index].get("name", "hit %d" % (index + 1)), values[index],
                   hits[index - 1].get("name", "hit %d" % index), values[index - 1]))
    base = min(values)
    resolved = dict(payload)
    resolved["hits"] = [
        {"name": hit.get("name", ""), "delay": round(value, 6)}
        for hit, value in zip(hits, values)
    ]
    resolved["first_hit_delay"] = round(base, 6)
    return resolved


def character_has_timing_overrides(spec: dict, cid: str) -> bool:
    abilities = spec["catalog"]["abilities"]
    for aid in (spec.get("ability_timings") or {}):
        payload = abilities.get(aid)
        if payload is not None and payload.get("character") == cid:
            return True
    return False


def field_sequences_payload() -> dict:
    out = {}
    for seq in presets.FIELD_SEQUENCE_REGISTRY.values():
        sid = sequence_id(seq.character, seq.name)
        placements = []
        for index, call in enumerate(seq.calls):
            owner = getattr(call.ability, "character", seq.character) or seq.character
            placements.append({
                "id": sid + "~" + str(index) + "~" + slug(call.ability.name),
                "ability": ability_id(owner, call.ability.name),
                # A placement is the programmed button press; each hit lands at
                # press + the hit's own delay.
                "cast_time": round(call.start_time, 6),
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


def preset_spec(party_names=None, ability_timings=None) -> dict:
    """A fresh editor spec seeded from the shipped presets.

    ``ability_timings`` is {ability id: [timings]} saved in a build; stale or
    malformed entries are dropped instead of poisoning the spec.
    """
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
    spec = {
        "catalog_version": CATALOG_VERSION,
        "catalog": {"characters": characters_payload(),
                    "abilities": abilities_payload()},
        "ability_timings": {},
        "field_seqs": sequences,
        "rotations": rotations,
        "trials": trials,
        "active_trial": active or next(iter(trials)),
    }
    for aid, delays in (ability_timings or {}).items():
        payload = spec["catalog"]["abilities"].get(aid)
        if payload is None or payload.get("category") == "triggered":
            continue
        try:
            values = [round(float(value), 6) for value in delays]
            spec["catalog"]["abilities"][aid] = apply_timings_to_payload(payload, values)
        except (TypeError, ValueError):
            continue
        spec["ability_timings"][aid] = values
    return spec
