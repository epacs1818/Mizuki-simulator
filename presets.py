"""Presets: the field-sequence library, the rotation macros and the preset trials.

Division of labour with abilities.py:

  * `Ability` (hits, motion values, cooldowns) is immutable DATA -> abilities.py.
  * `FieldSequence` (which ability is cast when, how long you stay on field) is a saved
    COMPOSITION: the ones below are mine (presets); the user's are created in the editor
    and stored inside the build JSON.
  * This module therefore owns the sequence catalogue the editors read
    (FIELD_SEQUENCE_REGISTRY / field_sequences_for); abilities.py owns ABILITY_REGISTRY.

Ordering matters: sequences are defined first, the catalogue is collected right after
them, then the rotations/trials reference the objects directly.
"""
from models import FieldSequence, Rotation, Trial
from abilities import (
    aether_skill, aether_n1, aether_n1ca, aether_burst_enhanced,
    odette_cast, odette_recast, odette_burst,
    faruzan_skill_cast, faruzan_burst,
    mizuki_n1, mizuki_charged, mizuki_pullout_2,
    mizuki_pullout_5, mizuki_pullout_9, mizuki_pullout_13, mizuki_burst,
    sucrose_skill, sucrose_burst, sucrose_n1, sucrose_n2,
    diona_skill_tap, diona_skill_hold, diona_burst,
    anastasya_tap, anastasya_burst,
)


# Default party used when no saved JSON configuration is available
# (main_test.py fallback, smoke_test.py).
DEFAULT_PARTY = {
    "Mizuki": {"constellation": 2, "level": 90, "refinement": 5,
               "weapon": "Sacrificial Fragments", "artifact_set": "2p/2p EM",
               "talents": "10/13/13"},
    "Aether": {"constellation": 6, "level": 90, "refinement": 1,
               "weapon": "New Bough", "artifact_set": "2p/2p ATK",
               "talents": "1/13/13"},
    "Faruzan": {"constellation": 6, "level": 90, "refinement": 1,
                "weapon": "Favonius Warbow", "artifact_set": "Instructor",
                "talents": "1/13/13"},
    "Odette": {"constellation": 2, "level": 90, "refinement": 1,
               "weapon": "New Bough", "artifact_set": "2p/2p ATK",
               "talents": "1/13/13"},
}

# 1. SEQUENCE LIBRARY - one definition per sequence, no duplicates anywhere else.
# Every module-level FieldSequence here is collected into FIELD_SEQUENCE_REGISTRY.
# --- Aether ---
aether_ecq = FieldSequence("AetherECQ", "Aether", swap_out_time=3.631)
aether_ecq.add_ability(0.601, aether_skill)
aether_ecq.add_ability(1.2, aether_n1ca)
aether_ecq.add_ability(3.061, aether_burst_enhanced)

aether_en1 = FieldSequence("AetherEN1", "Aether", swap_out_time=1.23)
aether_en1.add_ability(0.601, aether_skill)
aether_en1.add_ability(1.2, aether_n1)

aether_cq = FieldSequence("AetherCQ", "Aether", swap_out_time=2.941)
aether_cq.add_ability(0.51, aether_n1ca)
aether_cq.add_ability(2.371, aether_burst_enhanced)

# --- Odette ---
odette_ee = FieldSequence("OdetteEE", "Odette", swap_out_time=2.371)
odette_ee.add_ability(0.660, odette_cast)
odette_ee.add_ability(1.170, odette_recast)

odette_qe = FieldSequence("OdetteQE", "Odette", swap_out_time=3.451)
odette_qe.add_ability(2.160, odette_burst)
odette_qe.add_ability(2.250, odette_recast)

# --- Faruzan ---
faruzan_q = FieldSequence("FaruzanQSwap", "Faruzan", swap_out_time=1.410)
faruzan_q.add_ability(1.200, faruzan_burst)

