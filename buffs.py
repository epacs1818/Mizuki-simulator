CONDITIONAL_CONSTANT_BUFFS = {
    # Artifact Buffs
    "Gilded Dreams":{
        "em": 100.0,
        "atk_percent": 0.140,
    },
    "Instructor": {
        "em": 120.0,
    },
    "Heart Of The Furnace (Self)": {
        "stellar_bonus": 0.500,
    },
    "Heart Of The Furnace (Party)": {
        "atk_percent": 0.120,
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
    "Mizuki C6 Stellar Crit": {
        "crit_rate" : 0.100,
        "crit_dmg" : 0.200,
    },

    #Aether
    "Aether C2 Buff Initial":{
        "em": 60.0,
    },
    "Aether C2 Buff Enhanced":{
        "em": 120.0,
    },
    "Aether C6": {
        "stellar_bonus": 0.40,
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
    "Faruzan C6 Buff":{
        "anemo_bonus": 0.385,
        "crit_dmg" : 0.400,
    },
    "Faruzan C6 Debuff":{
        "anemo_shred": 0.30,
    },
    
    #Sucrose
    "Sucrose A2":{
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
    # Mizuki Skill: e.g., 4.5% of her total EM as stellar bonus
    "Mizuki Skill": {
        "caster": "Mizuki",
        "target_stat": "stellar_bonus",
        "compute": lambda stats, ref=1: stats.get("em", 0.0) * 0.045,
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
    #"Odette_A4":{"mv_increase":}           #For every 100 ATK Odette has over 1,000, her Stellar Glimmer DMG is additionally
    #                                           #increased by 1.5% of the original DMG. She can deal up to 30% more additional DMG in this way.

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

TEAM_SHARE_BUFFS = {
    "Sucrose A4 Share": {
        "caster": "Sucrose",
        "target_stat": "em",
        "compute": lambda caster_stats: 0.20 * caster_stats.get("em", 0.0)
    },
    "Mizuki Vast Share": {
        "caster": "Mizuki",
        "target_stat": "em",
        "compute": lambda caster_stats: 0.10 * caster_stats.get("em", 0.0)
    }
}

PERMANENT_BUFFS = {
    "Aether": {
        "Aether Quest": {
            "crit_rate": 0.100, 
            "crit_dmg": 0.200,
            "atk_percent": 0.20,
            "hp_percent": 0.20,
            "em":60.0,
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