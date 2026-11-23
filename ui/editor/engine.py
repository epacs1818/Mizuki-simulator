"""Simulation adapter: the editor spec -> our engine -> the result the strips read.

Pure on purpose: every call builds fresh FieldSequence / Rotation / Trial objects,
so a cached result can never share mutable state with a later run. No Streamlit
imports here, so the smoke test can exercise it headlessly.
"""

from __future__ import annotations

import copy

import abilities as ab
from models import ActionCategory, FieldSequence, Rotation, Trial
from timeline import CooldownError, RotationTimeline

from ui.editor import catalog



def _ability_map() -> dict:
    """ability id -> Ability, using the ids the catalog publishes."""
    out = {}
    for names in ab.ABILITY_REGISTRY.values():
        for ability in names.values():
            out[catalog.ability_id(ability.character, ability.name)] = ability
    return out


def ability_map(spec: dict | None = None) -> dict:
    """ability id -> Ability, with the spec's timing overrides applied to copies.

    Always a copy: the registry's Ability objects are shared by every preset and
    every session, so the engine must never hold (or mutate) them.
    """
    overrides = (spec or {}).get("ability_timings") or {}
    out = {}
    for aid, ability in _ability_map().items():
        delays = overrides.get(aid)
        if delays and len(delays) == len(ability.hits):
            out[aid] = ab.ability_with_hit_delays(ability, delays)
        else:
            out[aid] = copy.deepcopy(ability)
    return out


def _character_name(spec: dict, cid: str) -> str:
    return spec["catalog"]["characters"][cid]["name"]


def _field_sequence(fs: dict, spec: dict, abilities: dict) -> FieldSequence:
    seq = FieldSequence(fs["name"], _character_name(spec, fs["character"]),
                        float(fs["field_time"]))
    for placement in fs["placements"]:
        ability = abilities.get(placement["ability"])
        if ability is None:
            continue
        seq.add_ability(float(placement["cast_time"]), ability)
    return seq


def _rotation(rot: dict, spec: dict, abilities: dict, cache: dict) -> Rotation:
    seqs = []
    for sid in rot["blocks"]:
        fs = spec["field_seqs"].get(sid)
        if fs is None:
            continue
        if sid not in cache:
            cache[sid] = _field_sequence(fs, spec, abilities)
        seqs.append(cache[sid])
    return Rotation(rot["name"], seqs, 1, rot.get("description", ""))


def _trial(payload: dict, spec: dict, abilities: dict) -> Trial:
    cache: dict = {}
    rotations = []
    for slot in payload["slots"]:
        rot = spec["rotations"].get(slot["rotation"])
        if rot is None:
            continue
        rotation = _rotation(rot, spec, abilities, cache)
        rotation.repetitions = max(1, int(slot.get("repeat", 1)))
        rotations.append(rotation)
    return Trial(payload["name"], rotations,
                 end_mode=payload.get("end_mode", "time"),
                 end_time=float(payload.get("end_time", 30.0)),
                 description=payload.get("description", ""))


def _blocks(payload: dict, spec: dict) -> list:
    """Block layout straight from the trial definition.

    Chaining matches add_field_sequence(): every block starts where the previous one
    swapped out, so the block bounds agree with the engine own schedule.
    """
    blocks = []
    t = 0.0
    for slot in payload["slots"]:
        rot = spec["rotations"].get(slot["rotation"])
        if rot is None:
            continue
        for rep in range(max(1, int(slot.get("repeat", 1)))):
            for index, sid in enumerate(rot["blocks"]):
                fs = spec["field_seqs"].get(sid)
                if fs is None:
                    continue
                end = t + float(fs["field_time"])
                blocks.append({
                    "id": slot["id"] + "~" + str(rep) + "~" + str(index),
                    "occurrence": slot["id"] + "~" + str(rep),
                    "rotation": rot["id"],
                    "rotation_name": rot["name"],
                    "field_seq": sid,
                    "character": fs["character"],
                    "start": round(t, 6),
                    "end": round(end, 6),
                })
                t = end
    return blocks


def _placement_index(blocks: list, spec: dict, abilities: dict) -> dict:
    """(character, ability, hit time) -> (block id, hit index, hit count).

    Built with the same arithmetic the engine uses, so a placed hit is matched
    exactly instead of guessed from the block bounds.
    """
    index = {}
    for block in blocks:
        fs = spec["field_seqs"][block["field_seq"]]
        for placement in fs["placements"]:
            ability = abilities.get(placement["ability"])
            if ability is None:
                continue
            cast = float(placement["cast_time"])
            hits = ability.hits or ()
            for position, hit in enumerate(hits):
                when = round(block["start"] + cast + hit.relative_delay, 6)
                index[(block["character"], placement["ability"], when)] = (
                    block["id"], position, len(hits))
    return index