# Faruzan E: her skill CAST only. The Pressurized Collapse is a TRIGGERED ability and
# is therefore not part of this (or any) field sequence: it only fires when its own
# trigger conditions are met (her burst cast, or any hit while her C6 window is up,
# 3.0s CD). Same insertion time and swap-out time as the burst cast of her Q swap, so
# both visits last exactly as long. Kept for rotations that cannot afford a burst
# every loop.
faruzan_e = FieldSequence("FaruzanESwap", "Faruzan", swap_out_time=1.410)
faruzan_e.add_ability(1.200, faruzan_skill_cast)

# --- Diona ---
# Tap / hold skill and the burst. Her "Choice Treasures" Icy Paws are triggered by a
# Stellar Swirl (20s state opened by either skill hit), so they live in abilities.py
# as an engine-internal ability and never appear in a sequence.
diona_e = FieldSequence("DionaE", "Diona", swap_out_time=1.410)
diona_e.add_ability(0.660, diona_skill_tap)

diona_hE = FieldSequence("DionaHE", "Diona", swap_out_time=1.410)
diona_hE.add_ability(0.660, diona_skill_hold)

# The burst is cast 0.029s before she leaves the field, so her own burst cast hit is
# still ON FIELD: her C6 buff ("the ACTIVE character") and every active-character-gated
# effect must reach that hit (swap_out_time was 3.071 = the cast time, which made the
# cast hit resolve with active_character = None).
diona_hEQ = FieldSequence("DionaHEQ", "Diona", swap_out_time=3.100)
diona_hEQ.add_ability(0.660, diona_skill_hold)
diona_hEQ.add_ability(3.071, diona_burst)

# --- Mizuki ---
# One sequence per pull-out length (the number of stellar nukes she banks), plus the
# skill+burst combo and a normal-attack filler.
mizuki_pullout_4_nukes = FieldSequence("Skill Pullout 4 Nukes", "Mizuki", swap_out_time=10.000)
mizuki_pullout_4_nukes.add_ability(0.301, mizuki_pullout_13)

mizuki_pullout_1_nuke = FieldSequence("Skill Pullout 1 Nuke", "Mizuki", swap_out_time=1.750)
mizuki_pullout_1_nuke.add_ability(0.301, mizuki_pullout_2)

mizuki_pullout_3_nukes = FieldSequence("Skill Pullout 3 Nukes", "Mizuki", swap_out_time=7.100)
mizuki_pullout_3_nukes.add_ability(0.301, mizuki_pullout_9)

mizuki_pullout_2_nukes = FieldSequence("Skill Pullout 2 Nukes", "Mizuki", swap_out_time=4.101)
mizuki_pullout_2_nukes.add_ability(0.301, mizuki_pullout_5)

mizuki_n1c = FieldSequence("N1C", "Mizuki", swap_out_time=1.410)
mizuki_n1c.add_ability(0.660, mizuki_n1)
mizuki_n1c.add_ability(1.080, mizuki_charged)

mizuki_pullout_burst_4_nukes = FieldSequence("Burst Pullout 4 Nukes", "Mizuki", swap_out_time=9.3)
mizuki_pullout_burst_4_nukes.add_ability(0.301, mizuki_pullout_13)
mizuki_pullout_burst_4_nukes.add_ability(8.100, mizuki_burst)

# --- Sucrose ---
sucrose_e = FieldSequence("Sucrose E", "Sucrose", swap_out_time=1.259)
sucrose_e.add_ability(1.02, sucrose_skill)

sucrose_eq = FieldSequence("Sucrose EQ", "Sucrose", swap_out_time=1.59)
sucrose_eq.add_ability(1.02, sucrose_skill)
sucrose_eq.add_ability(3.119, sucrose_burst)

# Button order is Q then N1, but the burst's first hit resolves AFTER the N1: the
# numbers below are HIT times, so the N1 (1.319) still lands while she is on field
# and takes the swirl credit, and the burst resolves at 2.460.
sucrose_qn1 = FieldSequence("Sucrose QN1", "Sucrose", swap_out_time=1.320)
sucrose_qn1.add_ability(1.319, sucrose_n1)
sucrose_qn1.add_ability(2.460, sucrose_burst)

