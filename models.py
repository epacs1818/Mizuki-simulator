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
    element: str                          # Now mandatory (e.g., "Cryo", "Anemo", "Physical")
    elemental_app: Optional[str] = None   # e.g., "1U"
    category: ActionCategory = ActionCategory.STANDARD_DMG
    stat_ref: StatRef = StatRef.ATK
    motion_value: float = 0.0
    attack_type: Optional[AttackType] = None  # Optional tag for effect checks
    # Optional scaling coordinates in CHARACTER_SKILLS: (character, category, sub_ability)
    scaling_key: Optional[tuple] = None

    @property
    def multiplier(self) -> float:
        """Alias for motion_value to preserve backward compatibility."""
        return self.motion_value

    @multiplier.setter
    def multiplier(self, value: float):
        self.motion_value = value


@dataclass
class Ability:
    name: str
    hits: List[Hit]
    cooldown: float = 0.0
    talent_level: int = 10  # Track skill level of the attack (1-13)
    talent_type: str = "skill_talent"


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
