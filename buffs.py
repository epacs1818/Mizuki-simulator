CONDITIONAL_CONSTANT_BUFFS = {
    # Artifact Buffs
    # NOTE: Gilded Dreams has no constant buff entry. Its 2pc EM is permanent
    # (artifacts.py) and its 4pc buff is dynamic/party-composition based, so it
    # lives in CONDITIONAL_NON_CONSTANT_BUFFS ("Gilded Dreams ATK"/"EM").
    "Instructor": {
        "em": 120.0,
    },
    # HotF triggers when the holder deals Stellar DMG or triggers a swirl (12s, refresh).
# The USER (holder) gains +12% ATK; the WHOLE PARTY gains +50% stellar_bonus.
    "Heart Of The Furnace (Self)": {
        "atk_percent": 0.120,
    },
    "Heart Of The Furnace (Party)": {
        "stellar_bonus": 0.500,
    },
    "Noblesse Oblige": {
        "atk_percent": 0.200,
    },
    "Tenacity Of The Millelith": {
        "atk_percent": 0.200,
    },
    "A Day Carved From Rising Winds":{
        "atk_percent": 0.250,
    },
    "Scarlet Proof": {
        "crit_rate": 0.160,
        "stellar_bonus": 0.400,
    },
    "Viridescent Venerer": {
        "cryo_shred": 0.40,
    },
    # Characters' Buffs
    #Mizuki
    "Mizuki A4": {
        "em": 100.0,
    },
    "Mizuki C2": {
        "pyro_shred":0.20,
        "hydro_shred":0.20,
        "cryo_shred":0.20,
        "electro_shred":0.20,
        "anemo_shred": 0.20,
    },
    #"Mizuki C6 Stellar Crit": {
    #    "crit_rate" : 0.100,
    #    "crit_dmg" : 0.200,
    #},

    #Aether
    "Aether C2 Buff Initial":{
        "em": 60.0,
    },
    # C2 Enhanced grants the active character another 60 EM (total 120 with Basic).
    "Aether C2 Buff Enhanced":{
        "em": 60.0,
    },

    #Odette
    "Odette C2": {
        "cryo_shred": 0.20,
        "anemo_shred": 0.20,
    },
    # NOTE: Odette's "Snow Swan's Dream" has no fixed-value entries. It is the
    # talent-scaled "Odette Burst" descriptor in CONDITIONAL_NON_CONSTANT_BUFFS
    # (path into skill_scalings), self-only, 20s from her burst cast hit.
    "Odette C6 self":{
        "elevation_mult": 0.20,
    },
    "Odette C6 party":{
        "elevation_mult": 0.25,
    },
    
    #Faruzan
    # +40% crit_dmg, applied only to ANEMO-element hits (faruzan_buff_state is gated
    # to anemo events in the timeline). The talent-scaled party anemo_bonus is
    # provided separately by "Faruzan C6 Anemo Bonus" (non_constant).
    "Faruzan C6 Buff":{
        "crit_dmg" : 0.400,
    },
    "Faruzan C6 Debuff":{
        "anemo_shred": 0.30,
    },
    
    #Sucrose
    # A1: after Sucrose triggers a swirl, non-Anemo party members get +50 EM for 8s.
    "Sucrose A1":{
        "em":50.0,
    },
    "Sucrose C6":{
        "cryo_bonus":0.20,
    },

    #Anastasya
    # A1: after her skill cast hits, OTHER party members gain 16% crit DMG for 19s.
    "Anastasya A1":{
        "crit_dmg": 0.16,
    },
    # A4: while she is in the party, STELLAR SWIRL REACTION damage gains +0.15
    # jubilee (a separate key: stellar DMG is unaffected).
    "Anastasya A4":{
        "reaction_jubilee_mult": 0.15,
    },

    #Diona
    "Diona C6":{
        "em": 200.0,
        "stellar_bonus":0.40,
    },
    
    # Team Buffs
    "Cryo Resonance": {
        "crit_rate": 0.15,
    },

    #WEAPONS
    # NOTE: these weapon/passive values are kept as a reference table only. A
    # weapon buff is applied by the engine ONLY once timeline.evaluate_timeline()
    # emits its state flag (see FLAG_TO_BUFFS). Widsith / TTDS / A Thousand
    # Floating Dreams / Wandering Evenstar / Breezeborne are not triggered yet and
    # are tracked in text/Implementation_Backlog.md.
    "Exaiphanes Blade":{
        "atk_percent": [0.16, 0.20, 0.24, 0.32, 0.40],
    },
    # The Widsith (Average): the 3-way roll modelled as one third of every outcome
    # at the same time. Per-element DMG bonuses are STANDARD-damage only (they never
    # enter stellar or stellar-reaction damage), so they are written out element by
    # element - there is no generic "elemental_bonus" stat.
    "The Widsith (Average)": {
        "atk_percent": [0.20, 0.25, 0.30, 0.35, 0.40],
        "em":          [80.0, 100.0, 120.0, 140.0, 160.0],
        "pyro_bonus":    [0.16, 0.20, 0.24, 0.28, 0.32],
        "hydro_bonus":   [0.16, 0.20, 0.24, 0.28, 0.32],
        "cryo_bonus":    [0.16, 0.20, 0.24, 0.28, 0.32],
        "electro_bonus": [0.16, 0.20, 0.24, 0.28, 0.32],
        "anemo_bonus":   [0.16, 0.20, 0.24, 0.28, 0.32],
        "geo_bonus":     [0.16, 0.20, 0.24, 0.28, 0.32],
        "dendro_bonus":  [0.16, 0.20, 0.24, 0.28, 0.32],
    },
    # The Widsith (All EM): the same weapon with the roll always landing on EM.
    "The Widsith (All EM)": {
        "em": [240.0, 300.0, 360.0, 420.0, 480.0],
    },
    "Breezeborne Refrain":{
        "stellar_bonus": [0.24, 0.30, 0.36, 0.42, 0.48],
    },
    "Sacrificial Jade":{
        "hp_percent": [0.32, 0.40, 0.48, 0.56, 0.64],
        "em": [40.0, 50.0, 60.0, 70.0, 80.0],
    },
    "Sunny Morning Sleep-In Swirl": {
        "em": [120.0, 150.0, 180.0, 210.0, 240.0],
    },
    "Sunny Morning Sleep-In Skill": {
        "em": [96.0, 120.0, 144.0, 168.0, 192.0],
    },
    "Sunny Morning Sleep-In Burst": {
        "em": [32.0, 40.0, 48.0, 56.0, 64.0],
    },
    # NOTE: A Thousand Floating Dreams has no buff entry. Its description effect is
    # PERMANENT and party-composition dependent, so it lives in weapons.py
    # ("party_stats") and is applied by stats_calc.apply_weapon_party_stats().
    "Thrilling Tales of Dragon Slayers":{
        "atk_percent": [0.24, 0.30, 0.36, 0.42, 0.48],
    },
    "Starsealed Edict Constant":{
        "em": [48.0, 60.0, 72.0, 84.0, 96.0],
    },
    # Whitelake Frostfeather: the payoff is STELLAR crit DMG only, and only while
    # at the maximum 3 stacks. (The per-stack ATK% lives in STACK_BUFFS.)
    "Whitelake Frostfeather (3 stacks)":{
        "stellar_crit_dmg":[0.50, 0.65, 0.80, 0.95, 1.10],
    },
    "Finale Of The Deep":{
        "atk_percent":[0.12, 0.15, 0.18, 0.21, 0.24],
    },
    "Elegy for the End":{
        "atk_percent":[0.20, 0.25, 0.30, 0.35, 0.40],
        "em":[100.0, 125.0, 150.0, 175.0, 200.0],
    },
    # New Tsaritsa set: while stacked, the holder gains crit rate on CRYO hits
    # (the timeline only flags it on Cryo events, like Faruzan C6 does for Anemo)
    # and stellar crit rate everywhere.
    "New Tsaritsa set CR":{
        "crit_rate": 0.20,
    },
    "New Tsaritsa set Stellar CR":{
        "stellar_crit_rate": 0.20,
    },
    "Silverdawn":{
        "atk_percent":[0.40, 0.52, 0.64, 0.76, 0.88],
        "stellar_crit_dmg":[0.40, 0.52, 0.64, 0.76, 0.88],
    }
}

