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


# ==========================================
# 3. CHARACTER ABILITIES & COMBOS
# ==========================================

# --- Aether ---
aether_n1 = Ability("N1", hits=[Hit("N1_Hit", 0.000)])
aether_n1ca = Ability("Charged Attack", hits=[Hit("N1", 0.000), Hit("C1_Hit", 0.510), Hit("C2_Hit", 0.720)])
aether_skill = Ability(
    name="Elemental Skill",
    cooldown=15.0,
    hits=[
        Hit("Skill_Initial", 0.000, "1U", element="Cryo"),
        Hit("Skill_Proc1", 3.149, "1U", element="Cryo"),
        Hit("Skill_Proc2", 3.329),
        Hit("Skill_Proc3", 6.030, "1U", element="Cryo"),
        Hit("Skill_Proc4", 6.269),
        Hit("Skill_Proc5", 8.969, "1U", element="Cryo"),
        Hit("Skill_Proc6", 9.179),
        Hit("Skill_Proc7", 11.880, "1U", element="Cryo"),
        Hit("Skill_Proc8", 12.090),
        Hit("Skill_Proc9", 14.880, "1U", element="Cryo"),
        Hit("Skill_Proc10", 15.090),
    ]
)
aether_burst = Ability(
    name="Elemental Burst",
    cooldown=15.0,
    hits=[
        Hit("Burst_Cast", 0.000, "1U", element="Cryo"),
        Hit("Burst_Tick1", 0.550),
        Hit("Burst_Tick2", 0.550),
        Hit("Burst_Tick3", 0.660, "1U", element="Cryo"),
        Hit("Burst_Tick4", 0.780),
    ]
)
aether_ecq = Combo("AetherECQ", "Aether", swap_out_time=3.631)
aether_ecq.add_ability(0.601, aether_skill)
aether_ecq.add_ability(1.2, aether_n1ca)
aether_ecq.add_ability(3.061, aether_burst)

aether_en1 = Combo("AetherEN1", "Aether", swap_out_time=1.23)
aether_en1.add_ability(0.601, aether_skill)
aether_en1.add_ability(1.2, aether_n1)

aether_cq = Combo("AetherCQ", "Aether", swap_out_time=2.941)
aether_cq.add_ability(0.51, aether_n1ca)
aether_cq.add_ability(2.371, aether_burst)

