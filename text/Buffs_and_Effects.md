# Buffs, Effects and Trigger Windows - Complete Reference

This file tracks every buff, effect, conditional proc and state window the
simulator models: characters, weapons, artifact sets and team composition.
Each row states who gets it (Target), what starts it (Trigger), how long it
lasts (Window), roughly what it is worth (Value), the engine flag behind it, and
the exact header it gets in the Simulation Results table.

## 2026-11 revision (current model)

- Casts are hidden `CAST` events. Every "on cast" effect arms on that marker, so the
  first hit is included; hit-triggered effects stay exclusive (pre-arm read).
- Element crit is data: `anemo_crit_dmg` (Faruzan C6) and `cryo_crit_rate`
  (New Tsaritsa set). It applies to standard and stellar damage of that element;
  the timeline no longer gates these buffs per hit.
- Stellar reaction shares use each contributor's full final stats: EM, stellar_bonus,
  jubilee, elevation, RES, CR/CD, stellar crit and the reaction element's crit.
  The effective column ignores RES; reaction multiplier audit columns stay null.
- Quills: the Mizuki C1 5.5xEM quill is shown in `Quills` (Faruzan/VBTD too); reactions
  add it once after the contributor shares, with the owner's elevation.
- Removed columns: Mizuki C1 Debuff, Odette C2 Shred (inside Shadow), Anastasya A4
  Jubilee, Anastasya Triumph. Every registry entry now has header help text.
- Odette Marvelous: full at cast, decays from her FIRST swap-out; re-entry and later
  swap-outs do not refill, only a new cast does. C6 still keeps the full pool.
- Aether: the charged attack grants +2 Frostglow on cast (N1 is NORMAL, C1/C2 are
  CHARGED); stacks cap at 8 and reset only when the burst consumes them.
- Constellation stat gates live in `FLAG_TO_BUFFS` (Aether C2/C6, Faruzan C6, Mizuki C6).

## Source of truth (change these, not this file)

| What | Where |
|---|---|
| Stat values | `buffs.py`: CONDITIONAL_CONSTANT_BUFFS, CONDITIONAL_NON_CONSTANT_BUFFS, PERMANENT_BUFFS, STACK_BUFFS |
| Wiring flag -> target / caster / constellation | `stats_calc.FLAG_TO_BUFFS` |
| Triggers and windows | `timeline.evaluate_timeline()` (writes one audit flag per event) |
| Permanent gear stats | `weapons.py`, `artifacts.py`, `characters.py` |
| Results-table columns | `buff_registry.BUFFS` |

## 0. Conventions

| Term | Meaning |
|---|---|
| Target: Party | every party member |
| Target: Active | whoever is on field at that instant |
| Target: User | the holder (member equipping the weapon / artifact set) |
| Target: Self | the caster of the buff (e.g. Odette) |
| Target: Others | everyone except the caster / holder |
| Target: named | one specific character |
| Inclusive | the hit that starts the window ALSO benefits from it |
| Pre-arm read | default rule: the window is read before the current hit arms it, so the proccing hit does NOT benefit |
| R1-R5 | refinement-scaled value |
| Window | duration in seconds from the trigger, or "always" / "permanent" |
| Flag key | audit flag in the event table; "(always_on)" = no flag, resolved on every event |
| initial_stats | permanent gear stat folded into the character before the simulation starts (not an event flag) |
| PERMANENT_BUFFS | permanent character passive applied once at setup (not an event flag) |
| (triggered) | an engine-injected proc: no per-event flag, but a damage row exists |
| Table column | exact header in the results table; "(not a table column)" means the effect is real but is not audited as its own column |
| Flat EM basis | base + weapon + artifact EM + flat EM buffs, including holder-based EM (Starsealed, Silver Light) for their holder and dynamic flat EM (Gilded Dreams 4pc); percentage EM shares are excluded (no feedback loops) |

Stacking is additive into the stat pool. Two effects ship WITHOUT a stat and
have no buff entry: **quills** (flat damage added before the multipliers, keys
`quill_damage` / `c1_quill`) and **stellar MV multipliers** (`stellar_mv_mult`).

## 1. Team composition

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| Cryo Resonance | Party | 2+ Cryo characters AND the enemy already has a Cryo aura (pre-hit) | while both hold | +15% Crit Rate | cryo_resonance_state | Cryo Resonance CR | The hit that first applies Cryo does not get it (pre-hit aura snapshot). |
| A Thousand Floating Dreams - EM per same-element ally | User | permanent, party composition (holder excluded) | permanent | +32/40/48/56/64 EM (R1-R5) per such ally | initial_stats | (not a table column) | Applied by apply_weapon_party_stats, before any buff. |
| A Thousand Floating Dreams - own element bonus | User | permanent, per ally of a DIFFERENT element | permanent | +10/14/18/22/26% own element DMG (R1-R5) per such ally | initial_stats | (not a table column) | Uses the holder's vision element. |
| A Thousand Floating Dreams - EM to others | Others | permanent | permanent | +40/42/44/46/48 flat EM (R1-R5) | initial_stats | (not a table column) | Holder is never counted in its own ally tallies. |
| Jade Vista - EM per same-element ally | User | permanent, party composition | permanent | +64/80/96/112/128 EM (R1-R5) per same-element ally | initial_stats | (not a table column) | Same helper as ATFD; idempotent pass. |
| Jade Vista - ATK% per other element | User | permanent, per ally of a different element | permanent | +12/15/18/21/24% ATK (R1-R5) per such ally | initial_stats | (not a table column) | Can be invoked twice safely (delta marker). |

## 2. Characters

