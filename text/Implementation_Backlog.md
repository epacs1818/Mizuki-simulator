# Party Configuration Backlog

Tracks which characters, constellations, weapons, artifact sets and buffs have
been verified against in-game records. The `New test` calibration set is the
only fully verified configuration so far; everything else is a stub that still
needs a manual pass.

Legend: ✔ = verified (the `New test` set or an automated engine check) | ◻ = implemented
but not yet verified

## 2026-11 revision

* Ability calls are hidden `CAST` events (`event_type="CAST"`). Every "on cast" effect
  arms on the marker, so its first hit is included; hit-triggered effects keep the
  pre-arm read. Sucrose A1/A4/C6 remain hit-triggered.
* Element crit is data: `anemo_crit_dmg` (Faruzan C6) and `cryo_crit_rate`
  (New Tsaritsa set), applied in `damage_calc` to standard and stellar damage.
* Stellar reaction shares use each contributor's full final stats; effective damage
  ignores RES; reaction multiplier audit columns stay null.
* Quills: Mizuki C1's quill is shown in `Quills`; reactions add it post-share with the
  owner's elevation. Faruzan/VBTD quills remain.
* Columns removed: Mizuki C1 Debuff, Odette C2 Shred (inside Shadow), Anastasya A4
  Jubilee, Anastasya Triumph; header help added to all registry entries.
* Odette Marvelous: full at cast; decay anchors on the first swap-out, re-entry does not
  refill; a new cast does.
* Aether charged: +2 Frostglow on cast (N1 NORMAL, C1/C2 CHARGED); cap 8, consumed by
  the burst.
* Constellation stat gates moved into `FLAG_TO_BUFFS` (Aether C2/C6, Faruzan C6,
  Mizuki C6).

## Characters

| Character | Element | Constellations offered | Status | Notes |
| --- | --- | --- | --- | --- |
| Mizuki | Anemo | C0-C6 | ✔ | C2 verified (shred + flat-EM PHEC bonus); C6 verified (party stellar crit + flat-EM crit). Her skill is ONE ability per in-game FORM (`[Pullout]` / `[Standard]`), cut by her own swap-out - the field-sequence window decides the tick count |
| Aether | Cryo | C4-C6 | ✔ | C6 verified (Frostglow / Aether C6 stellar) |
| Odette | Cryo | C0-C6 | ✔ | C1 extra stellar proc (+4.500 MV @0.010s) and 6-stack/2-per-second Marvelous; C2 shred + 7% ATK per stack; C4 SSD shares 50% with the OTHERS and adds a 0.990 MV stellar proc (3.5s trigger CD); C6 party elevation 0.25 / self 0.45 and she keeps her stacks off-field. C3/C5 only change talent levels (user-entered) |
| Anastasya | Cryo | C0-C6 | ✔ | Burst party stellar_bonus (**0.354 @ B13**, 20s — nerfed from 0.575), **Accolades** (12% crit DMG for the whole party, 20s, inclusive on the skill cast; once sealed the OTHERS get her share → 16% and she gets 0 at C0; C1 → 48%/36% + 60%/240 ATK/EM, C4 → 68.8%/51.6% + 86%/344), A4 reaction-only jubilee (+0.10) + Lv2 vortices, Jubilee passive, **Triumph** (15s after the seal, on her next swap-in, hit delay 0.010), conditional extra stellar beat, **C2 Love** (0.50 stellar CD for 30s + permanent 0.05 elevation), **C6** (Love +0.10 elevation, C6 Triumph 2.0x MV on every ally swap-in, 15s per-character CD) |
| Faruzan | Anemo | C6 | ✔ | C6 CD buff + Anemo shred verified; her Skill Cast and the triggered Pressurized Collapse are separate abilities (collapse delay + 3.0s CD live in abilities.py) |
| Sucrose | Anemo | C0-C6 | ✔ | A1/A4/C6 verified (scope, magnitude and window) |
| Diona | Cryo | C6 | ✔ | Choice Treasures (20s state from either skill hit) → Icy Paw volley 0.270s after ANY Stellar Swirl (3.5s CD from the trigger); C6 burst-cast buff (+200 EM / +0.40 stellar) on the ACTIVE character for the whole burst (11.75s) |

