"""smoke_test.py — automated invariant checks for the Mizuki simulator engine.

Run with:
    python smoke_test.py

Checks:
  1. All engine modules import and a full preset trial evaluates without error.
  2. The event table is strictly chronological (auditability requirement).
  3. No NaN / non-finite average_damage values.
  4. Aether kit auditors update: Frostglow stacks, C2 basic/enhanced, Aether C6
     window, and Burst variant substitution ("Enhanced"/"Standard").
  5. evaluate_timeline() is idempotent (calling display() after evaluate_timeline
     must NOT duplicate events).
  6. Sucrose kit semantics: A1 (+50 EM, non-Anemo, 8s), A4 (20% of her FLAT EM,
     others only, 8s) and C6 (+20% cryo_bonus for exactly one burst field).
  7. Mizuki C6 semantics: party +10% stellar CR / +20% stellar CD while DDS is
     up, and self crit-from-EM on her FLAT EM basis (caps 20% / 80%).
  8. Buff catalogue integrity: every entry in buffs.py is either reachable from
     stats_calc.FLAG_TO_BUFFS or explicitly declared DORMANT, every dispatch key
     exists, and every non-constant descriptor uses a known basis.
  9. Weapons phase 1: permanent stats resolve for every implemented weapon
     (name parsing / secondary keys) and the conditional passives of The Widsith,
     Sacrificial Jade and Sunny Morning Sleep-In honour their triggers, durations
     and cooldowns.
"""
from timeline import RotationTimeline, SUCROSE_BURST_WINDOW, ANASTASYA_TRIUMPH_DELAY
from abilities import (
    odette_qe, aether_en1, sucrose_eq, aether_n1, mizuki_skill, aether_skill,
    sucrose_skill, sucrose_burst,
)
from models import FieldSequence, Rotation, Trial, ActionCategory
from stats_calc import (
    build_initial_stats, build_snapshot_stats, compute_final_stats, compute_flat_em,
    compute_card_stats, is_rv_mode,
)
from damage_calc import crit_mult_from_crit_value
import copy
import presets
import build_io


def _buffed_stats(timeline, event, char):
    """Resolve *char*'s final stats for one event (same path the engine uses)."""
    init = timeline.char_initial_stats_map.get(char)
    if init is None:
        init = build_initial_stats(char, None, None, {}, {})
    snap = build_snapshot_stats(
        initial_stats=init,
        event_flags=event,
        party=timeline.party,
        refinement=timeline.party.get(char, {}).get("refinement", 1),
        char_name=char,
        active_character=event.get("active_character"),
        char_initial_stats_map=timeline.char_initial_stats_map,
    )
    return compute_final_stats(snap)


def _run_sucrose_check() -> dict:
    """Sucrose kit semantics.

    Timeline: Aether (Cryo) sets a cryo aura -> Sucrose skill (swirl => A1)
    -> Sucrose burst (A4 refresh + C6 field) -> late Aether hits after the field.

    Checks the three buffs' scope, magnitude and window length:
      A1  +50 EM, non-Anemo allies only, 8s
      A4  +20% of Sucrose's FLAT EM, others only, 8s
      C6  +20% cryo_bonus to the whole party for exactly ONE burst field
    """
    party = {
        "Sucrose": {"constellation": 6, "level": 90, "refinement": 1,
                    "weapon": "The Widsith (Average)", "artifact_set": "2p/2p EM",
                    "talents": "1/10/10"},
        "Aether": {"constellation": 0, "level": 90, "refinement": 1,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK",
                   "talents": "1/10/10"},
    }
    late = FieldSequence("Late N1", "Aether", swap_out_time=1.2)
    late.add_ability(0.5, aether_n1)

    t = RotationTimeline(party=party)
    t.add_trial(Trial(
        name="suc", end_mode="time", end_time=16.0,
        rotations=[Rotation(name="r", sequences=[aether_en1, sucrose_eq, late], repetitions=1)],
    ))
    t.evaluate_timeline()

    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    burst_hits = [e for e in hits
                  if e.get("character") == "Sucrose" and e.get("ability_name") == "Sucrose Burst"]
    cast = burst_hits[0]["global_time"]
    last_hit = burst_hits[-1]["global_time"]
    after_burst = [e for e in hits if e["global_time"] > last_hit + 1e-9]

    def em_from_flags(event, char, flags):
        """EM contribution of *flags* for *char* at *event* (on minus forced-off)."""
        on = _buffed_stats(t, event, char)["EM"]
        stripped = dict(event)
        for flag in flags:
            stripped[flag] = "OFF"
        return on - _buffed_stats(t, stripped, char)["EM"]

    inside = next(e for e in hits
                  if e.get("character") == "Aether"
                  and e.get("sucrose_a1_state") == "ON"
                  and e.get("sucrose_a4_state") == "ON"
                  and e["global_time"] < cast)
    in_c6 = next(e for e in hits
                 if e.get("character") == "Aether" and e.get("sucrose_c6_state") == "ON")

    return {
        "a1": any(e.get("sucrose_a1_state") == "ON" for e in hits),
        "a4": any(e.get("sucrose_a4_state") == "ON" for e in hits),
        "c6": any(e.get("sucrose_c6_state") == "ON" for e in hits),
        "window": round(last_hit - cast, 6),
        "last_hit_on": burst_hits[-1].get("sucrose_c6_state") == "ON",
        "after_burst_c6": any(e.get("sucrose_c6_state") == "ON" for e in after_burst),
        "sucrose_flat_em": round(compute_flat_em(
            "Sucrose", inside, inside.get("active_character"),
            t.party, t.char_initial_stats_map), 4),
        "ally_a1_em": round(em_from_flags(inside, "Aether", ["sucrose_a1_state"]), 4),
        "self_a1_em": round(em_from_flags(inside, "Sucrose", ["sucrose_a1_state"]), 4),
        "ally_a4_em": round(em_from_flags(inside, "Aether", ["sucrose_a4_state"]), 4),
        "self_a4_em": round(em_from_flags(inside, "Sucrose", ["sucrose_a4_state"]), 4),
        "ally_c6_bonus": round(_buffed_stats(t, in_c6, "Aether")["Cryo Bonus"], 4),
    }


def _run_mizuki_c6_check() -> dict:
    """Mizuki C6, both halves, at C0 vs C6 with a fixed 600 base EM.

      part 1: party stellar_crit_rate +10% / stellar_crit_dmg +20% while DDS is up
      part 2: self crit_rate +0.04% and crit_dmg +0.16% per EM above 500 on her
              FLAT EM basis (caps 20% / 80% at 1000 flat EM)
    """
    out = {}
    for const in (0, 6):
        party = copy.deepcopy(presets.DEFAULT_PARTY)
        party["Mizuki"]["constellation"] = const
        t = RotationTimeline(party=party)
        t.char_initial_stats_map["Mizuki"]["em"] = 600.0
        t.add_trial(presets.TEST_TRIAL_30S)
        t.evaluate_timeline()

        events = [e for e in t.global_events
                  if e.get("event_type") == "HIT"
                  and e.get("character") == "Mizuki"
                  and e.get("dreamdrifter_state") == "ON"
                  and e.get("mizuki_a4_state") == "ON"]
        event = events[-1]
        final = _buffed_stats(t, event, "Mizuki")
        out[const] = {
            "CR": final["CR"],
            "CD": final["CD"],
            "stellar_cr": final["Stellar CR"],
            "stellar_cd": final["Stellar CD"],
            "flat_em": compute_flat_em("Mizuki", event, event.get("active_character"),
                                       t.party, t.char_initial_stats_map),
        }
    return out


def _run_odette_burst_check() -> bool:
    """Builds an Odette QE run (burst+recast) and checks her 6s burst buff fires."""
    t = RotationTimeline(party=presets.DEFAULT_PARTY)
    t.add_trial(Trial(
        name="odette_qe", end_mode="time", end_time=8.0,
        rotations=[Rotation(name="r", sequences=[odette_qe], repetitions=1)],
    ))
    t.evaluate_timeline()
    return any(e.get("odette_burst_state") == "ON"
               for e in t.global_events if e.get("event_type") == "HIT")


def _flag_delta(timeline, event, char, flag, stat):
    """Contribution of *flag* to *char*'s *stat* at *event* (on minus forced-off)."""
    on = _buffed_stats(timeline, event, char)[stat]
    stripped = dict(event)
    stripped[flag] = "OFF"
    return on - _buffed_stats(timeline, stripped, char)[stat]