# --- Anastasya ---
# E / Q mirror Aether's EN1 / CQ timings (the rotation swaps Aether out for Anastasya in
# both slots); EQ is the combined variant.
anastasya_e = FieldSequence("AnastasyaE", "Anastasya", swap_out_time=1.23)
anastasya_e.add_ability(0.601, anastasya_tap)

anastasya_q = FieldSequence("AnastasyaQ", "Anastasya", swap_out_time=2.941)
anastasya_q.add_ability(2.371, anastasya_burst)

anastasya_eq = FieldSequence("AnastasyaEQ", "Anastasya", swap_out_time=2.851)
anastasya_eq.add_ability(0.601, anastasya_tap)
anastasya_eq.add_ability(2.371, anastasya_burst)

# Preset keys: readable handles for the rotations below (they are NOT the UI labels,
# which come from FieldSequence.name through FIELD_SEQUENCE_REGISTRY).
STANDARD_FIELD_SEQUENCES = {
    "Aether EN1": aether_en1,
    "Aether CQ": aether_cq,
    "Aether ECQ": aether_ecq,
    "Faruzan Q": faruzan_q,
    "Odette EE": odette_ee,
    "Mizuki E (Sac Frag Proc)": mizuki_pullout_1_nuke,
    "Mizuki E (Pullout)": mizuki_pullout_4_nukes,
    "Mizuki E (2 nukes)": mizuki_pullout_2_nukes,
    "Mizuki E (3 nukes)": mizuki_pullout_3_nukes,
    "Mizuki EQ (4 nukes)": mizuki_pullout_burst_4_nukes,
    "Mizuki N1C": mizuki_n1c,
    "Anastasya E": anastasya_e,
    "Anastasya Q": anastasya_q,
    "Anastasya EQ": anastasya_eq,
    "Faruzan E": faruzan_e,
    "Odette QE": odette_qe,
    "Diona E": diona_e,
    "Diona HE": diona_hE,
    "Diona HEQ": diona_hEQ,
    "Sucrose E": sucrose_e,
    "Sucrose EQ": sucrose_eq,
    "Sucrose QN1": sucrose_qn1,
}

# ---------------------------------------------------------------------------
# Sequence catalogue (read by the editors and by build_io)
# ---------------------------------------------------------------------------


def _collect_field_sequences():
    """{name: FieldSequence} from every sequence bound to a module global.

    Module-level definition is the whole registration step: a new sequence needs no
    second entry anywhere else, it shows up in the editors for its character.
    """
    sequences = {}
    for value in list(globals().values()):
        if isinstance(value, FieldSequence):
            sequences.setdefault(value.name, value)
    return sequences


FIELD_SEQUENCE_REGISTRY = _collect_field_sequences()


def field_sequences_for(characters) -> dict:
    """{sequence name: FieldSequence} for the characters that are actually in play."""
    party = {c for c in (characters or []) if c}
    return {name: seq for name, seq in FIELD_SEQUENCE_REGISTRY.items()
            if seq.character in party}


