"""Headless checks for the calculator.

    python smoke_test.py

Covers the engine (deterministic, prices every hit, buff windows disjoint), the
validator (the demo must be error-free), and a full AppTest rerun of app.py so
widget/session-state wiring is exercised without a browser.
"""

from __future__ import annotations

import copy
import json

from core.catalog import default_spec
from core.compare import diff_results
from core.sim import simulate
from core.validate import validate

EPS = 1e-6


def test_engine() -> None:
    spec = default_spec()
    result = simulate(spec)
    totals = result["totals"]

    assert totals["hits"] > 0, "no hits generated"
    assert totals["damage"] > 0, "no damage"
    assert totals["dps"] > 0, "no dps"
    assert totals["truncated_hits"] == 0, "demo trial should fit in its duration"
    assert "odette_c4" in result["fired_triggers"], "crit trigger never fired"

    again = simulate(spec)
    assert again["totals"]["damage"] == totals["damage"], "simulation is not deterministic"
    assert len(again["events"]) == len(result["events"])

    for hit in result["hits"]:
        assert hit["damage"] >= hit["raw"] - EPS, "damage below raw: multiplier went negative"

    times = [event["t"] for event in result["events"]]
    assert times == sorted(times), "events are not time ordered"

    by_buff: dict[str, list[dict]] = {}
    for segment in result["buffs"]:
        by_buff.setdefault(segment["buff"], []).append(segment)
    for segments in by_buff.values():
        segments.sort(key=lambda s: s["start"])
        for prev, nxt in zip(segments, segments[1:]):
            assert nxt["start"] >= prev["end"] - 1e-9, "buff segments overlap"
        for seg in segments:
            assert seg["end"] > seg["start"] and seg["stacks"] >= 1

    # residual hits: the demo deliberately swaps out mid-ultimate
    assert totals["residual_hits"] > 0, "expected off-field hits in the demo"

    print(
        f"engine OK  : {totals['hits']} hits, {totals['damage']:,.0f} damage, "
        f"{totals['dps']:,.0f} dps, {totals['triggered_hits']} triggered, "
        f"{totals['residual_hits']} off-field"
    )


def test_validation() -> None:
    spec = default_spec()
    issues = validate(spec, simulate(spec))
    errors = [i for i in issues if i["severity"] == "error"]
    assert not errors, errors
    print(f"validate OK: {len(issues)} issue(s), 0 errors")


def test_spec_is_json_safe() -> None:
    spec = default_spec()
    blob = json.dumps(spec)
    assert json.loads(blob) == spec, "spec changes shape when serialised"
    print(f"spec OK    : {len(blob):,} bytes of JSON")


def test_app() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    print("app OK     : app.py rendered without exceptions")


def _click(at, label: str):
    button = next(b for b in at.button if b.label == label)
    return button.click().run()


def _active_trial(at) -> dict:
    store = at.session_state["store"]
    return store["trials"][store["active_trial"]]


def test_rotation_rules() -> None:
    from core.validate import validate_rotation

    spec = default_spec()

    issues = validate_rotation(spec, "rot_field")
    assert not [i for i in issues if i["severity"] == "error"], issues
    # rot_field ends on OdetteEE and her Skill Cast resolves for 19.8s.
    assert any("past the loop seam" in i["message"] for i in issues), issues

    # ends on Odette, starts on Aether -> no seam problem
    spec["rotations"]["rot_field"]["blocks"] = ["fs_aether_en1", "fs_odette_ee"]
    assert not any("Loop seam" in i["message"] for i in validate_rotation(spec, "rot_field"))

    # two Aether blocks -> ends on the character it starts with
    spec["rotations"]["rot_field"]["blocks"] = ["fs_aether_en1", "fs_aether_cq"]
    seam = [i for i in validate_rotation(spec, "rot_field") if "Loop seam" in i["message"]]
    assert seam and seam[0]["severity"] == "warning", seam

    # an empty rotation reports an error instead of crashing
    spec["rotations"]["rot_field"]["blocks"] = []
    empty = validate_rotation(spec, "rot_field")
    assert empty and empty[0]["severity"] == "error", empty

    missing = validate_rotation(default_spec(), "nope")
    assert missing[0]["severity"] == "error"

    print("rotation OK: seam + continuity + empty/missing rules")


