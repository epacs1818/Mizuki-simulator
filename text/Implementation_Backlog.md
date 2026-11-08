# Party Configuration Backlog

Tracks which characters, constellations, weapons, artifact sets and buffs have
been verified against in-game records. The `New test` calibration set is the
only fully verified configuration so far; everything else is a stub that still
needs a manual pass.

Legend: ✔ = verified (the `New test` set or an automated invariant in
`smoke_test.py`) | ◻ = implemented but not yet verified

## Characters

| Character | Element | Constellations offered | Status | Notes |
| --- | --- | --- | --- | --- |
| Mizuki | Anemo | C0-C6 | ✔ | C2 verified (shred + flat-EM PHEC bonus); C6 verified (party stellar crit + flat-EM crit) |
| Aether | Cryo | C4-C6 | ✔ | C6 verified (Frostglow / Aether C6 stellar) |
| Odette | Cryo | C0 | ✔ | C2 verified (Marvelous stacks); Snow Swan's Dream = 20s self stellar_bonus |
| Anastasya | Cryo | C0 | ✔ | Burst party stellar_bonus (0.575 @ B13, 20s), A1 (+16% CD others/19s), A4 reaction-only jubilee (+0.15) + Lv2 vortices (3 swirls to detonate), Jubilee passive, Triumph (next swap-in, provisional delay 0.0 → every loop from the 2nd), conditional extra stellar beat |
| Faruzan | Anemo | C6 | ✔ | C6 CD buff + Anemo shred verified |
| Sucrose | Anemo | C0-C6 | ✔ | A1/A4/C6 verified (scope, magnitude and window) |
| Diona | Cryo | C6 | ◻ | C6 EM / stellar buff only — no timeline trigger yet |

## Weapons

| Weapon | Type | Status |
| --- | --- | --- |
| Sacrificial Fragments | Catalyst | ✔ |
| New Bough | Sword | ✔ (1 stack/s to 3 inside a 12s skill-opened window) |
| Silver Light | Sword | ✔ |
| Exaiphanes Blade | Sword | ✔ |
| Favonius Warbow | Bow | ✔ |
| The Widsith (Average) | Catalyst | ✔ (10s buff on taking the field, 30s CD, ⅓ of each roll) |
| The Widsith (All EM) | Catalyst | ✔ (same window, EM roll only) |
| Sacrificial Jade | Catalyst | ✔ (on/off-field toggle passive) |
| Sunny Morning Sleep-In | Catalyst | ✔ (swirl 6s / skill 9s / burst 30s EM windows) |
| Starcaller's Watch | Catalyst | ✔ (permanent EM only, no buff) |
| A Thousand Floating Dreams | Catalyst | ✔ (permanent stats from party composition) |
| Wandering Evenstar | Catalyst | ✔ (10s cycle / 12s buff, stacks to 2, self + others) |
| Thrilling Tales of Dragon Slayers | Catalyst | ✔ (swap-out proc → next character, 10s, 20s CD) |
| Starsealed Edict | Catalyst | ✔ (permanent CD% + 20s skill-cast EM window + swirl stacks) |
| Whitelake Frostfeather | Sword | ✔ (3 stacks × 8s, stellar crit DMG at 3) |
| Finale Of The Deep | Sword | ✔ (15s ATK% window, 10s CD) |
| Azurelight | Sword | ✔ (permanent ATK% only) |
| Aquila Favonia | Sword | ✔ (permanent ATK% only) |
| Sacrificial Bow | Bow | ✔ (base ATK + ER, no description) |
| Breezeborne Refrain | Bow | ✔ (permanent ER + 3 sigils → party stellar_bonus 12s) |
| Elegy for the End | Bow | ✔ (permanent EM + 4 sigils → party ATK%/EM, 20s lockout) |
| Silverdawn | Bow | ✔ (6s self ATK%/stellar crit, +3s per swirl/stellar hit) |

## Artifact sets

