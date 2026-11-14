"""Catalogue lookups used by the rotation / trial editors."""

import streamlit as st

from abilities import ABILITY_REGISTRY, abilities_for
from presets import field_sequences_for


# --- Editor catalogues -------------------------------------------------------
# Everything the editors offer comes from the catalogues: field sequences from
# presets.py (FIELD_SEQUENCE_REGISTRY) and abilities from abilities.py
# (ABILITY_REGISTRY), so a new definition shows up automatically and never has to be
# listed twice. Availability is gated by the CURRENT PARTY: only sequences/abilities
# whose owner is actually in the team are offered.

def party_characters() -> list:
    """Character names selected in the current party (order preserved)."""
    party = st.session_state.get("my_party") or {}
    return [name for name in party.keys()
            if name and name not in ("Select Character", "None")]


def available_field_sequences() -> dict:
    """{label: FieldSequence} — abilities.py sequences for this party + custom ones."""
    options = {}
    for name, seq in field_sequences_for(party_characters()).items():
        options[f"{name} ({seq.character})"] = seq
    for name, seq in (st.session_state.get("custom_field_sequences") or {}).items():
        options[f"{name} ({seq.character}) [custom]"] = seq
    return options


def available_abilities(character: str) -> dict:
    """{ability name: Ability} owned by *character* (empty when not in the party)."""
    if character not in party_characters():
        return {}
    return abilities_for(character)


def rotation_field_time(rotation) -> float:
    """Sum of the field times of one pass through a rotation."""
    return sum(seq.swap_out_time for seq in rotation.sequences)


def trial_field_time(trial) -> float:
    """Total field time of a trial: every rotation, every repetition."""
    return sum(rotation_field_time(rot) * rot.repetitions for rot in trial.rotations)


def select_trial_label(key: str, trial) -> str:
    """Trial dropdown label: preset trials show their team so duplicates stay clear."""
    if trial.required_party:
        return f"{trial.name}  [{' / '.join(trial.required_party)}]"
    return key


BUFF_GROUP_TAG = {"Character": "", "Weapon": "[W] ", "Artifact": "[A] ", "Team": "[T] "}


def buff_is_active(value):
    """True when a buff audit cell is not OFF / 0 / empty."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in ("", "OFF", "-")
    return value != 0