# 2. STANDARD ROTATIONS (Macro Loops)
STANDARD_ROTATIONS = {
    "standard_mizuki_loop": Rotation(
        name="Standard Mizuki-Faruzan Loop",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Aether EN1"],
            STANDARD_FIELD_SEQUENCES["Faruzan Q"],
            STANDARD_FIELD_SEQUENCES["Odette EE"],
            STANDARD_FIELD_SEQUENCES["Mizuki E (Sac Frag Proc)"],
            STANDARD_FIELD_SEQUENCES["Aether CQ"],            
            STANDARD_FIELD_SEQUENCES["Mizuki E (Pullout)"]
        ],
        repetitions=6,
        description="Core double-swirl team rotation looped twice."
    ),
    # Anastasya variant: she replaces Aether in both slots and does her skill and
    # burst in ONE visit (EQ) — she cannot split them across the loop. Odette uses
    # her QE (burst + recast, 3.071s field) so the loop is 19.082s: just enough for
    # Faruzan's 19s burst cooldown, and it keeps Odette's own burst buff up.
    "anastasya_mizuki_loop": Rotation(
        name="Anastasya Mizuki-Faruzan Loop",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Anastasya EQ"],
            STANDARD_FIELD_SEQUENCES["Faruzan Q"],
            STANDARD_FIELD_SEQUENCES["Mizuki E (Sac Frag Proc)"],
            STANDARD_FIELD_SEQUENCES["Odette QE"],
            STANDARD_FIELD_SEQUENCES["Mizuki E (Pullout)"]
        ],
        repetitions=6,
        description="Anastasya EQ -> Faruzan Q -> Mizuki (Sac Frag) -> Odette QE -> Mizuki (pull out)."
    ),

    #Aether test rotation: just a simple skill press to test Aether's crit multiplier
    "test_aether_loop": Rotation(
        name="Test Aether Loop",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Aether EN1"],
        ],
        repetitions=1,
        description="A simple skill press to test Aether's crit multiplier."
    ),

    # --- Sucrose rounds -----------------------------------------------------
    # Sucrose takes her own swirl credit with a QN1 (see the sequence comment) and
    # hands the field over for Mizuki's pull-out. The starter uses Mizuki's 4-nuke
    # burst pull-out once, every standard alternates a 3-nuke skill pull-out with
    # the 4-nuke burst pull-out.
    "sucrose_starter": Rotation(
        name="Sucrose Starter",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Aether EN1"],
            STANDARD_FIELD_SEQUENCES["Sucrose EQ"],
            STANDARD_FIELD_SEQUENCES["Odette EE"],
            STANDARD_FIELD_SEQUENCES["Mizuki EQ (4 nukes)"]
        ],
        repetitions=1,
        description="Aether EN1 -> Sucrose EQ -> Odette EE -> Mizuki burst pull-out (4 nukes)."
    ),
    "sucrose_standard": Rotation(
        name="Sucrose Standard",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Sucrose E"],
            STANDARD_FIELD_SEQUENCES["Aether ECQ"],
            STANDARD_FIELD_SEQUENCES["Odette EE"],
            STANDARD_FIELD_SEQUENCES["Sucrose E"],
            STANDARD_FIELD_SEQUENCES["Mizuki E (3 nukes)"],
            STANDARD_FIELD_SEQUENCES["Sucrose E"],
            STANDARD_FIELD_SEQUENCES["Aether ECQ"],
            STANDARD_FIELD_SEQUENCES["Odette EE"],
            STANDARD_FIELD_SEQUENCES["Sucrose QN1"],
            STANDARD_FIELD_SEQUENCES["Mizuki EQ (4 nukes)"]
        ],
        repetitions=1,
        description="Sucrose E -> Aether ECQ -> Odette EE -> Sucrose E -> Mizuki (3 nukes) "
                    "-> Sucrose E -> Aether ECQ -> Odette EE -> Sucrose QN1 -> Mizuki burst (4 nukes)."
    ),
    # Anastasya variant: her EQ replaces Aether's EN1/ECQ, but it is 0.78s SHORTER
    # (2.851s vs 3.631s), which would re-cast her 15s skill/burst at 14.84s. Odette's
    # QE (+1.08s per visit) buys the missing time and clears the cooldown.
    "sucrose_starter_anastasya": Rotation(
        name="Sucrose Starter",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Anastasya EQ"],
            STANDARD_FIELD_SEQUENCES["Sucrose EQ"],
            STANDARD_FIELD_SEQUENCES["Odette QE"],
            STANDARD_FIELD_SEQUENCES["Mizuki EQ (4 nukes)"]
        ],
        repetitions=1,
        description="Anastasya EQ -> Sucrose EQ -> Odette QE -> Mizuki burst pull-out (4 nukes)."
    ),
    "sucrose_standard_anastasya": Rotation(
        name="Sucrose Standard",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Sucrose E"],
            STANDARD_FIELD_SEQUENCES["Anastasya EQ"],
            STANDARD_FIELD_SEQUENCES["Odette QE"],
            STANDARD_FIELD_SEQUENCES["Sucrose E"],
            STANDARD_FIELD_SEQUENCES["Mizuki E (3 nukes)"],
            STANDARD_FIELD_SEQUENCES["Sucrose E"],
            STANDARD_FIELD_SEQUENCES["Anastasya EQ"],
            STANDARD_FIELD_SEQUENCES["Odette QE"],
            STANDARD_FIELD_SEQUENCES["Sucrose QN1"],
            STANDARD_FIELD_SEQUENCES["Mizuki EQ (4 nukes)"]
        ],
        repetitions=1,
        description="Sucrose E -> Anastasya EQ -> Odette QE -> Sucrose E -> Mizuki (3 nukes) "
                    "-> Sucrose E -> Anastasya EQ -> Odette QE -> Sucrose QN1 -> Mizuki burst (4 nukes)."
    ),

    # --- Triple Cryo --------------------------------------------------------
    # Aether / Anastasya / Odette are all Cryo, so their bursts share the resonance.
    # Mizuki opens with N1C and closes each round with a 4-nuke burst pull-out.
    "triple_cryo_starter": Rotation(
        name="Triple Cryo Starter",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Aether EN1"],
            STANDARD_FIELD_SEQUENCES["Mizuki N1C"],
            STANDARD_FIELD_SEQUENCES["Anastasya EQ"],
            STANDARD_FIELD_SEQUENCES["Odette QE"],
            STANDARD_FIELD_SEQUENCES["Mizuki EQ (4 nukes)"]
        ],
        repetitions=1,
        description="Aether EN1 -> Mizuki N1C -> Anastasya EQ -> Odette QE -> "
                    "Mizuki burst pull-out (4 nukes)."
    ),
    "triple_cryo_standard": Rotation(
        name="Triple Cryo Standard",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Aether ECQ"],
            STANDARD_FIELD_SEQUENCES["Anastasya EQ"],
            STANDARD_FIELD_SEQUENCES["Odette QE"],
            STANDARD_FIELD_SEQUENCES["Mizuki E (Pullout)"],
            STANDARD_FIELD_SEQUENCES["Aether ECQ"],
            STANDARD_FIELD_SEQUENCES["Anastasya EQ"],
            STANDARD_FIELD_SEQUENCES["Odette QE"],
            STANDARD_FIELD_SEQUENCES["Mizuki EQ (4 nukes)"]
        ],
        repetitions=1,
        description="Aether ECQ -> Anastasya EQ -> Odette QE -> Mizuki (4 nukes) -> "
                    "Aether ECQ -> Anastasya EQ -> Odette QE -> Mizuki burst (4 nukes)."
    ),

    # --- UNVERIFIED drafts --------------------------------------------------
    # The parties that field Aether AND Anastasya without Odette: her slots are
    # taken by Anastasya's EQ, everything else follows the existing Sucrose / Sac
    # Frag patterns. Nobody has checked these two in game yet - edit freely.
    "sucrose_starter_aether_anastasya": Rotation(
        name="Sucrose Starter",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Aether EN1"],
            STANDARD_FIELD_SEQUENCES["Sucrose EQ"],
            STANDARD_FIELD_SEQUENCES["Anastasya EQ"],
            STANDARD_FIELD_SEQUENCES["Mizuki EQ (4 nukes)"]
        ],
        repetitions=1,
        description="UNVERIFIED draft. Aether EN1 -> Sucrose EQ -> Anastasya EQ -> "
                    "Mizuki burst pull-out (4 nukes)."
    ),
    "sucrose_standard_aether_anastasya": Rotation(
        name="Sucrose Standard",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Sucrose E"],
            STANDARD_FIELD_SEQUENCES["Aether ECQ"],
            STANDARD_FIELD_SEQUENCES["Anastasya EQ"],
            STANDARD_FIELD_SEQUENCES["Sucrose E"],
            STANDARD_FIELD_SEQUENCES["Mizuki E (3 nukes)"],
            STANDARD_FIELD_SEQUENCES["Sucrose E"],
            STANDARD_FIELD_SEQUENCES["Aether ECQ"],
            STANDARD_FIELD_SEQUENCES["Anastasya EQ"],
            STANDARD_FIELD_SEQUENCES["Sucrose QN1"],
            STANDARD_FIELD_SEQUENCES["Mizuki EQ (4 nukes)"]
        ],
        repetitions=1,
        description="UNVERIFIED draft. Sucrose E -> Aether ECQ -> Anastasya EQ -> "
                    "Sucrose E -> Mizuki (3 nukes) -> Sucrose E -> Aether ECQ -> "
                    "Anastasya EQ -> Sucrose QN1 -> Mizuki burst (4 nukes)."
    ),
    "aether_anastasya_mizuki_loop": Rotation(
        name="Aether-Anastasya Mizuki Loop",
        sequences=[
            STANDARD_FIELD_SEQUENCES["Aether EN1"],
            STANDARD_FIELD_SEQUENCES["Faruzan Q"],
            STANDARD_FIELD_SEQUENCES["Anastasya EQ"],
            STANDARD_FIELD_SEQUENCES["Mizuki E (Sac Frag Proc)"],
            STANDARD_FIELD_SEQUENCES["Aether CQ"],
            STANDARD_FIELD_SEQUENCES["Mizuki E (Pullout)"]
        ],
        repetitions=6,
        description="UNVERIFIED draft. Aether EN1 -> Faruzan Q -> Anastasya EQ -> "
                    "Mizuki (Sac Frag) -> Aether CQ -> Mizuki (pull out), six times."
    )
}