### 2.1 Mizuki (Anemo)

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| Dreamdrifter State (DDS) | Party (gate) | her skill CAST (hidden CAST marker) | until swap-out or Tick13 | state only: gates every DDS row below | dreamdrifter_state | Mizuki DDS | Armed on the cast marker, so the first hit is included. |
| Skill swirl bonus | Party | while DDS | while DDS | stellar_bonus += (talent "Elemental Mastery-Based Swirl DMG Increase" / 1000) x her FLAT EM | dreamdrifter_state | Mizuki DDS | Divisor 1000 turns the stored talent percent into a ratio. |
| VBTD 2 EM share | Party | while DDS | while DDS | +10% of her FLAT EM | dreamdrifter_state | Mizuki DDS | Name implies VBTD only, but the gate is DDS (up from the cast). |
| A4 | Mizuki | a Cryo hit lands while DDS is up | 4s, refreshed | +100 flat EM | mizuki_a4_state | Mizuki A4 | No gauge requirement: any Cryo hit refreshes it. |
| C1 trigger state | (proc enabler) | any Mizuki skill hit during DDS, at most once per 3.5s | 3s | no stat; a Stellar Swirl consumes it -> C1 mini nuke (400% EM) + 5.5 x EM swirl quill | c1_debuff_state | (not a table column) | The C1 5.5xEM quill is shown in Quills; the mini nuke is a separate hit. |
| C2 shred (C2+) | Party | while DDS | while DDS | -20% Pyro/Hydro/Electro/Cryo/Anemo RES | dreamdrifter_state | Mizuki DDS | Code includes Anemo shred; the design note says PHEC only. |
| C2 elemental bonus (C2+) | Party | while DDS | while DDS | +0.04% of her FLAT EM to Pyro, Hydro, Electro and Cryo DMG bonus | dreamdrifter_state | Mizuki DDS | Four separate descriptors, one per element. |
| C6 stellar crit (C6) | Party | while DDS | while DDS | +10% Stellar Crit Rate, +20% Stellar Crit DMG | dreamdrifter_state | Mizuki DDS | Data-driven: "Mizuki C6 Stellar Crit" in buffs.py, min_constellation 6. |
| C6 EM crit (C6) | Mizuki | always; FLAT EM above 500 | always | +0.04% CR and +0.16% CD per EM above 500 (caps +20% / +80%) | always_on | (not a table column) | Recomputed per event because the EM basis moves. |
| VBTD nuke (non-stat) | Mizuki | her next skill Tick after a swirl she triggered in DDS (2.5s prep CD) | instant; nuke hit at +0.500 | quill 1000% EM x1.10 on the tick, nuke hit 1000% EM | vbtd_state | Mizuki VBTD EM | Delivered as quill damage, never as an EM stat. |

### 2.2 Aether (Cryo)

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| A4 | Aether | always | always | EM = 8% of his ATK, capped +160 | always_on | (not a table column) | Regenerated per event from his initial ATK. |
| Jubilee | Party | always | always | jubilee_mult = 0.0035% of his ATK, cap +7% | always_on | (not a table column) | Adds to Odette / Anastasya jubilee sources. |
| C2 Basic | Active | Aether skill TICK (not Skill_Initial) | until that character swaps out | +60 flat EM | aether_c2_state | Aether C2 EM | Arms for whoever is active at the tick, not necessarily Aether. |
| C2 Enhanced | Active | the armed active character deals Stellar DMG or triggers a swirl | until that character swaps out | +60 flat EM, stacking with Basic (+120) | aether_c2_enhanced_state | Aether C2 EM (Amp) | Read pre-arm: the hit that arms it does not benefit. |
| C6 (C6) | Party | his Burst consumes Frostglow stacks | 15s from the burst hit | +5% stellar_bonus per consumed stack (max 8 -> +40%) | aether_c6_state | Aether C6 Stellar | No min_constellation in the descriptor; the timeline flag is C6-gated. |
| Frostglow | (resource) | +1 per Elemental Skill tick except the initial hit (max 8) | consumed by the Burst | >=8 picks the Enhanced burst variant | frostglow_stacks | Aether Frostglow | On burst rows the column shows the stacks CONSUMED. |
| Quest (permanent) | Aether | always | permanent | +10 base ATK, +50 base HP, +10% CR, +20% CD, +20% ATK, +20% HP, +75 EM, +20% ER, +20% DEF | PERMANENT_BUFFS | (not a table column) | Key name is "Aether Quest"; applied before any timeline logic. |

### 2.3 Odette (Cryo)

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| Shadow on field | Party (gate) | CAST of Skill Cast or Odette Burst (recast excluded) | 20s, inclusive | state only: gates Marvelous, C2 and C6 | odette_shadow_state | Odette Shadow | The first hit of the cast is included. |
| Marvelous Splendor (A1) | Party | while the shadow is up: on-field = full pool; off-field transfers 1 stack/s (2/s at C1) to the party; C6 keeps her own full pool and the party ramps at the C1 rate | shadow window | +15% stellar_bonus per stack; pool 4 (C1+: 6) | marvelous_stacks | Odette Marvelous | Column shows Odette's own count on her rows and the party count on other rows. |
| C2 ATK per stack (C2+) | Party | while the shadow is up | shadow window | +7% ATK per Marvelous stack | marvelous_stacks | (not a separate column) | Uses the same stack flag; the column only displays the count. |
| C2 shred (C2+) | Party | while the shadow is up | shadow window | -20% Cryo RES, -20% Anemo RES | odette_shadow_state | (no own column) | The C2 shred is part of the Shadow bundle; no separate column. |
| C6 elevation (C6) | Others + Self | while the shadow is up | shadow window | +25% elevation for the OTHERS, +45% for Odette | odette_shadow_state | Odette Shadow | buffs.py comment says "0.25 party + 0.20 personal"; code applies 0.45 self / 0.25 others. |
| Snow Swan's Dream (SSD) | Odette | Odette Burst CAST | 20s | stellar_bonus = burst talent value (0.620 at B13) | odette_ssd_state | Odette SSD | The burst first hit is included. |
| SSD shared (C4+) | Others | while SSD is up | 20s | +50% of the SSD value (0.310 at B13) | odette_ssd_state | Odette SSD | Same flag/column as the self part. |
| A4 | Odette | always | always | stellar MV multiplier = 1 + 0.015% of ATK above 1000, cap 1.30 | always_on | (not a table column) | Delivered as stellar_mv_mult, a multiplier not a stat. |
| Jubilee | Party | always | always | jubilee_mult = 0.007% of her ATK, cap +14% | always_on | (not a table column) | Adds with Aether / Anastasya jubilee. |
| C1 extra stellar (C1+) | proc | her Recast's Skill_Stellar hit | +0.010, once per recast | 450% ATK stellar hit | (triggered) | (hit row only) | Inserted chronologically after the trigger. |
| C4 extra stellar (C4+) | proc | ANY party Stellar DMG hit while SSD is up | +0.010, 3.5s CD from the trigger | 99% ATK stellar hit | (triggered) | (hit row only) | CD measured from the trigger, not from the proc hit. |

