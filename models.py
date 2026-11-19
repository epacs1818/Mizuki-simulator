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