def test_rotation_preview() -> None:
    from ui.state import rotation_tail

    spec = default_spec()
    rotation = spec["rotations"]["rot_field"]
    loop_time = sum(spec["field_seqs"][b]["field_time"] for b in rotation["blocks"])
    tail = rotation_tail(spec, "rot_field")
    assert tail > 0, "Odette's Skill Cast deliberately overruns her field time"

    preview = {
        "catalog": spec["catalog"],
        "field_seqs": spec["field_seqs"],
        "rotations": spec["rotations"],
        "trial": {
            "id": "_preview",
            "duration": loop_time * 2 + tail,
            "slots": [{"id": "_pv", "rotation": "rot_field", "repeat": 2}],
        },
    }
    result = simulate(preview)
    first = sum(d for k, d in result["by_block"].items() if k.startswith("_pv~0~"))
    second = sum(d for k, d in result["by_block"].items() if k.startswith("_pv~1~"))
    assert first > 0 and second > 0
    assert abs(result["totals"]["damage"] - (first + second)) < 1e-6
    assert result["totals"]["truncated_hits"] == 0, "the preview window must fit both loops plus the tail"

    spanning = [s for s in result["buffs"] if s["start"] < loop_time < s["end"]]
    print(f"preview OK : {first:,.0f} first loop / {second:,.0f} second, {len(spanning)} buff(s) span the seam")


def test_rotation_ui() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=90).run()
    at.segmented_control(key="mode_sw").set_value("Rotation").run()
    assert not at.exception, [e.value for e in at.exception]

    before = list(at.session_state["store"]["rotations"]["rot_field"]["blocks"])
    at.button(key="bdn_rot_field_0").click().run()
    assert not at.exception, [e.value for e in at.exception]
    reordered = list(at.session_state["store"]["rotations"]["rot_field"]["blocks"])
    assert reordered[:2] == [before[1], before[0]], (before, reordered)
    reordered_count = len(reordered)

    at.button(key="brm_rot_field_2").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.session_state["store"]["rotations"]["rot_field"]["blocks"]) == reordered_count - 1

    at = _click(at, "Append to loop")
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.session_state["store"]["rotations"]["rot_field"]["blocks"]) == reordered_count

    # "Edit this field sequence" queues a view intent consumed on the same run.
    at.button(key="bedit_rot_field_0").click().run()
    assert not at.exception, [e.value for e in at.exception]
    first_block = at.session_state["store"]["rotations"]["rot_field"]["blocks"][0]
    assert at.session_state["mode_sw"] == "Field sequence", at.session_state["mode_sw"]
    assert at.session_state["view"]["fs"] == first_block

    print("rotation ui OK: reorder / remove / append / jump to field sequence")


def test_buff_attribution() -> None:
    from core.sim import CRIT_MULTIPLIER

    result = simulate(default_spec())
    rows = result["buff_attribution"]
    assert rows, "no buff attribution produced"
    for row in rows:
        assert 0.0 <= row["uptime"] <= 1.0 + 1e-9, row
        assert row["avg_stacks"] >= 0.0
        assert row["added"] >= 0.0

    # The invariant that makes attribution trustworthy: buff-free damage plus
    # every buff's attributed damage equals the reported total.
    buff_free = sum(hit["raw"] * (CRIT_MULTIPLIER if hit["crit"] else 1.0) for hit in result["hits"])
    attributed = sum(row["added"] for row in rows)
    total = result["totals"]["damage"]
    assert abs(buff_free + attributed - total) < 1e-6, (buff_free, attributed, total)

    active = [row for row in rows if row["added"] > 0]
    assert active, "the demo should have at least one buff doing work"
    print(f"buff OK    : {len(active)} buff(s) add {attributed:,.0f} of {total:,.0f} damage")


def test_compare() -> None:
    spec = default_spec()
    base = simulate(spec)

    unchanged = diff_results(base, base)
    assert unchanged["totals"]["damage"]["delta"] == 0
    assert not unchanged["changed"]

    edited = copy.deepcopy(spec)
    edited["trials"][edited["active_trial"]]["duration"] = 30.0
    diff = diff_results(simulate(edited), base)

    assert diff["totals"]["damage"]["delta"] < -1000, diff["totals"]["damage"]
    assert diff["changed"]
    assert diff["abilities"][0]["delta"] != 0, "rows are sorted by absolute delta"

    # odette_burst never plays inside a 30s window, but it still gets a row
    assert "odette_burst" in {row["ability"] for row in diff["abilities"]}
    print(
        f"compare OK : {diff['totals']['damage']['delta']:+,.0f} damage, "
        f"{len(diff['abilities'])} ability rows, top mover {diff['abilities'][0]['name']}"
    )