def _run_weapon_check() -> dict:
    """Weapon phase 1: permanent stats resolve + conditional passives behave.

    Covers The Widsith (Average / All EM), Sacrificial Jade, Sunny Morning Sleep-In
    and Starcaller's Watch (permanent only). The permanent-stat block is what
    catches the weapon-name parsing and the 'elemental_mastery' key regressions.
    """
    from characters import CHARACTER_BASE_STATS
    from stats_calc import build_initial_stats
    from weapons import resolve_weapon_key

    out = {}
    char_atk = CHARACTER_BASE_STATS["Mizuki"]["base_atk"][3]   # level 90
    char_em = CHARACTER_BASE_STATS["Mizuki"]["em"][3]
    artifact_em = 160.0                                        # 2p/2p EM

    def init(weapon, refinement=1):
        return build_initial_stats("Mizuki", 90, weapon, "2p/2p EM", {}, {},
                                   refinement=refinement)

    # --- 1. Permanent stats (base ATK + secondary) for every phase-1 weapon ---
    widsith = init("The Widsith (Average)", 5)
    sunny = init("Sunny Morning Sleep-In", 1)
    jade = init("Sacrificial Jade", 1)
    starcaller = init("Starcaller's Watch", 5)
    out["widsith_atk"] = round(widsith["base_atk"] - char_atk, 3)          # 510
    out["widsith_cd"] = round(widsith["crit_dmg"] - 0.5, 4)                # 0.551
    out["sunny_em"] = round(sunny["em"] - char_em - artifact_em, 3)        # 265
    out["jade_cr"] = round(jade["crit_rate"] - 0.05, 4)                    # 0.368
    out["starcaller_em"] = round(starcaller["em"] - char_em - artifact_em, 3)  # 465
    out["key_variant"] = resolve_weapon_key("The Widsith (Average)")
    out["key_suffixed"] = resolve_weapon_key("Silver Light (R5)")

    aether = {"constellation": 0, "level": 90, "refinement": 1,
              "weapon": "New Bough", "artifact_set": "2p/2p ATK", "talents": "1/13/13"}

    # --- 2. The Widsith: 10s window, 30s cooldown measured from the trigger ---
    # Mizuki takes the field at 0, 18 and 36 (18s cycle keeps her 15s skill CD legal),
    # so the second entry must NOT re-proc and the third one must.
    party = {
        "Mizuki": {"constellation": 2, "level": 90, "refinement": 5,
                   "weapon": "The Widsith (Average)", "artifact_set": "2p/2p EM",
                   "talents": "10/13/13"},
        "Aether": dict(aether),
    }
    mizuki_field = FieldSequence("Mizuki Field", "Mizuki", swap_out_time=10.0)
    mizuki_field.add_ability(0.3, mizuki_skill)
    aether_field = FieldSequence("Aether Field", "Aether", swap_out_time=8.0)
    aether_field.add_ability(0.5, aether_n1)

    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="widsith", end_mode="time", end_time=60.0,
                      rotations=[Rotation(name="r", sequences=[mizuki_field, aether_field],
                                          repetitions=3)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    on_times = [e["global_time"] for e in hits if e.get("widsith_state") == "ON"]
    out["widsith_on_early"] = any(x <= 10.0 for x in on_times)
    out["widsith_on_mid"] = any(11.0 <= x <= 35.0 for x in on_times)     # must be False
    out["widsith_on_late"] = any(36.0 <= x <= 46.0 for x in on_times)
    first_on = next((e for e in hits if e.get("widsith_state") == "ON"), None)
    if first_on is not None:
        out["widsith_em"] = round(_flag_delta(t, first_on, "Mizuki", "widsith_state", "EM"), 3)
        out["widsith_atk_pct"] = round(
            _flag_delta(t, first_on, "Mizuki", "widsith_state", "atk_percent"), 4)
        out["widsith_cryo"] = round(
            _flag_delta(t, first_on, "Mizuki", "widsith_state", "Cryo Bonus"), 4)
    else:
        out["widsith_em"] = out["widsith_atk_pct"] = out["widsith_cryo"] = None

    # --- 3. Sacrificial Jade: on at start, off after >10s on-field, back after 5s ---
    party = {
        "Mizuki": {"constellation": 2, "level": 90, "refinement": 1,
                   "weapon": "Sacrificial Jade", "artifact_set": "2p/2p EM",
                   "talents": "10/13/13"},
        "Aether": dict(aether),
    }
    mizuki_long = FieldSequence("Mizuki Long", "Mizuki", swap_out_time=14.0)
    mizuki_long.add_ability(0.3, mizuki_skill)
    observer = FieldSequence("Observer", "Aether", swap_out_time=9.0)
    for offset in (0.5, 2.5, 4.5, 6.5):
        observer.add_ability(offset, aether_n1)

    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="jade", end_mode="time", end_time=40.0,
                      rotations=[Rotation(name="r", sequences=[mizuki_long, observer],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    jade_on = [e["global_time"] for e in hits if e.get("sacrificial_jade_state") == "ON"]
    out["jade_on_early"] = any(x <= 10.0 for x in jade_on)
    out["jade_off_onfield"] = not any(10.5 <= x <= 18.0 for x in jade_on)
    out["jade_on_after_bench"] = any(x >= 20.0 for x in jade_on)
    jade_event = next((e for e in hits if e.get("sacrificial_jade_state") == "ON"), None)
    if jade_event is not None:
        out["jade_em"] = round(
            _flag_delta(t, jade_event, "Mizuki", "sacrificial_jade_state", "EM"), 3)
        out["jade_hp_pct"] = round(
            _flag_delta(t, jade_event, "Mizuki", "sacrificial_jade_state", "hp_percent"), 4)
    else:
        out["jade_em"] = out["jade_hp_pct"] = None

    # --- 4. Sunny Morning Sleep-In: swirl 6s / skill 9s / burst 30s ----------
    party = {
        "Sucrose": {"constellation": 6, "level": 90, "refinement": 1,
                    "weapon": "Sunny Morning Sleep-In", "artifact_set": "2p/2p EM",
                    "talents": "1/10/10"},
        "Aether": dict(aether),
    }
    watcher = FieldSequence("Watcher", "Aether", swap_out_time=44.0)
    for offset in (10.0, 13.0, 16.0, 19.0, 22.0, 25.0, 28.0, 31.0, 34.0, 37.0, 40.0):
        watcher.add_ability(offset, aether_n1)

    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="sunny", end_mode="time", end_time=50.0,
                      rotations=[Rotation(name="r", sequences=[aether_en1, sucrose_eq, watcher],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]

    def window_info(flag):
        """(first ON, last ON, first OFF after the last ON) for a window flag."""
        on = [e["global_time"] for e in hits if e.get(flag) == "ON"]
        if not on:
            return None, None, None
        first_on, last_on = min(on), max(on)
        later = [e["global_time"] for e in hits
                 if e["global_time"] > last_on + 1e-9 and e.get(flag) != "ON"]
        return first_on, last_on, (min(later) if later else None)

    # The watcher's normal attacks are the only events after the burst, so they are
    # what proves each window survives its full duration and then expires.
    for name, flag, duration in (("swirl", "sunny_swirl_state", 6.0),
                                 ("skill", "sunny_skill_state", 9.0),
                                 ("burst", "sunny_burst_state", 30.0)):
        first_on, last_on, first_off = window_info(flag)
        out[f"sunny_{name}_on"] = first_on is not None
        out[f"sunny_{name}_long_enough"] = (
            first_on is not None and last_on is not None
            and (last_on - first_on) >= duration - 3.5)
        out[f"sunny_{name}_off"] = (
            first_off is not None and last_on is not None
            and (first_off - last_on) <= duration + 3.5)

    swirl_event = next((e for e in hits if e.get("sunny_swirl_state") == "ON"), None)
    skill_event = next((e for e in hits if e.get("sunny_skill_state") == "ON"), None)
    burst_event = next((e for e in hits if e.get("sunny_burst_state") == "ON"), None)
    out["sunny_swirl_em"] = round(
        _flag_delta(t, swirl_event, "Sucrose", "sunny_swirl_state", "EM"), 3) if swirl_event else None
    out["sunny_skill_em"] = round(
        _flag_delta(t, skill_event, "Sucrose", "sunny_skill_state", "EM"), 3) if skill_event else None
    out["sunny_burst_em"] = round(
        _flag_delta(t, burst_event, "Sucrose", "sunny_burst_state", "EM"), 3) if burst_event else None

    return out


def _run_weapon_phase2_check() -> dict:
    """Weapon phase 2: A Thousand Floating Dreams (party composition), Wandering
    Evenstar (periodic stacks), Thrilling Tales (next-character proc) and
    Starsealed Edict (cast window + swirl stacks)."""
    from stats_calc import build_initial_stats, apply_weapon_party_stats, compute_flat_em

    out = {}
    aether = {"constellation": 0, "level": 90, "refinement": 1,
              "weapon": "New Bough", "artifact_set": "2p/2p ATK", "talents": "1/13/13"}

    # --- 1. A Thousand Floating Dreams: composition-dependent permanent stats --
    def atfd_deltas(members, refinement=5):
        party, raw, enriched = {}, {}, {}
        for index, name in enumerate(members):
            weapon = "A Thousand Floating Dreams" if index == 0 else "New Bough"
            party_ref = refinement if index == 0 else 1
            party[name] = {"weapon": weapon, "refinement": party_ref}
            raw[name] = build_initial_stats(name, 90, weapon, "2p/2p EM", {}, {},
                                            refinement=party_ref)
            enriched[name] = dict(raw[name])
        apply_weapon_party_stats(enriched, party)
        holder = members[0]
        return (enriched[holder]["em"] - raw[holder]["em"],
                enriched[holder]["anemo_bonus"] - raw[holder]["anemo_bonus"],
                enriched[members[1]]["em"] - raw[members[1]]["em"])

    # Anemo holder: Aether/Odette are Cryo (different), Sucrose is Anemo (same).
    em, elem, ally = atfd_deltas(["Mizuki", "Aether", "Odette", "Sucrose"])
    out["atfd_mixed"] = (round(em, 3), round(elem, 4), round(ally, 3))       # 128, .26, 48
    em, elem, _ = atfd_deltas(["Mizuki", "Aether", "Odette", "Diona"])
    out["atfd_all_diff"] = (round(em, 3), round(elem, 4))                    # 192, 0
    em, elem, _ = atfd_deltas(["Mizuki", "Sucrose", "Faruzan"])
    out["atfd_all_same"] = (round(em, 3), round(elem, 4))                    # 0, .52

    party = {"Mizuki": {"weapon": "A Thousand Floating Dreams", "refinement": 5},
             "Aether": {"weapon": "New Bough", "refinement": 1},
             "Odette": {"weapon": "New Bough", "refinement": 1}}
    stats_map = {name: build_initial_stats(name, 90, data["weapon"], "2p/2p EM", {}, {},
                                           refinement=data["refinement"])
                 for name, data in party.items()}
    apply_weapon_party_stats(stats_map, party)
    once = {name: stats_map[name]["em"] for name in stats_map}
    apply_weapon_party_stats(stats_map, party)
    out["atfd_idempotent"] = all(abs(once[n] - stats_map[n]["em"]) < 1e-9 for n in once)

    # --- 2. Wandering Evenstar: 12s buff every 10s, stacking to 2 -------------
    party = {
        "Mizuki": {"constellation": 2, "level": 90, "refinement": 5,
                   "weapon": "Wandering Evenstar", "artifact_set": "2p/2p EM",
                   "talents": "10/13/13"},
        "Aether": dict(aether),
    }
    watcher = FieldSequence("Watcher", "Aether", swap_out_time=20.0)
    for offset in (4.5, 10.5, 13.5):
        watcher.add_ability(offset, aether_n1)
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="evenstar", end_mode="time", end_time=25.0,
                      rotations=[Rotation(name="r", sequences=[watcher], repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    out["evenstar_stacks_at"] = [
        next((e.get("evenstar_stacks") for e in hits if lo <= e["global_time"] <= hi), None)
        for lo, hi in ((0.0, 5.0), (10.0, 11.0), (13.0, 14.0))
    ]
    one = next((e for e in hits if e.get("evenstar_stacks") == 1), None)
    two = next((e for e in hits if e.get("evenstar_stacks") == 2), None)
    if one is not None and two is not None:
        flat = compute_flat_em("Mizuki", one, one.get("active_character"),
                               t.party, t.char_initial_stats_map)
        out["evenstar_self_one"] = round(_flag_delta(t, one, "Mizuki", "evenstar_stacks", "atk_flat"), 3)
        out["evenstar_want_one"] = round(0.48 * flat, 3)
        out["evenstar_self_two"] = round(_flag_delta(t, two, "Mizuki", "evenstar_stacks", "atk_flat"), 3)
        out["evenstar_want_two"] = round(2 * 0.48 * flat, 3)
        out["evenstar_ally_one"] = round(_flag_delta(t, one, "Aether", "evenstar_stacks", "atk_flat"), 3)
        out["evenstar_ally_want"] = round(0.30 * 0.48 * flat, 3)
    else:
        out["evenstar_self_one"] = out["evenstar_want_one"] = None
        out["evenstar_self_two"] = out["evenstar_want_two"] = None
        out["evenstar_ally_one"] = out["evenstar_ally_want"] = None

    # --- 3. Thrilling Tales: holder swap-out -> NEXT character, 10s, 20s CD ----
    party = {
        "Mizuki": {"constellation": 2, "level": 90, "refinement": 1,
                   "weapon": "Thrilling Tales of Dragon Slayers",
                   "artifact_set": "2p/2p EM", "talents": "10/13/13"},
        "Aether": dict(aether),
    }
    mizuki_short = FieldSequence("Mizuki Short", "Mizuki", swap_out_time=1.5)
    mizuki_short.add_ability(0.3, mizuki_skill)
    late = FieldSequence("Late", "Aether", swap_out_time=14.5)
    for offset in (0.5, 6.0, 11.0):
        late.add_ability(offset, aether_n1)
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="ttds", end_mode="time", end_time=40.0,
                      rotations=[Rotation(name="r", sequences=[mizuki_short, late],
                                          repetitions=2)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    on = [e for e in hits if e.get("ttds_state") == "ON"]
    out["ttds_on"] = bool(on)
    out["ttds_only_target"] = bool(on) and all(e.get("character") == "Aether" for e in on)
    out["ttds_off_after_cd"] = not any(e["global_time"] >= 12.0 for e in on)
    out["ttds_atk_pct"] = (round(_flag_delta(t, on[0], "Aether", "ttds_state", "atk_percent"), 4)
                           if on else None)

    # --- 4. Starsealed Edict: cast window (20s) + swirl stacks -----------------
    party = {
        "Aether": dict(aether),
        "Mizuki": {"constellation": 2, "level": 90, "refinement": 5,
                   "weapon": "Starsealed Edict", "artifact_set": "2p/2p EM",
                   "talents": "10/13/13"},
    }
    mizuki_field = FieldSequence("Mizuki Field", "Mizuki", swap_out_time=10.0)
    mizuki_field.add_ability(0.3, mizuki_skill)
    tail = FieldSequence("Tail", "Aether", swap_out_time=12.0)
    for offset in (14.0, 16.0):
        tail.add_ability(offset, aether_n1)
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="starsealed", end_mode="time", end_time=32.0,
                      rotations=[Rotation(name="r",
                                          sequences=[aether_en1, mizuki_field, tail],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    on = [e for e in hits if e.get("starsealed_state") == "ON"]
    cast_times = [e["global_time"] for e in hits
                  if e.get("character") == "Mizuki"
                  and e.get("ability_name") == "Mizuki Skill"
                  and e.get("hit_offset") == 0.0]
    out["starsealed_on"] = bool(on)
    out["starsealed_opens_at_cast"] = bool(on) and bool(cast_times) and \
        abs(on[0]["global_time"] - cast_times[0]) < 1e-6
    out["starsealed_max_stacks"] = max((int(e.get("starsealed_stacks") or 0) for e in hits),
                                       default=0)
    out["starsealed_off_tail"] = not any(e["global_time"] > 22.0 for e in on)
    stacked = next((e for e in hits if int(e.get("starsealed_stacks") or 0) >= 1), None)
    if stacked is not None:
        stacks = int(stacked.get("starsealed_stacks") or 0)
        out["starsealed_const_em"] = round(
            _flag_delta(t, stacked, "Mizuki", "starsealed_state", "EM"), 3)
        out["starsealed_stack_em"] = round(
            _flag_delta(t, stacked, "Mizuki", "starsealed_stacks", "EM"), 3)
        out["starsealed_want_stack_em"] = round(48.0 * stacks, 3)
    else:
        out["starsealed_const_em"] = None
        out["starsealed_stack_em"] = out["starsealed_want_stack_em"] = None

    return out


def _run_weapon_phase3_check() -> dict:
    """Weapon phase 3.

    Permanent: Azurelight / Aquila Favonia (ATK%), Elegy (EM), Sacrificial Bow.
    Conditional: Whitelake (stacks + 3-stack stellar crit), Finale Of The Deep,
    Breezeborne Refrain, Elegy for the End, New Bough, Silverdawn.
    """
    from characters import CHARACTER_BASE_STATS
    from stats_calc import build_initial_stats

    out = {}
    char_em = CHARACTER_BASE_STATS["Mizuki"]["em"][3]
    artifact_em = 160.0

    def init(weapon, refinement=1, char="Mizuki"):
        return build_initial_stats(char, 90, weapon, "2p/2p EM", {}, {},
                                   refinement=refinement)

    # --- 1. Permanent stats ---------------------------------------------------
    azure = init("Azurelight", 5)
    aquila = init("Aquila Favonia", 5)
    sac_bow = init("Sacrificial Bow", 1)
    elegy_weapon = init("Elegy for the End", 5)
    out["azurelight_atk_pct"] = round(azure["atk_percent"], 4)          # 0.48
    out["aquila_atk_pct"] = round(aquila["atk_percent"], 4)            # 0.40
    out["aquila_phys"] = round(aquila["physical_bonus"], 4)            # 0.413
    out["sacbow_er"] = round(sac_bow["er"] - 1.0, 4)                   # 0.306
    out["sacbow_atk_pct"] = round(sac_bow["atk_percent"], 4)           # 0.0
    out["elegy_weapon_em"] = round(elegy_weapon["em"] - char_em - artifact_em, 3)  # 120

    mizuki_base = {"constellation": 2, "level": 90, "refinement": 5,
                   "weapon": "Sacrificial Fragments", "artifact_set": "2p/2p EM",
                   "talents": "10/13/13"}
    aether_base = {"constellation": 0, "level": 90, "refinement": 1,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK",
                   "talents": "1/13/13"}

    # --- 2. Whitelake Frostfeather: 3 stacks (8s each) + stellar crit at 3 ----
    party = {
        "Mizuki": dict(mizuki_base, weapon="Whitelake Frostfeather"),
        "Aether": dict(aether_base),
    }
    field = FieldSequence("Field", "Mizuki", swap_out_time=10.0)
    field.add_ability(0.3, mizuki_skill)
    observer = FieldSequence("Observer", "Aether", swap_out_time=8.0)
    observer.add_ability(11.0, aether_n1)           # lands at ~21s, after 8s expiry
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="whitelake", end_mode="time", end_time=25.0,
                      rotations=[Rotation(name="r", sequences=[field, observer],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    out["whitlake_max_stacks"] = max((int(e.get("whitlake_stacks") or 0) for e in hits),
                                     default=0)
    late = [e for e in hits if e["global_time"] > 20.0]
    out["whitlake_expired"] = bool(late) and all(
        int(e.get("whitlake_stacks") or 0) == 0 for e in late)
    peak = next((e for e in hits if e.get("whitlake_max_state") == "ON"), None)
    if peak is not None:
        out["whitlake_stellar_cd"] = round(
            _flag_delta(t, peak, "Mizuki", "whitlake_max_state", "Stellar CD"), 4)
        out["whitlake_plain_cd"] = round(
            _flag_delta(t, peak, "Mizuki", "whitlake_max_state", "CD"), 6)
    else:
        out["whitlake_stellar_cd"] = out["whitlake_plain_cd"] = None

    # --- 3. Finale Of The Deep: 15s ATK% window ------------------------------
    # Sucrose's skill is a single standard skill hit, so the window start is exact
    # (a multi-tick skill would keep refreshing it).
    party = {
        "Sucrose": {"constellation": 6, "level": 90, "refinement": 5,
                    "weapon": "Finale Of The Deep", "artifact_set": "2p/2p EM",
                    "talents": "1/10/10"},
        "Aether": dict(aether_base),
    }
    skill_field = FieldSequence("Skill Field", "Sucrose", swap_out_time=1.259)
    skill_field.add_ability(0.5, sucrose_skill)
    watcher = FieldSequence("Watcher", "Aether", swap_out_time=18.0)
    watcher.add_ability(10.0, aether_n1)            # ~11.3s: inside the window
    watcher.add_ability(15.5, aether_n1)            # ~16.8s: past it
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="finale", end_mode="time", end_time=25.0,
                      rotations=[Rotation(name="r", sequences=[skill_field, watcher],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    finale_on = next((e for e in hits if e.get("finale_state") == "ON"), None)
    out["finale_on"] = finale_on is not None
    out["finale_opens_at_cast"] = (finale_on is not None
                                   and abs(finale_on["global_time"] - 0.5) < 1e-6)
    out["finale_atk_pct"] = (round(_flag_delta(t, finale_on, "Sucrose", "finale_state",
                                               "atk_percent"), 4) if finale_on else None)
    out["finale_alive_mid"] = any(e.get("finale_state") == "ON"
                                  for e in hits if 11.0 <= e["global_time"] <= 11.5)
    out["finale_expired"] = all(e.get("finale_state") != "ON"
                                for e in hits if e["global_time"] > 16.0)

    # --- 4. Breezeborne Refrain: 3 sigils -> party stellar_bonus 12s ----------
    party = {
        "Aether": dict(aether_base, weapon="Breezeborne Refrain", refinement=5),
        "Odette": {"constellation": 2, "level": 90, "refinement": 5,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK",
                   "talents": "1/13/13"},
    }
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="breezeborne", end_mode="time", end_time=20.0,
                      rotations=[Rotation(name="r", sequences=[aether_en1],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    breeze_on = next((e for e in hits if e.get("breezeborne_state") == "ON"), None)
    out["breezeborne_on"] = breeze_on is not None
    out["breezeborne_party_stellar"] = (
        round(_flag_delta(t, breeze_on, "Odette", "breezeborne_state", "Stellar Bonus"), 4)
        if breeze_on else None)
    out["breezeborne_no_sigils_while_on"] = all(
        int(e.get("breezeborne_sigils") or 0) == 0
        for e in hits if e.get("breezeborne_state") == "ON")

    # --- 5. Elegy for the End: 4 sigils -> party ATK% + EM, 20s lockout -------
    party = {
        "Aether": dict(aether_base, weapon="Elegy for the End", refinement=5),
        "Odette": {"constellation": 2, "level": 90, "refinement": 5,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK",
                   "talents": "1/13/13"},
    }
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="elegy", end_mode="time", end_time=30.0,
                      rotations=[Rotation(name="r",
                                          sequences=[presets.STANDARD_FIELD_SEQUENCES["Aether ECQ"]],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    elegy_on = next((e for e in hits if e.get("elegy_state") == "ON"), None)
    out["elegy_on"] = elegy_on is not None
    if elegy_on is not None:
        out["elegy_party_atk"] = round(
            _flag_delta(t, elegy_on, "Odette", "elegy_state", "atk_percent"), 4)
        out["elegy_party_em"] = round(_flag_delta(t, elegy_on, "Odette", "elegy_state", "EM"), 3)
        trigger = elegy_on["global_time"]
        out["elegy_lockout"] = all(
            int(e.get("elegy_sigils") or 0) == 0
            for e in hits if trigger <= e["global_time"] <= trigger + 20.0)
    else:
        out["elegy_party_atk"] = out["elegy_party_em"] = out["elegy_lockout"] = None

    # --- 6. New Bough: 1 stack/s ramp to 3 inside a 12s window ---------------
    party = {
        "Aether": dict(aether_base),
        "Odette": {"constellation": 2, "level": 90, "refinement": 5,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK",
                   "talents": "1/13/13"},
    }
    ramp = FieldSequence("Ramp", "Aether", swap_out_time=6.0)
    ramp.add_ability(0.0, aether_skill)
    for offset in (1.5, 2.5):
        ramp.add_ability(offset, aether_n1)
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="newbough", end_mode="time", end_time=14.0,
                      rotations=[Rotation(name="r", sequences=[ramp], repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    out["newbough_ramp"] = [int(e.get("newbough_stacks") or 0) for e in hits][:6]
    out["newbough_max"] = max((int(e.get("newbough_stacks") or 0) for e in hits), default=0)

    # --- 7. Silverdawn: 6s window extended by swirls / stellar hits ----------
    party = {
        "Sucrose": {"constellation": 6, "level": 90, "refinement": 5,
                    "weapon": "Silverdawn", "artifact_set": "2p/2p EM",
                    "talents": "1/10/10"},
        "Aether": dict(aether_base),
    }
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="silverdawn", end_mode="time", end_time=20.0,
                      rotations=[Rotation(name="r", sequences=[aether_en1, sucrose_eq],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    dawn_on = next((e for e in hits if e.get("silverdawn_state") == "ON"), None)
    out["silverdawn_on"] = dawn_on is not None
    out["silverdawn_max_ext"] = max((int(e.get("silverdawn_extensions") or 0) for e in hits),
                                    default=0)
    if dawn_on is not None:
        out["silverdawn_atk_pct"] = round(
            _flag_delta(t, dawn_on, "Sucrose", "silverdawn_state", "atk_percent"), 4)
        out["silverdawn_stellar_cd"] = round(
            _flag_delta(t, dawn_on, "Sucrose", "silverdawn_state", "Stellar CD"), 4)
        out["silverdawn_plain_cd"] = round(
            _flag_delta(t, dawn_on, "Sucrose", "silverdawn_state", "CD"), 6)
    else:
        out["silverdawn_atk_pct"] = out["silverdawn_stellar_cd"] = None
        out["silverdawn_plain_cd"] = None

    return out


def _run_artifact_stat_check() -> dict:
    """Artifact sets may grant ANY stat (element bonuses, stellar_bonus,
    skill/burst/charged_bonus, crit_*, er...).

    They must reach initial_stats (and the saved party JSON) and the damage
    formulas, but they must NOT be printed on the character card.
    """
    import artifacts
    from damage_calc import calculate_damage, calculate_stellar_damage, DEFAULT_ENEMY_STATS
    from abilities import aether_burst_enhanced

    probe = {
        "cryo_bonus": 0.20,
        "skill_bonus": 0.10,
        "burst_bonus": 0.15,
        "stellar_bonus": 0.30,
        "stellar_crit_dmg": 0.40,
        "crit_rate": 0.10,
        "er": 0.25,
    }
    out = {}
    artifacts.ARTIFACTS_BONUSES["__Probe Set__"] = dict(probe)
    try:
        stats = build_initial_stats("Aether", 90, "New Bough", "__Probe Set__", {}, {})
        final = compute_final_stats(dict(stats))
        card = compute_card_stats(stats)

        out["cryo_bonus"] = round(stats.get("cryo_bonus", 0.0), 4)
        out["skill_bonus"] = round(stats.get("skill_bonus", 0.0), 4)
        out["burst_bonus"] = round(stats.get("burst_bonus", 0.0), 4)
        out["stellar_bonus"] = round(stats.get("stellar_bonus", 0.0), 4)
        out["stellar_crit_dmg"] = round(stats.get("stellar_crit_dmg", 0.0), 4)
        out["crit_rate"] = round(stats.get("crit_rate", 0.0), 4)
        out["er"] = round(stats.get("er", 0.0), 4)

        # Card must stay clean: only the standard fields (+ element DMG lines).
        standard_card = {"HP", "ATK", "DEF", "EM", "CR", "CD", "CV", "ER"}
        out["card_leaks"] = sorted(k for k in card
                                   if k not in standard_card and not k.endswith(" DMG"))
        out["card_stellar"] = any("Stellar" in k for k in card)
        out["card_skill_burst"] = any(("Skill" in k or "Burst" in k) for k in card)

        # Standard damage routing: element bonus + the matching attack-type bonus.
        skill_hit = aether_skill.hits[0]            # Cryo, Skill, STANDARD
        cryo_burst_hit = sucrose_burst.hits[1]      # Cryo, Burst, STANDARD
        anemo_burst_hit = sucrose_burst.hits[0]     # Anemo, Burst, STANDARD
        std_skill = calculate_damage(skill_hit, final, DEFAULT_ENEMY_STATS)
        std_cryo_burst = calculate_damage(cryo_burst_hit, final, DEFAULT_ENEMY_STATS)
        std_anemo_burst = calculate_damage(anemo_burst_hit, final, DEFAULT_ENEMY_STATS)
        out["std_skill_mult"] = round(std_skill["bonus_mult"], 4)          # 1 + .20 + .10
        out["std_cryo_burst_mult"] = round(std_cryo_burst["bonus_mult"], 4)  # 1 + .20 + .15
        out["std_anemo_burst_mult"] = round(std_anemo_burst["bonus_mult"], 4)  # 1 + .15
        # Standard crit must NOT contain the stellar crit dmg.
        out["std_crit_absolute"] = round(std_skill["crit_mult_absolute"], 6)
        out["std_crit_expected"] = round(1.0 + final.get("CD", 0.5), 6)

        # Stellar routing: only stellar_bonus / stellar crit apply.
        stellar_hit = next(h for h in aether_burst_enhanced.hits if h.category == ActionCategory.STELLAR_DMG)
        stellar = calculate_stellar_damage(stellar_hit, final, DEFAULT_ENEMY_STATS)
        zeroed = dict(final)
        for key in ("cryo_bonus", "skill_bonus", "burst_bonus"):
            zeroed[key] = 0.0
        stellar_zeroed = calculate_stellar_damage(stellar_hit, zeroed, DEFAULT_ENEMY_STATS)
        no_stellar = dict(final)
        no_stellar["stellar_bonus"] = 0.0
        stellar_without_bonus = calculate_stellar_damage(stellar_hit, no_stellar, DEFAULT_ENEMY_STATS)
        out["stellar_ignores_std"] = abs(stellar["bonus_mult"] - stellar_zeroed["bonus_mult"]) < 1e-12
        out["stellar_uses_bonus"] = stellar["bonus_mult"] > stellar_without_bonus["bonus_mult"] + 1e-9
        out["stellar_cd"] = round(final.get("Stellar CD", 0.0), 4)         # 0.40

        # Real sets that used to lose their permanent stats.
        vv = build_initial_stats("Faruzan", 90, "Favonius Warbow", "Viridescent Venerer", {}, {})
        noblesse = build_initial_stats("Faruzan", 90, "Favonius Warbow", "Noblesse Oblige", {}, {})
        out["vv_anemo"] = round(vv.get("anemo_bonus", 0.0), 4)             # 0.15
        out["vv_stellar"] = round(vv.get("stellar_bonus", 0.0), 4)         # 0.20
        out["noblesse_burst"] = round(noblesse.get("burst_bonus", 0.0), 4)  # 0.20
    finally:
        artifacts.ARTIFACTS_BONUSES.pop("__Probe Set__", None)

    return out


def _run_artifact_phase1_check() -> dict:
    """Artifact set buffs, phase 1: Instructor, Gilded Dreams, Noblesse Oblige,
    Tenacity, A Day Carved From Rising Winds, Scarlet Proof, New Tsaritsa set."""
    from abilities import sucrose_e

    out = {}
    aether = {"constellation": 0, "level": 90, "refinement": 1,
              "weapon": "New Bough", "artifact_set": "2p/2p ATK", "talents": "1/13/13"}
    odette = {"constellation": 2, "level": 90, "refinement": 1,
              "weapon": "New Bough", "artifact_set": "2p/2p ATK", "talents": "1/13/13"}
    faruzan = {"constellation": 6, "level": 90, "refinement": 1,
               "weapon": "Favonius Warbow", "artifact_set": "2p/2p EM", "talents": "1/13/13"}
    sucrose = {"constellation": 6, "level": 90, "refinement": 1,
               "weapon": "Sacrificial Fragments", "artifact_set": "2p/2p EM", "talents": "1/10/10"}
    mizuki = {"constellation": 2, "level": 90, "refinement": 5,
              "weapon": "Sacrificial Fragments", "artifact_set": "2p/2p EM",
              "talents": "10/13/13"}

    def observer(offsets, swap_out=16.0):
        seq = FieldSequence("Observer", "Aether", swap_out_time=swap_out)
        for offset in offsets:
            seq.add_ability(offset, aether_n1)
        return seq

    # --- 1. Instructor: on-field swirl only, 8s -------------------------------
    party = {"Sucrose": dict(sucrose, artifact_set="Instructor"), "Aether": dict(aether)}
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="instructor", end_mode="time", end_time=20.0,
                      rotations=[Rotation(name="r",
                                          sequences=[aether_en1, sucrose_e, observer([10.5])],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    ins_on = next((e for e in hits if e.get("instructor_state") == "ON"), None)
    out["instructor_on"] = ins_on is not None
    # Measured on the HOLDER: the buff is party-wide (she gets it too) and, unlike an
    # ally, her own EM has no Sucrose-A4 self-share to ripple through the comparison.
    out["instructor_em"] = (round(_flag_delta(t, ins_on, "Sucrose", "instructor_state", "EM"), 3)
                            if ins_on else None)
    # Her off-field burst swirls must NOT refresh, and the window is 8s, so the
    # observer hit at ~12.9s has to be OFF.
    out["instructor_off_late"] = all(e.get("instructor_state") != "ON"
                                     for e in hits if e["global_time"] > 12.0)

    # --- 2. Gilded Dreams: 8s composition buff, 8s CD -------------------------
    party = {
        "Sucrose": dict(sucrose, artifact_set="Gilded Dreams"),   # Anemo holder
        "Aether": dict(aether),                                    # Cryo
        "Odette": dict(odette),                                    # Cryo
        "Faruzan": dict(faruzan),                                  # Anemo (same, 1)
    }
    watcher = FieldSequence("Watcher", "Aether", swap_out_time=14.0)
    watcher.add_ability(7.0, aether_n1)      # ~9.5s: inside the 8s window
    watcher.add_ability(9.0, aether_n1)      # ~11.5s: past it
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="gilded", end_mode="time", end_time=20.0,
                      rotations=[Rotation(name="r",
                                          sequences=[aether_en1, sucrose_e, watcher],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    gilded_on = next((e for e in hits if e.get("gilded_state") == "ON"), None)
    out["gilded_on"] = gilded_on is not None
    out["gilded_atk"] = (round(_flag_delta(t, gilded_on, "Sucrose", "gilded_state", "atk_percent"), 4)
                         if gilded_on else None)
    out["gilded_em"] = (round(_flag_delta(t, gilded_on, "Sucrose", "gilded_state", "EM"), 3)
                        if gilded_on else None)
    out["gilded_alive_mid"] = any(e.get("gilded_state") == "ON"
                                  for e in hits if 9.0 <= e["global_time"] <= 9.8)
    out["gilded_off_late"] = all(e.get("gilded_state") != "ON"
                                 for e in hits if e["global_time"] > 11.0)

    # --- 3. Noblesse Oblige: burst CAST only, party ATK% 12s ------------------
    party = {"Sucrose": dict(sucrose, artifact_set="Noblesse Oblige"), "Aether": dict(aether)}
    burst_field = FieldSequence("Burst Field", "Sucrose", swap_out_time=1.2)
    burst_field.add_ability(0.5, sucrose_burst)
    watcher = FieldSequence("Watcher", "Aether", swap_out_time=16.0)
    watcher.add_ability(11.0, aether_n1)     # ~12.7s: inside the 12s window
    watcher.add_ability(13.0, aether_n1)     # ~14.7s: past it
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="noblesse", end_mode="time", end_time=20.0,
                      rotations=[Rotation(name="r", sequences=[burst_field, watcher],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    nob_on = next((e for e in hits if e.get("noblesse_state") == "ON"), None)
    out["noblesse_on"] = nob_on is not None
    out["noblesse_atk"] = (round(_flag_delta(t, nob_on, "Aether", "noblesse_state", "atk_percent"), 4)
                           if nob_on else None)
    # Only the CAST arms it: mid-burst ticks must not extend the 12s window.
    out["noblesse_off_late"] = all(e.get("noblesse_state") != "ON"
                                   for e in hits if e["global_time"] > 14.0)

    # --- 4. Tenacity: standard skill hit -> party ATK% 3s ---------------------
    party = {"Sucrose": dict(sucrose, artifact_set="Tenacity Of The Millelith"),
             "Aether": dict(aether)}
    skill_field = FieldSequence("Skill Field", "Sucrose", swap_out_time=1.0)
    skill_field.add_ability(0.5, sucrose_skill)
    watcher = FieldSequence("Watcher", "Aether", swap_out_time=6.0)
    watcher.add_ability(2.0, aether_n1)       # 3.0s: inside the 3s window
    watcher.add_ability(3.0, aether_n1)       # 4.0s: past it
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="tenacity", end_mode="time", end_time=12.0,
                      rotations=[Rotation(name="r", sequences=[skill_field, watcher],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    ten_on = next((e for e in hits if e.get("tenacity_state") == "ON"), None)
    out["tenacity_on"] = ten_on is not None
    out["tenacity_atk"] = (round(_flag_delta(t, ten_on, "Aether", "tenacity_state", "atk_percent"), 4)
                           if ten_on else None)
    out["tenacity_alive_mid"] = any(e.get("tenacity_state") == "ON"
                                    for e in hits if 2.9 <= e["global_time"] <= 3.1)
    out["tenacity_off_late"] = all(e.get("tenacity_state") != "ON"
                                   for e in hits if e["global_time"] > 4.0)

    # --- 5. A Day Carved From Rising Winds: holder-only ATK% 6s ---------------
    #     The FIRST skill hit arms the window and must NOT benefit from it; a later
    #     holder hit inside the window gets the ATK%, other members never do.
    party = {"Sucrose": dict(sucrose, artifact_set="A Day Carved From Rising Winds"),
             "Aether": dict(aether)}
    skill_field = FieldSequence("Skill Field", "Sucrose", swap_out_time=3.0)
    skill_field.add_ability(0.5, sucrose_skill)          # 0.5s: arms the 6s window
    skill_field.add_ability(2.0, sucrose_burst)          # 2.5s: her next hit, inside it
    watcher = FieldSequence("Watcher", "Aether", swap_out_time=2.0)
    watcher.add_ability(0.5, aether_n1)                  # 3.5s: a non-holder hit
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="risingwinds", end_mode="time", end_time=12.0,
                      rotations=[Rotation(name="r",
                                          sequences=[skill_field, watcher],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    rw_trig = next((e for e in hits if abs(e["global_time"] - 0.5) < 0.06), None)
    out["risingwinds_trigger_off"] = (rw_trig is not None
                                      and rw_trig.get("risingwinds_state") != "ON")
    rw_on = next((e for e in hits if e.get("risingwinds_state") == "ON"), None)
    out["risingwinds_on"] = rw_on is not None
    out["risingwinds_atk"] = (round(_flag_delta(t, rw_on, "Sucrose", "risingwinds_state",
                                                "atk_percent"), 4) if rw_on else None)
    out["risingwinds_not_party"] = (round(_flag_delta(t, rw_on, "Aether", "risingwinds_state",
                                                      "atk_percent"), 4) if rw_on else None)

    # --- 6. Scarlet Proof: on-field swirl -> holder crit + stellar, 10s -------
    party = {"Sucrose": dict(sucrose, artifact_set="Scarlet Proof"), "Aether": dict(aether)}
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="scarlet", end_mode="time", end_time=16.0,
                      rotations=[Rotation(name="r", sequences=[aether_en1, sucrose_e],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    sc_on = next((e for e in hits if e.get("scarlet_state") == "ON"), None)
    out["scarlet_on"] = sc_on is not None
    out["scarlet_cr"] = (round(_flag_delta(t, sc_on, "Sucrose", "scarlet_state", "CR"), 4)
                         if sc_on else None)
    out["scarlet_stellar"] = (round(_flag_delta(t, sc_on, "Sucrose", "scarlet_state",
                                                "Stellar Bonus"), 4) if sc_on else None)

    # --- 7a. New Tsaritsa set: stacks (Aether, Cryo) ---------------------------
    party = {"Aether": dict(aether, artifact_set="New Tsaritsa set"), "Odette": dict(odette)}
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="tsaritsa", end_mode="time", end_time=8.0,
                      rotations=[Rotation(name="r", sequences=[aether_en1], repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    out["tsaritsa_max_stacks"] = max((int(e.get("tsaritsa_stacks") or 0) for e in hits), default=0)
    ts_on = next((e for e in hits if e.get("tsaritsa_state") == "ON"), None)
    out["tsaritsa_cr"] = (round(_flag_delta(t, ts_on, "Aether", "tsaritsa_state", "CR"), 4)
                          if ts_on else None)
    out["tsaritsa_stellar_cr"] = (round(_flag_delta(t, ts_on, "Aether", "tsaritsa_stellar_state",
                                                    "Stellar CR"), 4) if ts_on else None)

    # --- 7b. Tsaritsa element gate + 3s on-field decay (Mizuki, Anemo) --------
    party = {"Mizuki": dict(mizuki, artifact_set="New Tsaritsa set"),
             "Aether": dict(aether)}
    field = FieldSequence("Field", "Mizuki", swap_out_time=10.0)
    field.add_ability(0.3, mizuki_skill)
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="tsaritsa_anemo", end_mode="time", end_time=14.0,
                      rotations=[Rotation(name="r", sequences=[field], repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    out["tsaritsa_anemo_cr_flag"] = any(e.get("tsaritsa_state") == "ON" for e in hits)
    out["tsaritsa_stacks_early"] = next((int(e.get("tsaritsa_stacks") or 0)
                                         for e in hits if e["global_time"] < 3.0), None)
    out["tsaritsa_stacks_decayed"] = all(int(e.get("tsaritsa_stacks") or 0) == 0
                                         for e in hits if e["global_time"] > 4.0)

    return out


def _run_odette_burst_check() -> dict:
    """Odette's "Snow Swan's Dream": self-only stellar_bonus, talent-scaled, 20s
    from her BURST CAST hit and refreshed by a new cast."""
    from abilities import odette_burst
    out = {}
    party = {
        "Odette": {"constellation": 2, "level": 90, "refinement": 1,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK", "talents": "1/13/13"},
        "Aether": {"constellation": 0, "level": 90, "refinement": 1,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK", "talents": "1/13/13"},
    }
    burst_field = FieldSequence("Odette Burst", "Odette", swap_out_time=2.0)
    burst_field.add_ability(0.5, odette_burst)
    watcher = FieldSequence("Watcher", "Aether", swap_out_time=22.0)
    watcher.add_ability(13.5, aether_n1)      # ~15.5s: inside the 20s window
    watcher.add_ability(19.5, aether_n1)      # ~21.5s: past it
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="odette_burst", end_mode="time", end_time=26.0,
                      rotations=[Rotation(name="r", sequences=[burst_field, watcher],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    on = [e for e in hits if e.get("odette_burst_state") == "ON"]
    out["on"] = bool(on)
    out["alive_at_15s"] = any(e["global_time"] > 15.0 for e in on)
    out["off_after_20s"] = all(e.get("odette_burst_state") != "ON"
                               for e in hits if e["global_time"] > 21.0)
    if on:
        out["stellar"] = round(_flag_delta(t, on[0], "Odette", "odette_burst_state",
                                           "Stellar Bonus"), 4)
        out["not_party"] = round(_flag_delta(t, on[0], "Aether", "odette_burst_state",
                                             "Stellar Bonus"), 4)
    else:
        out["stellar"] = out["not_party"] = None
    return out


def _run_mizuki_c2_check() -> dict:
    """Mizuki C2: PHEC bonus from her FLAT EM + anemo/PHEC shreds while in DDS."""
    out = {}
    for const in (1, 2):
        party = copy.deepcopy(presets.DEFAULT_PARTY)
        party["Mizuki"]["constellation"] = const
        t = RotationTimeline(party=party)
        t.add_trial(presets.TEST_TRIAL_30S)
        t.evaluate_timeline()
        events = [e for e in t.global_events
                  if e.get("event_type") == "HIT"
                  and e.get("character") == "Mizuki"
                  and e.get("dreamdrifter_state") == "ON"
                  and e.get("mizuki_a4_state") == "ON"]
        ev = events[-1]
        flat = compute_flat_em("Mizuki", ev, ev.get("active_character"),
                               t.party, t.char_initial_stats_map)
        out[f"flat_em_{const}"] = round(flat, 3)
        # The C2 descriptors are dispatched by the dreamdrifter_state flag, so that is
        # the flag to toggle: cryo_bonus comes only from "Mizuki C2 Cryo" and the
        # shreds only from "Mizuki C2" inside that window.
        out[f"cryo_bonus_{const}"] = round(
            _flag_delta(t, ev, "Mizuki", "dreamdrifter_state", "Cryo Bonus"), 6)
        out[f"anemo_shred_{const}"] = round(
            _flag_delta(t, ev, "Mizuki", "dreamdrifter_state", "anemo_shred"), 4)
        out[f"cryo_shred_{const}"] = round(
            _flag_delta(t, ev, "Mizuki", "dreamdrifter_state", "cryo_shred"), 4)
    return out


def _run_cryo_resonance_check() -> dict:
    """Cryo Resonance: +15% CR only with a Cryo-affected enemy AND 2+ Cryo chars.

    The aura must ALREADY be on the enemy when the hit lands, so the hit that
    applies Cryo from a clean enemy is flagged OFF and the next hit is ON.
    """
    out = {}
    two_cryo = {
        "Aether": {"constellation": 0, "level": 90, "refinement": 1,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK", "talents": "1/13/13"},
        "Odette": {"constellation": 2, "level": 90, "refinement": 1,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK", "talents": "1/13/13"},
    }
    one_cryo = {
        "Aether": two_cryo["Aether"],
        "Sucrose": {"constellation": 6, "level": 90, "refinement": 1,
                    "weapon": "Sacrificial Fragments", "artifact_set": "2p/2p EM",
                    "talents": "1/10/10"},
    }
    for key, party in (("two", two_cryo), ("one", one_cryo)):
        t = RotationTimeline(party=party)
        t.add_trial(Trial(name=f"res_{key}", end_mode="time", end_time=10.0,
                          rotations=[Rotation(name="r", sequences=[aether_en1],
                                              repetitions=1)]))
        t.evaluate_timeline()
        hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
        ev = next((e for e in hits if e.get("cryo_resonance_state") == "ON"), None)
        out[f"{key}_on"] = ev is not None
        out[f"{key}_cr"] = (round(_flag_delta(t, ev, "Aether", "cryo_resonance_state", "CR"), 4)
                            if ev is not None else None)

        # The first Cryo hit of the run CREATES the aura: it must be OFF, and the hit
        # right after it (aura already there) must be ON.
        first_cryo = next((e for e in hits
                           if e.get("element") == "Cryo" and e.get("character") == "Aether"), None)
        out[f"{key}_first_cryo_state"] = (first_cryo.get("cryo_resonance_state")
                                          if first_cryo is not None else None)
        # The Aura column reports the state the hit RESOLVED AGAINST, so the applying
        # hit shows the old (empty) aura and only the next row shows the new one.
        out[f"{key}_first_aura"] = (first_cryo.get("cryo_aura") if first_cryo is not None else None)
        out[f"{key}_first_aura_after"] = (first_cryo.get("cryo_aura_after")
                                          if first_cryo is not None else None)
        later = [e for e in hits if first_cryo is not None
                 and e["global_time"] > first_cryo["global_time"]]
        out[f"{key}_later_on"] = any(e.get("cryo_resonance_state") == "ON" for e in later)
        out[f"{key}_later_aura"] = (later[0].get("cryo_aura") if later else None)
    return out


def _run_rv_mode_check() -> dict:
    """100% RV / KQM standard: crit is ONE Crit Value, not 1 + CR*CD.

    Uses the preset "Test Aether" trial (the one the UI offers) so the check runs
    through the same path as a real simulation:
      * the party entry carries `rv_mode`,
      * crit_mult == cv - 1 (CV > 4) instead of 1 + CR*CD,
      * the aura-applying hit has no Cryo Resonance (see the resonance check),
      * a swirl reaction with all-RV contributors has no crit variance left.
    """
    out = {}
    slots = [dict(data, character=name,
                  standard_mode=("100% RV (Crit Value)" if name == "Aether" else "Manual"))
             for name, data in presets.DEFAULT_PARTY.items()]
    party = build_io.assemble_party(slots)
    out["entry_flag"] = bool(party["Aether"].get("rv_mode"))
    out["manual_entry_flag"] = bool(party["Mizuki"].get("rv_mode"))
    # Hand-written / legacy entries only carry the UI label.
    out["kqm_label"] = bool(is_rv_mode({"standard_mode": "KQM Standards (40 rolls)"}))
    out["manual_label"] = bool(is_rv_mode({"standard_mode": "Manual"}))
    out["empty_entry"] = bool(is_rv_mode({}))

    # The UI rebuilds the party from the WIDGET state right before a run, so
    # collect_slot() -> assemble_party() must preserve the standard (that path stores
    # the label under `substat_standard`, not `standard_mode`).
    widget_state = {
        "char_1": "Aether", "level_1": 90, "const_1": 6, "weapon_1": "New Bough",
        "ref_1": 1, "talents_1": "1/13/13", "std_1": "100% RV (Crit Value)",
        "art_set_1": "2p/2p ATK",
    }
    widget_slot = build_io.collect_slot(widget_state, 1)
    out["collect_standard"] = widget_slot.get("substat_standard")
    out["collect_rv"] = bool((build_io.assemble_party([widget_slot]).get("Aether") or {}).get("rv_mode"))
    out["summary"] = build_io.party_rv_summary(party)

    t = RotationTimeline(party=party)
    t.add_trial(presets.STANDARD_TRIALS["Test Aether"])
    t.evaluate_timeline()
    hits = [e for e in t.global_events
            if e.get("event_type") == "HIT" and e.get("character") == "Aether"]
    out["hits"] = len(hits)
    for idx, ev in enumerate(hits[:2]):
        cv = 2.0 * (ev.get("stat_cr") or 0.0) + (ev.get("stat_cd") or 0.0)
        out[f"cv_{idx}"] = round(cv, 4)
        out[f"mult_{idx}"] = round(ev.get("crit_mult_avg") or 0.0, 4)
        out[f"expected_{idx}"] = round(crit_mult_from_crit_value(
            ev.get("stat_cr") or 0.0, ev.get("stat_cd") or 0.0), 4)
        out[f"manual_{idx}"] = round(1.0 + (ev.get("stat_cr") or 0.0) * (ev.get("stat_cd") or 0.0), 4)
        out[f"flag_{idx}"] = bool(ev.get("rv_mode"))
        out[f"reso_{idx}"] = ev.get("cryo_resonance_state")

    # Reaction path: with every contributor in RV mode nothing is random any more.
    def swirl_events(rv):
        p = {name: dict(data, standard_mode=("100% RV (Crit Value)" if rv else "Manual"),
                        rv_mode=rv)
             for name, data in presets.DEFAULT_PARTY.items()}
        tl = RotationTimeline(party=p)
        tl.add_trial(presets.TEST_TRIAL_30S)
        tl.evaluate_timeline()
        return [e for e in tl.global_events if e.get("hit_name") == "Stellar_Swirl_Hit"]

    rv_swirls = swirl_events(True)
    man_swirls = swirl_events(False)
    out["swirls"] = len(rv_swirls)
    out["rv_deterministic"] = bool(rv_swirls) and all(
        abs((e.get("average_damage") or 0.0) - (e.get("non_crit") or 0.0)) < 1e-6
        and abs((e.get("crit_damage") or 0.0) - (e.get("non_crit") or 0.0)) < 1e-6
        for e in rv_swirls)
    out["manual_has_variance"] = any(
        abs((e.get("average_damage") or 0.0) - (e.get("non_crit") or 0.0)) > 1e-6
        for e in man_swirls)
    return out


def _run_buff_catalogue_check() -> dict:
    """Structural integrity of the buff catalogue (buffs.py) vs its dispatch table.

    Catches the class of bug we hit before: a catalogue entry that no timeline
    flag can ever reach (dead data), a dispatch key that no longer exists, and a
    non-constant descriptor that the basis engine could not resolve.

    Note: every REACHABLE non-constant entry is also exercised numerically by the
    other checks in this file (Mizuki swirl/VBTD/C6/C2, Odette burst+A4+jubilee,
    Aether A4+jubilee, Faruzan C6 anemo bonus, Sucrose A4 share), so a wrong
    skill_scalings path would already fail there.
    """
    import buffs
    import stats_calc

    tables = {
        "constant": buffs.CONDITIONAL_CONSTANT_BUFFS,
        "non_constant": buffs.CONDITIONAL_NON_CONSTANT_BUFFS,
        "stack": buffs.STACK_BUFFS,
    }

    referenced = set()
    missing = []
    for flag, descriptors in stats_calc.FLAG_TO_BUFFS.items():
        for desc in descriptors:
            table = tables.get(desc["type"])
            if table is None:
                missing.append(f"{flag}: unknown type {desc['type']!r}")
            elif desc["key"] in table:
                referenced.add(desc["key"])
            elif (desc["type"] == "stack"
                  and desc["key"] in buffs.CONDITIONAL_NON_CONSTANT_BUFFS):
                # Basis-scaled per-stack effect (e.g. Wandering Evenstar): the
                # per-stack value comes from the dynamic table, not STACK_BUFFS.
                referenced.add(desc["key"])
            else:
                missing.append(f"{flag}: key {desc['key']!r} missing from the "
                               f"{desc['type']} table")

    unreachable = [
        key for table in tables.values() for key in table
        if key not in referenced and key not in buffs.DORMANT
    ]

    malformed = []
    for key, desc in buffs.CONDITIONAL_NON_CONSTANT_BUFFS.items():
        if not desc.get("target_stat"):
            malformed.append(f"{key}: missing target_stat")
        basis = desc.get("basis", "em")
        if basis not in stats_calc.BASIS_NAMES:
            malformed.append(f"{key}: unknown basis {basis!r}")
        elif basis == "talent":
            if "path" not in desc:
                malformed.append(f"{key}: basis 'talent' needs a path")
        elif "ratio" not in desc and "ratio_from_talent" not in desc:
            malformed.append(f"{key}: needs ratio or ratio_from_talent")

    return {
        "missing": missing,
        "unreachable": unreachable,
        "malformed": malformed,
        "referenced": len(referenced),
        "dormant": len(buffs.DORMANT),
        "catalogue": sum(len(table) for table in tables.values()),
    }


def _anastasya_party() -> dict:
    """Party used by the Anastasya checks: she replaces Aether in rotation A."""
    return {
        "Mizuki": {"constellation": 2, "level": 90, "refinement": 5,
                   "weapon": "Sacrificial Fragments", "artifact_set": "2p/2p EM",
                   "talents": "10/13/13"},
        "Anastasya": {"constellation": 0, "level": 90, "refinement": 1,
                      "weapon": "Favonius Warbow", "artifact_set": "2p/2p ATK",
                      "talents": "1/13/13"},
        "Faruzan": {"constellation": 6, "level": 90, "refinement": 1,
                    "weapon": "Favonius Warbow", "artifact_set": "Instructor",
                    "talents": "1/13/13"},
        "Odette": {"constellation": 0, "level": 90, "refinement": 1,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK",
                   "talents": "1/13/13"},
    }


def _vortex_swirl_counts(events) -> list:
    """(time, action, swirls_since_previous_vortex_event) for every vortex event."""
    out = []
    n = 0
    for e in events:
        if e.get("event_type") != "HIT":
            continue
        if e.get("hit_name") == "Stellar_Swirl_Hit":
            n += 1
        elif "Vortex" in str(e.get("hit_name")):
            out.append((round(e["global_time"], 3), e.get("action"), n))
            n = 0
    return out


def _run_anastasya_check() -> dict:
    """Anastasya kit semantics (rotation A + isolated windows/mechanics).

    Covers: party-wide talent-scaled burst stellar_bonus (20s), A1 crit DMG for the
    OTHERS only (19s), her Jubilee passive, the A4 reaction-only jubilee, the A4
    vortex lifecycle (spawn at Lv2, 3 further swirls to detonate), the conditional
    extra stellar beat while the burst is up, and Triumph's 18s arming rule.
    """
    from abilities import anastasya_burst
    from damage_calc import calculate_damage

    out = {}

    timeline = RotationTimeline(party=_anastasya_party())
    timeline.add_trial(presets.STANDARD_TRIALS["Mizuki Sac Frag Pull out 6x rotations (Anastasya)"])
    timeline.evaluate_timeline()
    hits = [e for e in timeline.global_events if e.get("event_type") == "HIT"]
    out["total"] = round(sum((e.get("average_damage", 0.0) or 0.0) for e in hits), 1)

    # ---- 1. Burst: party stellar_bonus, talent-scaled, 20s refreshed window ----
    casts = [e["global_time"] for e in hits
             if e.get("ability_name") == "To the New World"
             and e.get("hit_name") == "Burst_Cast"]
    burst_hits = [e for e in hits if e.get("anastasya_burst_state") == "ON"]
    out["burst_casts"] = len(casts)
    out["burst_on"] = bool(burst_hits)
    if burst_hits and casts:
        ev = burst_hits[len(burst_hits) // 2]
        out["burst_bonus_ally"] = round(
            _flag_delta(timeline, ev, "Mizuki", "anastasya_burst_state", "Stellar Bonus"), 4)
        out["burst_bonus_self"] = round(
            _flag_delta(timeline, ev, "Anastasya", "anastasya_burst_state", "Stellar Bonus"), 4)
        out["burst_offenders"] = sum(
            1 for e in burst_hits
            if e["global_time"] > max([c for c in casts if c <= e["global_time"]],
                                      default=-1e9) + 20.0 + 1e-6)
    else:
        out["burst_bonus_ally"] = out["burst_bonus_self"] = None
        out["burst_offenders"] = -1

    # ---- 2. A1: +16% crit DMG to the OTHERS, 19s refreshed window ----
    skill_casts = [e["global_time"] for e in hits
                   if e.get("ability_name") == "Skill Tap" and e.get("hit_name") == "Cast"]
    a1_hits = [e for e in hits if e.get("anastasya_a1_state") == "ON"]
    out["a1_on"] = bool(a1_hits)
    if a1_hits:
        out["a1_cd_ally"] = round(
            _flag_delta(timeline, a1_hits[0], "Mizuki", "anastasya_a1_state", "CD"), 4)
        out["a1_cd_self"] = round(
            _flag_delta(timeline, a1_hits[0], "Anastasya", "anastasya_a1_state", "CD"), 4)
        out["a1_offenders"] = sum(
            1 for e in a1_hits
            if e["global_time"] > max([c for c in skill_casts if c <= e["global_time"]],
                                      default=-1e9) + 19.0 + 1e-6)
    else:
        out["a1_cd_ally"] = out["a1_cd_self"] = None
        out["a1_offenders"] = -1

    # ---- 3. A4: reaction-only jubilee exists with her, absent without her ----
    swirl_ev = next((e for e in hits if e.get("hit_name") == "Stellar_Swirl_Hit"), None)
    out["swirl_found"] = swirl_ev is not None
    if swirl_ev is not None:
        owner = swirl_ev.get("character")
        fs = _buffed_stats(timeline, swirl_ev, owner)
        out["reaction_jubilee"] = round(fs.get("reaction_jubilee_mult", 0.0), 4)
        # Stellar (non-reaction) damage must NOT see the A4 multiplier: a plain
        # stellar hit's bonus_mult stays (1+jubilee)*(1+em_bonus+stellar_bonus).
        stellar_ev = next((e for e in hits
                           if e.get("category") == ActionCategory.STELLAR_DMG
                           and e.get("character") == "Odette"), None)
        if stellar_ev is not None:
            s_fs = _buffed_stats(timeline, stellar_ev, "Odette")
            em = s_fs.get("EM", 0.0)
            expected = ((1.0 + s_fs.get("jubilee_mult", 0.0))
                        * (1.0 + (6.0 * em) / (2000.0 + em)
                           + s_fs.get("stellar_bonus", 0.0)))
            out["stellar_bonus_mult_ok"] = (
                abs((stellar_ev.get("bonus_mult") or 0.0) - expected) <= 1e-9)
        else:
            out["stellar_bonus_mult_ok"] = False
        # Stellar REACTION damage moves by exactly the A4 factor.
        party_dict = {}
        for name in ("Mizuki", "Anastasya", "Odette", "Faruzan"):
            st = _buffed_stats(timeline, swirl_ev, name)
            party_dict[name] = {"level": 90, "EM": st.get("EM", 0.0),
                                "CR": st.get("CR", 0.05), "CD": st.get("CD", 0.5)}
        on = calculate_damage(swirl_ev, fs, timeline.enemy_stats, party_dict=party_dict)
        fs_off = dict(fs)
        fs_off.pop("reaction_jubilee_mult", None)
        off = calculate_damage(swirl_ev, fs_off, timeline.enemy_stats, party_dict=party_dict)
        ratio = (off["average_damage"] / on["average_damage"]) if on["average_damage"] else 0.0
        jub = fs.get("jubilee_mult", 0.0)
        out["reaction_ratio_err"] = round(
            abs(ratio - (1.0 + jub) / (1.0 + jub + 0.15)), 12)
    # ---- 4. Jubilee passive: 0.007% of HER ATK (cap 14%) for the party ----
    def _jubilee(members):
        tl = RotationTimeline(party=members)
        tl.add_trial(Trial(name="jub", end_mode="time", end_time=6.0,
                           rotations=[Rotation(
                               name="r",
                               sequences=[presets.STANDARD_FIELD_SEQUENCES["Mizuki E (Pullout)"]],
                               repetitions=1)]))
        tl.evaluate_timeline()
        ev = next(e for e in tl.global_events if e.get("event_type") == "HIT")
        return tl, ev

    full = _anastasya_party()
    base = {k: v for k, v in full.items() if k in ("Mizuki", "Faruzan")}
    t_no, ev_no = _jubilee(base)
    t_yes, ev_yes = _jubilee({**base, "Anastasya": full["Anastasya"]})
    j_no = _buffed_stats(t_no, ev_no, "Mizuki").get("jubilee_mult", 0.0)
    j_yes = _buffed_stats(t_yes, ev_yes, "Mizuki").get("jubilee_mult", 0.0)
    init = t_yes.char_initial_stats_map.get("Anastasya", {})
    ana_atk = (init.get("base_atk", 0.0) * (1.0 + init.get("atk_percent", 0.0))
               + init.get("atk_flat", 0.0))
    out["jubilee_share"] = round(j_yes - j_no, 6)
    out["jubilee_expected"] = round(min(0.00007 * ana_atk, 0.14), 6)
    out["jubilee_off_without_her"] = abs(j_no) <= 1e-12
    out["reaction_jubilee_without_her"] = round(
        _buffed_stats(t_no, ev_no, "Mizuki").get("reaction_jubilee_mult", 0.0), 4)

    # ---- 5. A4 vortex lifecycle: spawn at Lv2, 3 further swirls to detonate ----
    seq = _vortex_swirl_counts(timeline.global_events)
    out["vortex_events"] = len(seq)
    out["vortex_all_lv2"] = all("Lv2" in str(a) for _t, a, _n in seq) if seq else False
    early = [(t, n) for t, a, n in seq if "Early" in str(a)]
    out["early_count"] = len(early)
    out["early_swirls"] = sorted({n for _t, n in early})
    # Baseline (no A4): 6 swirls from spawn to an early detonation.
    t_base = RotationTimeline(party=presets.DEFAULT_PARTY)
    t_base.add_trial(presets.STANDARD_TRIALS["Mizuki Sac Frag Pull out 6x rotations"])
    t_base.evaluate_timeline()
    out["baseline_early_swirls"] = sorted({
        n for _t, a, n in _vortex_swirl_counts(t_base.global_events)
        if "Early" in str(a)})

    # ---- 6. Conditional extra stellar beat (only while the burst is up) ----
    extra = [e for e in hits if e.get("hit_name") == "Palestar Crown Extra Stellar"]
    beats = [e for e in hits
             if str(e.get("hit_name", "")).startswith("Palestar Crown Stellar")]
    out["extra_count"] = len(extra)
    out["extra_only_in_window"] = all(e.get("anastasya_burst_state") == "ON"
                                      for e in extra)
    out["extras_never_exceed_beats"] = len(extra) <= len(beats)
    out["no_extra_before_first_burst"] = bool(beats) and bool(casts) and not any(
        e["global_time"] < min(casts) for e in extra)

    # ---- 7. Triumph: armed by the burst, fires on the next swap-in >= 18s ----
    fill = FieldSequence("Filler", "Aether", swap_out_time=10.0)
    fill.add_ability(0.5, aether_n1)
    burst_seq = FieldSequence("AnaBurst", "Anastasya", swap_out_time=2.941)
    burst_seq.add_ability(2.371, anastasya_burst)
    t_tr = RotationTimeline(party={
        "Anastasya": {"constellation": 0, "level": 90, "refinement": 1,
                      "weapon": "Favonius Warbow", "artifact_set": "2p/2p ATK",
                      "talents": "1/13/13"},
        "Aether": {"constellation": 0, "level": 90, "refinement": 1,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK",
                   "talents": "1/13/13"},
    })
    t_tr.add_trial(Trial(name="triumph", end_mode="time", end_time=30.0,
                         rotations=[Rotation(name="r",
                                             sequences=[burst_seq, fill, fill, burst_seq],
                                             repetitions=1)]))
    t_tr.evaluate_timeline()
    tr_hits = [e for e in t_tr.global_events if e.get("hit_name") == "Triumph"]
    tr_casts = [e["global_time"] for e in t_tr.global_events
                if e.get("hit_name") == "Burst_Cast"]
    out["triumph_count"] = len(tr_hits)
    out["triumph_times"] = [round(e["global_time"], 3) for e in tr_hits]
    out["triumph_casts"] = [round(c, 3) for c in tr_casts]
    out["triumph_gap_ok"] = all(
        e["global_time"] >= max([c for c in tr_casts if c <= e["global_time"]],
                                default=1e9) + ANASTASYA_TRIUMPH_DELAY - 1e-6
        for e in tr_hits)

    # ---- 8. Triumph inside the preset: every loop from the 2nd one onwards ----
    rot_triumphs = [e for e in hits if e.get("hit_name") == "Triumph"]
    ana_swap_ins = [s for s in timeline.global_events
                    if s.get("event_type") == "SWAP_IN" and s.get("character") == "Anastasya"]
    out["rotation_swap_ins"] = len(ana_swap_ins)
    out["rotation_triumphs"] = len(rot_triumphs)
    out["rotation_triumph_expected"] = max(0, len(ana_swap_ins) - 1)
    out["rotation_triumph_times"] = [round(e["global_time"], 3) for e in rot_triumphs]
    out["triumph_on_her_swap_in"] = all(
        any(abs(e["global_time"] - s["global_time"]) <= 1e-9 for s in ana_swap_ins)
        for e in rot_triumphs)
    out["no_triumph_on_first_loop"] = (
        bool(ana_swap_ins)
        and all(e["global_time"] > ana_swap_ins[0]["global_time"] + 1e-9 for e in rot_triumphs))
    return out

def _run_editor_catalogue_check() -> dict:
    """Editor catalogues + preset trial team gating (what the UI is allowed to offer).

    Every FieldSequence / Ability in abilities.py must be reachable through the
    registries, ownership must resolve, and a preset trial must advertise exactly the
    team its rotation actually plays.
    """
    import abilities

    out = {}
    seq_names = {seq.name for seq in abilities.FIELD_SEQUENCE_REGISTRY.values()}
    ab_names = {(char, name) for char, m in abilities.ABILITY_REGISTRY.items() for name in m}
    out["sequence_count"] = len(seq_names)
    out["ability_count"] = len(ab_names)

    # Faruzan E: collapse only, same insertion time / field time as her Q swap.
    fe = abilities.FIELD_SEQUENCE_REGISTRY.get("FaruzanESwap")
    fq = abilities.FIELD_SEQUENCE_REGISTRY.get("FaruzanQSwap")
    out["faruzan_e_exists"] = fe is not None
    if fe is not None and fq is not None:
        out["faruzan_e_same_swap"] = abs(fe.swap_out_time - fq.swap_out_time) <= 1e-9
        out["faruzan_e_same_insert"] = abs(fe.calls[0].start_time - fq.calls[0].start_time) <= 1e-9
        out["faruzan_e_is_collapse"] = (len(fe.calls) == 1
                                        and fe.calls[0].ability.name == "Pressurized Collapse")
        out["faruzan_e_no_burst"] = all(c.ability.name != "Elemental Burst" for c in fe.calls)
    else:
        out["faruzan_e_same_swap"] = out["faruzan_e_same_insert"] = False
        out["faruzan_e_is_collapse"] = out["faruzan_e_no_burst"] = False

    # Party-gated filtering helper used by the UI.
    only_mizuki = abilities.field_sequences_for(["Mizuki"])
    out["filter_only_party"] = bool(only_mizuki) and all(
        seq.character == "Mizuki" for seq in only_mizuki.values())
    out["filter_hides_outside"] = "AnastasyaEQ" not in only_mizuki
    out["abilities_for_anastasya"] = sorted(abilities.abilities_for("Anastasya").keys())
    out["abilities_for_absent"] = abilities.abilities_for("Diona")
    # Engine-injected procs stay registered but are never offered by the editor.
    out["internal_hidden"] = ("Triumph" in abilities.ABILITY_REGISTRY.get("Anastasya", {})
                              and "Triumph" not in abilities.abilities_for("Anastasya"))

    # Preset trials: required team == the characters their rotations actually use.
    mismatched = []
    for key, trial in presets.STANDARD_TRIALS.items():
        if not trial.required_party:
            mismatched.append(f"{key}: missing required_party")
            continue
        used = {seq.character for rot in trial.rotations for seq in rot.sequences}
        if used != set(trial.required_party):
            mismatched.append(f"{key}: rotation plays {sorted(used)}, "
                              f"trial declares {sorted(trial.required_party)}")
    out["trial_team_mismatches"] = mismatched

    aether_trial = presets.STANDARD_TRIALS["Mizuki Sac Frag Pull out 6x rotations"]
    ana_trial = presets.STANDARD_TRIALS["Mizuki Sac Frag Pull out 6x rotations (Anastasya)"]
    out["same_display_name"] = aether_trial.name == ana_trial.name
    out["aether_team_only"] = (
        aether_trial.matches_party(["Mizuki", "Aether", "Odette", "Faruzan"])
        and not aether_trial.matches_party(["Mizuki", "Anastasya", "Odette", "Faruzan"]))
    out["ana_team_only"] = (
        ana_trial.matches_party(["Faruzan", "Odette", "Anastasya", "Mizuki"])
        and not ana_trial.matches_party(presets.MIZUKI_SACFRAG_TEAM))
    out["no_3_char_match"] = not ana_trial.matches_party(["Mizuki", "Anastasya", "Odette"])
    out["timed_trial_not_offered"] = all(
        t.end_mode != "time" for t in presets.STANDARD_TRIALS.values())
    return out


def _run_save_load_check() -> dict:
    """Build documents (save / load): a saved build must round-trip completely.

    Uses a representative catalogue (the UI passes its own via BUILD_CATALOGUE) to
    prove that: raw gear is written to the file, restoring writes the WIDGET STATE
    back (so the build stays editable), the rebuilt party has identical
    initial_stats, and a trial can be opened in the editor.
    """
    import json

    catalogue = {
        "characters": ["Select Character", "Mizuki", "Aether", "Odette", "Faruzan"],
        "levels": [60, 70, 80, 90, 95, 100],
        "constellations": {"Select Character": ["C0"], "Faruzan": ["C6"],
                           "Mizuki": ["C0", "C1", "C2", "C6"], "Aether": ["C4", "C5", "C6"],
                           "Odette": ["C0"]},
        "weapons": {"Mizuki": [("Sacrificial Fragments", [4, 5])],
                    "Faruzan": [("Favonius Warbow", [1, 2, 3, 4, 5])],
                    "Aether": [("New Bough", [1, 2, 3, 4, 5])],
                    "Odette": [("New Bough", [1, 2, 3, 4, 5])]},
        "artifact_sets": {"Mizuki": ["Select Set", "Gilded Dreams"],
                          "Faruzan": ["Select Set", "Instructor"],
                          "Aether": ["Select Set", "2p/2p ATK"],
                          "Odette": ["Select Set", "2p/2p ATK"]},
        "substat_options": ["None", "Flat ATK", "Flat HP", "Flat DEF", "ATK%", "HP%",
                            "DEF%", "Crit Rate%", "Crit Damage%", "ER%", "EM"],
        "mains": {"Sands": ["ATK%", "EM", "ER%"], "Goblet": ["Anemo Bonus%", "EM"],
                  "Circlet": ["Crit Rate%", "Crit Damage%", "EM"]},
        "rarities": ["5★", "4★"],
        "standards": list(build_io.SUBSTAT_STANDARDS),
    }

    state = {
        "char_1": "Mizuki", "level_1": 90, "const_1": "C2",
        "weapon_1": "Sacrificial Fragments", "ref_1": "R5", "talents_1": "6/10/10",
        "std_1": "Manual", "art_set_1": "Gilded Dreams",
        "char_2": "Faruzan", "level_2": 90, "const_2": "C6",
        "weapon_2": "Favonius Warbow", "ref_2": "R3", "talents_2": "1/13/13",
        "art_set_2": "Instructor",
        "char_3": "Select Character", "char_4": "Select Character",
        "input_enemy_lv": 95,
        "trial_selector": "Round trip trial",
    }
    for element in build_io.ELEMENTS:
        state[f"input_{element}_res"] = 12.5
    mains_in = {"Flower": "Flat HP", "Feather": "Flat ATK", "Sands": "EM",
                "Goblet": "Anemo Bonus%", "Circlet": "Crit Rate%"}
    subs_in = [("EM", "40"), ("Crit Rate%", "3.5"), ("Crit Damage%", "7.0"), ("ER%", "5.2")]
    for slot in (1, 2):
        for piece in build_io.PIECES:
            state[f"rarity_{piece}_{slot}"] = "5★"
            state[f"main_{piece}_{slot}"] = mains_in[piece]
            for index, (sub_name, sub_value) in enumerate(subs_in, start=1):
                state[f"sub_type_{piece}_{slot}_{index}"] = sub_name
                state[f"sub_val_{piece}_{slot}_{index}"] = sub_value

    rotation = Rotation(name="Round trip rotation",
                        sequences=[presets.STANDARD_FIELD_SEQUENCES["Mizuki E (Pullout)"]],
                        repetitions=2)
    trial = Trial(name="Round trip trial", rotations=[rotation], end_mode="time",
                  end_time=45.0, description="round trip")
    state["custom_field_sequences"] = {}
    state["custom_rotations"] = {rotation.name: rotation}
    state["active_trial_pool"] = dict(presets.STANDARD_TRIALS)
    state["active_trial_pool"][trial.name] = trial

    out = {}
    document = build_io.collect_build_document(state, "Round trip")
    text = build_io.document_to_json(document)
    parsed = build_io.parse_document(text)
    out["schema"] = parsed["schema_version"]
    out["size"] = len(text)
    out["substats_saved"] = (parsed["party"][0]["pieces"]["Sands"]["substats"][0]
                             == {"stat": "EM", "value": "40"})
    out["trial_saved"] = [t["name"] for t in parsed["custom_trials"]] == [trial.name]

    restored = {}
    out["restore_warnings"] = build_io.apply_build_document(parsed, restored, catalogue)
    skip = ("active_trial_pool", "custom_rotations", "custom_field_sequences",
            "imported_sim_name")
    out["widget_mismatches"] = sorted(
        key for key in state
        if key not in skip and not key.startswith(("main_Flower", "main_Feather"))
        and restored.get(key) != state[key]
    )
    out["trial_restored"] = (restored.get("trial_selector") == trial.name
                             and trial.name in restored.get("active_trial_pool", {}))
    out["enemy_restored"] = (restored.get("enemy_confirmed") is True
                             and restored.get("input_enemy_lv") == 95)

    party = build_io.build_party_from_document(parsed)
    out["party_keys"] = sorted(party)
    mains_saved, subs_saved = build_io.slot_stats_from_pieces(
        "Mizuki", parsed["party"][0]["pieces"], "Manual")
    expected = build_initial_stats("Mizuki", 90, "Sacrificial Fragments", "Gilded Dreams",
                                   mains_saved, subs_saved, refinement=5)
    out["stats_match"] = "Mizuki" in party and all(
        abs(expected[key] - party["Mizuki"]["initial_stats"][key]) <= 1e-9
        for key in ("em", "crit_rate", "crit_dmg", "er"))

    editor_state = {"custom_rotations": {}, "custom_field_sequences": {}}
    preset_trial = presets.STANDARD_TRIALS["Mizuki Sac Frag Pull out 6x rotations"]
    build_io.load_trial_into_editor(preset_trial, editor_state)
    out["editor_materialised"] = all(
        rot.name in editor_state["custom_rotations"] for rot in preset_trial.rotations)
    out["editor_queue"] = (len(editor_state["temp_trial_rot_entries"])
                           == len(preset_trial.rotations))

    # A schema 1.0 file still loads: characters + enemy, but no artifact gear.
    legacy = {"schema_version": "1.0", "simulation_name": "legacy",
              "party": {"Mizuki": {"level": 90, "constellation": 2,
                                   "weapon": "Sacrificial Fragments", "refinement": 5,
                                   "talents": "6/10/10", "artifact_set": "Gilded Dreams"}},
              "enemy_stats": {"enemy_lv": 95, "cryo_res": 0.2}}
    legacy_doc = build_io.parse_document(json.dumps(legacy))
    legacy_state = {}
    build_io.apply_build_document(legacy_doc, legacy_state, catalogue)
    out["legacy_ok"] = (build_io.document_lacks_gear(legacy_doc)
                        and legacy_state.get("char_1") == "Mizuki"
                        and "Mizuki" in build_io.build_party_from_document(legacy_doc))

    # A slot the file does not fill must be emptied, not left holding an old character.
    small_state = {"char_3": "Odette", "char_4": "Aether"}
    build_io.apply_build_document(
        build_io.parse_document(json.dumps({
            "schema_version": "2.0",
            "party": [{"slot": 1, "character": "Mizuki", "level": 90,
                       "constellation": 2, "weapon": "Sacrificial Fragments",
                       "refinement": 5, "talents": "6/10/10", "pieces": {}}],
            "enemy": {"enemy_lv": 100},
        })),
        small_state, catalogue)
    out["slot_cleanup"] = (small_state.get("char_3") == "Select Character"
                           and small_state.get("char_4") == "Select Character")

    # The UI writes one widget key per input; the importer must speak the same names,
    # so a rename in streamlit_app.py has to be mirrored in build_io (and vice versa).
    out["key_mismatches"] = ["(streamlit_app.py not found)"]
    try:
        with open("streamlit_app.py", encoding="utf-8") as handle:
            app_source = handle.read()
    except OSError:
        pass
    else:
        templates = ["char_{slot_num}", "level_{slot_num}", "const_{slot_num}",
                     "weapon_{slot_num}", "ref_{slot_num}", "talents_{slot_num}",
                     "art_set_{slot_num}", "std_{slot_num}",
                     "main_{piece_name}_{slot_num}", "rarity_{piece_name}_{slot_num}",
                     "rarity_locked_{piece_name}_{slot_num}",
                     "sub_type_{piece_name}_{slot_num}_{sub_idx}",
                     "sub_val_{piece_name}_{slot_num}_{sub_idx}",
                     "input_{elem}_res"]
        out["key_mismatches"] = [name for name in templates
                                 if 'f"%s"' % name not in app_source]
    return out


def run(verbose: bool = True) -> None:
    party = presets.DEFAULT_PARTY
    trial = presets.TEST_TRIAL_30S

    timeline = RotationTimeline(party=party)
    timeline.add_trial(trial)
    timeline.evaluate_timeline()

    events = timeline.global_events
    hit_events = [e for e in events if e.get("event_type") == "HIT"]

    failures = []

    # 1. Chronology across ALL events
    times = [e["global_time"] for e in events]
    bad_pairs = sum(1 for a, b in zip(times, times[1:]) if b < a - 1e-9)
    if bad_pairs:
        failures.append(f"out-of-order adjacent events: {bad_pairs}")
    elif verbose:
        print(f"[OK] chronological order ({len(events)} events)")

    # 2. No NaN / non-finite damage
    bad_dmg = [
        e for e in hit_events
        if e.get("average_damage") is not None and e["average_damage"] != e["average_damage"]
    ]
    if bad_dmg:
        failures.append(f"{len(bad_dmg)} hit events have NaN average_damage")
    elif verbose:
        print("[OK] no NaN damage values")

    # 3. Aether kit auditors present
    burst_variants = sorted({e.get("burst_variant") for e in hit_events if e.get("burst_variant") in ("Enhanced", "Standard")})
    max_frostglow = max((e.get("frostglow_stacks", 0) for e in hit_events), default=0)
    c6_on = any(e.get("aether_c6_state") == "ON" for e in hit_events)
    c2_on = any(e.get("aether_c2_state") == "ON" for e in hit_events)
    c2e_on = any(e.get("aether_c2_enhanced_state") == "ON" for e in hit_events)

    if burst_variants and verbose:
        print(f"[OK] burst variants fired: {burst_variants}")
    if not burst_variants:
        failures.append("no Aether burst was substituted (no Enhanced/Standard events)")
    if max_frostglow == 0:
        failures.append("Frostglow stacks never accumulated")
    if c6_on and verbose:
        print(f"[OK] Aether C6 window activated")
    if c2_on and verbose:
        print(f"[OK] Aether C2 basic activated")
    if c2e_on and verbose:
        print(f"[OK] Aether C2 enhanced activated")

    # 3b. Odette kit auditors (Marvelous + C2 shred) on the standard run.
    odette_marvel_on = "Odette" in party and any(int(e.get("marvelous_stacks", 0) or 0) > 0 for e in hit_events)
    odette_c2_on = "Odette" in party and any(e.get("odette_c2_state") == "ON" for e in hit_events)
    if odette_marvel_on and verbose:
        print("[OK] Odette Marvelous activated")
    if not odette_marvel_on:
        failures.append("Odette Marvelous never activated")
    if odette_c2_on and verbose:
        print("[OK] Odette C2 shred activated")
    if "Odette" in party and not odette_c2_on:
        failures.append("Odette C2 shred never activated")

    # 3c. Odette's "Snow Swan's Dream": self-only, talent-scaled, 20s from the cast.
    ob = _run_odette_burst_check()
    if ob["on"] and verbose:
        print("[OK] Odette burst buff activated")
    if not ob["on"]:
        failures.append("Odette burst buff never activated")
    if ob["on"]:
        if not ob["alive_at_15s"]:
            failures.append("Odette's Snow Swan window is shorter than 15s (expected 20s)")
        if not ob["off_after_20s"]:
            failures.append("Odette's Snow Swan window outlived its 20s")
        if abs((ob["stellar"] or 0.0) - 0.62) > 1e-6:
            failures.append(f"Odette's Snow Swan stellar bonus is {ob['stellar']}, "
                            f"expected 0.62 at burst lv13")
        if abs(ob["not_party"] or 0.0) > 1e-12:
            failures.append(f"Odette's Snow Swan leaked onto the party ({ob['not_party']})")
        if verbose and not (ob["alive_at_15s"] and ob["off_after_20s"]):
            print("[INFO] Odette Snow Swan window check failed")

    # 3d. Faruzan auditors (buff on anemo hits, debuff window, quill on anemo).
    faruzan_buff_on = "Faruzan" in party and any(e.get("faruzan_buff_state") == "ON" for e in hit_events)
    faruzan_debuff_on = "Faruzan" in party and any(e.get("faruzan_debuff_state") == "ON" for e in hit_events)
    faruzan_quill_on = "Faruzan" in party and any(
        (e.get("quill_damage", 0) or 0) > 0
        for e in hit_events if e.get("element") == "Anemo"
    )
    if faruzan_buff_on and verbose:
        print("[OK] Faruzan buff applied to anemo hits")
    if "Faruzan" in party and not faruzan_buff_on:
        failures.append("Faruzan buff never applied to any hit")
    if faruzan_debuff_on and verbose:
        print("[OK] Faruzan debuff window active")
    if "Faruzan" in party and not faruzan_debuff_on:
        failures.append("Faruzan debuff never active")
    if faruzan_quill_on and verbose:
        print("[OK] Faruzan quill fired on anemo hits")
    if "Faruzan" in party and not faruzan_quill_on:
        failures.append("Faruzan quill never applied to anemo standard hits")

    # 3e. Sucrose kit: A1 (50 EM, non-Anemo), A4 (20% flat EM, others), C6 field.
    suc = _run_sucrose_check()
    if suc["a1"] and verbose:
        print("[OK] Sucrose A1 window fired on her swirl")
    if not suc["a1"]:
        failures.append("Sucrose A1 never activated (no swirl window)")
    if suc["a4"] and verbose:
        print("[OK] Sucrose A4 share window fired")
    if not suc["a4"]:
        failures.append("Sucrose A4 never activated")
    if suc["c6"] and verbose:
        print("[OK] Sucrose C6 cryo_bonus window fired")
    if not suc["c6"]:
        failures.append("Sucrose C6 never activated")

    if abs(suc["ally_a1_em"] - 50.0) > 1e-6:
        failures.append(f"Sucrose A1 EM share is {suc['ally_a1_em']}, expected 50")
    elif verbose:
        print("[OK] Sucrose A1 grants +50 EM to a non-Anemo ally")
    if abs(suc["self_a1_em"]) > 1e-6:
        failures.append(f"Sucrose A1 leaked onto herself ({suc['self_a1_em']} EM)")
    elif verbose:
        print("[OK] Sucrose A1 excludes Anemo (herself)")

    want_a4 = 0.20 * suc["sucrose_flat_em"]
    if abs(suc["ally_a4_em"] - want_a4) > 1e-6:
        failures.append(f"Sucrose A4 share is {suc['ally_a4_em']}, "
                        f"expected {want_a4:.2f} (20% of {suc['sucrose_flat_em']})")
    elif verbose:
        print(f"[OK] Sucrose A4 shares 20% of her flat EM ({want_a4:.1f})")
    if abs(suc["self_a4_em"]) > 1e-6:
        failures.append(f"Sucrose A4 leaked onto herself ({suc['self_a4_em']} EM)")
    elif verbose:
        print("[OK] Sucrose A4 is 'others only'")

    if abs(suc["window"] - SUCROSE_BURST_WINDOW) > 1e-6:
        failures.append(f"Sucrose C6 window is {suc['window']}s, "
                        f"expected {SUCROSE_BURST_WINDOW:.3f}s (one burst field)")
    elif verbose:
        print(f"[OK] Sucrose C6 window spans one burst field ({suc['window']:.3f}s)")
    if not suc["last_hit_on"]:
        failures.append("Sucrose C6 is OFF on the burst's last hit")
    if suc["after_burst_c6"]:
        failures.append("Sucrose C6 still ON after the burst field expired")
    elif verbose:
        print("[OK] Sucrose C6 turns off with the burst field")
    if abs(suc["ally_c6_bonus"] - 0.20) > 1e-6:
        failures.append(f"Sucrose C6 cryo_bonus is {suc['ally_c6_bonus']}, expected 0.20")
    elif verbose:
        print("[OK] Sucrose C6 grants +20% cryo_bonus to allies")

    # 3f. Mizuki C6: party stellar crit (part 1) + crit from flat EM (part 2).
    mz = _run_mizuki_c6_check()
    c0, c6 = mz[0], mz[6]
    if abs(c6["stellar_cr"] - 0.10) > 1e-9 or abs(c6["stellar_cd"] - 0.20) > 1e-9:
        failures.append(f"Mizuki C6 stellar crit is {c6['stellar_cr']}/{c6['stellar_cd']}, "
                        f"expected 0.10/0.20")
    elif verbose:
        print("[OK] Mizuki C6 grants +10% stellar CR / +20% stellar CD during DDS")
    if abs(c0["stellar_cr"]) > 1e-9 or abs(c0["stellar_cd"]) > 1e-9:
        failures.append("Mizuki stellar crit applies below C6")
    elif verbose:
        print("[OK] Mizuki stellar crit is C6-gated")

    want_cr = min(0.0004 * max(c6["flat_em"] - 500.0, 0.0), 0.20)
    want_cd = min(0.0016 * max(c6["flat_em"] - 500.0, 0.0), 0.80)
    if (abs((c6["CR"] - c0["CR"]) - want_cr) > 1e-9
            or abs((c6["CD"] - c0["CD"]) - want_cd) > 1e-9):
        failures.append(
            f"Mizuki C6 crit-from-EM is {c6['CR'] - c0['CR']:.4f}/{c6['CD'] - c0['CD']:.4f}, "
            f"expected {want_cr:.4f}/{want_cd:.4f} at flat EM {c6['flat_em']:.1f}")
    elif verbose:
        print(f"[OK] Mizuki C6 crit-from-EM = {want_cr:.3%}/{want_cd:.3%} "
              f"at flat EM {c6['flat_em']:.1f}")

    # 3h. Weapons phase 1: permanent stats + conditional passives.
    wp = _run_weapon_check()
    weapon_checks = [
        (abs(wp["widsith_atk"] - 510.0) <= 1e-6,
         f"The Widsith base ATK is {wp['widsith_atk']}, expected 510"),
        (abs(wp["widsith_cd"] - 0.551) <= 1e-6,
         f"The Widsith crit DMG is {wp['widsith_cd']}, expected 0.551"),
        (abs(wp["sunny_em"] - 265.0) <= 1e-6,
         f"Sunny Morning Sleep-In EM is {wp['sunny_em']}, expected 265"),
        (abs(wp["jade_cr"] - 0.368) <= 1e-6,
         f"Sacrificial Jade CR is {wp['jade_cr']}, expected 0.368"),
        (abs(wp["starcaller_em"] - 465.0) <= 1e-6,
         f"Starcaller's Watch EM is {wp['starcaller_em']}, expected 465 at R5"),
        (wp["key_variant"] == "The Widsith (Average)",
         f"weapon key for the Widsith variant is {wp['key_variant']!r}"),
        (wp["key_suffixed"] == "Silver Light",
         f"weapon key for 'Silver Light (R5)' is {wp['key_suffixed']!r}"),
        (wp["widsith_on_early"], "The Widsith never procced on taking the field"),
        (not wp["widsith_on_mid"], "The Widsith re-procced inside its 30s cooldown"),
        (wp["widsith_on_late"], "The Widsith did not proc again after the 30s cooldown"),
        (abs((wp["widsith_em"] or 0.0) - 160.0) <= 1e-6,
         f"Widsith EM roll is {wp['widsith_em']}, expected 160 at R5"),
        (abs((wp["widsith_atk_pct"] or 0.0) - 0.40) <= 1e-6,
         f"Widsith ATK% roll is {wp['widsith_atk_pct']}, expected 0.40 at R5"),
        (abs((wp["widsith_cryo"] or 0.0) - 0.32) <= 1e-6,
         f"Widsith elemental roll is {wp['widsith_cryo']}, expected 0.32 at R5"),
        (wp["jade_on_early"], "Sacrificial Jade did not start active"),
        (wp["jade_off_onfield"], "Sacrificial Jade stayed active after 10s on-field"),
        (wp["jade_on_after_bench"], "Sacrificial Jade did not return after 5s off-field"),
        (abs((wp["jade_em"] or 0.0) - 40.0) <= 1e-6,
         f"Sacrificial Jade EM is {wp['jade_em']}, expected 40 at R1"),
        (abs((wp["jade_hp_pct"] or 0.0) - 0.32) <= 1e-6,
         f"Sacrificial Jade HP% is {wp['jade_hp_pct']}, expected 0.32 at R1"),
        (wp["sunny_swirl_on"], "Sunny Morning swirl window never opened"),
        (wp["sunny_skill_on"], "Sunny Morning skill window never opened"),
        (wp["sunny_burst_on"], "Sunny Morning burst window never opened"),
        (wp["sunny_swirl_long_enough"], "Sunny Morning swirl window died before 6s"),
        (wp["sunny_skill_long_enough"], "Sunny Morning skill window died before 9s"),
        (wp["sunny_burst_long_enough"], "Sunny Morning burst window died before 30s"),
        (wp["sunny_swirl_off"], "Sunny Morning swirl window outlived its 6s"),
        (wp["sunny_skill_off"], "Sunny Morning skill window outlived its 9s"),
        (wp["sunny_burst_off"], "Sunny Morning burst window outlived its 30s"),
        (abs((wp["sunny_swirl_em"] or 0.0) - 120.0) <= 1e-6,
         f"Sunny swirl EM is {wp['sunny_swirl_em']}, expected 120 at R1"),
        (abs((wp["sunny_skill_em"] or 0.0) - 96.0) <= 1e-6,
         f"Sunny skill EM is {wp['sunny_skill_em']}, expected 96 at R1"),
        (abs((wp["sunny_burst_em"] or 0.0) - 32.0) <= 1e-6,
         f"Sunny burst EM is {wp['sunny_burst_em']}, expected 32 at R1"),
    ]
    weapon_failures = [msg for ok, msg in weapon_checks if not ok]
    failures.extend(weapon_failures)
    if not weapon_failures and verbose:
        print("[OK] weapons phase 1: stats resolve + Widsith/Jade/Sunny windows behave")

    # 3i. Weapons phase 2: composition stats, periodic stacks, next-char proc.
    wp2 = _run_weapon_phase2_check()
    phase2_checks = [
        (wp2["atfd_mixed"] == (128.0, 0.26, 48.0),
         f"ATFD mixed party gave {wp2['atfd_mixed']}, expected (128.0, 0.26, 48.0)"),
        (wp2["atfd_all_diff"] == (192.0, 0.0),
         f"ATFD all-different party gave {wp2['atfd_all_diff']}, expected (192.0, 0.0)"),
        (wp2["atfd_all_same"] == (0.0, 0.52),
         f"ATFD all-same party gave {wp2['atfd_all_same']}, expected (0.0, 0.52)"),
        (wp2["atfd_idempotent"],
         "A Thousand Floating Dreams party stats are not idempotent"),
        (wp2["evenstar_stacks_at"] == [1, 2, 1],
         f"Evenstar stack timeline is {wp2['evenstar_stacks_at']}, expected [1, 2, 1]"),
        (wp2["evenstar_self_one"] is not None
         and abs(wp2["evenstar_self_one"] - wp2["evenstar_want_one"]) <= 1e-6,
         f"Evenstar holder ATK is {wp2['evenstar_self_one']}, expected {wp2['evenstar_want_one']}"),
        (wp2["evenstar_self_two"] is not None
         and abs(wp2["evenstar_self_two"] - wp2["evenstar_want_two"]) <= 1e-6,
         f"Evenstar 2-stack ATK is {wp2['evenstar_self_two']}, expected {wp2['evenstar_want_two']}"),
        (wp2["evenstar_ally_one"] is not None
         and abs(wp2["evenstar_ally_one"] - wp2["evenstar_ally_want"]) <= 1e-6,
         f"Evenstar party ATK is {wp2['evenstar_ally_one']}, expected {wp2['evenstar_ally_want']}"),
        (wp2["ttds_on"], "Thrilling Tales never procced"),
        (wp2["ttds_only_target"],
         "Thrilling Tales landed on someone other than the incoming character"),
        (wp2["ttds_off_after_cd"], "Thrilling Tales procced again inside its 20s cooldown"),
        (abs((wp2["ttds_atk_pct"] or 0.0) - 0.24) <= 1e-6,
         f"TTDS ATK% is {wp2['ttds_atk_pct']}, expected 0.24 at R1"),
        (wp2["starsealed_on"], "Starsealed Edict window never opened"),
        (wp2["starsealed_opens_at_cast"],
         "Starsealed Edict window did not open on the skill CAST hit"),
        (wp2["starsealed_max_stacks"] >= 1, "Starsealed Edict never gained a swirl stack"),
        (wp2["starsealed_off_tail"], "Starsealed Edict window outlived its 20s"),
        (abs((wp2["starsealed_const_em"] or 0.0) - 96.0) <= 1e-6,
         f"Starsealed constant EM is {wp2['starsealed_const_em']}, expected 96 at R5"),
        (wp2["starsealed_stack_em"] is not None
         and abs(wp2["starsealed_stack_em"] - wp2["starsealed_want_stack_em"]) <= 1e-6,
         f"Starsealed stack EM is {wp2['starsealed_stack_em']}, "
         f"expected {wp2['starsealed_want_stack_em']}"),
    ]
    phase2_failures = [msg for ok, msg in phase2_checks if not ok]
    failures.extend(phase2_failures)
    if not phase2_failures and verbose:
        print("[OK] weapons phase 2: ATFD composition + Evenstar/TTDS/Starsealed behave")

    # 3j. Weapons phase 3: permanents + stacks/sigils/windows.
    wp3 = _run_weapon_phase3_check()
    phase3_checks = [
        (wp3["azurelight_atk_pct"] == 0.48,
         f"Azurelight ATK% is {wp3['azurelight_atk_pct']}, expected 0.48 at R5"),
        (wp3["aquila_atk_pct"] == 0.40,
         f"Aquila Favonia ATK% is {wp3['aquila_atk_pct']}, expected 0.40 at R5"),
        (wp3["aquila_phys"] == 0.413,
         f"Aquila Favonia physical bonus is {wp3['aquila_phys']}, expected 0.413"),
        (wp3["sacbow_er"] == 0.306,
         f"Sacrificial Bow ER is {wp3['sacbow_er']}, expected 0.306"),
        (wp3["sacbow_atk_pct"] == 0.0,
         f"Sacrificial Bow grants ATK% ({wp3['sacbow_atk_pct']}), expected none"),
        (wp3["elegy_weapon_em"] == 120.0,
         f"Elegy permanent EM is {wp3['elegy_weapon_em']}, expected 120 at R5"),
        (wp3["whitlake_max_stacks"] == 3,
         f"Whitelake reached {wp3['whitlake_max_stacks']} stacks, expected 3"),
        (wp3["whitlake_expired"],
         "Whitelake stacks did not expire 8s after the last skill hit"),
        (abs((wp3["whitlake_stellar_cd"] or 0.0) - 1.10) <= 1e-6,
         f"Whitelake 3-stack stellar crit is {wp3['whitlake_stellar_cd']}, "
         f"expected 1.10 at R5"),
        (abs(wp3["whitlake_plain_cd"] or 0.0) <= 1e-9,
         f"Whitelake leaked into STANDARD crit dmg ({wp3['whitlake_plain_cd']})"),
        (wp3["finale_on"], "Finale Of The Deep never procced"),
        (abs((wp3["finale_atk_pct"] or 0.0) - 0.24) <= 1e-6,
         f"Finale ATK% is {wp3['finale_atk_pct']}, expected 0.24 at R5"),
        (wp3["finale_expired"], "Finale Of The Deep window outlived its 15s"),
        (wp3["breezeborne_on"], "Breezeborne Refrain never triggered"),
        (abs((wp3["breezeborne_party_stellar"] or 0.0) - 0.48) <= 1e-6,
         f"Breezeborne party stellar bonus is {wp3['breezeborne_party_stellar']}, "
         f"expected 0.48 at R5"),
        (wp3["breezeborne_no_sigils_while_on"],
         "Breezeborne gained sigils during its own buff"),
        (wp3["elegy_on"], "Elegy for the End never triggered"),
        (abs((wp3["elegy_party_atk"] or 0.0) - 0.40) <= 1e-6,
         f"Elegy party ATK% is {wp3['elegy_party_atk']}, expected 0.40 at R5"),
        (abs((wp3["elegy_party_em"] or 0.0) - 200.0) <= 1e-6,
         f"Elegy party EM is {wp3['elegy_party_em']}, expected 200 at R5"),
        (wp3["elegy_lockout"], "Elegy gained sigils inside its 20s lockout"),
        (bool(wp3["newbough_ramp"]) and wp3["newbough_ramp"][0] == 1,
         f"New Bough did not start at 1 stack ({wp3['newbough_ramp']})"),
        (wp3["newbough_max"] == 3,
         f"New Bough reached {wp3['newbough_max']} stacks, expected 3"),
        (wp3["silverdawn_on"], "Silverdawn never triggered"),
        (wp3["silverdawn_max_ext"] >= 1,
         f"Silverdawn gained {wp3['silverdawn_max_ext']} extensions, expected >= 1"),
        (abs((wp3["silverdawn_stellar_cd"] or 0.0) - 0.88) <= 1e-6,
         f"Silverdawn stellar crit is {wp3['silverdawn_stellar_cd']}, "
         f"expected 0.88 at R5"),
        (abs(wp3["silverdawn_plain_cd"] or 0.0) <= 1e-9,
         f"Silverdawn leaked into STANDARD crit dmg ({wp3['silverdawn_plain_cd']})"),
    ]
    phase3_failures = [msg for ok, msg in phase3_checks if not ok]
    failures.extend(phase3_failures)
    if not phase3_failures and verbose:
        print("[OK] weapons phase 3: permanents + Whitelake/Finale/Breeze/Elegy/"
              "NewBough/Silverdawn behave")

    # 3k. Artifact rare stats: data + damage yes, card no.
    art = _run_artifact_stat_check()
    artifact_checks = [
        (art["cryo_bonus"] == 0.20,
         f"artifact cryo_bonus is {art['cryo_bonus']}, expected 0.20"),
        (art["skill_bonus"] == 0.10,
         f"artifact skill_bonus is {art['skill_bonus']}, expected 0.10"),
        (art["burst_bonus"] == 0.15,
         f"artifact burst_bonus is {art['burst_bonus']}, expected 0.15"),
        (art["stellar_bonus"] == 0.30,
         f"artifact stellar_bonus is {art['stellar_bonus']}, expected 0.30"),
        (art["stellar_crit_dmg"] == 0.40,
         f"artifact stellar_crit_dmg is {art['stellar_crit_dmg']}, expected 0.40"),
        (abs(art["crit_rate"] - 0.15) <= 1e-9,
         f"artifact crit_rate is {art['crit_rate']}, expected 0.15 (base 0.05 + 0.10)"),
        (abs(art["er"] - 1.25) <= 1e-9,
         f"artifact ER is {art['er']}, expected 1.25 (1.0 + 0.25)"),
        (art["card_leaks"] == [],
         f"rare artifact stats leaked onto the card: {art['card_leaks']}"),
        (not art["card_stellar"], "stellar_bonus leaked onto the card"),
        (not art["card_skill_burst"], "skill/burst bonus leaked onto the card"),
        (abs(art["std_skill_mult"] - 1.30) <= 1e-9,
         f"standard skill bonus_mult is {art['std_skill_mult']}, expected 1.30 "
         f"(cryo 0.20 + skill 0.10)"),
        (abs(art["std_cryo_burst_mult"] - 1.35) <= 1e-9,
         f"standard cryo burst bonus_mult is {art['std_cryo_burst_mult']}, expected 1.35"),
        (abs(art["std_anemo_burst_mult"] - 1.15) <= 1e-9,
         f"standard anemo burst bonus_mult is {art['std_anemo_burst_mult']}, expected 1.15"),
        (abs(art["std_crit_absolute"] - art["std_crit_expected"]) <= 1e-9,
         "standard crit picked up stellar_crit_dmg"),
        (art["stellar_ignores_std"],
         "stellar damage picked up a standard-only artifact bonus"),
        (art["stellar_uses_bonus"], "stellar damage ignored stellar_bonus"),
        (art["stellar_cd"] == 0.40,
         f"stellar crit dmg is {art['stellar_cd']}, expected 0.40"),
        (art["vv_anemo"] == 0.15,
         f"Viridescent Venerer anemo_bonus is {art['vv_anemo']}, expected 0.15"),
        (art["vv_stellar"] == 0.20,
         f"Viridescent Venerer stellar_bonus is {art['vv_stellar']}, expected 0.20"),
        (art["noblesse_burst"] == 0.20,
         f"Noblesse burst_bonus is {art['noblesse_burst']}, expected 0.20"),
    ]
    artifact_failures = [msg for ok, msg in artifact_checks if not ok]
    failures.extend(artifact_failures)
    if not artifact_failures and verbose:
        print("[OK] artifact rare stats reach the data + damage, never the card")

    # 3l. Artifact set buffs (phase 1).
    af = _run_artifact_phase1_check()
    artifact_buff_checks = [
        (af["instructor_on"], "Instructor never activated"),
        (abs((af["instructor_em"] or 0.0) - 120.0) <= 1e-6,
         f"Instructor EM is {af['instructor_em']}, expected 120"),
        (af["instructor_off_late"],
         "Instructor window outlived 8s / refreshed from an off-field swirl"),
        (af["gilded_on"], "Gilded Dreams never activated"),
        (abs((af["gilded_atk"] or 0.0) - 0.14) <= 1e-6,
         f"Gilded Dreams ATK% is {af['gilded_atk']}, expected 0.14 (1 same-element ally)"),
        (abs((af["gilded_em"] or 0.0) - 100.0) <= 1e-6,
         f"Gilded Dreams EM is {af['gilded_em']}, expected 100 (2 different-element allies)"),
        (af["gilded_alive_mid"], "Gilded Dreams window closed before its 8s"),
        (af["gilded_off_late"], "Gilded Dreams window outlived its 8s"),
        (af["noblesse_on"], "Noblesse Oblige never activated"),
        (abs((af["noblesse_atk"] or 0.0) - 0.20) <= 1e-6,
         f"Noblesse party ATK% is {af['noblesse_atk']}, expected 0.20"),
        (af["noblesse_off_late"],
         "Noblesse window was extended by something other than the burst cast"),
        (af["tenacity_on"], "Tenacity Of The Millelith never activated"),
        (abs((af["tenacity_atk"] or 0.0) - 0.20) <= 1e-6,
         f"Tenacity party ATK% is {af['tenacity_atk']}, expected 0.20"),
        (af["tenacity_alive_mid"], "Tenacity window closed before its 3s"),
        (af["tenacity_off_late"], "Tenacity window outlived its 3s"),
        (af["risingwinds_on"], "A Day Carved From Rising Winds never activated"),
        (af["risingwinds_trigger_off"],
         "Rising Winds buffed the hit that armed it (the proc must apply afterwards)"),
        (abs((af["risingwinds_atk"] or 0.0) - 0.25) <= 1e-6,
         f"Rising Winds ATK% is {af['risingwinds_atk']}, expected 0.25"),
        (abs(af["risingwinds_not_party"] or 0.0) <= 1e-12,
         f"Rising Winds leaked onto a party member ({af['risingwinds_not_party']})"),
        (af["scarlet_on"], "Scarlet Proof never activated"),
        (abs((af["scarlet_cr"] or 0.0) - 0.16) <= 1e-6,
         f"Scarlet Proof crit rate is {af['scarlet_cr']}, expected 0.16"),
        (abs((af["scarlet_stellar"] or 0.0) - 0.40) <= 1e-6,
         f"Scarlet Proof stellar bonus is {af['scarlet_stellar']}, expected 0.40"),
        (af["tsaritsa_max_stacks"] == 2,
         f"New Tsaritsa set reached {af['tsaritsa_max_stacks']} stacks, expected 2"),
        (abs((af["tsaritsa_cr"] or 0.0) - 0.20) <= 1e-6,
         f"Tsaritsa cryo crit rate is {af['tsaritsa_cr']}, expected 0.20"),
        (abs((af["tsaritsa_stellar_cr"] or 0.0) - 0.20) <= 1e-6,
         f"Tsaritsa stellar crit rate is {af['tsaritsa_stellar_cr']}, expected 0.20"),
        (not af["tsaritsa_anemo_cr_flag"],
         "Tsaritsa crit rate applied to a non-Cryo hit"),
        (af["tsaritsa_stacks_early"] == 1,
         f"Tsaritsa stacks early were {af['tsaritsa_stacks_early']}, expected 1"),
        (af["tsaritsa_stacks_decayed"],
         "Tsaritsa stacks did not decay after 3s of on-field time"),
    ]
    artifact_buff_failures = [msg for ok, msg in artifact_buff_checks if not ok]
    failures.extend(artifact_buff_failures)
    if not artifact_buff_failures and verbose:
        print("[OK] artifact buffs phase 1: Instructor/Gilded/Noblesse/Tenacity/"
              "RisingWinds/Scarlet/Tsaritsa behave")

    # 3m. Mizuki C2: PHEC bonus from the FLAT EM, anemo/PHEC shred in DDS.
    c2 = _run_mizuki_c2_check()
    c2_checks = [
        (abs((c2["cryo_bonus_2"] or 0.0) - 0.0004 * c2["flat_em_2"]) <= 1e-9,
         f"Mizuki C2 cryo bonus is {c2['cryo_bonus_2']}, expected 0.0004 x "
         f"flat EM ({c2['flat_em_2']})"),
        (abs(c2["cryo_bonus_1"] or 0.0) <= 1e-12,
         f"Mizuki C2 PHEC bonus applied below C2 ({c2['cryo_bonus_1']})"),
        (abs((c2["anemo_shred_2"] or 0.0) - 0.20) <= 1e-9,
         f"Mizuki C2 anemo shred is {c2['anemo_shred_2']}, expected 0.20"),
        (abs((c2["cryo_shred_2"] or 0.0) - 0.20) <= 1e-9,
         f"Mizuki C2 cryo shred is {c2['cryo_shred_2']}, expected 0.20"),
        (abs(c2["anemo_shred_1"] or 0.0) <= 1e-12,
         f"Mizuki C2 shred applied below C2 ({c2['anemo_shred_1']})"),
    ]
    c2_failures = [msg for ok, msg in c2_checks if not ok]
    failures.extend(c2_failures)
    if not c2_failures and verbose:
        print("[OK] Mizuki C2: flat-EM PHEC bonus + anemo/PHEC shred (DDS, C2+)")

    # 3n. Cryo Resonance: 2+ Cryo characters AND a Cryo-affected enemy.
    cr = _run_cryo_resonance_check()
    cr_checks = [
        (cr["two_on"], "Cryo Resonance never activated with 2 Cryo characters"),
        (abs((cr["two_cr"] or 0.0) - 0.15) <= 1e-9,
         f"Cryo Resonance CR is {cr['two_cr']}, expected 0.15"),
        (not cr["one_on"],
         "Cryo Resonance activated with a single Cryo character"),
        (cr["two_first_cryo_state"] == "OFF",
         "Cryo Resonance buffed the hit that APPLIED the aura (it needs a pre-existing aura)"),
        (cr["two_later_on"],
         "Cryo Resonance stayed off after the aura was applied"),
        (cr["two_first_aura"] == "0.00U",
         f"the Aura column shows {cr['two_first_aura']} on the hit that applied the aura "
         f"(it must show the PRE-hit state 0.00U)"),
        (cr["two_first_aura_after"] not in (None, "0.00U"),
         "the post-hit aura was not recorded"),
        (cr["two_later_aura"] not in (None, "0.00U"),
         f"the Aura column did not carry the applied aura to the next hit "
         f"({cr['two_later_aura']})"),
    ]
    cr_failures = [msg for ok, msg in cr_checks if not ok]
    failures.extend(cr_failures)
    if not cr_failures and verbose:
        print("[OK] Cryo Resonance: +15% CR only with 2+ Cryo characters and an "
              "existing aura (not on the applying hit)")

    # 3o. 100% RV / KQM standards: crit is one Crit Value (cv - 1), not 1 + CR*CD.
    rv = _run_rv_mode_check()
    rv_checks = [
        (rv["entry_flag"], "assemble_party did not flag a 100% RV slot"),
        (not rv["manual_entry_flag"], "a Manual slot was flagged as RV"),
        (rv["kqm_label"], "is_rv_mode() ignored the KQM standard label"),
        (not rv["manual_label"], "is_rv_mode() treated 'Manual' as a standard"),
        (not rv["empty_entry"], "is_rv_mode() flagged an empty entry"),
        (rv["collect_rv"],
         "assemble_party() dropped the standard coming from the widget state "
         f"(collect_slot -> {rv['collect_standard']})"),
        ("Aether 100% RV" in (rv["summary"] or ""),
         f"party_rv_summary() is {rv['summary']!r}, expected it to mention Aether"),
        (rv["hits"] >= 2, f"the Test Aether trial produced {rv['hits']} Aether hits"),
        (all(rv[f"flag_{i}"] for i in range(2)),
         "RV hits were not marked rv_mode in the event table"),
        (all(abs(rv[f"mult_{i}"] - rv[f"expected_{i}"]) <= 1e-6 for i in range(2)),
         f"RV crit_mult is {rv['mult_0']}/{rv['mult_1']}, expected the Crit Value "
         f"values {rv['expected_0']}/{rv['expected_1']}"),
        (all(abs(rv[f"mult_{i}"] - rv[f"manual_{i}"]) > 1e-3 for i in range(2)),
         "RV crit_mult still matches 1 + CR*CD"),
        # The aura-applying hit loses Cryo Resonance, the next one keeps it.
        (round((cr.get("two_cr") or 0.0), 4) == 0.15 and rv["reso_0"] == "OFF",
         "RV snapshot still applies Cryo Resonance to the aura-applying hit"),
        (rv["swirls"] > 0, "the RV run produced no stellar swirls"),
        (rv["rv_deterministic"],
         "RV reaction contributors still have crit variance (average != non-crit)"),
        (rv["manual_has_variance"],
         "Manual reaction contributors lost their crit variance"),
    ]
    rv_failures = [msg for ok, msg in rv_checks if not ok]
    failures.extend(rv_failures)
    if not rv_failures and verbose:
        print(f"[OK] 100% RV / KQM: crit_mult {rv['mult_1']} = CV - 1 (cv {rv['cv_1']}) "
              f"instead of 1+CR*CD {rv['manual_1']}; reactions are deterministic")

    # 3g. Buff catalogue integrity: buffs.py <-> stats_calc.FLAG_TO_BUFFS.
    cat = _run_buff_catalogue_check()
    if cat["missing"]:
        failures.append("buff dispatch references missing catalogue entries: "
                        + "; ".join(cat["missing"]))
    if cat["unreachable"]:
        failures.append("unreachable buff catalogue entries (not referenced by any "
                        "flag and not declared DORMANT): "
                        + ", ".join(sorted(cat["unreachable"])))
    if cat["malformed"]:
        failures.append("malformed non-constant buff descriptors: "
                        + "; ".join(cat["malformed"]))
    if not (cat["missing"] or cat["unreachable"] or cat["malformed"]) and verbose:
        print(f"[OK] buff catalogue consistent ({cat['referenced']} referenced, "
              f"{cat['dormant']} dormant, {cat['catalogue']} total entries)")

    # 4. Idempotence: display() must not duplicate events after evaluation
    n_before = len(events)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        timeline.display()
    n_after = len(timeline.global_events)
    if n_after != n_before:
        failures.append(f"evaluate_timeline not idempotent: {n_before} -> {n_after} events")
    elif verbose:
        print(f"[OK] idempotence preserved ({n_after} events after display())")

    # 5. Totals for review
    total = sum((e.get("average_damage", 0.0) or 0.0) for e in hit_events)
    if verbose:
        print(f"[INFO] hit_events={len(hit_events)} total_avg_dmg={total:,.1f}")

    # 2o. Anastasya kit: burst buff, A1, A4 jubilee + vortex lifecycle, extra
    #     stellar beat and Triumph arming.
    ana = _run_anastasya_check()
    ana_checks = [
        (ana["burst_on"] and ana["burst_casts"] > 0,
         "Anastasya burst buff never activated"),
        (abs((ana["burst_bonus_ally"] or 0.0) - 0.575) <= 1e-6,
         f"Anastasya burst stellar_bonus on allies is {ana['burst_bonus_ally']}, "
         f"expected 0.575 (burst lv13)"),
        (abs((ana["burst_bonus_self"] or 0.0) - 0.575) <= 1e-6,
         f"Anastasya burst stellar_bonus on herself is {ana['burst_bonus_self']}"),
        (ana["burst_offenders"] == 0,
         f"{ana['burst_offenders']} hits kept the burst buff past its 20s window"),
        (ana["a1_on"], "Anastasya A1 window never activated"),
        (abs((ana["a1_cd_ally"] or 0.0) - 0.16) <= 1e-9,
         f"Anastasya A1 crit DMG on allies is {ana['a1_cd_ally']}, expected 0.16"),
        (abs(ana["a1_cd_self"] or 0.0) <= 1e-12,
         f"Anastasya A1 applied to herself ({ana['a1_cd_self']})"),
        (ana["a1_offenders"] == 0,
         f"{ana['a1_offenders']} hits kept A1 past its 19s window"),
        (ana["swirl_found"], "no Stellar Swirl event found in rotation A"),
        (abs((ana["reaction_jubilee"] or 0.0) - 0.15) <= 1e-9,
         f"Anastasya A4 reaction jubilee is {ana['reaction_jubilee']}, expected 0.15"),
        (ana["reaction_jubilee_without_her"] == 0.0,
         "Anastasya A4 reaction jubilee applied without her in the party"),
        (ana["stellar_bonus_mult_ok"],
         "A4 reaction jubilee leaked into plain stellar damage"),
        (ana["reaction_ratio_err"] <= 1e-9,
         f"A4 reaction jubilee does not scale reaction damage exactly "
         f"(ratio error {ana['reaction_ratio_err']})"),
        (ana["jubilee_off_without_her"],
         "Anastasya Jubilee passive applied without her in the party"),
        (abs(ana["jubilee_share"] - ana["jubilee_expected"]) <= 1e-6,
         f"Anastasya Jubilee share is {ana['jubilee_share']}, expected "
         f"{ana['jubilee_expected']} (0.007% of her ATK)"),
        (ana["vortex_all_lv2"],
         "A4 did not spawn Stellar Vortices at level 2"),
        (ana["early_count"] > 0,
         "no early vortex detonation occurred with A4"),
        (ana["early_swirls"] == [4],
         f"A4 early detonation happens after {ana['early_swirls']} swirls, "
         f"expected [4] (spawn + 3)"),
        (all(n >= 6 for n in ana["baseline_early_swirls"]),
         f"baseline early detonation happened before 6 swirls "
         f"({ana['baseline_early_swirls']})"),
        (ana["extra_count"] > 0, "conditional extra stellar beat never fired"),
        (ana["extra_only_in_window"],
         "extra stellar beat fired outside the burst window"),
        (ana["extras_never_exceed_beats"],
         "more extra stellar beats than stellar beats"),
        (ana["no_extra_before_first_burst"],
         "extra stellar beat fired before her first burst cast"),
        (ana["triumph_count"] == 1,
         f"Triumph fired {ana['triumph_count']} times, expected 1 "
         f"(at {ana['triumph_times']})"),
        (ana["triumph_gap_ok"],
         f"Triumph fired before its delay ({ANASTASYA_TRIUMPH_DELAY}s) after the burst "
         f"cast (casts {ana['triumph_casts']}, hits {ana['triumph_times']})"),
        (ana["rotation_triumphs"] == ana["rotation_triumph_expected"],
         f"preset rotation has {ana['rotation_triumphs']} Triumph procs "
         f"({ana['rotation_triumph_times']}), expected {ana['rotation_triumph_expected']} "
         f"({ana['rotation_swap_ins']} loops => every loop from the 2nd)"),
        (ana["triumph_on_her_swap_in"],
         f"Triumph did not land on one of her swap-ins ({ana['rotation_triumph_times']})"),
        (ana["no_triumph_on_first_loop"],
         "Triumph proc'd on the first loop, before any burst cast"),
    ]
    ana_failures = [msg for ok, msg in ana_checks if not ok]
    failures.extend(ana_failures)
    if not ana_failures and verbose:
        print(f"[OK] Anastasya: burst buff (0.575/20s), A1 (+16% CD others/19s), "
              f"A4 reaction jubilee + Lv2 vortices, extra beat, Triumph")
        print(f"     Anastasya preset total_avg_dmg={ana['total']:,.1f}")

    # 2p. Editor catalogues + preset trial team gating.
    cat2 = _run_editor_catalogue_check()
    cat2_checks = [
        (cat2["faruzan_e_exists"], "faruzan_e field sequence missing from abilities.py"),
        (cat2["faruzan_e_same_swap"],
         "faruzan_e swap-out time differs from faruzan_q"),
        (cat2["faruzan_e_same_insert"],
         "faruzan_e insertion time differs from faruzan_q's burst cast"),
        (cat2["faruzan_e_is_collapse"],
         "faruzan_e does not call Pressurized Collapse only"),
        (cat2["faruzan_e_no_burst"], "faruzan_e contains a burst cast"),
        (cat2["filter_only_party"],
         "field_sequences_for() returned a sequence owned by a non-party character"),
        (cat2["filter_hides_outside"],
         "field_sequences_for() leaked a sequence of a character outside the party"),
        (cat2["abilities_for_anastasya"] == ["Skill Tap", "To the New World"],
         f"abilities_for('Anastasya') is {cat2['abilities_for_anastasya']}"),
        (cat2["abilities_for_absent"] == {},
         "abilities_for() returned abilities for a character that is not registered"),
        (cat2["internal_hidden"],
         "engine-injected abilities (Triumph / extra stellar) are offered by the editor"),
        (not cat2["trial_team_mismatches"],
         "preset trial team mismatches: " + "; ".join(cat2["trial_team_mismatches"])),
        (cat2["same_display_name"],
         "the two preset trials do not share the same display name"),
        (cat2["aether_team_only"], "Aether preset trial is offered for the Anastasya team"),
        (cat2["ana_team_only"], "Anastasya preset trial is offered for the Aether team"),
        (cat2["no_3_char_match"], "preset trial matched an incomplete team"),
        (cat2["timed_trial_not_offered"],
         "a time-capped trial is still offered in the preset pool"),
    ]
    cat2_failures = [msg for ok, msg in cat2_checks if not ok]
    failures.extend(cat2_failures)
    if not cat2_failures and verbose:
        print(f"[OK] editor catalogues: {cat2['sequence_count']} field sequences / "
              f"{cat2['ability_count']} abilities, party-gated; preset trials team-gated")

    # 2q. Save / Load build documents (export + import).
    save = _run_save_load_check()
    save_checks = [
        (save["schema"].startswith("2"), f"build document schema is {save['schema']}"),
        (save["substats_saved"], "artifact substats are not written to the build file"),
        (save["trial_saved"], "the custom trial is not written to the build file"),
        (not save["restore_warnings"],
         "loading a build reported warnings: " + "; ".join(save["restore_warnings"])),
        (not save["widget_mismatches"],
         "restored widget state differs from the saved one: "
         + ", ".join(save["widget_mismatches"])),
        (save["trial_restored"], "the saved trial does not come back with the build"),
        (save["enemy_restored"], "the enemy configuration is not restored"),
        (save["party_keys"] == ["Faruzan", "Mizuki"],
         f"rebuilt party is {save['party_keys']}, expected Faruzan + Mizuki"),
        (save["stats_match"],
         "rebuilt initial_stats differ from build_initial_stats (substats lost?)"),
        (save["editor_materialised"] and save["editor_queue"],
         "a loaded/preset trial could not be opened in the editor"),
        (save["legacy_ok"], "a schema 1.0 build file no longer loads"),
        (save["slot_cleanup"], "slots the file does not use keep stale characters"),
        (save["key_mismatches"] == [],
         "the importer writes keys the UI does not use: "
         + ", ".join(save["key_mismatches"])),
    ]
    save_failures = [msg for ok, msg in save_checks if not ok]
    failures.extend(save_failures)
    if not save_failures and verbose:
        print(f"[OK] save/load round-trip: gear + enemy + trial restored "
              f"({save['size']} byte document), loaded builds stay editable")

    if failures:
        print("\nSMOKE TEST FAILED:")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    print("\nSMOKE TEST PASSED")


if __name__ == "__main__":
    run()