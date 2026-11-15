"""Payload builders: Python decides what a strip draws, the JS only draws it.

Every builder returns the flat shape strips.py documents: rows, absolutely
positioned items, a cursor and a zoom. Nothing here touches the engine.
"""

from __future__ import annotations

from ui.editor import engine


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


def _hit_items(spec: dict, hits: list, selected=None) -> list:
    """One tick per hit. ``off`` dims a hit whose owner was not on field.

    That flag is a paint cue only, straight from the engine's ``on_field``: the
    strip dims a hit that resolved from the backline (an ability tail after the
    swap, a trigger fired by someone else). No number is derived from it.
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
            "title": "%s #%d \u00b7 %s \u00b7 %.2fs" % (hit["ability_name"],
                     hit["hit_index"] + 1, format(hit["damage"], ",.0f"), hit["t"]),
        })
    return items


def trial_payload(spec: dict, trial_id: str, result: dict, *, selected=None,
                  cursor=None, px_per_sec: float = 0.0) -> dict:
    """The whole trial: one lane per character, one band per field sequence."""
    chars = spec["catalog"]["characters"]
    blocks, hits = result["blocks"], result["hits"]
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
            "label": "",
            "title": "%s / %s  %.2fs - %.2fs" % (
                block["rotation_name"], sequence.get("name", ""),
                block["start"], block["end"]),
            "color": colour,
            "draggable": False,
            "dim": duration > 0 and block["start"] > duration + 1e-9,
            "selected": selected == ("block", block["id"]),
        })
    items.extend(_hit_items(spec, hits, selected))
    return {
        "tMax": max(duration, 1.0),
        "rows": _rows(spec, _row_ids(blocks, hits)),
        "items": _stagger(items),
        "cursor": cursor,
        "pxPerSec": px_per_sec,
    }


def rotation_seconds(spec: dict, rotation_id: str) -> float:
    """One pass through a rotation: the sum of its blocks field times."""
    rotation = spec["rotations"].get(rotation_id) or {}
    return sum(float(spec["field_seqs"][block]["field_time"])
               for block in rotation.get("blocks", []) if block in spec["field_seqs"])


def rotation_preview(spec: dict, rotation_id: str, party: dict, enemy: dict) -> dict:
    """Simulate one rotation twice: the second pass exposes the loop seam."""
    rotation = spec["rotations"][rotation_id]
    probe = {
        "id": "__preview__",
        "name": rotation["name"] + " (preview)",
        "description": "",
        "end_mode": "last_swap",
        "end_time": 0.0,
        "required_party": [],
        "slots": [{"id": "__preview__~0", "rotation": rotation_id, "repeat": 2}],
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
    hits = [hit for hit in preview["hits"] if hit["block"] in ids]

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
            "label": "",
            "title": "%s  %.2fs - %.2fs" % (sequence.get("name", ""), block["start"], block["end"]),
            "color": colour,
            "draggable": False,
            "selected": selected == ("block", block["id"]),
        })
    items.extend(_hit_items(spec, hits, selected))
    items.append({"kind": "marker", "t": 0.0, "label": "loop start", "kind2": "in", "draggable": False})
    items.append({"kind": "marker", "t": round(loop_time, 3),
                  "label": "loop end %.2fs" % loop_time, "kind2": "seam", "draggable": False})
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
        first = float(placement["first_hit"])
        last = max((hit["offset"] for hit in ability["hits"]), default=0.0)
        residual = sum(1 for hit in ability["hits"] if first + hit["offset"] > field_time + 1e-9)
        items.append({
            "kind": "band",
            "row": row_id,
            "id": placement["id"],
            "refKind": "placement",
            "start": first,
            "end": first + last,
            "label": ability["name"],
            "title": "%s  first hit %.2fs, last hit %.2fs" % (
                ability["name"], first, first + last),
            "color": colour,
            # Display only: the field time is set by the number box. The bar is the
            # ability's runtime, so it is faded and sits behind its own hit ticks.
            "draggable": False,
            "dim": False,
            "soft": True,
            "minPx": 14,
            "tailFrom": field_time if residual else None,
            "selected": selected == ("placement", placement["id"]),
        })
        for index, hit in enumerate(ability["hits"]):
            when = first + hit["offset"]
            items.append({
                "kind": "hit",
                "row": row_id,
                "id": ability["id"],
                "t": round(when, 6),
                "color": colour,
                "crit": False,
                "off": when > field_time + 1e-9,
                "selected": False,
                "title": "hit #%d . %.2fs" % (index + 1, when),
            })
    items.append({"kind": "marker", "t": 0.0, "label": "swap in", "kind2": "in", "draggable": False})
    items.append({"kind": "marker", "t": field_time, "label": "swap out %.1fs" % field_time,
                  "kind2": "out", "draggable": False})
    return {
        "tMax": max(field_time, 1.0) * 1.05,
        "rows": rows,
        "items": _stagger(items),
        "cursor": cursor,
        "pxPerSec": px_per_sec,
    }
