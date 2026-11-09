import copy
from typing import Dict, List, Optional, Tuple

from models import ActionCategory, FieldSequence, AttackType, StatRef, Rotation, Trial
from aura import CryoAuraTracker
from mechanics import StellarVortex, stellar_swirl_hit
from abilities import (
    mizuki_nuke_hit,
    mizuki_c1_mini_nuke_hit,
    aether_burst_enhanced,
    aether_burst_standard,
    odette_recast_c1,
    anastasya_extra_stellar,
    anastasya_triumph,
    sucrose_burst,
    update_ability_talent_level,
    configure_field_sequence_talents,
    get_ability_motion_value,
)
from damage_calc import calculate_damage, DEFAULT_ENEMY_STATS
from stats_calc import (
    build_initial_stats, apply_permanent_buffs, apply_weapon_party_stats,
    build_snapshot_stats, compute_final_stats, is_rv_mode,
)
from weapons import resolve_weapon_key
from characters import party_element_counts


# ---------------------------------------------------------------------------
# Buff windows derived from ability hit timelines
# ---------------------------------------------------------------------------
# A buff that lasts "while the ability's field is up" should span exactly one
# cast: from the first hit to the LAST hit of that ability. Deriving the length
# from the ability definition keeps the window in sync if hit timings change.
# Sucrose C6 (party cryo_bonus) is the first user of this pattern:
#   burst hits at +0.000 / +1.889 / +3.869 / +5.729  ->  window = 5.729 s
SUCROSE_BURST_WINDOW = max(hit.relative_delay for hit in sucrose_burst.hits)

# Float tolerance for "is this event still inside the window" checks, so the
# hit that lands exactly on the closing edge is never lost to rounding.
_WINDOW_EPS = 1e-9


# Anastasya "Triumph": armed by her burst cast and fired by her NEXT swap-in (once
# per cast). The delay is the minimum time that must pass between the cast and that
# swap-in.
#   PROVISIONAL: 0.0 while the real rule is still unknown (unreleased content).
#   With the current rotations this makes it proc on every loop from the 2nd one
#   onwards. Raise it (18.0 was the earlier guess) once the kit rule is confirmed.
ANASTASYA_TRIUMPH_DELAY = 0.0


# ==========================================
# 5. TIMELINE ENGINE & EVALUATOR
# ==========================================

