"""
Generate Figure 7: Multi-HAPS interference signal power attenuation (corrected HAPS model).

This replaces the old 5_multi_node_sinr.png with a version using:
- HAPS altitude: 20 km
- Frequency: 2 GHz (service link)
- 3-HAPS constellation (60-70 km spacing)
- Linear-domain SINR calculation (corrected formula)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')  # Add parent dir to path

import numpy as np
import matplotlib.pyplot as plt
from models.channel_model import (haps_a2g_pathloss_db, multi_node_sinr_db,
                                  ENVIRONMENTS, P_TX_HAPS_DBM, NOISE_DBM)


def generate_figure7():
    """Generate corrected Figure 7: Signal power attenuation with multi-HAPS interference."""

    # Range: 0-100 km
    r = np.linspace(1000, 100000, 500)  # 1 km to 100 km

    plt.figure(figsize=(13, 8))

    # Color palette for environments
    colors = {
        'suburban': '#1f77b4',
        'urban': '#ff7f0e',
        'dense_urban': '#2ca02c',
        'high_rise': '#d62728'
    }

    freq_hz = 2000e6  # 2 GHz service link
    haps_alt_m = 20000.0  # 20 km HAPS altitude

    for env in ['suburban', 'urban', 'dense_urban', 'high_rise']:
        # Path loss to serving HAPS (single node)
        pl_serving = haps_a2g_pathloss_db(r, h_haps_m=haps_alt_m, f_hz=freq_hz,
                                         env=env, h_user_m=1.5)
        pl_serving = np.asarray(pl_serving).flatten()

        # Received power from serving HAPS only (clean signal)
        rx_serving_dbm = P_TX_HAPS_DBM - pl_serving

        # SINR with 3-HAPS interference (linear-domain calculation)
        # This returns SINR_Actual from multi_node_sinr_db
        sinr_3haps = multi_node_sinr_db(r, num_haps=3, h_node_m=haps_alt_m,
                                       f_hz=freq_hz, env=env, noise_dbm=NOISE_DBM,
                                       constellation_spacing_km=65.0)
        sinr_3haps = np.asarray(sinr_3haps).flatten()

        # Effective signal power with interference:
        # From SINR = P_serving / (N + I), we can derive:
        # P_effective = SINR * (N + I)
        # But for visualization, we show the degradation as a gap
        # SINR (dB) = 10*log10(P_serving / (N+I))
        # Degradation = 10*log10(P_serving / N) - 10*log10(P_serving / (N+I))
        sinr_no_interf = 10.0 * np.log10(10.0**(rx_serving_dbm/10.0) / (10.0**(NOISE_DBM/10.0)))
        degradation_db = sinr_no_interf - sinr_3haps

        # Effective received power showing the interference effect
        rx_effective_dbm = rx_serving_dbm - degradation_db

        # Plot: serving signal (solid) and effective signal with interference (dashed)
        plt.plot(r/1000, rx_serving_dbm, linestyle='-', linewidth=3, alpha=0.9,
                color=colors[env], label=f"{env}: Received (1 HAPS, clean)")
        plt.plot(r/1000, rx_effective_dbm, linestyle='--', linewidth=2.5, alpha=0.6,
                color=colors[env], label=f"{env}: Effective (3 HAPS interference)")

    plt.xlabel("Horizontal Distance from HAPS Nadir [km]", fontsize=11, fontweight='bold')
    plt.ylabel("Received Power [dBm]", fontsize=11, fontweight='bold')
    plt.title("Signal Power Attenuation: Clean vs. Multi-HAPS Interference (Altitude 20 km, 2 GHz, 0–100 km)",
             fontsize=12, fontweight='bold')
    plt.legend(fontsize=9, loc='best', ncol=2)
    plt.grid(True, alpha=0.3)
    plt.ylim(-220, -20)

    # Add annotation
    textstr = ('Solid lines: Signal received from 1 serving HAPS (no interference)\n'
               'Dashed lines: Effective signal with 3 HAPS (2 interfering nodes)\n'
               'Vertical gap = power margin lost to interference from other HAPS nodes\n'
               'Linear-domain SINR calculation per Arani et al. Eq. 12')
    plt.text(0.02, 0.98, textstr, transform=plt.gca().transAxes, fontsize=9,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig('output/5_multi_node_sinr.png', dpi=150, bbox_inches='tight')
    print("Generated: 5_multi_node_sinr.png (Figure 7 - Multi-HAPS interference)")
    plt.close()


if __name__ == "__main__":
    generate_figure7()
