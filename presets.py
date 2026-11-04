from models import FieldSequence, Rotation, Trial
from abilities import (
    aether_skill, aether_n1, aether_n1ca, aether_burst_enhanced,
    aether_ecq as aether_ecq_ability_seq, # imported or built natively
    odette_cast, odette_recast,
    faruzan_burst, faruzan_collapse_ability,
    mizuki_skill, mizuki_sacfrag_skill
)

# Default party used when no saved JSON configuration is available
# (main_test.py fallback, smoke_test.py).
DEFAULT_PARTY = {
    "Mizuki": {"constellation": 6, "level": 90, "refinement": 5,
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
    "Mizuki E (Sac Frag Proc)": FieldSequence("SacFragFill", "Mizuki", swap_out_time=1.75),
    "Mizuki E (Pullout)": FieldSequence("BurstlessPullOut", "Mizuki", swap_out_time=10.0),
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

STANDARD_FIELD_SEQUENCES["Mizuki E (Pullout)"].add_ability(0.300, mizuki_skill)

STANDARD_FIELD_SEQUENCES["Mizuki E (Sac Frag Proc)"].add_ability(0.300, mizuki_sacfrag_skill)


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
        repetitions=2,
        description="Core double-swirl team rotation looped twice."
    )
}


# 3. STANDARD TRIALS (Execution Windows)
STANDARD_TRIALS = {
    "Standard 30s Trial": Trial(
        name="30s Fixed Trial",
        rotations=[STANDARD_ROTATIONS["standard_mizuki_loop"]],
        end_mode="time",
        end_time=30.0,
        description="Capped strictly at 30.0 seconds."
    ),
    "Exact Rotation Trial": Trial(
        name="Auto-End Trial",
        rotations=[STANDARD_ROTATIONS["standard_mizuki_loop"]],
        end_mode="last_swap",
        description="Ends automatically when the final character swaps out."
    )
}