### 2.4 Faruzan (Anemo)

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| C6 buff | Party | her Burst CAST | 22s | +40% Anemo Crit DMG (anemo_crit_dmg) + talent Anemo DMG bonus | faruzan_buff_state | Faruzan C6 Buff | Applies to Anemo hits only; the burst first hit is included. |
| C6 shred | Party | burst cast hit (opens 22s); Pressurized Collapse refreshes to at least +4s without shortening a 22s window | 22s / max(existing, +4s) | -30% Anemo RES | faruzan_debuff_state | Faruzan C6 Anemo Shred | The "bigger number wins" rule means the burst window is never shortened. |
| Quill (non-stat) | active hitters | while the buff window is up, an ANEMO STANDARD hit from the ACTIVE character | per hit, while the window is up | +32% of Faruzan's BASE ATK added to the hit | quill_damage | (not a table column) | Added before multipliers; off-field hits do not get it. |
| Pressurized Collapse | proc | burst cast hit, or ANY hit while the buff window is up | +0.720, 3.0s CD from the trigger | skill-talent MV | (triggered) | (hit row only) | The 3.0s CD is charged at the trigger, not at the collapse. |

### 2.5 Sucrose (Anemo)

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| A1 | Party except Anemo | Sucrose herself triggers a Stellar Swirl | 8s, refreshed | +50 flat EM | sucrose_a1_state | Sucrose A1 EM | Anemo characters are excluded, Sucrose included. |
| A4 | Others | any Sucrose Skill or Burst hit | 8s, refreshed | +20% of her FLAT EM | sucrose_a4_state | Sucrose A4 EM | Matches A4 (Molen): the skill/burst HIT is the trigger, not a swirl. |
| C6 (C6) | Party | her Burst cast hit (hit_offset 0), once per cast | 5.729s (= last burst hit) | +20% Cryo DMG bonus | sucrose_c6_state | Sucrose C6 Cryo DMG | Comment says window is [cast, cast+5.729], but the flag is read pre-arm, so the cast hit is excluded. |

### 2.6 Diona (Cryo)

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| Choice Treasures state | (proc state) | CAST of either skill | 20s, refreshed | enables the Icy Paw volley on any Stellar Swirl | diona_ct_state | Diona Choice Treasures | No stat of its own; its 3.5s proc CD lives in the engine. |
| C6 buff (C6) | Active | her Diona Burst CAST, INCLUSIVE | 11.75s (whole burst field) | +200 flat EM, +40% stellar_bonus | diona_c6_state | Diona C6 Buff | The burst first hit is included. |
| C6 passive (C6) | Diona | always | permanent | +25% HP | PERMANENT_BUFFS | (not a table column) | Unconditional (the UI only offers C6); key name collides with the conditional Diona C6 entry in another dict. |
| Icy Paws (triggered) | proc | ANY character Stellar Swirl while Choice Treasures is up | +0.270 / +0.360 / +0.360; 3.5s CD from the trigger | 3 x Icy Paw talent MV (only tick 1 applies 1U) | (triggered) | (hit rows only) | Injected in chronological order, not simply at i+1. |

### 2.7 Anastasya (Cryo)

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| Accolades base (A1) | Party | her Skill Tap CAST, INCLUSIVE | 20s | +12% Crit DMG | anastasya_accolades_state | Anastasya Accolades | The skill first hit is included. |
| Accolades C1 unsealed (C1-C3) | Party | same cast | 20s | Cryo recipients +15% ATK; all others +60 flat EM | anastasya_accolades_state | Anastasya Accolades | Element include/exclude filters on the recipient. |
| Accolades sealed - shared (Others) | Others | while SEALED, or during the 8s linger after unsealing | sealed / 8s linger | C0: +16% CD; C1: +48% CD +60% ATK / 240 EM; C4: +68.8% CD +86% ATK / 344 EM | anastasya_accolades_shared_state | Anastasya Accolades / Anastasya Sealed | Mutually exclusive with the unsealed variant (separate flag). |
| Accolades sealed - self | Self | while SEALED (C1+; nothing at C0) | sealed | C1: +36% CD +45% ATK / 180 EM; C4: +51.6% CD +64.5% ATK / 258 EM | anastasya_accolades_shared_state | Anastasya Sealed | At C0 she loses her own Accolades when sealed (intended per backlog). |
| Burst stellar bonus | Party | her Burst CAST | 20s | stellar_bonus = burst talent (0.354 at B13) | anastasya_burst_state | Anastasya Burst Stellar | The burst first hit is included; talent divisor is 1.0 here. |
| Extra stellar beat (triggered) | proc | every Palestar Crown Stellar beat while the burst window is up | +0.010 | burst-talent stellar hit | (triggered) | (hit rows only) | The burst hit itself never gains the bonus it just armed. |
| Love (C2+) | Party | her Skill Tap CAST, INCLUSIVE | 30s | +50% Stellar Crit DMG | anastasya_love_state | Anastasya Love | Independent of Accolades; can overlap any variant. |
| Love elevation (C2) | Party | always | permanent | +5% elevation_mult | always_on | (not a table column) | One key, two paths: stellar DMG and each contributor's share of a stellar reaction. |
| Love elevation C6 (C6) | Party | always | permanent | +10% elevation_mult (total +15% with the C2 part) | always_on | (not a table column) | Applied as a second additive source. |
| A4 | Party | always | always | +10% jubilee on STELLAR SWIRL REACTIONS only | always_on | (not a table column) | Separate stat key (reaction_jubilee_mult); plain stellar DMG is unaffected. |
| Jubilee passive | Party | always | always | jubilee_mult = 0.007% of her ATK, cap +14% | always_on | (not a table column) | Adds with Aether / Odette jubilee. |
| Seal state | (state) | her burst is cast, then she swaps out | until unseal | enables the shared Accolades variants | anastasya_sealed_state | Anastasya Sealed | A burst without a following swap-out does not seal. |
| Unseal + Triumph | proc | her swap-in at least 15s after the seal, once per seal | +0.010 | burst-talent stellar hit | anastasya_triumph_ready | (not a table column) | One-off proc; the damage row is the only trace. |
| C6 Triumph (C6) | proc | ANY other character swap-in while Love is up | +0.010; 15s per-character CD from the trigger | 2.0x the Triumph MV | (triggered) | (no own column) | No dedicated audit header; the damage row is the only trace. |

