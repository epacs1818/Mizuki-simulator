"""Spec mutations: the only place that writes to the editor spec.

Pure functions on plain dicts - no Streamlit - so every rule (a preset is
read-only, a rotation that is still used cannot be deleted, ids stay unique) is
testable headlessly. The screens mutate, then rerun.
"""

from __future__ import annotations

import copy

from ui.editor import catalog

SECTIONS = ("trials", "rotations", "field_seqs")
LABELS = {"trials": "trial", "rotations": "rotation", "field_seqs": "field sequence"}
END_MODES = ("time", "last_swap")


def _section(spec: dict, section: str) -> dict:
    if section not in SECTIONS:
        raise ValueError("Unknown section %r." % (section,))
    return spec[section]


def _item(spec: dict, section: str, item_id: str) -> dict:
    item = _section(spec, section).get(item_id)
    if item is None:
        raise ValueError("That %s no longer exists." % LABELS[section])
    return item


def _writable(item: dict) -> None:
    """Presets are the shipped reference, not a starting point: copy them first."""
    if item.get("preset"):
        raise ValueError("Presets are read-only. Duplicate it first, then edit the copy.")


def unique_id(existing, base: str) -> str:
    base = catalog.slug(base) or "item"
    if base not in existing:
        return base
    index = 2
    while "%s_%d" % (base, index) in existing:
        index += 1
    return "%s_%d" % (base, index)


def duplicate(spec: dict, section: str, item_id: str) -> str:
    """Copy an entry into an editable twin; returns the new id."""
    source = _item(spec, section, item_id)
    twin = copy.deepcopy(source)
    twin["preset"] = False
    twin["name"] = source["name"] + " (copy)"
    new_id = unique_id(spec[section], item_id + "_copy")
    twin["id"] = new_id
    if section == "trials":
        twin["slots"] = [dict(slot, id=new_id + "~" + str(index))
                         for index, slot in enumerate(twin["slots"])]
    elif section == "field_seqs":
        twin["placements"] = [dict(placement, id=new_id + "~" + str(index))
                              for index, placement in enumerate(twin["placements"])]
    spec[section][new_id] = twin
    return new_id


def rename(spec: dict, section: str, item_id: str, name: str) -> None:
    item = _item(spec, section, item_id)
    _writable(item)
    name = (name or "").strip()
    if not name:
        raise ValueError("The name cannot be empty.")
    item["name"] = name


def delete(spec: dict, section: str, item_id: str) -> None:
    """Remove an entry, unless something still points at it."""
    item = _item(spec, section, item_id)
    _writable(item)
    if section == "rotations":
        users = [trial["name"] for trial in spec["trials"].values()
                 if any(slot["rotation"] == item_id for slot in trial["slots"])]
        if users:
            raise ValueError("Still used by: %s. Remove it from those trials first."
                             % ", ".join(users[:3]))
    elif section == "field_seqs":
        users = [rotation["name"] for rotation in spec["rotations"].values()
                 if item_id in rotation["blocks"]]
        if users:
            raise ValueError("Still used by: %s. Remove it from those rotations first."
                             % ", ".join(users[:3]))
    elif len(spec["trials"]) <= 1:
        raise ValueError("A spec needs at least one trial.")
    del spec[section][item_id]
    if spec.get("active_trial") == item_id:
        spec["active_trial"] = next(iter(spec["trials"]))


def new_trial(spec: dict, name: str, rotation_id: str | None = None,
              party=None) -> str:
    """A new trial, pinned to *party*: a trial belongs to the team it was built for."""
    new_id = unique_id(spec["trials"], catalog.slug(name) or "trial")
    slots = []
    if rotation_id:
        slots.append({"id": new_id + "~0", "rotation": rotation_id, "repeat": 1})
    characters = spec["catalog"]["characters"]
    spec["trials"][new_id] = {
        "id": new_id,
        "name": (name or "New trial").strip() or "New trial",
        "description": "",
        "end_mode": "time",
        "end_time": 30.0,
        "required_party": [cid for cid in (party or []) if cid in characters],
        "slots": slots,
        "preset": False,
    }
    return new_id


