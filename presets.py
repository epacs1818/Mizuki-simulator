from models import FieldSequence, Rotation, Trial
from abilities import (
    aether_skill, aether_n1, aether_n1ca, aether_burst_enhanced,
    aether_ecq as aether_ecq_ability_seq, # imported or built natively
    odette_cast, odette_recast,
    odette_qe,
    faruzan_burst, faruzan_collapse_ability,
    # Mizuki's skill variants + burst field already hold their own hits/abilities.
    mizuki_pullout_1_nuke, mizuki_pullout_2_nukes, mizuki_pullout_3_nukes,
    mizuki_pullout_4_nukes, mizuki_burst_field,
    sucrose_skill, sucrose_burst,
    anastasya_e, anastasya_q, anastasya_eq, faruzan_e,
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

# 1. STANDARD FIELD SEQUENCES (Building Blocks)
STANDARD_FIELD_SEQUENCES = {
    "Aether EN1": FieldSequence("AetherEN1", "Aether", swap_out_time=1.23),
    "Aether CQ": FieldSequence("AetherCQ", "Aether", swap_out_time=2.941),
    "Aether ECQ": FieldSequence("AetherECQ", "Aether", swap_out_time=3.631),
    "Faruzan Q": FieldSequence("FaruzanQSwap", "Faruzan", swap_out_time=1.410),
    "Odette EE": FieldSequence("OdetteEE", "Odette", swap_out_time=2.371),
    # Mizuki's pull-out lengths live in abilities.py: one sequence per number of
    # stellar nukes (1/2/3/4 = 2/5/9/13 skill ticks), plus her burst field.
    "Mizuki E (Sac Frag Proc)": mizuki_pullout_1_nuke,
    "Mizuki E (Pullout)": mizuki_pullout_4_nukes,
    "Mizuki E (2 nukes)": mizuki_pullout_2_nukes,
    "Mizuki E (3 nukes)": mizuki_pullout_3_nukes,
    "Mizuki Q": mizuki_burst_field,
    # Anastasya's sequences live in abilities.py (anastasya_e / anastasya_q /
    # anastasya_eq), built on Aether's EN1 / CQ timings.
    "Anastasya E": anastasya_e,
    "Anastasya Q": anastasya_q,
    "Anastasya EQ": anastasya_eq,
    "Faruzan E": faruzan_e,
    # Odette's QE lives in abilities.py (burst + recast, 3.071s field).
    "Odette QE": odette_qe,
}

# Populate calls for sequences (covering all abilities)
STANDARD_FIELD_SEQUENCES["Aether EN1"].add_ability(0.601, aether_skill)
STANDARD_FIELD_SEQUENCES["Aether EN1"].add_ability(1.2, aether_n1)

# Aether CQ sequence population
STANDARD_FIELD_SEQUENCES["Aether CQ"].add_ability(0.51, aether_n1ca)
STANDARD_FIELD_SEQUENCES["Aether CQ"].add_ability(2.371, aether_burst_enhanced)

# Aether ECQ sequence population (Completing the 12 abilities transition)
STANDARD_FIELD_SEQUENCES["Aether ECQ"].add_ability(0.601, aether_skill)
STANDARD_FIELD_SEQUENCES["Aether ECQ"].add_ability(1.2, aether_n1ca)
STANDARD_FIELD_SEQUENCES["Aether ECQ"].add_ability(3.061, aether_burst_enhanced)

STANDARD_FIELD_SEQUENCES["Odette EE"].add_ability(0.660, odette_cast)
STANDARD_FIELD_SEQUENCES["Odette EE"].add_ability(1.170, odette_recast)

STANDARD_FIELD_SEQUENCES["Faruzan Q"].add_ability(1.200, faruzan_burst)

# Mizuki's sequences are complete objects in abilities.py, so nothing to populate here.


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
    )
}


# 3. STANDARD TRIALS (Execution Windows)
# Both preset trials are the same 6x "Sac Frag pull out" loop; they differ only in
# who takes Aether's slots, so the UI gates them on the exact team.
MIZUKI_SACFRAG_TEAM = ["Mizuki", "Aether", "Odette", "Faruzan"]
ANASTASYA_SACFRAG_TEAM = ["Mizuki", "Anastasya", "Odette", "Faruzan"]

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