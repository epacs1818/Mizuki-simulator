from typing import Dict, List, Optional, Tuple

from models import ActionCategory, FieldSequence, AttackType, StatRef, Rotation, Trial
from aura import CryoAuraTracker
from mechanics import StellarVortex, stellar_swirl_hit
from abilities import (
    mizuki_nuke_hit,
    mizuki_c1_mini_nuke_hit,
    configure_field_sequence_talents,
    get_ability_motion_value,
)
from damage_calc import calculate_damage, DEFAULT_ENEMY_STATS
from stats_calc import build_initial_stats, apply_permanent_buffs, build_snapshot_stats, compute_final_stats


# ==========================================
# 5. TIMELINE ENGINE & EVALUATOR
# ==========================================

class RotationTimeline:
    def __init__(self, party: Optional[Dict[str, dict]] = None, enemy_stats: Optional[Dict[str, float]] = None):
        self.global_events = []
        self.last_used_timestamps: Dict[Tuple[str, str], float] = {}
        self.enemy_stats = enemy_stats if enemy_stats is not None else DEFAULT_ENEMY_STATS.copy()

        # Normalize party structure: ensure every entry has dict metadata
        self.party: Dict[str, dict] = {}
        if party:
            for char, data in party.items():
                if isinstance(data, int):  # Backward compatibility if someone passes just an int constellation
                    self.party[char] = {"constellation": data, "weapon": None, "artifact": None}
                else:
                    self.party[char] = data

        self._prepare_character_stats()

    def _prepare_character_stats(self):
        self.char_initial_stats_map = {}
        for char_name, data in self.party.items():
            char_level = data.get("level")
            weapon = data.get("weapon")
            artifact = data.get("artifact")
            main_stats = data.get("main_stats_total", {})
            subs = data.get("subs_total", {})
            init_s = build_initial_stats(char_name, char_level, weapon, artifact, main_stats, subs)
            init_s = apply_permanent_buffs(init_s, char_name)
            self.char_initial_stats_map[char_name] = init_s

    def add_field_sequence(self, field_sequence: FieldSequence, swap_in_time: float) -> float:
        if field_sequence.character not in self.party:
            # Auto-register missing characters with default settings
            self.party[field_sequence.character] = {"constellation": 0, "weapon": None, "artifact": None}
            self._prepare_character_stats()

        # Apply talent levels from party configuration if specified
        char_data = self.party.get(field_sequence.character, {})
        talents = char_data.get("talents")
        if talents:
            field_sequence = configure_field_sequence_talents(field_sequence, talents)

        self.global_events.append({
            "global_time": swap_in_time,
            "character": field_sequence.character,
            "action": "Swap In",
            "category": ActionCategory.SWAP,
            "elem_app": "-",
            "element": None,
            "event_type": "SWAP_IN"
        })

        swap_out_global = swap_in_time + field_sequence.swap_out_time
        self.global_events.append({
            "global_time": swap_out_global,
            "character": field_sequence.character,
            "action": "Swap Out",
            "category": ActionCategory.SWAP,
            "elem_app": "-",
            "element": None,
            "event_type": "SWAP_OUT"
        })

        for call in field_sequence.calls:
            ability_start_global = swap_in_time + call.start_time
            ability_key = (field_sequence.character, call.ability.name)

            if call.ability.cooldown > 0 and ability_key in self.last_used_timestamps:
                last_time = self.last_used_timestamps[ability_key]
                cd_expires_at = last_time + call.ability.cooldown
                if ability_start_global < cd_expires_at:
                    raise ValueError(f"[COOLDOWN ERROR] {field_sequence.character}'\''s {call.ability.name} on CD until {cd_expires_at:.3f}s")

            if call.ability.cooldown > 0:
                self.last_used_timestamps[ability_key] = ability_start_global

            self.global_events = [
                ev for ev in self.global_events
                if not (ev.get("event_type") == "HIT" and
                        ev.get("character") == field_sequence.character and
                        ev.get("ability_name") == call.ability.name and
                        ev["global_time"] >= ability_start_global)
            ]

            for hit in call.ability.hits:
                hit_global_time = ability_start_global + hit.relative_delay
                self.global_events.append({
                    "global_time": hit_global_time,
                    "character": field_sequence.character,
                    "action": f"{call.ability.name} ({hit.name})",
                    "category": hit.category,
                    "elem_app": hit.elemental_app if hit.elemental_app else "-",
                    "element": hit.element,
                    "event_type": "HIT",
                    "hit_name": hit.name,
                    "ability_name": call.ability.name,
                    "stat_ref": hit.stat_ref,
                    "multiplier": hit.multiplier,
                    "attack_type": hit.attack_type
                })

        self.global_events.sort(key=lambda x: x["global_time"])
        return swap_out_global

    def add_rotation(self, rotation: Rotation, start_time: float = 0.0) -> float:
        current_time = start_time
        for _ in range(rotation.repetitions):
            for field_sequence in rotation.sequences:
                # Reuse your existing field sequence addition logic
                current_time = self.add_field_sequence(field_sequence, swap_in_time=current_time)
        return current_time

    def add_trial(self, trial: Trial) -> float:
        current_time = 0.0
        for rotation in trial.rotations:
            current_time = self.add_rotation(rotation, start_time=current_time)
        
        # If set to last swap, calculate it and write it back to trial.end_time
        if trial.end_mode == "last_swap":
            swap_out_times = [
                ev["global_time"] for ev in self.global_events
                if ev.get("event_type") == "SWAP_OUT"
            ]
            if swap_out_times:
                trial.end_time = max(swap_out_times)
        
        # Enforce cutoff using the finalized trial.end_time
        self.global_events = [
            ev for ev in self.global_events
            if ev["global_time"] <= trial.end_time
        ]
        return trial.end_time

    def _cancel_pending_ability_hits(self, character: str, ability_name: str, current_time: float):
        """Internal helper method to scrub overlapping future hits."""
        self.global_events = [
            ev for ev in self.global_events
            if not (
                ev.get("event_type") == "HIT" and
                ev.get("character") == character and
                ev.get("ability_name") == ability_name and
                ev["global_time"] >= current_time
            )
        ]

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
        mizuki_data = self.party.get("Mizuki", {})
        mizuki_constellation = mizuki_data.get("constellation", 0)
        mizuki_c1_unlocked = mizuki_constellation >= 1
        mizuki_c6_unlocked = mizuki_constellation >= 6

        mizuki_dreamdrifter_active = False
        mizuki_a4_expiration: float = -1.0
        mizuki_nuke_armed = False
        mizuki_nuke_prep_cd_expires: float = -1.0
        mizuki_c1_debuff_expiration: float = -1.0
        mizuki_c1_app_cooldown_expires: float = -1.0
        mizuki_nuke_armed_time: float = -1.0
       

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
                event["active_character"] = active_character
            elif e_type == "SWAP_OUT":
                event["active_character"] = char
                active_character = "None"
            else:
                event["active_character"] = active_character

            fire_vbtd_nuke = False
            if "Mizuki" in self.party:
                mizuki_data = self.party.get("Mizuki", {})
                mizuki_constellation = mizuki_data.get("constellation", 0)
                mizuki_c1_unlocked = mizuki_constellation >= 1
                is_mizuki_skill = "Skill" in ability_name or "Mizuki" in ability_name or char == "Mizuki"

                if char == "Mizuki":
                    # DDS Enters immediately at skill cast
                    if e_type == "HIT" and is_mizuki_skill and hit_name == "Cast":
                        mizuki_dreamdrifter_active = True

                    # DDS Exits on Swap Out or last tick (Tick13)
                    if e_type == "SWAP_OUT" or hit_name == "Tick13":
                        mizuki_dreamdrifter_active = False
                        mizuki_a4_expiration = -1.0

                    # C1 Debuff Application on every skill hit during DDS
                    if mizuki_c1_unlocked and e_type == "HIT" and is_mizuki_skill and mizuki_dreamdrifter_active:
                        if t >= mizuki_c1_app_cooldown_expires:
                            mizuki_c1_debuff_expiration = t + 3.0
                            mizuki_c1_app_cooldown_expires = t + 3.5

                # A4 Refresh Logic: Triggers on Cryo elemental hit during DDS (no gauge check required)
                if mizuki_dreamdrifter_active and element == "Cryo" and e_type == "HIT":
                    mizuki_a4_expiration = t + 4.0

                mizuki_a4_active = mizuki_dreamdrifter_active and (t <= mizuki_a4_expiration)
                c1_debuff_active = mizuki_c1_unlocked and (t <= mizuki_c1_debuff_expiration)

                # VBTD Quill Assignment & Nuke Firing on Subsequent Skill Ticks
                vbtd_quill_active = False
                if char == "Mizuki" and is_mizuki_skill and hit_name.startswith("Tick"):
                    if mizuki_dreamdrifter_active and mizuki_nuke_armed and t > mizuki_nuke_armed_time:
                        vbtd_quill_active = True
                        fire_vbtd_nuke = True
                        mizuki_em = self.char_initial_stats_map.get("Mizuki", {}).get("em", 0.0)
                        event["quill_damage"] = mizuki_em * 10.0
                        mizuki_nuke_armed = False

                # Inject Auditable States into Event Dict for UI / Console Table
                event["dreamdrifter_state"] = "ON" if mizuki_dreamdrifter_active else "OFF"
                event["mizuki_a4_state"] = "ON" if mizuki_a4_active else "OFF"
                event["vbtd_state"] = "ON" if vbtd_quill_active else "OFF"
                event["c1_debuff_state"] = "ON" if c1_debuff_active else "OFF"
            else:
                event["dreamdrifter_state"] = "OFF"
                event["mizuki_a4_state"] = "OFF"
                event["vbtd_state"] = "OFF"
                event["c1_debuff_state"] = "OFF"

            # 3. Faruzan Buff & Debuff Logic
            if "Faruzan" in self.party:
                # Helper to safely pull Faruzan's skill talent level (index 1 of int/int/int)
                far_talents = self.party.get("Faruzan", {}).get("talents", "1/13/13")
                if isinstance(far_talents, str):
                    skill_lvl = int(far_talents.split("/")[1])
                else:
                    skill_lvl = far_talents[1]

                # Helper function to build the dynamic collapse event dictionary
                def create_collapse_event(c_time):
                    collapse_mv = get_ability_motion_value("Faruzan", "Skill", "Pressurized Collapse Vortex DMG", skill_lvl)
                    return {
                        "global_time": c_time,
                        "character": "Faruzan",
                        "action": "Pressurized Collapse",
                        "category": ActionCategory.STANDARD_DMG,
                        "elem_app": "1U",
                        "element": "Anemo",
                        "event_type": "HIT",
                        "hit_name": "Pressurized_Collapse",
                        "ability_name": "Pressurized Collapse",
                        "stat_ref": StatRef.ATK,
                        "multiplier": collapse_mv,
                        "attack_type": AttackType.SKILL
                    }

                # 1. Insertion upon Burst Cast
                if e_type == "HIT" and char == "Faruzan" and ability_name == "Elemental Burst" and hit_name == "Burst_Cast":
                    faruzan_buff_expiration = t + 22.0
                    faruzan_debuff_expiration = t + 22.0
                    collapse_time = t + 0.720  # standard delay for pressurized collapse
                    faruzan_collapse_cd_expires = collapse_time + 3.0

                    self.global_events.insert(i + 1, create_collapse_event(collapse_time))

                if e_type == "HIT" and hit_name == "Pressurized_Collapse":
                    faruzan_debuff_expiration = t + 4.0

                faruzan_buff_active = (faruzan_buff_expiration is not None) and (t <= faruzan_buff_expiration)
                
                # 2. Insertion upon Passive Trigger during Buff Window
                if faruzan_buff_active and e_type == "HIT" and hit_name != "Pressurized_Collapse":
                    if t >= faruzan_collapse_cd_expires:
                        collapse_time = t + 0.720
                        faruzan_collapse_cd_expires = collapse_time + 3.0
                        self.global_events.insert(i + 1, create_collapse_event(collapse_time))

                faruzan_debuff_active = (faruzan_debuff_expiration is not None) and (t <= faruzan_debuff_expiration)
                event["faruzan_buff_state"] = "ON" if faruzan_buff_active else "OFF"
                event["faruzan_debuff_state"] = "ON" if faruzan_debuff_active else "OFF"
            else:
                event["faruzan_buff_state"] = "OFF"
                event["faruzan_debuff_state"] = "OFF"

            # 4. Elemental Aura & Reaction Processing
            reaction = None
            is_stellar_swirl = False

            if e_type == "HIT":
                gauge_u = self._parse_gauge(elem_app)
                reaction, is_stellar_swirl, swirl_meta = aura_tracker.apply_element(element, gauge_u, char, t)

                # VV Shred trigger
                if is_stellar_swirl and vv_holder and char == vv_holder:
                    vv_expiration_time = t + 10.0

                # Instructor trigger
                if is_stellar_swirl and instructor_holder and char == instructor_holder:
                    instructor_expiration_time = t + 12.0

                # Stellar Vortex & Stellar Swirl mechanics
                if is_stellar_swirl and swirl_meta:
                    current_c1_active = (event.get("c1_debuff_state") == "ON")
                    if current_c1_active:
                        mizuki_c1_debuff_expiration = -1.0

                    swirl_hit_event = {
                        "global_time": t,
                        "active_character": active_character,
                        "character": char,
                        "action": stellar_swirl_hit.name,
                        "category": stellar_swirl_hit.category,
                        "elem_app": stellar_swirl_hit.elemental_app if stellar_swirl_hit.elemental_app else "-",
                        "element": stellar_swirl_hit.element,
                        "event_type": "HIT",
                        "hit_name": "Stellar_Swirl_Hit",
                        "ability_name": "Stellar Swirl",
                        "stat_ref": stellar_swirl_hit.stat_ref,
                        "multiplier": stellar_swirl_hit.multiplier,
                        "attack_type": stellar_swirl_hit.attack_type,
                        "reaction": "Stellar Swirl",
                        "swirl_metadata": swirl_meta,
                        "c1_empowered": current_c1_active,
                        "dreamdrifter_state": event.get("dreamdrifter_state", "OFF"),
                        "mizuki_a4_state": event.get("mizuki_a4_state", "OFF"),
                        "vbtd_state": event.get("vbtd_state", "OFF"),
                        "c1_debuff_state": event.get("c1_debuff_state", "OFF"),
                        "fanz_buff_state": event.get("fanz_buff_state", "OFF"),
                        "fanz_debuff_state": event.get("fanz_debuff_state", "OFF"),
                        "aether_c2_state": event.get("aether_c2_state", "OFF"),
                        "marvelous_stacks": event.get("marvelous_stacks", 0),
                        "hotf_state": event.get("hotf_state", "OFF"),                        
                    }
                    self.global_events.insert(i + 1, swirl_hit_event)

                    if current_c1_active:
                        mizuki_em = self.char_initial_stats_map.get("Mizuki", {}).get("em", 0.0)
                        swirl_hit_event["quill_damage"] = mizuki_em * 5.5

                        mini_nuke_event = {
                            "global_time": t + mizuki_c1_mini_nuke_hit.relative_delay,
                            "active_character": active_character,
                            "character": "Mizuki",
                            "action": mizuki_c1_mini_nuke_hit.name,
                            "category": mizuki_c1_mini_nuke_hit.category,
                            "elem_app": mizuki_c1_mini_nuke_hit.elemental_app if mizuki_c1_mini_nuke_hit.elemental_app else "-",
                            "element": mizuki_c1_mini_nuke_hit.element,
                            "event_type": "HIT",
                            "hit_name": "C1_Mini_Nuke",
                            "ability_name": "Mizuki C1",
                            "stat_ref": mizuki_c1_mini_nuke_hit.stat_ref,
                            "multiplier": mizuki_c1_mini_nuke_hit.multiplier,
                            "attack_type": mizuki_c1_mini_nuke_hit.attack_type,
                            "reaction": "-",
                            "dreamdrifter_state": event.get("dreamdrifter_state", "OFF"),
                            "mizuki_a4_state": event.get("mizuki_a4_state", "OFF"),
                            "vbtd_state": event.get("vbtd_state", "OFF"),
                            "c1_debuff_state": event.get("c1_debuff_state", "OFF"),
                            "fanz_buff_state": event.get("fanz_buff_state", "OFF"),
                            "fanz_debuff_state": event.get("fanz_debuff_state", "OFF"),
                            "aether_c2_state": event.get("aether_c2_state", "OFF"),
                            "marvelous_stacks": event.get("marvelous_stacks", 0),
                            "hotf_state": event.get("hotf_state", "OFF")
                        }
                        self.global_events.insert(i + 2, mini_nuke_event)

                    if active_vortex is None or not active_vortex.is_active:
                        active_vortex = StellarVortex(swirl_meta, t)
                        reaction = "SSW (Vortex Spawn)"
                    else:
                        exploded, reaction = active_vortex.inherit_swirl(swirl_meta)
                        if exploded:
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
                            self.global_events.insert(i + insertion_offset, explosion_event)
                            active_vortex = None

            # 5. Mizuki Nuke Preparation Check
            if is_stellar_swirl and char == "Mizuki" and mizuki_dreamdrifter_active:
                if t >= mizuki_nuke_prep_cd_expires:
                    mizuki_nuke_armed = True
                    mizuki_nuke_armed_time = t
                    mizuki_nuke_prep_cd_expires = t + 2.5

            # VBTD Nuke Hit Insertion (fired on subsequent skill tick)
            if fire_vbtd_nuke:
                nuke_hit_time = t + mizuki_nuke_hit.relative_delay
                nuke_event = {
                    "global_time": nuke_hit_time,
                    "active_character": active_character,
                    "character": "Mizuki",
                    "action": mizuki_nuke_hit.name,
                    "category": mizuki_nuke_hit.category,
                    "elem_app": mizuki_nuke_hit.elemental_app if mizuki_nuke_hit.elemental_app else "-",
                    "element": mizuki_nuke_hit.element,
                    "event_type": "HIT",
                    "hit_name": mizuki_nuke_hit.name,
                    "ability_name": "Mizuki Nuke",
                    "stat_ref": mizuki_nuke_hit.stat_ref,
                    "multiplier": mizuki_nuke_hit.multiplier,
                    "attack_type": mizuki_nuke_hit.attack_type,
                    "reaction": "-",
                    "dreamdrifter_state": event.get("dreamdrifter_state", "OFF"),
                    "mizuki_a4_state": event.get("mizuki_a4_state", "OFF"),
                    "vbtd_state": "OFF",
                    "c1_debuff_state": event.get("c1_debuff_state", "OFF"),
                    "fanz_buff_state": event.get("fanz_buff_state", "OFF"),
                    "fanz_debuff_state": event.get("fanz_debuff_state", "OFF"),
                    "aether_c2_state": event.get("aether_c2_state", "OFF"),
                    "marvelous_stacks": event.get("marvelous_stacks", 0),
                    "hotf_state": event.get("hotf_state", "OFF"),
                }
                nuke_offset = 1
                if is_stellar_swirl and swirl_meta:
                    nuke_offset += 1
                    if current_c1_active:
                        nuke_offset += 1
                self.global_events.insert(i + nuke_offset, nuke_event)

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

            i += 1

        self._calculate_all_hits_damage()

    def _calculate_all_hits_damage(self):
        for event in self.global_events:
            if event.get("event_type") == "HIT":
                char = event.get("character")
                active_char = event.get("active_character", "None")
                char_data = self.party.get(char, {})
                char_refinement = char_data.get("refinement", 1)
                char_level = char_data.get("level", 90)

                init_stats = self.char_initial_stats_map.get(char)
                if init_stats is None:
                    init_stats = build_initial_stats(char, None, None, {}, {})
                    init_stats = apply_permanent_buffs(init_stats, char)
                    self.char_initial_stats_map[char] = init_stats

                snapshot = build_snapshot_stats(
                    initial_stats=init_stats,
                    event_flags=event,
                    party=self.party,
                    refinement=char_refinement,
                    char_name=char,
                    active_character=active_char,
                    char_initial_stats_map=self.char_initial_stats_map,
                )
                final_stats = compute_final_stats(snapshot)

                # Prepare party_stats_dict for reaction contributors
                party_stats_dict = {}
                for p_name, p_d in self.party.items():
                    p_init = self.char_initial_stats_map.get(p_name, {})
                    party_stats_dict[p_name] = {
                        "level": p_d.get("level", 90),
                        "CR": p_init.get("crit_rate", 0.05),
                        "CD": p_init.get("crit_dmg", 0.50),
                        "crit_rate": p_init.get("crit_rate", 0.05),
                        "crit_dmg": p_init.get("crit_dmg", 0.50),
                    }
                    if event.get("cryo_resonance_state") == "ON":
                        party_stats_dict[p_name]["CR"] += 0.15
                        party_stats_dict[p_name]["crit_rate"] += 0.15

                if char in party_stats_dict:
                    party_stats_dict[char]["CR"] = final_stats.get("CR", party_stats_dict[char]["CR"])
                    party_stats_dict[char]["CD"] = final_stats.get("CD", party_stats_dict[char]["CD"])

                dmg = calculate_damage(
                    hit=event,
                    final_stats=final_stats,
                    enemy_stats=self.enemy_stats,
                    quill_damage=event.get("quill_damage", 0.0),
                    char_level=char_level,
                    party_dict=party_stats_dict,
                )

                event["non_crit"] = dmg.get("non_crit", 0.0)
                event["crit_damage"] = dmg.get("crit_damage", 0.0)
                event["average_damage"] = dmg.get("average_damage", 0.0)
                event["effective_average_damage"] = dmg.get("effective_average_damage", 0.0)
            else:
                event["non_crit"] = None
                event["crit_damage"] = None
                event["average_damage"] = None
                event["effective_average_damage"] = None

    def get_analytics_summary(self, trial_end_time: float) -> dict:
        """
        Aggregates simulation results into structured analytics for UI visualization:
        - Total Damage & Overall DPS
        - Damage breakdown by Element
        - Damage breakdown by Hit Type / Category
        - Damage share by Owner (excluding stellar reactions)
        - Per-second DPS timeline breakdown
        """
        if not self.global_events or trial_end_time <= 0:
            return {}

        total_damage = 0.0
        element_breakdown: Dict[str, float] = {}
        hit_type_breakdown: Dict[str, float] = {}
        owner_damage_share: Dict[str, float] = {}
        
        # Per-second binning
        max_time = max((ev["global_time"] for ev in self.global_events), default=trial_end_time)
        max_sec = int(max_time) + 1
        second_damage = {s: 0.0 for s in range(max_sec + 1)}

        for event in self.global_events:
            if event.get("event_type") != "HIT":
                continue
            
            dmg = event.get("average_damage", 0.0) or 0.0
            if dmg <= 0:
                continue

            total_damage += dmg
            
            # 1. Element breakdown
            elem = event.get("element") or "Physical"
            element_breakdown[elem] = element_breakdown.get(elem, 0.0) + dmg

            # 2. Hit type breakdown (category)
            cat = event.get("category")
            cat_str = cat.name if hasattr(cat, "name") else (cat.value if hasattr(cat, "value") else str(cat))
            hit_type_breakdown[cat_str] = hit_type_breakdown.get(cat_str, 0.0) + dmg

            # 3. Owner damage share (explicitly excluding stellar reactions)
            char = event.get("character", "Unknown")
            is_reaction = "REACTION" in cat_str.upper() or cat == ActionCategory.STELLAR_REACTION
            if not is_reaction:
                owner_damage_share[char] = owner_damage_share.get(char, 0.0) + dmg

            # 4. Per-second binning
            sec = int(event.get("global_time", 0.0))
            second_damage[sec] = second_damage.get(sec, 0.0) + dmg

        overall_dps = total_damage / trial_end_time if trial_end_time > 0 else 0.0

        # Format per-second list for histogram/bar chart
        dps_timeline = [
            {"Second": s, "DPS": d} 
            for s, d in sorted(second_damage.items()) 
            if s <= int(trial_end_time) or d > 0
        ]

        return {
            "total_damage": total_damage,
            "overall_dps": overall_dps,
            "element_breakdown": element_breakdown,
            "hit_type_breakdown": hit_type_breakdown,
            "owner_damage_share": owner_damage_share,
            "dps_timeline": dps_timeline,
            "trial_duration": trial_end_time
        }

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
        has_mizuki = "Mizuki" in self.party or any(
            ev.get("dreamdrifter_state") == "ON" or
            ev.get("mizuki_a4_state") == "ON" or
            ev.get("vbtd_state") == "ON" or
            ev.get("c1_debuff_state") == "ON"
            for ev in self.global_events
        )

        # 1. Main category columns
        main_headers = ["Time (s)", "Active", "Owner", "Action", "Aura (Cryo)", "Reaction"]
        main_widths = [10, 8, 8, 36, 11, 24]

        # 2. Damage calcs category columns
        dmg_headers = ["non_crit", "crit_damage", "average_damage", "effective_average_damage"]
        dmg_widths = [12, 13, 16, 26]

        # 3. Buffs category columns
        buff_headers = []
        buff_widths = []
        if has_mizuki:
            buff_headers.extend(["DDS", "A4", "VBTD", "C1 Debuff"])
            buff_widths.extend([5, 5, 6, 11])
        if has_fanz:
            buff_headers.extend(["FanzBuff", "FanzDebuff"])
            buff_widths.extend([9, 12])
        if has_c2:
            buff_headers.append("AetherC2")
            buff_widths.append(9)
        buff_headers.append("Marvelous")
        buff_widths.append(10)
        if has_hotf:
            buff_headers.append("HotF")
            buff_widths.append(5)
        if has_dream:
            buff_headers.append("Dream")
            buff_widths.append(7)
        if has_vv:
            buff_headers.append("VV")
            buff_widths.append(5)
        if has_instructor:
            buff_headers.append("Instructor")
            buff_widths.append(10)
        if has_cryo_resonance:
            buff_headers.append("CryoResonance")
            buff_widths.append(13)

        # Spans for the 2-tier Category Header
        main_span = sum(main_widths) + 3 * (len(main_widths) - 1)
        dmg_span = sum(dmg_widths) + 3 * (len(dmg_widths) - 1)
        buff_span = sum(buff_widths) + 3 * (len(buff_widths) - 1) if buff_widths else 0

        # Construct Category Row
        categories = [
            f"{'Main':^{main_span}}",
            f"{'Damage calcs':^{dmg_span}}"
        ]
        if buff_widths:
            categories.append(f"{'Buffs':^{buff_span}}")
        category_str = " | ".join(categories)

        # Construct Column Header Row
        all_headers = main_headers + dmg_headers + buff_headers
        all_widths = main_widths + dmg_widths + buff_widths
        header_str = " | ".join(f"{h:<{w}}" for h, w in zip(all_headers, all_widths))

        # Print Headers and Separator
        print(category_str)
        print(header_str)
        print("-" * len(header_str))

        # Print Rows
        for event in self.global_events:
            nc_str = f"{event['non_crit']:.1f}" if event.get("non_crit") is not None else "-"
            cd_str = f"{event['crit_damage']:.1f}" if event.get("crit_damage") is not None else "-"
            avg_str = f"{event['average_damage']:.1f}" if event.get("average_damage") is not None else "-"
            eff_str = f"{event['effective_average_damage']:.1f}" if event.get("effective_average_damage") is not None else "-"

            row_data = [
                f"{event['global_time']:.3f}",
                str(event.get("active_character", "None")),
                str(event.get("character", "")),
                str(event.get("action", "")),
                str(event.get("cryo_aura", "-")),
                str(event.get("reaction", "-")),
                nc_str,
                cd_str,
                avg_str,
                eff_str,
            ]
            if has_mizuki:
                row_data.extend([
                    event.get("dreamdrifter_state", "OFF"),
                    event.get("mizuki_a4_state", "OFF"),
                    event.get("vbtd_state", "OFF"),
                    event.get("c1_debuff_state", "OFF"),
                ])
            if has_fanz:
                row_data.extend([event.get("faruzan_buff_state", "OFF"), event.get("faruzan_debuff_state", "OFF")])
            if has_c2:
                row_data.append(event.get("aether_c2_state", "OFF"))
            row_data.append(str(event.get("marvelous_stacks", 0)))
            if has_hotf:
                row_data.append(event.get("hotf_state", "OFF"))
            if has_dream:
                row_data.append(event.get("dreamdrifter_state", "OFF"))
            if has_vv:
                row_data.append(event.get("vv_state", "OFF"))
            if has_instructor:
                row_data.append(event.get("instructor_state", "OFF"))
            if has_cryo_resonance:
                row_data.append(event.get("cryo_resonance_state", "OFF"))

            row_str = " | ".join(f"{val:<{w}}" for val, w in zip(row_data, all_widths))
            print(row_str)

