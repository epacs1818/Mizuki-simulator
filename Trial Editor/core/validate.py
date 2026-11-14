"""Validation: cheap, clickable, and the main defence against silent nonsense.

Each issue is `{severity, message, where}`. `where` is the path the UI should
navigate to when the user clicks the issue, e.g. `("fs", "fs_hosh")`.
Severities: "error" (blocks export), "warning", "info".
"""

from __future__ import annotations

from typing import Any

from .models import Spec

EPS = 1e-6


def _issue(severity: str, message: str, where: tuple = ("trial",)) -> dict:
    return {"severity": severity, "message": message, "where": where}


def _describe(trigger: dict, cat) -> str:
    if trigger.get("on") == "crit":
        return "on any critical hit"
    if trigger.get("on") == "ability_end":
        ability = cat.abilities.get(trigger.get("ability", ""))
        return f"after {ability.name if ability else trigger.get('ability')}"
    return str(trigger.get("on"))


def has_errors(issues: list[dict]) -> bool:
    return any(i["severity"] == "error" for i in issues)


def validate(spec_dict: dict[str, Any], result: dict[str, Any] | None = None) -> list[dict]:
    spec = Spec.from_dict(spec_dict)
    cat = spec.catalog
    issues: list[dict] = []
    totals = (result or {}).get("totals", {})

    # ---- trial-level -----------------------------------------------------
    if not spec.trial.slots:
        issues.append(_issue("error", "The trial has no rotations. Add one to start."))
    if spec.trial.duration <= 0:
        issues.append(_issue("error", "Trial duration must be greater than zero."))

    content = totals.get("content_length")
    if content and content > spec.trial.duration + EPS:
        issues.append(
            _issue(
                "warning",
                f"Your rotations run {content:.1f}s but the trial is {spec.trial.duration:.1f}s. "
                "The rest is truncated.",
            )
        )
    if totals.get("truncated_hits"):
        issues.append(
            _issue("warning", f"{totals['truncated_hits']} hit(s) fall outside the trial window and are ignored.")
        )

    for rotation in spec.rotations.values():
        if not rotation.blocks:
            issues.append(_issue("error", f'Rotation "{rotation.name}" has no field sequences.', ("rot", rotation.id)))

    # ---- field-sequence-level --------------------------------------------
    for fs in spec.field_seqs.values():
        owner = cat.characters.get(fs.character)
        owner_name = owner.name if owner else fs.character
        if fs.field_time <= 0:
            issues.append(_issue("error", f'"{owner_name}" has a field time of {fs.field_time:.2f}s.', ("fs", fs.id)))
        if not fs.placements:
            issues.append(_issue("warning", f'"{owner_name}" has no abilities in this field sequence.', ("fs", fs.id)))

        spans: list[dict] = []
        for placement in fs.placements:
            ability = cat.abilities.get(placement.ability)
            if ability is None:
                issues.append(_issue("error", f"Unknown ability id '{placement.ability}'.", ("fs", fs.id)))
                continue
            if ability.character != fs.character:
                issues.append(
                    _issue(
                        "error",
                        f'"{ability.name}" belongs to {cat.characters[ability.character].name}, '
                        f"but this field sequence is {owner_name}.",
                        ("fs", fs.id),
                    )
                )
            if placement.first_hit < 0:
                issues.append(
                    _issue(
                        "error",
                        f'"{ability.name}" starts before the swap-in (-{placement.first_hit:.2f}s).',
                        ("fs", fs.id),
                    )
                )
            if fs.field_time > 0 and placement.first_hit >= fs.field_time - EPS:
                issues.append(
                    _issue(
                        "warning",
                        f'"{ability.name}" is placed at {placement.first_hit:.2f}s, after the '
                        f"{fs.field_time:.2f}s swap-out. Only its delayed hits land on field.",
                        ("fs", fs.id),
                    )
                )

            # Occupancy is only checked when the engine actually models it.
            if ability.action_time is not None:
                spans.append(
                    {
                        "name": ability.name,
                        "start": placement.first_hit,
                        "end": placement.first_hit + ability.action_time,
                    }
                )

        spans.sort(key=lambda s: s["start"])
        for prev, nxt in zip(spans, spans[1:]):
            if nxt["start"] < prev["end"] - EPS:
                issues.append(
                    _issue(
                        "warning",
                        f'"{nxt["name"]}" starts {prev["end"] - nxt["start"]:.2f}s before '
                        f'"{prev["name"]}" finishes casting.',
                        ("fs", fs.id),
                    )
                )

    # ---- continuity between consecutive blocks ----------------------------
    blocks = sorted((result or {}).get("blocks", []), key=lambda b: b["start"])
    for prev, nxt in zip(blocks, blocks[1:]):
        if prev["character"] == nxt["character"]:
            name = cat.characters[prev["character"]].name
            issues.append(
                _issue(
                    "warning",
                    f"{name} swaps out at {prev['end']:.2f}s and swaps right back in at "
                    f"{nxt['start']:.2f}s. Is that intentional?",
                    ("block", nxt["id"]),
                )
            )

    # ---- triggered abilities ---------------------------------------------
    fired = set((result or {}).get("fired_triggers", []))
    for ability_id, trigger in ((result or {}).get("trigger_conditions") or {}).items():
        if ability_id in fired:
            continue
        ability = cat.abilities.get(ability_id)
        if ability is None:
            continue
        issues.append(
            _issue(
                "info",
                f'Triggered ability "{ability.name}" never fires in this trial ({_describe(trigger, cat)}).',
                ("trial",),
            )
        )

    return issues


