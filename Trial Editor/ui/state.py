"""The app's single source of truth, plus every mutation the UI can trigger.

Why a dict store instead of the dataclasses?
-------------------------------------------
`st.session_state` survives reruns but is per-user, per-tab, and every widget
interaction reruns the whole script. Keeping the model as JSON-shaped dicts
means:

* `@st.cache_data` can hash it directly (see `simulate_cached`),
* undo is `deepcopy` and nothing else,
* export / import and share-links are one `json.dumps`,
* no widget can hold a stale reference into the engine's objects.

Mutators follow one rule: `begin()` snapshots for undo, then edit in place.
They are called from `on_click` / `on_change` / component callbacks, all of
which run *before* widgets are instantiated, so mutating session state there is
always legal.
"""

from __future__ import annotations

import base64
import copy
import json
import time
import uuid
import zlib

import streamlit as st

from core.catalog import default_spec
from core.sim import simulate

UNDO_LIMIT = 50
TIMELINE_KEY = "timeline"

# Widget-key prefixes that belong to authored content (cleared on reset).
_EPHEMERAL = {
    "rot", "rep", "ph", "ft", "pick", "newat", "menu", "trial", "fs",
    "rname", "newblk", "tname", "fname",
}

# A rotation preview simulates the rotation repeatedly so the loop seam is real
# rather than a drawing convention.
PREVIEW_SLOT = "_pv"
PREVIEW_LOOPS = 2

DEFAULT_VIEW = {
    "mode": "trial",  # "trial" | "rot" | "fs"
    "fs": "fs_aether_en1",  # focused field sequence
    "rot": "rot_field",  # focused rotation
    "cursor": None,  # playhead, seconds
    "selected": None,  # ("block" | "placement" | "hit", value)
    "zoom": 0,  # 0 = fit to width
    "pending": None,  # deferred navigation request (see request_view)
}


def init() -> None:
    st.session_state.setdefault("store", default_spec())
    st.session_state.setdefault("undo", [])
    st.session_state.setdefault("view", dict(DEFAULT_VIEW))
    st.session_state.setdefault("prev_damage", None)
    st.session_state.setdefault("baseline", None)


def store() -> dict:
    return st.session_state.store


def view() -> dict:
    v = st.session_state.view
    for key, default in DEFAULT_VIEW.items():
        v.setdefault(key, default)
    return v


# --------------------------------------------------------------------------
# undo
# --------------------------------------------------------------------------


def begin() -> dict:
    """Snapshot the current spec, then return the live dict to mutate."""
    snapshots = st.session_state.undo
    snapshots.append(copy.deepcopy(st.session_state.store))
    if len(snapshots) > UNDO_LIMIT:
        del snapshots[0 : len(snapshots) - UNDO_LIMIT]
    return st.session_state.store


def undo() -> None:
    if st.session_state.undo:
        st.session_state.store = st.session_state.undo.pop()
        st.session_state.prev_damage = None


def can_undo() -> bool:
    return bool(st.session_state.undo)


def forget(*keys: str) -> None:
    """Drop widget state so a native widget re-seeds itself from the model."""
    for key in keys:
        st.session_state.pop(key, None)


def sync_widget(key: str, value) -> None:
    """Mirror a model change into a live widget key.

    The timeline can change a value that a `st.number_input` also shows. Because
    component callbacks run *before* widgets are instantiated on that run,
    assigning the widget key here is legal and keeps the two views in lockstep.
    If the widget has never been rendered the assignment is skipped and the
    widget will seed itself from the model instead.
    """
    if key in st.session_state:
        st.session_state[key] = value


# --------------------------------------------------------------------------
# simulation (cached on the spec itself)
# --------------------------------------------------------------------------


@st.cache_data(max_entries=64, show_spinner=False)
def simulate_cached(spec: dict) -> dict:
    return simulate(spec)


# --------------------------------------------------------------------------
# mutations - field sequences
# --------------------------------------------------------------------------