# 3. STANDARD TRIALS (Execution Windows)
# Both preset trials are the same 6x "Sac Frag pull out" loop; they differ only in
# who takes Aether's slots, so the UI gates them on the exact team.
MIZUKI_SACFRAG_TEAM = ["Mizuki", "Aether", "Odette", "Faruzan"]
ANASTASYA_SACFRAG_TEAM = ["Mizuki", "Anastasya", "Odette", "Faruzan"]
MIZUKI_SUCROSE_TEAM = ["Mizuki", "Aether", "Odette", "Sucrose"]
MIZUKI_SUCROSE_ANASTASYA_TEAM = ["Mizuki", "Anastasya", "Odette", "Sucrose"]
MIZUKI_SUCROSE_AETHER_ANASTASYA_TEAM = ["Mizuki", "Aether", "Anastasya", "Sucrose"]
MIZUKI_SACFRAG_AETHER_ANASTASYA_TEAM = ["Mizuki", "Aether", "Anastasya", "Faruzan"]
MIZUKI_TRIPLE_CRYO_TEAM = ["Mizuki", "Aether", "Odette", "Anastasya"]

STANDARD_TRIALS = {
    "Mizuki Sac Frag Pull out 6x rotations": Trial(
        name="Mizuki Sac Frag Pull out 6x rotations",
        rotations=[STANDARD_ROTATIONS["standard_mizuki_loop"]],
        end_mode="last_swap",
        description="Mizuki / Aether / Odette / Faruzan: 6 loops, ends when the last character swaps out.",
        required_party=MIZUKI_SACFRAG_TEAM,
    ),
    "Mizuki Sac Frag Pull out 6x rotations (Anastasya)": Trial(
        name="Mizuki Sac Frag Pull out 6x rotations",
        rotations=[STANDARD_ROTATIONS["anastasya_mizuki_loop"]],
        end_mode="last_swap",
        description="Mizuki / Anastasya / Odette / Faruzan: the same 6 loops with Anastasya's EQ.",
        required_party=ANASTASYA_SACFRAG_TEAM,
    ),
    # Sucrose rounds: one starter plus three standards, so every standard pairs a
    # 3-nuke skill pull-out with the 4-nuke burst pull-out. The Anastasya variant
    # plays two extra standards (starter + 5) with her EQ and Odette's QE.
    "Sucrose Mizuki, Alternating 3 and 4 Nukes": Trial(
        name="Sucrose Mizuki, Alternating 3 and 4 Nukes",
        rotations=[STANDARD_ROTATIONS["sucrose_starter"],
                   STANDARD_ROTATIONS["sucrose_standard"],
                   STANDARD_ROTATIONS["sucrose_standard"],
                   STANDARD_ROTATIONS["sucrose_standard"]],
        end_mode="last_swap",
        description="Mizuki / Aether / Odette / Sucrose: starter + 3 standards "
                    "(3-nuke skill pull-out, then the 4-nuke burst pull-out).",
        required_party=MIZUKI_SUCROSE_TEAM,
    ),
    "Sucrose Mizuki, Alternating 3 and 4 Nukes (Anastasya)": Trial(
        name="Sucrose Mizuki, Alternating 3 and 4 Nukes",
        rotations=[STANDARD_ROTATIONS["sucrose_starter_anastasya"]]
                  + [STANDARD_ROTATIONS["sucrose_standard_anastasya"]] * 5,
        end_mode="last_swap",
        description="The same rounds with Anastasya's EQ in Aether's slots: "
                    "starter + 5 standards.",
        required_party=MIZUKI_SUCROSE_ANASTASYA_TEAM,
    ),
    # Triple Cryo: one starter plus three standards, ends at the last swap-out.
    "Triple Cryo Rotation": Trial(
        name="Triple Cryo Rotation",
        rotations=[STANDARD_ROTATIONS["triple_cryo_starter"]]
                  + [STANDARD_ROTATIONS["triple_cryo_standard"]] * 3,
        end_mode="last_swap",
        description="Mizuki / Aether / Odette / Anastasya: starter + 3 standards "
                    "(Mizuki 4-nuke pull-out, then the 4-nuke burst pull-out).",
        required_party=MIZUKI_TRIPLE_CRYO_TEAM,
    ),
    # UNVERIFIED drafts: the two teams that field Aether AND Anastasya without
    # Odette. Rotations are pattern-derived, not checked in game yet.
    "Sucrose Mizuki, Alternating 3 and 4 Nukes (Aether + Anastasya)": Trial(
        name="Sucrose Mizuki, Alternating 3 and 4 Nukes",
        rotations=[STANDARD_ROTATIONS["sucrose_starter_aether_anastasya"]]
                  + [STANDARD_ROTATIONS["sucrose_standard_aether_anastasya"]] * 3,
        end_mode="last_swap",
        description="UNVERIFIED draft. The Sucrose rounds with Anastasya's EQ in "
                    "Odette's slots: starter + 3 standards.",
        required_party=MIZUKI_SUCROSE_AETHER_ANASTASYA_TEAM,
    ),
    "Mizuki Sac Frag Pull out 6x rotations (Aether + Anastasya)": Trial(
        name="Mizuki Sac Frag Pull out 6x rotations",
        rotations=[STANDARD_ROTATIONS["aether_anastasya_mizuki_loop"]],
        end_mode="last_swap",
        description="UNVERIFIED draft. The Sac Frag loop with Anastasya's EQ in "
                    "Odette's slot: 6 loops.",
        required_party=MIZUKI_SACFRAG_AETHER_ANASTASYA_TEAM,
    ),
    "Test Aether": Trial(
        name="Test Aether",
        rotations=[STANDARD_ROTATIONS["test_aether_loop"]],
        end_mode="last_swap",
        description="A simple skill press to test Aether's crit multiplier",
        # Only Aether appears in the rotation, so the trial is gated on him alone
        # (any team that fields him can run it).
        required_party=["Aether"],
    )
}

# Calibration / test harness only: the fixed 30s window is NOT offered in the UI
# (a rotation mid-loop gets cut), but the automated checks rely on it.
TEST_TRIAL_30S = Trial(
    name="30s Fixed Trial",
    rotations=[STANDARD_ROTATIONS["standard_mizuki_loop"]],
    end_mode="time",
    end_time=30.0,
    description="Capped strictly at 30.0 seconds. Test/calibration harness only.",
)