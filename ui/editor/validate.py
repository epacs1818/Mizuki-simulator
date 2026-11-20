"""Pre-flight warnings for the three libraries.

Every check works on the spec alone, so a trial that cannot run still shows why.
Runtime notices (the cooldown the engine actually hit) come from
engine.simulate() and are merged by the view.
"""

from __future__ import annotations

from models import ChargePool, interrupted_hit_count
from weapons import get_skill_cd_reset

INFO = "info"
WARNING = "warning"
ERROR = "error"
MAX_ISSUES = 40


def _issue(severity, message, where):
    return {"severity": severity, "message": message, "where": where}


def _char(spec: dict, cid: str) -> str:
    return spec["catalog"]["characters"].get(cid, {}).get("name", cid)


def sequence_issues(spec: dict, sequence_key: str) -> list:
    """One field sequence: something to cast, a window to cast it in."""
    sequence = spec["field_seqs"].get(sequence_key)
    where = ("fs", sequence_key)
    if sequence is None:
        return [_issue(ERROR, "This field sequence no longer exists.", where)]
    issues = []
    label = sequence["name"]
    if not sequence["placements"]:
        issues.append(_issue(ERROR, "%s places nothing: add an ability first." % label, where))
    if float(sequence["field_time"]) <= 0:
        issues.append(_issue(ERROR, "%s has no field time: drag the swap-out handle." % label, where))
    for placement in sequence["placements"]:
        ability = spec["catalog"]["abilities"].get(placement["ability"])
        if ability is None:
            issues.append(_issue(ERROR, "%s references an unknown ability." % label, where))
            continue
        when = float(placement["first_hit"])
        window = float(sequence["field_time"])
        if when > window + 1e-9:
            issues.append(_issue(INFO, "%s starts at %.3fs, after the %.3fs swap-out: it resolves off-field." % (ability["name"], when, window), where))
        hits = ability.get("hits") or ()
        kept = len(hits)
        if ability.get("interrupt_on_swap_out"):
            times = [when + float(hit["offset"]) for hit in hits]
            kept = interrupted_hit_count(times, window)
        if 0 < kept < len(hits):
            issues.append(_issue(INFO, "%s is interrupted by the %.3fs swap-out: %d of its %d hits land." % (ability["name"], window, kept, len(hits)), where))
    return issues


def rotation_issues(spec: dict, rotation_key: str) -> list:
    """One rotation: at least one block, and no dangling references."""
    rotation = spec["rotations"].get(rotation_key)
    where = ("rotation", rotation_key)
    if rotation is None:
        return [_issue(ERROR, "This rotation no longer exists.", where)]
    issues = []
    label = rotation["name"]
    if not rotation["blocks"]:
        issues.append(_issue(ERROR, "%s has no field sequences in it." % label, where))
    if int(rotation.get("repeat", 1)) < 1:
        issues.append(_issue(ERROR, "%s repeats %s times: use at least one." % (label, rotation.get("repeat", 1)), where))
    for block in rotation["blocks"]:
        sequence = spec["field_seqs"].get(block)
        if sequence is None:
            issues.append(_issue(ERROR, "%s references a field sequence that no longer exists." % label, where))
        elif float(sequence["field_time"]) <= 0:
            issues.append(_issue(WARNING, "%s has a block with no field time: the loop stalls there." % label, where))
    return issues


