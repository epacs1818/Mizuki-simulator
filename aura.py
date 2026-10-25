from typing import List, Optional, Tuple


# ==========================================
# 4. ELEMENTAL AURA ENGINE
# ==========================================

class CryoAuraTracker:
    """Manages Cryo gauge decay rates, inheritance rules, and lifecycle contributors for Swirls."""
    def __init__(self):
        self.current_gauge: float = 0.0
        self.decay_rate: float = 0.0  # U/s
        self.last_update_time: float = 0.0
        self.active_cryo_appliers: List[str] = []

    def advance_time(self, current_time: float):
        if self.current_gauge > 0.0:
            dt = current_time - self.last_update_time
            decay_amount = self.decay_rate * dt
            self.current_gauge = max(0.0, self.current_gauge - decay_amount)
            if self.current_gauge == 0.0:
                self.decay_rate = 0.0
                self.active_cryo_appliers.clear()
        self.last_update_time = current_time

    def apply_element(self, element: Optional[str], gauge_u: float, char: str, current_time: float) -> Tuple[Optional[str], bool, Optional[dict]]:
        self.advance_time(current_time)
        reaction_triggered = None
        is_stellar_swirl = False
        swirl_metadata = None

        if element == "Cryo" and gauge_u > 0.0:
            b_new_applied = 0.8 * gauge_u
            if self.current_gauge == 0.0:
                duration = 2.5 * gauge_u + 7.0
                self.decay_rate = b_new_applied / duration
                self.current_gauge = b_new_applied
                self.active_cryo_appliers = [char]
            else:
                self.current_gauge = max(self.current_gauge, b_new_applied)
                if char not in self.active_cryo_appliers:
                    self.active_cryo_appliers.append(char)

        elif element == "Anemo" and gauge_u > 0.0:
            if self.current_gauge > 0.0:
                reaction_triggered = "Stellar Swirl"
                is_stellar_swirl = True

                swirl_metadata = {
                    "anemo_contributor": char,
                    "cryo_contributors": list(self.active_cryo_appliers)
                }

                consumed = 0.5 * gauge_u
                self.current_gauge = max(0.0, self.current_gauge - consumed)
                if self.current_gauge == 0.0:
                    self.decay_rate = 0.0
                    self.active_cryo_appliers.clear()
            else:
                reaction_triggered = "No Aura"

        return reaction_triggered, is_stellar_swirl, swirl_metadata
