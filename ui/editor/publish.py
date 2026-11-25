"""Publish a spec trial into the pools the rest of the app reads.

trial_runner.py, the results tab and the build export all read the session pools
(active_trial_pool / custom_rotations / custom_field_sequences), keyed by display
name. This module is the one place that turns editor payloads back into those
objects, so a published trial stays as runnable and exportable as a preset one.
"""

from __future__ import annotations

import copy

import streamlit as st

from models import FieldSequence, Rotation, Trial
from ui.editor import engine

POOL_KEY = "active_trial_pool"
ROTATIONS_KEY = "custom_rotations"
SEQUENCES_KEY = "custom_field_sequences"
PENDING_SELECTION = "_pending_trial_selection"


def _sequence(spec: dict, sequence_id: str, abilities: dict) -> FieldSequence:
    payload = spec["field_seqs"].get(sequence_id)
    if payload is None:
        raise ValueError("This trial uses a field sequence that no longer exists.")
    character = spec["catalog"]["characters"][payload["character"]]["name"]
    sequence = FieldSequence(payload["name"], character, float(payload["field_time"]))
    for placement in payload["placements"]:
        ability = abilities.get(placement["ability"])
        if ability is None:
            raise ValueError("%s places an ability that is not in the catalogue."
                             % payload["name"])
        sequence.add_ability(float(placement["cast_time"]), ability)
    return sequence


def build(spec: dict, trial_id: str):
    """(trial, sequences, rotations) for *trial_id* as fresh engine objects.

    The trial gets one rotation per slot, with the slot repeat; the rotations
    returned for the pool keep their own default repeats.
    """
    payload = spec["trials"].get(trial_id)
    if payload is None:
        raise ValueError("This trial no longer exists.")
    if not payload["slots"]:
        raise ValueError("Add at least one rotation before creating the trial.")
    characters = spec["catalog"]["characters"]
    abilities = engine.ability_map(spec)
    sequences: dict = {}
    pool_rotations: list = []
    played: list = []
    for slot in payload["slots"]:
        rotation_payload = spec["rotations"].get(slot["rotation"])
        if rotation_payload is None:
            raise ValueError("This trial uses a rotation that no longer exists.")
        if not rotation_payload["blocks"]:
            raise ValueError("Rotation %s has no field sequences." % rotation_payload["name"])
        blocks = []
        for sequence_id in rotation_payload["blocks"]:
            if sequence_id not in sequences:
                sequences[sequence_id] = _sequence(spec, sequence_id, abilities)
            blocks.append(sequences[sequence_id])
        base = Rotation(rotation_payload["name"], blocks,
                        max(1, int(rotation_payload.get("repeat", 1))))
        pool_rotations.append(copy.deepcopy(base))
        slot_rotation = copy.deepcopy(base)
        slot_rotation.repetitions = max(1, int(slot.get("repeat", 1)))
        played.append(slot_rotation)
    names = [characters[cid]["name"] for cid in payload.get("required_party") or []
             if cid in characters]
    trial = Trial(name=payload["name"], rotations=played,
                  end_mode=payload.get("end_mode", "time"),
                  end_time=float(payload.get("end_time") or 30.0),
                  description=payload.get("description", ""),
                  required_party=names or None)
    return trial, sequences, pool_rotations


def _store(trial, sequences, rotations) -> None:
    """Write one built trial and everything it uses into the pools."""
    sequence_pool = st.session_state.setdefault(SEQUENCES_KEY, {})
    rotation_pool = st.session_state.setdefault(ROTATIONS_KEY, {})
    pool = st.session_state.setdefault(POOL_KEY, {})
    for sequence in sequences.values():
        sequence_pool[sequence.name] = sequence
    for rotation in rotations:
        rotation_pool[rotation.name] = rotation
    pool[trial.name] = trial


def publish(spec: dict, trial_id: str) -> str:
    """Write the trial and everything it uses into the pools; returns its key."""
    trial, sequences, rotations = build(spec, trial_id)
    _store(trial, sequences, rotations)
    # The runner widget is already instantiated this run, so the selection is
    # queued: rotation.py applies it before the selectbox is created.
    st.session_state[PENDING_SELECTION] = trial.name
    return trial.name


def publish_all(spec: dict) -> list:
    """Sync EVERY non-preset editor trial into the pools (a draft save).

    Unlike publish(), the runner selection is left alone: this exists so a
    "Save file" includes trials that were never explicitly created in the
    runner. Trials that cannot be built yet (no rotations, empty slots) are
    skipped instead of aborting the save.
    """
    synced = []
    for trial_id, payload in (spec.get("trials") or {}).items():
        if payload.get("preset"):
            continue
        try:
            trial, sequences, rotations = build(spec, trial_id)
        except ValueError:
            continue
        _store(trial, sequences, rotations)
        synced.append(trial.name)
    return synced