CONDITIONAL_NON_CONSTANT_BUFFS = {
    # ------------------------------------------------------------------
    # Every entry below is DATA. stats_calc.evaluate_dynamic_buff() resolves it:
    #
    #   basis           "em" | "flat_em" | "atk" | "talent"  (what it scales from)
    #                     em      = caster's initial EM (base + weapon + artifacts)
    #                     flat_em = caster's FLAT EM basis (never % shares)
    #                     atk     = caster's resolved ATK from the initial stats
    #                     talent  = the value IS a talent scaling
    #   ratio           multiplier on the basis (scalar, or [R1..R5] per refinement)
    #   ratio_from_talent  derive the ratio from a talent scaling instead
    #   offset          subtract from the basis before scaling (e.g. 500 EM)
    #   floor           constant added after scaling (e.g. 1.0 for a mv multiplier)
    #   cap             optional upper clamp
    #   path            (character, category, key) into skill_scalings
    #   divisor         talent divisor: 100 -> percent form, 1000 -> ratio form
    #
    #   value = min(floor + ratio * max(basis - offset, 0), cap)
    #
    # No lambdas: a buff that is not reachable from FLAG_TO_BUFFS can no longer
    # hide behind a closure that silently returns 0.
    # ------------------------------------------------------------------
    ## Mizuki
    # Skill swirl bonus: talent-scaled % of her FLAT EM -> party stellar_bonus
    # (single source of truth for the scaling lives in skill_scalings.py).
    "Mizuki Skill": {
        "caster": "Mizuki",
        "target_stat": "stellar_bonus",
        "basis": "flat_em",
        "ratio_from_talent": {"path": ("Mizuki", "Skill", "Elemental Mastery-Based Swirl DMG Increase"),
                              "divisor": 1000.0},
    },
    # VBTD 2: 10% of Mizuki's FLAT EM shared to the party during DDS.
    "Mizuki VBTD EM Share": {
        "caster": "Mizuki",
        "target_stat": "em",
        "basis": "flat_em",
        "ratio": 0.10,
    },
    # C2: 0.04% of her FLAT EM as PHEC elemental bonus (no anemo bonus).
    # "Flat" = base + weapon + artifacts + flat buffs (A4, Aether C2, Instructor...);
    # percentage shares (her VBTD 10%, Sucrose A4) never feed it, exactly like
    # C6-2 and the skill swirl bonus.
    "Mizuki C2 Pyro": {
        "caster": "Mizuki", "target_stat": "pyro_bonus", "basis": "flat_em", "ratio": 0.0004,
    },
    "Mizuki C2 Hydro": {
        "caster": "Mizuki", "target_stat": "hydro_bonus", "basis": "flat_em", "ratio": 0.0004,
    },
    "Mizuki C2 Cryo": {
        "caster": "Mizuki", "target_stat": "cryo_bonus", "basis": "flat_em", "ratio": 0.0004,
    },
    "Mizuki C2 Electro": {
        "caster": "Mizuki", "target_stat": "electro_bonus", "basis": "flat_em", "ratio": 0.0004,
    },
    # C6 part 2: +0.04% CR / +0.16% CD per point of FLAT EM above 500,
    # capped at 20% / 80% (reached at 1000 flat EM).
    "Mizuki C6 EM CR": {
        "caster": "Mizuki", "target_stat": "crit_rate",
        "basis": "flat_em", "ratio": 0.0004, "offset": 500.0, "cap": 0.20,
    },
    "Mizuki C6 EM CD": {
        "caster": "Mizuki", "target_stat": "crit_dmg",
        "basis": "flat_em", "ratio": 0.0016, "offset": 500.0, "cap": 0.80,
    },

    ## Aether
    # A4: EM = 8% of his ATK, capped at 160.
    "Aether A4": {
        "caster": "Aether", "target_stat": "em",
        "basis": "atk", "ratio": 0.08, "cap": 160.0,
    },
    # Jubilee: party jubilee_mult = 0.0035% of his ATK, capped at 7%.
    "Aether_jubilee": {
        "caster": "Aether", "target_stat": "jubilee_mult",
        "basis": "atk", "ratio": 0.000035, "cap": 0.07,
    },
    ## Odette
    # Jubilee: party jubilee_mult = 0.007% of her ATK, capped at 14%.
    "Odette_jubilee": {
        "caster": "Odette", "target_stat": "jubilee_mult",
        "basis": "atk", "ratio": 0.00007, "cap": 0.14,
    },
    # Burst: 6s SELF stellar_bonus, talent-scaled (Snow Swan's Dream).
    "Odette Burst": {
        "caster": "Odette", "target_stat": "stellar_bonus",
        "basis": "talent",
        "path": ("Odette", "Burst", "Snow Swan's Dream Stellar Glimmer Reaction DMG Bonus"),
    },
    # A4: mv_increase on her stellar attacks = 1 + 0.015% of ATK past 1000,
    # capped at 1.30 (3000 ATK).
    "Odette A4": {
        "caster": "Odette", "target_stat": "stellar_mv_mult",
        "basis": "atk", "ratio": 0.00015, "offset": 1000.0, "floor": 1.0, "cap": 1.30,
    },
    ## Faruzan
    # C6: talent-scaled party anemo_bonus (18%–38.25% by burst level).
    "Faruzan C6 Anemo Bonus": {
        "caster": "Faruzan", "target_stat": "anemo_bonus",
        "basis": "talent",
        "path": ("Faruzan", "Burst", "Anemo DMG Bonus"),
    },
    ## Sucrose
    # A4: windowed (8s) share of 20% of her FLAT EM to the OTHERS.
    "Sucrose A4 Share": {
        "caster": "Sucrose", "target_stat": "em",
        "basis": "flat_em", "ratio": 0.20,
    },
    ## Anastasya
    # Burst cast: the whole party gains stellar_bonus equal to her burst talent
    # scaling. The values in skill_scalings are already decimals (0.275 -> 0.575),
    # so the divisor is 1.0 instead of 100.
    "Anastasya Burst": {
        "caster": "Anastasya", "target_stat": "stellar_bonus",
        "basis": "talent",
        "path": ("Anastasya", "Burst", "To the New World Stellar Glimmer Reaction DMG Increase"),
        "divisor": 1.0,
    },
    # Jubilee passive: identical to Odette's (0.007% of ATK, capped at 14%).
    "Anastasya_jubilee": {
        "caster": "Anastasya", "target_stat": "jubilee_mult",
        "basis": "atk", "ratio": 0.00007, "cap": 0.14,
    },

    ## Artifacts
    # Gilded Dreams: 8s party-composition buff on the holder after they trigger a
    # swirl (8s CD). Same-element allies give ATK%, different-element ones give EM.
    "Gilded Dreams ATK": {
        "caster": "holder:Gilded Dreams", "target_stat": "atk_percent",
        "basis": "allies_same_element", "ratio": 0.14,
    },
    "Gilded Dreams EM": {
        "caster": "holder:Gilded Dreams", "target_stat": "em",
        "basis": "allies_diff_element", "ratio": 50.0,
    },
    ## Weapons
    # Wandering Evenstar: a periodic (10s) self ATK buff worth [24%..48%] of the
    # holder's FLAT EM, stacking to 2. The party version is 30% of that value.
    # These are STACK effects: the stack count comes from the timeline
    # ("evenstar_stacks") and the resolved value is multiplied by it.
    "Wandering Evenstar Self": {
        "caster": "holder:Wandering Evenstar", "target_stat": "atk_flat",
        "basis": "flat_em", "ratio": [0.24, 0.30, 0.36, 0.42, 0.48],
    },
    "Wandering Evenstar Party": {
        "caster": "holder:Wandering Evenstar", "target_stat": "atk_flat",
        "basis": "flat_em", "ratio": [0.072, 0.09, 0.108, 0.126, 0.144],
    },
}