def move_placement(placement_id: str, first_hit: float) -> bool:
    spec = begin()
    for fs in spec["field_seqs"].values():
        for placement in fs["placements"]:
            if placement["id"] == placement_id:
                placement["first_hit"] = round(max(0.0, float(first_hit)), 3)
                sync_widget(f"ph_{placement_id}", placement["first_hit"])
                return True
    return False


def set_field_time(fs_id: str, value: float) -> None:
    spec = begin()
    spec["field_seqs"][fs_id]["field_time"] = round(max(0.5, float(value)), 2)
    sync_widget(f"ft_{fs_id}", spec["field_seqs"][fs_id]["field_time"])


def add_placement(fs_id: str, ability_id: str, at: float) -> str:
    spec = begin()
    pid = "p_" + uuid.uuid4().hex[:6]
    spec["field_seqs"][fs_id]["placements"].append(
        {"id": pid, "ability": ability_id, "first_hit": round(max(0.0, float(at)), 2)}
    )
    return pid


def remove_placement(placement_id: str) -> None:
    spec = begin()
    for fs in spec["field_seqs"].values():
        fs["placements"] = [p for p in fs["placements"] if p["id"] != placement_id]


# --------------------------------------------------------------------------
# mutations - the field-sequence library
# --------------------------------------------------------------------------


def add_field_sequence(character: str) -> str:
    spec = begin()
    fs_id = "fs_" + uuid.uuid4().hex[:5]
    owner = spec["catalog"]["characters"].get(character, {}).get("name", character)
    spec["field_seqs"][fs_id] = {
        "id": fs_id,
        "name": f"{owner} field {len(spec['field_seqs']) + 1}",
        "character": character,
        "field_time": 2.0,
        "placements": [],
    }
    st.session_state.prev_damage = None
    return fs_id


def rename_field_sequence(fs_id: str, name: str) -> None:
    spec = begin()
    fs = spec["field_seqs"].get(fs_id)
    if fs and name.strip():
        fs["name"] = name.strip()


def delete_field_sequence(fs_id: str) -> None:
    spec = begin()
    if fs_id not in spec["field_seqs"]:
        return
    del spec["field_seqs"][fs_id]
    # A block pointing at a deleted sequence would be a dangling reference.
    for rotation in spec["rotations"].values():
        rotation["blocks"] = [b for b in rotation["blocks"] if b != fs_id]
    st.session_state.prev_damage = None


# --------------------------------------------------------------------------
# mutations - trials (the library) and their slots
# --------------------------------------------------------------------------


def active_trial(spec: dict) -> dict:
    """The trial the engine simulates; trials themselves live in a library."""
    return spec["trials"][spec["active_trial"]]


def set_active_trial(trial_id: str) -> None:
    # Navigation rather than an edit: deliberately outside begin(), so switching
    # trial does not bury a real change in the undo stack.
    spec = store()
    if trial_id in spec["trials"]:
        spec["active_trial"] = trial_id
        st.session_state.prev_damage = None


def add_trial() -> str:
    spec = begin()
    tid = "trial_" + uuid.uuid4().hex[:5]
    spec["trials"][tid] = {
        "id": tid,
        "name": f"Trial {len(spec['trials']) + 1}",
        "duration": 60.0,
        "slots": [],
    }
    spec["active_trial"] = tid
    st.session_state.prev_damage = None
    return tid


def rename_trial(trial_id: str, name: str) -> None:
    spec = begin()
    trial = spec["trials"].get(trial_id)
    if trial and name.strip():
        trial["name"] = name.strip()


def delete_trial(trial_id: str) -> None:
    spec = begin()
    # Never delete the last trial: the app always needs one to simulate.
    if trial_id not in spec["trials"] or len(spec["trials"]) <= 1:
        return
    del spec["trials"][trial_id]
    if spec["active_trial"] == trial_id:
        spec["active_trial"] = next(iter(spec["trials"]))
    st.session_state.prev_damage = None


def set_duration(value: float) -> None:
    spec = begin()
    active_trial(spec)["duration"] = round(max(1.0, float(value)), 2)


