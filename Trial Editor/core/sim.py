"""Reference simulation engine.

`simulate(spec_dict) -> result_dict` is a **pure function of its input**. Drop
your real engine in here: keep the signature and the result keys, and every
screen keeps working. That is the whole adapter contract.

Pipeline
--------
1. expand trial -> slots -> rotation blocks -> field sequences -> placements -> hits
2. resolve triggered abilities breadth-first (bounded depth, so a trigger loop
   can never hang the app)
3. merge buff applications into disjoint intervals that carry a stack count
4. price every hit against the buffs active at its timestamp
5. truncate to the trial duration, then aggregate
"""

from __future__ import annotations

import math
from typing import Any

from .models import Spec

MAX_TRIGGER_DEPTH = 4
CRIT_MULTIPLIER = 1.5
EPS = 1e-9


def _active_stacks(apps: list[dict], cat, t: float) -> dict[str, int]:
    """Stack count per buff at time `t` (start inclusive, end exclusive)."""
    stacks: dict[str, int] = {}
    for app in apps:
        buff = cat.buffs[app["buff"]]
        if app["t"] <= t + EPS < app["t"] + buff.duration - EPS:
            stacks[buff.id] = min(stacks.get(buff.id, 0) + 1, buff.max_stacks)
    return stacks


def _trigger_matches(trigger: dict, src: dict) -> bool:
    on = trigger.get("on")
    if on == "crit":
        return bool(src["crit"])
    if on == "ability_end":
        return src["ability"] == trigger.get("ability") and src["hit_index"] == src["hit_count"] - 1
    return False


def _buff_segments(apps: list[dict], cat) -> list[dict]:
    """Disjoint [start, end) intervals per buff, merged when stacks are equal."""
    by_buff: dict[str, list[float]] = {}
    for app in apps:
        by_buff.setdefault(app["buff"], []).append(app["t"])

    out: list[dict] = []
    for buff_id, times in by_buff.items():
        buff = cat.buffs[buff_id]
        times = sorted(times)
        bounds = sorted({round(x, 6) for x in times} | {round(x + buff.duration, 6) for x in times})
        segs: list[dict] = []
        for a, b in zip(bounds, bounds[1:]):
            if b - a <= EPS:
                continue
            stacks = sum(1 for t in times if t <= a + EPS < t + buff.duration - EPS)
            if stacks <= 0:
                continue
            stacks = min(stacks, buff.max_stacks)
            if segs and abs(segs[-1]["end"] - a) <= 1e-6 and segs[-1]["stacks"] == stacks:
                segs[-1]["end"] = b
            else:
                segs.append({"buff": buff_id, "start": a, "end": b, "stacks": stacks})
        out.extend(segs)
    return out