## 3. Weapons

### 3.1 Permanent passives (always while equipped)

Ordinary secondary stat lines (base ATK, CR, CD, ER, EM, ATK%, elemental bonus) are
folded by `build_initial_stats` and are gear stats, not buffs. The rows below are
passives that are permanent for the whole run.

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| A Thousand Floating Dreams | User / Others | party composition | permanent | see section 1 | initial_stats | (not a table column) | Applied by apply_weapon_party_stats. |
| Jade Vista | User | party composition | permanent | see section 1 | initial_stats | (not a table column) | Same helper; holder never counts itself. |
| Starcaller's Watch | User | always | permanent | EM 365/390/415/440/465 (R1-R5) | initial_stats | (not a table column) | Permanent EM only; no conditional passive modelled. |
| Azurelight | User | always | permanent | +24/30/36/42/48% ATK (R1-R5) | initial_stats | (not a table column) | Refinement list under the ATK% key. |
| Aquila Favonia | User | always | permanent | +41.3% Physical DMG; +20/25/30/35/40% ATK (R1-R5) | initial_stats | (not a table column) | Two permanent stats in one entry. |
| Exaiphanes Blade | User | always | permanent | Crit DMG 0/42/42/42/42% (R1-R5) | initial_stats | (not a table column) | Uses the `crit_damage` alias, not `crit_dmg`; R1 is 0%. |
| Breezeborne Refrain | User | always | permanent | ER +20/25/30/35/40% (R1-R5) | initial_stats | (not a table column) | A refinement-scaled secondary is unusual for a weapon stat. |
| Elegy for the End | User | always | permanent | EM 60/75/90/105/120 (R1-R5) | initial_stats | (not a table column) | In game this EM comes from the passive; here it is folded permanently while the sigil buff stays separate. |
| Starsealed Edict | User | always | permanent | Crit DMG 112.2/118.2/124.2/130.2/136.2% (0.882 + 0.24-0.48 by refinement) | initial_stats | (not a table column) | Two additive CD sources in one entry. |
| Favonius Warbow | User | always | permanent | ER 61.3% | initial_stats | (not a table column) | Stat line only; its passive is not modelled. |