def set_slot_repeat(index: int, repeat: int) -> None:
    spec = begin()
    slots = active_trial(spec)["slots"]
    if 0 <= index < len(slots):
        slots[index]["repeat"] = max(1, int(repeat))


def set_slot_rotation(index: int, rotation_id: str) -> None:
    spec = begin()
    slots = active_trial(spec)["slots"]
    if 0 <= index < len(slots):
        slots[index]["rotation"] = rotation_id


def move_slot(index: int, delta: int) -> None:
    spec = begin()
    slots = active_trial(spec)["slots"]
    target = index + delta
    if 0 <= index < len(slots) and 0 <= target < len(slots):
        slots[index], slots[target] = slots[target], slots[index]


def duplicate_slot(index: int) -> None:
    spec = begin()
    slots = active_trial(spec)["slots"]
    if 0 <= index < len(slots):
        clone = copy.deepcopy(slots[index])
        clone["id"] = "s_" + uuid.uuid4().hex[:6]
        slots.insert(index + 1, clone)


def delete_slot(index: int) -> None:
    spec = begin()
    slots = active_trial(spec)["slots"]
    if 0 <= index < len(slots):
        slots.pop(index)


def add_slot(rotation_id: str | None = None) -> None:
    spec = begin()
    rotations = spec["rotations"]
    if not rotations:
        return
    active_trial(spec)["slots"].append(
        {"id": "s_" + uuid.uuid4().hex[:6], "rotation": rotation_id or next(iter(rotations)), "repeat": 1}
    )


def rotation_duration(spec: dict, rotation_id: str) -> float:
    rotation = spec["rotations"].get(rotation_id)
    if not rotation:
        return 0.0
    return sum(
        float(spec["field_seqs"][b]["field_time"]) for b in rotation["blocks"] if b in spec["field_seqs"]
    )


# --------------------------------------------------------------------------
# reset / import / export
# --------------------------------------------------------------------------


def reset() -> None:
    st.session_state.store = default_spec()
    st.session_state.undo = []
    st.session_state.prev_damage = None
    st.session_state.baseline = None
    st.session_state.view = dict(DEFAULT_VIEW)
    # Widget state for content that no longer exists must go too, otherwise the
    # next run seeds stale ids into the new model.
    for key in list(st.session_state.keys()):
        if str(key).split("_")[0] in _EPHEMERAL:
            del st.session_state[key]


def _authored_payload(spec: dict) -> dict:
    """Only the authored content; the catalog is code, not data."""
    return {
        "version": 2,
        "field_seqs": spec["field_seqs"],
        "rotations": spec["rotations"],
        "trials": spec["trials"],
        "active_trial": spec["active_trial"],
    }


def _apply_authored(data: dict) -> str | None:
    if not isinstance(data, dict) or "field_seqs" not in data:
        return "Expected keys: field_seqs, rotations, trial(s)."

    if "trials" in data:
        trials = data["trials"]
        active = data.get("active_trial") if data.get("active_trial") in trials else next(iter(trials))
    elif "trial" in data:
        # v1 files and share links stored a single trial under "trial".
        legacy = dict(data["trial"])
        legacy.setdefault("name", legacy["id"])
        trials = {legacy["id"]: legacy}
        active = legacy["id"]
    else:
        return "Expected keys: field_seqs, rotations, trial(s)."
    if not trials:
        return "That file has no trials in it."

    spec = begin()
    spec["field_seqs"] = data["field_seqs"]
    spec["rotations"] = data.get("rotations", {})
    spec["trials"] = trials
    spec["active_trial"] = active
    sync_widget("trial_duration", active_trial(spec)["duration"])
    st.session_state.prev_damage = None
    return None


def export_json() -> str:
    return json.dumps(_authored_payload(store()), indent=2)


