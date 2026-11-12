# Party Configuration Backlog

Tracks which characters, constellations, weapons, artifact sets and buffs have
been verified against in-game records. The `New test` calibration set is the
only fully verified configuration so far; everything else is a stub that still
needs a manual pass.

Legend: ✔ = verified (the `New test` set or an automated engine check) | ◻ = implemented
but not yet verified

## Characters

| Character | Element | Constellations offered | Status | Notes |
| --- | --- | --- | --- | --- |
| Mizuki | Anemo | C0-C6 | ✔ | C2 verified (shred + flat-EM PHEC bonus); C6 verified (party stellar crit + flat-EM crit) |
| Aether | Cryo | C4-C6 | ✔ | C6 verified (Frostglow / Aether C6 stellar) |
| Odette | Cryo | C0-C6 | ✔ | C1 extra stellar proc (+4.500 MV @0.010s) and 6-stack/2-per-second Marvelous; C2 shred + 7% ATK per stack; C4 SSD shares 50% with the OTHERS and adds a 0.990 MV stellar proc (3.5s trigger CD); C6 party elevation 0.25 / self 0.45 and she keeps her stacks off-field. C3/C5 only change talent levels (user-entered) |
| Anastasya | Cryo | C0-C6 | ✔ | Burst party stellar_bonus (**0.354 @ B13**, 20s — nerfed from 0.575), **Accolades** (12% crit DMG for the whole party, 20s, inclusive on the skill Cast hit; once sealed the OTHERS get her share → 16% and she gets 0 at C0; C1 → 48%/36% + 60%/240 ATK/EM, C4 → 68.8%/51.6% + 86%/344), A4 reaction-only jubilee (+0.15) + Lv2 vortices, Jubilee passive, **Triumph** (15s after the seal, on her next swap-in, hit delay 0.010), conditional extra stellar beat, **C2 Love** (0.60 stellar CD for 30s + permanent 0.05 elevation), **C6** (Love +0.10 elevation, C6 Triumph 2.5x MV on every ally swap-in, 15s per-character CD) |
| Faruzan | Anemo | C6 | ✔ | C6 CD buff + Anemo shred verified; her Skill Cast and the triggered Pressurized Collapse are separate abilities (collapse delay + 3.0s CD live in abilities.py) |
| Sucrose | Anemo | C0-C6 | ✔ | A1/A4/C6 verified (scope, magnitude and window) |
| Diona | Cryo | C6 | ✔ | Choice Treasures (20s state from either skill hit) → Icy Paw volley 0.270s after ANY Stellar Swirl (3.5s CD from the trigger); C6 burst-cast buff (+200 EM / +0.40 stellar) on the ACTIVE character for the whole burst (11.75s) |

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
| A Thousand Floating Dreams | Catalyst | ✔ (permanent stats from party composition: EM per same-element ally, elemental DMG bonus per different-element ally, +EM to the others) |
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
| Rainbow Serpent's Rain Bow | Bow | ✔ (off-field hit by the holder → 8s self ATK%, refreshed on every later one) |
| Jade Vista | Bow | ✔ (permanent stats from party composition: EM per same-element ally, ATK% per different-element ally) |

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

## Effects

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
| Odette Shadow | Character | Odette | always | ✔ |
| Odette SSD | Character | Odette | always | ✔ (shared at 50% with the OTHERS from C4) |
| Odette C2 Shred | Character | Odette | C2+ | ✔ |
| Sucrose A1 EM | Character | Sucrose | always | ✔ |
| Sucrose A4 EM | Character | Sucrose | always | ✔ |
| Sucrose C6 Cryo DMG | Character | Sucrose | C6 | ✔ |
| Anastasya Burst Stellar | Character | Anastasya | always | ✔ |
| Anastasya Accolades | Character | Anastasya | always | ✔ |
| Anastasya Sealed | Character | Anastasya | always | ✔ (also ON for the 8s linger after an unseal) |
| Anastasya Love | Character | Anastasya | C2+ | ✔ |
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
| Cryo Resonance CR | Team | Cryo Resonance | 2+ Cryo + pre-existing Cryo aura | ✔ |

## Verified buff semantics

