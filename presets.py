from models import FieldSequence, Rotation, Trial
from abilities import (
    aether_skill, aether_n1, aether_n1ca, aether_burst,
    aether_ecq as aether_ecq_ability_seq, # imported or built natively
    odette_cast, odette_recast,
    faruzan_burst, faruzan_collapse_ability,
    mizuki_skill, mizuki_sacfrag_skill
)

# 1. STANDARD FIELD SEQUENCES (Building Blocks)
STANDARD_FIELD_SEQUENCES = {
    "aether_en1": FieldSequence("AetherEN1", "Aether", swap_out_time=1.23),
    "aether_cq": FieldSequence("AetherCQ", "Aether", swap_out_time=2.941),
    "aether_ecq": FieldSequence("AetherECQ", "Aether", swap_out_time=3.631),
    "faruzan_q": FieldSequence("FaruzanQSwap", "Faruzan", swap_out_time=1.410),
    "odette_ee": FieldSequence("OdetteEE", "Odette", swap_out_time=2.371),
    "mizuki_sacfrag_fill": FieldSequence("SacFragFill", "Mizuki", swap_out_time=1.75),
    "mizuki_burstless_pull_out": FieldSequence("BurstlessPullOut", "Mizuki", swap_out_time=10.0),
}

# Populate calls for sequences (covering all abilities)
STANDARD_FIELD_SEQUENCES["aether_en1"].add_ability(0.601, aether_skill)
STANDARD_FIELD_SEQUENCES["aether_en1"].add_ability(1.2, aether_n1)

# Aether CQ sequence population
STANDARD_FIELD_SEQUENCES["aether_cq"].add_ability(0.51, aether_n1ca)
STANDARD_FIELD_SEQUENCES["aether_cq"].add_ability(2.371, aether_burst)

# Aether ECQ sequence population (Completing the 12 abilities transition)
STANDARD_FIELD_SEQUENCES["aether_ecq"].add_ability(0.601, aether_skill)
STANDARD_FIELD_SEQUENCES["aether_ecq"].add_ability(1.2, aether_n1ca)
STANDARD_FIELD_SEQUENCES["aether_ecq"].add_ability(3.061, aether_burst)

STANDARD_FIELD_SEQUENCES["odette_ee"].add_ability(0.660, odette_cast)
STANDARD_FIELD_SEQUENCES["odette_ee"].add_ability(1.170, odette_recast)

STANDARD_FIELD_SEQUENCES["faruzan_q"].add_ability(1.200, faruzan_burst)

STANDARD_FIELD_SEQUENCES["mizuki_burstless_pull_out"].add_ability(0.300, mizuki_skill)

STANDARD_FIELD_SEQUENCES["mizuki_sacfrag_fill"].add_ability(0.300, mizuki_sacfrag_skill)


# 2. STANDARD ROTATIONS (Macro Loops)
STANDARD_ROTATIONS = {
    "standard_mizuki_loop": Rotation(
        name="Standard Mizuki-Faruzan Loop",
        sequences=[
            STANDARD_FIELD_SEQUENCES["aether_en1"],
            STANDARD_FIELD_SEQUENCES["faruzan_q"],
            STANDARD_FIELD_SEQUENCES["odette_ee"],
            STANDARD_FIELD_SEQUENCES["mizuki_sacfrag_fill"],
            STANDARD_FIELD_SEQUENCES["aether_cq"],            
            STANDARD_FIELD_SEQUENCES["mizuki_burstless_pull_out"]
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