class RotationTimeline:
    def __init__(self, party: Optional[Dict[str, dict]] = None, enemy_stats: Optional[Dict[str, float]] = None):
        self.global_events = []
        self.last_used_timestamps: Dict[Tuple[str, str], float] = {}
        self.enemy_stats = enemy_stats if enemy_stats is not None else DEFAULT_ENEMY_STATS.copy()
        self._timeline_evaluated = False
        self._burst_call_seq = 0

        # Normalize party structure: ensure every entry has dict metadata and
        # that both "artifact" / "artifact_set" keys resolve to the same name
        # (some call paths / UIs use one or the other).
        self.party: Dict[str, dict] = {}
        if party:
            for char, data in party.items():
                if isinstance(data, int):  # Backward compatibility if someone passes just an int constellation
                    self.party[char] = {"constellation": data, "weapon": None, "artifact": None, "artifact_set": None}
                else:
                    d = dict(data)
                    artifact = d.get("artifact") or d.get("artifact_set")
                    d["artifact"] = artifact
                    d["artifact_set"] = artifact
                    self.party[char] = d

        self._prepare_character_stats()

    def _prepare_character_stats(self):
        self.char_initial_stats_map = {}
        for char_name, data in self.party.items():
            char_level = data.get("level")
            weapon = data.get("weapon")
            artifact = data.get("artifact")
            main_stats = data.get("main_stats_total", {})
            subs = data.get("subs_total", {})
            pre = data.get("initial_stats")
            if isinstance(pre, dict) and pre:
                # Reuse precomputed (UI / saved-config) stats instead of rebuilding,
                # so artifact mains/subs/set passives are not silently dropped.
                init_s = dict(pre)
            else:
                init_s = build_initial_stats(
                    char_name, char_level, weapon, artifact, main_stats, subs,
                    refinement=data.get("refinement", 1),
                )
            init_s = apply_permanent_buffs(init_s, char_name)
            self.char_initial_stats_map[char_name] = init_s

        # Permanent, party-composition-dependent weapon stats (e.g. A Thousand
        # Floating Dreams). Idempotent, so it is safe even when the UI already
        # applied them to its precomputed stats.
        apply_weapon_party_stats(self.char_initial_stats_map, self.party)

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
            # Odette C1+: her Recast is a distinct ability (adds Skill_Stellar_c1),
            # chosen build-time by her constellation – mirroring the Aether burst split.
            c_ability = call.ability
            if (field_sequence.character == "Odette" and c_ability.name == "Skill Recast"
                    and self.party.get("Odette", {}).get("constellation", 0) >= 1):
                c_ability = copy.deepcopy(odette_recast_c1)
                od_tal = self.party.get("Odette", {}).get("talents", "10/10/10")
                if isinstance(od_tal, str):
                    _p = od_tal.split("/")
                    skill_lvl = int(_p[1]) if len(_p) > 1 else 10
                elif isinstance(od_tal, (list, tuple)) and len(od_tal) > 1:
                    skill_lvl = int(od_tal[1])
                else:
                    skill_lvl = 10
                update_ability_talent_level(c_ability, skill_lvl)

            ability_start_global = swap_in_time + call.start_time
            ability_key = (field_sequence.character, c_ability.name)

            if c_ability.cooldown > 0 and ability_key in self.last_used_timestamps:
                last_time = self.last_used_timestamps[ability_key]
                cd_expires_at = last_time + c_ability.cooldown
                if ability_start_global < cd_expires_at:
                    raise ValueError(f"[COOLDOWN ERROR] {field_sequence.character}'\''s {c_ability.name} on CD until {cd_expires_at:.3f}s")

            if c_ability.cooldown > 0:
                self.last_used_timestamps[ability_key] = ability_start_global

            self.global_events = [
                ev for ev in self.global_events
                if not (ev.get("event_type") == "HIT" and
                        ev.get("character") == field_sequence.character and
                        ev.get("ability_name") == c_ability.name and
                        ev["global_time"] >= ability_start_global)
            ]

            # Aether's Burst comes in two variants (enhanced vs standard) chosen at
            # cast time based on Frostglow stacks. Tag the scheduled hits so the
            # evaluator can substitute the correct variant and consume Frostglow.
            is_aether_burst = (field_sequence.character == "Aether" and c_ability.name == "Elemental Burst")
            if is_aether_burst:
                self._burst_call_seq += 1
            burst_call_id = self._burst_call_seq if is_aether_burst else None

            for hit in c_ability.hits:
                hit_global_time = ability_start_global + hit.relative_delay
                ev = {
                    "global_time": hit_global_time,
                    "character": field_sequence.character,
                    "action": f"{c_ability.name} ({hit.name})",
                    "category": hit.category,
                    "elem_app": hit.elemental_app if hit.elemental_app else "-",
                    "element": hit.element,
                    "event_type": "HIT",
                    "hit_name": hit.name,
                    "ability_name": c_ability.name,
                    "stat_ref": hit.stat_ref,
                    "multiplier": hit.multiplier,
                    "attack_type": hit.attack_type,
                    # Offset of this hit inside its own ability cast. Lets the
                    # evaluator back-derive the cast time of any hit (used by
                    # ability-wide buff windows such as Sucrose's C6).
                    "hit_offset": hit.relative_delay,
                }
                if is_aether_burst:
                    ev["burst_variant"] = "auto"
                    ev["burst_call_id"] = burst_call_id
                self.global_events.append(ev)

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

    def _weapon_holder(self, weapon_name: str) -> Optional[str]:
        """Name of the party member equipping *weapon_name* (None if unequipped).

        Weapon names can contain parentheses ("The Widsith (Average)") while UI
        labels may add a refinement suffix, so both sides go through
        resolve_weapon_key() before comparing.
        """
        target = resolve_weapon_key(weapon_name)
        return next((c for c, d in self.party.items()
                     if resolve_weapon_key(d.get("weapon")) == target), None)

    def _artifact_holder(self, set_name: str) -> Optional[str]:
        """Name of the party member wearing *set_name* (None if unequipped)."""
        return next((c for c, d in self.party.items()
                     if (d.get("artifact_set") or d.get("artifact")) == set_name), None)

    def evaluate_timeline(self):
        # Idempotence guard: this pass mutates the event list (inserts swirls,
        # nukes, vortex explosions, burst substitution). Re-running it would
        # duplicate events, so skip if we already evaluated.
        if self._timeline_evaluated:
            return

        active_character = "None"
        aether_c2_active = False
        marvelous_active = False
        marvelous_activation_time = 0.0
        odette_swap_time: Optional[float] = None
        odette_burst_expiration: Optional[float] = None      # self stellar_bonus buff (6s)
        odette_c2_shred_expiration: Optional[float] = None   # party cryo/anemo shred (20s)
        # Anastasya trackers
        anastasya_burst_expiration: Optional[float] = None   # party stellar_bonus + extra stellar beats (20s)
        anastasya_a1_expiration: Optional[float] = None      # others crit_dmg (19s)
        anastasya_triumph_ready_at: Optional[float] = None   # earliest swap-in that fires Triumph
        anastasya_triumph_armed: bool = False                # one Triumph per burst cast
        # Sucrose State Trackers
        sucrose_a1_expiration: Optional[float] = None  # +50 EM (non-anemo) after her swirl (8s)
        sucrose_a4_expiration: Optional[float] = None  # 20% flat-EM share to others (8s)
        sucrose_c6_expiration: Optional[float] = None  # party cryo_bonus for one burst cast
        hotf_expiration_time: Optional[float] = None
        vv_expiration_time: Optional[float] = None
        instructor_expiration_time: Optional[float] = None
        # Weapon-proc trackers (persist across the evaluate loop).
        exaiphanes_atk_expiration: Optional[float] = None
        exaiphanes_atk_proc_cd: float = -1.0
        silver_light_stack_expiries: List[float] = []

        # --- DYNAMIC GEAR RESOLUTION ---
        # Find which character has "Heart of the Furnace" equipped as their weapon or artifact
        hotf_holder = next(
            (char for char, data in self.party.items()
            if (data.get("weapon") or "").lower() == "heart of the furnace"
            or (data.get("artifact") or "").lower() == "heart of the furnace"),
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

        # Aether State Trackers (Frostglow / C2 / C6)
        aether_frostglow = 0
        aether_c2_basic_holder: Optional[str] = None
        aether_c2_enhanced_holder: Optional[str] = None
        aether_c6_expiration: Optional[float] = None
        aether_c6_stacks = 0

        # Faruzan State Trackers
        faruzan_buff_expiration: Optional[float] = None
        faruzan_debuff_expiration: Optional[float] = None
        faruzan_collapse_cd_expires: float = -1.0

        # Weapon State Trackers (all holder-only; None when not equipped)
        widsith_holder = (self._weapon_holder("The Widsith (Average)")
                          or self._weapon_holder("The Widsith (All EM)"))
        widsith_expiration: Optional[float] = None
        widsith_proc_cd: float = -1.0
        jade_holder = self._weapon_holder("Sacrificial Jade")
        jade_active = True            # the passive starts active on the wielder
        jade_state_since: float = 0.0
        jade_was_active = False
        sunny_holder = self._weapon_holder("Sunny Morning Sleep-In")
        sunny_swirl_expiration: Optional[float] = None
        sunny_skill_expiration: Optional[float] = None
        sunny_burst_expiration: Optional[float] = None
        evenstar_holder = self._weapon_holder("Wandering Evenstar")
        ttds_holder = self._weapon_holder("Thrilling Tales of Dragon Slayers")
        ttds_target: Optional[str] = None
        ttds_expiration: Optional[float] = None
        ttds_pending = False
        ttds_cd_ready: float = -1.0
        starsealed_holder = self._weapon_holder("Starsealed Edict")
        starsealed_expiration: Optional[float] = None
        starsealed_stacks = 0
        whitlake_holder = self._weapon_holder("Whitelake Frostfeather")
        whitlake_stack_expiries: List[float] = []
        whitlake_gain_cd_ready: float = -1.0
        finale_holder = self._weapon_holder("Finale Of The Deep")
        finale_expiration: Optional[float] = None
        finale_cd_ready: float = -1.0
        breezeborne_holder = self._weapon_holder("Breezeborne Refrain")
        breezeborne_sigils = 0
        breezeborne_gain_cd_ready: float = -1.0
        breezeborne_expiration: Optional[float] = None
        elegy_holder = self._weapon_holder("Elegy for the End")
        elegy_sigils = 0
        elegy_gain_cd_ready: float = -1.0
        elegy_expiration: Optional[float] = None
        elegy_lockout_until: float = -1.0
        newbough_holder = self._weapon_holder("New Bough")
        newbough_stacks = 0
        newbough_expiration: Optional[float] = None
        newbough_last_gain: float = -1.0
        silverdawn_holder = self._weapon_holder("Silverdawn")
        silverdawn_expiration: Optional[float] = None
        silverdawn_extensions = 0
        silverdawn_ext_cd_ready: float = -1.0
        # Artifact set trackers (phase 1)
        gilded_holder = self._artifact_holder("Gilded Dreams")
        gilded_expiration: Optional[float] = None
        gilded_cd_ready: float = -1.0
        noblesse_holder = self._artifact_holder("Noblesse Oblige")
        noblesse_expiration: Optional[float] = None
        tenacity_holder = self._artifact_holder("Tenacity Of The Millelith")
        tenacity_expiration: Optional[float] = None
        tenacity_cd_ready: float = -1.0
        risingwinds_holder = self._artifact_holder("A Day Carved From Rising Winds")
        risingwinds_expiration: Optional[float] = None
        scarlet_holder = self._artifact_holder("Scarlet Proof")
        scarlet_expiration: Optional[float] = None
        tsaritsa_holder = self._artifact_holder("New Tsaritsa set")
        tsaritsa_stacks = 0
        tsaritsa_active_accum = 0.0
        tsaritsa_last_t: Optional[float] = None

        aura_tracker = CryoAuraTracker()
        active_vortex: Optional[StellarVortex] = None

        # Cryo Resonance only exists with 2+ Cryo characters in the party.
        cryo_resonance_enabled = party_element_counts(self.party).get("Cryo", 0) >= 2

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

            # 0. Aether Burst resolution: at cast time pick the variant by Frostglow
            #    stacks (enhanced at 8, standard otherwise), consume the stacks, and
            #    substitute the scheduled hits. Works on both scheduled variants.
            if (e_type == "HIT" and char == "Aether" and ability_name == "Elemental Burst"
                    and event.get("burst_variant") == "auto"):
                burst_call_id = event.get("burst_call_id")
                consumed = aether_frostglow
                aether_frostglow = 0
                variant = aether_burst_enhanced if consumed >= 8 else aether_burst_standard
                variant_name = "Enhanced" if consumed >= 8 else "Standard"

                # Aether's Burst talent = index 2 of the N/S/B talent config.
                aether_data = self.party.get("Aether", {})
                b_tal = aether_data.get("talents", "1/13/13")
                if isinstance(b_tal, str):
                    parts = b_tal.split("/")
                    b_lvl = int(parts[2]) if len(parts) > 2 else 13
                elif isinstance(b_tal, (list, tuple)) and len(b_tal) > 2:
                    b_lvl = int(b_tal[2])
                else:
                    b_lvl = 13

                mv = get_ability_motion_value("Aether", "Burst (Stellar Swirl)",
                                              "Ice Javelin Single Strike DMG", b_lvl, stacks=consumed)

                # Drop any LATER pre-scheduled hits of THIS burst call (they will be
                # replaced below with the chosen variant's ticks).
                if burst_call_id is not None:
                    self.global_events = [
                        ev for ev in self.global_events
                        if not (ev.get("burst_call_id") == burst_call_id and ev.get("global_time") > t)
                    ]
                    event = self.global_events[i]

                # Rewrite the first tick in place, then insert the remaining ticks
                # of the chosen variant right after it so they evaluate in order.
                offset = 1
                for h in variant.hits:
                    if h.relative_delay == 0.0:
                        event["action"] = f"{h.name}"
                        event["hit_name"] = h.name
                        event["elem_app"] = h.elemental_app if h.elemental_app else "-"
                        event["element"] = h.element
                        event["stat_ref"] = h.stat_ref
                        event["attack_type"] = h.attack_type
                        event["multiplier"] = mv
                        event["burst_variant"] = variant_name
                        event["frostglow_consumed"] = consumed
                    else:
                        sub = {
                            "global_time": t + h.relative_delay,
                            "character": "Aether",
                            "action": f"{h.name}",
                            "category": h.category,
                            "elem_app": h.elemental_app if h.elemental_app else "-",
                            "element": h.element,
                            "event_type": "HIT",
                            "hit_name": h.name,
                            "ability_name": "Elemental Burst",
                            "stat_ref": h.stat_ref,
                            "multiplier": mv,
                            "attack_type": h.attack_type,
                            "burst_variant": variant_name,
                            "burst_call_id": burst_call_id,
                            "frostglow_consumed": consumed,
                        }
                        self.global_events.insert(i + offset, sub)
                        offset += 1

                # Aether C6: Burst consuming Frostglow opens a 15s window where the
                # whole party gains 5% stellar_bonus per consumed stack.
                if aether_data.get("constellation", 0) >= 6:
                    aether_c6_expiration = t + 15.0
                    aether_c6_stacks = consumed
                    event["aether_c6_consumed_on"] = t

            # ---- Frostglow gain: every Aether skill TICK grants one stack (max 8).
            #      The initial cast (Skill_Initial) does NOT grant a stack. ----
            if (e_type == "HIT" and char == "Aether" and ability_name == "Elemental Skill"
                    and hit_name != "Skill_Initial"):
                aether_frostglow = min(8, aether_frostglow + 1)

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
                # Aether C2 is bound to the ACTIVE character: when they swap out,
                # both C2 Basic and Enhanced expire for them.
                if aether_c2_basic_holder == char:
                    aether_c2_basic_holder = None
                    aether_c2_enhanced_holder = None
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

                # A4 / C1 windows are read BEFORE this event arms them, so the hit that
                # refreshes A4 or applies the C1 shred does not gain their stats.
                mizuki_a4_active = mizuki_dreamdrifter_active and (t <= mizuki_a4_expiration)
                c1_debuff_active = mizuki_c1_unlocked and (t <= mizuki_c1_debuff_expiration)

                if char == "Mizuki":
                    # C1 Debuff Application on every skill hit during DDS
                    if mizuki_c1_unlocked and e_type == "HIT" and is_mizuki_skill and mizuki_dreamdrifter_active:
                        if t >= mizuki_c1_app_cooldown_expires:
                            mizuki_c1_debuff_expiration = t + 3.0
                            mizuki_c1_app_cooldown_expires = t + 3.5

                # A4 Refresh Logic: Triggers on Cryo elemental hit during DDS (no gauge check required)
                if mizuki_dreamdrifter_active and element == "Cryo" and e_type == "HIT":
                    mizuki_a4_expiration = t + 4.0

                # VBTD Quill Assignment & Nuke Firing on Subsequent Skill Ticks
                vbtd_quill_active = False
                if char == "Mizuki" and is_mizuki_skill and hit_name.startswith("Tick"):
                    if mizuki_dreamdrifter_active and mizuki_nuke_armed and t > mizuki_nuke_armed_time:
                        vbtd_quill_active = True
                        fire_vbtd_nuke = True
                        mizuki_em = self.char_initial_stats_map.get("Mizuki", {}).get("em", 0.0)
                        # Nuke base scales on Mizuki's EFFECTIVE DDS EM (initial * VBTD2 self-share).
                        event["quill_damage"] = mizuki_em * 10.0 * 1.10
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

                # Faruzan's BASE ATK (character + weapon base, ignoring atk% / flat).
                faruzan_base_atk = self.char_initial_stats_map.get("Faruzan", {}).get("base_atk", 0.0)

                # Resolve the DEBUFF state from the PRIOR expiration (before this event's
                # own refresh), so the applying hit never benefits from the shred it spawned.
                faruzan_debuff_active = (faruzan_debuff_expiration is not None) and (t <= faruzan_debuff_expiration)
                # Same for her buff window: her own burst cast arms it, so it is read
                # from the pre-event expiration (the cast's damage comes first).
                faruzan_buff_active = (faruzan_buff_expiration is not None) and (t <= faruzan_buff_expiration)

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
                    # Debuff "bigger number wins": burst opens the full 22s window.
                    old_debuff = faruzan_debuff_expiration if faruzan_debuff_expiration is not None else 0.0
                    faruzan_debuff_expiration = max(old_debuff, t + 22.0)
                    collapse_time = t + 0.720  # standard delay for pressurized collapse
                    faruzan_collapse_cd_expires = collapse_time + 3.0

                    self.global_events.insert(i + 1, create_collapse_event(collapse_time))

                # Pressurized Collapse refreshes the debuff by 4s, but never overrides
                # a longer 22s window already in effect (bigger number priority).
                if e_type == "HIT" and hit_name == "Pressurized_Collapse":
                    old_debuff = faruzan_debuff_expiration if faruzan_debuff_expiration is not None else 0.0
                    faruzan_debuff_expiration = max(old_debuff, t + 4.0)

                # 2. Insertion upon Passive Trigger during Buff Window
                if faruzan_buff_active and e_type == "HIT" and hit_name != "Pressurized_Collapse":
                    if t >= faruzan_collapse_cd_expires:
                        collapse_time = t + 0.720
                        faruzan_collapse_cd_expires = collapse_time + 3.0
                        self.global_events.insert(i + 1, create_collapse_event(collapse_time))

                # 3. Faruzan Quill: 32% of her BASE_ATK added to any ANEMO + STANDARD hit
                #    from a buffed character (base = character+weapon, ignores atk% / flat).
                if (e_type == "HIT" and faruzan_buff_active and element == "Anemo"
                        and cat == ActionCategory.STANDARD_DMG and char == active_character):
                    faruzan_quill = 0.32 * faruzan_base_atk
                    event["quill_damage"] = event.get("quill_damage", 0.0) + faruzan_quill

                # Buff stat effects (crit_dmg / anemo_bonus) apply only to ANEMO hits,
                # so the buff state is shown as ON for Anemo-element events only.
                event["faruzan_buff_state"] = "ON" if (faruzan_buff_active and element == "Anemo" and char == active_character) else "OFF"
                # Window-only flag: gates Faruzan's buff PER-CONTRIBUTOR in swirl reactions
                # (the buff only reaches the ACTIVE character).
                event["faruzan_buff_window"] = "ON" if faruzan_buff_active else "OFF"
                event["faruzan_debuff_state"] = "ON" if faruzan_debuff_active else "OFF"
            else:
                event["faruzan_buff_state"] = "OFF"
                event["faruzan_debuff_state"] = "OFF"

            # 4. Elemental Aura & Reaction Processing
            reaction = None
            is_stellar_swirl = False

            # Windows granted BY this event are read from their PRE-event state, so the
            # triggering hit never benefits from the effect it just procced (the game
            # resolves damage before anything the hit applies). Same rule as HotF.
            vv_active = (vv_expiration_time is not None) and (t <= vv_expiration_time)
            instructor_active = (instructor_expiration_time is not None) and (t <= instructor_expiration_time)
            # Aura the event is RESOLVED AGAINST: the gauge as it stands before this
            # event applies anything (non-damage rows simply keep the current gauge).
            aura_before_u = aura_tracker.current_gauge
            cryo_aura_present = aura_before_u > 0.0

            if e_type == "HIT":
                gauge_u = self._parse_gauge(elem_app)
                # Cryo Resonance requires the enemy to ALREADY be Cryo-affected, so read
                # the gauge after decay is advanced to this timestamp but BEFORE this
                # hit's own elemental application (a hit cannot benefit from the aura
                # it creates).
                aura_tracker.advance_time(t)
                aura_before_u = aura_tracker.current_gauge
                cryo_aura_present = aura_before_u > 0.0
                reaction, is_stellar_swirl, swirl_meta = aura_tracker.apply_element(element, gauge_u, char, t)

                # VV Shred trigger
                # VV only procs when the holder is ON THE FIELD and triggers the swirl.
                if is_stellar_swirl and vv_holder and char == vv_holder and active_character == char:
                    vv_expiration_time = t + 10.0

                # Instructor trigger: the holder must be ON FIELD and trigger the
                # swirl themselves; subsequent triggers refresh the 8s timer.
                if (is_stellar_swirl and instructor_holder and char == instructor_holder
                        and active_character == char):
                    instructor_expiration_time = t + 8.0

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
                        "faruzan_buff_state": event.get("faruzan_buff_state", "OFF"),
                        "faruzan_buff_window": event.get("faruzan_buff_window", "OFF"),
                        "faruzan_debuff_state": event.get("faruzan_debuff_state", "OFF"),
                        "aether_c2_state": event.get("aether_c2_state", "OFF"),
                        "marvelous_stacks": event.get("marvelous_stacks", 0),
                        "hotf_state": event.get("hotf_state", "OFF"),                        
                    }
                    self.global_events.insert(i + 1, swirl_hit_event)

                    if current_c1_active:
                        # C1 quill = 550% of Mizuki's EM at the swirl moment; its base is
                        # computed in the reaction calc from Mizuki's event-time stats.
                        swirl_hit_event["c1_quill"] = True

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
                            "faruzan_buff_state": event.get("faruzan_buff_state", "OFF"),
                        "faruzan_buff_window": event.get("faruzan_buff_window", "OFF"),
                            "faruzan_debuff_state": event.get("faruzan_debuff_state", "OFF"),
                            "aether_c2_state": event.get("aether_c2_state", "OFF"),
                            "marvelous_stacks": event.get("marvelous_stacks", 0),
                            "hotf_state": event.get("hotf_state", "OFF")
                        }
                        self.global_events.insert(i + 2, mini_nuke_event)

                    if active_vortex is None or not active_vortex.is_active:
                        # Anastasya A4: vortices spawn already at level 2 and only
                        # need 3 further stellar swirls to detonate early.
                        if "Anastasya" in self.party:
                            active_vortex = StellarVortex(swirl_meta, t, start_level=2,
                                                          detonation_swirls=4)
                        else:
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
                                "faruzan_buff_state": event.get("faruzan_buff_state", "OFF"),
                                "faruzan_buff_window": event.get("faruzan_buff_window", "OFF"),
                                "faruzan_debuff_state": event.get("faruzan_debuff_state", "OFF"),
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
                    "faruzan_buff_state": event.get("faruzan_buff_state", "OFF"),
                    "faruzan_debuff_state": event.get("faruzan_debuff_state", "OFF"),
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

            # The Aura column reports the state this event was resolved against (before
            # its own elemental application), so it only changes on the NEXT row after
            # the hit that applied the element - and it always agrees with
            # cryo_resonance_state. The post-hit gauge is kept for debugging.
            event["cryo_aura"] = f"{aura_before_u:.2f}U"
            event["cryo_aura_after"] = f"{aura_tracker.current_gauge:.2f}U"
            event["reaction"] = reaction if reaction else "-"

            event["vv_state"] = "ON" if vv_active else "OFF"

            event["instructor_state"] = "ON" if instructor_active else "OFF"

            # Cryo Resonance needs BOTH a Cryo-affected enemy AND 2+ Cryo characters.
            # The aura is the PRE-application one (see 4.): the hit that applies Cryo
            # from a clean enemy does not get the 15% CR.
            cryo_resonance_active = cryo_resonance_enabled and cryo_aura_present
            event["cryo_resonance_state"] = "ON" if cryo_resonance_active else "OFF"

            # 6. Aether C2, C6 & Frostglow audit columns.
            aether_data = self.party.get("Aether", {})
            aether_c2_ok = aether_data.get("constellation", 0) >= 2

            # C2 Enhanced state is resolved from the PRE-arm value, so the applying hit does
            # NOT benefit from a C2E it just triggered (the game deals damage first).
            c2_enh_on = (aether_c2_ok
                         and aether_c2_basic_holder is not None
                         and aether_c2_basic_holder == active_character
                         and aether_c2_enhanced_holder == active_character)

            if aether_c2_ok:
                # C2 Basic arms for the ACTIVE character on a skill TICK (not the cast).
                if e_type == "HIT" and char == "Aether" and ability_name == "Elemental Skill" and hit_name != "Skill_Initial":
                    if active_character not in (None, "None"):
                        aether_c2_basic_holder = active_character

                # C2 Enhanced: Basic is on AND the active (holder) character deals
                # Stellar DMG or triggers a swirl.
                if aether_c2_basic_holder and aether_c2_basic_holder == active_character:
                    if (e_type == "HIT" and cat == ActionCategory.STELLAR_DMG) or is_stellar_swirl:
                        aether_c2_enhanced_holder = aether_c2_basic_holder

            # Audit columns (always populated so the table stays column-stable).
            c2_basic_on = (aether_c2_ok
                           and aether_c2_basic_holder is not None
                           and aether_c2_basic_holder == active_character)
            event["aether_c2_state"] = "ON" if c2_basic_on else "OFF"
            event["aether_c2_enhanced_state"] = "ON" if c2_enh_on else "OFF"

            # Frostglow + Aether C6 (15s window) audit columns.
            c6_on = (aether_data.get("constellation", 0) >= 6
                     and aether_c6_expiration is not None and t <= aether_c6_expiration)
            # On burst events show the number of stacks that were consumed (pre-reset);
            # otherwise the current stack count.
            event["frostglow_stacks"] = event.get("frostglow_consumed", aether_frostglow)
            event["aether_c6_state"] = "ON" if c6_on else "OFF"
            event["aether_c6_stacks"] = aether_c6_stacks if c6_on else 0

            # 6b. Sucrose buff windows: A4 (skill/burst hit), C6 (burst), A1 (swirl).
            if "Sucrose" in self.party:
                # Read the windows BEFORE arming them: the hit/cast that triggers one
                # of her passives does not gain that passive (damage resolves first).
                # _WINDOW_EPS keeps the hit that lands exactly on the closing edge
                # inside the window (float addition is not associative).
                a1_on = sucrose_a1_expiration is not None and t <= sucrose_a1_expiration + _WINDOW_EPS
                a4_on = sucrose_a4_expiration is not None and t <= sucrose_a4_expiration + _WINDOW_EPS
                c6_on = sucrose_c6_expiration is not None and t <= sucrose_c6_expiration + _WINDOW_EPS

                if e_type == "HIT" and char == "Sucrose" and ability_name in ("Sucrose Skill", "Sucrose Burst"):
                    sucrose_a4_expiration = t + 8.0

                # C6: the party cryo_bonus field exists for exactly one burst cast.
                # Arm it ONCE at the cast (hit offset 0) and end it with the LAST
                # burst hit (SUCROSE_BURST_WINDOW), so re-hitting never extends it
                # past the field's lifetime. Verified window: [cast, cast + 5.729].
                if (e_type == "HIT" and char == "Sucrose" and ability_name == "Sucrose Burst"
                        and self.party.get("Sucrose", {}).get("constellation", 0) >= 6
                        and event.get("hit_offset", 0.0) == 0.0):
                    sucrose_c6_expiration = t + SUCROSE_BURST_WINDOW

                # A1 only procs when Sucrose HERSELF triggers a swirl (like Mizuki's
                # nuke preparation), refreshing the 8s non-Anemo EM buff.
                if char == "Sucrose" and is_stellar_swirl:
                    sucrose_a1_expiration = t + 8.0

                event["sucrose_a1_state"] = "ON" if a1_on else "OFF"
                event["sucrose_a4_state"] = "ON" if a4_on else "OFF"
                event["sucrose_c6_state"] = "ON" if c6_on else "OFF"
            else:
                event["sucrose_a1_state"] = "OFF"
                event["sucrose_a4_state"] = "OFF"
                event["sucrose_c6_state"] = "OFF"

            # 6c. Weapon passives (holder-only): Exaiphanes Blade ATK proc + Silver Light stacks.
            #      Exaiphanes: the holder's HITS grant +40% ATK for 8s, internal 5s CD.
            exaiphanes_holder = self._weapon_holder("Exaiphanes Blade")
            # "after every hit": the flag reflects a buff already active BEFORE this
            # hit proc, so the triggering hit itself does NOT get the +40% ATK.
            exaiphanes_on = (exaiphanes_atk_expiration is not None
                             and t < exaiphanes_atk_expiration and exaiphanes_holder is not None)
            event["exaiphanes_blade_state"] = "ON" if exaiphanes_on else "OFF"
            if (e_type == "HIT" and exaiphanes_holder == char
                    and t >= exaiphanes_atk_proc_cd):
                exaiphanes_atk_expiration = t + 8.0
                exaiphanes_atk_proc_cd = t + 5.0

            #      Silver Light: the holder gains +1 stack per skill cast (and Odette
            #      recast), each stack expiring after 12s.
            silver_holder = self._weapon_holder("Silver Light")
            # One stack per cast action (the cast / first recast hit), not per damage tick.
            if (silver_holder == char and e_type == "HIT"
                    and ((ability_name == "Skill Cast" and hit_name == "Cast")
                         or (ability_name == "Skill Recast" and hit_name == "Skill_Recast1")
                         or (ability_name == "Elemental Skill" and hit_name == "Skill_Initial"))):
                silver_light_stack_expiries.append(t + 12.0)
            if silver_holder is not None:
                silver_light_stack_expiries = [x for x in silver_light_stack_expiries if x > t]
                event["silver_light_stacks"] = len(silver_light_stack_expiries)
            else:
                event["silver_light_stacks"] = 0

            #      The Widsith: taking the field grants the roll buff for 10s, with a
            #      30s cooldown measured from the trigger, so re-entering early does
            #      not refresh it. "Average" applies one third of all three outcomes
            #      at once; "All EM" applies the full EM roll only.
            if widsith_holder is not None:
                # Taking the field arms it, so the SWAP_IN row itself shows the
                # pre-arm state (the buff applies to what comes after).
                widsith_on = (widsith_expiration is not None
                              and t <= widsith_expiration + _WINDOW_EPS)
                if e_type == "SWAP_IN" and char == widsith_holder and t >= widsith_proc_cd:
                    widsith_expiration = t + 10.0
                    widsith_proc_cd = t + 30.0
                event["widsith_state"] = "ON" if widsith_on else "OFF"
            else:
                event["widsith_state"] = "OFF"

            #      Sacrificial Jade: the passive is up while the wielder is off the
            #      field. >10s of CONTINUOUS on-field time removes it, and >=5s of
            #      continuous off-field time brings it back. It starts active.
            if jade_holder is not None:
                holder_active = (active_character == jade_holder)
                if holder_active != jade_was_active:
                    jade_was_active = holder_active
                    jade_state_since = t
                if holder_active and jade_active and (t - jade_state_since) > 10.0 + _WINDOW_EPS:
                    jade_active = False
                elif (not holder_active) and (not jade_active) and \
                        (t - jade_state_since) >= 5.0 - _WINDOW_EPS:
                    jade_active = True
                event["sacrificial_jade_state"] = "ON" if jade_active else "OFF"
            else:
                event["sacrificial_jade_state"] = "OFF"

            #      Sunny Morning Sleep-In: three independent self windows.
            #      swirl <- the holder is the anemo contributor of a stellar swirl
            #      skill <- a STANDARD hit whose attack type is Skill
            #      burst <- a STANDARD hit whose attack type is Burst
            if sunny_holder is not None:
                attack_type = event.get("attack_type")
                is_standard = (cat == ActionCategory.STANDARD_DMG)
                # Read the three windows BEFORE arming them (same rule as everything else).
                sunny_swirl_on = (sunny_swirl_expiration is not None
                                  and t <= sunny_swirl_expiration + _WINDOW_EPS)
                sunny_skill_on = (sunny_skill_expiration is not None
                                  and t <= sunny_skill_expiration + _WINDOW_EPS)
                sunny_burst_on = (sunny_burst_expiration is not None
                                  and t <= sunny_burst_expiration + _WINDOW_EPS)
                if e_type == "HIT" and char == sunny_holder and is_stellar_swirl:
                    sunny_swirl_expiration = t + 6.0
                if (e_type == "HIT" and char == sunny_holder and is_standard
                        and attack_type == AttackType.SKILL):
                    sunny_skill_expiration = t + 9.0
                if (e_type == "HIT" and char == sunny_holder and is_standard
                        and attack_type == AttackType.BURST):
                    sunny_burst_expiration = t + 30.0
                event["sunny_swirl_state"] = "ON" if sunny_swirl_on else "OFF"
                event["sunny_skill_state"] = "ON" if sunny_skill_on else "OFF"
                event["sunny_burst_state"] = "ON" if sunny_burst_on else "OFF"
            else:
                event["sunny_swirl_state"] = "OFF"
                event["sunny_skill_state"] = "OFF"
                event["sunny_burst_state"] = "OFF"

            #      Wandering Evenstar: a 12s buff every 10s from the trial start, so
            #      the holder always has a 2s overlap with two active instances.
            #      The stack count is a closed form of t (no trigger events needed).
            if evenstar_holder is not None:
                last_start = int(t // 10.0)
                first_start = max(0, int((t - 12.0) // 10.0) + 1)
                event["evenstar_stacks"] = max(0, last_start - first_start + 1)
            else:
                event["evenstar_stacks"] = 0

            #      Thrilling Tales: the holder's swap-out arms the buff for the NEXT
            #      character to take the field (10s, 20s cooldown from the trigger).
            if ttds_holder is not None:
                if e_type == "SWAP_OUT" and char == ttds_holder and t >= ttds_cd_ready:
                    ttds_pending = True
                    ttds_cd_ready = t + 20.0
                if ttds_pending and e_type == "SWAP_IN" and char != ttds_holder:
                    ttds_target = char
                    ttds_expiration = t + 10.0
                    ttds_pending = False
                ttds_on = (ttds_target is not None
                           and char == ttds_target
                           and active_character == ttds_target
                           and ttds_expiration is not None
                           and t <= ttds_expiration + _WINDOW_EPS)
                event["ttds_state"] = "ON" if ttds_on else "OFF"
            else:
                event["ttds_state"] = "OFF"

            #      Starsealed Edict: a 20s EM window opened by the holder's skill CAST
            #      (first hit of a skill ability). Every stellar swirl by ANYONE while
            #      it is up adds a stack; refreshing or expiring resets them to 0.
            if starsealed_holder is not None:
                if (e_type == "HIT" and char == starsealed_holder
                        and event.get("attack_type") == AttackType.SKILL
                        and event.get("hit_offset") == 0.0):
                    starsealed_expiration = t + 20.0
                    starsealed_stacks = 0
                starsealed_on = (starsealed_expiration is not None
                                 and t <= starsealed_expiration + _WINDOW_EPS)
                if starsealed_on and is_stellar_swirl:
                    starsealed_stacks += 1
                if not starsealed_on:
                    starsealed_stacks = 0
                event["starsealed_state"] = "ON" if starsealed_on else "OFF"
                event["starsealed_stacks"] = starsealed_stacks if starsealed_on else 0
            else:
                event["starsealed_state"] = "OFF"
                event["starsealed_stacks"] = 0

            #      Whitelake Frostfeather: one stack per skill hit (0.1s gain CD), each
            #      stack lasting 8s on its own; at 3 stacks a new stack refreshes the
            #      OLDEST one. Per stack: ATK%. At exactly 3 stacks: stellar crit DMG.
            if whitlake_holder is not None:
                whitlake_stack_expiries = [x for x in whitlake_stack_expiries if x > t]
                if (e_type == "HIT" and char == whitlake_holder
                        and event.get("attack_type") == AttackType.SKILL
                        and t >= whitlake_gain_cd_ready):
                    if len(whitlake_stack_expiries) >= 3:
                        whitlake_stack_expiries.remove(min(whitlake_stack_expiries))
                    whitlake_stack_expiries.append(t + 8.0)
                    whitlake_gain_cd_ready = t + 0.1
                whitlake_stacks = len(whitlake_stack_expiries)
                event["whitlake_stacks"] = whitlake_stacks
                event["whitlake_max_state"] = "ON" if whitlake_stacks >= 3 else "OFF"
            else:
                event["whitlake_stacks"] = 0
                event["whitlake_max_state"] = "OFF"

            #      Finale Of The Deep: 15s ATK% on a standard skill hit, 10s CD,
            #      refreshed by later triggers.
            if finale_holder is not None:
                if (e_type == "HIT" and char == finale_holder
                        and cat == ActionCategory.STANDARD_DMG
                        and event.get("attack_type") == AttackType.SKILL
                        and t >= finale_cd_ready):
                    finale_expiration = t + 15.0
                    finale_cd_ready = t + 10.0
                finale_on = (finale_expiration is not None
                             and t <= finale_expiration + _WINDOW_EPS)
                event["finale_state"] = "ON" if finale_on else "OFF"
            else:
                event["finale_state"] = "OFF"

            #      Breezeborne Refrain: skill/burst damage grants a sigil (0.03s CD,
            #      sigils never expire). At 3 the sigils reset and the whole party
            #      gains stellar_bonus for 12s; no sigils are gained meanwhile.
            if breezeborne_holder is not None:
                breezeborne_on = (breezeborne_expiration is not None
                                  and t <= breezeborne_expiration + _WINDOW_EPS)
                if not breezeborne_on:
                    breezeborne_expiration = None
                    if (e_type == "HIT" and char == breezeborne_holder
                            and event.get("attack_type") in (AttackType.SKILL, AttackType.BURST)
                            and t >= breezeborne_gain_cd_ready):
                        breezeborne_sigils += 1
                        breezeborne_gain_cd_ready = t + 0.03
                        if breezeborne_sigils >= 3:
                            breezeborne_sigils = 0
                            breezeborne_expiration = t + 12.0
                            breezeborne_on = True
                event["breezeborne_sigils"] = breezeborne_sigils
                event["breezeborne_state"] = "ON" if breezeborne_on else "OFF"
            else:
                event["breezeborne_sigils"] = 0
                event["breezeborne_state"] = "OFF"

            #      Elegy for the End: skill/burst damage grants a sigil (0.2s CD).
            #      At 4 the sigils reset, the party gets ATK% + EM for 12s and no
            #      further sigils are gained for 20s.
            if elegy_holder is not None:
                elegy_on = (elegy_expiration is not None
                            and t <= elegy_expiration + _WINDOW_EPS)
                if (e_type == "HIT" and char == elegy_holder
                        and event.get("attack_type") in (AttackType.SKILL, AttackType.BURST)
                        and t >= elegy_gain_cd_ready and t >= elegy_lockout_until):
                    elegy_sigils += 1
                    elegy_gain_cd_ready = t + 0.2
                    if elegy_sigils >= 4:
                        elegy_sigils = 0
                        elegy_expiration = t + 12.0
                        elegy_lockout_until = t + 20.0
                        elegy_on = True
                event["elegy_sigils"] = elegy_sigils
                event["elegy_state"] = "ON" if elegy_on else "OFF"
            else:
                event["elegy_sigils"] = 0
                event["elegy_state"] = "OFF"

            #      New Bough: a skill hit opens/refreshes a 12s window; ANY damage hit
            #      by the holder inside it adds a stack (max 3), at most one per second
            #      (the opening skill hit counts as the first one).
            if newbough_holder is not None:
                newbough_window = (newbough_expiration is not None
                                   and t <= newbough_expiration + _WINDOW_EPS)
                if not newbough_window:
                    newbough_expiration = None
                    newbough_stacks = 0
                if e_type == "HIT" and char == newbough_holder:
                    if event.get("attack_type") == AttackType.SKILL:
                        newbough_expiration = t + 12.0
                        newbough_window = True
                    if (newbough_window and newbough_stacks < 3
                            and t >= newbough_last_gain + 1.0):
                        newbough_stacks += 1
                        newbough_last_gain = t
                event["newbough_stacks"] = newbough_stacks
            else:
                event["newbough_stacks"] = 0

            #      Silverdawn: skill/burst damage opens a 6s self window. Every stellar
            #      swirl the holder triggers, or stellar hit they deal, extends it by
            #      3s (0.1s CD, at most 8 extensions => 30s cap).
            if silverdawn_holder is not None:
                # Window is read from the pre-event state: the skill/burst hit that
                # opens it does not benefit from it.
                silverdawn_on = (silverdawn_expiration is not None
                                 and t <= silverdawn_expiration + _WINDOW_EPS)
                if (e_type == "HIT" and char == silverdawn_holder
                        and event.get("attack_type") in (AttackType.SKILL, AttackType.BURST)):
                    silverdawn_expiration = t + 6.0
                    silverdawn_extensions = 0
                if (silverdawn_on and char == silverdawn_holder
                        and (cat == ActionCategory.STELLAR_DMG or is_stellar_swirl)
                        and silverdawn_extensions < 8
                        and t >= silverdawn_ext_cd_ready):
                    silverdawn_expiration += 3.0
                    silverdawn_extensions += 1
                    silverdawn_ext_cd_ready = t + 0.1
                event["silverdawn_state"] = "ON" if silverdawn_on else "OFF"
                event["silverdawn_extensions"] = (silverdawn_extensions
                                                  if silverdawn_on else 0)
            else:
                event["silverdawn_state"] = "OFF"
                event["silverdawn_extensions"] = 0

            # 7. Odette Marvelous Stacks + Burst buff + C2 shred logic
            if "Odette" in self.party:
                odette_cons7 = self.party["Odette"].get("constellation", 0)
                # C1+: max stacks 6 and transfer rate doubles to 2/s.
                marvelous_max = 6 if odette_cons7 >= 1 else 4
                marvelous_rate = 2 if odette_cons7 >= 1 else 1

                is_cast = (e_type == "HIT" and char == "Odette"
                           and ((ability_name == "Skill Cast" and hit_name == "Cast")
                                or (ability_name == "Odette Burst" and hit_name == "Burst_tick1")))

                # Burst / C2 windows are read BEFORE this event arms them, so the cast
                # itself does not gain the buffs it starts.
                ob_on = odette_burst_expiration is not None and t <= odette_burst_expiration
                oc2_on = (odette_cons7 >= 2
                          and odette_c2_shred_expiration is not None
                          and t <= odette_c2_shred_expiration)

                if is_cast:
                    # Skill cast OR burst cast (NOT recast) opens/refreshes the window.
                    marvelous_active = True
                    marvelous_activation_time = t
                    odette_swap_time = None
                    # C2: casts a party cryo/anemo shred alongside Marvelous.
                    if odette_cons7 >= 2:
                        odette_c2_shred_expiration = t + 20.0

                # Burst buff ("Snow Swan's Dream", HERS only): 20s from the cast hit,
                # refreshed by every new burst cast. Value is talent-scaled.
                if (e_type == "HIT" and char == "Odette" and ability_name == "Odette Burst"
                        and hit_name == "Burst_tick1"):
                    odette_burst_expiration = t + 20.0

                if marvelous_active and (t - marvelous_activation_time >= 20.0):
                    marvelous_active = False

                if e_type == "SWAP_OUT" and char == "Odette" and marvelous_active:
                    odette_swap_time = t

                odette_stacks = 0
                party_stacks = 0
                if marvelous_active:
                    if odette_swap_time is None or t < odette_swap_time:
                        odette_stacks = marvelous_max
                        party_stacks = 0
                    else:
                        # Off-field, her stacks decay at `rate`/s and transfer to party.
                        time_off_field = t - odette_swap_time
                        stacks_transferred = min(marvelous_max, int(time_off_field * marvelous_rate))
                        odette_stacks = marvelous_max - stacks_transferred
                        party_stacks = stacks_transferred

                if char == "Odette":
                    event["marvelous_stacks"] = odette_stacks
                else:
                    event["marvelous_stacks"] = party_stacks

                # Audit columns for Odette's burst buff and C2 shred windows.
                event["odette_burst_state"] = "ON" if ob_on else "OFF"
                event["odette_c2_state"] = "ON" if oc2_on else "OFF"

            else:
                event["marvelous_stacks"] = 0
                event["odette_burst_state"] = "OFF"
                event["odette_c2_state"] = "OFF"

            # 7b. Anastasya: burst buff, A1 window, conditional extra stellar beat
            #     and the Triumph stellar swirl.
            if "Anastasya" in self.party:
                is_ana_skill_cast = (e_type == "HIT" and char == "Anastasya"
                                     and ability_name == "Skill Tap" and hit_name == "Cast")
                is_ana_burst_cast = (e_type == "HIT" and char == "Anastasya"
                                     and ability_name == "To the New World"
                                     and hit_name == "Burst_Cast")

                # Windows are read BEFORE this event arms them: her own cast does not
                # gain the buff it starts (the game resolves damage first).
                ana_burst_open = (anastasya_burst_expiration is not None
                                  and t <= anastasya_burst_expiration + _WINDOW_EPS)
                ana_a1_open = (anastasya_a1_expiration is not None
                               and t <= anastasya_a1_expiration + _WINDOW_EPS)

                # A1: the OTHER party members gain 16% crit DMG for 19s (refreshed
                # by every new skill cast).
                if is_ana_skill_cast:
                    anastasya_a1_expiration = t + 19.0

                # Burst cast: party stellar_bonus for 20s (value is talent-scaled)
                # plus the extra stellar beat window, and Triumph is armed.
                if is_ana_burst_cast:
                    anastasya_burst_expiration = t + 20.0
                    anastasya_triumph_armed = True
                    anastasya_triumph_ready_at = t + ANASTASYA_TRIUMPH_DELAY

                # Conditional hit: while her burst buff is up, every stellar beat of
                # her skill additionally fires an extra Stellar Swirl DMG hit.
                if (e_type == "HIT" and char == "Anastasya"
                        and hit_name.startswith("Palestar Crown Stellar")
                        and ana_burst_open):
                    extra = anastasya_extra_stellar.hits[0]
                    extra_event = dict(event)
                    extra_event.update({
                        "action": extra.name,
                        "hit_name": extra.name,
                        "category": extra.category,
                        "element": extra.element,
                        "elem_app": extra.elemental_app if extra.elemental_app else "-",
                        "ability_name": anastasya_extra_stellar.name,
                        "stat_ref": extra.stat_ref,
                        "multiplier": extra.multiplier,
                        "hit_offset": event.get("hit_offset", 0.0),
                        "attack_type": extra.attack_type,
                        "burst_call_id": None,
                    })
                    self.global_events.insert(i + 1, extra_event)

                # Triumph: fired by her next swap-in once 18s have elapsed since the
                # burst cast; one trigger per burst cast.
                if (e_type == "SWAP_IN" and char == "Anastasya"
                        and anastasya_triumph_armed
                        and anastasya_triumph_ready_at is not None
                        and t >= anastasya_triumph_ready_at - _WINDOW_EPS):
                    th = anastasya_triumph.hits[0]
                    triumph_event = {
                        "global_time": t,
                        "active_character": active_character,
                        "character": "Anastasya",
                        "action": th.name,
                        "category": th.category,
                        "elem_app": th.elemental_app if th.elemental_app else "-",
                        "element": th.element,
                        "event_type": "HIT",
                        "hit_name": th.name,
                        "ability_name": anastasya_triumph.name,
                        "stat_ref": th.stat_ref,
                        "multiplier": th.multiplier,
                        "attack_type": th.attack_type,
                        "hit_offset": 0.0,
                    }
                    self.global_events.insert(i + 1, triumph_event)
                    anastasya_triumph_armed = False

            # 8. Heart of the Furnace (HotF) Gear Effect Logic
            # Triggers when whoever holds the piece deals Stellar DMG OR triggers a
            # swirl (Stellar Reaction). Refreshes the 12s window on each new cast.
            # The applying hit must NOT benefit from the buff (the game deals damage
            # before casting/refreshing it), so resolve the state from the PRIOR window.
            hotf_active = (hotf_expiration_time is not None) and (t <= hotf_expiration_time)

            if hotf_holder and char == hotf_holder and e_type == "HIT" and (
                    cat == ActionCategory.STELLAR_DMG or is_stellar_swirl):
                hotf_expiration_time = t + 12.0

            event["hotf_state"] = "ON" if hotf_active else "OFF"

            # 9. Artifact set buffs (phase 1)
            #    Same rule as HotF and Cryo Resonance: every window is READ from the
            #    pre-event state and then armed, so the hit that triggers the set never
            #    benefits from the effect it just procced.
            #    Gilded Dreams: a swirl by the holder (anywhere) grants a party-
            #    composition buff to THEM for 8s, 8s CD measured from the trigger.
            if gilded_holder is not None:
                gilded_on = (gilded_expiration is not None
                             and t <= gilded_expiration + _WINDOW_EPS)
                if is_stellar_swirl and char == gilded_holder and t >= gilded_cd_ready:
                    gilded_expiration = t + 8.0
                    gilded_cd_ready = t + 8.0
                event["gilded_state"] = "ON" if gilded_on else "OFF"
            else:
                event["gilded_state"] = "OFF"

            #    Noblesse Oblige: the CAST of a burst gives the party ATK% for 12s.
            if noblesse_holder is not None:
                noblesse_on = (noblesse_expiration is not None
                               and t <= noblesse_expiration + _WINDOW_EPS)
                if (e_type == "HIT" and char == noblesse_holder
                        and event.get("attack_type") == AttackType.BURST
                        and event.get("hit_offset") == 0.0):
                    noblesse_expiration = t + 12.0
                event["noblesse_state"] = "ON" if noblesse_on else "OFF"
            else:
                event["noblesse_state"] = "OFF"

            #    Tenacity: a standard SKILL hit gives the party ATK% for 3s
            #    (refreshable, 0.5s trigger CD).
            if tenacity_holder is not None:
                tenacity_on = (tenacity_expiration is not None
                               and t <= tenacity_expiration + _WINDOW_EPS)
                if (e_type == "HIT" and char == tenacity_holder
                        and cat == ActionCategory.STANDARD_DMG
                        and event.get("attack_type") == AttackType.SKILL
                        and t >= tenacity_cd_ready):
                    tenacity_expiration = t + 3.0
                    tenacity_cd_ready = t + 0.5
                event["tenacity_state"] = "ON" if tenacity_on else "OFF"
            else:
                event["tenacity_state"] = "OFF"

            #    A Day Carved From Rising Winds: ANY standard hit by the holder
            #    gives THEM ATK% for 6s (refreshable).
            if risingwinds_holder is not None:
                risingwinds_on = (risingwinds_expiration is not None
                                  and t <= risingwinds_expiration + _WINDOW_EPS)
                if (e_type == "HIT" and char == risingwinds_holder
                        and cat == ActionCategory.STANDARD_DMG):
                    risingwinds_expiration = t + 6.0
                event["risingwinds_state"] = "ON" if risingwinds_on else "OFF"
            else:
                event["risingwinds_state"] = "OFF"

            #    Scarlet Proof: an ON-FIELD swirl by the holder gives THEM crit rate
            #    + stellar bonus for 10s (refreshable).
            if scarlet_holder is not None:
                scarlet_on = (scarlet_expiration is not None
                              and t <= scarlet_expiration + _WINDOW_EPS)
                if (is_stellar_swirl and char == scarlet_holder
                        and active_character == scarlet_holder):
                    scarlet_expiration = t + 10.0
                event["scarlet_state"] = "ON" if scarlet_on else "OFF"
            else:
                event["scarlet_state"] = "OFF"

            #    New Tsaritsa set: +1 stack (max 2) on a normal standard hit, a skill
            #    cast or a burst cast; every trigger refreshes the decay timer. The
            #    holder loses one stack per 3s of ON-FIELD time. While stacked they
            #    get crit rate on CRYO hits and stellar crit rate on everything.
            if tsaritsa_holder is not None:
                holder_active = (active_character == tsaritsa_holder)
                if holder_active:
                    if tsaritsa_last_t is not None:
                        tsaritsa_active_accum += max(0.0, t - tsaritsa_last_t)
                    tsaritsa_last_t = t
                    while tsaritsa_active_accum >= 3.0 - _WINDOW_EPS and tsaritsa_stacks > 0:
                        tsaritsa_active_accum -= 3.0
                        tsaritsa_stacks -= 1
                else:
                    tsaritsa_last_t = None

                attack_type = event.get("attack_type")
                is_cast = (attack_type in (AttackType.SKILL, AttackType.BURST)
                           and event.get("hit_offset") == 0.0)
                is_normal_standard = (cat == ActionCategory.STANDARD_DMG
                                      and attack_type == AttackType.NORMAL)
                # The crit / stellar-crit flags are read from the PRE-gain stack count,
                # so the hit that grants a stack does not benefit from it.
                stacks_before = tsaritsa_stacks
                if e_type == "HIT" and char == tsaritsa_holder and (is_cast or is_normal_standard):
                    tsaritsa_stacks = min(2, tsaritsa_stacks + 1)
                    tsaritsa_active_accum = 0.0

                event["tsaritsa_stacks"] = tsaritsa_stacks
                cryo_hit = (element == "Cryo" and char == tsaritsa_holder)
                event["tsaritsa_state"] = (
                    "ON" if (stacks_before > 0 and cryo_hit) else "OFF")
                event["tsaritsa_stellar_state"] = "ON" if stacks_before > 0 else "OFF"
            else:
                event["tsaritsa_stacks"] = 0
                event["tsaritsa_state"] = "OFF"
                event["tsaritsa_stellar_state"] = "OFF"

            # 11. Anastasya audit flags (these drive her FLAG_TO_BUFFS entries).
            #     burst / A1 reuse the PRE-arm windows computed in 7b.
            if "Anastasya" in self.party:
                triumph_ready = (anastasya_triumph_armed
                                 and anastasya_triumph_ready_at is not None
                                 and t >= anastasya_triumph_ready_at - _WINDOW_EPS)
                event["anastasya_burst_state"] = "ON" if ana_burst_open else "OFF"
                event["anastasya_a1_state"] = "ON" if ana_a1_open else "OFF"
                event["anastasya_triumph_ready"] = "ON" if triumph_ready else "OFF"
                # A4 is a permanent passive while she is in the party.
                event["anastasya_a4_state"] = "ON"
            else:
                event["anastasya_burst_state"] = "OFF"
                event["anastasya_a1_state"] = "OFF"
                event["anastasya_triumph_ready"] = "OFF"
                event["anastasya_a4_state"] = "OFF"

            i += 1

        # Re-sort so the auditable table and analytics are strictly chronological
        # (evaluated events may have been inserted out of place).
        self.global_events.sort(key=lambda x: x["global_time"])
        self._timeline_evaluated = True
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
                # 100% RV / KQM flag for this hit's owner (carries only). The party
                # entry stores the UI label, so resolve it through the shared helper.
                final_stats["rv_mode"] = is_rv_mode(char_data)

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
                        "EM": p_init.get("em", p_init.get("EM", 0.0)),
                        "rv_mode": is_rv_mode(p_d),
                    }
                    if event.get("cryo_resonance_state") == "ON":
                        party_stats_dict[p_name]["CR"] += 0.15
                        party_stats_dict[p_name]["crit_rate"] += 0.15

                if char in party_stats_dict:
                    party_stats_dict[char]["CR"] = final_stats.get("CR", party_stats_dict[char]["CR"])
                    party_stats_dict[char]["CD"] = final_stats.get("CD", party_stats_dict[char]["CD"])
                    party_stats_dict[char]["crit_rate"] = final_stats.get("CR", party_stats_dict[char]["crit_rate"])
                    party_stats_dict[char]["crit_dmg"] = final_stats.get("CD", party_stats_dict[char]["crit_dmg"])
                    party_stats_dict[char]["EM"] = final_stats.get("EM", final_stats.get("em", party_stats_dict[char]["EM"]))
                    party_stats_dict[char]["rv_mode"] = is_rv_mode(char_data)

                # Reaction contributors resolve their buffed stats AT THIS EVENT (swirls
                # and vortex explosions), so each contributor's crit / EM is taken from
                # the moment of the hit. Faruzan's buff reaches only the ACTIVE char.
                vmeta = event.get("vortex_metadata")
                smeta = event.get("swirl_metadata")
                contributor_names = []
                if vmeta:
                    contributor_names = [c for c in set(
                        (vmeta.get("anemo_contributors") or []) + (vmeta.get("cryo_contributors") or [])) if c]
                elif smeta:
                    ac = smeta.get("anemo_contributor")
                    cl = smeta.get("cryo_contributors", []) or []
                    contributor_names = list(dict.fromkeys(([ac] if ac else []) + [c for c in cl if c]))

                for cname in contributor_names:
                    if cname not in party_stats_dict:
                        continue
                    c_data = self.party.get(cname, {})
                    c_init = self.char_initial_stats_map.get(cname)
                    if c_init is None:
                        c_init = build_initial_stats(cname, None, None, {}, {})
                        c_init = apply_permanent_buffs(c_init, cname)
                        self.char_initial_stats_map[cname] = c_init
                    c_flags = dict(event)
                    c_flags["faruzan_buff_state"] = (
                        "ON" if (cname == active_char and event.get("faruzan_buff_window") == "ON") else "OFF"
                    )
                    c_snap = build_snapshot_stats(
                        initial_stats=c_init,
                        event_flags=c_flags,
                        party=self.party,
                        refinement=c_data.get("refinement", 1),
                        char_name=cname,
                        active_character=active_char,
                        char_initial_stats_map=self.char_initial_stats_map,
                    )
                    c_final = compute_final_stats(c_snap)
                    party_stats_dict[cname]["CR"] = c_final.get("CR", party_stats_dict[cname]["CR"])
                    party_stats_dict[cname]["CD"] = c_final.get("CD", party_stats_dict[cname]["CD"])
                    party_stats_dict[cname]["crit_rate"] = c_final.get("CR", party_stats_dict[cname]["crit_rate"])
                    party_stats_dict[cname]["crit_dmg"] = c_final.get("CD", party_stats_dict[cname]["crit_dmg"])
                    party_stats_dict[cname]["EM"] = c_final.get("EM", c_final.get("em", party_stats_dict[cname]["EM"]))

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
                # Multiplier audit fields (None for Stellar Reaction / non-damage → "—").
                event["base_damage"] = dmg.get("base_damage")
                event["quills_total"] = dmg.get("quill_damage")
                event["bonus_mult"] = dmg.get("bonus_mult")
                event["elevation_mult"] = dmg.get("elevation_mult")
                event["crit_mult_avg"] = dmg.get("crit_mult_average")
                event["def_mult"] = dmg.get("def_mult")
                event["res_mult"] = dmg.get("res_mult")
                # Snapshot stats used for this hit's damage (owner, after buffs).
                event["stat_hp"] = final_stats.get("HP", 0.0)
                event["stat_atk"] = final_stats.get("ATK", 0.0)
                event["stat_def"] = final_stats.get("DEF", 0.0)
                event["stat_em"] = final_stats.get("EM", 0.0)
                event["stat_cr"] = final_stats.get("CR", 0.05)
                event["stat_cd"] = final_stats.get("CD", 0.50)
                # 100% RV / KQM: crit is a single Crit Value, so the table shows CV
                # instead of CR% / CD% (which are only storage in this model).
                event["rv_mode"] = bool(final_stats.get("rv_mode"))
            else:
                event["non_crit"] = None
                event["crit_damage"] = None
                event["average_damage"] = None
                event["effective_average_damage"] = None
                event["base_damage"] = None
                event["quills_total"] = None
                event["bonus_mult"] = None
                event["elevation_mult"] = None
                event["crit_mult_avg"] = None
                event["def_mult"] = None
                event["res_mult"] = None
                event["stat_hp"] = None
                event["stat_atk"] = None
                event["stat_def"] = None
                event["stat_em"] = None
                event["stat_cr"] = None
                event["stat_cd"] = None
                event["rv_mode"] = False

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
        has_faruzan = any(ev.get("faruzan_buff_state") == "ON" for ev in self.global_events)
        has_c2 = any(ev.get("aether_c2_state") == "ON" for ev in self.global_events)
        has_c2_enhanced = any(ev.get("aether_c2_enhanced_state") == "ON" for ev in self.global_events)
        has_aether = "Aether" in self.party
        has_frostglow = has_aether or any(ev.get("frostglow_stacks", 0) > 0 for ev in self.global_events)
        has_odette = "Odette" in self.party
        has_odette_burst = any(ev.get("odette_burst_state") == "ON" for ev in self.global_events)
        has_odette_c2 = any(ev.get("odette_c2_state") == "ON" for ev in self.global_events)
        has_sucrose_a1 = any(ev.get("sucrose_a1_state") == "ON" for ev in self.global_events)
        has_sucrose_a4 = any(ev.get("sucrose_a4_state") == "ON" for ev in self.global_events)
        has_sucrose_c6 = any(ev.get("sucrose_c6_state") == "ON" for ev in self.global_events)
        has_exaiphanes = any(ev.get("exaiphanes_blade_state") == "ON" for ev in self.global_events)
        has_silver_light = any((ev.get("silver_light_stacks", 0) or 0) > 0 for ev in self.global_events)
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
        dmg_headers = ["average_damage", "non_crit", "crit_damage", "effective_average_damage"]
        dmg_widths = [12, 13, 16, 26]

        # 2b. Mults category columns (multiplier audit; "—" = not applicable)
        mult_headers = ["Base", "Quills", "Bonus", "Elev", "Crit", "DEF", "Res"]
        mult_widths = [10, 10, 9, 8, 9, 9, 9]

        # 3. Buffs category columns -- registry-driven: technical names, grouped
        #    characters -> weapons -> artifacts -> team, and only for effects whose
        #    owner (character/constellation, weapon, artifact set, resonance) is in
        #    the party.
        import buff_registry
        buff_columns = buff_registry.visible_buffs(getattr(self, "party", {}) or {})
        buff_headers = [entry["label"] for entry in buff_columns]
        buff_widths = [min(max(len(header), 6), 14) for header in buff_headers]

        # Spans for the 2-tier Category Header
        main_span = sum(main_widths) + 3 * (len(main_widths) - 1)
        dmg_span = sum(dmg_widths) + 3 * (len(dmg_widths) - 1)
        mult_span = sum(mult_widths) + 3 * (len(mult_widths) - 1)
        buff_span = sum(buff_widths) + 3 * (len(buff_widths) - 1) if buff_widths else 0

        # Construct Category Row
        categories = [
            f"{'Main':^{main_span}}",
            f"{'Damage calcs':^{dmg_span}}",
            f"{'Mults':^{mult_span}}",
        ]
        if buff_widths:
            categories.append(f"{'Buffs':^{buff_span}}")
        category_str = " | ".join(categories)

        # Construct Column Header Row
        all_headers = main_headers + dmg_headers + mult_headers + buff_headers
        all_widths = main_widths + dmg_widths + mult_widths + buff_widths
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

            def _f1(v):
                return f"{v:.1f}" if v is not None else "--"
            def _f3(v):
                return f"{v:.3f}" if v is not None else "--"
            base_str = _f1(event.get("base_damage"))
            q_str = _f1(event.get("quills_total"))
            bonus_str = _f3(event.get("bonus_mult"))
            elev_str = _f3(event.get("elevation_mult"))
            crit_str = _f3(event.get("crit_mult_avg"))
            def_str = _f3(event.get("def_mult"))
            res_str = _f3(event.get("res_mult"))

            row_data = [
                f"{event['global_time']:.3f}",
                str(event.get("active_character", "None")),
                str(event.get("character", "")),
                str(event.get("action", "")),
                str(event.get("cryo_aura", "-")),
                str(event.get("reaction", "-")),
                avg_str,
                nc_str,
                cd_str,
                eff_str,
                base_str,
                q_str,
                bonus_str,
                elev_str,
                crit_str,
                def_str,
                res_str,
            ]
            for entry in buff_columns:
                value = event.get(entry["key"], "OFF")
                row_data.append("OFF" if value is None else str(value))

            row_str = " | ".join(f"{val:<{w}}" for val, w in zip(row_data, all_widths))
            print(row_str)