def schedule(spec: dict, trial_key: str):
    """(casts, content_length): every cast in order, and where the content ends.

    The chaining mirrors engine._blocks exactly, so the times here are the times the
    engine will schedule.
    """
    trial = spec["trials"].get(trial_key) or {}
    casts = []
    t = 0.0
    for slot in trial.get("slots", []):
        rotation = spec["rotations"].get(slot["rotation"])
        if rotation is None:
            continue
        for _ in range(max(1, int(slot.get("repeat", 1)))):
            for block in rotation["blocks"]:
                sequence = spec["field_seqs"].get(block)
                if sequence is None:
                    continue
                for placement in sequence["placements"]:
                    ability = spec["catalog"]["abilities"].get(placement["ability"]) or {}
                    casts.append((
                        round(t + float(placement["first_hit"]), 6),
                        sequence["character"],
                        placement["ability"],
                        ability.get("name", ""),
                        float(ability.get("cooldown", 0.0) or 0.0),
                        ability.get("cooldown_family") or ability.get("name", ""),
                        int(ability.get("ability_max_charges") or 1),
                    ))
                t += float(sequence["field_time"])
    return casts, round(t, 6)


def cooldown_issues(spec: dict, trial_key: str, casts=None, resets=None) -> list:
    """Casts that land before the previous cast cooldown is over.

    *resets* maps a character id to the internal cooldown of a weapon that can END
    the elemental skill's cooldown (Sacrificial Fragments / Bow). Such a cast is a
    guaranteed proc at its own cast time: it clears that character's skill
    abilities, so a later skill cast is legal inside the ability cooldown.

    Cooldowns are shared per (character, cooldown family): the two forms of one
    in-game button (Mizuki's pullout/standard, Diona's tap/hold) clash with each
    other, while Odette's cast and recast stay independent. The family - not the
    ability id - is the key, exactly like timeline.add_field_sequence().

    Stocked skills (Sucrose's 2 casts) use the same models.ChargePool as the engine:
    a cast spends a charge, the recharge timer starts on the FIRST spend, and the
    cooldown is only reported once the pool is empty.

    This is the pre-flight view only. The engine re-checks exactly, and it also
    knows about procs from a skill's LATER ticks (a tail tick can eat the weapon's
    ICD and leave the next rotation without a reset), so a real clash still comes
    back from engine.simulate() / the trial runner.
    """
    where = ("trial", trial_key)
    if casts is None:
        casts, _ = schedule(spec, trial_key)
    resets = resets or {}
    abilities = spec["catalog"]["abilities"]
    skill_ids = {}
    skill_families = {}
    for ability_id, payload in abilities.items():
        if payload.get("category") == "skill":
            character = payload.get("character")
            skill_ids.setdefault(character, set()).add(ability_id)
            skill_families.setdefault(character, set()).add(
                (character, payload.get("cooldown_family") or payload.get("id")))
    pools = {}
    icd_ready = {}
    issues = []
    for when, character, ability_id, name, cooldown, family, max_charges in casts:
        key = (character, family)
        if cooldown > 0:
            pool = pools.get(key)
            if pool is None:
                pool = pools[key] = ChargePool(max_charges)
            available = pool.block_until(cooldown, when)
            if available is not None:
                # A refused cast is reported and NOT spent, so the list shows every
                # cast that is genuinely early instead of swallowing the next ones.
                issues.append(_issue(ERROR, "%s is cast at %.3fs but is on cooldown until %.3fs." % (name, when, available), where))
                if len(issues) >= MAX_ISSUES:
                    break
            else:
                # The FIRST spend starts the recharge timer; later spends do not
                # push it back (a 1-charge skill is the old ready-at rule).
                pool.consume(cooldown, when)

        icd = resets.get(character)
        if icd is None or ability_id not in skill_ids.get(character, ()):
            continue
        if when < icd_ready.get(character, float("-inf")) - 1e-6:
            continue
        icd_ready[character] = when + icd
        for skill_family in skill_families.get(character, ()):
            pool = pools.get(skill_family)
            if pool is not None:
                pool.grant(when)
    return issues


