"""Typed domain model for the rotation / damage calculator.

Design rule for this project
----------------------------
The simulation engine consumes **frozen dataclasses**; the Streamlit layer only
ever touches the **plain-dict** form. `to_dict()` / `from_dict()` are the single
boundary between the two worlds, which buys us three things for free:

* `@st.cache_data` can hash the spec (it is all primitives),
* undo / redo is a `copy.deepcopy` snapshot,
* export / import is `json.dumps`.

Because the dataclasses are frozen and their collections are tuples, they are
hashable too - if you ever want to memoise on them directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# --------------------------------------------------------------------------
# Catalog (static game data)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    color: str  # hex, chosen colour-blind-friendly in catalog.py
    initial: str  # shown inside blocks so colour is never the only signal

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "color": self.color, "initial": self.initial}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Character:
        return cls(d["id"], d["name"], d["color"], d["initial"])


@dataclass(frozen=True)
class Buff:
    """A timed damage modifier. All buffs multiply the hit that carries them."""

    id: str
    name: str
    duration: float  # seconds one application lasts
    per_stack: float  # e.g. 0.25 -> +25% damage per stack
    max_stacks: int
    color: str
    kind: str = "ally"  # "ally" | "enemy" - display grouping only

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "duration": self.duration,
            "per_stack": self.per_stack,
            "max_stacks": self.max_stacks,
            "color": self.color,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Buff:
        return cls(
            d["id"],
            d["name"],
            float(d["duration"]),
            float(d["per_stack"]),
            int(d["max_stacks"]),
            d["color"],
            d.get("kind", "ally"),
        )


@dataclass(frozen=True)
class Hit:
    """One damage tick. `offset` is measured from the ability's first hit."""

    offset: float
    raw: float
    crit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"offset": self.offset, "raw": self.raw, "crit": self.crit}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Hit:
        return cls(float(d["offset"]), float(d["raw"]), bool(d.get("crit", False)))


@dataclass(frozen=True)
class Ability:
    """A fixed set of hits plus the rule that makes it fire.

    `category` is "basic" | "skill" | "ultimate" | "triggered".
    Triggered abilities are never placed by the user; `trigger` describes the
    condition that fires them (see sim.py for the supported conditions).
    """

    id: str
    name: str
    character: str
    category: str
    hits: tuple[Hit, ...]
    buff: str | None = None
    buff_at: int = 0  # index of the hit that applies `buff`
    trigger: dict[str, Any] | None = None
    # How long the character is actually busy casting. Optional on purpose: in
    # engines where a "cast time" is really the *hit* time (a skill whose procs
    # land 15s later), there is no occupancy to model and the overlap check is
    # skipped. None means "not modelled".
    action_time: float | None = None

    @property
    def span(self) -> float:
        """Seconds from first hit to last hit."""
        return max((h.offset for h in self.hits), default=0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "character": self.character,
            "category": self.category,
            "hits": [h.to_dict() for h in self.hits],
            "buff": self.buff,
            "buff_at": self.buff_at,
            "trigger": self.trigger,
            "action_time": self.action_time,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Ability:
        return cls(
            d["id"],
            d["name"],
            d["character"],
            d["category"],
            tuple(Hit.from_dict(h) for h in d["hits"]),
            d.get("buff"),
            int(d.get("buff_at", 0)),
            d.get("trigger"),
            None if d.get("action_time") is None else float(d["action_time"]),
        )


# --------------------------------------------------------------------------
# Authored content (what the user builds)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Placement:
    """One standard ability dropped into a field sequence.

    `first_hit` is the only thing the user can move: every other hit of the
    ability keeps its offset relative to it.
    """

    id: str
    ability: str
    first_hit: float

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "ability": self.ability, "first_hit": self.first_hit}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Placement:
        return cls(d["id"], d["ability"], float(d["first_hit"]))


@dataclass(frozen=True)
class FieldSequence:
    """A character's field time: swap in at t=0, swap out at `field_time`."""

    id: str
    name: str
    character: str
    field_time: float
    placements: tuple[Placement, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "character": self.character,
            "field_time": self.field_time,
            "placements": [p.to_dict() for p in self.placements],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FieldSequence:
        return cls(
            d["id"],
            d.get("name", d["id"]),
            d["character"],
            float(d["field_time"]),
            tuple(Placement.from_dict(p) for p in d.get("placements", [])),
        )


@dataclass(frozen=True)
class Rotation:
    """An ordered list of field sequences. Blocks always run back to back."""

    id: str
    name: str
    blocks: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "blocks": list(self.blocks)}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Rotation:
        return cls(d["id"], d["name"], tuple(d.get("blocks", [])))


@dataclass(frozen=True)
class TrialSlot:
    """One rotation inserted into the trial, repeated N times."""

    id: str
    rotation: str
    repeat: int

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "rotation": self.rotation, "repeat": int(self.repeat)}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TrialSlot:
        return cls(d["id"], d["rotation"], int(d.get("repeat", 1)))


@dataclass(frozen=True)
class Trial:
    id: str
    name: str
    duration: float
    slots: tuple[TrialSlot, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "duration": self.duration,
            "slots": [s.to_dict() for s in self.slots],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Trial:
        return cls(
            d["id"],
            d.get("name", d["id"]),
            float(d["duration"]),
            tuple(TrialSlot.from_dict(s) for s in d["slots"]),
        )


# --------------------------------------------------------------------------
# Whole-spec container
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Catalog:
    characters: dict[str, Character]
    abilities: dict[str, Ability]
    buffs: dict[str, Buff]

    def to_dict(self) -> dict[str, Any]:
        return {
            "characters": {k: v.to_dict() for k, v in self.characters.items()},
            "abilities": {k: v.to_dict() for k, v in self.abilities.items()},
            "buffs": {k: v.to_dict() for k, v in self.buffs.items()},
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Catalog:
        return cls(
            {k: Character.from_dict(v) for k, v in d["characters"].items()},
            {k: Ability.from_dict(v) for k, v in d["abilities"].items()},
            {k: Buff.from_dict(v) for k, v in d["buffs"].items()},
        )


@dataclass(frozen=True)
class Spec:
    """Everything the engine needs: rules + committed user content."""

    catalog: Catalog
    field_seqs: dict[str, FieldSequence]
    rotations: dict[str, Rotation]
    trials: dict[str, Trial]
    active_trial: str

    @property
    def trial(self) -> Trial:
        """The trial being simulated. The engine never sees the library."""
        return self.trials[self.active_trial]

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog": self.catalog.to_dict(),
            "field_seqs": {k: v.to_dict() for k, v in self.field_seqs.items()},
            "rotations": {k: v.to_dict() for k, v in self.rotations.items()},
            "trials": {k: v.to_dict() for k, v in self.trials.items()},
            "active_trial": self.active_trial,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Spec:
        trials_raw = d.get("trials")
        if trials_raw:
            trials = {k: Trial.from_dict(v) for k, v in trials_raw.items()}
            active = d.get("active_trial") if d.get("active_trial") in trials else next(iter(trials))
        else:
            # Legacy payload: a single trial under "trial" (old exports and links).
            legacy = Trial.from_dict(d["trial"])
            trials = {legacy.id: legacy}
            active = legacy.id

        return cls(
            Catalog.from_dict(d["catalog"]),
            {k: FieldSequence.from_dict(v) for k, v in d.get("field_seqs", {}).items()},
            {k: Rotation.from_dict(v) for k, v in d.get("rotations", {}).items()},
            trials,
            active,
        )