### 3.2 Conditional weapon passives (holder only)

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| Exaiphanes Blade - ATK proc | User | any hit by the holder | 8s; 5s internal CD | +16/20/24/32/40% ATK (R1-R5) | exaiphanes_blade_state | Exaiphanes ATK% | Read pre-arm: the triggering hit does not get the proc. R4 jumps 0.24 -> 0.32; a 0.28 rung is missing (possible typo). |
| Silver Light - EM stacks | User | one stack per skill cast or recast (first hit) | 12s per stack, no cap | +52/65/78/91/104 EM per stack (R1-R5) | silver_light_stacks | Silver Light EM Stacks | Stacks are per CAST, not per damage tick; they expire independently. |
| The Widsith (Average) - roll buff | User | taking the field (SWAP_IN) | 10s; 30s CD from the trigger | 1/3 of each roll at once: +20/25/30/35/40% ATK, +80/100/120/140/160 EM, +16/20/24/28/32% to all 7 elemental bonuses (R1-R5) | widsith_state | Widsith Buff | Approximation: the game rolls ONE of the three; this variant averages by applying a third of all three. |
| The Widsith (All EM) - roll buff | User | taking the field (SWAP_IN) | 10s; 30s CD from the trigger | +240/300/360/420/480 EM (R1-R5) | widsith_state | Widsith Buff | Shares one flag/column with the Average variant. Only ONE Widsith holder is tracked per run (see known issues). |
| Sacrificial Jade - off-field passive | User | passive starts ON; >10s of continuous on-field time removes it; >=5s off-field restores it | toggle, no fixed duration | +32/40/48/56/64% HP; +40/50/60/70/80 EM (R1-R5) | sacrificial_jade_state | Sacrificial Jade | Detects the exact 10s/5s thresholds with an epsilon; the off-field clock restarts on every swap. |
| Sunny Morning Sleep-In - swirl window | User | the holder triggers a Stellar Swirl | 6s, refreshed | +120/150/180/210/240 EM (R1-R5) | sunny_swirl_state | Sunny Swirl EM | Independent of the other two Sunny windows. |
| Sunny Morning Sleep-In - skill window | User | a STANDARD hit by the holder whose attack type is Skill | 9s, refreshed | +96/120/144/168/192 EM (R1-R5) | sunny_skill_state | Sunny Skill EM | Attack type, not hit name, is the test. |
| Sunny Morning Sleep-In - burst window | User | a STANDARD hit by the holder whose attack type is Burst | 30s, refreshed | +32/40/48/56/64 EM (R1-R5) | sunny_burst_state | Sunny Burst EM | All three windows can be active at once and add up. |
| Wandering Evenstar - periodic ATK | User + Others | periodic: a 12s buff starting every 10s from trial start, so 2 instances overlap | 12s per instance; stack count max 2 | holder: flat ATK = 24/30/36/42/48% of FLAT EM (R1-R5) per stack; others: 7.2/9/10.8/12.6/14.4% per stack | evenstar_stacks | Evenstar Stacks | Closed-form from t (no trigger events), so after 10s the holder is always at 2 stacks. |
| Thrilling Tales of Dragon Slayers | Active | holder swaps out, then a DIFFERENT character swaps in | 10s on the incoming character; 20s CD from the swap-out | +24/30/36/42/48% ATK (R1-R5) | ttds_state | TTDS ATK% | The buff is only flagged while the target is the owner AND on field, so it drops if they leave early. |
| Starsealed Edict - skill window | User | holder skill CAST | 20s; refreshed/reset by the next cast | +48/60/72/84/96 EM (R1-R5) | starsealed_state | Starsealed EM | The skill first hit is included; refreshing resets the stack count. |
| Starsealed Edict - swirl stacks | User | any Stellar Swirl by ANY character while the window is up | until the window ends | +24/30/36/42/48 EM per stack (R1-R5) | starsealed_stacks | Starsealed Stacks | Capped at 3 stacks (STARSEALED_MAX_STACKS); stacks are per swirl event, not per character. |
| Whitelake Frostfeather - ATK stacks | User | one stack per skill hit (0.1s gain CD) | 8s per stack, max 3; a 4th stack replaces the oldest | +8/10/12/14/16% ATK per stack (R1-R5) | whitlake_stacks | Whitelake Stacks | Stack expiries are pruned per event, so the count can drop between hits. |
| Whitelake Frostfeather - 3-stack payoff | User | at 3 or more stacks | tied to the 3rd stack lifetime | +50/65/80/95/110% Stellar Crit DMG (R1-R5) | whitlake_max_state | Whitelake 3-Stack Crit | Constant gate: it does NOT scale with 4+ stacks; it turns OFF when the pool drops below 3. |
| Finale Of The Deep - ATK window | User | a STANDARD hit by the holder whose attack type is Skill | 15s; 10s CD from the trigger | +12/15/18/21/24% ATK (R1-R5) | finale_state | Finale ATK% | Later triggers refresh the 15s window. |
| Breezeborne Refrain - sigils | User (source) | skill or burst DAMAGE by the holder grants a sigil (0.03s gain CD); sigils never expire | until 3 sigils | 3 sigils -> see the buff row | breezeborne_sigils | Breezeborne Sigils | No sigils are gained while the Buff itself is active. |
| Breezeborne Refrain - buff | Party | the 3rd sigil | 12s; no sigils gained meanwhile | +24/30/36/42/48% stellar_bonus (R1-R5) | breezeborne_state | Breezeborne Buff | The sigil counter resets to 0 on proc. |
| Elegy for the End - sigils | User (source) | skill or burst DAMAGE by the holder grants a sigil (0.2s gain CD) | until 4 sigils | 4 sigils -> see the buff row | elegy_sigils | Elegy Sigils | No sigils during the 20s lockout. |
| Elegy for the End - buff | Party | the 4th sigil | 12s buff; 20s lockout from the proc | +20/25/30/35/40% ATK and +100/125/150/175/200 EM (R1-R5) | elegy_state | Elegy Buff | Lockout starts at the same instant as the buff, so it ends 8s after the buff. |
| New Bough - stacks | User | a skill CAST opens/refreshes a 12s window; any damage hit by the holder inside it adds a stack (max 3, at most 1/s) | 12s window; stacks die with it | +6/7.5/9/10.5/12% ATK and +8/10/12/14/16% stellar_bonus per stack (R1-R5) | newbough_stacks | New Bough Stacks | The first hit after the cast gains the first stack. |
| Silverdawn - window | User | a skill or burst CAST by the holder | 6s base, extended by 3s per proc (0.1s CD, max 8 -> 30s cap) | +40/52/64/76/88% ATK and +40/52/64/76/88% Stellar Crit DMG (R1-R5) | silverdawn_state | Silverdawn Buff | The first hit is included. |
| Silverdawn - extensions | User | inside the window, a Stellar Swirl the holder triggers or a Stellar DMG hit they deal | +3s each, max 8 | - | silverdawn_extensions | Silverdawn Ext | Extensions are reset to 0 whenever the window is re-opened by a skill/burst. |
| Rainbow Serpent's Rain Bow | User | a hit the holder deals while OFF the field (owner != active character) | 8s, refreshed by later off-field hits | +28/35/42/49/56% ATK (R1-R5) | rainbow_bow_state | Rain Bow ATK% | On-field hits do NOT refresh it. |

### 3.3 Sacrificial weapons - skill cooldown reset

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| Sacrificial Fragments / Sacrificial Bow | User | SKILL damage dealt by the ON-FIELD holder | instant; ICD 30/26/22/19/16s (R1-R5) from the proc | +1 charge of the holder elemental skill (a plain 1-charge skill becomes castable again) | WEAPON_PROC | (own row: action = proc label) | Modelled as GUARANTEED (no RNG). Any skill tick can consume the ICD, so a late tick can steal the reset. Triggered/engine hits never count as proc sources. |

## 4. Artifact sets