| Effect | Invariant |
| --- | --- |
| Sucrose A1 | +50 EM, non-Anemo allies only, 8s, procs when she is the anemo contributor |
| Sucrose A4 | +20% of her FLAT EM, others only, 8s, refreshed by any skill/burst hit |
| Sucrose C6 | +20% cryo_bonus party-wide, window = [first burst hit, last burst hit] = 5.729s |
| Mizuki C6-1 | +10% stellar CR / +20% stellar CD party-wide while DDS is up (C6 only) |
| Mizuki C6-2 | +0.04% CR / +0.16% CD per FLAT EM above 500, capped 20% / 80% at 1000 |
| Flat EM basis | base + weapon + artifacts + flat buffs; % shares (VBTD2, Sucrose A4) never feed it |

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

## Dormant passives (values known, trigger not modelled yet)

These effects have no modelled trigger yet, so the engine never applies them.
Re-enabling one means adding its trigger to the timeline and its values to the
buff dispatch.

| Effect | Kind | Trigger that is still missing |
| --- | --- | --- |
| *(none)* | - | - |

(Diona C6 left this list in the Diona round, and Odette C6 (self/party) left it in the
Odette constellation round.)

## Next verification targets

Weapons (phases 1-3), artifacts (phase 1), Mizuki C2/C6, Sucrose, Cryo Resonance,
Odette's Snow Swan's Dream and her C1/C2/C4/C6 effects are all implemented and
checked. Remaining work:

1. Odette C3/C5 are talent-level-only by design (the user types the levels).
2. Sucrose's burst absorption stays hardcoded to `Cryo` **by design** for the
   foreseeable future (no work planned).
3. Anastasya C3/C5 are talent-level-only (user-entered); the seal → unseal rule is
   15s after the seal.

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

New field sequence `faruzan_e` (`FaruzanESwap`): her skill CAST at the same 1.200s
insertion time and the same 1.410s field time as her burst swap. The collapse is a
triggered ability and is not part of the sequence (see the triggered-hit round below).
Not used by the presets; kept for future loops.

`DEFAULT_PARTY` still runs Aether, so **the baseline did not move**:
1064651.5 / 1211525.5 / 1273564.4 / 1476591.7 (C0/C1/C2/C6).
The Anastasya trial totals ~~4,904,232.3~~ → **4,460,586.2** average damage over its
6 passes (see the triggered-hit round: -3.6 % from the nerf + the Faruzan CD rule).

* **Historical note (superseded):** at that time Triumph was armed by the burst cast
  with `ANASTASYA_TRIUMPH_DELAY = 0.0` as a provisional minimum gap, so it procced on
  every loop from the second one. The real rule is now implemented: the burst cast +
  swap-out **seals** her, and her next swap-in that is ≥
  `ANASTASYA_UNSEAL_DELAY` (15s) **after the seal** unseals her and fires Triumph at
  +0.010s. See "Anastasya Accolades & constellation round".

Side fixes from these rounds:
* Aether's, Odette's and Anastasya's jubilee passives (and Anastasya's A4) only apply
  while their owner is in the party. Before this, a party without them still received
  a jubilee computed from the recipient's own ATK.

## Odette constellation round

Her whole constellation set hangs off two timeline states:

* **`odette_shadow_state`** — the shadow, spawned by the skill OR burst cast and
  stipulated to live `ODETTE_SHADOW_WINDOW = 20s`. It drives the C2 shred, the C6
  elevation and (through `marvelous_stacks`) A1/C2's per-stack values.
* **`odette_ssd_state`** — Snow Swan's Dream, cast by the BURST only, its own 20s
  `ODETTE_SSD_WINDOW` (independent of the shadow).

Both are **inclusive on the cast hit** (unlike most windows in this engine): the first
hit already has the shred / elevation / SSD it started.

| Cons | Effect | Where |
| --- | --- | --- |
| C1 | `odette_c1_stellar_hit` (bare Hit, 450% ATK, +0.010s) right after the Recast's `Skill_Stellar`; Marvelous pool 4 -> 6 and transfer 1/s -> 2/s | `abilities.py`, `timeline.py` |
| C2 | party Cryo/Anemo shred 20% while the shadow is up; every Marvelous stack ALSO gives +7% ATK (`Odette C2 ATK` in `STACK_BUFFS`) | `buffs.py`, `stats_calc.py` |
| C3 / C5 | talent levels only (`+3` skill/burst) — the user types them, no code | UI |
| C4 | SSD is shared with the OTHERS at 50% (`"multiplier": 0.5`); ANY party `STELLAR_DMG` hit triggers `odette_c4_stellar_hit` (bare Hit, 99% ATK, +0.010s) with a 3.5s CD from the trigger | `buffs.py`, `stats_calc.py`, `timeline.py` |
| C6 | she keeps her 6 stacks off-field while the party still ramps at 2/s; the shadow grants +0.25 elevation to the OTHERS and +0.45 to her (0.25 party + 0.20 personal) | `buffs.py`, `stats_calc.py`, `timeline.py` |

