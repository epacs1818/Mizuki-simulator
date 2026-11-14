# Rotation calculator — Streamlit slice

A concrete, runnable version of the trial editor we discussed:
`Trial → Rotations → Field sequences → Abilities → Hits`, with a draggable
timeline, live recomputation, clickable validation, and an event log.

```powershell
streamlit run app.py
python smoke_test.py     # headless checks: engine, validator, app, UI round-trip
```

## Data provenance

The characters, abilities, hit timings, field sequences and rotations are lifted
from **`My Program/`** (the Mizuki simulator): `abilities.py` for the hit lists,
`presets.py` for the field sequences and rotations, `characters.py` for the
roster. Only the data crossed over — none of its UI or engine.

| Source | Here |
|---|---|
| `Ability(name, character, hits=[Hit(name, relative_delay, motion_value, ...)])` | `Ability(id, name, character, category, hits=[Hit(offset, raw)])` |
| `FieldSequence(name, character, swap_out_time)` + `add_ability(start_time, ability)` | `FieldSequence(id, name, character, field_time, placements=[(first_hit, ability)])` |
| `Rotation(name, sequences, repetitions)` | `Rotation(id, name, blocks)` |
| `Trial(end_time)` | `Trial(id, name, duration, slots)` — now a **library** (`spec["trials"]` + `active_trial`); `Spec.trial` still resolves the active one, so the engine never changed. Old exports and share links that store a single `trial` are still read. |

Deliberate simplifications, marked `TODO` in `core/catalog.py`:

- **`raw = motion_value × 1000`** — a nominal 1000 ATK standing in for the stat
  sheet until `damage_calc.py` is wired into `core/sim.py`.
- **Buffs** are timed, ability-applied multipliers. The real ones are conditional
  stat mods (party composition, active character, RES shred, stellar-only).
- **Triggers**: one `Odette C4 Extra Stellar` on `crit`. The real one fires on any
  party STELLAR hit with a 3.5 s internal cooldown, which this trigger model
  cannot express — so one recast hit is flagged `crit` to stand in for it.
- **Cooldowns** (15 s / 19 s) are not modelled, and your rotations are designed
  around them. That is the largest remaining gap.

## UI polish pass

- **Off-field prose is gone, the shading stayed.** Removed: the "After swap-out"
  metric, `· off-field` in tooltips, `+N late` on field-sequence bars, the
  `N after swap-out` caption, and the validator rule that reported it. Kept: the
  faded ticks and the striped tail on the field-sequence bar, because that is the
  readable version of the same fact.
- **Every level has a library.** Trials, rotations and field sequences can each be
  created, renamed (a labelled box under the selector) and deleted. Deleting a
  field sequence also removes it from every rotation; the last trial cannot be
  deleted because the engine always needs one.
- **Creating focuses the new object**, for all three levels, by making the widget
  key authoritative instead of relying on `index=`.
- **The rename box no longer fights you.** It used to be re-stamped from the model
  on every rerun (`st.text_input` only commits on Enter), which erased typing and
  looked like focus jumping. The key is per-object, so the box is only seeded once.
- **One strip density.** No zoom controls: rotation and trial run at a fixed
  40 px/s ("detailed"), the field sequence always fits its content.
- **Quieter strips.** Trial and rotation bands are colour only (names live in the
  tooltip), and the rotation draws one loop: loop 1's bands, hits and buff bars
  are drawn, the simulated repeat is not. Buff bars stay on both; the
  field-sequence strip has none.
- **The field-sequence strip zooms to field time.** The axis stops just past the
  swap-out, so a 1.2 s visit fills the strip at maximum zoom; the after-swap tail
  is drawn beyond the right edge and reached by scrolling, keeping the dimmed
  ticks and striped shading without pretending they happen on field.
- **Field sequences are scoped by character.** A character selector sits above the
  sequence picker; both the picker and the library table only show that
  character's sequences, and new ones are created for them.



## What your data changed in the engine

Four things in your numbers did not fit the demo, and three of them were real bugs:

1. **Single hits** (`mizuki_n1`, `aether_n1`, `faruzan_burst`…) produced a 3 px
   sliver with no label in the field-sequence editor. Draggable bands now get a
   **14 px minimum** hit area, and a label that does not fit moves **outside** the
   bar (`.band .bl.out`).
2. **Duplicate timestamps** (`aether_burst` has two hits at 0.550; every Odette
   dance step is a standard + Stellar pair) drew one tick on top of another.
   Hits sharing a row and a timestamp are now **staggered by ±3.2 px** with a
   `1/2` suffix in the tooltip.
