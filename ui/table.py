"""The event / audit table shown in the results tab."""

import pandas as pd

import buff_registry
from ui.editors import BUFF_GROUP_TAG, buff_is_active


TEXT_COLUMNS = ("Active", "Owner", "Action", "Reaction")

# The engine writes "-" / "None" / "" for "nothing here". The table treats those as
# MISSING so that the dataframe renders them with the ONE placeholder the app sets
# (results.py passes placeholder="-"). A literal "-" string would render brighter
# than a missing cell, which made identical-looking cells look inconsistent.
EMPTY_TEXT = ("", "-", "None", "nan")


def _text(value):
    """A text cell, or None when the engine used its 'nothing here' sentinel."""
    if value is None:
        return None
    text = str(value).strip()
    return None if text in EMPTY_TEXT else text


def _number(value):
    """A float, or NaN when the event has no value for this row.

    NaN (not "-") keeps the column numeric so st.dataframe sorts by VALUE; the "-"
    the user sees is added by ui.style.style_timeline_dataframe when it paints.
    """
    return float(value) if value is not None else float("nan")


def _gauge(value):
    """"1U" / "1.20U" -> 1.0 / 1.2, "-" (or anything unparseable) -> NaN."""
    if not isinstance(value, str):
        return float("nan")
    text = value.strip()
    if not text.endswith("U"):
        return float("nan")
    try:
        return float(text[:-1])
    except ValueError:
        return float("nan")


def _is_missing(value):
    return value is pd.NA or (isinstance(value, float) and value != value)


def _buff_cell(value):
    """Audit-flag cell: ON/OFF -> True/False, a stack counter stays a number."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text == "ON":
            return True
        if text == "OFF":
            return False
        return pd.NA
    if isinstance(value, (int, float)):
        return value
    return pd.NA


def build_timeline_dataframe(timeline_events, party=None):
    """Flat audit table ordered by block:
        time -> description (active/owner/action) -> reaction (app/aura/reaction)
        -> stats (HP/ATK/DEF/EM/CR/CD) -> multipliers -> output damage -> buffs.

    Buff columns come from buff_registry: only effects whose owner character,
    weapon, artifact set or resonance is present, AND that actually trigger
    somewhere in this run, are ever built into the table.

    Every NUMERIC column is built as a number (float, nullable boolean for ON/OFF
    flags, nullable Int64 for stack counters), so sorting a column in st.dataframe
    sorts values instead of text. Only Active / Owner / Action / Reaction stay text,
    and the engine's "-" / "None" / "" sentinels are stored as missing (None / NaN)
    so the dataframe renders every empty cell with its own placeholder (results.py
    passes placeholder="-"). Units and decimals ("1U", "1.20U", "12.345s") are
    display formats in ui.style.AUDIT_COLUMN_CONFIG.
    """
    if not timeline_events:
        return pd.DataFrame()

    buff_entries = [
        entry for entry in buff_registry.visible_buffs(party or {})
        if any(buff_is_active(ev.get(entry["key"])) for ev in timeline_events)
    ]
    buff_labels = [BUFF_GROUP_TAG.get(entry["group"], "") + entry["label"]
                   for entry in buff_entries]

    rows = []
    for event in timeline_events:
        row = {}
        row["Time (s)"] = float(event["global_time"])
        row["Active"] = _text(event.get("active_character"))
        row["Owner"] = _text(event.get("character"))
        row["Action"] = _text(event.get("action"))
        # Aura comes BEFORE the elemental application it reacts with: it is the state
        # the hit was resolved against, so it only changes on the following row.
        # Both gauges are stored in U; the column formats put the "U" back on screen.
        row["Aura"] = _gauge(event.get("cryo_aura"))
        row["Elemental App"] = _gauge(event.get("elem_app"))
        row["Reaction"] = _text(event.get("reaction"))
        row["HP"] = _number(event.get("stat_hp"))
        row["ATK"] = _number(event.get("stat_atk"))
        row["DEF"] = _number(event.get("stat_def"))
        row["EM"] = _number(event.get("stat_em"))
        # Crit display depends on the build standard: a 100% RV / KQM build carries
        # crit as ONE Crit Value (CV = 2*CR + CD) and lets the engine re-split it, so
        # CR% / CD% are internal storage there. Those rows show the CV instead, which
        # is the number the damage formula actually uses.
        stat_cr = event.get("stat_cr")
        stat_cd = event.get("stat_cd")
        if stat_cr is None or stat_cd is None:
            row["CR%"] = row["CD%"] = row["CV"] = float("nan")
        else:
            is_rv_hit = bool(event.get("rv_mode"))
            row["CR%"] = float("nan") if is_rv_hit else stat_cr * 100.0
            row["CD%"] = float("nan") if is_rv_hit else stat_cd * 100.0
            row["CV"] = (2.0 * stat_cr + stat_cd) * 100.0
        row["Base DMG"] = _number(event.get("base_damage"))
        row["Quills"] = _number(event.get("quills_total"))
        row["Bonus Mult"] = _number(event.get("bonus_mult"))
        row["Elev Mult"] = _number(event.get("elevation_mult"))
        row["Crit Mult"] = _number(event.get("crit_mult_avg"))
        row["DEF Mult"] = _number(event.get("def_mult"))
        row["Res Mult"] = _number(event.get("res_mult"))
        row["Average DMG"] = _number(event.get("average_damage"))
        row["Non-Crit DMG"] = _number(event.get("non_crit"))
        row["Crit DMG"] = _number(event.get("crit_damage"))
        row["Effective Avg DMG"] = _number(event.get("effective_average_damage"))
        for entry, label in zip(buff_entries, buff_labels):
            row[label] = _buff_cell(event.get(entry["key"], "OFF"))

        rows.append(row)

    frame = pd.DataFrame(rows)

    # Numeric contract. A column that never had a value would otherwise stay object
    # (and sort as text), so the dtypes are forced instead of inferred.
    for column in frame.columns:
        if column in TEXT_COLUMNS:
            frame[column] = frame[column].astype(object)
        elif column in buff_labels:
            values = frame[column]
            if all(isinstance(value, bool) for value in values
                   if not _is_missing(value)):
                frame[column] = values.astype("boolean")
            else:
                frame[column] = values.map(
                    lambda value: pd.NA if _is_missing(value) else value
                ).astype("Int64")
        else:
            frame[column] = frame[column].astype("float64")
    return frame