| Effect | Target | Trigger / condition | Window | Value | Flag key | Table column | Notes |
|---|---|---|---|---|---|---|---|
| 2p/2p EM | User | always | permanent | +160 EM | initial_stats | (not a table column) | Two 2-piece EM sets; folded as a set bonus. |
| 2p/2p ATK | User | always | permanent | +36% ATK | initial_stats | (not a table column) | Two 2-piece ATK sets. |
| Gilded Dreams - 2pc | User | always | permanent | +80 EM | initial_stats | (not a table column) | The 4pc effect is dynamic (next row). |
| Gilded Dreams - 4pc | User | the holder triggers a Stellar Swirl | 8s; 8s CD from the trigger | +14% ATK per same-element ally, +50 EM per different-element ally | gilded_state | Gilded Dreams | Modelled on swirl only; the game also counts other reactions. Read pre-arm. |
| Heart Of The Furnace - 2pc | User | always | permanent | +18% ATK | initial_stats | (not a table column) | The same name is also treated as a WEAPON by the holder scan (see known issues). |
| Heart Of The Furnace - 4pc | Self + Party | whoever holds it deals Stellar DMG OR triggers a Stellar Swirl | 12s, refreshed | holder: +12% ATK; party: +50% stellar_bonus | hotf_state | HotF Stellar | Read pre-arm; holder detection accepts weapon or artifact slot. |
| Instructor - 2pc | User | always | permanent | +80 EM | initial_stats | (not a table column) | - |
| Instructor - 4pc | Party | the ON-FIELD holder triggers a Stellar Swirl | 8s, refreshed | +120 EM | instructor_state | Instructor EM | Swirl only, although the game triggers on any reaction. |
| Noblesse Oblige - 2pc | User | always | permanent | +20% Burst DMG | initial_stats | (not a table column) | Standard-damage burst bonus only. |
| Noblesse Oblige - 4pc | Party | the holder CASTS a burst (attack type Burst) | 12s | +20% ATK | noblesse_state | Noblesse ATK% | The burst first hit is included. |
| Tenacity Of The Millelith - 2pc | User | always | permanent | +20% HP | initial_stats | (not a table column) | - |
| Tenacity Of The Millelith - 4pc | Party | a STANDARD hit by the holder whose attack type is Skill | 3s; 0.5s trigger CD | +20% ATK | tenacity_state | Tenacity ATK% | Requires standard damage AND skill type; off-field holder hits still count if the holder owns the hit. |
| A Day Carved From Rising Winds - 2pc | User | always | permanent | +18% ATK | initial_stats | (not a table column) | - |
| A Day Carved From Rising Winds - 4pc | User | ANY standard hit by the holder | 6s, refreshed | +25% ATK | risingwinds_state | Rising Winds ATK% | Simplified to any standard hit; the game wording is broader. |
| Scarlet Proof - 2pc | User | always | permanent | +18% ATK | initial_stats | (not a table column) | - |
| Scarlet Proof - 4pc | User | an ON-FIELD Stellar Swirl by the holder | 10s, refreshed | +16% Crit Rate, +40% stellar_bonus | scarlet_state | Scarlet Proof | Requires active_character == holder. |
| Viridescent Venerer - set bonus | User | always | permanent | +15% Anemo DMG, +20% stellar_bonus | initial_stats | (not a table column) | The 20% stellar bonus is a custom value, not a standard VV line. |
| Viridescent Venerer - 4pc | Party | an ON-FIELD Stellar Swirl by the holder | 10s, refreshed | -40% CRYO RES | vv_state | VV Elemental Shred | ONLY Cryo shred exists in the engine; the label says elemental, but Anemo/Pyro/etc. are not shredded. |
| New Tsaritsa set - 2pc | User | always | permanent | +18% ATK | initial_stats | (not a table column) | - |
| New Tsaritsa set - stacks | User | +1 stack (max 2) on a normal standard hit, a skill cast or a burst cast (hit_offset 0); -1 stack per 3s of ON-FIELD time | until the stacks decay | 2 stacks max | tsaritsa_stacks | Tsaritsa Stacks | Cast stacks require the first hit of the cast; the crit flags read the PRE-gain count. |
| New Tsaritsa set - Cryo crit | User | while stacked; applies to Cryo hits | while stacked | +20% cryo_crit_rate | tsaritsa_state | Tsaritsa Cryo CR | Element gating lives in the stat key; the flag is the holder window. |
| New Tsaritsa set - stellar crit | User | while stacked (any element) | while stacked | +20% Stellar Crit Rate | tsaritsa_stellar_state | Tsaritsa Stellar CR | Applies to stellar damage, not to standard hits. |

## 5. Audit-key index (quick lookup)

Character keys:

- `dreamdrifter_state` -> Mizuki DDS: DDS active (gates every DDS effect).
- `mizuki_a4_state` -> Mizuki A4: +100 EM window.
- `vbtd_state` -> Mizuki VBTD Quill: VBTD quill armed on this tick.
- `faruzan_buff_state` -> Faruzan C6 Buff: buff window (Anemo-gated).
- `faruzan_debuff_state` -> Faruzan C6 Anemo Shred: shred window.
- `aether_c2_state` -> Aether C2 EM: C2 Basic armed for the active character.
- `aether_c2_enhanced_state` -> Aether C2 EM (Amp): C2 Enhanced armed.
- `frostglow_stacks` -> Aether Frostglow: current (or consumed) stacks.
- `aether_c6_state` -> Aether C6 Stellar: 15s window ON/OFF.
- `aether_c6_stacks` -> (no column): stack count consumed by the C6 buff.
- `marvelous_stacks` -> Odette Marvelous: stack count (own or party).
- `odette_shadow_state` -> Odette Shadow: shadow window (gates Marvelous/C2/C6).
- `odette_ssd_state` -> Odette SSD: Snow Swan's Dream window.
- `sucrose_a1_state` -> Sucrose A1 EM: 8s non-Anemo EM window.
- `sucrose_a4_state` -> Sucrose A4 EM: 8s flat-EM share window.
- `sucrose_c6_state` -> Sucrose C6 Cryo DMG: one-burst cryo bonus window.
- `anastasya_burst_state` -> Anastasya Burst Stellar: 20s party stellar window.
- `anastasya_accolades_state` -> Anastasya Accolades: 20s Accolades window.
- `anastasya_accolades_unsealed_state` -> (no own column): unsealed variant split.
- `anastasya_accolades_shared_state` -> (no own column): sealed/shared variant split.
- `anastasya_sealed_state` -> Anastasya Sealed: seal/shared state.
- `anastasya_love_state` -> Anastasya Love: 30s C2 window.
- `diona_ct_state` -> Diona Choice Treasures: 20s proc state.
- `diona_c6_state` -> Diona C6 Buff: 11.75s Active buff.

