from core import RotationTimeline

# Import the specific combos you need from your character modules
from characters.aether import aether_en1, aether_cq
from characters.faruzan import faruzan_q
from characters.odette import odette_ee
from characters.mizuki import mizuki_sacfrag_fill, mizuki_burstless_pull_out

if __name__ == "__main__":
    timeline = RotationTimeline()
    current_time = 0.0

    current_time = timeline.add_combo(aether_en1, swap_in_time=current_time)
    current_time = timeline.add_combo(faruzan_q, swap_in_time=current_time)    
    current_time = timeline.add_combo(odette_ee, swap_in_time=current_time)
    current_time = timeline.add_combo(mizuki_sacfrag_fill, swap_in_time=current_time)    
    current_time = timeline.add_combo(aether_cq, swap_in_time=current_time)
    current_time = timeline.add_combo(mizuki_burstless_pull_out, swap_in_time=current_time)

    timeline.display()