def _block_for(blocks: list, character: str, t: float):
    """Best block for a hit the index did not match (a triggered one)."""
    same, any_char = None, None
    for block in blocks:
        if block["start"] <= t + 1e-9:
            any_char = block["id"]
            if block["character"] == character:
                same = block["id"]
    return same or any_char or (blocks[0]["id"] if blocks else None)


def _hits(events: list, blocks: list, index: dict) -> list:
    """Engine events -> the hit rows the strips and tables read.

    ``reaction`` marks a Stellar Swirl / Vortex explosion: those rows carry the
    engine's STELLAR_REACTION category and their own reaction metadata, and the
    strips leave them out of the building view (ui/editor/payloads.py) while the
    totals, the rotation log and the results table keep them.
    """
    out = []
    for event in events:
        if event.get("event_type") != "HIT":
            continue
        name = event.get("character") or ""
        cid = catalog.character_id(name)
        t = round(float(event.get("global_time") or 0.0), 6)
        ability_name = event.get("ability_name") or event.get("hit_name") or ""
        aid = catalog.ability_id(name, ability_name)
        match = index.get((cid, aid, t))
        if match:
            block_id, hit_index, hit_count = match
        else:
            block_id = _block_for(blocks, cid, t)
            hit_index, hit_count = 0, 1
        out.append({
            "t": t,
            "ability": aid,
            "ability_name": ability_name,
            "character": cid,
            "block": block_id,
            "damage": float(event.get("average_damage") or 0.0),
            "hit_index": hit_index,
            "hit_count": hit_count,
            "on_field": event.get("active_character") == name,
            "reaction": event.get("category") == ActionCategory.STELLAR_REACTION,
        })
    return out


def _aggregate(hits: list, blocks: list):
    by_block = {block["id"]: 0.0 for block in blocks}
    by_character: dict = {}
    by_ability: dict = {}
    for hit in hits:
        by_block[hit["block"]] = by_block.get(hit["block"], 0.0) + hit["damage"]
        key = hit["character"]
        by_character[key] = by_character.get(key, 0.0) + hit["damage"]
        slot = by_ability.setdefault(hit["ability"], {
            "name": hit["ability_name"], "character": key,
            "damage": 0.0, "hits": 0})
        slot["damage"] += hit["damage"]
        slot["hits"] += 1
    return by_block, by_character, by_ability



def _totals(hits: list, analytics: dict, duration: float) -> dict:
    """The four numbers the editor shows: damage, DPS, hits, duration."""
    return {
        "damage": float(analytics.get("total_damage") or 0.0),
        "dps": float(analytics.get("overall_dps") or 0.0),
        "hits": len(hits),
        "duration": float(duration),
    }


def _issue(severity: str, message: str, where=("trial", "")) -> dict:
    return {"severity": severity, "message": message, "where": where}


def _empty(blocks: list, warnings: list) -> dict:
    totals = {"damage": 0.0, "dps": 0.0, "hits": 0, "duration": 0.0}
    return {"blocks": blocks, "hits": [], "events": [], "by_block": {},
            "by_character": {}, "by_ability": {}, "totals": totals,
            "warnings": warnings}


def simulate(spec: dict, trial_id: str, party: dict, enemy: dict | None = None) -> dict:
    """Run one trial of the spec and return what the editor draws."""
    payload = (spec.get("trials") or {}).get(trial_id)
    if payload is None:
        return _empty([], [_issue("error", "This trial no longer exists.",
                                  ("trial", trial_id))])
    blocks = _blocks(payload, spec)
    abilities = ability_map(spec)
    trial = _trial(payload, spec, abilities)
    timeline = RotationTimeline(party=copy.deepcopy(party or {}),
                                enemy_stats=dict(enemy or {}))
    try:
        duration = timeline.add_trial(trial)
        timeline.evaluate_timeline()
    except CooldownError as exc:
        message = (f"{exc.character} {exc.ability_name} is on cooldown "
                   f"until {exc.until:.3f}s.")
        return _empty(blocks, [_issue("error", message, ("trial", trial_id))])
    index = _placement_index(blocks, spec, abilities)
    hits = _hits(timeline.global_events, blocks, index)
    by_block, by_character, by_ability = _aggregate(hits, blocks)
    analytics = timeline.get_analytics_summary(duration)
    return {
        "blocks": blocks,
        "hits": hits,
        "events": timeline.global_events,
        "by_block": by_block,
        "by_character": by_character,
        "by_ability": by_ability,
        "totals": _totals(hits, analytics, duration),
        "warnings": [],
    }