def validate_rotation(spec_dict: dict[str, Any], rotation_id: str) -> list[dict]:
    """Checks that only make sense inside a single rotation, seam included.

    The loop seam is the point where a rotation repeats. Three things go wrong
    there and all of them are invisible in a flat list of blocks:

    * the rotation ends on a character and immediately re-enters her,
    * an ability is still resolving when the next loop starts,
    * a block points at a field sequence that was deleted.
    """
    spec = Spec.from_dict(spec_dict)
    cat = spec.catalog
    issues: list[dict] = []

    rotation = spec.rotations.get(rotation_id)
    if rotation is None:
        return [_issue("error", f"Unknown rotation '{rotation_id}'.", ("rot", rotation_id))]
    if not rotation.blocks:
        return [_issue("error", "This rotation has no field sequences yet.", ("rot", rotation.id))]

    missing = [b for b in rotation.blocks if b not in spec.field_seqs]
    if missing:
        issues.append(
            _issue(
                "error",
                f"{len(missing)} block(s) point at a field sequence that no longer exists.",
                ("rot", rotation.id),
            )
        )

    blocks = [spec.field_seqs[b] for b in rotation.blocks if b in spec.field_seqs]
    if not blocks:
        return issues

    names = {c.id: c.name for c in cat.characters.values()}

    for index, (first, second) in enumerate(zip(blocks, blocks[1:])):
        if first.character == second.character:
            issues.append(
                _issue(
                    "warning",
                    f"{names[first.character]} swaps out at the end of block {index + 1} and swaps right back "
                    f"in at block {index + 2}. Only do that if the game allows immediate re-entry.",
                    ("rot", rotation.id),
                )
            )

    # ---- the loop seam ---------------------------------------------------
    if len(blocks) >= 2 and blocks[-1].character == blocks[0].character:
        issues.append(
            _issue(
                "warning",
                f"Loop seam: the rotation ends on {names[blocks[-1].character]} and starts on "
                f"{names[blocks[0].character]} again, so every repeat re-enters the same character.",
                ("rot", rotation.id),
            )
        )

    last = blocks[-1]
    for placement in last.placements:
        ability = cat.abilities.get(placement.ability)
        if ability is None:
            continue
        overrun = placement.first_hit + ability.span - last.field_time
        if overrun <= EPS:
            continue
        late = sum(1 for h in ability.hits if placement.first_hit + h.offset > last.field_time + EPS)
        issues.append(
            _issue(
                "info",
                f'"{ability.name}" is still resolving {overrun:.2f}s past the loop seam '
                f"({late} hit(s)); those land during the next loop's first block.",
                ("rot", rotation.id),
            )
        )

    return issues

