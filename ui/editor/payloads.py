"""Payload builders: Python decides what a strip draws, the JS only draws it.

Every builder returns the flat shape strips.py documents: rows, absolutely
positioned items, a cursor and a zoom. Nothing here touches the engine.
"""

from __future__ import annotations

from models import interrupted_hit_count
import buff_registry
from ui.editor import engine


# Buff lanes are colour-coded by what grants them, so a strip of several windows
# stays readable at a glance: weapons gold, artifact sets green, team auras blue.
BUFF_COLOURS = {"Weapon": "#b99349", "Artifact": "#4f9d7a", "Team": "#6f8fc4"}
_BUFF_COLOUR_FALLBACK = "#9aa4b2"


def _stagger(items: list) -> list:
    """Nudge apart hits that share a row and an instant, or one hides the other.
"""
    groups: dict = {}
    for item in items:
        if item.get("kind") == "hit":
            groups.setdefault((item["row"], round(item["t"], 6)), []).append(item)
    for group in groups.values():
        if len(group) < 2:
            continue
        span = len(group) - 1
        for index, item in enumerate(group):
            item["dx"] = round((index - span / 2) * 3.2, 2)
    return items


def _rows(spec: dict, characters: list) -> list:
    chars = spec["catalog"]["characters"]
    return [{"id": "c_" + cid, "label": chars[cid]["name"], "kind": "lane",
             "color": chars[cid]["color"]} for cid in characters if cid in chars]


def _row_ids(blocks: list, hits: list) -> list:
    order: list = []
    for block in blocks:
        if block["character"] not in order:
            order.append(block["character"])
    for hit in hits:
        if hit["character"] not in order:
            order.append(hit["character"])
    return order


def _strip_hits(hits: list) -> list:
    """The ticks a strip draws: reaction results stay out of the building view.

    A Stellar Swirl / Vortex explosion is what the rotation *produces*, not part
    of building it: it lands on whichever lane happened to own the trigger and
    doubles the tick count the author is reading. The engine's rows keep them, so
    the totals, the rotation log and the results table are unchanged - only the
    strips drop them.
    """
    return [hit for hit in hits if not hit.get("reaction")]


def _hit_items(spec: dict, hits: list, selected=None) -> list:
    """One tick per hit. ``off`` dims a hit whose owner was not on field.

    That flag is a paint cue only, straight from the engine's ``on_field``: the
    strip dims a hit that resolved from the backline (an ability tail after the
    swap, a trigger fired by someone else). No number is derived from it.

    Callers pass the authored hits only (``_strip_hits``): Stellar reaction rows
    are not drawn.
    """
    chars = spec["catalog"]["characters"]
    items = []
    for hit in hits:
        character = chars.get(hit["character"], {})
        items.append({
            "kind": "hit",
            "row": "c_" + hit["character"],
            "id": hit["ability"],
            "t": hit["t"],
            "color": character.get("color", "#9aa4b2"),
            "crit": False,
            "off": not hit.get("on_field", True),
            "selected": selected is not None and selected[0] == "hit"
                        and abs(float(selected[1]) - hit["t"]) < 1e-6,
            "title": "%s #%d \u00b7 %s \u00b7 %.3fs" % (hit["ability_name"],
                     hit["hit_index"] + 1, format(hit["damage"], ",.0f"), hit["t"]),
        })
    return items


def _buff_windows(events: list, key: str) -> list:
    """[(start, end), ...] - one window per contiguous run of ON samples.

    The engine writes every audit flag on EVERY event ("ON"/"OFF"), so a run is
    dense: its bounds are the first and the last event that saw the buff up. A
    window therefore ends where the rotation provably stopped enjoying it - the
    strip draws the sampled uptime, not the theoretical expiry it cannot know.
    """
    windows: list = []
    start = last = None
    for event in events:
        when = float(event.get("global_time") or 0.0)
        if buff_registry.buff_is_active(event.get(key)):
            if start is None:
                start = when
            last = when
        elif start is not None:
            windows.append((start, last))
            start = last = None
    if start is not None:
        windows.append((start, last))
    return windows


def _buff_lane_items(result: dict, party, duration: float) -> tuple:
    """Buff uptime lanes, drawn under the character lanes of a trial strip.

    A lane exists only when the effect is BOTH equipped (buff_registry.strip_buffs
    applies the same gate as the audit table) AND actually triggered somewhere in
    this trial: an empty row would just push the strips the author is reading out
    of view. The bars carry no text - the lane label names the buff - because a
    30s window at 14px/s is thinner than its own name.
    """
    events = result.get("events") or []
    rows, items = [], []
    for entry in buff_registry.strip_buffs(party):
        windows = _buff_windows(events, entry["key"])
        if not windows:
            continue
        row_id = "b_" + entry["key"]
        colour = BUFF_COLOURS.get(entry["group"], _BUFF_COLOUR_FALLBACK)
        label = entry.get("strip") or entry["label"]
        rows.append({"id": row_id, "label": label, "kind": "buff", "color": colour})
        for start, end in windows:
            # Clamp to the trial: a window that runs to the end must not stretch the
            # canvas past tMax (which would add a phantom horizontal scroll).
            start = min(start, duration) if duration else start
            end = min(end, duration) if duration else end
            items.append({
                # A seg, not a band: an 8px pill is a read-out, it has no text, no
                # drag handle and no click handler - the lane label names the buff.
                "kind": "seg",
                "row": row_id,
                "id": entry["key"],
                "refKind": "buff",
                "start": round(start, 6),
                "end": round(end, 6),
                "color": colour,
                # .seg opacity is 0.3 + 0.2 * stacks; 1 keeps it a calm 0.5 so the
                # character lanes stay the loudest thing on the strip.
                "stacks": 1,
                "title": "%s  %.3fs - %.3fs (%.3fs up)" % (
                    entry["label"], start, end, max(0.0, end - start)),
            })
    return rows, items


