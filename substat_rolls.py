"""True substat roll values and the "hidden decimal" resolver.

The game DISPLAYS substats rounded (one decimal for % stats, whole numbers for
EM and the flat stats) but every roll is an exact 2-decimal value from a fixed
per-stat table. A piece showing "13.2% Crit Rate" therefore really holds some
combination of 2.72 / 3.11 / 3.50 / 3.89 rolls (one of each sums to 13.22, which
the game displays as 13.2).

`snap_substat()` recovers the real value behind a displayed number:

  * the display interval is the rounding band of the typed value,
  * every multiset of 1..MAX_ROLLS_PER_SUBSTAT rolls whose sum falls inside that
    band is a candidate,
  * when several candidates exist the one closest to the displayed number wins
    (ties go to the combination with fewer rolls),
  * a value no roll combination can produce is returned untouched.

Stats without a roll table (mains, Crit Value, element bonuses, ...) come back
unchanged, so calling it is always safe.
"""

from functools import lru_cache
from itertools import combinations_with_replacement

# 5-star substat roll values per tier: 70% / 80% / 90% / 100%.
ROLL_VALUES_5STAR = {
    "hp_percent":  (4.08, 4.66, 5.25, 5.83),
    "atk_percent": (4.08, 4.66, 5.25, 5.83),
    "def_percent": (5.10, 5.83, 6.56, 7.29),
    "em":          (16.32, 18.65, 20.98, 23.31),
    "er":          (4.53, 5.18, 5.83, 6.48),
    "crit_rate":   (2.72, 3.11, 3.50, 3.89),
    "crit_dmg":    (5.44, 6.22, 6.99, 7.77),
    "hp_flat":     (209.13, 239.00, 268.88, 298.75),
    "atk_flat":    (13.62, 15.56, 17.51, 19.45),
    "def_flat":    (16.20, 18.52, 20.83, 23.15),
}

# A substat starts with its +0 roll and can absorb all 5 upgrades of a +20
# 5-star piece, so at most 6 rolls of one stat can sit on a single piece.
MAX_ROLLS_PER_SUBSTAT = 6

# How the GAME DISPLAYS each substat: % stats show one decimal, EM and the
# flat stats show whole numbers. A real roll sum counts as "the same value"
# as the user's input when both are displayed identically.
_DISPLAY_DECIMALS = {
    "hp_percent": 1, "atk_percent": 1, "def_percent": 1,
    "er": 1, "crit_rate": 1, "crit_dmg": 1,
    "em": 0, "hp_flat": 0, "atk_flat": 0, "def_flat": 0,
}


@lru_cache(maxsize=None)
def _roll_totals(stat_key):
    """{exact total: fewest rolls that reach it} for one stat (cached).

    Every total a 5-star piece can actually hold, so a lookup never has to
    re-enumerate combinations. Cheap: at most 126 multisets per stat.
    """
    totals = {}
    for count in range(1, MAX_ROLLS_PER_SUBSTAT + 1):
        for combo in combinations_with_replacement(ROLL_VALUES_5STAR[stat_key], count):
            total = round(sum(combo), 2)
            if total not in totals or count < totals[total]:
                totals[total] = count
    return totals


def snap_substat(stat_key, displayed_value, max_rolls: int = MAX_ROLLS_PER_SUBSTAT):
    """Displayed value -> (true value, roll count).

    "True value" is the exact 2-decimal total of the roll combination the game
    would display as `displayed_value`. Returns (displayed_value, 0) when the
    stat has no roll table or no combination lands in the display band, so an
    unrecognised number is passed through instead of being invented.
    """
    try:
        displayed = float(displayed_value)
    except (TypeError, ValueError):
        return displayed_value, 0
    if stat_key not in ROLL_VALUES_5STAR or not displayed > 0.0:
        return displayed, 0

    # The game rounds to N decimals, so anything within half a display step is
    # shown as the typed number.
    half_step = 0.5 * 10.0 ** -_DISPLAY_DECIMALS.get(stat_key, 1)
    candidates = [
        (total, count)
        for total, count in _roll_totals(stat_key).items()
        if count <= max_rolls and abs(total - displayed) <= half_step + 1e-9
    ]
    if not candidates:
        return displayed, 0
    total, count = min(candidates, key=lambda candidate: (abs(candidate[0] - displayed),
                                                         candidate[1]))
    return total, count
