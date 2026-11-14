"""The event / audit table shown in the results tab."""

import pandas as pd

import buff_registry
from ui.editors import BUFF_GROUP_TAG, buff_is_active


def build_timeline_dataframe(timeline_events, party=None):
    """Flat audit table ordered by block:
        time -> description (active/owner/action) -> reaction (app/aura/reaction)
        -> stats (HP/ATK/DEF/EM/CR/CD) -> multipliers -> output damage -> buffs.

    Buff columns come from buff_registry: only effects whose owner character,
    weapon, artifact set or resonance is present, AND that actually trigger
    somewhere in this run, are ever built into the table.
    """
    if not timeline_events:
        return pd.DataFrame()

    buff_entries = [
        entry for entry in buff_registry.visible_buffs(party or {})
        if any(buff_is_active(ev.get(entry["key"])) for ev in timeline_events)
    ]

    rows = []
    for event in timeline_events:
        nc = event.get("non_crit")
        cd = event.get("crit_damage")
        avg = event.get("average_damage")
        eff = event.get("effective_average_damage")

        row = {}
        row["Time (s)"] = f"{event['global_time']:.3f}"
        row["Active"] = event.get("active_character", "None")
        row["Owner"] = event.get("character", "")
        row["Action"] = event.get("action", "")
        # Aura comes BEFORE the elemental application it reacts with: it is the state
        # the hit was resolved against, so it only changes on the following row.
        row["Aura"] = event.get("cryo_aura", "-")
        row["Elemental App"] = event.get("elem_app", "-")
        row["Reaction"] = event.get("reaction", "-")
        row["HP"] = f"{event['stat_hp']:.0f}" if event.get("stat_hp") is not None else "-"
        row["ATK"] = f"{event['stat_atk']:.0f}" if event.get("stat_atk") is not None else "-"
        row["DEF"] = f"{event['stat_def']:.0f}" if event.get("stat_def") is not None else "-"
        row["EM"] = f"{event['stat_em']:.0f}" if event.get("stat_em") is not None else "-"
        # Crit display depends on the build standard: a 100% RV / KQM build carries
        # crit as ONE Crit Value (CV = 2*CR + CD) and lets the engine re-split it, so
        # CR% / CD% are internal storage there. Those rows show the CV instead, which
        # is the number the damage formula actually uses.
        stat_cr = event.get("stat_cr")
        stat_cr_val = stat_cr if stat_cr is not None else 0.0
        stat_cd = event.get("stat_cd")
        stat_cd_val = stat_cd if stat_cd is not None else 0.0
        is_rv_hit = bool(event.get("rv_mode"))
        if stat_cr is None or stat_cd is None:
            row["CR%"] = "-"
            row["CD%"] = "-"
            row["CV"] = "-"
        else:
            row["CR%"] = "-" if is_rv_hit else f"{stat_cr_val * 100:.1f}"
            row["CD%"] = "-" if is_rv_hit else f"{stat_cd_val * 100:.1f}"
            row["CV"] = f"{(2.0 * stat_cr_val + stat_cd_val) * 100:.1f}"
        row["Base DMG"] = f"{event['base_damage']:.1f}" if event.get("base_damage") is not None else "-"
        row["Quills"] = f"{event['quills_total']:.1f}" if event.get("quills_total") is not None else "-"
        row["Bonus Mult"] = f"{event['bonus_mult']:.3f}" if event.get("bonus_mult") is not None else "-"
        row["Elev Mult"] = f"{event['elevation_mult']:.3f}" if event.get("elevation_mult") is not None else "-"
        row["Crit Mult"] = f"{event['crit_mult_avg']:.3f}" if event.get("crit_mult_avg") is not None else "-"
        row["DEF Mult"] = f"{event['def_mult']:.3f}" if event.get("def_mult") is not None else "-"
        row["Res Mult"] = f"{event['res_mult']:.3f}" if event.get("res_mult") is not None else "-"
        row["Average DMG"] = f"{avg:.1f}" if avg is not None else "-"
        row["Non-Crit DMG"] = f"{nc:.1f}" if nc is not None else "-"
        row["Crit DMG"] = f"{cd:.1f}" if cd is not None else "-"
        row["Effective Avg DMG"] = f"{eff:.1f}" if eff is not None else "-"
        for entry in buff_entries:
            label = BUFF_GROUP_TAG.get(entry["group"], "") + entry["label"]
            row[label] = event.get(entry["key"], "OFF")

        rows.append(row)

    return pd.DataFrame(rows)
