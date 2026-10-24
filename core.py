from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Set
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


# ==========================================
# 2. MECHANICS STATE MANAGERS
# ==========================================

class StellarVortex:
    """Tracks active Stellar Vortex lifecycle, leveling, and contributor inheritance."""
    def __init__(self, creation_swirl_meta: dict, creation_time: float):
        self.creator = creation_swirl_meta["anemo_contributor"]
        self.creation_time = creation_time
        self.scheduled_explosion_time = creation_time + 3.0
        self.swirl_count = 1  # 1st swirl creates it
        self.level = 1
        self.last_trigger = self.creator

        # Inherit contributors from the initial Stellar Swirl
        self.anemo_contributors: Set[str] = {self.creator}
        self.cryo_contributors: Set[str] = set(creation_swirl_meta["cryo_contributors"])
        self.is_active = True

    def inherit_swirl(self, swirl_meta: dict) -> Tuple[bool, str]:
        """Inherits contributors from subsequent Stellar Swirls, handling leveling and early detonations."""
        self.swirl_count += 1
        anemo_char = swirl_meta["anemo_contributor"]
        self.last_trigger = anemo_char

        # Aggregate contributors
        self.anemo_contributors.add(anemo_char)
        self.cryo_contributors.update(swirl_meta["cryo_contributors"])

        if self.swirl_count >= 3 and self.level < 2:
            self.level = 2

        if self.swirl_count >= 6:
            self.is_active = False
            return True, "SSW (Vortex Early Detonation)"

        return False, "Stellar Swirl"