Weapon keys:

- `exaiphanes_blade_state` -> Exaiphanes ATK%.
- `silver_light_stacks` -> Silver Light EM Stacks.
- `widsith_state` -> Widsith Buff (both variants).
- `sacrificial_jade_state` -> Sacrificial Jade.
- `sunny_swirl_state` / `sunny_skill_state` / `sunny_burst_state` -> Sunny Swirl / Skill / Burst EM.
- `evenstar_stacks` -> Evenstar Stacks.
- `ttds_state` -> TTDS ATK%.
- `starsealed_state` -> Starsealed EM; `starsealed_stacks` -> Starsealed Stacks.
- `whitlake_stacks` -> Whitelake Stacks; `whitlake_max_state` -> Whitelake 3-Stack Crit.
- `finale_state` -> Finale ATK%.
- `breezeborne_sigils` -> Breezeborne Sigils; `breezeborne_state` -> Breezeborne Buff.
- `elegy_sigils` -> Elegy Sigils; `elegy_state` -> Elegy Buff.
- `newbough_stacks` -> New Bough Stacks.
- `silverdawn_state` -> Silverdawn Buff; `silverdawn_extensions` -> Silverdawn Ext.
- `rainbow_bow_state` -> Rain Bow ATK%.

Artifact keys:

- `hotf_state` -> HotF Stellar.
- `vv_state` -> VV Elemental Shred (Cryo only).
- `instructor_state` -> Instructor EM.
- `gilded_state` -> Gilded Dreams.
- `noblesse_state` -> Noblesse ATK%.
- `tenacity_state` -> Tenacity ATK%.
- `risingwinds_state` -> Rising Winds ATK%.
- `scarlet_state` -> Scarlet Proof.
- `tsaritsa_stacks` -> Tsaritsa Stacks; `tsaritsa_state` -> Tsaritsa Cryo CR; `tsaritsa_stellar_state` -> Tsaritsa Stellar CR.

Team keys:

- `cryo_resonance_state` -> Cryo Resonance CR.

No-flag effects (`always_on`): Odette A4, Odette jubilee, Aether A4, Aether jubilee, Anastasya jubilee, Anastasya A4, Love elevation (C2 and C6), Mizuki C6 EM CR/CD.

## 6. Cross-cutting engine rules

1. **Pre-arm read (HIT-triggered effects).** A window is resolved from its pre-event expiry, then re-armed, so the hit that procs it never benefits. Applies to VV, Instructor, HotF, Gilded, Tenacity, Rising Winds, Scarlet, Sucrose A1/A4/C6, Widsith, Jade, Sunny, Whitelake, Finale, Breezeborne, Elegy, Rainbow Bow, Exaiphanes, and TTDS start.
2. **Cast effects are inclusive.** A hidden `CAST` event is processed before the first hit, so Mizuki DDS, Odette Shadow/SSD, Faruzan C6 buff+shred, Diona Choice Treasures/C6, Anastasya Accolades/Love/burst, Silver Light, Starsealed, Silverdawn, New Bough, Noblesse, Tsaritsa stacks and Aether C6 all arm first and include that first hit. Sucrose A1/A4/C6 stay hit-triggered.
3. **Window epsilon.** `_WINDOW_EPS = 1e-9` keeps the hit that lands exactly on the closing edge inside the window.
4. **Additive stacking.** Resolved buffs are added into the stat pool; percentage shares never feed the flat-EM basis (no EM feedback loops).
5. **Constellation gates.** `min_constellation` / `max_constellation` are checked on the CASTER (or holder), not on the recipient.
6. **Target scopes.** Party / Active / User / Self / Others / named character. `Active` is `active_character` at that instant; `User` is the weapon / set holder.
7. **Caster sentinels.** `user`, `hotf_holder`, and `holder:<Weapon or Set Name>` resolve to a party member; an unequipped weapon resolves to None and every target check then fails (no phantom buffs).
8. **Refinement.** Every list is indexed R1-R5; an unparseable refinement falls back to R1.
9. **Non-stat deliveries.** Quills add flat damage before the multipliers; `stellar_mv_mult` scales a motion value; RES shreds modify the RES multiplier. None of these appear as a stat in the table.
10. **Crit model.** Normal builds use `1 + CR*CD` (average) and `1 + CD` (crit). 100% RV / KQM builds use one Crit Value `CV = 2*CR + CD` and the piecewise `1 + CV^2/8` / `CV - 1` multiplier.
11. **Missing flag = OFF.** An event without a key is treated as OFF/0; only `always_on` resolves unconditionally.
12. **Element crit.** `anemo_crit_dmg` / `cryo_crit_rate` are real stat keys: they apply to standard and stellar damage of that element, so the timeline does not gate the buff per hit.
13. **Reaction shares.** Stellar reactions use each contributor's full final stats (EM, stellar bonus, jubilee, elevation, RES, CR/CD, stellar crit, reaction-element crit). The effective column ignores RES; the reaction multiplier audit columns stay null.
14. **Quills.** Standard damage keeps the bonus multiplier on quills. Stellar and reaction damage add quills without it; the C1 quill is added once post-share with Mizuki's elevation/crit and is shown in `Quills`.
15. **Once-per-cast checks.** `hit_offset == 0` identifies the first hit of a cast; triggered hits carry `hit_offset = their own trigger delay`, so they never look like a cast start.
16. **Trial-strip buff lanes.** The trial strip draws an uptime lane per buff that (a) opts in with a `strip` label in `buff_registry` and (b) passes the same `visible_buffs()` gate as the audit table. The current six are Widsith, VV, Gilded, Instructor, HotF and Cryo Resonance. Bars are the sampled runs of the flag the engine writes on every event, so a bar ends at the last event that saw the buff up rather than at the theoretical expiry; the rotation and field-sequence strips draw none.