## Weapons

| Weapon | Type | Status |
| --- | --- | --- |
| Sacrificial Fragments | Catalyst | ✔ (permanent EM + guaranteed skill-CD reset proc, ICD 30/26/22/19/16, own audit row) |
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
| Starsealed Edict | Catalyst | ✔ (permanent CD% + 20s skill-cast EM window + swirl stacks, cap 3) |
| Whitelake Frostfeather | Sword | ✔ (3 stacks × 8s, stellar crit DMG at 3) |
| Finale Of The Deep | Sword | ✔ (15s ATK% window, 10s CD) |
| Azurelight | Sword | ✔ (permanent ATK% only) |
| Aquila Favonia | Sword | ✔ (permanent ATK% only) |
| Sacrificial Bow | Bow | ✔ (base ATK + ER + the same guaranteed skill-CD reset passive) |
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
| Mizuki A4 | Character | Mizuki | always | ✔ |
| Mizuki VBTD Quill | Character | Mizuki | always | ✔ |
| Mizuki C1 Debuff | Character | Mizuki | C1+ | ✔ |
| Faruzan C6 Buff | Character | Faruzan | C6 | ✔ |
| Faruzan C6 Anemo Shred | Character | Faruzan | C6 | ✔ |
| Aether C2 EM | Character | Aether | C2+ | ✔ |
| Aether C2 EM (Amp) | Character | Aether | C2+ | ✔ |
| Aether Frostglow | Character | Aether | always | ✔ |
| Aether C6 Stellar | Character | Aether | C6 | ✔ |
| Odette Marvelous | Character | Odette | always | ✔ |
| Odette Shadow | Character | Odette | always | ✔ |
| Odette SSD | Character | Odette | always | ✔ (shared at 50% with the OTHERS from C4) |
| Odette C2 (inside Shadow) | Character | Odette | C2+ | ✔ |
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
| `elevation_mult` | ✗ | ✓ | ✓ (per contributor) |
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

Both are **inclusive on the cast** (the hidden CAST marker runs before the first hit):
the cast's first hit already has the shred / elevation / SSD it started.

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

**Love (C2)**: 30s party `stellar_crit_dmg = 0.50`, cast with the skill (refreshed by
each cast, independent of Accolades), plus a **permanent** `0.05 elevation_mult` with
no window (`always_on`, C2+). At C6 Love also gives another `0.10 elevation_mult`
(total 0.15) and unlocks the **C6 Triumph**: every OTHER character's swap-in while
Love is up fires `anastasya_c6_triumph` (2.0× the talent-scaled Triumph MV —
668 vs 334 base — credited to her, 15s per-character CD, so up to 2 per Love window).
The elevation is the same key Odette's C6 uses, so it applies to stellar DMG **and**
to each contributor's share of a stellar reaction (swirl / vortex explosion).

## Calibration baseline (after the Anastasya nerf round)

Nerfs in this round: A4 reaction jubilee 0.15 → 0.10, C2 Love stellar CD 0.60 →
0.50, C6 Triumph 2.5× → 2.0× the talent-scaled Triumph MV (835 → 668 base) and her
burst cooldown 15.0 → 17.1s. The ascension stat also moved from crit rate to crit DMG
(0.146/0.194/0.242 CR → 0.692/0.788/0.884 CD).

