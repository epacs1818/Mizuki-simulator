# Genshin Impact Talent Multiplier Library

MULTIPLIER_SEQUENCES = {
    "Elemental 1": [1.0, 1.075, 1.150, 1.250, 1.325, 1.400, 1.500, 1.600, 1.700, 1.800, 1.900, 2.000, 2.125],
    "Physical 1": [1.0, 1.081, 1.163, 1.279, 1.360, 1.453, 1.581, 1.709, 1.837, 1.977, 2.116, 2.256, 2.395],
    "Effect Flat": [1.0, 1.100, 1.208, 1.325, 1.450, 1.583, 1.725, 1.875, 2.033, 2.200, 2.375, 2.559, 2.750]
}

def get_scaled_list(base: float, sequence_name: str, multiplier: float = 1.0) -> list:
    multipliers = MULTIPLIER_SEQUENCES[sequence_name]
    return [round(base * m * multiplier, 4) for m in multipliers]

# Character Skills Database
CHARACTER_SKILLS = {
    "Aether": {
        "Charged Attack": {
            "C1_Hit": {
                "scaling": get_scaled_list(55.9, "Physical 1"),
                "mv_increase": 1.4
            },
            "C2_Hit": {
                "scaling": get_scaled_list(60.7, "Physical 1"),
                "mv_increase": 1.4
            }
        },
        "Normal Attack": {
            "N1": {
                "scaling": get_scaled_list(44.5, "Physical 1"),
            }
        },
        "Skill": {
            "Cast": {
                "scaling": get_scaled_list(91.68, "Elemental 1"),
            },
            "Skill Proc": {
                "scaling": get_scaled_list(21.39, "Elemental 1"),
            }
        },
        "Burst (Stellar Swirl)": {
            "Ice Javelin Single Strike DMG": {
                "scaling": get_scaled_list(55.13, "Elemental 1"),
                # Per-stack MV increase of the Ice Javelin, applied multiplicatively as
                # base * (1 + stacks * per_stack). The 2.76 base yields 5.86% per stack
                # at talent 13 (2.76 * 2.125 = 5.865), i.e. ~46.9% at 8 stacks.
                # NOTE: additive vs. multiplicative application is PENDING game-test
                # verification and can be toggled in abilities.get_ability_motion_value.
                "mv_per_stack": get_scaled_list(2.76, "Elemental 1"),
            }
        }
    },
    "Mizuki": {
        "Skill": {
            "Skill DMG": {
                "scaling": get_scaled_list(57.74, "Elemental 1"),
            },
            "Continuous Attack DMG": {
                "scaling": get_scaled_list(44.91, "Elemental 1"),
            },
            "Elemental Mastery-Based Swirl DMG Increase": {
                "scaling": [0.18, 0.21, 0.24, 0.27, 0.3, 0.33, 0.36, 0.39, 0.42, 0.45, 0.48, 0.51, 0.54],
            }
        },
        "Burst": {
            "Skill DMG": {
                "scaling": get_scaled_list(94.08, "Elemental 1"),
            },
            "Munen Shockwave DMG": {
                "scaling": get_scaled_list(70.56, "Elemental 1"),
            }
        }
    },
    "Odette": {
        "Skill": {
            "Skill DMG": {
                "scaling": get_scaled_list(108.08, "Elemental 1"),
            },
            "Coda at Dawn's Tolling DoT": {
                "scaling": get_scaled_list(95.84, "Elemental 1"),
            },
            "Coda at Dawn's Tolling Stellar Swirl DMG": {
                "scaling": get_scaled_list(458.64, "Elemental 1"),
            },
            "Plume Dance Move DMG": {
                "scaling": get_scaled_list(43.04, "Elemental 1"),
            },
            "Plume Dance Move Stellar Swirl DMG": {
                "scaling": get_scaled_list(40.53, "Elemental 1"),
            },
            "Wing Dance Move DMG": {
                "scaling": get_scaled_list(51.46, "Elemental 1"),
            },
            "Wing Dance Move Stellar Swirl DMG": {
                "scaling": get_scaled_list(48.46, "Elemental 1"),
            }
        },
        "Burst": {
            "Slash DMG (Per Hit)": {
                "scaling": get_scaled_list(110.18, "Elemental 1"),
            },
            "Final Slash DMG": {
                "scaling": get_scaled_list(170.27, "Elemental 1"),
            },
            "Snow Swan's Dream Stellar Glimmer Reaction DMG Bonus": {
                "scaling": [14, 18, 22, 26, 30, 34, 38, 42, 46, 50, 54, 58, 62],
            }
        }
    },
    "Faruzan": {
        "Skill": {
            "Skill DMG": {
                "scaling": get_scaled_list(148.8, "Elemental 1"),
            },
            "Pressurized Collapse Vortex DMG": {
                "scaling": get_scaled_list(108.0, "Elemental 1"),
            }
        },
        "Burst": {
            "Skill DMG": {
                "scaling": get_scaled_list(377.6, "Elemental 1"),
            },
            "Anemo DMG Bonus": {
                "scaling": [18.0, 19.35, 20.7, 22.5, 23.85, 25.2, 27.0, 28.8, 30.6, 32.4, 34.2, 36.0, 38.25],
            }
        }
    },
    "Sucrose": {
        "Skill": {
            "Skill DMG": {
                "scaling": get_scaled_list(211.2, "Elemental 1"),
            }
        },
        "Burst": {
            "DoT": {
                "scaling": get_scaled_list(148.0, "Elemental 1"),
            },
            "Additional Elemental DMG": {
                "scaling": get_scaled_list(44.0, "Elemental 1"),
            }
        }
    },
    "Diona": {
        "Skill": {
            "Icy Paw DMG": {
                "scaling": get_scaled_list(41.92, "Elemental 1"),
            }
        },
        "Burst": {
            "Skill DMG": {
                "scaling": get_scaled_list(80.0, "Elemental 1"),
            },
            "Continuous Field DMG": {
                "scaling": get_scaled_list(52.64, "Elemental 1"),
            }
        }
    }
}