## 7. Known issues / possible inconsistencies worth checking

These are observations, not confirmed bugs. Each one is a place where the data,
the comments and the implementation do not fully agree. Items 1 and 6 below were
resolved by the 2026-11 revision.

1. **Mizuki C1 label vs effect (resolved).** The C1 column was removed; the mini nuke stays a hit and the 5.5 x EM quill is shown in `Quills`.
2. **VV is Cryo-only.** The column says `VV Elemental Shred`, but `buffs.py` only defines `cryo_shred: 0.40`. Anemo/Pyro/Hydro/Electro are not shredded.
3. **Sucrose C6 window edge.** The timeline comment says the window is `[cast, cast + 5.729]`, but the flag is read pre-arm, so the cast hit itself is excluded. One of the two should change.
4. **VBTD naming vs DDS gate.** `Mizuki Skill` and `Mizuki VBTD EM Share` are gated by `dreamdrifter_state`, so they apply from the cast hit for the whole DDS, not only after a VBTD proc.
5. **Mizuki C2 includes Anemo.** The design note/backlog describes PHEC, but `Mizuki C2` also carries `anemo_shred: 0.20`.
6. **Mizuki C6 stellar crit (resolved).** Now `Mizuki C6 Stellar Crit` in `buffs.py` + a `dreamdrifter_state` descriptor with `min_constellation: 6`.
7. **Exaiphanes data gaps.** The ATK list `[0.16, 0.20, 0.24, 0.32, 0.40]` skips 0.28 between R3 and R4, and the permanent Crit DMG list is `[0.0, 0.42, 0.42, 0.42, 0.42]` (0% at R1, 42% at R2-R5). Both look like data typos.
8. **CRIT key alias.** Exaiphanes uses `crit_damage` while other weapons use `crit_dmg`; `build_initial_stats` special-cases it, but new code reading only `crit_dmg` would silently drop it.
9. **Diona C6 name collision.** `Diona C6` is a key in CONDITIONAL_CONSTANT_BUFFS (200 EM / 0.40 stellar) AND in PERMANENT_BUFFS (25% HP). Different dicts, same name.
10. **Anastasya burst divisor.** That talent uses divisor 1.0 (already decimal) while Mizuki uses 1000 and most others 100; copied entries can be off by 10x-1000x.
11. **Anastasya C0 sealed self.** There is no sealed-self descriptor at C0, so sealing removes her own Accolades (intended per backlog, surprising in the table).
12. **One Widsith holder only.** `_weapon_holder("The Widsith (Average)") or _weapon_holder("The Widsith (All EM)")` tracks a single holder; two different Widsiths in one party leave one untracked.
13. **Odette C6 comment.** The comment says `0.25 party + 0.20 personal`, but the code applies 0.45 to Odette and 0.25 to the others; the comment implies a party share she does not receive.
14. **Elegy EM may be double-counted.** The 60-120 EM is folded as a permanent `WEAPON_STATS` stat while the sigil buff also grants 100-200 EM. If the 60-120 is the passive, it should be windowed with the buff.
15. **Aether late skill ticks.** His skill has no `interrupt_on_swap_out`, so a tick after his swap-out still resolves; C2 Basic arms for `active_character` at that instant, which can be the NEXT character.
16. **Aether C6 has no stack column.** `aether_c6_stacks` exists as a stack flag but not as a `buff_registry` column, unlike Tsaritsa / Whitelake / Evenstar stacks.
17. **Artifact trigger simplifications.** Gilded / Instructor / VV trigger on swirl only; Rising Winds on any standard hit; Tenacity requires standard damage + Skill type; HotF accepts the name in the weapon OR artifact slot (but its 2pc ATK exists only as an artifact set). Confirm these are the intended custom rules.
18. **VV permanent 20% stellar.** `artifacts.ARTIFACTS_BONUSES["Viridescent Venerer"]` includes `stellar_bonus: 0.20`, which is not a standard VV line.
19. **Evenstar stacks are a formula.** The count comes from `int(t // 10)` windows, not from procs, so it ignores field state and can show 2 stacks immediately (by design, but not a real trigger).
20. **New Bough counts engine hits.** Any damage hit by the holder inside the 12s window adds a stack, including injected procs (the 1/s cap limits the impact).

## 8. Maintenance map: adding a new buff

1. Add the value to the right dict in `buffs.py` (constant / non-constant / permanent / stack).
2. Add a descriptor to `stats_calc.FLAG_TO_BUFFS` with its `target`, `caster`, optional constellation gates, `require_party` and element include/exclude.
3. Emit the audit flag in `timeline.evaluate_timeline()` and store the window as a module constant next to the other `*_WINDOW` values.
4. Add the column to `buff_registry.BUFFS` (key, label, group, owner, min constellation / team requirement).
5. Update this file and `text/Implementation_Backlog.md`; the smoke test requires every `buffs.py` entry to be reachable or explicitly `DORMANT`.