def _group(segments: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for seg in segments:
        out.setdefault(seg["buff"], []).append(seg)
    for segs in out.values():
        segs.sort(key=lambda s: s["start"])
    return out


def simulate(spec_dict: dict[str, Any]) -> dict[str, Any]:
    spec = Spec.from_dict(spec_dict)
    cat = spec.catalog

    hits: list[dict] = []
    blocks: list[dict] = []
    apps: list[dict] = []  # buff applications: {buff, t, source, character}
    seq = 0

    # -- 1. expand the authored structure -----------------------------------
    t = 0.0
    for slot in spec.trial.slots:
        rotation = spec.rotations.get(slot.rotation)
        if rotation is None:
            continue
        for rep in range(max(1, int(slot.repeat))):
            for bi, fs_id in enumerate(rotation.blocks):
                fs = spec.field_seqs.get(fs_id)
                if fs is None:
                    continue
                start, end = t, t + max(fs.field_time, 0.0)
                block = {
                    "id": f"{slot.id}~{rep}~{bi}",
                    "occurrence": f"{slot.id}~{rep}",
                    "rotation": rotation.id,
                    "rotation_name": rotation.name,
                    "field_seq": fs.id,
                    "character": fs.character,
                    "start": start,
                    "end": end,
                    "repeat_index": rep,
                }
                blocks.append(block)

                for placement in fs.placements:
                    ability = cat.abilities.get(placement.ability)
                    if ability is None:
                        continue
                    for i, hit in enumerate(ability.hits):
                        ht = start + placement.first_hit + hit.offset
                        hits.append(
                            {
                                "t": ht,
                                "ability": ability.id,
                                "ability_name": ability.name,
                                "character": ability.character,
                                "placement": placement.id,
                                "block": block["id"],
                                "raw": hit.raw,
                                "crit": hit.crit,
                                "hit_index": i,
                                "hit_count": len(ability.hits),
                                "source": "ability",
                                "seq": seq,
                            }
                        )
                        seq += 1
                        if ability.buff and i == ability.buff_at:
                            apps.append(
                                {"buff": ability.buff, "t": ht, "source": ability.id, "character": ability.character}
                            )
                t = end

    # -- 2. triggered abilities (may fire for an off-field character) --------
    fired: set[tuple] = set()
    frontier = list(hits)
    trigger_log: list[dict] = []
    for _ in range(MAX_TRIGGER_DEPTH):
        spawned: list[dict] = []
        for ability in cat.abilities.values():
            trigger = ability.trigger
            if ability.category != "triggered" or not trigger:
                continue
            delay = float(trigger.get("delay", 0.0))
            for src in frontier:
                if not _trigger_matches(trigger, src):
                    continue
                key = (ability.id, src["block"], src["placement"], src["ability"], src["hit_index"])
                if key in fired:
                    continue
                fired.add(key)
                base = src["t"] + delay
                trigger_log.append(
                    {
                        "t": base,
                        "ability": ability.id,
                        "ability_name": ability.name,
                        "character": ability.character,
                        "block": src["block"],
                        "caused_by": src["ability_name"],
                    }
                )
                for i, hit in enumerate(ability.hits):
                    ht = base + hit.offset
                    spawned.append(
                        {
                            "t": ht,
                            "ability": ability.id,
                            "ability_name": ability.name,
                            "character": ability.character,
                            "placement": None,
                            "block": src["block"],
                            "raw": hit.raw,
                            "crit": hit.crit,
                            "hit_index": i,
                            "hit_count": len(ability.hits),
                            "source": "triggered",
                            "seq": seq,
                        }
                    )
                    seq += 1
                    if ability.buff and i == ability.buff_at:
                        apps.append(
                            {"buff": ability.buff, "t": ht, "source": ability.id, "character": ability.character}
                        )
        if not spawned:
            break
        hits.extend(spawned)
        frontier = spawned

    # -- 3. buff intervals ---------------------------------------------------
    segments = _buff_segments(apps, cat)

    # -- 4. price every hit --------------------------------------------------
    for hit in hits:
        stacks = _active_stacks(apps, cat, hit["t"])
        buff_mult = 1.0
        logs: dict[str, float] = {}
        for buff_id, count in stacks.items():
            factor = 1.0 + cat.buffs[buff_id].per_stack * count
            buff_mult *= factor
            logs[buff_id] = math.log(factor)
        crit = CRIT_MULTIPLIER if hit["crit"] else 1.0

        hit["multiplier"] = buff_mult * crit
        hit["damage"] = hit["raw"] * buff_mult * crit
        hit["active_buffs"] = sorted(cat.buffs[b].name for b in stacks)
        # Kept for attribution: what the buffs added, and how to split it up.
        hit["buff_lift"] = hit["raw"] * crit * (buff_mult - 1.0)
        hit["buff_logs"] = logs
        hit["on_field"] = any(
            b["character"] == hit["character"] and b["start"] - EPS <= hit["t"] < b["end"] - EPS for b in blocks
        )

    # -- 5. truncate + aggregate --------------------------------------------
    duration = max(0.0, float(spec.trial.duration))
    kept = sorted((h for h in hits if h["t"] <= duration + EPS), key=lambda h: (h["t"], h["seq"]))
    truncated = len(hits) - len(kept)

    for block in blocks:
        block["beyond"] = block["start"] > duration + EPS

    by_character: dict[str, float] = {c: 0.0 for c in cat.characters}
    by_ability: dict[str, dict] = {}
    by_block: dict[str, float] = {}
    for hit in kept:
        by_character[hit["character"]] = by_character.get(hit["character"], 0.0) + hit["damage"]
        slot = by_ability.setdefault(
            hit["ability"],
            {"name": hit["ability_name"], "character": hit["character"], "damage": 0.0, "hits": 0},
        )
        slot["damage"] += hit["damage"]
        slot["hits"] += 1
        by_block[hit["block"]] = by_block.get(hit["block"], 0.0) + hit["damage"]

    rows = _event_rows(blocks, kept, trigger_log, segments, cat, duration)
    total = sum(h["damage"] for h in kept)

    return {
        "blocks": blocks,
        "hits": kept,
        "events": rows,
        "buffs": [s for s in segments if s["start"] <= duration + EPS],
        "buff_attribution": _buff_summary(segments, kept, cat, duration, total),
        "by_character": by_character,
        "by_ability": by_ability,
        "by_block": by_block,
        "totals": {
            "damage": total,
            "dps": total / duration if duration > 0 else 0.0,
            "hits": len(kept),
            "duration": duration,
            "content_length": t,
            "truncated_hits": truncated,
            "residual_hits": sum(1 for h in kept if not h["on_field"]),
            "triggered_hits": sum(1 for h in kept if h["source"] == "triggered"),
        },
        "fired_triggers": sorted({log["ability"] for log in trigger_log}),
        "trigger_conditions": {
            a.id: a.trigger for a in cat.abilities.values() if a.category == "triggered" and a.trigger
        },
    }


def _buff_summary(segments, kept, cat, duration, total) -> list[dict]:
    """Per-buff uptime and the damage that buff actually added.

    Attribution uses a log decomposition of the multiplicative stack:
    with `mult = prod(1 + p_i * s_i)`, each buff's share of the total lift is
    `ln(1 + p_i*s_i) / sum(ln(...))`. That is order-independent and, unlike
    "remove one buff at a time", the shares add up exactly to the lift - so the
    baseline (no buffs at all) plus every attribution equals the reported total.
    """
    attribution = {buff_id: 0.0 for buff_id in cat.buffs}
    for hit in kept:
        logs = hit["buff_logs"]
        total_log = sum(logs.values())
        if total_log <= 0:
            continue
        for buff_id, weight in logs.items():
            attribution[buff_id] += hit["buff_lift"] * (weight / total_log)

    rows: list[dict] = []
    for buff_id, buff in cat.buffs.items():
        covered = 0.0
        stack_seconds = 0.0
        for seg in segments:
            if seg["buff"] != buff_id:
                continue
            start = seg["start"]
            end = min(seg["end"], duration)
            if end <= start:
                continue
            covered += end - start
            stack_seconds += (end - start) * seg["stacks"]

        added = attribution[buff_id]
        rows.append(
            {
                "buff": buff_id,
                "name": buff.name,
                "color": buff.color,
                "uptime": covered / duration if duration > 0 else 0.0,
                "avg_stacks": stack_seconds / duration if duration > 0 else 0.0,
                "stack_seconds": stack_seconds,
                "added": added,
                "share": added / total if total > 0 else 0.0,
            }
        )
    rows.sort(key=lambda row: row["added"], reverse=True)
    return rows


def _event_rows(blocks, kept, trigger_log, segments, cat, duration) -> list[dict]:
    """The table's ground truth: hits, swaps, trigger firings, buff expiries."""
    rows: list[dict] = []
    for block in blocks:
        name = cat.characters[block["character"]].name
        rows.append(
            {
                "t": block["start"],
                "kind": "swap_in",
                "character": block["character"],
                "label": f"Swap in {name}",
                "damage": None,
                "source": "block",
                "block": block["id"],
            }
        )
        rows.append(
            {
                "t": block["end"],
                "kind": "swap_out",
                "character": block["character"],
                "label": f"Swap out {name}",
                "damage": None,
                "source": "block",
                "block": block["id"],
            }
        )
    for hit in kept:
        rows.append(
            {
                "t": hit["t"],
                "kind": "crit" if hit["crit"] else "hit",
                "character": hit["character"],
                "label": f"{hit['ability_name']} #{hit['hit_index'] + 1}",
                "damage": hit["damage"],
                "source": hit["source"],
                "block": hit["block"],
            }
        )
    for log in trigger_log:
        if log["t"] > duration + EPS:
            continue
        rows.append(
            {
                "t": log["t"],
                "kind": "trigger",
                "character": log["character"],
                "label": f"{log['ability_name']} (from {log['caused_by']})",
                "damage": None,
                "source": "triggered",
                "block": log["block"],
            }
        )
    for buff_id, segs in _group(segments).items():
        prev_end = None
        for seg in segs:
            if prev_end is not None and seg["start"] - prev_end > EPS:
                rows.append(_expiry(cat, buff_id, prev_end, duration))
            prev_end = seg["end"]
        if prev_end is not None:
            rows.append(_expiry(cat, buff_id, prev_end, duration))
    rows = [r for r in rows if r["t"] <= duration + EPS]
    rows.sort(key=lambda r: r["t"])
    return rows


def _expiry(cat, buff_id: str, t: float, duration: float) -> dict:
    return {
        "t": t,
        "kind": "buff_end",
        "character": "",
        "label": f"{cat.buffs[buff_id].name} expired",
        "damage": None,
        "source": "buff",
        "block": None,
    }


