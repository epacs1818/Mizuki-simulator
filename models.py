from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


# ==========================================
# 1. ENUMS & CORE DATA STRUCTURES
# ==========================================

class ActionCategory(Enum):
    SWAP = "Swap"
    STANDARD_DMG = "Standard DMG"
    STELLAR_DMG = "Stellar DMG"
    STELLAR_REACTION = "Stellar Reaction"

class AttackType(Enum):
    NORMAL = "Normal Attack"
    CHARGED = "Charged Attack"
    PLUNGING = "Plunging Attack"
    SKILL = "Elemental Skill"
    BURST = "Elemental Burst"

class StatRef(Enum):
    ATK = "ATK"
    HP = "HP"
    DEF = "DEF"
    EM = "EM"

@dataclass
class Hit:
    name: str
    relative_delay: float
    element: str                          # "Cryo", "Anemo", "Physical", ...
    elemental_app: Optional[str] = None   # e.g. "1U"
    category: ActionCategory = ActionCategory.STANDARD_DMG
    stat_ref: StatRef = StatRef.ATK
    motion_value: float = 0.0
    attack_type: Optional[AttackType] = None  # Optional tag for effect checks
    # Optional scaling coordinates in CHARACTER_SKILLS: (character, category, sub_ability)
    scaling_key: Optional[tuple] = None


@dataclass
class Ability:
    name: str
    character: str
    hits: List[Hit]
    cooldown: float = 0.0
    talent_level: int = 10  # Track skill level of the attack (1-13)
    talent_type: str = "skill_talent"
    # A skill FORM can be CUT by the caster's swap-out (Mizuki). When this is set,
    # the field sequence's window decides how many hits happen: everything up to and
    # including the FIRST hit after the swap-out still lands (that tick was already
    # in the air, so it resolves off field), and every later hit never happens.
    interrupt_on_swap_out: bool = False
    # Abilities that are the SAME in-game button share one cooldown by naming the
    # same family (Mizuki's two skill forms, Diona's tap/hold). None falls back to
    # the ability's own name, which is the old per-ability behaviour. Odette's cast
    # and recast keep separate families on purpose: her recast must stay castable
    # right after her cast, which is what her OdetteEE / OdetteQE presets do.
    cooldown_family: Optional[str] = None
    # How many casts a skill can stock (Sucrose: 2; 1 everywhere else). Charges
    # belong to the BUTTON, so every ability in one cooldown family must declare
    # the same value. A cast spends one charge; a charge returns every `cooldown`
    # seconds, and the recharge timer is started by the FIRST spend (later spends
    # do not push it back).
    ability_max_charges: int = 1

    @property
    def cooldown_key(self) -> tuple:
        """(character, family-or-name): the key cooldowns are tracked under.

        The character is part of the key, so "skill" on Mizuki and "skill" on
        Diona are different cooldowns. The family - not the ability name - is
        what makes two forms of one button clash with each other.
        """
        return (self.character, self.cooldown_family or self.name)


# Float tolerance for "the charge is up at exactly this time" checks, matching the
# window tolerance the timeline uses (timeline._WINDOW_EPS).
_CHARGE_EPS = 1e-9


class ChargePool:
    """Charges (Sucrose's 2 skill casts) and the one recharge timer behind them.

    Genshin refills stocked charges ONE at a time from a single timer: spending a
    charge while the pool is full starts that timer, and further spends do not move
    it. `advance()` rolls the clock forward, `block_until()` answers "when can this
    cast happen", `consume()` spends, and `grant()` is a Sacrificial-weapon proc -
    it makes the next charge available now, it does NOT refill the pool.

    Charges are clamped to [0, capacity]: consume() never goes negative, advance()
    never over-fills, and grant() is a no-op on a full pool. `ready_at` is None
    exactly while the pool is full (no timer running).
    """

    __slots__ = ("capacity", "charges", "ready_at")

    def __init__(self, max_charges):
        self.capacity = max(1, int(max_charges or 1))
        self.charges = self.capacity
        self.ready_at: Optional[float] = None

    def advance(self, cooldown, when) -> None:
        """Grant every charge whose timer has come up by *when*."""
        while (self.charges < self.capacity and self.ready_at is not None
               and when >= self.ready_at - _CHARGE_EPS):
            self.charges += 1
            self.ready_at = (None if self.charges >= self.capacity
                             else self.ready_at + cooldown)

    def block_until(self, cooldown, when) -> Optional[float]:
        """None when the cast can happen at *when*, else when it becomes legal."""
        self.advance(cooldown, when)
        return None if self.charges > 0 else self.ready_at

    def consume(self, cooldown, when) -> None:
        """Spend one charge; a spend from a FULL pool starts the recharge timer."""
        if self.charges <= 0:
            return
        if self.charges >= self.capacity:
            self.ready_at = when + cooldown
        self.charges -= 1

    def grant(self, when) -> None:
        """Sacrificial proc: the next charge arrives now (never over-fills)."""
        if self.charges >= self.capacity:
            return
        if self.ready_at is None or self.ready_at > when:
            self.ready_at = when


def interrupted_hit_count(times, swap_out_time, eps=1e-9):
    """How many of *times* still land when the caster swaps out at *swap_out_time*.

    *times* are sequence-relative hit times in ascending order. The rule (see
    Ability.interrupt_on_swap_out): keep every hit at or before the swap-out, keep
    the first hit after it (the one already in the air), then stop.
    """
    count = 0
    airborne = False
    for when in times:
        if when > swap_out_time + eps:
            if airborne:
                break
            airborne = True
        count += 1
    return count


@dataclass
class TimedAbilityCall:
    ability: Ability
    start_time: float


class FieldSequence:
    def __init__(self, name: str, character: str, swap_out_time: float):
        self.name = name
        self.character = character
        self.swap_out_time = swap_out_time
        self.calls: List[TimedAbilityCall] = []

    def add_ability(self, start_time: float, ability: Ability):
        self.calls.append(TimedAbilityCall(ability=ability, start_time=start_time))

@dataclass
class Rotation:
    name: str
    sequences: List[FieldSequence]
    repetitions: int = 1
    description: Optional[str] = ""

@dataclass
class Trial:
    name: str
    rotations: List[Rotation]
    end_mode: str = "time"
    end_time: float = 30.0
    description: Optional[str] = ""
    # Characters this trial was authored for. A preset trial is only offered when
    # the user's party is exactly this team (order-insensitive). None = no gate.
    required_party: Optional[List[str]] = None

    def matches_party(self, characters) -> bool:
        """True when *characters* is exactly the team this trial was built for."""
        if not self.required_party:
            return True
        chosen = {c for c in (characters or []) if c}
        return chosen == set(self.required_party)