**Side effect to be aware of:** the retimed `OdetteQE` (recast 2.250, swap-out 3.451)
moved her Cryo applications out of the 3s life of Anastasya's level-2 Stellar Vortex, so
the Anastasya preset no longer detonates one early. The A4 "spawn + 3 further swirls"
rule is verified independently of the rotation spacing.

## Anastasya Accolades & constellation round

**Accolades** (her A1) is one 20s window opened by her skill `Cast` hit and it is
**inclusive** on that hit. It is a party-wide 12% crit DMG buff with three states:

| State | Crit DMG | ATK% (Cryo recipients, C1+) | EM (non-Cryo recipients, C1+) |
| --- | --- | --- | --- |
| Unsealed — everyone | 0.12 | 0.15 | 60 |
| Shared (sealed) — OTHERS, C0 | 0.16 (her share ×4/3) | – | – |
| Shared (sealed) — Anastasya, C0 | 0 | – | – |
| Shared (sealed) — OTHERS, C1–C3 | 0.48 (12 × 3 × 4/3) | 0.60 | 240 |
| Shared (sealed) — Anastasya, C1–C3 | 0.36 (12 × 3) | 0.45 | 180 |
| Shared (sealed) — OTHERS, C4+ | 0.688 (12 × 4.3 × 4/3) | 0.86 | 344 |
| Shared (sealed) — Anastasya, C4+ | 0.516 (12 × 4.3) | 0.645 | 258 |

* **Seal**: she used her **burst** and then swapped out → the OTHERS get her share
  (×4/3) and from C1 on the value is 300% stronger (430% from C4). At C1+ she keeps a
  NON-shared copy; at C0 she loses hers entirely.
* **Unseal**: her next swap-in that is ≥ `ANASTASYA_UNSEAL_DELAY` (15s) after the
  **seal**; that swap-in also fires **Triumph**. The shared state then **lingers 8s**
  (`ANASTASYA_SHARED_LINGER`), which is why the re-cast that lands 0.6s later is still
  shared and she effectively never gets her share back in the preset loop.
* The two value sets are dispatched from two mutually exclusive flags
  (`anastasya_accolades_unsealed_state` / `..._shared_state`) so they can never
  double-count; `anastasya_accolades_state` is the display column.

**Love (C2)**: 30s party `stellar_crit_dmg = 0.60`, cast with the skill (refreshed by
each cast, independent of Accolades), plus a **permanent** `0.05 elevation_mult` with
no window (`always_on`, C2+). At C6 Love also gives another `0.10 elevation_mult`
(total 0.15) and unlocks the **C6 Triumph**: every OTHER character's swap-in while
Love is up fires `anastasya_c6_triumph` (2.5× the talent-scaled Triumph MV —
835 vs 334 base — credited to her, 15s per-character CD, so up to 2 per Love window).

## Calibration baseline (after the Anastasya Accolades round)

The standard 30s trial (DEFAULT_PARTY, Mizuki C0/C1/C2/C6):
1087457.8 / 1212982.7 / 1275225.0 / 1476757.9  (unchanged — that party has no Anastasya)

Anastasya 6x preset, per constellation:
**4,350,677.6 (C0) / 6,269,037.8 (C1) / 7,221,345.2 (C2) / 8,675,730.1 (C4) /
11,415,775.5 (C6)** — C3 = C2 and C5 = C4, because those constellations only change
talent levels (user-entered).

At C0 the Accolades rewrite is a tiny gain over the old flat A1 (+1,049): the cast hit is
inclusive and she keeps 12% for the first, still-unsealed window, while the OTHERS keep
their 16%. From C1 the OTHERS jump 16% → 48% crit DMG (+60% ATK / 240 EM) for the shared
part of every loop — that is the +44% at C1. C2 adds Love (0.60 stellar CD + 0.05
elevation), C4 replaces the 300% tier with 430%, and C6 adds the 0.10 elevation plus the
C6 Triumph procs (18 in the 6-loop preset).