# --- Odette ---
odette_cast = Ability(
    name="Skill Cast",
    cooldown=15.0,
    hits=[
        Hit("Skill_Cast", 0.000, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_1", 2.220, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_Stellar_1", 2.220, category=ActionCategory.STELLAR_DMG),
        Hit("Wing_1", 4.080, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Wing_Stellar_1", 4.080, category=ActionCategory.STELLAR_DMG),
        Hit("Plume_2", 6.180, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_Stellar_2", 6.180, category=ActionCategory.STELLAR_DMG),
        Hit("Wing_2", 8.010, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Wing_Stellar_2", 8.010, category=ActionCategory.STELLAR_DMG),
        Hit("Plume_3", 10.110, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_Stellar_3", 10.110, category=ActionCategory.STELLAR_DMG),
        Hit("Wing_3", 11.940, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Wing_Stellar_3", 11.940, category=ActionCategory.STELLAR_DMG),
        Hit("Plume_4", 14.040, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_Stellar_4", 14.040, category=ActionCategory.STELLAR_DMG),
        Hit("Wing_4", 15.901, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Wing_Stellar_4", 15.901, category=ActionCategory.STELLAR_DMG),
        Hit("Plume_5", 17.940, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Plume_Stellar_5", 17.940, category=ActionCategory.STELLAR_DMG),
        Hit("Wing_5", 19.800, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Wing_Stellar_5", 19.800, category=ActionCategory.STELLAR_DMG),
    ]
)
odette_recast = Ability(
    name="Skill Recast",
    cooldown=0.0,
    hits=[
        Hit("Skill_Recast1", 0.000, "1U", element="Cryo", category=ActionCategory.STANDARD_DMG),
        Hit("Skill_Recast2", 0.180, category=ActionCategory.STANDARD_DMG),
        Hit("Skill_Recast3", 0.300, category=ActionCategory.STANDARD_DMG),
        Hit("Skill_Stellar", 0.871, category=ActionCategory.STELLAR_DMG),
    ]
)
odette_ee = Combo("OdetteEE", "Odette", swap_out_time=2.371)
odette_ee.add_ability(0.660, odette_cast)
odette_ee.add_ability(1.170, odette_recast)

# --- Faruzan ---
faruzan_burst = Ability(
    name="Elemental Burst",
    cooldown=19.0,
    hits=[
        Hit("Burst_Cast", 0.000, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG)
    ]
)
faruzan_collapse_hit = Hit("Pressurized Collapse", relative_delay=0.0, elemental_app="1U", element="Anemo", category=ActionCategory.STANDARD_DMG)
faruzan_q = Combo("FaruzanQSwap", "Faruzan", swap_out_time=1.410)
faruzan_q.add_ability(1.200, faruzan_burst)

# --- Mizuki ---
mizuki_skill = Ability(
    name="Mizuki Skill",
    cooldown=15.0,
    hits=[
        Hit("Cast", 0.301, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick1", 1.230, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick2", 1.920, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick3", 2.940, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick4", 3.601, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick5", 4.291, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick6", 5.101, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick7", 5.791, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick8", 6.570, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick9", 7.290, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick10", 7.980, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick11", 8.790, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick12", 9.480, element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick13", 10.17, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
    ]
)
mizuki_burstless_pull_out = Combo("BurstlessPullOut", "Mizuki", swap_out_time=10.0)
mizuki_burstless_pull_out.add_ability(0.000, mizuki_skill)

mizuki_sacfrag_skill = Ability(
    name="Mizuki Skill (SacFrag)",
    cooldown=0.0,
    hits=[
        Hit("Cast", 0.301, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick1", 1.230, "1U", element="Anemo", category=ActionCategory.STANDARD_DMG),
        Hit("Tick2", 1.920, element="Anemo", category=ActionCategory.STANDARD_DMG),
    ]
)
mizuki_sacfrag_fill = Combo("SacFragFill", "Mizuki", swap_out_time=1.75)
mizuki_sacfrag_fill.add_ability(0.000, mizuki_sacfrag_skill)


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


# ==========================================
# 5. TIMELINE ENGINE & EVALUATOR
# ==========================================

class RotationTimeline:
    def __init__(self, party: Optional[Dict[str, dict]] = None):
        self.global_events = []
        self.last_used_timestamps: Dict[Tuple[str, str], float] = {}

        # Normalize party structure: ensure every entry has dict metadata
        self.party: Dict[str, dict] = {}
        if party:
            for char, data in party.items():
                if isinstance(data, int): # Backward compatibility if someone passes just an int constellation
                    self.party[char] = {"constellation": data, "weapon": None, "artifact": None}
                else:
                    self.party[char] = data

    def add_combo(self, combo: Combo, swap_in_time: float) -> float:
        if combo.character not in self.party:
            # Auto-register missing characters with default settings
            self.party[combo.character] = {"constellation": 0, "weapon": None, "artifact": None}
        self.global_events.append({
            "global_time": swap_in_time,
            "character": combo.character,
            "action": "Swap In",
            "category": ActionCategory.SWAP,
            "elem_app": "-",
            "element": None,
            "event_type": "SWAP_IN"
        })

        swap_out_global = swap_in_time + combo.swap_out_time
        self.global_events.append({
            "global_time": swap_out_global,
            "character": combo.character,
            "action": "Swap Out",
            "category": ActionCategory.SWAP,
            "elem_app": "-",
            "element": None,
            "event_type": "SWAP_OUT"
        })

        for call in combo.calls:
            ability_start_global = swap_in_time + call.start_time
            ability_key = (combo.character, call.ability.name)

            if call.ability.cooldown > 0 and ability_key in self.last_used_timestamps:
                last_time = self.last_used_timestamps[ability_key]
                cd_expires_at = last_time + call.ability.cooldown
                if ability_start_global < cd_expires_at:
                    raise ValueError(f"[COOLDOWN ERROR] {combo.character}'s {call.ability.name} on CD until {cd_expires_at:.3f}s")

            if call.ability.cooldown > 0:
                self.last_used_timestamps[ability_key] = ability_start_global

            self.global_events = [
                ev for ev in self.global_events
                if not (ev.get("event_type") == "HIT" and
                        ev.get("character") == combo.character and
                        ev.get("ability_name") == call.ability.name and
                        ev["global_time"] >= ability_start_global)
            ]

            for hit in call.ability.hits:
                hit_global_time = ability_start_global + hit.relative_delay
                self.global_events.append({
                    "global_time": hit_global_time,
                    "character": combo.character,
                    "action": f"{call.ability.name} ({hit.name})",
                    "category": hit.category,
                    "elem_app": hit.elemental_app if hit.elemental_app else "-",
                    "element": hit.element,
                    "event_type": "HIT",
                    "hit_name": hit.name,
                    "ability_name": call.ability.name
                })

        self.global_events.sort(key=lambda x: x["global_time"])
        return swap_out_global

    def _parse_gauge(self, elem_app: str) -> float:
        if elem_app and elem_app != "-" and elem_app.endswith("U"):
            try:
                return float(elem_app[:-1])
            except ValueError:
                return 0.0
        return 0.0

    def evaluate_timeline(self):
        active_character = "None"
        aether_c2_active = False
        marvelous_active = False
        marvelous_activation_time = 0.0
        odette_swap_time: Optional[float] = None
        hotf_expiration_time: Optional[float] = None
        vv_expiration_time: Optional[float] = None
        instructor_expiration_time: Optional[float] = None

        # --- DYNAMIC GEAR RESOLUTION ---
        # Find which character has "Heart of the Furnace" equipped as their weapon or artifact
        hotf_holder = next(
            (char for char, data in self.party.items()
            if data.get("weapon") == "Heart of the Furnace" or data.get("artifact") == "Heart of the Furnace"),
            None
        )
        
        vv_holder = next(
            (char for char, data in self.party.items()
            if data.get("artifact") in ["Viridescent Venerer", "Viridescent"]),
            None
        )
        
        instructor_holder = next(
            (char for char, data in self.party.items()
            if data.get("artifact") == "Instructor"),
            None
        )        

        # Mizuki State Trackers
        mizuki_dreamdrifter_active = False
        mizuki_nuke_armed = False
        mizuki_nuke_armed_time: float = -1.0
        mizuki_nuke_prep_cd_expires: float = -1.0

        # Mizuki C1 State Trackers
        mizuki_c1_debuff_expiration: float = -1.0
        mizuki_c1_app_cooldown_expires: float = -1.0

        # Faruzan State Trackers
        faruzan_buff_expiration: Optional[float] = None
        faruzan_debuff_expiration: Optional[float] = None
        faruzan_collapse_cd_expires: float = -1.0

        aura_tracker = CryoAuraTracker()
        active_vortex: Optional[StellarVortex] = None

        self.global_events.sort(key=lambda x: x["global_time"])

        i = 0
        while i < len(self.global_events):
            event = self.global_events[i]
            t = event["global_time"]
            e_type = event.get("event_type")
            char = event.get("character")
            cat = event.get("category")
            elem_app = event.get("elem_app", "-")
            element = event.get("element")
            ability_name = event.get("ability_name", "")
            hit_name = event.get("hit_name", "")

            # 1. Handle Stellar Vortex Timer Expiration
            if active_vortex and active_vortex.is_active and t >= active_vortex.scheduled_explosion_time:
                exp_time = active_vortex.scheduled_explosion_time
                active_vortex.is_active = False

                explosion_event = {
                    "global_time": exp_time,
                    "active_character": active_character,
                    "character": active_vortex.last_trigger,
                    "action": f"Vortex Explosion (Lv{active_vortex.level})",
                    "category": ActionCategory.STELLAR_REACTION,
                    "elem_app": "1U",
                    "element": "Cryo",
                    "event_type": "HIT",
                    "hit_name": f"Vortex_Exp_Lv{active_vortex.level}",
                    "ability_name": "Stellar Vortex",
                    "reaction": f"Vortex Lv{active_vortex.level} Exp",
                    "vortex_metadata": {
                        "primary_credit": active_vortex.last_trigger,
                        "creation_credit": active_vortex.creator,
                        "anemo_contributors": list(active_vortex.anemo_contributors),
                        "cryo_contributors": list(active_vortex.cryo_contributors),
                        "level": active_vortex.level
                    }
                }
                self.global_events.insert(i, explosion_event)
                active_vortex = None
                continue

            # 2. Active Character Tracking
            if e_type == "SWAP_IN":
                active_character = char
            elif e_type == "SWAP_OUT" and active_character == char:
                active_character = "None"

            event["active_character"] = active_character

            # 3. Faruzan Buff & Debuff Logic
            if "Faruzan" in self.party:
                if e_type == "HIT" and char == "Faruzan" and ability_name == "Elemental Burst" and hit_name == "Burst_Cast":
                    faruzan_buff_expiration = t + 22.0
                    faruzan_debuff_expiration = t + 22.0
                    collapse_time = t + 0.720
                    faruzan_collapse_cd_expires = collapse_time + 3.0

                    self.global_events.insert(i + 1, {
                        "global_time": collapse_time,
                        "character": "Faruzan",
                        "action": "Pressurized Collapse",
                        "category": faruzan_collapse_hit.category,
                        "elem_app": faruzan_collapse_hit.elemental_app,
                        "element": faruzan_collapse_hit.element,
                        "event_type": "HIT",
                        "hit_name": "Pressurized_Collapse",
                        "ability_name": "Pressurized Collapse"
                    })

                if e_type == "HIT" and hit_name == "Pressurized_Collapse":
                    faruzan_debuff_expiration = t + 4.0

                faruzan_buff_active = (faruzan_buff_expiration is not None) and (t <= faruzan_buff_expiration)
                if faruzan_buff_active and e_type == "HIT" and hit_name != "Pressurized_Collapse":
                    if t >= faruzan_collapse_cd_expires:
                        collapse_time = t + 0.720
                        faruzan_collapse_cd_expires = collapse_time + 3.0
                        self.global_events.insert(i + 1, {
                            "global_time": collapse_time,
                            "character": "Faruzan",
                            "action": "Pressurized Collapse",
                            "category": faruzan_collapse_hit.category,
                            "elem_app": faruzan_collapse_hit.elemental_app,
                            "element": faruzan_collapse_hit.element,
                            "event_type": "HIT",
                            "hit_name": "Pressurized_Collapse",
                            "ability_name": "Pressurized Collapse"
                        })

                faruzan_debuff_active = (faruzan_debuff_expiration is not None) and (t <= faruzan_debuff_expiration)
                event["faruzan_buff_state"] = "ON" if faruzan_buff_active else "OFF"
                event["faruzan_debuff_state"] = "ON" if faruzan_debuff_active else "OFF"
            else:
                event["faruzan_buff_state"] = "OFF"
                event["faruzan_debuff_state"] = "OFF"

            # 4. Aura Processing & Stellar Swirls
            gauge_u = self._parse_gauge(elem_app)
            reaction, is_stellar_swirl, swirl_meta = aura_tracker.apply_element(element, gauge_u, char, current_time=t)

            if is_stellar_swirl and swirl_meta:
                # Check if Mizuki is in the party and has at least C1, and her debuff is active
                mizuki_data = self.party.get("Mizuki", {})
                mizuki_c1_unlocked = mizuki_data.get("constellation", 0) >= 1

                c1_debuff_active = mizuki_c1_unlocked and (t <= mizuki_c1_debuff_expiration)
                if c1_debuff_active:
                    mizuki_c1_debuff_expiration = -1.0

                # Reaction Trigger Artifacts
                if vv_holder and char == vv_holder and active_character == vv_holder:
                    vv_expiration_time = t + 10.0

                if instructor_holder and char == instructor_holder and active_character == instructor_holder:
                    instructor_expiration_time = t + 10.0

                swirl_hit_event = {
                    "global_time": t,
                    "active_character": active_character,
                    "character": char,
                    "action": "Stellar Swirl DMG",
                    "category": ActionCategory.STELLAR_REACTION,
                    "elem_app": "-",
                    "element": "Anemo",
                    "event_type": "HIT",
                    "hit_name": "Stellar_Swirl_Hit",
                    "ability_name": "Stellar Swirl",
                    "reaction": "Stellar Swirl",
                    "swirl_metadata": swirl_meta,
                    "c1_empowered": c1_debuff_active,
                    "fanz_buff_state": event.get("fanz_buff_state", "OFF"),
                    "fanz_debuff_state": event.get("fanz_debuff_state", "OFF"),
                    "aether_c2_state": event.get("aether_c2_state", "OFF"),
                    "marvelous_stacks": event.get("marvelous_stacks", 0),
                    "hotf_state": event.get("hotf_state", "OFF"),
                    "dreamdrifter_state": event.get("dreamdrifter_state", "OFF")
                }
                self.global_events.insert(i + 1, swirl_hit_event)

                if c1_debuff_active:
                    mini_nuke_event = {
                        "global_time": t,
                        "active_character": active_character,
                        "character": "Mizuki",
                        "action": "Mizuki C1 Mini Nuke",
                        "category": ActionCategory.STELLAR_DMG,
                        "elem_app": "-",
                        "element": "Anemo",
                        "event_type": "HIT",
                        "hit_name": "C1_Mini_Nuke",
                        "ability_name": "Mizuki C1",
                        "reaction": "-",
                        "fanz_buff_state": event.get("fanz_buff_state", "OFF"),
                        "fanz_debuff_state": event.get("fanz_debuff_state", "OFF"),
                        "aether_c2_state": event.get("aether_c2_state", "OFF"),
                        "marvelous_stacks": event.get("marvelous_stacks", 0),
                        "hotf_state": event.get("hotf_state", "OFF"),
                        "dreamdrifter_state": event.get("dreamdrifter_state", "OFF")
                    }
                    self.global_events.insert(i + 2, mini_nuke_event)

                if active_vortex is None or not active_vortex.is_active:
                    active_vortex = StellarVortex(creation_swirl_meta=swirl_meta, creation_time=t)
                    reaction = "SSW (Vortex Spawn)"
                else:
                    exploded_early, reaction_msg = active_vortex.inherit_swirl(swirl_meta)
                    reaction = reaction_msg

                    if exploded_early:
                        active_vortex.is_active = False
                        explosion_event = {
                            "global_time": t,
                            "active_character": active_character,
                            "character": active_vortex.last_trigger,
                            "action": f"Vortex Explosion (Lv{active_vortex.level} Early)",
                            "category": ActionCategory.STELLAR_REACTION,
                            "elem_app": "1U",
                            "element": "Cryo",
                            "event_type": "HIT",
                            "hit_name": f"Vortex_Exp_Lv{active_vortex.level}",
                            "ability_name": "Stellar Vortex",
                            "reaction": f"Vortex Lv{active_vortex.level} Exp",
                            "vortex_metadata": {
                                "primary_credit": active_vortex.last_trigger,
                                "creation_credit": active_vortex.creator,
                                "anemo_contributors": list(active_vortex.anemo_contributors),
                                "cryo_contributors": list(active_vortex.cryo_contributors),
                                "level": active_vortex.level
                            },
                            "fanz_buff_state": event.get("fanz_buff_state", "OFF"),
                            "fanz_debuff_state": event.get("fanz_debuff_state", "OFF"),
                            "aether_c2_state": event.get("aether_c2_state", "OFF"),
                            "marvelous_stacks": event.get("marvelous_stacks", 0),
                            "hotf_state": event.get("hotf_state", "OFF"),
                            "dreamdrifter_state": event.get("dreamdrifter_state", "OFF")
                        }
                        insertion_offset = 3 if c1_debuff_active else 2
                        self.global_events.insert(i + 2, explosion_event)
                        active_vortex = None

            # 5. Mizuki Nuke Preparation Check
            if is_stellar_swirl and char == "Mizuki" and mizuki_dreamdrifter_active:
                if t >= mizuki_nuke_prep_cd_expires:
                    mizuki_nuke_armed = True
                    mizuki_nuke_armed_time = t
                    mizuki_nuke_prep_cd_expires = t + 2.5

            event["cryo_aura"] = f"{aura_tracker.current_gauge:.2f}U"
            event["reaction"] = reaction if reaction else "-"

            vv_active = (vv_expiration_time is not None) and (t <= vv_expiration_time)
            event["vv_state"] = "ON" if vv_active else "OFF"

            instructor_active = (instructor_expiration_time is not None) and (t <= instructor_expiration_time)
            event["instructor_state"] = "ON" if instructor_active else "OFF"

            cryo_resonance_active = aura_tracker.current_gauge > 0.0
            event["cryo_resonance_state"] = "ON" if cryo_resonance_active else "OFF"

            # 6. Aether C2 Logic (Requires C2+)
            aether_data = self.party.get("Aether", {})
            if aether_data.get("constellation", 0) >= 2:
                if e_type == "HIT" and char == "Aether" and ability_name == "Elemental Skill":
                    if hit_name != "Skill_Initial":
                        aether_c2_active = True
                elif e_type == "SWAP_OUT" and char == "Aether":
                    aether_c2_active = False
                event["aether_c2_state"] = "ON" if aether_c2_active else "OFF"
            else:
                event["aether_c2_state"] = "OFF"

            # 7. Odette Marvelous Stacks Logic
            if "Odette" in self.party:
                if e_type == "HIT" and char == "Odette" and hit_name == "Skill_Cast":
                    marvelous_active = True
                    marvelous_activation_time = t
                    odette_swap_time = None

                if marvelous_active and (t - marvelous_activation_time >= 20.0):
                    marvelous_active = False

                if e_type == "SWAP_OUT" and char == "Odette" and marvelous_active:
                    odette_swap_time = t

                odette_stacks = 0
                party_stacks = 0
                if marvelous_active:
                    if odette_swap_time is None or t < odette_swap_time:
                        odette_stacks = 4
                        party_stacks = 0
                    else:
                        time_off_field = t - odette_swap_time
                        stacks_transferred = min(4, int(time_off_field))
                        odette_stacks = 4 - stacks_transferred
                        party_stacks = stacks_transferred

                if char == "Odette":
                    event["marvelous_stacks"] = odette_stacks
                else:
                    event["marvelous_stacks"] = party_stacks

            else:
                event["marvelous_stacks"] = 0

            # 8. Heart of the Furnace (HotF) Gear Effect Logic
            # Triggers when whoever holds the gear piece deals Stellar DMG
            if hotf_holder and char == hotf_holder and e_type == "HIT" and cat == ActionCategory.STELLAR_DMG:
                hotf_expiration_time = t + 12.0

            hotf_active = (hotf_expiration_time is not None) and (t <= hotf_expiration_time)
            event["hotf_state"] = "ON" if hotf_active else "OFF"


            # 9. Mizuki Dreamdrifter & Nuke Firing Logic
            mizuki_data = self.party.get("Mizuki", {})
            mizuki_c1_unlocked = mizuki_data.get("constellation", 0) >= 1

            if "Mizuki" in self.party:
                if char == "Mizuki":
                    if e_type == "HIT" and "Mizuki Skill" in ability_name and hit_name == "Cast":
                        mizuki_dreamdrifter_active = True
                        if t >= mizuki_nuke_prep_cd_expires:
                            mizuki_nuke_armed = True
                            mizuki_nuke_prep_cd_expires = t + 2.5
                    elif e_type == "SWAP_OUT":
                        mizuki_dreamdrifter_active = False

                    if mizuki_c1_unlocked:
                        if e_type == "HIT" and "Mizuki Skill" in ability_name and mizuki_dreamdrifter_active:
                            if t >= mizuki_c1_app_cooldown_expires:
                                mizuki_c1_debuff_expiration = t + 3.0
                                mizuki_c1_app_cooldown_expires = t + 3.5

                event["dreamdrifter_state"] = "ON" if mizuki_dreamdrifter_active else "OFF"

                event["nuke_fired"] = False
                if char == "Mizuki" and "Mizuki Skill" in ability_name and hit_name.startswith("Tick"):
                    if mizuki_dreamdrifter_active and mizuki_nuke_armed and t > mizuki_nuke_armed_time:
                        event["nuke_fired"] = True
                        mizuki_nuke_armed = False

                        nuke_hit_time = t + 0.5
                        self.global_events.insert(i + 1, {
                            "global_time": nuke_hit_time,
                            "active_character": active_character,
                            "character": "Mizuki",
                            "action": "Mizuki Nuke Hit",
                            "category": ActionCategory.STELLAR_DMG,
                            "elem_app": "-",
                            "element": "Anemo",
                            "event_type": "HIT",
                            "hit_name": "Nuke_Hit",
                            "ability_name": "Mizuki Nuke",
                            "reaction": "-",
                            "fanz_buff_state": event.get("fanz_buff_state", "OFF"),
                            "fanz_debuff_state": event.get("fanz_debuff_state", "OFF"),
                            "aether_c2_state": event.get("aether_c2_state", "OFF"),
                            "marvelous_stacks": event.get("marvelous_stacks", 0),
                    "hotf_state": event.get("hotf_state", "OFF"),
                            "dreamdrifter_state": event.get("dreamdrifter_state", "OFF")
                        })
            else:
                event["dreamdrifter_state"] = "OFF"
                event["nuke_fired"] = False

            i += 1

    def display(self):
        self.evaluate_timeline()

        # Check which optional buffs are actually used/triggered across all events
        has_vv = any(ev.get("vv_state") == "ON" for ev in self.global_events)
        has_instructor = any(ev.get("instructor_state") == "ON" for ev in self.global_events)
        has_hotf = any(ev.get("hotf_state") == "ON" for ev in self.global_events)
        has_fanz = any(ev.get("faruzan_buff_state") == "ON" for ev in self.global_events)
        has_c2 = any(ev.get("aether_c2_state") == "ON" for ev in self.global_events)
        has_dream = any(ev.get("dreamdrifter_state") == "ON" for ev in self.global_events)
        has_cryo_resonance = any(ev.get("cryo_resonance_state") == "ON" for ev in self.global_events)

        # Build dynamic header components
        headers = ["Time (s)", "Active", "Owner", "Action", "Aura (Cryo)", "Reaction"]
        if has_fanz:
            headers.extend(["FanzBuff", "FanzDebuff"])
        if has_c2:
            headers.append("AetherC2")
        headers.append("Marvelous")
        if has_hotf:
            headers.append("HotF")
        if has_dream:
            headers.append("Dream")
        if has_vv:
            headers.append("VV")
        if has_instructor:
            headers.append("Instructor")
        if has_cryo_resonance:
            headers.append("CryoResonance")

        # Format widths
        col_widths = [10, 8, 8, 36, 11, 24]
        if has_fanz:
            col_widths.extend([9, 12])
        if has_c2:
            col_widths.append(9)
        col_widths.append(10) # Marvelous
        if has_hotf:
            col_widths.append(5)
        if has_dream:
            col_widths.append(7)
        if has_vv:
            col_widths.append(5)
        if has_instructor:
            col_widths.append(10)
        if has_cryo_resonance:
            col_widths.append(12)

        # Print Header
        header_str = " | ".join(f"{h:<{w}}" for h, w in zip(headers, col_widths))
        print(header_str)
        print("-" * len(header_str))

        # Print Rows
        for event in self.global_events:
            row_data = [
                f"{event['global_time']:.3f}",
                event['active_character'],
                event['character'],
                event['action'],
                event['cryo_aura'],
                event['reaction']
            ]
            if has_fanz:
                row_data.extend([event.get('faruzan_buff_state', 'OFF'), event.get('faruzan_debuff_state', 'OFF')])
            if has_c2:
                row_data.append(event.get('aether_c2_state', 'OFF'))
            row_data.append(str(event.get('marvelous_stacks', 0)))
            if has_hotf:
                row_data.append(event.get('hotf_state', 'OFF'))
            if has_dream:
                row_data.append(event.get('dreamdrifter_state', 'OFF'))
            if has_vv:
                row_data.append(event.get('vv_state', 'OFF'))
            if has_instructor:
                row_data.append(event.get('instructor_state', 'OFF'))
            if has_cryo_resonance:
                row_data.append(event.get('cryo_resonance_state', 'OFF'))

            row_str = " | ".join(f"{val:<{w}}" for val, w in zip(row_data, col_widths))
            print(row_str)


# ==========================================
# 6. TESTING EXECUTION
# ==========================================

if __name__ == "__main__":
    my_party = {
        "Aether": {"constellation": 4, "weapon": "Favonius Sword", "artifact": "Noblesse"},
        "Odette": {"constellation": 0, "weapon": "Heart of the Furnace", "artifact": "Blizzard Strayer"},
        "Faruzan": {"constellation": 6, "weapon": "Elegy", "artifact": "Tenacity"},
        "Mizuki": {"constellation": 2, "weapon": "Sacrificial Fragments", "artifact": "Viridescent"}
    }

    timeline = RotationTimeline(party=my_party)
    current_time = 0.0

    current_time = timeline.add_combo(aether_en1, swap_in_time=current_time)
    current_time = timeline.add_combo(faruzan_q, swap_in_time=current_time)
    current_time = timeline.add_combo(odette_ee, swap_in_time=current_time)
    current_time = timeline.add_combo(mizuki_sacfrag_fill, swap_in_time=current_time)
    current_time = timeline.add_combo(aether_cq, swap_in_time=current_time)
    current_time = timeline.add_combo(mizuki_burstless_pull_out, swap_in_time=current_time)

    timeline.display()