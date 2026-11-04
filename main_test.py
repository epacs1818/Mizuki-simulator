import json
import io
import contextlib
import copy
from pathlib import Path

from timeline import RotationTimeline
from models import Rotation, Trial
from stats_calc import apply_permanent_buffs, compute_final_stats
import presets


def main():
    base_dir = Path(__file__).resolve().parent
    # In-game test config (character cards / enemy / rotation) saved by the user.
    json_path = base_dir / "New test" / "Mizuki_Faruzan_Sac_Frag_120s.json"
    output_path = base_dir / "output.txt"

    # 1. Load party and enemy setup from the saved in-game test configuration.
    #    Falls back to the default party if the file is missing.
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        party = copy.deepcopy(data.get("party", {}))
        enemy_stats = data.get("enemy_stats", {"enemy_lv": 100, "cryo_res": 0.1, "anemo_res": 0.1})
        sim_name = data.get("simulation_name", "Mizuki Faruzan Sac Frag")
    except FileNotFoundError:
        party = copy.deepcopy(presets.DEFAULT_PARTY)
        enemy_stats = {"enemy_lv": 100, "cryo_res": 0.1, "anemo_res": 0.1}
        sim_name = "DEFAULT_PARTY fallback"

    # Build the card vs on-field (post-permanent) stat block BEFORE the crit
    # override, so it reflects the characters' real (gear) stats like the card.
    stat_lines = []
    for char_name, char_data in party.items():
        raw = char_data.get("initial_stats")
        if not raw:
            continue
        card = compute_final_stats(dict(raw))
        onf = compute_final_stats(apply_permanent_buffs(copy.deepcopy(raw), char_name))

        def _fmt(c, f, key, is_pct=False):
            a = ("%.1f%%" % (c[key] * 100)) if is_pct else (("%.1f" % c[key]) if key == "EM" else "%.0f" % c[key])
            b = ("%.1f%%" % (f[key] * 100)) if is_pct else (("%.1f" % f[key]) if key == "EM" else "%.0f" % f[key])
            return a if a == b else (a + "->" + b)

        stat_lines.append(
            "  %-7s ATK %-8s HP %-8s DEF %-8s EM %-7s CR %-8s CD %-8s ER %-8s" % (
                char_name,
                _fmt(card, onf, "ATK"), _fmt(card, onf, "HP"), _fmt(card, onf, "DEF"),
                _fmt(card, onf, "EM"), _fmt(card, onf, "CR", is_pct=True),
                _fmt(card, onf, "CD", is_pct=True), _fmt(card, onf, "ER", is_pct=True),
            )
        )
    stat_header = "=== Character Stats (card -> on-field/permanent) ===\n" + "\n".join(stat_lines) + "\n\n"

    # The in-game test used ~100% crit rate on every character (a +102.61% C.Rate
    # test modifier) to avoid variance. Repro that by forcing crit_rate = 1.0.
    # Set FORCE_100_CRIT = False to use the characters' real (gear) crit rates.
    FORCE_100_CRIT = True
    if FORCE_100_CRIT:
        for char_data in party.values():
            if "initial_stats" in char_data and char_data["initial_stats"]:
                char_data["initial_stats"]["crit_rate"] = 1.0

    # Normalize artifact naming to match timeline checks
    for char_name, char_data in party.items():
        art = char_data.get("artifact") or char_data.get("artifact_set")
        if art:
            if art.lower() == "heart of the furnace":
                art = "Heart of the Furnace"
            char_data["artifact"] = art
            char_data["artifact_set"] = art

    # 2. Build the trial: the standard in-game rotation, repeated to reach the
    #    ~40.71 s window (Abyss 12) recorded in the in-game test.
    rotation = copy.deepcopy(presets.STANDARD_ROTATIONS["standard_mizuki_loop"])
    rotation.repetitions = 3
    trial_obj = Trial(
        name="Mizuki Faruzan Sac Frag (in-game 40.71s)",
        rotations=[rotation],
        end_mode="time",
        end_time=40.71,
        description="In-game test reproduction — 40.71s, 100% crit.",
    )

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
        f.write(stat_header + table_content)

    print(f"Simulation completed for trial: '{sim_name}'.")
    print(f"Results successfully written to '{output_path.name}'.")


if __name__ == "__main__":
    main()

