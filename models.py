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


@dataclass
class Hit:
    name: str
    relative_delay: float
    elemental_app: Optional[str] = None  # e.g., "1U"
    element: Optional[str] = None        # "Cryo", "Anemo", etc.
    category: ActionCategory = ActionCategory.STANDARD_DMG


@dataclass
class Ability:
    name: str
    hits: List[Hit]
    cooldown: float = 0.0


@dataclass
class TimedAbilityCall:
    ability: Ability
    start_time: float


class Combo:
    def __init__(self, name: str, character: str, swap_out_time: float):
        self.name = name
        self.character = character
        self.swap_out_time = swap_out_time
        self.calls: List[TimedAbilityCall] = []

    def add_ability(self, start_time: float, ability: Ability):
        self.calls.append(TimedAbilityCall(ability=ability, start_time=start_time))
