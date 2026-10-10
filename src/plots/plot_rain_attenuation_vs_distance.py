"""
Rain attenuation vs. HAPS-Gateway horizontal distance (38 GHz backhaul), ITU-R
P.838/P.618, at several fixed rain rates. Elevation angle is derived from the same
HAPS/Gateway geometry used elsewhere (HAPS at 20 km, Gateway at 50 m AGL).

Output: figures/rain_attenuation_vs_distance.png

Run from repo root: python src/plots/plot_rain_attenuation_vs_distance.py
"""

import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from atmospheric_losses import rain_attenuation_db  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_PATH = os.path.join(ROOT, "figures", "rain_attenuation_vs_distance.png")

HAPS_ALT_M = 20_000.0
GATEWAY_ALT_M = 50.0
FREQ_GHZ = 38.0
RAIN_RATES_MMHR = [5, 10, 25, 50]


def main() -> None:
    dh = HAPS_ALT_M - GATEWAY_ALT_M
    d_km = np.linspace(1, 200, 400)
    elev_deg = np.degrees(np.arctan2(dh, d_km * 1000))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for rate in RAIN_RATES_MMHR:
        atten = np.array([rain_attenuation_db(rate, FREQ_GHZ, e) for e in elev_deg])
        ax.plot(d_km, atten, lw=2, label=f"{rate} mm/h")

    ax.set_xlabel("HAPS–Gateway horizontal distance [km]")
    ax.set_ylabel("Rain attenuation [dB]")
    ax.set_title(
        "38 GHz Backhaul Rain Attenuation vs. Distance (ITU-R P.838/P.618)\n"
        "HAPS at 20 km, Gateway at 50 m AGL"
    )
    ax.legend(title="Rain rate")
    ax.grid(alpha=0.3)

    # Secondary x-axis: elevation angle, so the distance <-> elevation relationship
    # (and its effect on the rain slant-path length) is visible on the figure itself,
    # not just asserted in a caption.
    def dist_to_elev(d):
        return np.degrees(np.arctan2(dh, np.maximum(d, 1e-9) * 1000))

    def elev_to_dist(e):
        e = np.clip(e, 1e-3, 89.999)
        return dh / np.tan(np.radians(e)) / 1000

    secax = ax.secondary_xaxis("top", functions=(dist_to_elev, elev_to_dist))
    secax.set_xlabel("Elevation angle [deg]")

    fig.tight_layout()
    fig.savefig(OUT_PATH, dpi=150)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
