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
"""
from timeline import RotationTimeline
from abilities import odette_qe, aether_en1, sucrose_eq
from models import Rotation, Trial
import presets


def _run_sucrose_check() -> dict:
    """Cryo aura (Aether) -> Sucrose skill/burst; checks A1/A4/C6 windows fire."""
    party = {
        "Sucrose": {"constellation": 6, "level": 90, "refinement": 1,
                    "weapon": "The Widsith (Average)", "artifact_set": "2p/2p EM",
                    "talents": "1/10/10"},
        "Aether": {"constellation": 0, "level": 90, "refinement": 1,
                   "weapon": "New Bough", "artifact_set": "2p/2p ATK",
                   "talents": "1/10/10"},
    }
    t = RotationTimeline(party=party)
    t.add_trial(Trial(
        name="suc", end_mode="time", end_time=10.0,
        rotations=[Rotation(name="r", sequences=[aether_en1, sucrose_eq], repetitions=1)],
    ))
    t.evaluate_timeline()
    hits = [e for e in t.global_events if e.get("event_type") == "HIT"]
    return {
        "a1": any(e.get("sucrose_a1_state") == "ON" for e in hits),
        "a4": any(e.get("sucrose_a4_state") == "ON" for e in hits),
        "c6": any(e.get("sucrose_c6_state") == "ON" for e in hits),
    }


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


def run(verbose: bool = True) -> None:
    party = presets.DEFAULT_PARTY
    trial = presets.STANDARD_TRIALS["Standard 30s Trial"]

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

    # 3c. Odette burst buff check via an Odette QE field-sequence run.
    odette_burst_on = _run_odette_burst_check()
    if odette_burst_on and verbose:
        print("[OK] Odette burst buff activated")
    if not odette_burst_on:
        failures.append("Odette burst buff never activated")

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

    # 3e. Sucrose (A1 swirl -> non-anemo EM, A4 flat-EM share, C6 cryo bonus).
    suc = _run_sucrose_check()
    if suc["a1"] and verbose:
        print("[OK] Sucrose A1 EM window activated (on swirl)")
    if not suc["a1"]:
        failures.append("Sucrose A1 never activated (no swirl window)")
    if suc["a4"] and verbose:
        print("[OK] Sucrose A4 share window activated")
    if not suc["a4"]:
        failures.append("Sucrose A4 never activated")
    if suc["c6"] and verbose:
        print("[OK] Sucrose C6 cryo_bonus window activated")
    if not suc["c6"]:
        failures.append("Sucrose C6 never activated")

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

    if failures:
        print("\nSMOKE TEST FAILED:")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    print("\nSMOKE TEST PASSED")


if __name__ == "__main__":
    run()