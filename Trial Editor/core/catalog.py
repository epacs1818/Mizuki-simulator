"""Real data lifted from the Mizuki simulator (`My Program/abilities.py` + `presets.py`).

Only the *data* crosses over - the shapes are this project's own. Anything the
demo engine cannot express yet is marked TODO so the mismatch stays visible
instead of being smoothed away.
"""

from __future__ import annotations

from .models import (
    Ability,
    Buff,
    Catalog,
    Character,
    FieldSequence,
    Hit,
    Placement,
    Rotation,
    Spec,
    Trial,
    TrialSlot,
)

# The source stores motion values as fractions of ATK (0.941 == 94.1%). This
# project prices a hit as `raw x multipliers`, so a nominal 1000 ATK stands in
# for the stat sheet until the real damage_calc.py is wired in here.
ATK = 1000.0


def _h(offset: float, mv: float, crit: bool = False) -> Hit:
    return Hit(offset=offset, raw=round(mv * ATK), crit=crit)


def _hits(*pairs: tuple[float, float]) -> tuple[Hit, ...]:
    return tuple(_h(offset, mv) for offset, mv in pairs)


# --------------------------------------------------------------------------
# Characters (element-appropriate colours)
# --------------------------------------------------------------------------

CHR_MIZUKI = Character("mizuki", "Mizuki", "#e0a13a", "M")
CHR_AETHER = Character("aether", "Aether", "#6fb8d9", "A")
CHR_ODETTE = Character("odette", "Odette", "#a78bfa", "O")
CHR_FARUZAN = Character("faruzan", "Faruzan", "#4dbfa0", "F")

# --------------------------------------------------------------------------
# Buffs
#
# TODO: the real buffs are conditional stat mods (party composition, active
# character, RES shred, stellar-only damage). These keep the timed,
# ability-applied shape this engine actually simulates.
# --------------------------------------------------------------------------

BUFF_ODETTE_C2 = Buff(
    "odette_c2", "Odette C2 (RES shred)", duration=20.0, per_stack=0.25, max_stacks=1,
    color="#a78bfa", kind="enemy",
)
BUFF_AETHER_C2 = Buff(
    "aether_c2", "Aether C2 (EM)", duration=8.0, per_stack=0.20, max_stacks=2, color="#6fb8d9",
)

# --------------------------------------------------------------------------
# Mizuki's continuous-attack pattern: one cast hit, then ticks every ~0.7-1.0s.
# The source ships one ability per pull-out length, so the tick count *is* the
# ability variant - that is a modelling choice of theirs, kept intact.
# --------------------------------------------------------------------------

TICK_TIMES = (0.929, 1.619, 2.639, 3.300, 3.990, 4.800, 5.490, 6.269, 6.989, 7.679, 8.489, 9.179, 9.869)


def _skill_ticks(count: int) -> tuple[Hit, ...]:
    return (_h(0.0, 1.039),) + tuple(_h(t, 0.808) for t in TICK_TIMES[:count])


# --------------------------------------------------------------------------
# Odette's dance: every timestamp carries a standard hit AND a Stellar one, so
# duplicate timestamps are the norm rather than an edge case.
# --------------------------------------------------------------------------

ODETTE_CAST_TIMES = (2.220, 4.080, 6.180, 8.010, 10.110, 11.940, 14.040, 15.901, 17.940, 19.800)
ODETTE_BURST_TIMES = (1.441, 2.790, 4.560, 6.120, 8.161, 9.990, 12.060, 13.890, 15.960, 17.821)


def _dance(times: tuple[float, ...], preamble: tuple[tuple[float, float], ...] = ()) -> tuple[Hit, ...]:
    hits = [_h(offset, mv) for offset, mv in preamble]
    for index, when in enumerate(times):
        first, second = (0.775, 0.730) if index % 2 == 0 else (0.926, 0.872)
        hits += [_h(when, first), _h(when, second)]
    return tuple(hits)


# --------------------------------------------------------------------------
# Abilities
# --------------------------------------------------------------------------