def trial_payload(spec: dict, trial_id: str, result: dict, *, party=None, selected=None,
                  cursor=None, px_per_sec: float = 0.0) -> dict:
    """The whole trial: one lane per character, one band per field sequence.

    With *party* (the gear-aware party that was simulated) the strip also gets the
    uptime lanes of the equipment / aura buffs worth watching - see
    _buff_lane_items. Without it the payload is exactly what it used to be, which
    is what the rotation and field-sequence strips pass.
    """
    chars = spec["catalog"]["characters"]
    # Reaction rows stay out of the strip (see _strip_hits), and the lanes follow:
    # a character who only ever shows up as a swirl's contributor gets no lane here.
    blocks, hits = result["blocks"], _strip_hits(result["hits"])
    duration = result["totals"]["duration"]

    items = []
    for block in blocks:
        colour = chars.get(block["character"], {}).get("color", "#9aa4b2")
        sequence = spec["field_seqs"].get(block["field_seq"], {})
        items.append({
            "kind": "band",
            "row": "c_" + block["character"],
            "id": block["id"],
            "refKind": "block",
            "start": block["start"],
            "end": block["end"],
            "label": sequence.get("name", ""),
            "title": "%s / %s  %.3fs - %.3fs" % (
                block["rotation_name"], sequence.get("name", ""),
                block["start"], block["end"]),
            "color": colour,
            "draggable": False,
            "dim": duration > 0 and block["start"] > duration + 1e-9,
            # Same band as the field-sequence strip: a faded bar with its name in it
            # and a minimum width, never a lane-filling block.
            "soft": True,
            "minPx": 14,
            "selected": selected == ("block", block["id"]),
        })
    items.extend(_hit_items(spec, hits, selected))
    rows = _rows(spec, _row_ids(blocks, hits))
    buff_rows, buff_items = ([], []) if party is None else _buff_lane_items(result, party, duration)
    return {
        "tMax": max(duration, 1.0),
        "rows": rows + buff_rows,
        "items": _stagger(items + buff_items),
        "cursor": cursor,
        "pxPerSec": px_per_sec,
    }


def rotation_seconds(spec: dict, rotation_id: str) -> float:
    """One pass through a rotation: the sum of its blocks field times."""
    rotation = spec["rotations"].get(rotation_id) or {}
    return sum(float(spec["field_seqs"][block]["field_time"])
               for block in rotation.get("blocks", []) if block in spec["field_seqs"])


def _tail_slack(spec: dict, rotation: dict) -> float:
    """How long after the seam the last hit of this loop can still land."""
    abilities = spec["catalog"]["abilities"]
    sequences = spec["field_seqs"]
    slack = 0.0
    for block in rotation.get("blocks") or []:
        sequence = sequences.get(block)
        if sequence is None:
            continue
        end = float(sequence["field_time"])
        for placement in sequence["placements"]:
            ability = abilities.get(placement["ability"]) or {}
            last = max((hit["delay"] for hit in ability.get("hits") or ()), default=0.0)
            slack = max(slack, float(placement["cast_time"]) + last - end)
    return max(slack, 0.0) + 0.5


def rotation_preview(spec: dict, rotation_id: str, party: dict, enemy: dict) -> dict:
    """Simulate one loop, in a window long enough for its tails to resolve.

    Playing the loop twice (as this used to) made the engine reject every loop
    shorter than its own cooldowns: the second pass re-casts each ability inside
    its cooldown and CooldownError threw the whole preview away, so only the
    longest loop ever worked. One play is what a loop is; the extended window
    keeps the hits that land after the seam.
    """
    rotation = spec["rotations"][rotation_id]
    loop_time = rotation_seconds(spec, rotation_id)
    probe = {
        "id": "__preview__",
        "name": rotation["name"] + " (preview)",
        "description": "",
        "end_mode": "time",
        "end_time": round(loop_time + _tail_slack(spec, rotation), 3),
        "required_party": [],
        "slots": [{"id": "__preview__~0", "rotation": rotation_id, "repeat": 1}],
        "preset": True,
    }
    scratch = dict(spec)
    scratch["trials"] = dict(spec["trials"])
    scratch["trials"][probe["id"]] = probe
    return engine.simulate(scratch, probe["id"], party, enemy)


