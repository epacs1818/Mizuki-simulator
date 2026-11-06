# Party Configuration Backlog

Tracks which characters, constellations, weapons, artifact sets and buffs have
been verified against in-game records. The `New test` calibration set is the
only fully verified configuration so far; everything else is a stub that still
needs a manual pass.

Legend: ✔ = verified in the New test set | ◻ = implemented but not yet verified

## Characters

| Character | Element | Constellations offered | Status | Notes |
| --- | --- | --- | --- | --- |
| Mizuki | Anemo | C0-C6 | ✔ | C2 verified; C6 crit-from-EM path present |
| Aether | Cryo | C4-C6 | ✔ | C6 verified (Frostglow / Aether C6 stellar) |
| Odette | Cryo | C0-C3 | ✔ | C2 verified (Marvelous stacks) |
| Faruzan | Anemo | C6 | ✔ | C6 CD buff + Anemo shred verified |
| Sucrose | Anemo | C0-C6 | ◻ | A1/A4/C6 implemented, not calibrated |
| Diona | Cryo | C6 | ◻ | C6 EM / stellar buff only |

## Weapons

| Weapon | Type | Status |
| --- | --- | --- |
| Sacrificial Fragments | Catalyst | ✔ |
| New Bough | Sword | ✔ |
| Silver Light | Sword | ✔ |
| Exaiphanes Blade | Sword | ✔ |
| Favonius Warbow | Bow | ✔ |
| The Widsith (Average) | Catalyst | ◻ |
| The Widsith (All EM) | Catalyst | ◻ |
| Sacrificial Jade | Catalyst | ◻ |
| Sunny Morning Sleep-In | Catalyst | ◻ |
| Starcaller's Watch | Catalyst | ◻ |
| A Thousand Floating Dreams | Catalyst | ◻ |
| Wandering Evenstar | Catalyst | ◻ |
| Thrilling Tales of Dragon Slayers | Catalyst | ◻ |
| Starsealed Edict | Catalyst | ◻ |
| Whitelake Frostfeather | Sword | ◻ |
| Finale Of The Deep | Sword | ◻ |
| Azurelight | Sword | ◻ |
| Aquila Favonia | Sword | ◻ |
| Sacrificial Bow | Bow | ◻ |
| Breezeborne Refrain | Bow | ◻ |
| Elegy for the End | Bow | ◻ |

## Artifact sets

| Set | Status |
| --- | --- |
| 2p/2p EM | ✔ |
| 2p/2p ATK | ✔ |
| Heart Of The Furnace | ✔ |
| Viridescent Venerer | ✔ |
| Instructor | ✔ |
| Gilded Dreams | ◻ |
| Noblesse Oblige | ◻ |
| Tenacity Of The Millelith | ◻ |
| A Day Carved From Rising Winds | ◻ |
| Scarlet Proof | ◻ |

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
| Sucrose A1 EM | Character | Sucrose | always | ◻ |
| Sucrose A4 EM | Character | Sucrose | always | ◻ |
| Sucrose C6 Cryo DMG | Character | Sucrose | C6 | ◻ |
| Exaiphanes ATK% | Weapon | Exaiphanes Blade | equipped | ✔ |
| Silver Light EM Stacks | Weapon | Silver Light | equipped | ✔ |
| HotF Stellar | Artifact | Heart Of The Furnace | equipped | ✔ |
| VV Elemental Shred | Artifact | Viridescent Venerer | equipped | ✔ |
| Instructor EM | Artifact | Instructor | equipped | ✔ |
| Cryo Resonance CR | Team | Cryo Resonance | 2+ Cryo | ◻ |

## Next verification targets

1. Cryo Resonance: confirm the 15% CR applies only with 2+ Cryo characters.
2. Sucrose kit: A1 (50 EM on swirl), A4 (20% flat EM share), C6 (20% Cryo DMG).
3. Odette C2 / burst window: confirm stack and 6s stellar buff timings.
4. Catalyst weapons: Widsith phases, Sacrificial Jade, Thousand Floating Dreams.
5. Remaining artifact sets: Gilded Dreams, Noblesse, Tenacity, Scarlet Proof,
   A Day Carved From Rising Winds.