# ---------------------------------------------------------------------------
# DORMANT effects  –  values known, TRIGGER not modelled yet
# ---------------------------------------------------------------------------
# These entries are intentionally unreachable from stats_calc.FLAG_TO_BUFFS.
# They are kept because they are the reference table of in-game values, and
# text/Implementation_Backlog.md tracks what still has to be implemented.
# smoke_test.py asserts that every OTHER catalogue entry IS reachable, so a dead
# entry can never hide again.
DORMANT = {
    # Characters
    "Diona C6",
    "Odette C6 self",
    "Odette C6 party",
}

# Team-share effects (Sucrose A4, Mizuki VBTD2) are ordinary declarative
# non-constant buffs now (see CONDITIONAL_NON_CONSTANT_BUFFS), so there is no
# separate team-share table any more.

PERMANENT_BUFFS = {
    "Aether": {
        "Aether Quest": {
            "base_atk": 10,
            "base_hp": 50,
            "crit_rate": 0.100, 
            "crit_dmg": 0.200,
            "atk_percent": 0.20,
            "hp_percent": 0.20,
            "em":60.0 + 15.0,
            "er":0.200,
            "def_percent":0.20
        }
    },



    "Diona C6": {
        "hp_percent": 0.25
    }

}

STACK_BUFFS = {
    #Characters
    "Odette A1":{
        "stellar_bonus": 0.15   #per stack
    },
    # Aether C6: after Burst consumes Frostglow, each stack gives +5% stellar_bonus
    # to the whole party (0.40 at 8 stacks) for 15s.
    "Aether C6": {
        "stellar_bonus": 0.05    #per stack
    },
    "Odette C2": {
        "atk_percent": 0.07    #per stack of marvelous splendor
    },

    #Weapons
    "Whitelake Frostfeather":{
        "atk_percent": [0.08, 0.10, 0.12, 0.14, 0.16] # per stack
    },
    "Starsealed Edict Stacks": {
        "em": [24.0, 30.0, 36.0, 42.0, 48.0] # per stack
    },
    "New Bough": {
        "atk_percent": [0.06, 0.075, 0.09, 0.105, 0.12], # per stack
        "stellar_bonus": [0.08, 0.10, 0.12, 0.14, 0.16] # per stack
    },
    "Silver Light":{
        "em": [52.0, 65.0, 78.0, 91.0, 104.0] # per stack
    },
  
}