| Set | Status |
| --- | --- |
| 2p/2p EM | ✔ |
| 2p/2p ATK | ✔ |
| Heart Of The Furnace | ✔ |
| Viridescent Venerer | ✔ |
| Instructor | ✔ (on-field swirl → party EM 8s) |
| Gilded Dreams | ✔ (swirl → holder composition buff, 8s / 8s CD) |
| Noblesse Oblige | ✔ (burst cast → party ATK% 12s) |
| Tenacity Of The Millelith | ✔ (skill hit → party ATK% 3s, 0.5s CD) |
| A Day Carved From Rising Winds | ✔ (any standard hit → holder ATK% 6s) |
| Scarlet Proof | ✔ (on-field swirl → holder CR + stellar 10s) |
| New Tsaritsa set | ✔ (stacks 0-2, on-field decay, Cryo CR + stellar CR) |

## Effects (buff_registry.py)

Buff columns are gated by owner: a column only appears when the character
(and constellation), weapon, artifact set or resonance that provides it is
present in the party.

| Label | Group | Owner | Requirement | Status |
| --- | --- | --- | --- | --- |
| Mizuki DDS | Character | Mizuki | always | ✔ |
| Mizuki A4 EM | Character | Mizuki | always | ✔ |
| Mizuki VBTD EM | Character | Mizuki | always | ✔ |
| Mizuki C1 Shred | Character | Mizuki | C1+ | ✔ |
| Faruzan C6 CD (Anemo) | Character | Faruzan | C6 | ✔ |
| Faruzan C6 Anemo Shred | Character | Faruzan | C6 | ✔ |
| Aether C2 EM | Character | Aether | C2+ | ✔ |
| Aether C2 EM (Amp) | Character | Aether | C2+ | ✔ |
| Aether Frostglow | Character | Aether | always | ✔ |
| Aether C6 Stellar | Character | Aether | C6 | ✔ |
| Odette Marvelous | Character | Odette | always | ✔ |
| Odette Burst Stellar | Character | Odette | always | ◻ |
| Odette C2 ATK | Character | Odette | C2+ | ◻ |
| Sucrose A1 EM | Character | Sucrose | always | ✔ |
| Sucrose A4 EM | Character | Sucrose | always | ✔ |
| Sucrose C6 Cryo DMG | Character | Sucrose | C6 | ✔ |
| Anastasya Burst Stellar | Character | Anastasya | always | ✔ |
| Anastasya A1 CD | Character | Anastasya | always | ✔ |
| Anastasya A4 Jubilee | Character | Anastasya | always | ✔ |
| Anastasya Triumph | Character | Anastasya | always | ✔ |
| Exaiphanes ATK% | Weapon | Exaiphanes Blade | equipped | ✔ |
| Silver Light EM Stacks | Weapon | Silver Light | equipped | ✔ |
| Widsith Buff | Weapon | The Widsith (Average) / (All EM) | equipped | ✔ |
| Sacrificial Jade | Weapon | Sacrificial Jade | equipped | ✔ |
| Sunny Swirl/Skill/Burst EM | Weapon | Sunny Morning Sleep-In | equipped | ✔ |
| Evenstar Stacks | Weapon | Wandering Evenstar | equipped | ✔ |
| TTDS ATK% | Weapon | Thrilling Tales of Dragon Slayers | equipped | ✔ |
| Starsealed EM / Stacks | Weapon | Starsealed Edict | equipped | ✔ |
| Whitelake Stacks / 3-Stack Crit | Weapon | Whitelake Frostfeather | equipped | ✔ |
| Finale ATK% | Weapon | Finale Of The Deep | equipped | ✔ |
| Breezeborne Sigils / Buff | Weapon | Breezeborne Refrain | equipped | ✔ |
| Elegy Sigils / Buff | Weapon | Elegy for the End | equipped | ✔ |
| New Bough Stacks | Weapon | New Bough | equipped | ✔ |
| Silverdawn Buff / Ext | Weapon | Silverdawn | equipped | ✔ |
| HotF Stellar | Artifact | Heart Of The Furnace | equipped | ✔ |
| VV Elemental Shred | Artifact | Viridescent Venerer | equipped | ✔ |
| Instructor EM | Artifact | Instructor | equipped | ✔ |
| Gilded Dreams | Artifact | Gilded Dreams | equipped | ✔ |
| Noblesse ATK% | Artifact | Noblesse Oblige | equipped | ✔ |
| Tenacity ATK% | Artifact | Tenacity Of The Millelith | equipped | ✔ |
| Rising Winds ATK% | Artifact | A Day Carved From Rising Winds | equipped | ✔ |
| Scarlet Proof | Artifact | Scarlet Proof | equipped | ✔ |
| Tsaritsa Stacks / Cryo CR / Stellar CR | Artifact | New Tsaritsa set | equipped | ✔ |
| Cryo Resonance CR | Team | Cryo Resonance | 2+ Cryo + Cryo aura | ✔ |

