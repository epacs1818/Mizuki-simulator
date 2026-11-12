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
     and cooldowns. Phases 2/3 cover the composition stats (A Thousand Floating
     Dreams, Jade Vista), the periodic/sigil windows and Rainbow Serpent's
     Rain Bow's off-field trigger.
 10. Diona kit: "Choice Treasures" (20s state opened by her tap OR hold skill hit) fires
     a 3-hit Icy Paw volley 0.270s after ANY Stellar Swirl (3.5s CD from the trigger),
     and her C6 burst cast buffs the ACTIVE character (+200 EM / +0.40 stellar_bonus)
     for the whole burst field, cast hit included.
 11. Triggered hits: every engine-injected proc takes its delay from abilities.py
     (Mizuki nuke 0.500, C1 mini nuke 0.0, Faruzan collapse 0.720, Diona paws
     0.270/0.360/0.360, Anastasya extra stellar/Triumph/C6 Triumph 0.010), lands at
     trigger + that delay, and respects its trigger-based cooldown.
 12. The Anastasya kit values (50.4% stellar swirl base, 0.354 burst bonus at B13)
     are pinned as literals, so an accidental drift cannot pass silently.
"""
from timeline import (
    RotationTimeline, SUCROSE_BURST_WINDOW, ANASTASYA_UNSEAL_DELAY,
    ANASTASYA_ACCOLADES_WINDOW, ANASTASYA_C6_TRIUMPH_CD,
    FARUZAN_COLLAPSE_CD, DIONA_CHOICE_TREASURES_WINDOW, DIONA_CHOICE_TREASURES_CD,
    DIONA_C6_WINDOW,
)
from abilities import (
    aether_n1, aether_skill, sucrose_skill, sucrose_burst,
    # The 13-tick skill is what the pre-existing Mizuki checks exercise.
    mizuki_pullout_13 as mizuki_skill,
)
# Field sequences live in presets.py (abilities.py holds only immutable Ability data).
from presets import aether_en1, odette_qe, sucrose_eq
from models import FieldSequence, Rotation, Trial, ActionCategory, AttackType
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
    """Builds an Odette QE run (burst+recast) and checks her SSD buff fires."""
    t = RotationTimeline(party=presets.DEFAULT_PARTY)
    t.add_trial(Trial(
        name="odette_qe", end_mode="time", end_time=8.0,
        rotations=[Rotation(name="r", sequences=[odette_qe], repetitions=1)],
    ))
    t.evaluate_timeline()
    return any(e.get("odette_ssd_state") == "ON"
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
    """Weapon phase 2: A Thousand Floating Dreams and Jade Vista (party
    composition), Wandering Evenstar (periodic stacks), Thrilling Tales
    (next-character proc) and Starsealed Edict (cast window + swirl stacks)."""
    from stats_calc import build_initial_stats, apply_weapon_party_stats, compute_flat_em

    out = {}
    aether = {"constellation": 0, "level": 90, "refinement": 1,
              "weapon": "New Bough", "artifact_set": "2p/2p ATK", "talents": "1/13/13"}

    # --- 1. Composition-dependent permanent stats (ATFD / Jade Vista) ---------
    # Both weapons count allies per element: same element -> EM, different
    # element -> a second stat. The element bonus lands on the HOLDER's own
    # element, so an Anemo holder always moves anemo_bonus.
    def composition_deltas(weapon, members, refinement=5):
        """(holder EM, holder anemo_bonus, holder ATK%, first ally's EM)."""
        party, raw, enriched = {}, {}, {}
        for index, name in enumerate(members):
            weapon_name = weapon if index == 0 else "New Bough"
            party_ref = refinement if index == 0 else 1
            party[name] = {"weapon": weapon_name, "refinement": party_ref}
            raw[name] = build_initial_stats(name, 90, weapon_name, "2p/2p EM", {}, {},
                                            refinement=party_ref)
            enriched[name] = dict(raw[name])
        apply_weapon_party_stats(enriched, party)
        holder = members[0]
        return (round(enriched[holder]["em"] - raw[holder]["em"], 3),
                round(enriched[holder]["anemo_bonus"] - raw[holder]["anemo_bonus"], 4),
                round(enriched[holder]["atk_percent"] - raw[holder]["atk_percent"], 4),
                round(enriched[members[1]]["em"] - raw[members[1]]["em"], 3))

    atfd = "A Thousand Floating Dreams"
    # Anemo holder: Sucrose shares her element, Aether/Odette are Cryo.
    out["atfd_mixed"] = composition_deltas(atfd, ["Mizuki", "Aether", "Odette", "Sucrose"])
    out["atfd_all_diff"] = composition_deltas(atfd, ["Mizuki", "Aether", "Odette", "Diona"])
    out["atfd_all_same"] = composition_deltas(atfd, ["Mizuki", "Sucrose", "Faruzan"])
    # Jade Vista: EM per SAME-element ally, ATK% per DIFFERENT-element ally.
    out["jade_mixed"] = composition_deltas(
        "Jade Vista", ["Faruzan", "Mizuki", "Sucrose", "Diona"], refinement=1)
    out["jade_pair"] = composition_deltas("Jade Vista", ["Diona", "Aether"])

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
                  and e.get("ability_name") == mizuki_skill.name
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

    # --- 8. Rainbow Serpent's Rain Bow: only OFF-field holder hits count ------
    # Diona's Icy Paw volley is a genuine off-field hit (a swirl triggers it while
    # she is benched), so it is the natural trigger. Her own on-field skill hits
    # must never arm the passive.
    import abilities as ab
    rainbow = "Rainbow Serpent's Rain Bow"
    diona_bow = {"constellation": 6, "level": 90, "refinement": 1,
                 "weapon": rainbow, "artifact_set": "2p/2p EM", "talents": "1/10/10"}

    on_field = _run_sequences_trial(["Diona E"], {"Diona": dict(diona_bow)}, 4.0)
    out["rainbow_onfield_never_on"] = not any(
        e.get("rainbow_bow_state") == "ON" for e in on_field.global_events)

    tail = FieldSequence("Tail", "Aether", swap_out_time=12.0)
    for offset in (0.5, 4.5, 9.5, 11.5):
        tail.add_ability(offset, aether_n1)
    party = {"Diona": dict(diona_bow), "Mizuki": dict(mizuki_base),
             "Aether": dict(aether_base)}
    t = RotationTimeline(party=party)
    t.add_trial(Trial(name="rainbow", end_mode="time", end_time=30.0,
                      rotations=[Rotation(name="r", sequences=[
                          presets.STANDARD_FIELD_SEQUENCES["Diona HEQ"],
                          presets.STANDARD_FIELD_SEQUENCES["Mizuki E (Pullout)"],
                          tail], repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    paws = [e for e in hits if e.get("ability_name") == ab.diona_choice_treasures.name]
    on_paws = [e for e in paws if e.get("rainbow_bow_state") == "ON"]
    out["rainbow_paws"] = len(paws)
    out["rainbow_opens"] = bool(on_paws)
    # The hit that opens the window resolves first (house rule: read pre-event).
    out["rainbow_first_paw_off"] = bool(paws) and paws[0].get("rainbow_bow_state") == "OFF"
    # A volley more than 8s after the first ON proves the refresh.
    first_on = on_paws[0]["global_time"] if on_paws else None
    out["rainbow_refreshes"] = any(e["global_time"] > first_on + 8.05 for e in on_paws)
    out["rainbow_expires"] = bool(hits) and hits[-1].get("rainbow_bow_state") == "OFF"
    out["rainbow_atk_pct"] = (
        round(_flag_delta(t, on_paws[0], "Diona", "rainbow_bow_state", "atk_percent"), 4)
        if on_paws else None)

    # Data nobody can pick is dead data: both bows must be offered by the UI.
    try:
        with open("streamlit_app.py", encoding="utf-8") as handle:
            app_source = handle.read()
    except OSError:
        app_source = ""
    out["bow_ui"] = [name for name in (rainbow, "Jade Vista")
                     if '("%s", [1, 2, 3, 4, 5])' % name not in app_source]

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

        # Artifact sets with permanent stats of their own.
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
    from presets import sucrose_e

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
    """Odette's "Snow Swan's Dream" (SSD): self-only below C4, talent-scaled, 20s
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
    on = [e for e in hits if e.get("odette_ssd_state") == "ON"]
    out["on"] = bool(on)
    out["alive_at_15s"] = any(e["global_time"] > 15.0 for e in on)
    out["off_after_20s"] = all(e.get("odette_ssd_state") != "ON"
                               for e in hits if e["global_time"] > 21.0)
    if on:
        out["stellar"] = round(_flag_delta(t, on[0], "Odette", "odette_ssd_state",
                                           "Stellar Bonus"), 4)
        out["not_party"] = round(_flag_delta(t, on[0], "Aether", "odette_ssd_state",
                                             "Stellar Bonus"), 4)
    else:
        out["stellar"] = out["not_party"] = None
    return out


def _run_odette_constellation_check() -> dict:
    """Odette C1/C2/C4/C6 mechanics, each isolated by constellation level.

    Layout (her QE preset, then a watcher so off-field time exists):
        burst cast @2.16  -> shadow + SSD start (both end @22.16)
        recast cast @2.25 -> recast stellar @3.121 (C1/C4 triggers) -> swap-out @3.451
        watcher hits @4.751 / 6.451 / 19.451 / 22.451

    C1  extra 4.500 MV stellar hit 0.010s after the recast's stellar hit; max stacks
        6 and a 2/s transfer (C0: 4 stacks, 1/s).
    C2  +7% ATK per Marvelous stack (party) on top of A1's +15% stellar_bonus.
    C4  SSD shares half its value with the OTHERS; ANY party stellar hit triggers her
        0.990 MV hit, 3.5s CD measured from the trigger.
    C6  she keeps 6 stacks off-field while the party still ramps at 2/s, and the shadow
        grants +0.25 elevation to the OTHERS / +0.45 to her.
    """
    out = {}

    def build(cons):
        party = {
            "Odette": {"constellation": cons, "level": 90, "refinement": 1,
                       "weapon": "New Bough", "artifact_set": "2p/2p ATK",
                       "talents": "1/13/13"},
            "Aether": {"constellation": 0, "level": 90, "refinement": 1,
                       "weapon": "New Bough", "artifact_set": "2p/2p ATK",
                       "talents": "1/13/13"},
        }
        watcher = FieldSequence("Watcher", "Aether", swap_out_time=24.0)
        watcher.add_ability(1.3, aether_n1)      # 4.751: 1.3s off-field -> 2 stacks
        watcher.add_ability(3.0, aether_n1)      # 6.451: 3.0s off-field -> 6 stacks
        watcher.add_ability(16.0, aether_n1)     # 19.451: still inside the shadow
        watcher.add_ability(19.0, aether_n1)     # 22.451: past it
        t = RotationTimeline(party=party)
        t.add_trial(Trial(name=f"odette_c{cons}", end_mode="time", end_time=30.0,
                          rotations=[Rotation(name="r", sequences=[odette_qe, watcher],
                                              repetitions=1)]))
        t.evaluate_timeline()
        return t

    def hits(t):
        return [e for e in t.global_events if e.get("event_type") == "HIT"]

    def closest(t, char, when):
        return min((e for e in hits(t) if e.get("character") == char),
                   key=lambda e: abs(e["global_time"] - when))

    def stack_delta(t, event, char, stat):
        on = _buffed_stats(t, event, char)[stat]
        stripped = dict(event)
        stripped["marvelous_stacks"] = 0
        return round(on - _buffed_stats(t, stripped, char)[stat], 6)

    tl = {cons: build(cons) for cons in (0, 1, 2, 3, 4, 6)}

    # ---- C1: triggered extra stellar hit on the recast's stellar hit ----------
    out["c1"] = {}
    for cons in (0, 1):
        c1 = [e for e in hits(tl[cons]) if e.get("ability_name") == "C1 Extra Stellar"]
        out["c1"][cons] = {
            "count": len(c1),
            "delay": round(c1[0]["global_time"] - 3.121, 3) if c1 else None,
            "mv": c1[0].get("motion_value") if c1 else None,
            "stellar": bool(c1) and c1[0].get("category") == ActionCategory.STELLAR_DMG,
            "owner": c1[0].get("character") if c1 else None,
        }

    # ---- C4: extra 0.990 MV stellar hit driven by ANY party stellar hit -------
    out["c4"] = {}
    for cons in (3, 4):
        evs = hits(tl[cons])
        c4 = [e for e in evs if e.get("ability_name") == "C4 Extra Stellar"]
        stellar = [e["global_time"] for e in evs
                   if e.get("category") == ActionCategory.STELLAR_DMG
                   and e.get("ability_name") not in ("C1 Extra Stellar",
                                                     "C4 Extra Stellar")]
        delays = []
        for e in c4:
            trigger = max((s for s in stellar if s < e["global_time"] - 1e-9),
                          default=None)
            if trigger is not None:
                delays.append(round(e["global_time"] - trigger, 6))
        gaps = [round(b["global_time"] - a["global_time"], 6)
                for a, b in zip(c4, c4[1:])]
        out["c4"][cons] = {
            "count": len(c4),
            "delays": delays,
            "gaps": gaps,
            "mv": c4[0].get("motion_value") if c4 else None,
            "owner": c4[0].get("character") if c4 else None,
        }

    # ---- Marvelous stacks: pool size and transfer behaviour ------------------
    out["stacks"] = {}
    for cons, t in tl.items():
        evs = hits(t)
        out["stacks"][cons] = {
            "own_max": max(int(e.get("marvelous_stacks", 0) or 0)
                           for e in evs if e.get("character") == "Odette"),
            "party_max": max(int(e.get("marvelous_stacks", 0) or 0)
                             for e in evs if e.get("character") != "Odette"),
            "own_after_swap": [int(e.get("marvelous_stacks", 0) or 0)
                               for e in evs
                               if e.get("character") == "Odette"
                               and e.get("odette_shadow_state") == "ON"
                               and e["global_time"] > 3.451],
            "party_at_6_451": int(closest(t, "Aether", 6.451).get("marvelous_stacks", 0) or 0),
            "party_after_window": int(closest(t, "Aether", 22.451).get("marvelous_stacks", 0) or 0),
        }

    # ---- C2: ATK% and stellar_bonus per stack --------------------------------
    t2 = tl[2]
    hit6 = closest(t2, "Aether", 6.451)
    out["c2_atk_per_stack"] = stack_delta(t2, hit6, "Aether", "atk_percent")
    out["c2_stellar_per_stack"] = stack_delta(t2, hit6, "Aether", "Stellar Bonus")

    # ---- SSD sharing at C4 vs C3 --------------------------------------------
    t3, t4 = tl[3], tl[4]
    out["ssd_others_c4"] = round(_flag_delta(
        t4, closest(t4, "Aether", 6.451), "Aether", "odette_ssd_state", "Stellar Bonus"), 4)
    out["ssd_self_c4"] = round(_flag_delta(
        t4, closest(t4, "Odette", 6.720), "Odette", "odette_ssd_state", "Stellar Bonus"), 4)
    out["ssd_others_c3"] = round(_flag_delta(
        t3, closest(t3, "Aether", 6.451), "Aether", "odette_ssd_state", "Stellar Bonus"), 4)
    out["ssd_self_c3"] = round(_flag_delta(
        t3, closest(t3, "Odette", 6.720), "Odette", "odette_ssd_state", "Stellar Bonus"), 4)

    # ---- C6: elevation to the party and to herself --------------------------
    t6 = tl[6]
    out["elev_others_c6"] = round(_buffed_stats(
        t6, closest(t6, "Aether", 6.451), "Aether")["Elevation Mult"], 4)
    out["elev_self_c6"] = round(_buffed_stats(
        t6, closest(t6, "Odette", 6.720), "Odette")["Elevation Mult"], 4)
    out["elev_others_after"] = round(_buffed_stats(
        t6, closest(t6, "Aether", 22.451), "Aether")["Elevation Mult"], 4)
    out["elev_others_c2"] = round(_buffed_stats(
        t2, closest(t2, "Aether", 6.451), "Aether")["Elevation Mult"], 4)
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
    # A hand-written entry may carry only the UI label.
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


def _run_hit_catalogue_check() -> dict:
    """abilities.py data integrity: every sequence casts something, every hit scales.

    Catches the mistakes that are otherwise silent: a FieldSequence whose add_ability()
    call never ran (empty step), a scaling_key that does not exist in skill_scalings, a
    hit with a zero motion value, two definitions sharing one display name (the registry
    keeps only the first), a sequence that ends before its last hit, and a renamed entry
    whose old name is still referenced somewhere.
    """
    import abilities as ab

    out = {}
    out["sequences"] = len(presets.FIELD_SEQUENCE_REGISTRY)
    out["abilities"] = sum(len(map_) for map_ in ab.ABILITY_REGISTRY.values())
    # Sequences are declared in presets.py, abilities in abilities.py: scan both.
    out["empty_bindings"] = sorted(
        attr for attr, value in vars(presets).items()
        if isinstance(value, ab.FieldSequence) and not value.calls
    )

    unresolved, zero_mv, bad_keys, talent_crash = [], [], [], []
    for ability_map in ab.ABILITY_REGISTRY.values():
        for ability in ability_map.values():
            # Re-configuring the talent level must work for EVERY ability: a malformed
            # scaling_key (e.g. a 4-tuple that still carries the talent level) crashes
            # timeline.add_field_sequence() as soon as a party sets talents.
            try:
                ab.update_ability_talent_level(copy.deepcopy(ability), 10)
            except Exception as exc:  # noqa: BLE001 - reported, not raised
                talent_crash.append(f"{ability.character} / {ability.name}: {exc!r}")
            for hit in ability.hits:
                if hit.scaling_key:
                    if len(hit.scaling_key) != 3:
                        bad_keys.append(f"{ability.name} / {hit.name}: {hit.scaling_key}")
                        continue
                    char_key, cat_key, sub_key = hit.scaling_key
                    try:
                        value = ab.get_ability_motion_value(
                            char_key, cat_key, sub_key, ability.talent_level)
                    except (KeyError, IndexError):
                        unresolved.append(f"{ability.name} / {hit.name}")
                        continue
                    if value <= 0:
                        zero_mv.append(f"{ability.name} / {hit.name}")
                elif hit.motion_value <= 0 and hit.category != ActionCategory.STELLAR_REACTION:
                    zero_mv.append(f"{ability.name} / {hit.name}")
    out["unresolved"] = unresolved
    out["zero_mv"] = zero_mv
    out["bad_scaling_keys"] = bad_keys
    out["talent_crash"] = talent_crash

    # The registries keep the first definition of a name, so a duplicate is invisible.
    # Intentional variants (Aether's burst) share a name by design, and an
    # object imported into the other module is the SAME object, not a duplicate.
    seen, duplicates, seen_ids = {}, [], set()
    for module in (ab, presets):
        for attr, value in vars(module).items():
            if not isinstance(value, (ab.FieldSequence, ab.Ability)):
                continue
            if getattr(value, "name", None) in ab.VARIANT_ABILITY_NAMES:
                continue
            if id(value) in seen_ids:
                continue
            seen_ids.add(id(value))
            key = (type(value).__name__, getattr(value, "character", None), value.name)
            if key in seen:
                duplicates.append(
                    f"{value.character} / {value.name} ({seen[key]} vs {module.__name__}.{attr})")
            seen.setdefault(key, f"{module.__name__}.{attr}")
    out["duplicates"] = duplicates

    # Informational: the engine keeps late hits (off-field damage is a feature here), so
    # this is not an error - it just lists sequences whose field ends before the last hit.
    late_hits = []
    for name, seq in presets.FIELD_SEQUENCE_REGISTRY.items():
        last_hit = 0.0
        for call in seq.calls:
            for hit in call.ability.hits:
                last_hit = max(last_hit, call.start_time + hit.relative_delay)
        if seq.calls and seq.swap_out_time < last_hit - 1e-9:
            late_hits.append(name)
    out["late_hit_sequences"] = sorted(late_hits)

    # What the editor offers for Mizuki (module-level sequence = registered).
    out["mizuki_ui"] = sorted(presets.field_sequences_for(["Mizuki"]))
    return out


def _run_mizuki_burst_check() -> dict:
    """Mizuki's burst is a pure hit register: BURST-typed, and no Dreamdrifter leak.

    Her DDS is entered by a "Cast" SKILL hit (timeline.py), so the burst cast must be
    named "Burst_Cast" and its hits tagged BURST - otherwise the burst would switch her
    skill stance on and poison every following snapshot.
    """
    import abilities as ab

    out = {}
    burst = ab.ABILITY_REGISTRY["Mizuki"]["Mizuki Burst"]
    out["hit_count"] = len(burst.hits)
    out["cast_name"] = burst.hits[0].name
    out["all_burst"] = all(h.attack_type == AttackType.BURST for h in burst.hits)
    out["positive_mv"] = all(h.motion_value > 0 for h in burst.hits)

    # Burst-only probe: the presets also ship a skill+burst combo, so the burst cannot be
    # checked through a preset sequence without pulling her skill (and DDS) into it.
    burst_only = FieldSequence("BurstProbe", "Mizuki", swap_out_time=12.8)
    burst_only.add_ability(0.301, burst)

    t = RotationTimeline(party={k: dict(v) for k, v in presets.DEFAULT_PARTY.items()})
    t.add_trial(Trial(name="mz_burst", end_mode="time", end_time=20.0,
                      rotations=[Rotation(name="r", sequences=[burst_only],
                                          repetitions=1)]))
    t.evaluate_timeline()
    hits = [e for e in t.global_events
            if e.get("event_type") == "HIT" and e.get("character") == "Mizuki"]
    out["engine_hits"] = len(hits)
    out["engine_cast_name"] = hits[0].get("hit_name") if hits else None
    out["dds_leak"] = any(e.get("dreamdrifter_state") == "ON" for e in t.global_events)
    out["all_damage_positive"] = all((e.get("average_damage") or 0.0) > 0 for e in hits)
    out["quill_leak"] = any((e.get("quills_total") or 0.0) > 0 for e in hits)
    return out



def _run_buff_catalogue_check() -> dict:
    """Structural integrity of the buff catalogue (buffs.py) vs its dispatch table.

    Catches a catalogue entry that no timeline flag can ever reach (dead data), a
    dispatch key that no longer exists, and a non-constant descriptor that the basis
    engine could not resolve.

    Every REACHABLE non-constant entry is also exercised numerically by the other
    checks in this file (Mizuki swirl/VBTD/C6/C2, Odette burst+A4+jubilee, Aether
    A4+jubilee, Faruzan C6 anemo bonus, Sucrose A4 share), so a wrong
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

    Covers: party-wide talent-scaled burst stellar_bonus (20s), Accolades (12% crit DMG
    for the whole party, 20s, inclusive on the skill Cast hit; shared/sealed once she
    bursts and swaps out), her Jubilee passive, the A4 reaction-only jubilee, the A4
    vortex lifecycle (spawn at Lv2, 3 further swirls to detonate), the conditional
    extra stellar beat while the burst is up, and Triumph's 15s seal -> unseal rule.
    """
    from abilities import anastasya_burst
    from damage_calc import calculate_damage

    out = {}

    # ---- 0. HARD-CODED KIT DATA (the "Tsaritsa Nerfs" round) -------------------
    # Commit 7d23982 lowered her stellar swirl MV (60.0 -> 50.4) and the burst
    # stellar bonus ([...0.575] -> [...0.354]). Those numbers are pinned as literals
    # here on purpose: the ENTIRE sim's Anastasya output hangs off them, so a silent
    # revert has to fail the suite instead of quietly inflating every total.
    from skill_scalings import CHARACTER_SKILLS
    _ana = CHARACTER_SKILLS["Anastasya"]
    out["swirl_mv_base"] = _ana["Skill"]["Palestar Crown Stellar Swirl DMG"]["scaling"][0]
    out["swirl_mv_lv13"] = _ana["Skill"]["Palestar Crown Stellar Swirl DMG"]["scaling"][12]
    out["tap_lv13"] = _ana["Skill"]["Instantaneous Tap DMG"]["scaling"][12]
    out["extra_stellar_lv13"] = _ana["Burst"]["Palestar Crown Extra Stellar Swirl DMG"]["scaling"][12]
    out["burst_bonus_lv13"] = _ana["Burst"]["To the New World Stellar Glimmer Reaction DMG Increase"]["scaling"][12]

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

    # ---- 2. Accolades (A1): 20s window, inclusive Cast hit, sealed/shared ----
    skill_casts = [e["global_time"] for e in hits
                   if e.get("ability_name") == "Skill Tap" and e.get("hit_name") == "Cast"]
    acc_hits = [e for e in hits if e.get("anastasya_accolades_state") == "ON"]
    out["acc_on"] = bool(acc_hits)
    if acc_hits:
        first = acc_hits[0]
        out["acc_first_is_cast"] = bool(skill_casts) and abs(
            first["global_time"] - min(skill_casts)) <= 1e-9
        out["acc_unsealed_ally"] = round(_flag_delta(
            timeline, first, "Mizuki", "anastasya_accolades_unsealed_state", "CD"), 4)
        out["acc_unsealed_self"] = round(_flag_delta(
            timeline, first, "Anastasya", "anastasya_accolades_unsealed_state", "CD"), 4)
        shared_hits = [e for e in hits
                       if e.get("anastasya_accolades_shared_state") == "ON"]
        out["acc_shared_on"] = bool(shared_hits)
        if shared_hits:
            ev = shared_hits[0]
            out["acc_shared_ally"] = round(_flag_delta(
                timeline, ev, "Mizuki", "anastasya_accolades_shared_state", "CD"), 4)
            out["acc_shared_self"] = round(_flag_delta(
                timeline, ev, "Anastasya", "anastasya_accolades_shared_state", "CD"), 4)
        else:
            out["acc_shared_ally"] = out["acc_shared_self"] = None
        out["acc_offenders"] = sum(
            1 for e in acc_hits
            if e["global_time"] > max([c for c in skill_casts if c <= e["global_time"]],
                                      default=-1e9) + ANASTASYA_ACCOLADES_WINDOW + 1e-6)
        out["acc_variants_exclusive"] = not any(
            e.get("anastasya_accolades_unsealed_state") == "ON"
            and e.get("anastasya_accolades_shared_state") == "ON" for e in hits)
    else:
        out["acc_first_is_cast"] = False
        out["acc_unsealed_ally"] = out["acc_unsealed_self"] = None
        out["acc_shared_on"] = False
        out["acc_shared_ally"] = out["acc_shared_self"] = None
        out["acc_offenders"] = -1
        out["acc_variants_exclusive"] = False

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

    # The preset's swirl spacing depends on the rotation and can fall outside the 3s
    # vortex life, so the "spawn at Lv2 + 3 further swirls" rule is also asserted
    # directly on the lifecycle object, independent of any timing.
    from mechanics import StellarVortex
    probe = StellarVortex({"anemo_contributor": "Mizuki",
                           "cryo_contributors": ["Odette"]},
                          0.0, start_level=2, detonation_swirls=4)
    inherits = [probe.inherit_swirl({"anemo_contributor": "Faruzan",
                                     "cryo_contributors": ["Odette"]})
                for _ in range(3)]
    out["probe_early_on_third"] = bool(inherits[-1][0]) and "Early" in inherits[-1][1]
    out["probe_not_early_before"] = not any(exploded for exploded, _r in inherits[:2])
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
    # Triggered-delay convention: the extra hit lands 0.010s after the stellar beat.
    beat_times = {round(e["global_time"], 6) for e in beats}
    out["extra_delay_ok"] = bool(extra) and all(
        round(e["global_time"] - 0.010, 6) in beat_times for e in extra)

    # ---- 7. Triumph: armed by the seal (burst + swap-out), fires on her next
    #         swap-in once ANASTASYA_UNSEAL_DELAY has passed ----
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
    tr_seals = [e["global_time"] for e in t_tr.global_events
                if e.get("event_type") == "SWAP_OUT" and e.get("character") == "Anastasya"]
    out["triumph_count"] = len(tr_hits)
    out["triumph_times"] = [round(e["global_time"], 3) for e in tr_hits]
    out["triumph_casts"] = [round(c, 3) for c in tr_casts]
    out["triumph_seals"] = [round(c, 3) for c in tr_seals]
    out["triumph_gap_ok"] = all(
        e["global_time"] >= max([s for s in tr_seals if s <= e["global_time"]],
                                default=1e9) + ANASTASYA_UNSEAL_DELAY - 1e-6
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
        any(abs(e["global_time"] - (s["global_time"] + 0.010)) <= 1e-9
            for s in ana_swap_ins)
        for e in rot_triumphs)
    out["no_triumph_on_first_loop"] = (
        bool(ana_swap_ins)
        and all(e["global_time"] > ana_swap_ins[0]["global_time"] + 1e-9 for e in rot_triumphs))
    return out

def _run_anastasya_constellation_check() -> dict:
    """Anastasya C1/C2/C4/C6, each isolated by constellation level.

    Everything runs on the preset Anastasya loop so the real cycle happens:
        skill Cast @0.601 (Accolades + Love, UNSEALED) -> burst @2.371 ->
        swap-out @2.851 (SEALED) -> the 8s linger keeps it shared after the unseal.
    """
    from abilities import anastasya_tap, anastasya_burst, anastasya_triumph
    out = {}

    def build(cons):
        party = _anastasya_party()
        party["Anastasya"]["constellation"] = cons
        t = RotationTimeline(party=party)
        t.add_trial(presets.STANDARD_TRIALS[
            "Mizuki Sac Frag Pull out 6x rotations (Anastasya)"])
        t.evaluate_timeline()
        return t

    def hits(t):
        return [e for e in t.global_events if e.get("event_type") == "HIT"]

    def closest(t, char, when):
        return min((e for e in hits(t) if e.get("character") == char),
                   key=lambda e: abs(e["global_time"] - when))

    def delta(t, ev, char, flag, stat):
        on = _buffed_stats(t, ev, char)[stat]
        stripped = dict(ev)
        stripped[flag] = "OFF"
        return round(on - _buffed_stats(t, stripped, char)[stat], 6)

    tl = {cons: build(cons) for cons in (0, 1, 2, 4, 5, 6)}
    out["totals"] = {
        cons: round(sum((e.get("average_damage", 0.0) or 0.0) for e in hits(t)), 1)
        for cons, t in tl.items()
    }

    # ---- Accolades: unsealed (inclusive cast hit) and shared/sealed --------
    out["acc"] = {}
    for cons in (0, 1, 4):
        t = tl[cons]
        cast = next(e for e in hits(t)
                    if e.get("ability_name") == "Skill Tap" and e.get("hit_name") == "Cast")
        shared = next(e for e in hits(t)
                      if e.get("anastasya_accolades_shared_state") == "ON")
        out["acc"][cons] = {
            "cast_cd_self": delta(t, cast, "Anastasya", "anastasya_accolades_unsealed_state", "CD"),
            "cast_cd_ally": delta(t, cast, "Mizuki", "anastasya_accolades_unsealed_state", "CD"),
            "cast_atk_cryo": delta(t, cast, "Odette", "anastasya_accolades_unsealed_state", "atk_percent"),
            "cast_em_anemo": delta(t, cast, "Mizuki", "anastasya_accolades_unsealed_state", "em"),
            "shared_cd_self": delta(t, shared, "Anastasya", "anastasya_accolades_shared_state", "CD"),
            "shared_cd_ally": delta(t, shared, "Mizuki", "anastasya_accolades_shared_state", "CD"),
            "shared_atk_cryo": delta(t, shared, "Odette", "anastasya_accolades_shared_state", "atk_percent"),
            "shared_em_anemo": delta(t, shared, "Mizuki", "anastasya_accolades_shared_state", "em"),
            "shared_atk_self": delta(t, shared, "Anastasya", "anastasya_accolades_shared_state", "atk_percent"),
            "shared_em_self": delta(t, shared, "Anastasya", "anastasya_accolades_shared_state", "em"),
        }

    # ---- Love (C2): 30s window + permanent elevation ----------------------
    out["love"] = {}
    for cons in (1, 2, 6):
        t = tl[cons]
        mid = closest(t, "Mizuki", 8.0)
        out["love"][cons] = {
            "flag": any(e.get("anastasya_love_state") == "ON" for e in hits(t)),
            "stellar_cd": delta(t, mid, "Mizuki", "anastasya_love_state", "Stellar CD"),
            "elevation": round(_buffed_stats(t, mid, "Mizuki")["Elevation Mult"], 6),
        }

    # ---- C6 Triumph: every ally swap-in while Love is up -------------------
    out["c6"] = {}
    for cons in (5, 6):
        t = tl[cons]
        procs = [e for e in hits(t) if e.get("ability_name") == "C6 Triumph"]
        ally_ins = [(e["global_time"], e.get("character"))
                    for e in t.global_events
                    if e.get("event_type") == "SWAP_IN" and e.get("character") != "Anastasya"]
        delay_ok, per_char = True, {}
        for e in procs:
            trig = max((s for s in ally_ins if s[0] <= e["global_time"] - 1e-9),
                       default=(None, None), key=lambda s: s[0])
            if trig[0] is None or abs(e["global_time"] - (trig[0] + 0.010)) > 1e-9:
                delay_ok = False
            per_char.setdefault(trig[1], []).append(e["global_time"])
        out["c6"][cons] = {
            "count": len(procs),
            "delay_ok": delay_ok,
            "cd_ok": all(all(b - a >= ANASTASYA_C6_TRIUMPH_CD - 1e-9
                             for a, b in zip(ts, ts[1:]))
                         for ts in per_char.values()),
            "max_per_char": max((len(ts) for ts in per_char.values()), default=0),
            "mv": procs[0].get("motion_value") if procs else None,
            "expected_mv": 2.5 * anastasya_triumph.hits[0].motion_value,
            "owner": procs[0].get("character") if procs else None,
        }

    # ---- seal / unseal / 8s linger (dedicated timeline) --------------------
    setup = FieldSequence("AnaSetup", "Anastasya", swap_out_time=3.0)
    setup.add_ability(0.5, anastasya_tap)       # Cast @0.5, burst @2.0, seal @3.0
    setup.add_ability(2.0, anastasya_burst)
    filler = FieldSequence("Filler", "Aether", swap_out_time=17.0)
    filler.add_ability(5.0, aether_n1)          # 8.0s: still sealed
    second = FieldSequence("AnaSecond", "Anastasya", swap_out_time=3.0)
    second.add_ability(0.5, anastasya_tap)      # swap-in @20.0 (unseal), Cast @20.5
    tail = FieldSequence("Tail", "Aether", swap_out_time=8.0)
    tail.add_ability(5.1, aether_n1)            # 28.1s: the 8s linger (ended 28.0) is over
    probe_party = _anastasya_party()
    probe_party["Anastasya"]["constellation"] = 1
    tp = RotationTimeline(party=probe_party)
    tp.add_trial(Trial(name="unseal", end_mode="time", end_time=35.0,
                       rotations=[Rotation(name="r",
                                           sequences=[setup, filler, second, tail],
                                           repetitions=1)]))
    tp.evaluate_timeline()
    before = closest(tp, "Aether", 8.0)
    during = closest(tp, "Anastasya", 20.5)
    after = closest(tp, "Aether", 28.1)
    out["linger"] = {
        "sealed_before_unseal": before.get("anastasya_sealed_state") == "ON",
        "shared_during_linger": (during.get("anastasya_accolades_shared_state") == "ON"
                                 and during.get("anastasya_sealed_state") == "ON"),
        "unsealed_after_linger": (after.get("anastasya_accolades_unsealed_state") == "ON"
                                  and after.get("anastasya_sealed_state") == "OFF"),
        "no_reseal_without_burst": after.get("anastasya_sealed_state") == "OFF",
    }
    return out


def _diona_party(constellation: int = 6) -> dict:
    """Diona + Mizuki: her skill opens the state, Mizuki's skill supplies the swirls."""
    return {
        "Diona": {"constellation": constellation, "level": 90, "refinement": 1,
                  "weapon": "Favonius Warbow", "artifact_set": "Noblesse Oblige",
                  "talents": "1/10/10"},
        "Mizuki": {"constellation": 2, "level": 90, "refinement": 5,
                   "weapon": "Sacrificial Fragments", "artifact_set": "2p/2p EM",
                   "talents": "10/13/13"},
    }


def _run_sequences_trial(names, party, end_time: float):
    """Evaluate *names* (STANDARD_FIELD_SEQUENCES keys) back to back in one trial."""
    timeline = RotationTimeline(party=party)
    timeline.add_trial(Trial(
        name="seqs", end_mode="time", end_time=end_time,
        rotations=[Rotation(
            name="r",
            sequences=[presets.STANDARD_FIELD_SEQUENCES[n] for n in names],
            repetitions=1)]))
    timeline.evaluate_timeline()
    return timeline


def _hit_time(event) -> float:
    return round(event["global_time"], 3)


def _run_diona_check() -> dict:
    """Diona kit: Choice Treasures state + Icy Paw volleys, and the C6 burst buff.

    Choice Treasures: her tap OR hold skill hit opens a 20s state (refreshed). While it
    is up, a Stellar Swirl triggered by ANY character fires a 3-hit Icy Paw volley that
    starts 0.270s after the trigger (3.5s CD, measured from the trigger).
    C6: her burst cast hit gives the ACTIVE character +200 EM and +0.40 stellar_bonus
    for the whole burst field (11.75s), INCLUDING the cast hit itself.
    """
    import abilities as ab

    out = {}

    # ---- 1. The state: opened by either skill, 20s, refreshed by the next cast ----
    out["window"] = DIONA_CHOICE_TREASURES_WINDOW
    out["cd"] = DIONA_CHOICE_TREASURES_CD
    tap_tl = _run_sequences_trial(["Diona E"], _diona_party(), 3.0)
    hold_tl = _run_sequences_trial(["Diona HE"], _diona_party(), 3.0)
    out["ct_on_after_tap"] = any(e.get("diona_ct_state") == "ON" for e in tap_tl.global_events)
    out["ct_on_after_hold"] = any(e.get("diona_ct_state") == "ON" for e in hold_tl.global_events)

    # Refresh + expiry: her tap at 0.66 opens the window until 20.66, her hold at 2.07
    # refreshes it until 22.07. Anastasya's 10 skill beats (3.42 .. 23.22) are the probe.
    refresh_party = dict(_diona_party())
    refresh_party["Anastasya"] = {"constellation": 0, "level": 90, "refinement": 1,
                                  "weapon": "Favonius Warbow", "artifact_set": "2p/2p ATK",
                                  "talents": "1/13/13"}
    refresh_tl = _run_sequences_trial(["Diona E", "Diona HE", "Anastasya E"],
                                      refresh_party, 26.0)
    probe_hits = [e for e in refresh_tl.global_events
                  if e.get("event_type") == "HIT" and e.get("character") == "Anastasya"]
    between = [e for e in probe_hits if 20.66 < e["global_time"] <= 22.07]
    after = [e for e in probe_hits if e["global_time"] > 22.07 + 1e-9]
    out["ct_refresh_hits"] = [_hit_time(e) for e in between]
    out["ct_refresh_on"] = bool(between) and all(
        e.get("diona_ct_state") == "ON" for e in between)
    out["ct_late_hits"] = [_hit_time(e) for e in after]
    out["ct_expires"] = bool(after) and all(
        e.get("diona_ct_state") == "OFF" for e in after)

    # ---- 2. No state -> no paws, however many swirls happen ----
    # (Anastasya supplies the Cryo, Mizuki the Anemo: plenty of Stellar Swirls, but
    # Diona never presses her skill, so the Choice Treasures state never opens.)
    idle_party = dict(_diona_party())
    idle_party["Anastasya"] = {"constellation": 0, "level": 90, "refinement": 1,
                               "weapon": "Favonius Warbow", "artifact_set": "2p/2p ATK",
                               "talents": "1/13/13"}
    idle_tl = _run_sequences_trial(["Anastasya E", "Mizuki E (Pullout)"], idle_party, 16.0)
    paws_name = ab.diona_choice_treasures.name
    out["paws_without_state"] = len(
        [e for e in idle_tl.global_events if e.get("ability_name") == paws_name])
    out["swirls_without_state"] = len(
        [e for e in idle_tl.global_events if e.get("hit_name") == "Stellar_Swirl_Hit"])

    # ---- 3. Volleys inside a real rotation (hold + burst, then Mizuki's pull-out) ----
    timeline = _run_sequences_trial(["Diona HEQ", "Mizuki E (Pullout)"], _diona_party(), 16.0)
    events = timeline.global_events
    paw_hits = [e for e in events if e.get("ability_name") == paws_name]
    swirl_times = [e["global_time"] for e in events if e.get("hit_name") == "Stellar_Swirl_Hit"]
    out["paw_count"] = len(paw_hits)
    out["paw_owner_ok"] = bool(paw_hits) and all(
        e.get("character") == "Diona" for e in paw_hits)
    out["paw_shape_ok"] = bool(paw_hits) and all(
        e.get("category") == ActionCategory.STANDARD_DMG
        and e.get("attack_type") == AttackType.SKILL for e in paw_hits)
    out["paw_aura_ok"] = bool(paw_hits) and all(
        (e.get("elem_app") == "1U") == (i % 3 == 0) for i, e in enumerate(paw_hits))

    volleys = [paw_hits[i:i + 3] for i in range(0, len(paw_hits), 3)]
    volley_errors, volley_triggers = [], []
    first_delay = ab.diona_choice_treasures.hits[0].relative_delay
    expected_offsets = [round(h.relative_delay - first_delay, 6)
                        for h in ab.diona_choice_treasures.hits]
    for volley in volleys:
        if len(volley) != 3:
            volley_errors.append(f"{_hit_time(volley[0])}: partial volley ({len(volley)} paws)")
            continue
        first = volley[0]["global_time"]
        earlier = [s for s in swirl_times if s <= first + 1e-9]
        if not earlier:
            volley_errors.append(f"{_hit_time(volley[0])}: no swirl trigger")
            continue
        trigger = earlier[-1]
        volley_triggers.append(trigger)
        if abs((first - trigger) - first_delay) > 1e-6:
            volley_errors.append(
                f"{_hit_time(volley[0])}: first paw {first - trigger:.3f}s after the trigger")
        offsets = [round(v["global_time"] - first, 6) for v in volley]
        if offsets != expected_offsets:
            volley_errors.append(
                f"{_hit_time(volley[0])}: offsets {offsets} != {expected_offsets}")
    out["volley_count"] = len(volleys)
    out["volley_errors"] = volley_errors
    out["volley_trigger_gaps"] = [round(b - a, 3)
                                  for a, b in zip(volley_triggers, volley_triggers[1:])]
    out["volley_cd_ok"] = all(
        gap >= DIONA_CHOICE_TREASURES_CD - 1e-6 for gap in out["volley_trigger_gaps"])

    # ---- 4. C6: value, target scope, cast-hit inclusion, window, constellation gate ----
    out["c6_window"] = DIONA_C6_WINDOW
    cast = [e for e in events if e.get("character") == "Diona"
            and e.get("ability_name") == "Diona Burst" and e.get("hit_name") == "Burst Cast"]
    out["c6_cast_hits"] = len(cast)
    out["c6_includes_cast_hit"] = bool(cast) and all(
        e.get("diona_c6_state") == "ON" for e in cast)
    if cast:
        cast_time = cast[0]["global_time"]
        burst_hits = [e for e in events if e.get("character") == "Diona"
                      and e.get("ability_name") == "Diona Burst"]
        last_tick = max(burst_hits, key=lambda e: e["global_time"])
        out["c6_last_tick_on"] = last_tick.get("diona_c6_state") == "ON"
        out["c6_last_tick_offset"] = round(last_tick["global_time"] - cast_time, 6)
        out["c6_on_past_window"] = sum(
            1 for e in events if e.get("diona_c6_state") == "ON"
            and e["global_time"] > cast_time + DIONA_C6_WINDOW + 1e-9)
    else:
        out["c6_last_tick_on"] = False
        out["c6_last_tick_offset"] = None
        out["c6_on_past_window"] = -1

    # Values isolated from every EM share: Diona + Faruzan, ACTIVE = Faruzan, so
    # Diona's own (off-field) stats must NOT move.
    probe_party = {
        "Diona": _diona_party()["Diona"],
        "Faruzan": {"constellation": 6, "level": 90, "refinement": 1,
                    "weapon": "Favonius Warbow", "artifact_set": "Instructor",
                    "talents": "1/13/13"},
    }
    probe_tl = RotationTimeline(party=probe_party)
    probe_ev = {"event_type": "HIT", "character": "Faruzan",
                "category": ActionCategory.STANDARD_DMG, "element": "Anemo",
                "attack_type": AttackType.SKILL, "active_character": "Faruzan",
                "diona_c6_state": "ON"}
    out["c6_em_active"] = _flag_delta(probe_tl, probe_ev, "Faruzan", "diona_c6_state", "EM")
    out["c6_stellar_active"] = _flag_delta(probe_tl, probe_ev, "Faruzan", "diona_c6_state",
                                           "Stellar Bonus")
    out["c6_em_offfield_owner"] = _flag_delta(probe_tl, probe_ev, "Diona", "diona_c6_state", "EM")

    # C5 must never receive it (the UI only offers C6, the engine gates it anyway).
    c5_events = _run_sequences_trial(["Diona HEQ"], _diona_party(5), 6.0).global_events
    out["c5_never_on"] = not any(e.get("diona_c6_state") == "ON" for e in c5_events)
    return out


def _run_triggered_ability_check(ana=None) -> dict:
    """Every triggered hit reads its delay from abilities.py - never from the engine.

    Audit table (the number is the FIRST hit's relative_delay, i.e. the trigger delay;
    every hit of a triggered ability lands at trigger_time + its own relative_delay):
        Mizuki VBTD nuke ....... mizuki_nuke_hit                (0.500)
        Mizuki C1 mini nuke .... mizuki_c1_mini_nuke_hit        (0.000)
        Faruzan collapse ....... faruzan_pressurized_collapse   (0.720)
        Diona Icy Paws ......... diona_choice_treasures         (0.270/0.360/0.360)
        Anastasya extra stellar  anastasya_extra_stellar        (0.010)
        Anastasya Triumph ...... anastasya_triumph              (0.010, trigger = her swap-in)
        Anastasya C6 Triumph ... anastasya_c6_triumph           (0.010, trigger = an ally's swap-in)
        Odette C1 extra stellar  odette_c1_stellar_hit          (0.010)
        Odette C4 extra stellar  odette_c4_stellar_hit          (0.010)
    """
    import abilities as ab

    out = {}
    templates = {
        "Mizuki VBTD nuke": (ab.mizuki_nuke_hit, 0.500),
        "Mizuki C1 mini nuke": (ab.mizuki_c1_mini_nuke_hit, 0.000),
        "Faruzan collapse": (ab.faruzan_pressurized_collapse.hits[0], 0.720),
        "Diona Icy Paws tick 1": (ab.diona_choice_treasures.hits[0], 0.270),
        "Diona Icy Paws tick 2": (ab.diona_choice_treasures.hits[1], 0.360),
        "Diona Icy Paws tick 3": (ab.diona_choice_treasures.hits[2], 0.360),
        "Anastasya extra stellar": (ab.anastasya_extra_stellar.hits[0], 0.010),
        "Anastasya Triumph": (ab.anastasya_triumph.hits[0], 0.010),
        "Anastasya C6 Triumph": (ab.anastasya_c6_triumph.hits[0], 0.010),
        "Odette C1 extra stellar": (ab.odette_c1_stellar_hit, 0.010),
        "Odette C4 extra stellar": (ab.odette_c4_stellar_hit, 0.010),
    }
    out["delays"] = {label: hit.relative_delay for label, (hit, _exp) in templates.items()}
    out["expected"] = {label: exp for label, (_hit, exp) in templates.items()}
    out["delay_mismatch"] = sorted(
        label for label, (hit, exp) in templates.items()
        if abs(hit.relative_delay - exp) > 1e-12)

    # The convention itself: the shared helper schedules at trigger + relative_delay,
    # and a 0.0 delay is honoured instead of being treated as "missing".
    probe_tl = RotationTimeline(party={})
    trigger = {"global_time": 10.0, "character": "Someone", "event_type": "HIT",
               "hit_name": "Trigger", "active_character": "Someone"}
    convention_errors = []
    for label, (hit, _exp) in templates.items():
        built = probe_tl._triggered_hit_event(hit, trigger, 10.0, label)
        if abs(built["global_time"] - (10.0 + hit.relative_delay)) > 1e-12:
            convention_errors.append(
                f"{label}: {built['global_time']} != 10 + {hit.relative_delay}")
        if abs(built["hit_offset"] - hit.relative_delay) > 1e-12:
            convention_errors.append(f"{label}: hit_offset is {built['hit_offset']}")
    out["convention_errors"] = convention_errors
    out["engine_windows"] = {
        "Faruzan collapse CD": FARUZAN_COLLAPSE_CD,
        "Diona paw CD": DIONA_CHOICE_TREASURES_CD,
        "Diona state": DIONA_CHOICE_TREASURES_WINDOW,
        "Diona C6": DIONA_C6_WINDOW,
    }

    # ---- Engine level: Faruzan collapses land 0.720s after a NON-collapse hit, and
    #      the 3.0s internal CD is measured from the TRIGGER (not from the collapse).
    timeline = RotationTimeline(party=presets.DEFAULT_PARTY)
    timeline.add_trial(presets.STANDARD_TRIALS["Mizuki Sac Frag Pull out 6x rotations"])
    timeline.evaluate_timeline()
    events = timeline.global_events
    collapse_name = ab.faruzan_pressurized_collapse.name
    collapses = [e for e in events if e.get("ability_name") == collapse_name]
    other_hit_times = {round(e["global_time"], 6) for e in events
                       if e.get("event_type") == "HIT"
                       and e.get("ability_name") != collapse_name}
    delay = ab.faruzan_pressurized_collapse.hits[0].relative_delay
    out["collapse_count"] = len(collapses)
    out["collapse_delay_ok"] = bool(collapses) and all(
        round(e["global_time"] - delay, 6) in other_hit_times for e in collapses)
    out["collapse_gaps"] = [round(b["global_time"] - a["global_time"], 3)
                            for a, b in zip(collapses, collapses[1:])]
    out["collapse_cd_ok"] = all(
        gap >= FARUZAN_COLLAPSE_CD - 1e-6 for gap in out["collapse_gaps"])

    # ---- Engine level: Anastasya's extra stellar beat keeps its 0.0 delay (it lands on
    #      the beat itself). Reuses the Anastasya run when run() already has it.
    if ana is None:
        ana = _run_anastasya_check()
    out["extra_count"] = ana["extra_count"]
    out["extra_delay_ok"] = ana["extra_delay_ok"]
    return out


def _run_editor_catalogue_check() -> dict:
    """Editor catalogues + preset trial team gating (what the UI is allowed to offer).

    Every FieldSequence / Ability must be reachable through the registries (sequences
    from presets.py, abilities from abilities.py), ownership must resolve, and a preset
    trial must advertise exactly the team its rotation actually plays.
    """
    import abilities

    out = {}
    seq_names = {seq.name for seq in presets.FIELD_SEQUENCE_REGISTRY.values()}
    ab_names = {(char, name) for char, m in abilities.ABILITY_REGISTRY.items() for name in m}
    out["sequence_count"] = len(seq_names)
    out["ability_count"] = len(ab_names)

    # Faruzan E: her skill CAST only (the collapse is a triggered ability now).
    fe = presets.FIELD_SEQUENCE_REGISTRY.get("FaruzanESwap")
    fq = presets.FIELD_SEQUENCE_REGISTRY.get("FaruzanQSwap")
    out["faruzan_e_exists"] = fe is not None
    if fe is not None and fq is not None:
        out["faruzan_e_same_swap"] = abs(fe.swap_out_time - fq.swap_out_time) <= 1e-9
        out["faruzan_e_same_insert"] = abs(fe.calls[0].start_time - fq.calls[0].start_time) <= 1e-9
        out["faruzan_e_is_skill_cast"] = (len(fe.calls) == 1
                                          and fe.calls[0].ability.name == "Skill Cast")
        out["faruzan_e_no_burst"] = all(c.ability.name != "Elemental Burst" for c in fe.calls)
    else:
        out["faruzan_e_same_swap"] = out["faruzan_e_same_insert"] = False
        out["faruzan_e_is_skill_cast"] = out["faruzan_e_no_burst"] = False

    # Party-gated filtering helper used by the UI.
    only_mizuki = presets.field_sequences_for(["Mizuki"])
    out["filter_only_party"] = bool(only_mizuki) and all(
        seq.character == "Mizuki" for seq in only_mizuki.values())
    out["filter_hides_outside"] = "AnastasyaEQ" not in only_mizuki
    out["abilities_for_anastasya"] = sorted(abilities.abilities_for("Anastasya").keys())
    # A character that is not registered at all must yield NOTHING.
    out["abilities_for_absent"] = abilities.abilities_for("Nobody")
    # Engine-injected procs stay registered but are never offered by the editor.
    out["internal_hidden"] = ({"Triumph", "C6 Triumph", "Palestar Crown Extra Stellar"}
                              <= set(abilities.ABILITY_REGISTRY.get("Anastasya", {}))
                              and not ({"Triumph", "C6 Triumph", "Palestar Crown Extra Stellar"}
                                       & set(abilities.abilities_for("Anastasya"))))
    # Triggered abilities: registered, never castable, never inside a field sequence.
    out["triggered_registered"] = {
        "Diona Choice Treasures": "Diona Choice Treasures" in abilities.ABILITY_REGISTRY.get("Diona", {}),
        "Pressurized Collapse": "Pressurized Collapse" in abilities.ABILITY_REGISTRY.get("Faruzan", {}),
    }
    out["triggered_hidden"] = {
        "Diona": "Diona Choice Treasures" not in abilities.abilities_for("Diona"),
        "Faruzan": "Pressurized Collapse" not in abilities.abilities_for("Faruzan"),
    }
    out["triggered_in_sequences"] = sorted({
        f"{seq.character} / {seq.name}: {call.ability.name}"
        for seq in presets.FIELD_SEQUENCE_REGISTRY.values()
        for call in seq.calls
        if call.ability.name in abilities.ENGINE_INTERNAL_ABILITIES
    })

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

    # Sucrose rounds. N1 has to be a real Ability: it was once written with a stray
    # trailing comma, which turned it into a 1-tuple (unregistered, and "Sucrose QN1"
    # crashed the field-sequence builder). The two preset trials must also build and
    # evaluate without a cooldown error.
    out["sucrose_n1_registered"] = "N1" in abilities.abilities_for("Sucrose")
    sucrose = {"constellation": 6, "level": 90, "refinement": 1,
               "weapon": "The Widsith (Average)", "artifact_set": "2p/2p EM",
               "talents": "1/10/10"}
    anastasya = {"constellation": 6, "level": 90, "refinement": 1,
                 "weapon": "Silverdawn", "artifact_set": "2p/2p ATK",
                 "talents": "1/13/13"}

    def run_sucrose_trial(key, extra, exact=False):
        """{rotations, duration, hits, total} or {error} for a preset trial.

        exact=True builds the party from *extra* alone (the combination trials are
        gated on exactly four characters); otherwise DEFAULT_PARTY is the base.
        """
        party = {} if exact else copy.deepcopy(presets.DEFAULT_PARTY)
        party.update({name: dict(data) for name, data in extra.items()})
        timeline = RotationTimeline(party=party)
        trial = presets.STANDARD_TRIALS[key]
        try:
            duration = timeline.add_trial(trial)
            timeline.evaluate_timeline()
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            return {"error": repr(exc), "rotations": len(trial.rotations)}
        hits = [e for e in timeline.global_events if e.get("event_type") == "HIT"]
        return {"error": None,
                "rotations": len(trial.rotations),
                "duration": round(duration, 3),
                "hits": len(hits),
                "total": round(sum(e.get("average_damage") or 0.0 for e in hits), 1)}

    out["sucrose_aether_trial"] = run_sucrose_trial(
        "Sucrose Mizuki, Alternating 3 and 4 Nukes", {"Sucrose": dict(sucrose)})
    out["sucrose_anastasya_trial"] = run_sucrose_trial(
        "Sucrose Mizuki, Alternating 3 and 4 Nukes (Anastasya)",
        {"Sucrose": dict(sucrose), "Anastasya": dict(anastasya)})
    out["sucrose_standard_steps"] = [seq.name for seq in
                                     presets.STANDARD_ROTATIONS["sucrose_standard"].sequences]
    aether_rounds = presets.STANDARD_TRIALS["Sucrose Mizuki, Alternating 3 and 4 Nukes"]
    ana_rounds = presets.STANDARD_TRIALS["Sucrose Mizuki, Alternating 3 and 4 Nukes (Anastasya)"]
    out["sucrose_trials_gated"] = (
        aether_rounds.matches_party(presets.MIZUKI_SUCROSE_TEAM)
        and not aether_rounds.matches_party(presets.MIZUKI_SUCROSE_ANASTASYA_TEAM)
        and ana_rounds.matches_party(presets.MIZUKI_SUCROSE_ANASTASYA_TEAM)
        and not ana_rounds.matches_party(presets.MIZUKI_SUCROSE_TEAM))

    # --- The other combination teams (always Mizuki + two of the Cryo trio + a
    # 4th slot of Sucrose / Faruzan). Two of those parties had no trial at all.
    mizuki_entry = presets.DEFAULT_PARTY["Mizuki"]
    aether_entry = presets.DEFAULT_PARTY["Aether"]
    odette_entry = presets.DEFAULT_PARTY["Odette"]
    faruzan_entry = presets.DEFAULT_PARTY["Faruzan"]
    out["triple_cryo_trial"] = run_sucrose_trial(
        "Triple Cryo Rotation",
        {"Mizuki": mizuki_entry, "Aether": aether_entry,
         "Odette": odette_entry, "Anastasya": anastasya}, exact=True)
    out["sucrose_aether_anastasya_trial"] = run_sucrose_trial(
        "Sucrose Mizuki, Alternating 3 and 4 Nukes (Aether + Anastasya)",
        {"Mizuki": mizuki_entry, "Aether": aether_entry,
         "Anastasya": anastasya, "Sucrose": sucrose}, exact=True)
    out["sacfrag_aether_anastasya_trial"] = run_sucrose_trial(
        "Mizuki Sac Frag Pull out 6x rotations (Aether + Anastasya)",
        {"Mizuki": mizuki_entry, "Aether": aether_entry,
         "Anastasya": anastasya, "Faruzan": faruzan_entry}, exact=True)
    out["triple_cryo_steps"] = [seq.name for seq in
                                presets.STANDARD_ROTATIONS["triple_cryo_standard"].sequences]
    out["combo_trials_gated"] = (
        presets.STANDARD_TRIALS["Triple Cryo Rotation"]
        .matches_party(presets.MIZUKI_TRIPLE_CRYO_TEAM)
        and not presets.STANDARD_TRIALS["Triple Cryo Rotation"]
        .matches_party(presets.MIZUKI_SUCROSE_TEAM)
        and presets.STANDARD_TRIALS["Sucrose Mizuki, Alternating 3 and 4 Nukes (Aether + Anastasya)"]
        .matches_party(presets.MIZUKI_SUCROSE_AETHER_ANASTASYA_TEAM)
        and not presets.STANDARD_TRIALS["Sucrose Mizuki, Alternating 3 and 4 Nukes (Aether + Anastasya)"]
        .matches_party(presets.MIZUKI_SUCROSE_TEAM)
        and presets.STANDARD_TRIALS["Mizuki Sac Frag Pull out 6x rotations (Aether + Anastasya)"]
        .matches_party(presets.MIZUKI_SACFRAG_AETHER_ANASTASYA_TEAM)
        and not presets.STANDARD_TRIALS["Mizuki Sac Frag Pull out 6x rotations (Aether + Anastasya)"]
        .matches_party(presets.MIZUKI_SACFRAG_TEAM))

    # Every Mizuki + (two of the Cryo trio) + (Sucrose | Faruzan) party must be
    # playable without building a custom trial.
    expected_teams = [
        ["Mizuki", "Aether", "Odette", "Sucrose"],
        ["Mizuki", "Anastasya", "Odette", "Sucrose"],
        ["Mizuki", "Aether", "Anastasya", "Sucrose"],
        ["Mizuki", "Aether", "Odette", "Faruzan"],
        ["Mizuki", "Anastasya", "Odette", "Faruzan"],
        ["Mizuki", "Aether", "Anastasya", "Faruzan"],
    ]
    out["missing_combination_trials"] = [
        team for team in expected_teams
        if not any(t.matches_party(team) for t in presets.STANDARD_TRIALS.values())]
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

    # A slot the file does not fill must be emptied, not left holding an old character.
    small_state = {"char_3": "Odette", "char_4": "Aether"}
    build_io.apply_build_document(
        build_io.parse_document(json.dumps({
            "schema_version": build_io.SCHEMA_VERSION,
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


def _run_trial_duration_check() -> dict:
    """Trial duration = the configured window (time) or the last swap-out (last_swap).

    A run must not modify the trial it was given, so the same preset can be
    simulated again with exactly the same numbers.
    """
    preset = presets.STANDARD_TRIALS["Mizuki Sac Frag Pull out 6x rotations"]
    field_sum = sum(seq.swap_out_time * rot.repetitions
                    for rot in preset.rotations for seq in rot.sequences)
    before = preset.end_time
    last_swap = RotationTimeline(party=presets.DEFAULT_PARTY).add_trial(preset)
    time_duration = RotationTimeline(party=presets.DEFAULT_PARTY).add_trial(
        copy.deepcopy(presets.TEST_TRIAL_30S))
    return {
        "mode": preset.end_mode,
        "time": time_duration,
        "last_swap": last_swap,
        "field_sum": field_sum,
        "end_untouched": preset.end_time == before,
    }


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

    # 3b. Odette kit auditors (shadow, Marvelous, C2 shred) on the standard run.
    odette_marvel_on = "Odette" in party and any(int(e.get("marvelous_stacks", 0) or 0) > 0 for e in hit_events)
    odette_shadow_on = "Odette" in party and any(e.get("odette_shadow_state") == "ON" for e in hit_events)
    odette_c2_on = "Odette" in party and any(e.get("odette_c2_state") == "ON" for e in hit_events)
    if odette_marvel_on and verbose:
        print("[OK] Odette Marvelous activated")
    if not odette_marvel_on:
        failures.append("Odette Marvelous never activated")
    if not odette_shadow_on:
        failures.append("Odette shadow state never activated")
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

    # 3c-ter. Odette's constellations (C1 trigger, C2 stacks, C4 share/proc, C6).
    oc = _run_odette_constellation_check()
    oc_checks = [
        (oc["c1"][0]["count"] == 0, "Odette's C1 extra stellar hit fired below C1"),
        (oc["c1"][1]["count"] == 1,
         f"Odette C1 extra hits: {oc['c1'][1]['count']} (expected 1 per recast)"),
        (abs((oc["c1"][1]["delay"] or -1) - 0.010) <= 1e-9,
         f"Odette C1 extra hit delay is {oc['c1'][1]['delay']}, expected 0.010"),
        (abs((oc["c1"][1]["mv"] or 0) - 4.5) <= 1e-12,
         f"Odette C1 extra hit MV is {oc['c1'][1]['mv']}, expected 4.500"),
        (oc["c1"][1]["stellar"] and oc["c1"][1]["owner"] == "Odette",
         "Odette C1 extra hit is not an Odette stellar hit"),
        (oc["stacks"][0]["own_max"] == 4 and oc["stacks"][0]["party_max"] == 4,
         f"C0 Marvelous pool is {oc['stacks'][0]} (expected 4)"),
        (oc["stacks"][1]["own_max"] == 6 and oc["stacks"][1]["party_max"] == 6,
         f"C1 Marvelous pool is {oc['stacks'][1]} (expected 6)"),
        (oc["stacks"][6]["party_at_6_451"] == 6,
         f"C6 party stacks after 3s off-field are "
         f"{oc['stacks'][6]['party_at_6_451']}, expected 6"),
        (bool(oc["stacks"][6]["own_after_swap"])
         and all(s == 6 for s in oc["stacks"][6]["own_after_swap"]),
         f"C6 Odette lost her own stacks off-field: {oc['stacks'][6]['own_after_swap']}"),
        (any(s < 6 for s in oc["stacks"][2]["own_after_swap"]),
         "C2 Odette did not transfer her stacks off-field"),
        (oc["stacks"][6]["party_after_window"] == 0
         and oc["stacks"][0]["party_after_window"] == 0,
         "Marvelous stacks outlived the shadow window"),
        (abs(oc["c2_atk_per_stack"] - 0.42) <= 1e-9,
         f"C2 ATK% at 6 stacks is {oc['c2_atk_per_stack']}, expected 0.42"),
        (abs(oc["c2_stellar_per_stack"] - 0.90) <= 1e-9,
         f"A1 stellar_bonus at 6 stacks is {oc['c2_stellar_per_stack']}, expected 0.90"),
        (oc["c4"][3]["count"] == 0,
         f"Odette's C4 extra hit fired below C4 ({oc['c4'][3]['count']})"),
        (oc["c4"][4]["count"] >= 4, f"only {oc['c4'][4]['count']} C4 extra hits fired"),
        (all(abs(d - 0.010) <= 1e-9 for d in oc["c4"][4]["delays"]),
         f"C4 extra hit delays are {oc['c4'][4]['delays']}, expected 0.010"),
        (all(g >= 3.5 - 1e-9 for g in oc["c4"][4]["gaps"]),
         f"C4 extra hits are closer than its 3.5s trigger CD ({oc['c4'][4]['gaps']})"),
        (abs((oc["c4"][4]["mv"] or 0) - 0.99) <= 1e-12,
         f"C4 extra hit MV is {oc['c4'][4]['mv']}, expected 0.990"),
        (oc["c4"][4]["owner"] == "Odette", "C4 extra hit is not credited to Odette"),
        (abs(oc["ssd_others_c4"] - 0.31) <= 1e-6,
         f"C4 shared SSD for the party is {oc['ssd_others_c4']}, expected 0.31"),
        (abs(oc["ssd_others_c3"] or 0.0) <= 1e-12,
         f"SSD leaked to the party below C4 ({oc['ssd_others_c3']})"),
        (abs(oc["ssd_self_c4"] - 0.62) <= 1e-6
         and abs(oc["ssd_self_c3"] - 0.62) <= 1e-6,
         f"Odette's own SSD is {oc['ssd_self_c4']} (C4) / {oc['ssd_self_c3']} (C3), "
         f"expected 0.62"),
        (abs(oc["elev_others_c6"] - 0.25) <= 1e-9,
         f"C6 elevation for the party is {oc['elev_others_c6']}, expected 0.25"),
        (abs(oc["elev_self_c6"] - 0.45) <= 1e-9,
         f"C6 elevation for Odette is {oc['elev_self_c6']}, expected 0.45"),
        (abs(oc["elev_others_after"] or 0.0) <= 1e-12,
         f"C6 elevation outlived the shadow ({oc['elev_others_after']})"),
        (abs(oc["elev_others_c2"] or 0.0) <= 1e-12,
         f"C6 elevation activated below C6 ({oc['elev_others_c2']})"),
    ]
    oc_failures = [msg for ok, msg in oc_checks if not ok]
    failures.extend(oc_failures)
    if not oc_failures and verbose:
        print(f"[OK] Odette constellations: C1 +{oc['c1'][1]['delay']}s {oc['c1'][1]['mv']} MV, "
              f"C4 {oc['c4'][4]['count']} procs (gaps {oc['c4'][4]['gaps']}), "
              f"SSD shared {oc['ssd_others_c4']}, "
              f"C6 elevation {oc['elev_self_c6']}/{oc['elev_others_c6']}")

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
        (wp2["atfd_mixed"] == (64.0, 0.52, 0.0, 48.0),
         f"ATFD mixed party gave {wp2['atfd_mixed']}, expected (64.0, 0.52, 0.0, 48.0)"),
        (wp2["atfd_all_diff"] == (0.0, 0.78, 0.0, 48.0),
         f"ATFD all-different party gave {wp2['atfd_all_diff']}, "
         f"expected (0.0, 0.78, 0.0, 48.0)"),
        (wp2["atfd_all_same"] == (128.0, 0.0, 0.0, 48.0),
         f"ATFD all-same party gave {wp2['atfd_all_same']}, "
         f"expected (128.0, 0.0, 0.0, 48.0)"),
        (wp2["atfd_idempotent"],
         "A Thousand Floating Dreams party stats are not idempotent"),
        (wp2["jade_mixed"] == (128.0, 0.0, 0.12, 0.0),
         f"Jade Vista mixed party gave {wp2['jade_mixed']}, expected (128.0, 0.0, 0.12, 0.0)"),
        (wp2["jade_pair"] == (128.0, 0.0, 0.0, 0.0),
         f"Jade Vista same-element party gave {wp2['jade_pair']}, "
         f"expected (128.0, 0.0, 0.0, 0.0)"),
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
        (wp3["rainbow_onfield_never_on"],
         "Rain Bow armed from an on-field hit by its own holder"),
        (wp3["rainbow_opens"],
         f"Rain Bow never armed from an off-field hit "
         f"({wp3['rainbow_paws']} Icy Paw hits seen)"),
        (wp3["rainbow_first_paw_off"],
         "the Icy Paw that opens the Rain Bow window buffed itself"),
        (wp3["rainbow_refreshes"],
         "Rain Bow did not refresh on a later off-field hit"),
        (wp3["rainbow_expires"], "Rain Bow window outlived its 8s"),
        (abs((wp3["rainbow_atk_pct"] or 0.0) - 0.28) <= 1e-6,
         f"Rain Bow ATK% is {wp3['rainbow_atk_pct']}, expected 0.28 at R1"),
        (wp3["bow_ui"] == [],
         f"bows missing from the UI weapon catalogue: {wp3['bow_ui']}"),
    ]
    phase3_failures = [msg for ok, msg in phase3_checks if not ok]
    failures.extend(phase3_failures)
    if not phase3_failures and verbose:
        print("[OK] weapons phase 3: permanents + Whitelake/Finale/Breeze/Elegy/"
              "NewBough/Silverdawn/RainBow behave")

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

    # 3q. abilities.py hit catalogue: new hits must register, scale and fit their field.
    hits_cat = _run_hit_catalogue_check()
    hits_checks = [
        (not hits_cat["empty_bindings"],
         "field sequences with no hits (a lost add_ability() call): "
         + ", ".join(hits_cat["empty_bindings"])),
        (not hits_cat["unresolved"],
         "hits whose scaling_key is not in skill_scalings: "
         + ", ".join(hits_cat["unresolved"])),
        (not hits_cat["zero_mv"],
         "hits with a zero motion value: " + ", ".join(hits_cat["zero_mv"])),
        (not hits_cat["duplicates"],
         "duplicate ability/sequence display names: " + ", ".join(hits_cat["duplicates"])),
        (not hits_cat["bad_scaling_keys"],
         "scaling_key must be exactly (character, category, sub ability); the talent "
         "LEVEL is never part of it: " + "; ".join(hits_cat["bad_scaling_keys"])),
        (not hits_cat["talent_crash"],
         "update_ability_talent_level() fails on these abilities (a party that sets "
         "talents would crash): " + "; ".join(hits_cat["talent_crash"])),
        ({"Burst Pullout 4 Nukes", "Skill Pullout 1 Nuke", "Skill Pullout 2 Nukes",
          "Skill Pullout 3 Nukes", "Skill Pullout 4 Nukes"}
         <= set(hits_cat["mizuki_ui"]),
         f"the editor catalogue for Mizuki is {hits_cat['mizuki_ui']}"),
    ]
    hits_failures = [msg for ok, msg in hits_checks if not ok]
    failures.extend(hits_failures)
    if not hits_failures and verbose:
        print(f"[OK] hit catalogue: {hits_cat['sequences']} sequences / "
              f"{hits_cat['abilities']} abilities, every hit scales and fits its field")

    # 3r. Mizuki's burst: hit register only (BURST damage, no Dreamdrifter leakage).
    mz = _run_mizuki_burst_check()
    mz_checks = [
        (mz["hit_count"] == 9, f"Mizuki's burst has {mz['hit_count']} hits, expected 9"),
        (mz["cast_name"] == "Burst_Cast",
         f"Mizuki's burst cast hit is {mz['cast_name']!r}; it must be 'Burst_Cast' so her "
         f"burst does not enter Dreamdrifter"),
        (mz["all_burst"], "Mizuki's burst hits are not AttackType.BURST"),
        (mz["positive_mv"], "Mizuki's burst has zero-motion hits"),
        (mz["engine_hits"] == 9,
         f"the burst field produced {mz['engine_hits']} hits, expected 9"),
        (mz["engine_cast_name"] == "Burst_Cast",
         f"the engine cast hit is {mz['engine_cast_name']!r}"),
        (not mz["dds_leak"], "Mizuki's burst switched Dreamdrifter ON"),
        (not mz["quill_leak"], "Mizuki's burst picked up VBTD quill damage"),
        (mz["all_damage_positive"], "Mizuki's burst produced a zero-damage hit"),
    ]
    mz_failures = [msg for ok, msg in mz_checks if not ok]
    failures.extend(mz_failures)
    if not mz_failures and verbose:
        print("[OK] Mizuki burst: 9 BURST hits, no Dreamdrifter / quill leakage")

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
        # Pinned post-nerf kit data (see section 0 of _run_anastasya_check).
        (abs(ana["swirl_mv_base"] - 50.4) <= 1e-9,
         f"Anastasya Palestar Crown Stellar Swirl DMG base is {ana['swirl_mv_base']}, "
         f"expected 50.4 (nerfed from 60.0)"),
        (abs(ana["swirl_mv_lv13"] - 107.1) <= 1e-9,
         f"Anastasya stellar swirl MV at lv13 is {ana['swirl_mv_lv13']}, expected 107.1 "
         f"(50.4 base)"),
        (abs(ana["tap_lv13"] - 251.175) <= 1e-9,
         f"Anastasya Instantaneous Tap DMG at lv13 is {ana['tap_lv13']}, expected 251.175"),
        (abs(ana["extra_stellar_lv13"] - 35.7) <= 1e-9,
         f"Anastasya extra stellar swirl DMG at lv13 is {ana['extra_stellar_lv13']}, "
         f"expected 35.7"),
        (abs(ana["burst_bonus_lv13"] - 0.354) <= 1e-12,
         f"Anastasya burst stellar bonus at lv13 is {ana['burst_bonus_lv13']}, "
         f"expected 0.354 (nerfed from 0.575)"),
        (ana["burst_on"] and ana["burst_casts"] > 0,
         "Anastasya burst buff never activated"),
        (abs((ana["burst_bonus_ally"] or 0.0) - 0.354) <= 1e-6,
         f"Anastasya burst stellar_bonus on allies is {ana['burst_bonus_ally']}, "
         f"expected 0.354 (burst lv13, nerfed)"),
        (abs((ana["burst_bonus_self"] or 0.0) - 0.354) <= 1e-6,
         f"Anastasya burst stellar_bonus on herself is {ana['burst_bonus_self']}, "
         f"expected 0.354 (burst lv13, nerfed)"),
        (ana["burst_offenders"] == 0,
         f"{ana['burst_offenders']} hits kept the burst buff past its 20s window"),
        (ana["acc_on"] and ana["acc_first_is_cast"],
         "Accolades does not start on (and include) her skill Cast hit"),
        (abs((ana["acc_unsealed_ally"] or 0.0) - 0.12) <= 1e-9
         and abs((ana["acc_unsealed_self"] or 0.0) - 0.12) <= 1e-9,
         f"unsealed Accolades is {ana['acc_unsealed_ally']} (ally) / "
         f"{ana['acc_unsealed_self']} (self), expected 0.12 for both"),
        (ana["acc_shared_on"], "Accolades never became the shared/sealed version"),
        (abs((ana["acc_shared_ally"] or 0.0) - 0.16) <= 1e-9
         and abs(ana["acc_shared_self"] or 0.0) <= 1e-12,
         f"shared Accolades at C0 is {ana['acc_shared_ally']} (ally) / "
         f"{ana['acc_shared_self']} (self), expected 0.16 / 0"),
        (ana["acc_variants_exclusive"],
         "both Accolades variants were active on the same event"),
        (ana["acc_offenders"] == 0,
         f"{ana['acc_offenders']} hits kept Accolades past its 20s window"),
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
        (ana["probe_early_on_third"] and ana["probe_not_early_before"],
         "A4's level-2 vortex must detonate on its 3rd inherited swirl (and not before)"),
        (all(n == 4 for n in ana["early_swirls"]),
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
         f"Triumph fired before {ANASTASYA_UNSEAL_DELAY}s after the seal "
         f"(seals {ana['triumph_seals']}, hits {ana['triumph_times']})"),
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
        print(f"[OK] Anastasya: burst buff (0.354/20s, nerfed), Accolades (12%/20s, "
              f"shared/sealed tiers), A4 reaction jubilee + Lv2 vortices, extra beat, Triumph")
        print(f"     Anastasya preset total_avg_dmg={ana['total']:,.1f}")

    # 2n-ter. Anastasya constellations: Accolades tiers, Love, C6 Triumph.
    anc = _run_anastasya_constellation_check()
    acc0, acc1, acc4 = anc["acc"][0], anc["acc"][1], anc["acc"][4]
    anc_checks = [
        (abs(acc0["cast_cd_self"] - 0.12) <= 1e-9
         and abs(acc0["cast_cd_ally"] - 0.12) <= 1e-9,
         f"C0 unsealed Accolades is {acc0['cast_cd_self']}/{acc0['cast_cd_ally']}, "
         f"expected 0.12 for both"),
        (abs(acc0["shared_cd_ally"] - 0.16) <= 1e-9 and abs(acc0["shared_cd_self"]) <= 1e-12,
         f"C0 shared Accolades is {acc0['shared_cd_ally']}/{acc0['shared_cd_self']}, "
         f"expected 0.16 (others) / 0 (her)"),
        (abs(acc1["cast_atk_cryo"] - 0.15) <= 1e-9
         and abs(acc1["cast_em_anemo"] - 60.0) <= 1e-9,
         f"C1 unsealed Accolades is {acc1['cast_atk_cryo']} ATK (Cryo) / "
         f"{acc1['cast_em_anemo']} EM (non-Cryo), expected 0.15 / 60"),
        (abs(acc1["shared_cd_ally"] - 0.48) <= 1e-9
         and abs(acc1["shared_cd_self"] - 0.36) <= 1e-9,
         f"C1 shared crit is {acc1['shared_cd_ally']}/{acc1['shared_cd_self']}, "
         f"expected 0.48 / 0.36"),
        (abs(acc1["shared_atk_cryo"] - 0.60) <= 1e-9
         and abs(acc1["shared_em_anemo"] - 240.0) <= 1e-9,
         f"C1 shared ATK/EM is {acc1['shared_atk_cryo']}/{acc1['shared_em_anemo']}, "
         f"expected 0.60 / 240"),
        (abs(acc1["shared_atk_self"] - 0.45) <= 1e-9
         and abs(acc1["shared_em_self"]) <= 1e-12,
         f"C1 sealed own ATK is {acc1['shared_atk_self']} (EM {acc1['shared_em_self']}), "
         f"expected 0.45 / 0 (she is Cryo, so she gets the ATK branch)"),
        (abs(acc4["shared_cd_ally"] - 0.688) <= 1e-9
         and abs(acc4["shared_cd_self"] - 0.516) <= 1e-9,
         f"C4 shared crit is {acc4['shared_cd_ally']}/{acc4['shared_cd_self']}, "
         f"expected 0.688 / 0.516"),
        (abs(acc4["shared_atk_cryo"] - 0.86) <= 1e-9
         and abs(acc4["shared_em_anemo"] - 344.0) <= 1e-9,
         f"C4 shared ATK/EM is {acc4['shared_atk_cryo']}/{acc4['shared_em_anemo']}, "
         f"expected 0.86 / 344"),
        (abs(acc4["shared_atk_self"] - 0.645) <= 1e-9
         and abs(acc4["shared_em_self"]) <= 1e-12,
         f"C4 sealed own ATK is {acc4['shared_atk_self']} (EM {acc4['shared_em_self']}), "
         f"expected 0.645 / 0"),
        (not anc["love"][1]["flag"] and abs(anc["love"][1]["stellar_cd"] or 0.0) <= 1e-12,
         f"Love activated below C2 ({anc['love'][1]})"),
        (anc["love"][2]["flag"] and abs(anc["love"][2]["stellar_cd"] - 0.60) <= 1e-9,
         f"C2 Love stellar_crit_dmg is {anc['love'][2]['stellar_cd']}, expected 0.60"),
        (abs(anc["love"][1]["elevation"]) <= 1e-12
         and abs(anc["love"][2]["elevation"] - 0.05) <= 1e-9
         and abs(anc["love"][6]["elevation"] - 0.15) <= 1e-9,
         f"Love elevation is {anc['love'][1]['elevation']}/"
         f"{anc['love'][2]['elevation']}/{anc['love'][6]['elevation']} at C1/C2/C6, "
         f"expected 0 / 0.05 / 0.15"),
        (anc["c6"][5]["count"] == 0, f"C6 Triumph fired below C6 ({anc['c6'][5]['count']})"),
        (anc["c6"][6]["count"] > 6, f"only {anc['c6'][6]['count']} C6 Triumphs fired"),
        (anc["c6"][6]["delay_ok"],
         "a C6 Triumph did not land 0.010s after an ally swap-in"),
        (anc["c6"][6]["cd_ok"],
         f"C6 Triumphs are closer than the {ANASTASYA_C6_TRIUMPH_CD}s per-character CD"),
        (abs((anc["c6"][6]["mv"] or 0) - anc["c6"][6]["expected_mv"]) <= 1e-9,
         f"C6 Triumph MV is {anc['c6'][6]['mv']}, expected "
         f"{anc['c6'][6]['expected_mv']} (2.5x the talent-scaled Triumph)"),
        (anc["c6"][6]["owner"] == "Anastasya", "C6 Triumph is not credited to Anastasya"),
        (anc["linger"]["sealed_before_unseal"],
         "she was not sealed before the unseal"),
        (anc["linger"]["shared_during_linger"],
         "the shared state did not survive the 8s linger"),
        (anc["linger"]["unsealed_after_linger"],
         "the shared state outlived its 8s linger"),
        (anc["linger"]["no_reseal_without_burst"],
         "a visit without a burst cast sealed her again"),
    ]
    anc_failures = [msg for ok, msg in anc_checks if not ok]
    failures.extend(anc_failures)
    if not anc_failures and verbose:
        print(f"[OK] Anastasya constellations: C1 {acc1['shared_cd_ally']}/"
              f"{acc1['shared_cd_self']} crit +{acc1['shared_atk_cryo']} ATK / "
              f"{acc1['shared_em_anemo']} EM, C4 {acc4['shared_cd_ally']}/"
              f"{acc4['shared_cd_self']}, C2 Love {anc['love'][2]['stellar_cd']}, "
              f"C6 elev {anc['love'][6]['elevation']}, "
              f"{anc['c6'][6]['count']} C6 Triumphs")
        print("     preset totals by constellation: "
              + ", ".join(f"C{c}={v:,.1f}" for c, v in anc["totals"].items()))

    # 2o-bis. Diona: Choice Treasures state, Icy Paw volleys and the C6 burst buff.
    diona = _run_diona_check()
    diona_checks = [
        (abs(diona["window"] - 20.0) <= 1e-12,
         f"Diona Choice Treasures window is {diona['window']}, expected 20.0"),
        (abs(diona["cd"] - 3.5) <= 1e-12,
         f"Diona Choice Treasures CD is {diona['cd']}, expected 3.5"),
        (diona["ct_on_after_tap"], "her tap did not open the Choice Treasures state"),
        (diona["ct_on_after_hold"], "her hold did not open the Choice Treasures state"),
        (diona["ct_refresh_on"],
         f"a second skill cast did not refresh the state (hits {diona['ct_refresh_hits']} "
         f"after the first 20s are OFF)"),
        (diona["ct_expires"],
         f"the state outlived its 20s (hits {diona['ct_late_hits']} are still ON)"),
        (diona["paws_without_state"] == 0 and diona["swirls_without_state"] > 0,
         f"{diona['paws_without_state']} Icy Paw hits fired without the state "
         f"({diona['swirls_without_state']} swirls happened)"),
        (diona["paw_count"] > 0, "no Icy Paw volley fired in the Diona rotation"),
        (diona["paw_owner_ok"], "an Icy Paw hit is not owned by Diona"),
        (diona["paw_shape_ok"], "an Icy Paw hit is not STANDARD DMG / Elemental Skill"),
        (diona["paw_aura_ok"], "Icy Paws apply Cryo on the wrong tick (expected tick 1 only)"),
        (diona["volley_count"] >= 2,
         f"only {diona['volley_count']} Icy Paw volley(s) fired (need 2+ to test the CD)"),
        (not diona["volley_errors"],
         "Icy Paw timing errors: " + "; ".join(diona["volley_errors"])),
        (diona["volley_cd_ok"],
         f"two volleys were fired less than 3.5s apart "
         f"(trigger gaps {diona['volley_trigger_gaps']})"),
        (abs(diona["c6_window"] - 11.75) <= 1e-12,
         f"Diona C6 window is {diona['c6_window']}, expected 11.75 (the whole burst)"),
        (diona["c6_cast_hits"] > 0, "Diona never cast her burst in the probe rotation"),
        (diona["c6_includes_cast_hit"],
         "Diona C6 buff does not include her own burst cast hit"),
        (diona["c6_last_tick_on"] and diona["c6_last_tick_offset"] is not None
         and abs(diona["c6_last_tick_offset"] - 11.73) <= 1e-9,
         f"Diona C6 buff does not cover her last burst tick "
         f"(offset {diona['c6_last_tick_offset']}, expected 11.73)"),
        (diona["c6_on_past_window"] == 0,
         f"{diona['c6_on_past_window']} hits kept the C6 buff past its 11.75s window"),
        (abs(diona["c6_em_active"] - 200.0) <= 1e-9,
         f"Diona C6 EM on the ACTIVE character is {diona['c6_em_active']}, expected 200"),
        (abs(diona["c6_stellar_active"] - 0.40) <= 1e-12,
         f"Diona C6 stellar_bonus on the ACTIVE character is "
         f"{diona['c6_stellar_active']}, expected 0.40"),
        (abs(diona["c6_em_offfield_owner"]) <= 1e-12,
         f"Diona C6 leaked to Diona while she is OFF field "
         f"({diona['c6_em_offfield_owner']} EM)"),
        (diona["c5_never_on"], "Diona C6 buff activated below C6"),
    ]
    diona_failures = [msg for ok, msg in diona_checks if not ok]
    failures.extend(diona_failures)
    if not diona_failures and verbose:
        print(f"[OK] Diona: Choice Treasures 20s -> {diona['volley_count']} Icy Paw volleys "
              f"({diona['cd']}s CD, gaps {diona['volley_trigger_gaps']}), C6 +200 EM / "
              f"+0.40 stellar on the active char")

    # 2o-ter. Triggered-hit convention: the delay lives in abilities.py, never in the engine.
    trig = _run_triggered_ability_check(ana)
    trig_checks = [
        (not trig["delay_mismatch"],
         "triggered-hit delays drifted from the pinned values: "
         + ", ".join(f"{k} {trig['delays'][k]} != {trig['expected'][k]}"
                     for k in trig["delay_mismatch"])),
        (not trig["convention_errors"],
         "the triggered-hit helper does not schedule at trigger + relative_delay: "
         + "; ".join(trig["convention_errors"])),
        (trig["collapse_count"] > 0, "no Pressurized Collapse fired in the preset"),
        (trig["collapse_delay_ok"],
         "a Pressurized Collapse did not land 0.720s after its trigger hit"),
        (trig["collapse_cd_ok"],
         f"Pressurized Collapses are closer than the 3.0s trigger CD "
         f"({trig['collapse_gaps']})"),
        (trig["extra_count"] > 0, "no Anastasya extra stellar beat fired"),
        (trig["extra_delay_ok"],
         "the extra stellar beat did not land on its stellar beat (0.0 delay ignored)"),
        (abs(trig["engine_windows"]["Faruzan collapse CD"] - 3.0) <= 1e-12
         and abs(trig["engine_windows"]["Diona paw CD"] - 3.5) <= 1e-12
         and abs(trig["engine_windows"]["Diona state"] - 20.0) <= 1e-12
         and abs(trig["engine_windows"]["Diona C6"] - 11.75) <= 1e-12,
         f"engine windows changed: {trig['engine_windows']}"),
    ]
    trig_failures = [msg for ok, msg in trig_checks if not ok]
    failures.extend(trig_failures)
    if not trig_failures and verbose:
        print(f"[OK] triggered hits: delays are data ("
              f"{', '.join(f'{k}={v:g}' for k, v in trig['delays'].items())}), "
              f"{trig['collapse_count']} collapses at +0.720s, 3.0s trigger CD")

    # 2p. Editor catalogues + preset trial team gating.
    cat2 = _run_editor_catalogue_check()
    cat2_checks = [
        (cat2["faruzan_e_exists"], "faruzan_e field sequence missing from abilities.py"),
        (cat2["faruzan_e_same_swap"],
         "faruzan_e swap-out time differs from faruzan_q"),
        (cat2["faruzan_e_same_insert"],
         "faruzan_e insertion time differs from faruzan_q's burst cast"),
        (cat2["faruzan_e_is_skill_cast"],
         "faruzan_e does not call her Skill Cast only"),
        (cat2["faruzan_e_no_burst"], "faruzan_e contains a burst cast"),
        (cat2["filter_only_party"],
         "field_sequences_for() returned a sequence owned by a non-party character"),
        (cat2["filter_hides_outside"],
         "field_sequences_for() leaked a sequence of a character outside the party"),
        (cat2["abilities_for_anastasya"] == ["Skill Tap", "To the New World"],
         f"abilities_for('Anastasya') is {cat2['abilities_for_anastasya']}"),
        (cat2["abilities_for_absent"] == {},
         "abilities_for() returned abilities for a character that is not registered"),
        (all(cat2["triggered_registered"].values()),
         "a triggered ability is missing from ABILITY_REGISTRY: "
         + ", ".join(k for k, ok in cat2["triggered_registered"].items() if not ok)),
        (all(cat2["triggered_hidden"].values()),
         "a triggered ability is offered by the field-sequence editor (it can only be "
         "cast on its own conditions): "
         + ", ".join(k for k, ok in cat2["triggered_hidden"].items() if not ok)),
        (not cat2["triggered_in_sequences"],
         "triggered abilities must never be part of a FieldSequence: "
         + "; ".join(cat2["triggered_in_sequences"])),
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
        (cat2["sucrose_n1_registered"],
         "Sucrose's N1 is not a registered ability (sucrose_n1 must be an Ability, "
         "not a tuple)"),
        (cat2["sucrose_aether_trial"]["error"] is None,
         f"the Sucrose/Aether trial failed: {cat2['sucrose_aether_trial']['error']}"),
        (cat2["sucrose_aether_trial"]["rotations"] == 4
         and abs((cat2["sucrose_aether_trial"].get("duration") or 0.0) - 114.994) <= 1e-3,
         f"the Sucrose/Aether trial is {cat2['sucrose_aether_trial']}"),
        (cat2["sucrose_anastasya_trial"]["error"] is None,
         f"the Sucrose/Anastasya trial failed: {cat2['sucrose_anastasya_trial']['error']}"),
        (cat2["sucrose_anastasya_trial"]["rotations"] == 6
         and abs((cat2["sucrose_anastasya_trial"].get("duration") or 0.0) - 187.697) <= 1e-3,
         f"the Sucrose/Anastasya trial is {cat2['sucrose_anastasya_trial']}"),
        (cat2["sucrose_standard_steps"] == [
            "Sucrose E", "AetherECQ", "OdetteEE", "Sucrose E",
            "Skill Pullout 3 Nukes", "Sucrose E", "AetherECQ", "OdetteEE",
            "Sucrose QN1", "Burst Pullout 4 Nukes"],
         f"the Sucrose Standard rotation is {cat2['sucrose_standard_steps']}"),
        (cat2["sucrose_trials_gated"],
         "a Sucrose trial is offered for the other team"),
        (cat2["missing_combination_trials"] == [],
         f"no preset trial covers these teams: {cat2['missing_combination_trials']}"),
        (cat2["triple_cryo_trial"]["error"] is None,
         f"the Triple Cryo trial failed: {cat2['triple_cryo_trial']['error']}"),
        (cat2["triple_cryo_trial"]["rotations"] == 4
         and abs((cat2["triple_cryo_trial"].get("duration") or 0.0) - 135.740) <= 1e-3,
         f"the Triple Cryo trial is {cat2['triple_cryo_trial']}"),
        (cat2["triple_cryo_steps"] == [
            "AetherECQ", "AnastasyaEQ", "OdetteQE", "Skill Pullout 4 Nukes",
            "AetherECQ", "AnastasyaEQ", "OdetteQE", "Burst Pullout 4 Nukes"],
         f"the Triple Cryo Standard rotation is {cat2['triple_cryo_steps']}"),
        (cat2["sucrose_aether_anastasya_trial"]["error"] is None,
         f"the Aether+Anastasya Sucrose trial failed: "
         f"{cat2['sucrose_aether_anastasya_trial']['error']}"),
        (cat2["sucrose_aether_anastasya_trial"]["rotations"] == 4
         and abs((cat2["sucrose_aether_anastasya_trial"].get("duration") or 0.0)
                 - 118.354) <= 1e-3,
         f"the Aether+Anastasya Sucrose trial is {cat2['sucrose_aether_anastasya_trial']}"),
        (cat2["sacfrag_aether_anastasya_trial"]["error"] is None,
         f"the Aether+Anastasya Sac Frag trial failed: "
         f"{cat2['sacfrag_aether_anastasya_trial']['error']}"),
        (cat2["sacfrag_aether_anastasya_trial"]["rotations"] == 1
         and abs((cat2["sacfrag_aether_anastasya_trial"].get("duration") or 0.0)
                 - 121.092) <= 1e-3,
         f"the Aether+Anastasya Sac Frag trial is {cat2['sacfrag_aether_anastasya_trial']}"),
        (cat2["combo_trials_gated"],
         "a combination trial is offered for the wrong team"),
    ]
    cat2_failures = [msg for ok, msg in cat2_checks if not ok]
    failures.extend(cat2_failures)
    if not cat2_failures and verbose:
        print(f"[OK] editor catalogues: {cat2['sequence_count']} field sequences / "
              f"{cat2['ability_count']} abilities, party-gated; preset trials team-gated")

    # 2p. Trial duration accounting.
    dur = _run_trial_duration_check()
    duration_checks = [
        (dur["mode"] == "last_swap", f"duration probe preset ends by {dur['mode']}"),
        (abs(dur["time"] - 30.0) < 1e-9, f"a 30s time trial reports {dur['time']}s"),
        (dur["end_untouched"], "add_trial() mutates the trial's own end_time"),
        (abs(dur["last_swap"] - dur["field_sum"]) < 1e-6,
         f"last-swap duration {dur['last_swap']}s != field time {dur['field_sum']}s"),
    ]
    duration_failures = [msg for ok, msg in duration_checks if not ok]
    failures.extend(duration_failures)
    if not duration_failures and verbose:
        print(f"[OK] trial duration: time window kept, last swap = field time "
              f"({dur['last_swap']:.3f}s), the trial object stays untouched")

    # 2q. Save / Load build documents (export + import).
    save = _run_save_load_check()
    save_checks = [
        (save["schema"] == build_io.SCHEMA_VERSION,
         f"build document schema is {save['schema']}"),
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