The 17.1s burst cooldown made two Sucrose presets illegal: they cast her EQ twice per
loop, ~15.9s apart. Both standards now split her kit across three visits built from the
existing sequences - `Anastasya E`, `Anastasya Q` (burst only), `Anastasya E` - so the
burst rides its own visit. A burst on either skill visit does not work: her tap shares
the 15s floor and the two Odette/Aether windows are ~17.2s / ~16.6s, so a burst there
either breaks the other burst's 15s cooldown or needs ~1.6s of idle field time. This
layout keeps Accolades refreshed twice per loop, Odette's two QEs, Aether's two ECQs,
Sucrose's QN1-into-pull-out order, and adds no new field sequence.

The standard 30s trial (DEFAULT_PARTY, Mizuki C0/C1/C2/C6):
1087457.8 / 1212982.7 / 1275225.0 / 1476757.9  (unchanged — that party has no Anastasya)

Anastasya 6x preset, per constellation:
**4,295,223.8 (C0) / 6,148,253.3 (C1) / 6,893,371.7 (C2) / 8,271,155.7 (C4) /
10,296,137.5 (C6)** — C3 = C2 and C5 = C4, because those constellations only change
talent levels (user-entered).

At C0 the Accolades rewrite is a tiny gain over the old flat A1 (+1,049): the cast hit is
inclusive and she keeps 12% for the first, still-unsealed window, while the OTHERS keep
their 16%. From C1 the OTHERS jump 16% → 48% crit DMG (+60% ATK / 240 EM) for the shared
part of every loop — that is the +44% at C1. C2 adds Love (0.50 stellar CD + 0.05
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

Retired in the Sucrose preset pass: the trial is no longer offered in the preset
list. The smoke test now builds the same one-shot Aether rotation locally, and
the new one-pass Sucrose trials replaced it for real rotations.

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

### Resolved: cooldowns are keyed per cooldown FAMILY

Cooldowns used to be keyed on `(character, ability name)`, so the two forms of one
in-game skill did not share one cooldown: alternating them inside 15 s was allowed.
`Ability.cooldown_family` (`models.py`) now names the in-game button an ability
belongs to, and the engine keys on `Ability.cooldown_key` = `(character, family)`:

| Ability objects | `cooldown_family` |
| --- | --- |
| `mizuki_skill_pullout`, `mizuki_skill_standard` | `skill` |
| `diona_skill_tap`, `diona_skill_hold` | `skill` |
| `odette_cast` / `odette_recast` | `skill_cast` / `skill_recast` (deliberately split) |
| normal / charged / burst / triggered abilities | `normal`, `charged`, `burst`, one family each |

The family is scoped per character, so Mizuki's and Diona's `skill` families never
collide. A cast of either form starts ONE cooldown, and the cooldown that applies is
the one the PREVIOUS cast started (Diona tap 6s -> hold is legal after 6s; hold
14.25s -> tap waits 14.25s) - the same rule `_skill_cd_reset_plan()` and the editor
pre-flight already used. Odette's cast and recast stay independent because her
presets chain them 0.51 s apart.

*Superseded:* the four skill variants were merged into the two skill forms in the
"Mizuki skill forms and the swap-out interrupt" round below.


---

## Triggered-hit round: Diona, Faruzan's trigger CD and the standardized delay

### Audit table of every triggered hit

| Triggered hit | Definition (abilities.py) | Triggered by | Delay | Cooldown |
| --- | --- | --- | --- | --- |
| Mizuki VBTD nuke | `mizuki_nuke_hit` (bare Hit, 1000% EM) | her next skill tick while DDS is up (armed by her own swirl, 2.5s prep CD) | **0.500** | - |
| Mizuki C1 mini nuke | `mizuki_c1_mini_nuke_hit` (bare Hit, 400% EM) | a Stellar Swirl while her C1 shred is up | **0.000** | - |
| Faruzan Pressurized Collapse | `faruzan_pressurized_collapse` (Ability, 108% skill) | her burst cast, or ANY hit while her C6 buff window is up | **0.720** | 3.0s **from the trigger** |
| Diona Icy Paws | `diona_choice_treasures` (Ability, 3 x 41.92% skill) | ANY character's Stellar Swirl while her Choice Treasures state (20s) is up | **0.270 / 0.360 / 0.360** | 3.5s **from the trigger** |
| Anastasya extra stellar | `anastasya_extra_stellar` (Ability, 16.8% burst) | her Palestar Crown Stellar beat while her burst window is up | **0.010** | - |
| Anastasya Triumph | `anastasya_triumph` (Ability, 334% burst) | her swap-in (trigger = SWAP_IN), armed by the SEAL (burst + swap-out) | **0.010**, on the swap-in that is ≥ `ANASTASYA_UNSEAL_DELAY` (15s) after the seal | once per seal |
| Anastasya C6 Triumph | `anastasya_c6_triumph` (Ability, 2.0x Triumph's talent-scaled MV) | ANY other character's swap-in while Love is up (C6) | **0.010** | 15s **per character**, from the trigger |
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
* C6: her burst cast gives the ACTIVE character `em: 200` + `stellar_bonus: 0.40`
  (`buffs.CONDITIONAL_CONSTANT_BUFFS["Diona C6"]`, flag `diona_c6_state`,
  `FLAG_TO_BUFFS` descriptor with `target: "Active"` and `min_constellation: 6`).
  Window = **11.75s from the cast** (`DIONA_C6_WINDOW`), i.e. the whole burst: the
  last burst tick at +11.73 is still buffed. The burst's first hit is INCLUDED - the one
  deliberate exception to the "read pre-arm" rule: arm first, resolve the flag after.
* `diona_hEQ` swap-out time 3.071 -> **3.100**: her burst is cast 0.029s before leaving,
  so the cast (and its first hit) is still on field (at 3.071 = swap-out it resolved with
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


## Sacrificial weapons round (guaranteed skill-CD reset)

`Sacrificial Fragments` and `Sacrificial Bow` no longer rely on the old "give the
skill talent CD 0" workaround: the passive is modelled.

* **Model**: SKILL damage (only standard damage carries attack types, so the type
  alone is the test) dealt by the **on-field holder** ends that holder's elemental
  skill cooldown. The proc is **guaranteed** - the app runs no RNG, and a rotation
  that depends on the roll is only worth authoring when it procs - and its own
  internal cooldown is **30 / 26 / 22 / 19 / 16 s for R1-R5**, measured **from the
  proc**.
* **Data**: `weapons.WEAPON_STATS[...]["skill_cd_reset"]` (`{"icd": [...],
  "label": ...}`) read through `weapons.get_skill_cd_reset(weapon, refinement)`. The
  block is nested and non-numeric, so `build_initial_stats` never folds it into a
  snapshot (asserted in the smoke test).
* **Trigger and row**: `timeline._skill_cd_reset_plan()` walks the scheduled events
  *before* the evaluator mutates them. It (a) re-checks the holder's casts - their
  eager check in `add_field_sequence` is deferred, because a proc can legally end the
  CD between two casts - and (b) places one **`WEAPON_PROC`** row per proc right after
  the hit that caused it: `Action` = "Sac Frag proc" / "Sac Bow proc", `Owner` and
  `Active` = the holder, no damage fields and no buff column (the passive changes
  cooldowns, not stats).
* **Every skill hit counts, not only the first hit**: a long pull-out that keeps
  ticking past the weapon's ICD consumes the proc on a late tick. The next rotation's
  cast then has no reset available and the engine reports the cooldown clash - the
  "the tail stole my Sac proc" error. The smoke test pins it (procs at 0.301 and
  16.869 -> the 21.5s cast is legal, the 23.0s cast is refused until 36.5s).
* **Reset scope**: a proc ends every `skill_talent` ability of the holder (both of
  Mizuki's skill forms, Sucrose's Skill, Diona tap/hold, ...). Cooldowns are keyed
  on `(character, cooldown_family)`, so the two Mizuki forms and Diona's tap/hold
  share one cooldown and alternating them inside it is refused - see the
  "cooldowns are keyed per cooldown FAMILY" section above.
* **Editor pre-flight**: `ui/editor/validate.cooldown_issues()` accepts the party's
  gear (`trial_issues()` takes the party dict or an id list) and treats a skill cast
  as a guaranteed proc at its own cast time, so the warning list cannot contradict
  the engine. The engine still re-checks with per-tick precision.
* **Not modelled**: engine-injected skill hits (Faruzan's own Pressurized Collapse
  after her burst) are not proc sources. Diona's Icy Paws are off-field and could not
  proc anyway.
* **Presets**: no stat changes, so the pinned totals did not move (30s trial C2
  `1,275,225.0`, Anastasya 6x `4,295,223.8`). The 30s trial now also shows the two
  procs at 5.312s and 25.014s. Once the real skill cooldowns are typed in, the
  Sucrose rounds (`sucrose_standard` family: three Sucrose skill casts per ~33.5s
  loop) and any R1-R3 Sac rotation will start failing **by design**; Mizuki's
  catalogue is R4/R5 only, which keeps the 6x Mizuki loop legal.

## Ability charges round (Sucrose stocks 2 skill casts)

Sucrose's skill holds **two** charges; every other ability still holds one. A cast
is no longer only "is the cooldown over?" - it **spends a charge**:

* **Data**: `Ability.ability_max_charges` (default 1). Charges belong to the
  in-game button, so every ability in one `cooldown_family` must declare the same
  capacity (a smoke check enforces it). `sucrose_skill` is the only 2-charge
  ability, and she starts every trial with both charges full.
* **Model** (`models.ChargePool`, shared by the engine and the editor pre-flight):
  ONE recharge timer per family. Spending from a FULL pool starts the timer;
  further spends do not push it back. A charge returns every `cooldown` seconds
  (14.25 for Sucrose), so casts at 1.0s and 2.0s leave the next cast legal at
  **15.25s**, not 17.25s. Charges are clamped to [0, capacity]; `ready_at` is
  None exactly while the pool is full.
* **Sacrificial weapons**: a proc *grants one charge* (`ChargePool.grant`)
  instead of "ending the cooldown". For a 1-charge skill that is the same thing
  ("castable again"), which is why the pinned Sacrificial numbers did not move.
* **Engine**: both passes drive the same pool - `add_field_sequence` for everyone
  except a Sac holder, `_skill_cd_reset_plan` for the holder (its procs are only
  known there). Hit events carry `cast_max_charges` next to `cast_family`, and a
  triggered hit never inherits them.
* **Editor pre-flight**: `validate.cooldown_issues()` keeps one `ChargePool` per
  (character, family) and reports the same clash times, so a stocked skill cannot
  produce a warning the engine disagrees with.
* **Cooldown data convention** (also commented in `abilities.py`): a 15s skill is
  entered as **14.25** because the 2-Anemo party buff (-5% CD) is hard-coded until
  the app has a party-aware CD reducer. Aether's charged ability keeps its full
  **15.0s** on purpose.
* **Presets**: Sucrose's first two skill casts per trial are free, so the
  `sucrose_mizuki_alternating_3_and_4_nukes` family no longer fails on its second
  cast (the 16.50s charge covers its third cast at 22.77s). It now fails at
  ~56.3s instead: three casts per ~33.5s loop against 2 charges per 28.5s is a
  real deficit once the buffer is gone, so the error is worth keeping.

## Mizuki skill forms and the swap-out interrupt

Her skill used to be authored as four separate abilities (`[2/5/9/13 Ticks]`) because the
engine could not interrupt it. In game it is ONE skill: the field-sequence window is what
decides how many ticks land.

* **Two hand-written forms**: `mizuki_skill_pullout` ("Mizuki Skill [Pullout]", the form
  every preset plays) and `mizuki_skill_standard` ("Mizuki Skill [Standard]", a catalogue
  stand-in with the same hits and the pull-out offset removed). Both set
  `Ability.interrupt_on_swap_out`; her burst does not.
* **Interrupt rule** (`models.interrupted_hit_count`, applied by
  `timeline.add_field_sequence`): every hit at or before the swap-out lands, the FIRST hit
  after it still lands (that tick is already in the air, so it resolves off field) and
  every later hit is never scheduled. The in-air tick needs no special casing: after the
  swap-out `active_character` is the next character (or None), so DDS, Faruzan's quill and
  every `Active`-scoped buff are already off for it.
* **Windows replace the variants** (same `swap_out_time` as before):

  | sequence | window | hits kept | last hit | in-air tick |
  | --- | --- | --- | --- | --- |
  | Skill Pullout 1 Nuke | 1.750 | 3 | 1.920 | Tick2 |
  | Skill Pullout 2 Nukes | 4.101 | 6 | 4.291 | Tick5 |
  | Skill Pullout 3 Nukes | 7.100 | 10 | 7.290 | Tick9 |
  | Skill Pullout 4 Nukes | 10.000 | 14 | 10.170 | Tick13 |
  | Burst Pullout 4 Nukes | 9.300 | 13 | 9.480 | Tick12 |

  The first four are hit-for-hit identical to the old `[2]/[5]/[9]/[13] Ticks` abilities.
  The burst window loses the Tick13 it used to keep after the swap-out (10.170 s): in the
  triple-cryo trial that is 3 skill ticks plus the 3 Stellar Swirls those ticks applied
  (808 -> 802 hits). The DEFAULT_PARTY calibration totals do not move.
* **Standard form timings**: the pull-out tech delays the 3rd tick's Anemo application
  until after the 2.5 s nuke-prep cooldown (Tick3 at 2.639 s), which is what buys the extra
  early VBTD nuke. The standard form removes that offset: Tick2 stays at 1.619 s, Tick3
  becomes 1.619 + 0.810 = 2.429 s and the whole tail moves with it (-0.210 s per hit), so
  the tail's own gaps survive. Of the game's alternating 0.69 / 0.81 cadence, 0.810 is the
  one that keeps the ability's mean gap closest to the ~0.750 s players expect
  (9.659 / 13 = 0.743, versus 0.734 for 0.69). Its 3rd application (2.429 s) now lands
  before the nuke-prep cooldown refreshes, so it misses the extra early nuke - the intended
  penalty for not using the tech.

* **Editor**: the picker offers the two forms; the focus strip draws only the hits that
  land (the in-air tick dimmed), the placement caption reads "3 of 14 hit(s) - cut by the
  1.75s swap-out", `sequence_issues()` reports the interruption as INFO, and auto-placing
  the next ability clears the in-air tick instead of the full hit table.
* **Not changed**: cooldowns stay keyed per ability, so the two forms do not share one yet
  (the `cooldown_key` follow-up above). The Sacrificial reset already ends both forms'
  cooldowns because it clears every `skill_talent` ability.
* **Smoke test**: `_run_skill_interrupt_check` pins the catalogue, both hit tables, the
  application ticks, the mean gap, the 2.5 s nuke-prep sides, the rule itself and the
  per-window counts / last hit / off-field state.

## Results table & time formatting

* The audit table (`ui/table.py`) is built from NUMBERS: floats for the stats,
  multipliers and damage columns, nullable `boolean` for the ON/OFF flags and nullable
  `Int64` for the stack counters; only Active / Owner / Action / Reaction stay text.
  It used to be strings, so clicking a header sorted "1,000" before "900".
* Empty cells follow ONE rule now: the engine's "-" / "None" / "" sentinels become real
  missing values in `ui/table.py`, and `st.dataframe(..., placeholder="-")` renders
  them (the `placeholder` parameter is the dataframe's own "text for missing values";
  without it Streamlit prints the literal string "None"). A literal "-" string used to
  render brighter than a placeholder, which is why identical-looking cells looked
  inconsistent.
* `ui/style.py` paints only two things: the per-owner row tint, and the STACK counter
  columns (grey at 0 / empty, green + bold with at least one stack). The boolean flags
  are grid-drawn checkboxes and are left completely unstyled - a Styler colour cannot
  reach a checkbox cell (it only ever added a dead `color` entry). `_is_inactive()`
  handles numpy scalars: pandas hands row values back as `numpy.bool_` / `numpy.int64`,
  which are NOT Python `bool`/`int` instances.
* The display layer is one simple literal dict, `ui/style.AUDIT_COLUMN_CONFIG`, in the
  same shape as the Streamlit `column_config` docs: one `st.column_config.NumberColumn
  ("name", format=..., help=...)` line per fixed column ("%.2f U" on the Aura gauge,
  "%.0f U" on Elemental App, "%d" for the stats, 3-decimal time, 1/3-decimal numbers),
  `TextColumn` for the four identity columns, and `pinned=True` on **Action** (the 4th
  column) so the row's action stays visible while the wide audit table is scrolled
  sideways. Every entry carries a one-line `help=` header tooltip. Columns that are not
  listed (the buff columns) keep the type Streamlit infers from their dtype: a checkbox
  for the boolean flags, a plain number for the stack counters.
  Streamlit gives column_config precedence over pandas.Styler formatting, so the Styler
  now paints colours only and the native cell value (which the frontend sorts on) is
  never touched. `ui/tabs/results.py` filters the dict to the columns actually shown,
  because the compact view only keeps a subset.
* The checkbox accent is the app theme's `primaryColor`, now **white**
  (`.streamlit/config.toml`). The grid draws checkboxes on a canvas, so the theme is
  the only lever - a Styler colour cannot reach them. The same accent drives buttons,
  sliders, focus rings and the strip cursor.
* Every time shown in the UI is **3 decimals**: audit table, results metrics, the
  trial breakdown and its step line, the editor metrics + rotation log, the strip
  ruler and its tooltips ("loop end", "swap out", hit tooltips), cooldown and
  validation messages and the interruption notes. The strip ruler switches to
  `m:ss.mmm` past 60s, and its step threshold moved from 56px to 64px so 3-decimal
  labels do not touch.
* `smoke_test._run_table_format_check` pins the dtypes, that every audit column sorts
  by value, that the empty sentinels never reach the table as text, the
  `placeholder="-"` contract, the stack-only painting, the `column_config` formats /
  pinned Action column / tooltips, and that no 1- or 2-decimal time format is left
  anywhere in `ui/`.



## Ability hit timings (advanced editor)

* The Field sequence screen shows one long-format `st.data_editor` per character:
  `Ability` / `Hit` / `Timing (s)`. Only `Timing (s)` is editable; the hit names
  are the shipped ones, and the ability name repeats on each row (a data editor
  cannot merge cells).
* A placement stores the **cast/press** time; the first hit lands at
  `cast + first timing`. Timings are delays from the cast and must be
  non-decreasing. The strip band starts at the cast. The placement control is
  "Cast time (s)".
* Overrides live in the editor spec (`ability_timings`) and are applied to COPIES
  of the `Ability` objects in `abilities.py`; the shared registry and every preset
  stay pristine. `smoke_test._run_ability_timing_check` pins the override, the
  engine result, the strip band and Reset, and asserts the registry did not move.
* The table is a draft: `Apply changes` commits it, `Reset timings` restores the
  shipped values and `Undo` restores the last snapshot. Unapplied edits are lost
  when the character changes.
* Build documents store `ability_timings` (schema 1.1); imported custom sequences
  re-apply them to deep copies, so a saved timing experiment survives a reload.