## Verified buff semantics (asserted by smoke_test.py)

| Effect | Invariant |
| --- | --- |
| Sucrose A1 | +50 EM, non-Anemo allies only, 8s, procs when she is the anemo contributor |
| Sucrose A4 | +20% of her FLAT EM, others only, 8s, refreshed by any skill/burst hit |
| Sucrose C6 | +20% cryo_bonus party-wide, window = [first burst hit, last burst hit] = 5.729s |
| Mizuki C6-1 | +10% stellar CR / +20% stellar CD party-wide while DDS is up (C6 only) |
| Mizuki C6-2 | +0.04% CR / +0.16% CD per FLAT EM above 500, capped 20% / 80% at 1000 |
| Flat EM basis | base + weapon + artifacts + flat buffs; % shares (VBTD2, Sucrose A4) never feed it |

## Buff architecture (buffs.py + stats_calc.py)

`buffs.py` is a pure DATA catalogue; all arithmetic lives in `stats_calc.py`.
Four tables, one dispatch table:

| Table | Contents | Resolution |
| --- | --- | --- |
| `CONDITIONAL_CONSTANT_BUFFS` | flat stat values (optionally `[R1..R5]`) | added as-is |
| `CONDITIONAL_NON_CONSTANT_BUFFS` | declarative dynamic effects | `evaluate_dynamic_buff()` |
| `STACK_BUFFS` | per-stack values | value x stack count |
| `DORMANT` | effects with known values but no modelled trigger | never resolved |
| `stats_calc.FLAG_TO_BUFFS` | timeline flag -> effect descriptors | the single dispatch point |

Dynamic effects never carry a lambda. Each declares a **basis**:

| basis | meaning | example |
| --- | --- | --- |
| `em` | caster's initial EM (base + weapon + artifacts + permanent) | Mizuki C2 elemental bonus |
| `flat_em` | caster's FLAT EM basis (never % shares) | Mizuki swirl bonus, VBTD2, C6-2, Sucrose A4 |
| `atk` | caster's resolved ATK from the initial stats | Aether/Odette A4 + jubilee, Odette mv_mult |
| `talent` | the value IS a talent scaling from `skill_scalings` | Odette burst, Faruzan C6 anemo bonus |

`value = min(floor + ratio * max(basis - offset, 0), cap)`, where `ratio` may be a
refinement list or be derived from a talent (`ratio_from_talent`).
Talent levels are read once by `get_talent_level()` (N/S/B config), not parsed
per character.

`smoke_test.py` asserts the catalogue is consistent: every entry is either
reachable from `FLAG_TO_BUFFS` or listed in `DORMANT`, every dispatch key exists,
and every dynamic descriptor uses a known basis. A dead entry can no longer hide.

### Weapons

Weapons split in exactly two halves:

* **Permanent** — base ATK, the secondary stat, and any *description* stat that is
  always on (refinement-keyed values merged into the secondary, e.g.
  `Starcaller's Watch` EM = 265 + [100…200]). These live in `weapons.py` and are
  folded into `initial_stats`, so they show up in the card stats.
