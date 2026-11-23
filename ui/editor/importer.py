"""Open an existing trial in the editor: the exact inverse of publish.py.

The runner and the pools speak our dataclasses (Trial / Rotation / FieldSequence);
the editor speaks ids and plain dicts. publish.py turns a spec trial into objects,
this module turns an object back into a spec entry, so "Open in editor" can hand
the trial the runner selected to the three screens without a second model of it.

Nothing is duplicated: an entry that already describes the same thing is reused
(that is why opening a preset lands on the preset, read-only, and opening a trial
you published lands on the trial you built). Only genuinely new content is copied
in, and it is copied in as editable (``preset: False``).

Pure and Streamlit-free, like mutations / engine / validate, so the smoke test can
drive the whole runner -> editor -> runner round-trip headlessly.
"""

from __future__ import annotations

from ui.editor import catalog, mutations

EPS = 1e-6


def _ability_owner(ability, sequence) -> str:
    return getattr(ability, "character", sequence.character) or sequence.character


def _sequence_signature(sequence) -> tuple:
    """What a FieldSequence *is*, in ids, so it can be compared with a payload."""
    calls = []
    for call in sequence.calls:
        ability = call.ability
        aid = catalog.ability_id(_ability_owner(ability, sequence), ability.name)
        calls.append((aid, round(float(call.start_time), 6)))
    return (sequence.name, catalog.character_id(sequence.character),
            round(float(sequence.swap_out_time), 6), tuple(calls))


def _payload_sequence_signature(payload: dict) -> tuple:
    return (payload["name"], payload["character"], round(float(payload["field_time"]), 6),
            tuple((placement["ability"], round(float(placement["cast_time"]), 6))
                  for placement in payload["placements"]))


def _import_sequence(spec: dict, sequence) -> str:
    """The spec id for *sequence*: an identical entry if there is one, else a copy."""
    signature = _sequence_signature(sequence)
    for sequence_id, payload in spec["field_seqs"].items():
        if _payload_sequence_signature(payload) == signature:
            return sequence_id

    character = catalog.character_id(sequence.character)
    if character not in spec["catalog"]["characters"]:
        raise ValueError("%s is not a character this editor knows." % sequence.character)
    abilities = spec["catalog"]["abilities"]
    placements = []
    for call in sequence.calls:
        ability = call.ability
        ability_id = catalog.ability_id(_ability_owner(ability, sequence), ability.name)
        if ability_id not in abilities:
            raise ValueError("%s uses %s, which the editor's catalogue does not have."
                             % (sequence.name, ability.name))
        placements.append({"ability": ability_id,
                           "cast_time": round(float(call.start_time), 6)})

    sequence_id = mutations.unique_id(spec["field_seqs"],
                                      catalog.sequence_id(sequence.character, sequence.name))
    for index, placement in enumerate(placements):
        placement["id"] = "%s~%d~%s" % (sequence_id, index,
                                         catalog.slug(abilities[placement["ability"]]["name"]))
    spec["field_seqs"][sequence_id] = {
        "id": sequence_id,
        "name": sequence.name,
        "character": character,
        "field_time": float(sequence.swap_out_time),
        "placements": placements,
        "preset": False,
    }
    return sequence_id


def _import_rotation(spec: dict, rotation, sequence_ids: dict) -> str:
    """The spec id for *rotation*; its blocks have already been imported."""
    blocks = [sequence_ids[id(sequence)] for sequence in rotation.sequences
              if id(sequence) in sequence_ids]
    if not blocks:
        raise ValueError("%s has no field sequences to open." % rotation.name)
    repeat = max(1, int(rotation.repetitions or 1))
    for rotation_id, payload in spec["rotations"].items():
        # The repeat a *trial slot* plays with is not the rotation's own default, so
        # the entry is matched on what it contains: same name, same blocks.
        if payload["name"] == rotation.name and payload["blocks"] == blocks:
            return rotation_id

    rotation_id = mutations.unique_id(spec["rotations"],
                                      catalog.slug(rotation.name) or "rotation")
    spec["rotations"][rotation_id] = {"id": rotation_id, "name": rotation.name,
                                      "blocks": blocks, "repeat": repeat, "preset": False}
    return rotation_id


def _same_trial(payload: dict, slots: list, party: list, trial) -> bool:
    if payload["name"] != trial.name:
        return False
    if payload.get("end_mode", "time") != (trial.end_mode or "time"):
        return False
    if abs(float(payload.get("end_time") or 0.0) - float(trial.end_time or 0.0)) > EPS:
        return False
    current = [(slot["rotation"], max(1, int(slot.get("repeat", 1))))
               for slot in payload["slots"]]
    if current != slots:
        return False
    return sorted(payload.get("required_party") or []) == sorted(set(party))


def trial_to_spec(spec: dict, trial) -> str:
    """Make *trial* (a Trial object) the editor's active trial; returns its spec id.

    A trial the spec already describes is reused, so a preset opens as the preset
    (read-only) and a published trial opens as the trial that was published.
    Anything new is copied in as an editable entry.
    """
    if not getattr(trial, "rotations", None):
        raise ValueError("This trial has no rotations, so there is nothing to open.")

    sequence_ids: dict = {}
    for rotation in trial.rotations:
        for sequence in rotation.sequences:
            sequence_ids.setdefault(id(sequence), _import_sequence(spec, sequence))
    rotation_ids = [_import_rotation(spec, rotation, sequence_ids)
                    for rotation in trial.rotations]
    slots = [(rotation_id, max(1, int(rotation.repetitions or 1)))
             for rotation_id, rotation in zip(rotation_ids, trial.rotations)]

    party = []
    for name in trial.required_party or []:
        character_id = catalog.character_id(name)
        if character_id not in spec["catalog"]["characters"]:
            raise ValueError("%s is not a character this editor knows." % name)
        party.append(character_id)

    for trial_id, payload in spec["trials"].items():
        if _same_trial(payload, slots, party, trial):
            return trial_id

    trial_id = mutations.unique_id(spec["trials"], catalog.slug(trial.name) or "trial")
    spec["trials"][trial_id] = {
        "id": trial_id,
        "name": trial.name,
        "description": trial.description or "",
        "end_mode": trial.end_mode or "time",
        "end_time": float(trial.end_time or 0.0),
        "required_party": sorted(set(party)),
        "slots": [{"id": "%s~%d" % (trial_id, index), "rotation": rotation_id,
                   "repeat": repeat}
                  for index, (rotation_id, repeat) in enumerate(slots)],
        "preset": False,
    }
    return trial_id