def import_json(text: str) -> str | None:
    """Replace authored content. Returns an error message, or None on success."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return f"Not valid JSON: {exc.msg} (line {exc.lineno})"
    return _apply_authored(data)


def encode_token(payload: dict) -> str:
    """Compact, URL-safe token. ~5 KB of JSON becomes ~1.4 K characters."""
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii").rstrip("=")


def decode_token(token: str) -> dict | None:
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = zlib.decompress(base64.urlsafe_b64decode(padded.encode("ascii")))
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, zlib.error, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def share_token() -> str:
    return encode_token(_authored_payload(store()))


def load_share_token(token: str) -> str | None:
    data = decode_token(token)
    if data is None:
        return "That share link could not be read."
    return _apply_authored(data)


# --------------------------------------------------------------------------
# recent runs
#
# Numbers stay live, so a "run" here is a deliberate bookmark of the current
# totals rather than a gate on the calculation. The delta is against the previous
# bookmark, which makes it a record of what an edit did.
# --------------------------------------------------------------------------

RUN_HISTORY_LIMIT = 12


def runs() -> list[dict]:
    return st.session_state.setdefault("runs", [])


def record_run(result: dict) -> None:
    totals = result["totals"]
    history = runs()
    previous = history[-1]["total"] if history else None
    history.append(
        {
            "at": time.strftime("%H:%M:%S"),
            "total": totals["damage"],
            "dps": totals["dps"],
            "hits": totals["hits"],
            "delta": (
                (totals["damage"] - previous) / previous * 100
                if previous and abs(previous) > 1e-9
                else None
            ),
        }
    )
    del history[:-RUN_HISTORY_LIMIT]


def clear_runs() -> None:
    st.session_state.runs = []


# --------------------------------------------------------------------------
# deferred navigation
#
# The view switch is a widget with a key, and a widget key cannot be written to
# after that widget has been instantiated in the current run. A button deep
# inside a screen therefore records an *intent*; `consume_pending()` applies it
# at the very top of the next run, before the switch exists. That is the clean
# way to do "open this field sequence" without a modal or an extra click.
# --------------------------------------------------------------------------

_MODE_LABEL = {"trial": "Trial", "rot": "Rotation", "fs": "Field sequence"}


def request_view(mode: str, *, fs: str | None = None, rot: str | None = None) -> None:
    view()["pending"] = {"mode": mode, "fs": fs, "rot": rot}


def consume_pending() -> None:
    v = view()
    pending = v.pop("pending", None)
    if not pending:
        return
    mode = pending.get("mode") or v["mode"]
    v["mode"] = mode
    label = _MODE_LABEL.get(mode)
    if label:
        st.session_state["mode_sw"] = label
    if pending.get("fs"):
        v["fs"] = pending["fs"]
        st.session_state.pop("fs_pick", None)
    if pending.get("rot"):
        v["rot"] = pending["rot"]
        st.session_state.pop("rot_pick", None)


# --------------------------------------------------------------------------
# rotation previews
#
# A rotation is previewed by simulating it as a real 2x trial rather than being
# drawn from a formula, so the loop seam is whatever the engine says it is:
# residual hits, buffs still ticking, triggers firing across the boundary.
# --------------------------------------------------------------------------


def rotation_tail(spec: dict, rotation_id: str) -> float:
    """How long abilities keep resolving past the end of the rotation's last block.

    The preview window has to include this, otherwise the tail of the second loop
    is silently truncated and the seam stops telling the truth.
    """
    rotation = spec["rotations"].get(rotation_id) or {}
    tail = 0.0
    for fs_id in rotation.get("blocks", []):
        fs = spec["field_seqs"].get(fs_id)
        if not fs:
            continue
        for placement in fs.get("placements", []):
            ability = spec["catalog"]["abilities"].get(placement["ability"])
            if not ability:
                continue
            span = max((hit["offset"] for hit in ability["hits"]), default=0.0)
            tail = max(tail, placement["first_hit"] + span - float(fs["field_time"]))
    return max(0.0, tail) + 0.05


def _preview_spec(spec: dict, rotation_id: str) -> dict:
    return {
        "catalog": spec["catalog"],
        "field_seqs": spec["field_seqs"],
        "rotations": spec["rotations"],
        "trial": {
            "id": "_preview",
            "duration": rotation_duration(spec, rotation_id) * PREVIEW_LOOPS + rotation_tail(spec, rotation_id),
            "slots": [{"id": PREVIEW_SLOT, "rotation": rotation_id, "repeat": PREVIEW_LOOPS}],
        },
    }


@st.cache_data(max_entries=32, show_spinner=False)
def rotation_preview_cached(spec: dict, rotation_id: str) -> dict:
    return simulate(_preview_spec(spec, rotation_id))


def rotation_totals(result: dict) -> dict[str, dict]:
    """Per-rotation damage as it actually happened in the trial.

    Read straight out of the trial's blocks, so a rotation that runs second
    inherits the buffs and the late hits of the rotation before it. That is the
    point of measuring here instead of in an isolated preview: no cold start, and
    no extra simulation per rotation.
    """
    totals: dict[str, dict] = {}
    for block in result["blocks"]:
        row = totals.setdefault(
            block["rotation"],
            {
                "id": block["rotation"],
                "name": block["rotation_name"],
                "damage": 0.0,
                "duration": 0.0,
                "occurrences": {},
            },
        )
        damage = result["by_block"].get(block["id"], 0.0)
        row["damage"] += damage
        row["duration"] += block["end"] - block["start"]

        occurrence = row["occurrences"].setdefault(block["occurrence"], {"at": block["start"], "damage": 0.0})
        occurrence["damage"] += damage
        occurrence["at"] = min(occurrence["at"], block["start"])

    for row in totals.values():
        row["dps"] = row["damage"] / row["duration"] if row["duration"] > 0 else 0.0
        row["count"] = len(row["occurrences"])
        row["per_occurrence"] = sorted(
            ({"at": item["at"], "damage": item["damage"]} for item in row["occurrences"].values()),
            key=lambda item: item["at"],
        )
        del row["occurrences"]
    return totals


# --------------------------------------------------------------------------
# mutations - rotations
# --------------------------------------------------------------------------


def add_rotation() -> str:
    spec = begin()
    rid = "rot_" + uuid.uuid4().hex[:5]
    spec["rotations"][rid] = {"id": rid, "name": f"Rotation {len(spec['rotations']) + 1}", "blocks": []}
    st.session_state.prev_damage = None
    return rid


def set_rotation_name(rotation_id: str, name: str) -> None:
    spec = begin()
    rotation = spec["rotations"].get(rotation_id)
    if rotation and name.strip():
        rotation["name"] = name.strip()


def add_rotation_block(rotation_id: str, field_seq_id: str | None) -> None:
    if not field_seq_id:
        return
    spec = begin()
    rotation = spec["rotations"].get(rotation_id)
    if rotation and field_seq_id in spec["field_seqs"]:
        rotation["blocks"].append(field_seq_id)
        st.session_state.prev_damage = None


def remove_rotation_block(rotation_id: str, index: int) -> None:
    spec = begin()
    rotation = spec["rotations"].get(rotation_id)
    if rotation and 0 <= index < len(rotation["blocks"]):
        rotation["blocks"].pop(index)
        st.session_state.prev_damage = None


def move_rotation_block(rotation_id: str, index: int, delta: int) -> None:
    spec = begin()
    rotation = spec["rotations"].get(rotation_id)
    if not rotation:
        return
    blocks = rotation["blocks"]
    target = index + delta
    if 0 <= index < len(blocks) and 0 <= target < len(blocks):
        blocks[index], blocks[target] = blocks[target], blocks[index]
        st.session_state.prev_damage = None


def duplicate_rotation_block(rotation_id: str, index: int) -> None:
    spec = begin()
    rotation = spec["rotations"].get(rotation_id)
    if rotation and 0 <= index < len(rotation["blocks"]):
        rotation["blocks"].insert(index + 1, rotation["blocks"][index])
        st.session_state.prev_damage = None


def delete_rotation(rotation_id: str) -> None:
    spec = begin()
    if rotation_id not in spec["rotations"]:
        return
    del spec["rotations"][rotation_id]
    spec["trial"]["slots"] = [s for s in spec["trial"]["slots"] if s["rotation"] != rotation_id]
    st.session_state.prev_damage = None