## RV / KQM crit model + trigger-ordering round

Three bugs, all found with the new `Test Aether` preset (Aether on the **100% RV**
standard: CR 30.0%, CD 392.5%, CV 4.525, expected crit_mult 3.525).

### 1. The RV flag never reached the engine

`build_io.assemble_party` stored the UI label in `standard_mode`, but
`timeline._calculate_all_hits_damage` (and therefore every `damage_calc` branch)
looked for a key called `rv_mode`, which **nothing ever wrote**. Every hit fell
back to `1 + CR*CD`, so an RV build showed the manual number: 2.1776 instead of
3.5252 (CV 4.5252 → `cv - 1`), while the card correctly showed CV 452.5
(`compute_card_stats` reads `standard_mode`).

Fix: `stats_calc.is_rv_mode(char_data)` is now the single place that maps the two,
`assemble_party` writes `rv_mode` next to `standard_mode`, and the helpers let old
or hand-written entries (only the label present) resolve the same way.

### 2. Reactions ignored the RV model

`calculate_stellar_reaction_damage` built its 2^n crit scenarios with `1 + CR*CD`
and only used the CV multiplier for the quill, so a swirl contributed by an RV
character would still be stochastic. Each RV contributor now collapses to a single
deterministic outcome (`prob = 1`, value = `non_crit * cv_mult`), and the
`non_crit` / `crit_damage` / `average_damage` aggregates agree with the standard
and stellar paths. `smoke_test._run_rv_mode_check()` asserts that an all-RV run
has `average == non_crit == crit_damage` on every swirl, and that a Manual run
still has variance.

### 3. Every timed buff buffed the hit that procced it

Cryo Resonance (reported): the aura gauge was read **after** `apply_element`, so
the hit that applied Cryo from a clean enemy got the 15% CR. The same
"arm-then-read" mistake existed in every other window that is armed by the event
that reads it (`HotF` was the only one already following the correct rule):
Cryo Resonance, VV, Instructor, Gilded Dreams, Noblesse, Tenacity, A Day Carved
From Rising Winds, Scarlet Proof, New Tsaritsa stacks, Faruzan's buff,
Mizuki's A4 + C1 debuff, Sucrose A1/A4/C6, The Widsith, Sunny Morning Sleep-In,
Silverdawn, Odette's burst + C2 and Anastasya's burst + A1.

All of them now read their state from the PRE-event value and arm afterwards
(damage resolves first, effects land second). Cryo Resonance additionally reads
the aura after decay is advanced to the hit's timestamp but before the elemental
application; the `Aura (Cryo)` column still shows the gauge the enemy is left
with.

Numeric impact (DEFAULT_PARTY): the 30s trial **1,273,564.4 → 1,266,300.5**
(-0.570%), the 6-loop preset **5,411,371.4 → 5,386,893.6** (-0.452%), the
Anastasya preset **4,904,232.3 → 4,948,837.2** (+0.910% — her per-burst collapse
insertions shift by one hit). Per-hit differences are exactly the triggering hits
(Aether's aura-applying skill -218, Faruzan's burst cast -1,657, Odette's cast
-651, ...). Mizuki's C1 mini-nuke moves with the swirl that empowers it, because
`c1_debuff_state` is also read pre-application now.

### `Test Aether` preset

`required_party` was `MIZUKI_SACFRAG_TEAM` although the rotation only plays
Aether, which tripped the preset-gating check; it is now `["Aether"]`.

### Decisions recorded

* RV mode is flagged **and** derived: `rv_mode` (bool) is written by
  `assemble_party` so a party dict is self-describing, while `is_rv_mode()` falls
  back to `standard_mode != "Manual"` for entries that only carry the label.
  The rejected alternatives were (a) deriving only, which leaves the engine
  re-parsing a UI string everywhere, and (b) writing `rv_mode` only, which
  silently turns the standard off for every older file/preset.
