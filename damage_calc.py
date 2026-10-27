def calculate_damage(hit, final_stats, enemy_stats, category):
    """
    Dispatcher function that routes damage calculation based on the damage category.
    """
    if category == "standard":
        return calculate_standard_damage(hit, final_stats, enemy_stats)
    elif category == "stellar":
        return calculate_stellar_damage(hit, final_stats, enemy_stats)
    elif category == "stellar_reaction":
        return calculate_stellar_reaction_damage(hit, final_stats, enemy_stats)
    else:
        raise ValueError(f"Unknown damage category: {category}")


def calculate_standard_damage(hit, final_stats, enemy_stats):
    """
    Calculates Standard Damage using 6 multipliers:
    1. Base Damage (+ Quills)
    2. Bonus Multiplier
    3. Elevation Multiplier
    4. Crit Multiplier
    5. DEF Multiplier
    6. RES Multiplier
    """
    # TODO: Implement Base Damage & Quills
    # TODO: Implement Bonus Multiplier
    # TODO: Implement Elevation Multiplier
    # TODO: Implement Crit Multiplier
    # TODO: Implement DEF Multiplier
    # TODO: Implement RES Multiplier
    pass


def calculate_stellar_damage(hit, final_stats, enemy_stats):
    """
    Calculates Stellar Damage using 5 multipliers (Bonus Multiplier does not apply to quills):
    1. Base Damage (+ Quills)
    2. Bonus Multiplier (Excludes Quills)
    3. Elevation Multiplier
    4. Crit Multiplier
    5. RES Multiplier
    """
    # TODO: Implement Base Damage & Quills
    # TODO: Implement Bonus Multiplier (excluding quills rule)
    # TODO: Implement Elevation Multiplier
    # TODO: Implement Crit Multiplier
    # TODO: Implement RES Multiplier
    pass


def calculate_stellar_reaction_damage(hit, final_stats, enemy_stats):
    """
    Calculates Stellar Reaction Damage using 6 multipliers (Bonus applies to quills here):
    1. Base Damage (+ Quills)
    2. Bonus Multiplier (Applies to Quills)
    3. Elevation Multiplier
    4. Contribution Multiplier
    5. Crit Multiplier
    6. RES Multiplier
    """
    # TODO: Implement Base Damage & Quills
    # TODO: Implement Bonus Multiplier (including quills rule)
    # TODO: Implement Elevation Multiplier
    # TODO: Implement Contribution Multiplier
    # TODO: Implement Crit Multiplier
    # TODO: Implement RES Multiplier
    pass