* **Buffs** — anything conditional (Widsith roll, Jade toggle, Sunny's procs).
  One timeline flag per effect, values in `buffs.py`, dispatch in `FLAG_TO_BUFFS`.

Weapon buffs are holder-only by construction: the descriptor's caster is the
sentinel `"holder:<Weapon Name>"`, which resolves to the party member equipping
it (`None` if nobody does, which makes every target check fail). A single flag can
therefore serve several value variants — The Widsith's two variants share
`widsith_state` and the unequipped one is skipped automatically.

Weapon labels go through `weapons.resolve_weapon_key()`, which strips only a
trailing `(R<digit>)`; a weapon's own parentheses ("The Widsith (Average)") are
kept, and `build_initial_stats` no longer mis-parses those names.

Per-element DMG bonuses (e.g. Widsith's elemental third) are written out element
by element and are **standard-damage only** — they never enter stellar or
stellar-reaction damage, matching Sucrose C6's `cryo_bonus`.

Three phase-2 capabilities worth knowing about:

* **Party-composition permanent stats** — a weapon can declare a `party_stats`
  block in `weapons.py` (`em_per_other_element`, `elem_bonus_per_same`,
  `em_to_others`). `stats_calc.apply_weapon_party_stats()` applies it to the whole
  `initial_stats` map (holder + allies). It is **idempotent** (removes its previous
  delta first), so the UI (card stats) and the timeline can both call it.
* **Basis-scaled stacks** — a `"type": "stack"` descriptor whose key lives in
  `CONDITIONAL_NON_CONSTANT_BUFFS` instead of `STACK_BUFFS` resolves the dynamic
  value once and multiplies it by the stack count (Wandering Evenstar).
* **Dynamic-target and time-based windows** — the timeline can track *who* a buff
  belongs to (Thrilling Tales: the next character to take the field) and derive a
  stack count purely from `t` (Wandering Evenstar's 10s/12s cycle).

Weapon values are always read with the **caster's** refinement, so an R5 weapon
buffs an R1 ally with its R5 numbers.

## Stat vocabulary (what feeds what)

`build_initial_stats` composes the common pools explicitly (character + weapon +
artifact mains + substats) and then folds **every other** artifact-set stat
generically, so a set may grant any key it wants:

| Stat family | Standard | Stellar | Stellar reaction |
| --- | --- | --- | --- |
| `<element>_bonus`, `physical_bonus` | ✓ | ✗ | ✗ |
| `normal_bonus` / `charged_bonus` / `plunging_bonus` / `skill_bonus` / `burst_bonus` | ✓ | ✗ | ✗ |
| `stellar_bonus` | ✗ | ✓ | ✓ |
| `stellar_crit_rate` / `stellar_crit_dmg` | ✗ | ✓ | ✓ (per contributor) |
| `crit_rate` / `crit_dmg` | ✓ | ✓ | ✓ |
| `em` | — | ✓ (EM bonus) | ✓ |
| `<element>_shred` | ✓ (RES) | ✓ (RES) | ✓ (RES) |
| `jubilee_mult` | ✗ | ✓ | ✓ |
| `elevation_mult` | ✗ | ✓ | ✗ |
| `atk/hp/def_*`, `er` | ✓ | ✓ (MV base) | ✗ |

Rare/extra stats are **kept in the backend**: they live in the character's
`initial_stats`, they are written to the party `.json` (`snapshot_party` →
`initial_stats`), and they feed every snapshot and damage formula. They are
**not** printed on the character cards (a card only shows HP/ATK/DEF/EM,
CR or CV + CD, ER and the element DMG lines).

## Dormant passives (values kept in buffs.py `DORMANT`, triggers not modelled yet)

These have no timeline flag, so the engine can never apply them (and can never
advertise them). Re-enabling one means adding, together: (a) its timeline state
flag in `evaluate_timeline()` and (b) its `FLAG_TO_BUFFS` descriptor — and
removing it from `buffs.DORMANT`.

| Effect | Kind | Trigger that is still missing |
| --- | --- | --- |
| Diona C6 | Character | burst field -> Active EM / stellar_bonus |
| Odette C6 (self/party) | Character | elevation_mult on her stellar hits |

## Next verification targets

Weapons (phases 1-3), artifacts (phase 1), Mizuki C2/C6, Sucrose, Cryo Resonance
and Odette's Snow Swan's Dream are all implemented and covered by `smoke_test.py`.
Remaining work:

1. Odette's constellations (C1 recast / C2 stacks / C3) end-to-end verification.
2. Diona (C6 only): burst field -> Active EM / stellar_bonus.
3. Sucrose's burst absorption stays hardcoded to `Cryo` **by design** for the
   foreseeable future (no work planned).
4. Anastasya: Triumph's rule is **provisional on purpose**
   (`ANASTASYA_TRIUMPH_DELAY = 0.0` in `timeline.py`, i.e. it fires on her next
   swap-in, so every loop from the 2nd one). Replace that constant with the real
   rule once the content is released — nothing else in the engine needs to change.

## Anastasya round (rotation with Odette QE)

Anastasya is a full playable character (C0 only, five bows, "New Tsaritsa set"
added to her / Aether's / Odette's artifact lists).

Preset trials (both `end_mode=last_swap`, ~114.5s for 6 passes of a 19.082s loop):

| Trial key | Team | Rotation |
| --- | --- | --- |
| `Mizuki Sac Frag Pull out 6x rotations` | Mizuki / Aether / Odette / Faruzan | Aether EN1, Faruzan Q, Odette EE, Mizuki (Sac Frag), Aether CQ, Mizuki (pull out) |
| `Mizuki Sac Frag Pull out 6x rotations (Anastasya)` | Mizuki / Anastasya / Odette / Faruzan | **Anastasya EQ**, Faruzan Q, Mizuki (Sac Frag), **Odette QE**, Mizuki (pull out) |

Both trials share the same display name; the dropdown appends the team, and each
trial is only offered when the selected party matches that team **exactly**
(`Trial.required_party` + `Trial.matches_party`). The timed 30s trial was removed
from the preset pool: it survives only as `presets.TEST_TRIAL_30S` for the
automated checks and the calibration baseline.

Anastasya cannot split her skill and burst across the loop, so she casts them in one
visit (EQ, 2.851s). The loop only becomes legal because Odette uses her QE
(3.071s field): 2.851 + 1.410 + 1.750 + 3.071 + 10.0 = 19.082s >= Faruzan's 19s
burst cooldown. Odette's own Snow Swan's Dream stays up on her as a side effect.

New field sequence `faruzan_e` (`FaruzanESwap`): the actively called Pressurized
Collapse at the same 1.200s insertion time and the same 1.410s field time as her
burst swap. Not used by the presets; kept for future loops.

`DEFAULT_PARTY` still runs Aether, so **the baseline did not move**:
1064651.5 / 1211525.5 / 1273564.4 / 1476591.7 (C0/C1/C2/C6).
The Anastasya trial totals **4,904,232.3** average damage over its 6 passes.

**Triumph is on a provisional rule** (unreleased content): it is armed by her burst
cast and fires on her next swap-in, with `ANASTASYA_TRIUMPH_DELAY = 0.0` in
`timeline.py` as the minimum gap. That makes it proc on every loop from the second
one onwards — 5 procs in the 6-loop preset, at 19.082 / 38.164 / 57.246 / 76.328 /
95.410 s, all on her own swap-ins. Only the one constant needs editing once the
real rule is known.

Side fixes from these rounds:
* `Aether_jubilee` / `Odette_jubilee` (and Anastasya's jubilee + A4) are gated with
  `require_party`, so a character that is **not in the party** can no longer apply
  their passive. Before this, a party without Aether/Odette still received a
  jubilee computed from the recipient's own ATK.
* Editor catalogues are generated from `abilities.py`
  (`FIELD_SEQUENCE_REGISTRY` / `ABILITY_REGISTRY` / `field_sequences_for()` /
  `abilities_for()`), so the UI offers every field sequence and every ability of the
  characters that are actually in the party. Engine-injected procs (Triumph, the
  extra stellar beat) stay registered but are never offered by hand.
* Custom config export/import round-trips abilities through the registry
  (`ability_name` + `ability_character`) instead of a hardcoded name map.

## Calibration baseline (after the C2 / resonance / Odette round)

The standard 30s trial (DEFAULT_PARTY, Mizuki C0/C1/C2/C6):
1064651.5 / 1211525.5 / 1273564.4 / 1476591.7

C0/C1 are unchanged; C2/C6 are ~0.07% higher than the artifact-phase-1 numbers
because Mizuki's C2 PHEC bonus now scales with her FLAT EM (base + flat buffs)
instead of her initial EM. The jump from the weapon-phase-3 numbers is the
Instructor fix (on-field only, 8s).


## Save / load round (`build_io.py`, cards, results shortcut)

The UI used to export only *cooked* party data (`initial_stats` + `card_stats`), so a
saved file could not reproduce a build: the artifact inputs came back empty, the
artifact substats were not in the file at all, and because the uploader kept the
file alive the importer re-applied it on **every rerun**, silently reverting every
edit made after loading.

New `build_io.py` owns the file format (`SCHEMA_VERSION = "2.0"`). It imports no
Streamlit and takes any mutable mapping, so it is unit-testable:

| function | role |
| --- | --- |
| `collect_build_document(state)` | UI state -> JSON-ready document |
| `apply_build_document(doc, state, catalogue)` | document -> widget state (+ warnings) |
| `build_party_from_document(doc)` | document -> `my_party` (initial + card stats) |
| `assemble_party(slots)` | slot specs -> `my_party` (shared with the Confirm button) |
| `slot_stats_from_pieces(...)` | pieces -> stat pools (the old inline confirm-button math) |
| `load_trial_into_editor(trial, state)` | make any trial (preset or imported) editable |
| `parse_document` / `document_to_json` | JSON I/O, upgrades schema 1.0 files |

Document shape: `party` is a **list of slots** carrying the raw gear
(`pieces[Flower].main_stat`, `.rarity`, `.substats[{stat, value}]`), plus `enemy`,
`selected_trial`, `custom_field_sequences`, `custom_rotations` and `custom_trials`.
Each rotation embeds its full field-sequence definitions, so a file stands alone
while abilities are still re-resolved by name (numbers follow `abilities.py`).

Rules the importer keeps:

* It writes the **widget keys** (`char_*`, `level_*`, `const_*`, `weapon_*`, `ref_*`,
  `talents_*`, `art_set_*`, `std_*`, `main_*`, `rarity_*`/`rarity_locked_*`,
  `sub_type_*`, `sub_val_*`, `input_enemy_lv`, `input_<elem>_res`), not just the
  finished party, so every input shows the imported build and stays editable.
* Every value is validated against the UI's own tables (`BUILD_CATALOGUE`) and
  replaced with a warning when it no longer exists.
* Slots the file does not fill are reset, so loading a 2-character build over a
  4-character team cannot leave stale characters behind.
* `last_team_signature` / `last_enemy_signature` are re-seeded, so the "settings
  changed" guards do not immediately un-confirm the imported build.
* The uploaded bytes are hashed: a file is applied **once** and the panel then shows
  "loaded, edit freely — re-upload to reset". Removing the file re-arms the importer.

UI changes in the same round:

* Character cards moved from the bottom of the tab to directly under
  *"1. Team, Characters and Weapon Configuration"*. They are written into an empty
  `st.container()` placeholder created there and filled at the end of the tab, so
  they always reflect the party the Confirm button just built (no rerun needed).
  Card height dropped from a fixed `height=1000` box with a full-width image to a
  74px portrait + identity block + two-column stat grid.
* Enemy *Target Overview* card shrunk the same way (88px thumbnail + 2-column
  resistance grid).
* Completing a run now shows **"Trial simulation complete!"** with a
  `📊 View Simulation Results` button (persistent, via `trial_finished`) instead of a
  message pointing at a tab.
* Trial editor gained `⤵ Load selected trial into editor`: it copies the trial's
  rotations (and any non-preset sequences) into the custom pools, pre-fills the
  rotation queue and queues the trial name/description (`editor_prefill`, applied at
  the top of the tab because widget keys cannot be written after instantiation).
* Every history entry now stores `snapshot_build`, so the per-run export writes the
  same 2.0 document (older entries fall back to `legacy_build_document`).

Bugs found while verifying (both fixed):

1. The `validate_talents` splice had dropped its `return True, None, levels`, which
   made *Confirm party configuration* raise `TypeError: cannot unpack non-iterable
   NoneType`. Caught by running the app headless with `streamlit.testing.v1.AppTest`.
2. Importing a smaller party left the trailing slots holding the old characters
   (which also tripped the "character already picked in another slot" guard).

`smoke_test.py` now asserts the round trip: substats in the file, widget state
identical after re-apply, rebuilt `initial_stats` equal to `build_initial_stats`,
enemy + trial restored, unused slots cleared, schema 1.0 files still loading, and a
source-level check that the widget-key names in `streamlit_app.py` still match the
ones the importer writes. A headless AppTest run confirms the real load path
(`char_1=C1 / Sacrificial Fragments R4 / talents 6/10/10`, Sands `EM` + substats
`EM 40` / `Crit Rate% 3.9`, enemy `105 / 20% / 15%`, trailing slots
`Select Character`) with **no exceptions**.

Engine untouched: `DEFAULT_PARTY` baseline stays
1064651.5 / 1211525.5 / 1273564.4 / 1476591.7 and the Anastasya trial stays at
4,904,232.3.

