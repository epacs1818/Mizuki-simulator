from timeline import RotationTimeline
from combos import (
    aether_en1,
    aether_cq,
    faruzan_q,
    odette_ee,
    mizuki_sacfrag_fill,
    mizuki_burstless_pull_out,
)

# ==========================================
# 6. TESTING EXECUTION
# ==========================================

if __name__ == "__main__":
    my_party = {
        "Aether":  {"constellation": 4, "weapon": "Favonius Sword",        "artifact": "Noblesse"},
        "Odette":  {"constellation": 0, "weapon": "Heart of the Furnace",   "artifact": "Blizzard Strayer"},
        "Faruzan": {"constellation": 6, "weapon": "Elegy",                  "artifact": "Tenacity"},
        "Mizuki":  {"constellation": 2, "weapon": "Sacrificial Fragments",  "artifact": "Viridescent"},
    }

    timeline = RotationTimeline(party=my_party)
    current_time = 0.0

    current_time = timeline.add_combo(aether_en1,               swap_in_time=current_time)
    current_time = timeline.add_combo(faruzan_q,                swap_in_time=current_time)
    current_time = timeline.add_combo(odette_ee,                swap_in_time=current_time)
    current_time = timeline.add_combo(mizuki_sacfrag_fill,      swap_in_time=current_time)
    current_time = timeline.add_combo(aether_cq,                swap_in_time=current_time)
    current_time = timeline.add_combo(mizuki_burstless_pull_out, swap_in_time=current_time)

    timeline.display()
