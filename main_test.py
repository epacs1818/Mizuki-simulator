import json
import io
import contextlib
import copy
from pathlib import Path

from timeline import RotationTimeline
import presets


def main():
    base_dir = Path(__file__).resolve().parent
    json_path = base_dir / "Exact_Rotation_Trial.json"
    output_path = base_dir / "output.txt"

    # 1. Load party and enemy setup from Exact_Rotation_Trial.json
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    party = copy.deepcopy(data.get("party", {}))
    enemy_stats = data.get("enemy_stats", {"enemy_lv": 100, "cryo_res": 0.1, "anemo_res": 0.1})
    sim_name = data.get("simulation_name", "Exact Rotation Trial")

    # Normalize artifact naming to match timeline checks
    for char_name, char_data in party.items():
        art = char_data.get("artifact") or char_data.get("artifact_set")
        if art:
            if art.lower() == "heart of the furnace":
                art = "Heart of the Furnace"
            char_data["artifact"] = art
            char_data["artifact_set"] = art

    # 2. Select trial preset from presets.py
    if sim_name in presets.STANDARD_TRIALS:
        trial_obj = copy.deepcopy(presets.STANDARD_TRIALS[sim_name])
    else:
        trial_obj = copy.deepcopy(presets.STANDARD_TRIALS["Exact Rotation Trial"])

    # 3. Initialize and populate the timeline
    timeline = RotationTimeline(party=party, enemy_stats=enemy_stats)

    # Preserve any precomputed initial_stats from party data
    for char_name, char_data in party.items():
        if "initial_stats" in char_data and char_data["initial_stats"]:
            timeline.char_initial_stats_map[char_name] = char_data["initial_stats"].copy()

    timeline.add_trial(trial_obj)

    # 4. Generate formatted table and write to output.txt (replacing every time)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        timeline.display()

    table_content = buf.getvalue()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(table_content)

    print(f"Simulation completed for trial: '{sim_name}'.")
    print(f"Results successfully written to '{output_path.name}'.")


if __name__ == "__main__":
    main()

