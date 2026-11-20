import matplotlib.pyplot as plt
import numpy as np


def calculate_instantaneous_dps(
    timestamps, damages, sigma=0.5, truncation=1.5, dt=0.05
):
  """Calculates instantaneous DPS using a truncated Gaussian convolution for each hit.

  Parameters:
  - timestamps: list/array of hit times (seconds)
  - damages: list/array of damage values per hit
  - sigma: standard deviation of the Gaussian (width of the bell curve)
  - truncation: distance from the hit time to cut off the Gaussian (seconds)
  - dt: time-step resolution of the output curve (seconds)
  """
  timestamps = np.asarray(timestamps)
  damages = np.asarray(damages)

  if len(timestamps) == 0:
    return np.array([]), np.array([])

  # 1. Create a continuous time grid spanning from the first hit minus truncation
  #    to the last hit plus truncation.
  t_start = timestamps.min() - truncation
  t_end = timestamps.max() + truncation
  t_grid = np.arange(t_start, t_end, dt)

  # Initialize our DPS curve array with zeros
  dps_curve = np.zeros_like(t_grid)

  # Normalization factor so the area under each hit's curve equals its damage
  norm_factor = 1.0 / (sigma * np.sqrt(2 * np.pi))

  # 2. Add each hit's Gaussian contribution to the curve
  for t_hit, dmg in zip(timestamps, damages):
    # Find indices within the +/- 1.5s truncation window
    mask = np.abs(t_grid - t_hit) <= truncation
    if not np.any(mask):
      continue

    t_sub = t_grid[mask]
    # Evaluate Gaussian formula for points inside the window
    gaussian = (
        dmg * norm_factor * np.exp(-((t_sub - t_hit) ** 2) / (2 * sigma**2))
    )
    dps_curve[mask] += gaussian

  return t_grid, dps_curve


# --- Example Usage with Simulated Data ---
if __name__ == "__main__":
  # Simulated combat trial data: (timestamp, damage)
  # Suppose we have a burst phase around t = 3.0s to 4.0s
  timestamps = [0.2, 0.8, 1.5, 3.0, 3.1, 3.3, 3.5, 4.0, 5.2, 6.0]
  damages = [800, 950, 1100, 4500, 5200, 4800, 6000, 3100, 900, 750]

  # Compute DPS curve
  t, dps = calculate_instantaneous_dps(
      timestamps, damages, sigma=0.5, truncation=1.5, dt=0.05
  )

  # Plotting the results
  plt.figure(figsize=(10, 5))
  plt.plot(t, dps, color="#ff4757", linewidth=2.5, label="Instantaneous DPS")
  plt.scatter(
      timestamps,
      np.zeros_like(timestamps),
      color="#2ed573",
      s=damages / 30,
      zorder=3,
      label="Raw Hits (scaled by damage)",
  )

  plt.title("Team Instantaneous DPS Spike Analysis", fontsize=14, fontweight="bold")
  plt.xlabel("Time (seconds)", fontsize=11)
  plt.ylabel("DPS (Damage / Second)", fontsize=11)
  plt.grid(True, linestyle="--", alpha=0.5)
  plt.legend()
  plt.tight_layout()
  plt.show()