def _party_view(spec: dict, party):
    """(party ids, {character id: skill-CD reset ICD}) from a party dict or id list.

    A gear-aware party (the app's ``{name: {weapon, refinement, ...}}`` mapping) lets
    the cooldown pre-flight honour the Sacrificial weapons; a plain id list (the
    smoke test) keeps the old behaviour.
    """
    if not isinstance(party, dict):
        return set(party or []), {}
    by_name = {payload.get("name"): cid
               for cid, payload in spec["catalog"]["characters"].items()}
    party_ids, resets = set(), {}
    for name, data in party.items():
        cid = by_name.get(name)
        if cid is None:
            continue
        party_ids.add(cid)
        data = data or {}
        icd, _label = get_skill_cd_reset(data.get("weapon"), data.get("refinement", 1))
        if icd is not None:
            resets[cid] = icd
    return party_ids, resets


def _sequences_used(spec: dict, trial: dict) -> list:
    """Every field sequence the trial plays, in order, once each."""
    seen = []
    for slot in trial.get("slots", []):
        rotation = spec["rotations"].get(slot["rotation"])
        if rotation is None:
            continue
        for sequence_key in rotation["blocks"]:
            if sequence_key in spec["field_seqs"] and sequence_key not in seen:
                seen.append(sequence_key)
    return seen


def trial_issues(spec: dict, trial_key: str, party=None) -> list:
    """One trial: structure, party fit, window fit and cooldowns.

    *party* may be the party dict the app runs (weapons/refinements included, so
    the Sacrificial weapons' skill-CD reset is honoured) or a plain list/set of
    character ids.
    """
    trial = spec["trials"].get(trial_key)
    where = ("trial", trial_key)
    if trial is None:
        return [_issue(ERROR, "This trial no longer exists.", where)]
    issues = []
    label = trial["name"]
    if not trial["slots"]:
        issues.append(_issue(ERROR, "%s has no rotation slots." % label, where))
    if trial.get("end_mode") == "time" and float(trial.get("end_time", 0.0)) <= 0:
        issues.append(_issue(ERROR, "%s runs for %.3fs: give it a length or end it at the last swap." % (label, float(trial.get("end_time", 0.0))), where))
    for slot in trial["slots"]:
        if slot["rotation"] not in spec["rotations"]:
            issues.append(_issue(ERROR, "%s references a rotation that no longer exists." % label, where))

    casts, content = schedule(spec, trial_key)
    if trial.get("end_mode") == "time":
        window = float(trial.get("end_time", 0.0))
        if window > 0 and content > window + 1e-6:
            issues.append(_issue(WARNING, "%s is %.3fs long but the trial runs %.3fs: the last %.3fs is cut." % (label, content, window, content - window), where))
    elif content <= 0:
        issues.append(_issue(ERROR, "%s ends at the last swap but schedules nothing." % label, where))

    party, resets = _party_view(spec, party)
    missing = [c for c in (trial.get("required_party") or []) if c not in party]
    if missing and party:
        issues.append(_issue(WARNING, "%s was authored for %s, so the runner will not offer it to this party." % (label, ", ".join(_char(spec, c) for c in missing)), where))
    if party:
        used = []
        for cast in casts:
            character = cast[1]
            if character not in party and character not in used:
                used.append(character)
        if used:
            issues.append(_issue(WARNING, "%s uses %s, who are not in your party: they run with default stats." % (label, ", ".join(_char(spec, c) for c in used)), where))

    # A trial is only as good as the sequences it plays, so a broken block is
    # reported here too - rolled up per sequence and pointing at the sequence
    # itself, which is what makes the warning clickable.
    for sequence_key in _sequences_used(spec, trial):
        found = [issue for issue in sequence_issues(spec, sequence_key)
                 if issue["severity"] in (ERROR, WARNING)]
        if not found:
            continue
        if len(found) == 1:
            issues.append(found[0])
        else:
            issues.append(_issue(WARNING,
                                 "%s: %d problems in this field sequence."
                                 % (spec["field_seqs"][sequence_key]["name"], len(found)),
                                 ("fs", sequence_key)))

    issues.extend(cooldown_issues(spec, trial_key, casts, resets))
    return issues