def new_rotation(spec: dict, name: str, party=None) -> str:
    """A new, empty rotation, owned by *party*.

    A rotation belongs to the team it was built for, so it is tagged with *party*
    here: the rotation list only offers loops that team can actually play.
    """
    new_id = unique_id(spec["rotations"], catalog.slug(name) or "rotation")
    characters = spec["catalog"]["characters"]
    spec["rotations"][new_id] = {
        "id": new_id,
        "name": (name or "New rotation").strip() or "New rotation",
        "blocks": [], "repeat": 1, "preset": False,
        "required_party": [cid for cid in (party or []) if cid in characters],
    }
    return new_id


def set_rotation_party(spec: dict, rotation_id: str, ids) -> None:
    """Pin a rotation to a team; an empty list means "whoever its blocks belong to"."""
    rotation = _item(spec, "rotations", rotation_id)
    _writable(rotation)
    characters = spec["catalog"]["characters"]
    rotation["required_party"] = [cid for cid in ids if cid in characters]


def new_sequence(spec: dict, name: str, character: str) -> str:
    new_id = unique_id(spec["field_seqs"], catalog.slug(name) or "sequence")
    spec["field_seqs"][new_id] = {"id": new_id,
                                  "name": (name or "New sequence").strip() or "New sequence",
                                  "character": character, "field_time": 1.0,
                                  "placements": [], "preset": False}
    return new_id


def set_trial_text(spec: dict, trial_id: str, *, name=None, description=None) -> None:
    trial = _item(spec, "trials", trial_id)
    _writable(trial)
    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("The name cannot be empty.")
        trial["name"] = name
    if description is not None:
        trial["description"] = description.strip()


def set_trial_end(spec: dict, trial_id: str, mode: str, seconds=None) -> None:
    trial = _item(spec, "trials", trial_id)
    _writable(trial)
    if mode not in END_MODES:
        raise ValueError("End mode must be one of: " + ", ".join(END_MODES))
    trial["end_mode"] = mode
    if seconds is not None:
        seconds = float(seconds)
        if seconds <= 0:
            raise ValueError("The trial must run for at least a moment.")
        trial["end_time"] = seconds


def set_trial_party(spec: dict, trial_id: str, ids) -> None:
    """Empty = any party; otherwise the runner only offers it to this team."""
    trial = _item(spec, "trials", trial_id)
    _writable(trial)
    characters = spec["catalog"]["characters"]
    trial["required_party"] = [cid for cid in ids if cid in characters]


def add_slot(spec: dict, trial_id: str, rotation_id: str, repeat: int = 1) -> str:
    trial = _item(spec, "trials", trial_id)
    _writable(trial)
    if rotation_id not in spec["rotations"]:
        raise ValueError("That rotation no longer exists.")
    slot_id = unique_id({slot["id"] for slot in trial["slots"]},
                        trial_id + "~" + rotation_id)
    trial["slots"].append({"id": slot_id, "rotation": rotation_id,
                           "repeat": max(1, int(repeat))})
    return slot_id


def remove_slot(spec: dict, trial_id: str, slot_id: str) -> None:
    trial = _item(spec, "trials", trial_id)
    _writable(trial)
    remaining = [slot for slot in trial["slots"] if slot["id"] != slot_id]
    if len(remaining) == len(trial["slots"]):
        raise ValueError("That slot no longer exists.")
    trial["slots"] = remaining


def move_slot(spec: dict, trial_id: str, slot_id: str, delta: int) -> None:
    trial = _item(spec, "trials", trial_id)
    _writable(trial)
    slots = trial["slots"]
    index = next((i for i, slot in enumerate(slots) if slot["id"] == slot_id), None)
    if index is None:
        raise ValueError("That slot no longer exists.")
    target = index + int(delta)
    if 0 <= target < len(slots):
        slots.insert(target, slots.pop(index))


def set_slot_repeat(spec: dict, trial_id: str, slot_id: str, repeat: int) -> None:
    trial = _item(spec, "trials", trial_id)
    _writable(trial)
    for slot in trial["slots"]:
        if slot["id"] == slot_id:
            slot["repeat"] = max(1, int(repeat))
            return
    raise ValueError("That slot no longer exists.")


