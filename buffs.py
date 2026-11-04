CONDITIONAL_CONSTANT_BUFFS = {
    # Artifact Buffs
    "Gilded Dreams":{
        "em": 100.0,
        "atk_percent": 0.140,
    },
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
    "Odette Snow Swan's Dream level 10": {
        "stellar_bonus" : 0.50,
    },
    "Odette Snow Swan's Dream level 13": {
        "stellar_bonus" : 0.62,
    },
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
    "Exaiphanes Blade":{
        "atk_percent": [0.16, 0.20, 0.24, 0.32, 0.40],
    },
    "The Widsith (Average)": {
        "atk_percent": [0.60/3, 0.75/3, 0.90/3, 1.05/3, 1.20/3],
        "elemental_bonus": [0.48/3, 0.60/3, 0.72/3, 0.84/3, 0.96/3],
        "em": [240/3, 300/3, 360/3, 420/3, 480/3],
    },
    "The Widsith (All EM)": {
        "em": [240, 300, 360, 420, 480],
    },
    "Breezeborne Refrain":{
        "atk_percent": [0.20, 0.25, 0.30, 0.35, 0.40],
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
    "A Thousand Floating Dreams":{
        "em": [40.0, 42.0, 44.0, 46.0, 48.0],
    },
    "Thrilling Tales of Dragon Slayers":{
        "atk_percent": [0.24, 0.30, 0.36, 0.42, 0.48],
    },
    "Starsealed Edict Constant":{
        "em": [48.0, 60.0, 72.0, 84.0, 96.0],
    },
    "Whitelake Frostfeather":{
        "crit_dmg":[0.50, 0.65, 0.80, 0.95, 1.10],
    },
    "Finality of the Deep":{
        "atk_percent":[0.12, 0.15, 0.18, 0.21, 0.24],
    },
    "Azurelight":{
        "atk_percent":[0.24, 0.30, 0.36, 0.42, 0.48],
    },
    "Breezeborne Refrain":{
        "stellar_bonus": [0.24, 0.30, 0.36, 0.42, 0.48],
    }
    
}

CONDITIONAL_NON_CONSTANT_BUFFS = {
    ## Mizuki
    # Mizuki Skill Swirl Bonus: dynamic talent scaling off of Mizuki's EM
    "Mizuki Skill": {
        "caster": "Mizuki",
        "target_stat": "stellar_bonus",
        "compute": lambda stats, ref=1, factor=0.045: stats.get("em", 0.0) * factor,
    },
    # VBTD 2: 10% of Mizuki's EM shared to the party during DDS
    "Mizuki VBTD EM Share": {
        "caster": "Mizuki",
        "target_stat": "em",
        "compute": lambda stats, ref=1: stats.get("em", 0.0) * 0.10,
    },
    "Mizuki C2 Pyro": {
        "caster": "Mizuki",
        "target_stat": "pyro_bonus",
        "compute": lambda stats, ref=1: stats.get("em", 0.0) * 0.0004,
    },
    "Mizuki C2 Hydro": {
        "caster":"Mizuki",
        "target_stat": "hydro_bonus",
        "compute": lambda stats, ref=1: stats.get("em", 0.0) * 0.0004,
    },
    "Mizuki C2 Cryo": {
        "caster":"Mizuki",
        "target_stat": "cryo_bonus",
        "compute": lambda stats, ref=1: stats.get("em", 0.0) * 0.0004,
    },
    "Mizuki C2 Electro": {
        "caster":"Mizuki",
        "target_stat": "electro_bonus",
        "compute": lambda stats, ref=1: stats.get("em", 0.0) * 0.0004,
    },
    "Mizuki C6 EM CR": {
        "caster": "Mizuki",
        "target_stat": "crit_rate",
        "compute": lambda stats, ref=1: min(max((stats.get("em", 0.0) - 500.0), 0.0) * 0.0004, 0.20),
    },
    "Mizuki C6 EM CD": {
        "caster": "Mizuki",
        "target_stat": "crit_dmg",
        "compute": lambda stats, ref=1: min(max((stats.get("em", 0.0) - 500.0), 0.0) * 0.0016, 0.80),
    },

    ##Aether
    # Aether A4: EM = 8% of his ATK up to 160
    "Aether A4": {
        "caster":"Aether",
        "target_stat": "em",
        "compute": lambda stats, ref=1: min(0.08 * ((stats["base_atk"] * (1.0 + stats["atk_percent"])) + stats["atk_flat"]), 160.0),
    },
    "Aether_jubilee": {
        "caster":"Aether",
        "target_stat": "jubilee_mult",
        "compute": lambda stats, ref=1: min(0.000035 * ((stats["base_atk"] * (1.0 + stats["atk_percent"])) + stats["atk_flat"]), 0.07),
    },
    #Odette
    "Odette_jubilee": {
        "caster":"Odette",
        "target_stat": "jubilee_mult",
        "compute": lambda stats, ref=1: min(0.00007 * ((stats["base_atk"] * (1.0 + stats["atk_percent"])) + stats["atk_flat"]), 0.14),
    },
    # Odette Burst: 6s buff for HERSELF ONLY that raises her stellar_bonus.
    # The talent-scaled value comes from skill_scalings (Snow Swan's Dream),
    # resolved in resolve_active_buffs and injected via the `factor` arg.
    "Odette Burst": {
        "caster":"Odette",
        "target_stat": "stellar_bonus",
        "compute": lambda stats, ref=1, factor=0.0: factor,
    },
    # Odette A4: mv_increase on ALL her stellar attack motion values
    # (Skill_stellar, plume_stellar, wing_stellar): 1 + 0.015% of her ATK past
    # 1000, capped at 1.30 (at 3000 ATK). Uses the same initial-ATK basis as jubilee.
    "Odette A4": {
        "caster":"Odette",
        "target_stat": "stellar_mv_mult",
        "compute": lambda stats, ref=1: min(1.0 + 0.00015 * max(0.0,
            (stats.get("base_atk", 0.0) * (1.0 + stats.get("atk_percent", 0.0))) + stats.get("atk_flat", 0.0) - 1000.0), 1.30),
    },
    # Faruzan C6: talent-scaled party anemo_bonus (from skill_scalings "Anemo DMG
    # Bonus", 18%–38.25% by burst level). Value injected via the `factor` arg.
    "Faruzan C6 Anemo Bonus": {
        "caster":"Faruzan",
        "target_stat": "anemo_bonus",
        "compute": lambda stats, ref=1, factor=0.0: factor,
    },
    # Sucrose A4: windowed (8s) share of 20% of her FLAT EM to the OTHERS.
    # The amount is computed in resolve_active_buffs via compute_flat_em (special-case).
    "Sucrose A4 Share": {
        "caster":"Sucrose",
        "target_stat": "em",
        "compute": lambda stats, ref=1: 0.0,
    },

    #Weapons
    # Wandering Evenstar: Gain 24% of EM as ATK
    "Wandering Evenstar Self": {
        "caster": "User",
        "target_stat": "atk_flat",
        "compute": lambda stats, ref=1: stats.get("em", 0.0) * [0.24, 0.30, 0.36, 0.42, 0.48][ref - 1],
    },
    # Wandering Evenstar Party: Gain 7.2% of EM as ATK
    "Wandering Evenstar Party": {
        "caster": "User",
        "target_stat": "atk_flat",
        "compute": lambda stats, ref=1: stats.get("em", 0.0) * [0.072, 0.09, 0.108, 0.126, 0.144][ref - 1],
    },
}

# Sucrose's A4 EM share is now a windowed buff (see "Sucrose A4 Share" in
# CONDITIONAL_NON_CONSTANT_BUFFS), so the permanent team-share table is empty.
TEAM_SHARE_BUFFS = {}

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
    "Breezeborne Refrain":{
        
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
    }
    

}