def test_share_token() -> None:
    from ui.state import _authored_payload, decode_token, encode_token

    payload = _authored_payload(default_spec())
    token = encode_token(payload)
    assert decode_token(token) == payload
    assert decode_token("not-a-token") is None
    assert decode_token(token[:-4] + "!!!!") is None
    assert len(token) < 4000, "token would make an uncomfortably long URL"
    print(f"share OK   : {len(json.dumps(payload)):,} B JSON -> {len(token):,} char token")


def test_rotation_totals_from_trial() -> None:
    """Rotation damage is read from the trial, so later occurrences inherit buffs."""
    from ui.state import rotation_totals

    result = simulate(default_spec())
    totals = rotation_totals(result)
    assert totals, "the trial should contain at least one rotation"

    measured = totals["rot_field"]
    assert measured["count"] >= 2, "the demo repeats this rotation inside the trial"
    per_occurrence = [round(item["damage"]) for item in measured["per_occurrence"]]
    assert len(set(per_occurrence)) > 1, "every occurrence came out identical - no carry-over?"

    # every block belongs to a rotation, so the parts add up to the trial total
    assert abs(sum(row["damage"] for row in totals.values()) - result["totals"]["damage"]) < 1e-6
    print(
        f"rotation totals OK: {measured['count']}x rot_field, "
        f"{per_occurrence[0]:,.0f} -> {per_occurrence[-1]:,.0f}"
    )


def test_recent_runs_ui() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=90).run()
    at = _click(at, "Record current numbers")
    assert not at.exception, [e.value for e in at.exception]

    runs = at.session_state["runs"]
    assert len(runs) == 1, runs
    assert runs[0]["total"] > 0
    assert runs[0]["delta"] is None, "the first bookmark has nothing to compare against"

    at = _click(at, "Record current numbers")
    assert len(at.session_state["runs"]) == 2
    assert at.session_state["runs"][1]["delta"] is not None, "the second bookmark gets a delta"

    at = _click(at, "Clear")
    assert at.session_state["runs"] == []
    print("recent runs OK: record / delta / clear")


def test_share_ui() -> None:
    from streamlit.testing.v1 import AppTest

    from ui.state import _authored_payload, encode_token

    at = AppTest.from_file("app.py", default_timeout=90).run()
    payload = _authored_payload(at.session_state["store"])
    payload["trials"][payload["active_trial"]]["duration"] = 41.0

    at.query_params["t"] = encode_token(payload)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    store = at.session_state["store"]
    assert store["trials"][store["active_trial"]]["duration"] == 41.0
    assert at.query_params.get("t") is None, "the token should be consumed, not left in the URL"
    print("share ui OK: link applied, then removed from the URL")


def test_rotation_strip_is_one_loop() -> None:
    """The strip draws loop 1 and its tail, never the simulated repeat."""
    from ui.state import _preview_spec
    from ui.timeline import rotation_payload

    spec = default_spec()
    preview = simulate(_preview_spec(spec, "rot_field"))
    loop_time = sum(
        spec["field_seqs"][b]["field_time"] for b in spec["rotations"]["rot_field"]["blocks"]
    )

    payload = rotation_payload(spec, "rot_field", preview, tail=18.0)
    kinds = {}
    for item in payload["items"]:
        kinds.setdefault(item["kind"], []).append(item)

    bands = kinds.get("band", [])
    assert bands, "the loop should have field-time bands"
    assert all(band["start"] < loop_time + 1e-9 for band in bands), "a repeat band leaked in"

    first_ids = {block["id"] for block in preview["blocks"] if block["repeat_index"] == 0}
    expected = sum(1 for hit in preview["hits"] if hit["block"] in first_ids)
    hits = kinds.get("hit", [])
    assert len(hits) == expected, f"{len(hits)} hits drawn, {expected} belong to loop 1"
    # loop 1's own late hits must survive: that is the tail, not the repeat
    assert any(hit["t"] > loop_time for hit in hits), "the loop's own tail disappeared"

    segs = kinds.get("seg", [])
    assert all(seg["start"] < loop_time + 1e-9 for seg in segs), "a repeat buff bar leaked in"

    print(f"one-loop strip OK: {len(bands)} bands, {len(hits)} hits, {len(segs)} buff bars")