def set_rotation_text(spec: dict, rotation_id: str, *, name=None, repeat=None) -> None:
    rotation = _item(spec, "rotations", rotation_id)
    _writable(rotation)
    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("The name cannot be empty.")
        rotation["name"] = name
    if repeat is not None:
        rotation["repeat"] = max(1, int(repeat))


def add_block(spec: dict, rotation_id: str, sequence_id: str, at=None) -> int:
    """Insert a field sequence into a rotation; returns its position."""
    rotation = _item(spec, "rotations", rotation_id)
    _writable(rotation)
    if sequence_id not in spec["field_seqs"]:
        raise ValueError("That field sequence no longer exists.")
    blocks = rotation["blocks"]
    index = len(blocks) if at is None else max(0, min(int(at), len(blocks)))
    blocks.insert(index, sequence_id)
    return index


def remove_block(spec: dict, rotation_id: str, index: int) -> None:
    rotation = _item(spec, "rotations", rotation_id)
    _writable(rotation)
    blocks = rotation["blocks"]
    if not 0 <= int(index) < len(blocks):
        raise ValueError("That block no longer exists.")
    del blocks[int(index)]


def move_block(spec: dict, rotation_id: str, index: int, delta: int) -> None:
    rotation = _item(spec, "rotations", rotation_id)
    _writable(rotation)
    blocks = rotation["blocks"]
    index = int(index)
    target = index + int(delta)
    if not 0 <= index < len(blocks):
        raise ValueError("That block no longer exists.")
    if 0 <= target < len(blocks):
        blocks.insert(target, blocks.pop(index))


def _placement_end(spec: dict, placement: dict) -> float:
    ability = spec["catalog"]["abilities"].get(placement["ability"]) or {}
    last = max((hit["offset"] for hit in ability.get("hits") or ()), default=0.0)
    return float(placement["first_hit"]) + last


def add_placement(spec: dict, sequence_id: str, ability_id: str, at=None) -> str:
    """Place an ability; a new one goes after whatever is already in the window."""
    sequence = _item(spec, "field_seqs", sequence_id)
    _writable(sequence)
    ability = spec["catalog"]["abilities"].get(ability_id)
    if ability is None:
        raise ValueError("That ability is not in the catalogue.")
    when = at
    if when is None:
        when = max([_placement_end(spec, p) for p in sequence["placements"]] + [0.0])
    placement_id = unique_id({p["id"] for p in sequence["placements"]},
                             sequence_id + "~" + catalog.slug(ability["name"]))
    sequence["placements"].append({"id": placement_id, "ability": ability_id,
                                   "first_hit": round(max(0.0, float(when)), 3)})
    return placement_id


def remove_placement(spec: dict, sequence_id: str, placement_id: str) -> None:
    sequence = _item(spec, "field_seqs", sequence_id)
    _writable(sequence)
    sequence["placements"] = [p for p in sequence["placements"] if p["id"] != placement_id]


def move_placement(spec: dict, sequence_id: str, placement_id: str, first_hit) -> None:
    sequence = _item(spec, "field_seqs", sequence_id)
    _writable(sequence)
    for placement in sequence["placements"]:
        if placement["id"] == placement_id:
            placement["first_hit"] = round(max(0.0, float(first_hit)), 3)
            return
    raise ValueError("That placement no longer exists.")


def set_field_time(spec: dict, sequence_id: str, seconds) -> None:
    sequence = _item(spec, "field_seqs", sequence_id)
    _writable(sequence)
    seconds = float(seconds)
    if seconds <= 0:
        raise ValueError("The swap-out must be after the swap-in.")
    sequence["field_time"] = round(seconds, 3)


def set_sequence_text(spec: dict, sequence_id: str, *, name=None, character=None) -> None:
    sequence = _item(spec, "field_seqs", sequence_id)
    _writable(sequence)
    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("The name cannot be empty.")
        sequence["name"] = name
    if character is not None:
        if character not in spec["catalog"]["characters"]:
            raise ValueError("Pick a character from the catalogue.")
        sequence["character"] = character