3. **Spans dwarf field time** (`aether_skill` = 15.09 s inside a 1.23 s visit), so
   the field-sequence strip must fit the whole span or the visit becomes a sliver.
   It now always fits, with the swap-out drawn as the striped boundary between the
   on-field and after-swap regions.
4. **Occupancy is not a thing in your model** — `start_time` in your presets is a
   *hit* time (your own Sucrose comment says so), so abilities overlap by design.
   `Ability.action_time` is now optional, and the overlap warning only fires when
   an engine actually models cast occupancy. In its place there is a rule that
   *does* matter for you: **a placement at or after the swap-out** ("only its
   delayed hits land on field").

The headline number this exposes: **259 of 473 hits (55%) land off-field**, which
is the normal state of your model rather than an edge case.

## What's here

| Screen | What you can do |
|---|---|
| **Trial** | A library of trials (new / rename / delete / switch). Per trial: rotation slots with repeat counts, duration, the strip, warnings, the trial library — with the event log underneath everything. |
| **Rotation** | A library of rotations (new / rename / delete). Per rotation: reorderable blocks, one-rotation strip, warnings, and the rotation table, whose damage is measured **inside the trial**. |
| **Field sequence** | A library of field sequences (new / rename / delete), scoped to one character. Per sequence: drag abilities, drag the swap-out handle, add/remove abilities. |
| **Sidebar** | Recent runs · export/import JSON · share link · reset. |
| **Top bar** | View switch (Trial / Rotation / Field sequence) next to **Undo**. |

## Why it is shaped like this

| Layer | File | Rule |
|---|---|---|
| Model | `core/models.py` | Frozen dataclasses. The engine's typed input. |
| Catalog | `core/catalog.py` | Demo game data. Swap for your real loader. |
| Engine | `core/sim.py` | `simulate(spec_dict) -> result_dict`, pure, no Streamlit, deterministic. |
| Validation | `core/validate.py` | `validate(spec, result) -> [{severity, message, where}]`, clickable. |
| Store | `ui/state.py` | The only mutable state: JSON-shaped dicts in `st.session_state` + undo snapshots. |
| Component | `ui/timeline.py` | The one non-native widget (CCv2, inline HTML/CSS/JS). |
| Screens | `ui/blocks.py`, `ui/results.py`, `app.py` | Widgets + dispatch. No business logic. |

Three decisions do most of the work:

1. **The model is JSON-shaped dicts, not dataclasses.** That makes
   `@st.cache_data` hashing, `deepcopy` undo, and `json.dumps` export free.
   `core/models.py` is the adapter at the engine boundary.
2. **`simulate()` is pure.** Every screen is a projection of its output, so
   authored intent and computed truth can never disagree.
3. **JS emits intents, never state.** The timeline sends `select` / `moved` /
   `retimed` / `seek` triggers; Python applies them in `on_*_change` callbacks
   (which run before widgets instantiate) and re-renders the payload. Drag is
   optimistic and local, so it stays smooth despite the server round-trip.

## Swapping in your real engine

`core/sim.py` is a reference implementation. Replace its body with a call to
you engine and keep the result keys:

```python
def simulate(spec_dict: dict) -> dict:
    spec = Spec.from_dict(spec_dict)         # your dataclasses
    ...                                      # your timeline
    return {
        "blocks":  [...],   # {id, field_seq, character, start, end, rotation_name, beyond}
        "hits":    [...],   # {t, ability, ability_name, character, block, raw, damage,
                            #  multiplier, crit, hit_index, hit_count, source, on_field, active_buffs}
        "events":  [...],   # {t, kind, character, label, damage, source, block}
        "buffs":   [...],   # {buff, start, end, stacks}
        "by_character": {...}, "by_ability": {...}, "by_block": {...},
        "totals": {"damage", "dps", "hits", "duration", "content_length",
                   "truncated_hits", "residual_hits", "triggered_hits"},
        "fired_triggers": [...], "trigger_conditions": {...},
    }
```

Nothing else needs to change: the UI reads only those keys. If your engine wants
different field-sequence fields, edit `FieldSequence` in `core/models.py` and
`from_dict` is the only place that has to keep up.

## The loop seam (rotation screen)

A rotation is a loop, so the interesting damage is at the boundary. The preview
is not drawn from arithmetic on field times: `state.rotation_preview_cached`
builds a throwaway trial of `2 × rotation` (plus the longest ability overrun)
and runs the real engine on it. Consequences that fall out for free:

- residual hits from the last block really do land in the next loop's first block,
- buffs that started in loop 1 are still ticking in loop 2, so loop 2 is worth
  more (in your data: 64,569 → 68,665 damage),
- triggered abilities fire across the boundary,
- `validate_rotation` can talk about "past the loop seam" instead of guessing.

The strip draws **loop 1 only**, with a `loop end` marker; anything a loop-1 cast
resolves past that point stays visible in the tail, so the seam is still readable
without a second copy of the rotation. The 2-loop simulation is kept for the
validation message, not for the drawing.

## Buff attribution (why the numbers add up)

Each hit is priced as `raw × crit × Π(1 + per_stack × stacks)`. Splitting that
product between buffs is the ambiguous part, so `core/sim.py::_buff_summary`
uses a **log decomposition**: a buff's share of the total lift is
`ln(1 + p_i·s_i) / Σ ln(...)`. That is order-independent and the shares sum
exactly to the lift, which gives one testable invariant:

```
buff-free damage + Σ attributed damage == reported total
```

The demo satisfies it to 1e-6: `158,789` of `696,141` damage comes from the two
buffs. Uptime and average stacks are read off the same disjoint buff segments
the timeline draws, so the table and the ribbon can never disagree.

## Rotation numbers come from the trial

The rotation table and the rotation metrics are read out of the **trial's** blocks
(`state.rotation_totals(result)` groups `by_block` by rotation), not out of the
isolated preview. So an occurrence inherits the buffs and the late hits of
everything that ran before it, and no extra simulation is needed — one trial
already contains every rotation.

In the demo `rot_field` runs five times: **64,569 → 71,592** (+10.9%). Its first
occurrence lands exactly on the isolated loop figure, which is the cross-check
that both paths agree; the per-occurrence expander shows the ramp.

## Recent runs

Numbers are live: the metric row updates on every edit, and its delta is against
the previous rerun. "Record current numbers" in the sidebar bookmarks the totals
you are looking at; each bookmark's delta is against the **previous bookmark**, so
the list reads as a history of what your edits did. Twelve are kept.

`core/compare.py` (`diff_results`) is still here and still tested, but unplugged:
it matches abilities by id and returns `current / baseline / delta / pct`. It is
what a "compare two runs" feature would be built on.

## Share links

`?t=` carries `zlib` + `base64url` of the authored content only — the current
build is 3,670 B of JSON → a **1,019-character** token, comfortably inside URL
limits.
The sidebar shows it through `st.code`, which gives a native copy button without
any clipboard hack. On arrival the token is applied and then **deleted from the
URL**, so your later edits never sit under a link that claims to be someone
else's build.

## Deliberately not built yet (the M4 list)

- Preset/template library, and a field-sequence duplication flow.
- Patch mode: keep two catalogs and diff them (the compare plumbing already
  works on any two results, so this is mostly catalog loading).
- Timeline: shared horizontal zoom across screens, and a "seek to event" jump
  from the issue list.
- Packaged component (only if `ui/timeline.py` outgrows one file).

## Widget-state gotchas this code already handles

- Empty label on icon-only buttons (`st.button` in 1.66 has no `label_visibility`).
- `number_input` + `key=` + `setdefault`, so the timeline can write into the same
  key from its callback without the widget going stale.
- Orphaned widget keys are purged on reset, so deleted ids cannot leak back in.
- `st.segmented_control` (not `st.tabs`) for view switching, so hidden screens
  don't compute.
- **Deferred navigation** (`state.request_view` / `consume_pending`): a widget key
  cannot be written after the widget is instantiated, so "Edit this field
  sequence" queues an intent that the *next* run applies before the view switch
  is built. Callbacks work in the same run; inline handlers add `st.rerun()`.
- Seed `mode_sw` with `setdefault` and mount the switch with `key=` only:
  passing both `default=` and a Session State value logs a warning.
- AppTest hands you live objects, so snapshot with `list(...)` before asserting
  on a list the app mutates in place.
- `st.code(url, language=None, wrap_lines=True)` is the cheapest copy-to-clipboard
  affordance; `st.context.url` can be `None` in tests, so the share helper falls
  back to the bare token.
- Apply a `?t=` share token before rendering, then delete it from the URL: a
  token left in place keeps re-importing and misrepresents later edits.
- `st.metric(..., help=...)` is supported, which is where the baseline value and
  percentage change go — the `delta=` string itself stays short.
