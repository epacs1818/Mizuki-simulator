from models import FieldSequence, Rotation, Trial
from abilities import (
    aether_skill, aether_n1, aether_n1ca, aether_burst,
    odette_cast, odette_recast,
    faruzan_burst,
    mizuki_skill
)

# 1. STANDARD FIELD SEQUENCES (Building Blocks)
STANDARD_FIELD_SEQUENCES = {
    "aether_en1": FieldSequence("AetherEN1", "Aether", swap_out_time=1.23),
    "aether_cq": FieldSequence("AetherCQ", "Aether", swap_out_time=2.941),
    "faruzan_q": FieldSequence("FaruzanQSwap", "Faruzan", swap_out_time=1.410),
    "odette_ee": FieldSequence("OdetteEE", "Odette", swap_out_time=2.371),
    "mizuki_sacfrag_fill": FieldSequence("SacFragFill", "Mizuki", swap_out_time=1.75),
    "mizuki_burstless_pull_out": FieldSequence("BurstlessPullOut", "Mizuki", swap_out_time=10.0),
}
# Populate calls for sequences...
STANDARD_FIELD_SEQUENCES["aether_en1"].add_ability(0.601, aether_skill)
STANDARD_FIELD_SEQUENCES["aether_en1"].add_ability(1.2, aether_n1)

STANDARD_FIELD_SEQUENCES["aether_cq"].add_ability()

STANDARD_FIELD_SEQUENCES["odette_ee"].add_ability(0.660, odette_cast)
STANDARD_FIELD_SEQUENCES["odette_ee"].add_ability(1.170, odette_recast)

STANDARD_FIELD_SEQUENCES["faruzan_q"].add_ability(1.200, faruzan_burst)
STANDARD_FIELD_SEQUENCES["mizuki_burstless_pull_out"].add_ability(0.000, mizuki_skill)


# 2. STANDARD ROTATIONS (Macro Loops)
STANDARD_ROTATIONS = {
    "standard_mizuki_loop": Rotation(
        name="Standard Mizuki-Faruzan Loop",
        sequences=[
            STANDARD_FIELD_SEQUENCES["aether_en1"],
            STANDARD_FIELD_SEQUENCES["faruzan_q"],
            STANDARD_FIELD_SEQUENCES["odette_ee"],
            STANDARD_FIELD_SEQUENCES["mizuki_burstless_pull_out"]
        ],
        repetitions=2,
        description="Core double-swirl team rotation looped twice."
    )
}


# 3. STANDARD TRIALS (Execution Windows)
STANDARD_TRIALS = {
    "Standard 30s Team Trial": Trial(
        name="30s Standard Trial",
        rotations=[STANDARD_ROTATIONS["standard_mizuki_loop"]],
        end_time=30.0,
        description="Standard 30-second combat simulation window using the optimal Mizuki loop."
    )
}