* The trigger-ordering change is applied to **all** windows on the assumption
  that they behave the same way in game (the user's call). Per-effect in-game
  verification is still pending — see below.

### Aura column = pre-hit state

The Aura column used to show the gauge *after* the hit applied its element, which made
it contradict `cryo_resonance_state` on exactly the rows where the aura was created.
It now reports the state the hit was resolved against (`timeline` stores it as
`cryo_aura`, the post-hit gauge is kept as `cryo_aura_after`), and the column order is
`… Action | Aura | Elemental App | Reaction …` (console table and UI), so a row reads
"what the enemy had → what this hit added". The applying hit therefore shows the old
value and the *next* row shows the new one:

```
0.601 Aether Skill_Initial  Aura 0.00U  App 1U  CV 422.5  crit_mult 3.225  reso OFF
1.200 Aether N1_Hit         Aura 0.75U  App  -  CV 452.5  crit_mult 3.525  reso ON
```

`smoke_test.py` asserts the pair (`first_aura == "0.00U"`, `first_aura_after != 0`,
`later_aura != 0`, resonance OFF then ON).

### Open items

1. Verify in game each of the windows that now read pre-event (VV, Instructor,
   Gilded, Noblesse, Tenacity, Rising Winds, Scarlet, Tsaritsa stack timing,
   Sucrose A1/A4/C6, Widsith, Sunny, Silverdawn, Odette burst/C2, Anastasya
   burst/A1, Faruzan buff, Mizuki A4/C1). The rule is uniform, the per-effect
   confirmation is not.
2. Stack counters (Silver Light, New Bough, Elegy / Breezeborne / Starsealed
   sigils) intentionally still count the triggering hit — confirm that matches
   the in-game "gain on hit" wording.
3. Mizuki's C1 mini-nuke now fires only on swirls that happen while the debuff is
   already up (it used to fire on the swirl that applied it). Needs a game check.

## Mizuki hit-register round (new pull-out lengths + burst)

Pure hit registers: no new buffs, flags or passives. The workflow is now documented
in `text/How_to_add_hits.txt` so the next one is mechanical.

### What was added

| object | kind | field | hits |
| --- | --- | --- | --- |
| `mizuki_pullout_13` | Ability ("Mizuki Skill 13 Ticks") | 15 s CD | Cast + Ticks 1-13 |
| `mizuki_pullout_9` | Ability ("Mizuki Skill 9 Ticks") | 15 s CD | Cast + Ticks 1-9 |
| `mizuki_pullout_5` | Ability ("Mizuki Skill 5 Ticks") | 15 s CD | Cast + Ticks 1-5 |
| `mizuki_skill_2` | Ability ("Mizuki Skill 2 Ticks") | 0 s (Sac Frag proc) | Cast + Ticks 1-2 |
| `mizuki_burst` | Ability ("Mizuki Burst") | 15 s CD | `Burst_Cast` + `Shock 1-8` |
| `mizuki_pullout_1_nuke` | FieldSequence | 1.750 s | the 2-tick skill |
| `mizuki_pullout_2_nukes` | FieldSequence | 4.101 s | the 5-tick skill |
| `mizuki_pullout_3_nukes` | FieldSequence | 7.100 s | the 9-tick skill |
| `mizuki_pullout_4_nukes` | FieldSequence | 10.000 s | the 13-tick skill |
| `mizuki_burst_field` | FieldSequence | 12.800 s | her burst (last shock at 12.601 s) |

`presets.STANDARD_FIELD_SEQUENCES` now points at those objects instead of building
duplicate shells, so `"Mizuki E (Sac Frag Proc)"` / `"Mizuki E (Pullout)"` keep
working and `"Mizuki E (2 nukes)"`, `"Mizuki E (3 nukes)"`, `"Mizuki Q"` were added.

### Known limitation (documented in the guide)

Cooldowns are keyed on `(character, ability name)`, so the four skill variants of the
same in-game skill do not share one cooldown: alternating them inside 15 s is
allowed by the engine. A `cooldown_key` field on `Ability` would fix it; it was left
out because it changes how rotations are validated and the current presets rely on
the Sac-Frag proc variant having `cooldown = 0`.


---

## Triggered-hit round: Diona, Faruzan's trigger CD and the standardized delay

### Audit table of every triggered hit

| Triggered hit | Definition (abilities.py) | Triggered by | Delay | Cooldown |
| --- | --- | --- | --- | --- |
| Mizuki VBTD nuke | `mizuki_nuke_hit` (bare Hit, 1000% EM) | her next skill tick while DDS is up (armed by her own swirl, 2.5s prep CD) | **0.500** | - |
| Mizuki C1 mini nuke | `mizuki_c1_mini_nuke_hit` (bare Hit, 400% EM) | a Stellar Swirl while her C1 shred is up | **0.000** | - |
| Faruzan Pressurized Collapse | `faruzan_pressurized_collapse` (Ability, 108% skill) | her burst cast hit, or ANY hit while her C6 buff window is up | **0.720** | 3.0s **from the trigger** |
| Diona Icy Paws | `diona_choice_treasures` (Ability, 3 x 41.92% skill) | ANY character's Stellar Swirl while her Choice Treasures state (20s) is up | **0.270 / 0.360 / 0.360** | 3.5s **from the trigger** |
| Anastasya extra stellar | `anastasya_extra_stellar` (Ability, 16.8% burst) | her Palestar Crown Stellar beat while her burst window is up | **0.010** | - |
| Anastasya Triumph | `anastasya_triumph` (Ability, 334% burst) | her swap-in (trigger = SWAP_IN), armed by the SEAL (burst + swap-out) | **0.010**, on the swap-in that is ≥ `ANASTASYA_UNSEAL_DELAY` (15s) after the seal | once per seal |
| Anastasya C6 Triumph | `anastasya_c6_triumph` (Ability, 2.5x Triumph's talent-scaled MV) | ANY other character's swap-in while Love is up (C6) | **0.010** | 15s **per character**, from the trigger |
| Odette C1 extra stellar | `odette_c1_stellar_hit` (bare Hit, 450% ATK) | her Recast's `Skill_Stellar` hit (C1+) | **0.010** | - (once per recast) |
| Odette C4 extra stellar | `odette_c4_stellar_hit` (bare Hit, 99% ATK) | ANY party `STELLAR_DMG` hit while Snow Swan's Dream is up (C4+) | **0.010** | 3.5s **from the trigger** (`ODETTE_C4_PROC_CD`) |

Triggered abilities are listed in `abilities.ENGINE_INTERNAL_ABILITIES`, so they stay in
`ABILITY_REGISTRY` but are never offered by the editor and never appear in a
`FieldSequence` (a smoke check enforces that). An ability that can happen both ways gets
two entries, like Faruzan's `Skill Cast` (active) and `Pressurized Collapse` (triggered).

### Diona (new)

* Choice Treasures: her tap OR hold skill **hit** opens a 20s state (refreshed by either).
  While it is up, a Stellar Swirl from ANY character fires `diona_choice_treasures`
  (3 Cryo hits, only tick 1 applies `1U`), 0.270s after the trigger, 3.5s CD from the
  trigger. The volley rows are inserted in chronological order (they are not the first
  injected rows of that event).
* C6: her burst cast hit gives the ACTIVE character `em: 200` + `stellar_bonus: 0.40`
  (`buffs.CONDITIONAL_CONSTANT_BUFFS["Diona C6"]`, flag `diona_c6_state`,
  `FLAG_TO_BUFFS` descriptor with `target: "Active"` and `min_constellation: 6`).
  Window = **11.75s from the cast hit** (`DIONA_C6_WINDOW`), i.e. the whole burst: the
  last burst tick at +11.73 is still buffed. The cast hit itself is INCLUDED - the one
  deliberate exception to the "read pre-arm" rule: arm first, resolve the flag after.
* `diona_hEQ` swap-out time 3.071 -> **3.100**: her burst is cast 0.029s before leaving,
  so the cast hit is still ON FIELD (at 3.071 = swap-out it resolved with
  `active_character = None`, which dropped her own C6 buff and Faruzan's quill on it).
* `Diona C6`'s permanent `hp_percent: 0.25` stays unconditional (the UI only offers C6;
  gating it would move every Diona number).

### Damage effect of this round

| Trial | Before | After | Why |
| --- | --- | --- | --- |
| 30s fixed trial (DEFAULT_PARTY) | 1,266,300.5 | **1,274,954.5** | Faruzan CD from the trigger |
| Aether 6x preset | 5,386,893.6 | **5,594,119.9** | the same rule, +3 collapses over the 6 loops |
| Anastasya 6x preset | 4,628,073.7 | **4,460,586.2** | extra collapses burn the Cryo aura before the swirls (swirls 93 -> 92) |

Proof the refactor itself is neutral: with `FARUZAN_COLLAPSE_CD` temporarily set to
3.72 (the old "CD from the hit" rule) the current engine reproduces the old Anastasya
total **exactly** (4,628,073.7), so every remaining difference comes from the CD rule.

