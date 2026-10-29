CONDITIONAL_CONSTANT_BUFFS = {
    # Artifact Buffs
    "Gilded Dreams":{
        "em": 100.0,
        "atk_percent": 0.140
    },
    "Instructor": {
        "em": 120.0
    },
    "Heart Of The Furnace (Self)": {
        "stellar_bonus": 0.500
    },
    "Heart Of The Furnace (Party)": {
        "atk_percent": 0.120
    },
    "Noblesse Oblige": {
        "atk_percent": 0.200
    },
    "Tenacity Of The Millelith": {
        "atk_percent": 0.200
    },
    "A Day Carved From Rising Winds":{
        "atk_percent": 0.250
    },
    "Scarlet Proof": {
        "crit_rate": 0.160,
        "stellar_bonus": 0.400
    },
    # Characters' Buffs
    #Mizuki
    "Mizuki A4": {
        "em": 100.0
    },
    "Mizuki C2": {
        "pyro_shred":0.20,
        "hydro_shred":0.20,
        "cryo_shred":0.20,
        "electro_shred":0.20,
        "anemo_shred": 0.20
    },
    "Mizuki C6 Stellar Crit": {
        "crit_rate" : 0.100,
        "crit_dmg" : 0.200
    },

    #Aether
    "Aether C2 Buff Initial":{
        "em": 60.0
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
        "anemo_shred": 0.20
    },
    "Odette Snow Swan's Dream level 10": {
        "stellar_bonus" : 0.50
    },
    "Odette Snow Swan's Dream level 13": {
        "stellar_bonus" : 0.62
    },
    "Odette C6 self":{
        "elevation_mult": 0.20
    },
    "Odette C6 party":{
        "elevation_mult": 0.25
    },
    
    #Faruzan
    "Faruzan C6 Buff":{
        "anemo_bonus": 0.385,
        "crit_dmg" : 0.400
    },
    "Faruzan C6 Debuff":{
        "anemo_shred": 0.30
    },
    
    #Sucrose
    "Sucrose A2":{
        "em":50.0
    },
    "Sucrose C6":{
        "cryo_bonus":0.20
    },

    #Diona
    "Diona C6":{
        "em": 200.0,
        "stellar_bonus":0.40
    },
    
    # Team Buffs
    "Cryo Resonance": {
        "crit_rate": 0.15
    },

    #WEAPONS
    "Exaiphanes Blade":{
        "atk_percent": [0.16, 0.20, 0.24, 0.32, 0.40]
    },
    "The Widsith (Average)": {
        "atk_percent": [0.60/3, 0.75/3, 0.90/3, 1.05/3, 1.20/3],
        "elemental_bonus": [0.48/3, 0.60/3, 0.72/3, 0.84/3, 0.96/3],
        "em": [240/3, 300/3, 360/3, 420/3, 480/3]
    },
    "The Widsith (All EM)": {
        "em": [240, 300, 360, 420, 480]
    },
    "Breezeborne Refrain":{
        "atk_percent": [0.20, 0.25, 0.30, 0.35, 0.40]
    },
    "Sacrificial Jade":{
        "hp_percent": [0.32, 0.40, 0.48, 0.56, 0.64],
        "em": [40.0, 50.0, 60.0, 70.0, 80.0]
    }
    
}

CONDITIONAL_NON_CONSTANT_BUFFS = {
    ## Mizuki
    #"Mizuki skill lv 10":{
    #    "stellar_bonus": 0 #(4.5% of her EM)%
    #},
    #"Mizuki skill lv 13":{
    #    "stellar_bonus": 0 # (5.4% of her EM)%
    #},
    #"Mizuki Witch": {
    #    "em_mult":1.10 #10% of her EM
    #},

    ##Aether
    #"Aether A4": {
    #    "em = 8% of his attack up to 160 "   
    #}
    #"Aether_jubilee":{"jubilee_mult":},    #0.35%% of his atk up to 7% (2000 ATK)

    #Odette
    #"Odette_jubilee":{"jubilee_mult":},    #0.7%% of her atk up to 14% (2000 ATK)
    #"Odette_A4":{"motion_value_multiplier":}   #For every 100 ATK Odette has over 1,000, her Stellar Glimmer DMG is additionally
    #                                           #increased by 1.5% of the original DMG. She can deal up to 30% more additional DMG in this way.
    #Sucrose
    #"Sucrose A4":{
    #    "em":                              #20 % of Sucrose's EM to everyone"
    #}
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
        
    },
    "Breezeborne Refrain":{
        
    },
    

}