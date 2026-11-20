"""Gaussian-smoothed damage rate for the results chart.

The per-second bar chart answered "how much damage landed inside second N". This
module answers a different question: "how fast was damage landing *around* time t".
Every damaging HIT is spread over a truncated Gaussian centred on its own timestamp
and the contributions are summed, so a burst reads as one spike instead of being
folded into an arbitrary second bucket.

The curve is a rate (DMG/s), not damage. Each bell is normalised over its full
window, so the area under the curve is the trial's total damage apart from the
tails that fall outside [0, duration] (about 0.8% on the preset trials). The tails
are deliberately NOT renormalised back in: propping up a clipped half-bell turns
the last hit of a trial into a fake edge spike (measured on the flagship preset:
the curve maximum moved from the real burst to t = 118.2 s, 220,975 vs 162,943
DMG/s).

No scipy: a truncated Gaussian sampled on the output grid is all this needs, and
the whole curve is O(hits x window samples) - microseconds for a 120 s trial.
"""

from __future__ import annotations

import numpy as np

# Defaults tuned by eye on the preset trials (see DPS_CURVE_ADVANCED_IDEAS.txt):
# the flagship 6x loop has 587 damaging hits, median gap 0.098 s, max gap 1.23 s.
# 0.70 s reads as smooth peaks and dips instead of raw spikes (the peak lands at
# ~1.6x the overall DPS), and 2.20 s keeps every neighbouring window overlapping
# (a gap only needs truncation >= gap/2, here 0.615 s) with room to spare.
DEFAULT_SIGMA = 0.70
DEFAULT_TRUNCATION = 2.20
DEFAULT_DT = 0.05

# Truncation window in units of sigma. 3.0 would already keep ~99.7% of each
# bell's area; 3.15 leaves a little headroom and makes auto_params() land on the
# shipped DEFAULT_TRUNCATION (3.15 x 0.70 = 2.205 s), so the two never disagree.
TRUNCATION_SIGMAS = 3.15

# A bell sampled with fewer than 4 points per sigma is a triangle at best, and if a
# hit lands on a single sample its peak becomes damage/dt (a 20x overstatement).
MIN_SAMPLES_PER_SIGMA = 4.0


def hit_series(events) -> tuple[np.ndarray, np.ndarray]:
    """(times, damages) of the rows the analytics count as damage.

    Same filter as RotationTimeline.get_analytics_summary(): HIT events whose
    average_damage is a positive number. Non-damage audit rows (swaps, procs) and
    0.0 hits are skipped, so the curve is drawn from exactly the rows the Total
    Damage metric counts.
    """
    times, damages = [], []
    for event in events or ():
        if event.get("event_type") != "HIT":
            continue
        damage = event.get("average_damage") or 0.0
        if damage <= 0:
            continue
        times.append(float(event.get("global_time", 0.0)))
        damages.append(float(damage))
    return (np.asarray(times, dtype=float), np.asarray(damages, dtype=float))


def gap_stats(times) -> dict:
    """Spacing between consecutive damaging hits, in seconds.

    Used for the truncation diagnostics under the chart: a window pair only
    overlaps while the gap between the two hits is at most 2 x truncation, so
    max_gap / 2 is the smallest truncation that leaves no dead zone.
    """
    times = np.sort(np.asarray(times, dtype=float))
    if times.size < 2:
        return {"count": int(times.size), "median": 0.0, "p90": 0.0,
                "p99": 0.0, "max": 0.0, "zero_share": 0.0}
    gaps = np.diff(times)
    return {
        "count": int(times.size),
        "median": float(np.median(gaps)),
        "p90": float(np.percentile(gaps, 90)),
        "p99": float(np.percentile(gaps, 99)),
        "max": float(gaps.max()),
        # Multi-hit procs resolve on one timestamp, so a large share of gaps is 0.
        "zero_share": float((gaps == 0).mean()),
    }


def auto_params(times, duration: float, sigma: float = DEFAULT_SIGMA) -> dict:
    """Default (sigma, truncation, dt) for one trial at the requested *sigma*.

    sigma      : DEFAULT_SIGMA - a burst stays a peak instead of becoming a
                 one-second block, and the peak lands ~1.6x the overall DPS.
    truncation : max(TRUNCATION_SIGMAS x sigma, largest hit gap), capped at 3 s -
                 long enough that no window is cut inside its visible bell and that
                 neighbouring rotations overlap instead of leaving a hard zero.
                 At DEFAULT_SIGMA this is 2.205 s, i.e. DEFAULT_TRUNCATION.
    dt         : sigma / 4, clamped to [0.01, 0.05] s. Deriving dt from the sigma
                 that is actually drawn keeps the bell at >= 4 samples, so the
                 slider value and the rendered width can never disagree.
    """
    gaps = gap_stats(times)
    truncation = min(max(TRUNCATION_SIGMAS * sigma, gaps["max"]), 3.0)
    dt = float(min(max(round(sigma / MIN_SAMPLES_PER_SIGMA, 3), 0.01), 0.05))
    return {"sigma": sigma, "truncation": truncation, "dt": dt, "gaps": gaps,
            "duration": float(duration)}


def gaussian_dps(times, damages, *, sigma: float = DEFAULT_SIGMA,
                 truncation: float = DEFAULT_TRUNCATION, dt: float = DEFAULT_DT,
                 duration: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Damage rate (DMG/s) from a truncated-Gaussian convolution of the hits.

    Each hit contributes ``damage * gaussian(t - t_hit) / dt``, with the bell
    normalised over its full window. A hit whose window pokes out of
    [0, duration] keeps only the visible part of its bell (about 0.8% of the total
    area on the preset trials), so no hit is ever inflated at the trial edges.

    Simultaneous hits are deliberately NOT merged: multi-hit procs resolve on the
    same timestamp, and their bells simply add up.
    """
    times = np.asarray(times, dtype=float)
    damages = np.asarray(damages, dtype=float)
    if times.size == 0 or duration <= 0:
        return np.array([]), np.array([])

    dt = float(dt)
    # Never fewer than 4 samples per bell, and never a window shorter than sigma
    # (a window shorter than ~1 sigma slices through its own peak).
    sigma = max(float(sigma), dt * MIN_SAMPLES_PER_SIGMA)
    truncation = max(float(truncation), sigma)

    grid = np.arange(0.0, duration + dt / 2.0, dt)
    curve = np.zeros_like(grid)

    offsets = np.arange(-truncation, truncation + dt / 2.0, dt)
    kernel = np.exp(-0.5 * (offsets / sigma) ** 2)
    # Normalise the SAMPLED bell to sum 1: a truncated bell holds only
    # erf(truncation / (sigma*sqrt(2))) of the continuous area, and without this
    # the curve would be off by the kernel's sample count.
    kernel /= kernel.sum()

    for t_hit, damage in zip(times, damages):
        start = int(round((t_hit - truncation) / dt))
        first, last = max(start, 0), min(start + kernel.size, grid.size)
        if first >= last:
            continue
        window = kernel[first - start:last - start]
        curve[first:last] += damage / dt * window

    return grid, curve