def rotation_payload(spec: dict, rotation_id: str, preview: dict, *, selected=None,
                     cursor=None, px_per_sec: float = 0.0) -> dict:
    """One loop of a rotation; a hit that resolves after the seam still belongs to it."""
    chars = spec["catalog"]["characters"]
    loop_time = rotation_seconds(spec, rotation_id)
    blocks = [block for block in preview["blocks"] if block["start"] < loop_time - 1e-9]
    ids = {block["id"] for block in blocks}
    hits = _strip_hits([hit for hit in preview["hits"] if hit["block"] in ids])

    items = []
    for block in blocks:
        colour = chars.get(block["character"], {}).get("color", "#9aa4b2")
        sequence = spec["field_seqs"].get(block["field_seq"], {})
        items.append({
            "kind": "band",
            "row": "c_" + block["character"],
            "id": block["id"],
            "refKind": "block",
            "start": block["start"],
            "end": block["end"],
            "label": sequence.get("name", ""),
            "title": "%s  %.3fs - %.3fs" % (sequence.get("name", ""), block["start"], block["end"]),
            "color": colour,
            # Display only: the field time is set by the number box. The bar is the
            # ability's runtime, so it is faded and sits behind its own hit ticks.
            "draggable": False,
            "dim": False,
            "soft": True,
            "minPx": 14,
            "selected": selected == ("block", block["id"]),
        })
    items.extend(_hit_items(spec, hits, selected))
    items.append({"kind": "marker", "t": 0.0, "label": "loop start", "kind2": "in", "draggable": False})
    items.append({"kind": "marker", "t": round(loop_time, 3),
                  "label": "loop end %.3fs" % loop_time, "kind2": "seam", "draggable": False})
    tail = max([hit["t"] for hit in hits] + [loop_time]) - loop_time
    return {
        "tMax": max(loop_time + max(tail, 0.0), 1.0),
        "rows": _rows(spec, _row_ids(blocks, hits)),
        "items": _stagger(items),
        "cursor": cursor,
        "pxPerSec": px_per_sec,
    }


def field_sequence_payload(spec: dict, sequence_key: str, *, selected=None,
                           cursor=None, px_per_sec: float = 0.0) -> dict:
    """Focus mode: one row per placement, plus the swap-in / swap-out markers."""
    chars = spec["catalog"]["characters"]
    abilities = spec["catalog"]["abilities"]
    sequence = spec["field_seqs"].get(sequence_key)
    if sequence is None:
        return {"tMax": 1.0, "rows": [], "items": [], "cursor": cursor, "pxPerSec": px_per_sec}
    colour = chars.get(sequence["character"], {}).get("color", "#9aa4b2")
    field_time = float(sequence["field_time"])

    rows, items = [], []
    for placement in sequence["placements"]:
        ability = abilities.get(placement["ability"])
        if ability is None:
            continue
        row_id = "p_" + placement["id"]
        rows.append({"id": row_id, "label": ability["name"], "kind": "lane", "color": colour})
        cast = float(placement["cast_time"])
        base = float(ability.get("first_hit_delay", 0.0))
        first = cast + base
        times = [cast + float(hit["delay"]) for hit in ability["hits"]]
        kept = times
        if ability.get("interrupt_on_swap_out"):
            kept = times[:interrupted_hit_count(times, field_time)]
        last = kept[-1] if kept else first
        interrupted = len(kept) < len(times)
        items.append({
            "kind": "band",
            "row": row_id,
            "id": placement["id"],
            "refKind": "placement",
            "start": cast,
            "end": last,
            "label": ability["name"],
            "title": "%s  cast %.3fs, first hit %.3fs, last hit %.3fs%s" % (
                ability["name"], cast, first, last,
                (", interrupted by the %.3fs swap-out (%d of %d hits land)"
                 % (field_time, len(kept), len(times))) if interrupted else ""),
            "color": colour,
            # Display only: the field time is set by the number box. The bar is the
            # ability's runtime, so it is faded and sits behind its own hit ticks.
            "draggable": False,
            "dim": False,
            "soft": True,
            "minPx": 14,
            "tailFrom": field_time if (interrupted and last > field_time + 1e-9) else None,
            "selected": selected == ("placement", placement["id"]),
        })
        for index, hit in enumerate(ability["hits"][:len(kept)]):
            when = cast + float(hit["delay"])
            items.append({
                "kind": "hit",
                "row": row_id,
                "id": ability["id"],
                "t": round(when, 6),
                "color": colour,
                "crit": False,
                "off": when > field_time + 1e-9,
                "selected": False,
                "title": "hit #%d . %.3fs" % (index + 1, when),
            })
    items.append({"kind": "marker", "t": 0.0, "label": "swap in", "kind2": "in", "draggable": False})
    items.append({"kind": "marker", "t": field_time, "label": "swap out %.3fs" % field_time,
                  "kind2": "out", "draggable": False})
    return {
        "tMax": max(field_time, 1.0) * 1.05,
        "rows": rows,
        "items": _stagger(items),
        "cursor": cursor,
        "pxPerSec": px_per_sec,
    }