ABILITIES = [
    # ---- Mizuki ----------------------------------------------------------
    Ability("mizuki_n1", "N1", "mizuki", "basic", _hits((0.0, 0.941))),
    Ability("mizuki_charged", "Charged Attack", "mizuki", "basic", _hits((0.0, 2.340))),
    Ability("mizuki_skill2", "Skill [2 Ticks]", "mizuki", "skill", _skill_ticks(2)),
    Ability("mizuki_skill5", "Skill [5 Ticks]", "mizuki", "skill", _skill_ticks(5)),
    Ability("mizuki_skill13", "Skill [13 Ticks]", "mizuki", "skill", _skill_ticks(13)),
    Ability(
        "mizuki_burst",
        "Mizuki Burst",
        "mizuki",
        "ultimate",
        (_h(0.0, 1.693),) + tuple(_h(t, 1.270) for t in (1.8, 3.3, 4.8, 6.3, 7.8, 9.3, 10.8, 12.3)),
    ),
    # ---- Aether ----------------------------------------------------------
    Ability("aether_n1", "N1", "aether", "basic", _hits((0.0, 0.880))),
    Ability(
        "aether_n1ca",
        "Charged Attack",
        "aether",
        "basic",
        _hits((0.0, 0.880), (0.510, 2.505), (0.720, 2.600)),
        buff="aether_c2",
        buff_at=1,
    ),
    Ability(
        "aether_skill",
        "Elemental Skill",
        "aether",
        "skill",
        (_h(0.0, 1.650),)
        + tuple(_h(t, 0.385) for t in (3.149, 3.329, 6.030, 6.269, 8.969, 9.179, 11.880, 12.090, 14.880, 15.090)),
    ),
    Ability(
        "aether_burst",
        "Elemental Burst",
        "aether",
        "ultimate",
        # Two hits share 0.550 on purpose: the source has multi-component hits.
        _hits((0.0, 1.721), (0.550, 1.721), (0.550, 1.721), (0.660, 1.721), (0.780, 1.721)),
        buff="aether_c2",
        buff_at=0,
    ),
    # ---- Odette ----------------------------------------------------------
    Ability(
        "odette_cast",
        "Skill Cast",
        "odette",
        "skill",
        _dance(ODETTE_CAST_TIMES, ((0.0, 1.945),)),
        buff="odette_c2",
        buff_at=0,
    ),
    Ability(
        "odette_recast",
        "Skill Recast",
        "odette",
        "skill",
        # The 8.256 hit is flagged as a crit so the C4 trigger has something to fire on.
        (_h(0.0, 1.725), _h(0.180, 1.725), _h(0.300, 1.725), _h(0.871, 8.256, crit=True)),
    ),
    Ability(
        "odette_burst",
        "Odette Burst",
        "odette",
        "ultimate",
        _dance(ODETTE_BURST_TIMES, ((0.0, 1.983), (0.391, 1.983), (0.510, 1.983), (0.631, 3.065))),
    ),
    # ---- Faruzan ---------------------------------------------------------
    Ability("faruzan_skill", "Skill Cast", "faruzan", "skill", _hits((0.0, 3.162))),
    Ability("faruzan_burst", "Elemental Burst", "faruzan", "ultimate", _hits((0.0, 8.024))),
    # ---- Triggered -------------------------------------------------------
    # TODO: the real Odette C4 fires on any party STELLAR hit with a 3.5s
    # internal cooldown. This engine only understands "on crit" and "after
    # ability X", so one recast hit is flagged as a crit to stand in for it.
    Ability(
        "odette_c4",
        "Odette C4 Extra Stellar",
        "odette",
        "triggered",
        _hits((0.010, 0.990)),
        trigger={"on": "crit", "delay": 0.0},
    ),
]

# --------------------------------------------------------------------------
# Field sequences - copied from presets.py, swap_out_time and call times intact
# --------------------------------------------------------------------------