def test_character_filter_ui() -> None:
    """The field-sequence screen is scoped to one character."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=90).run()
    at.segmented_control(key="mode_sw").set_value("Field sequence").run()
    assert not at.exception, [e.value for e in at.exception]

    at.selectbox(key="fs_char").set_value("faruzan").run()
    assert not at.exception, [e.value for e in at.exception]

    faruzan = {
        fid for fid, fs in at.session_state["store"]["field_seqs"].items() if fs["character"] == "faruzan"
    }
    assert faruzan, "the demo should have Faruzan sequences"
    # options come back formatted (the display name), not as raw ids
    expected = {at.session_state["store"]["field_seqs"][fid]["name"] for fid in faruzan}
    options = set(at.selectbox(key="fs_pick").options)
    assert options == expected, f"picker leaked other characters: {options - expected}"
    assert at.session_state["fs_pick"] in faruzan
    print(f"character filter OK: {len(faruzan)} sequence(s), nothing leaked")


def test_library_ui() -> None:
    """Create / rename / switch for trials and field sequences, plus focus."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]

    before_trials = len(at.session_state["store"]["trials"])
    at = _click(at, "New trial")
    assert not at.exception, [e.value for e in at.exception]
    store = at.session_state["store"]
    assert len(store["trials"]) == before_trials + 1
    new_trial = store["active_trial"]
    assert at.session_state["trial_pick"] == new_trial, "a new trial should be focused"

    first = [tid for tid in store["trials"] if tid != new_trial][0]
    at.selectbox(key="trial_pick").set_value(first).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["store"]["active_trial"] == first

    at.segmented_control(key="mode_sw").set_value("Field sequence").run()
    assert not at.exception, [e.value for e in at.exception]
    before_seqs = set(at.session_state["store"]["field_seqs"])
    at = _click(at, "New field sequence")
    assert not at.exception, [e.value for e in at.exception]
    store = at.session_state["store"]
    new_seq = (set(store["field_seqs"]) - before_seqs).pop()
    assert at.session_state["fs_pick"] == new_seq, "a new field sequence should be focused"

    at.text_input(key=f"fname_{new_seq}").set_value("Test field").run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["store"]["field_seqs"][new_seq]["name"] == "Test field"

    at.segmented_control(key="mode_sw").set_value("Rotation").run()
    at.text_input(key="rname_rot_field").set_value("Renamed loop").run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["store"]["rotations"]["rot_field"]["name"] == "Renamed loop"
    print("library ui OK: new trial / switch / new field sequence / rename both")


def test_interactions() -> None:
    """Drive the app the way a user would and assert the store followed."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=90).run()
    before = len(_active_trial(at)["slots"])

    at = _click(at, "Add rotation")
    assert not at.exception, [e.value for e in at.exception]
    assert len(_active_trial(at)["slots"]) == before + 1

    at.number_input(key="trial_duration").set_value(30.0).run()
    assert not at.exception, [e.value for e in at.exception]
    assert _active_trial(at)["duration"] == 30.0

    at.segmented_control(key="mode_sw").set_value("Field sequence").run()
    assert not at.exception, [e.value for e in at.exception]

    at.number_input(key="ph_p_en1_skill").set_value(0.5).run()
    assert not at.exception, [e.value for e in at.exception]
    placements = at.session_state["store"]["field_seqs"]["fs_aether_en1"]["placements"]
    assert placements[0]["first_hit"] == 0.5, placements[0]

    at.button(key="rm_p_en1_skill").click().run()
    assert not at.exception, [e.value for e in at.exception]
    remaining = [p["id"] for p in at.session_state["store"]["field_seqs"]["fs_aether_en1"]["placements"]]
    assert "p_en1_skill" not in remaining, remaining

    at = _click(at, "Undo")
    restored = [p["id"] for p in at.session_state["store"]["field_seqs"]["fs_aether_en1"]["placements"]]
    assert "p_en1_skill" in restored, "undo did not restore the removed placement"

    print("ui OK      : add / duration / focus / edit / delete / undo")


if __name__ == "__main__":
    test_engine()
    test_validation()
    test_spec_is_json_safe()
    test_rotation_rules()
    test_rotation_preview()
    test_buff_attribution()
    test_compare()
    test_share_token()
    test_app()
    test_interactions()
    test_rotation_ui()
    test_share_ui()
    test_library_ui()
    test_character_filter_ui()
    test_rotation_strip_is_one_loop()
    test_rotation_totals_from_trial()
    test_recent_runs_ui()
    print("all checks passed")