FIELD_SEQS = [
    FieldSequence(
        "fs_aether_en1", "AetherEN1", "aether", 1.230,
        (Placement("p_en1_skill", "aether_skill", 0.601), Placement("p_en1_n1", "aether_n1", 1.200)),
    ),
    FieldSequence(
        "fs_aether_ecq", "AetherECQ", "aether", 3.631,
        (
            Placement("p_ecq_skill", "aether_skill", 0.601),
            Placement("p_ecq_n1ca", "aether_n1ca", 1.200),
            Placement("p_ecq_burst", "aether_burst", 3.061),
        ),
    ),
    FieldSequence(
        "fs_aether_cq", "AetherCQ", "aether", 2.941,
        (Placement("p_cq_n1ca", "aether_n1ca", 0.510), Placement("p_cq_burst", "aether_burst", 2.371)),
    ),
    FieldSequence(
        "fs_odette_ee", "OdetteEE", "odette", 2.371,
        (Placement("p_ee_cast", "odette_cast", 0.660), Placement("p_ee_recast", "odette_recast", 1.170)),
    ),
    FieldSequence(
        "fs_odette_qe", "OdetteQE", "odette", 3.451,
        (Placement("p_qe_burst", "odette_burst", 2.160), Placement("p_qe_recast", "odette_recast", 2.250)),
    ),
    FieldSequence(
        "fs_mizuki_p1", "Skill Pullout 1 Nuke", "mizuki", 1.750,
        (Placement("p_p1_skill", "mizuki_skill2", 0.301),),
    ),
    FieldSequence(
        "fs_mizuki_p2", "Skill Pullout 2 Nukes", "mizuki", 4.101,
        (Placement("p_p2_skill", "mizuki_skill5", 0.301),),
    ),
    FieldSequence(
        "fs_mizuki_p4", "Skill Pullout 4 Nukes", "mizuki", 10.000,
        (Placement("p_p4_skill", "mizuki_skill13", 0.301),),
    ),
    FieldSequence(
        "fs_mizuki_b4", "Burst Pullout 4 Nukes", "mizuki", 9.300,
        (Placement("p_b4_skill", "mizuki_skill13", 0.301), Placement("p_b4_burst", "mizuki_burst", 8.301)),
    ),
    FieldSequence(
        "fs_mizuki_n1c", "N1C", "mizuki", 1.410,
        (Placement("p_n1c_n1", "mizuki_n1", 0.660), Placement("p_n1c_charged", "mizuki_charged", 1.080)),
    ),
    FieldSequence(
        "fs_faruzan_q", "FaruzanQSwap", "faruzan", 1.410,
        (Placement("p_fq_burst", "faruzan_burst", 1.200),),
    ),
    FieldSequence(
        "fs_faruzan_e", "FaruzanESwap", "faruzan", 1.410,
        (Placement("p_fe_skill", "faruzan_skill", 1.200),),
    ),
]

# --------------------------------------------------------------------------
# Rotations and trial
#
# Their presets run 5-10 blocks; these are trimmed to 3 so the editor stays
# readable. The trial fills 117.2s of a 140s window, so nothing is truncated.
# --------------------------------------------------------------------------

ROTATIONS = [
    Rotation("rot_field", "Aether → Mizuki → Odette", ("fs_aether_en1", "fs_mizuki_p4", "fs_odette_ee")),
    Rotation("rot_burst", "Mizuki burst field", ("fs_mizuki_b4", "fs_aether_ecq", "fs_odette_qe")),
    # Not used by the trial: gives the comparison table a third row.
    Rotation("rot_quick", "Quick swap", ("fs_aether_cq", "fs_mizuki_n1c", "fs_faruzan_q")),
]

TRIAL = Trial(
    "trial",
    "Full rotation",
    duration=140.0,
    slots=(TrialSlot("slot_a", "rot_field", 5), TrialSlot("slot_b", "rot_burst", 3)),
)

# A second trial so the trial library has something in it.
TRIAL_BURST = Trial(
    "trial_burst",
    "Burst check",
    duration=40.0,
    slots=(TrialSlot("slot_c", "rot_burst", 1),),
)


def catalog() -> Catalog:
    return Catalog(
        characters={c.id: c for c in (CHR_MIZUKI, CHR_AETHER, CHR_ODETTE, CHR_FARUZAN)},
        abilities={a.id: a for a in ABILITIES},
        buffs={b.id: b for b in (BUFF_ODETTE_C2, BUFF_AETHER_C2)},
    )


def default_spec() -> dict:
    """The JSON-serialisable spec the Streamlit session state stores."""
    spec = Spec(
        catalog=catalog(),
        field_seqs={f.id: f for f in FIELD_SEQS},
        rotations={r.id: r for r in ROTATIONS},
        trials={t.id: t for t in (TRIAL, TRIAL_BURST)},
        active_trial=TRIAL.id,
    )
    return spec.to_dict()

