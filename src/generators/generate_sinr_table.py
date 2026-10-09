#!/usr/bin/env python3
"""
Task 2.1: Generate Multi-Distance SINR Lookup Table
Outputs: CSV file for archive, LaTeX table for main document & appendix

Uses the corrected 3-HAPS equilateral-triangle constellation and pure-FSPL
HAPS path loss from channel_model.py (see haps_a2g_pathloss_db() docstring
-- no landscape-dependent excess loss on the HAPS tier, per Arani, Hu & Zhu
2023 Eq. 2). SINR is therefore landscape-independent here too, so this table
reports a single distance sweep (along +X from nadir) rather than per
environment. Angular/spatial variation across the constellation is covered
separately in Tables A.3a/b and Figures A.1/A.2 (generate_sinr_table_2d_spatial.py).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')  # Add parent dir to path

import numpy as np
import pandas as pd

from models.channel_model import (
    haps_a2g_pathloss_db,
    haps_horiz_ranges_to_user,
    rx_power_dbm,
    HAPS_ALT_M,
    F_HAPS_MHZ,
    P_TX_HAPS_DBM,
    NOISE_DBM,
)

# Create output directories
os.makedirs('appendix_data', exist_ok=True)
os.makedirs('appendix_tables', exist_ok=True)

USER_ALT_M = 1.5
DISTANCES_KM = [0, 30, 50, 100]

print("\n" + "=" * 80)
print("Task 2.1: Multi-Distance SINR Table Generation")
print("=" * 80 + "\n")

results = []
for dist_km in DISTANCES_KM:
    r_m = dist_km * 1000.0

    pl_serving = float(np.asarray(
        haps_a2g_pathloss_db(r_m, HAPS_ALT_M, f_hz=F_HAPS_MHZ * 1e6, h_user_m=USER_ALT_M)
    ).flat[0])
    p_rx_desired = rx_power_dbm(P_TX_HAPS_DBM, pl_serving)

    horiz_ranges = haps_horiz_ranges_to_user(r_m, spacing_km=65.0)
    interf_lin = 0.0
    for interf_key in ['interferer1', 'interferer2']:
        horiz_m = float(np.asarray(horiz_ranges[interf_key]).flat[0])
        pl_interf = float(np.asarray(
            haps_a2g_pathloss_db(horiz_m, HAPS_ALT_M, f_hz=F_HAPS_MHZ * 1e6, h_user_m=USER_ALT_M)
        ).flat[0])
        p_rx_interf = rx_power_dbm(P_TX_HAPS_DBM, pl_interf)
        interf_lin += 10.0 ** (p_rx_interf / 10.0)

    p_interf_dbm = 10.0 * np.log10(interf_lin) if interf_lin > 0 else -200.0
    desired_lin = 10.0 ** (p_rx_desired / 10.0)
    noise_lin = 10.0 ** (NOISE_DBM / 10.0)

    sinr_db = 10.0 * np.log10(desired_lin / (noise_lin + interf_lin))
    snr_db = 10.0 * np.log10(desired_lin / noise_lin)

    results.append({
        'Distance_km': dist_km,
        'Serving_HAPS_km': 0,
        'Interferer1_km': 65,
        'Interferer2_km': 32.5,
        'Desired_Signal_dBm': round(p_rx_desired, 1),
        'Interference_dBm': round(p_interf_dbm, 1),
        'SINR_dB': round(sinr_db, 1),
        'SNR_dB_Noise_Only': round(snr_db, 1),
    })

df = pd.DataFrame(results)

# ============================================================================
# Export CSV
# ============================================================================

df.to_csv('SINR_multinode_table_distances.csv', index=False)
print("[OK] CSV saved (main document): SINR_multinode_table_distances.csv")

df.to_csv('appendix_data/SINR_multinode_table_distances.csv', index=False)
print("[OK] CSV saved (appendix): appendix_data/SINR_multinode_table_distances.csv")

# ============================================================================
# Export LaTeX Table
# ============================================================================

latex_main = df.to_latex(
    index=False,
    escape=False,
    float_format=lambda x: f'{x:.1f}' if pd.notna(x) else ''
)

with open('SINR_multinode_table_distances.tex', 'w') as f:
    f.write(latex_main)
print("[OK] LaTeX table saved (main document): SINR_multinode_table_distances.tex")

latex_appendix = f"""\\begin{{table}}[htbp]
\\centering
\\small
{latex_main}
\\caption{{Table A.2: Multi-Distance SINR Analysis. SINR along the +X axis from HAPS nadir, using the corrected 65\\,km equilateral 3-HAPS constellation and pure free-space path loss (Arani et al.\\ Eq.\\ 2 -- landscape-independent, see channel\\_model.py). Angular/spatial variation across the constellation is covered separately (Tables A.3a/b, Figures A.1/A.2).}}
\\label{{table:app-sinr-multinode-distances}}
\\end{{table}}
"""

with open('appendix_tables/SINR_multinode_table_distances.tex', 'w') as f:
    f.write(latex_appendix)
print("[OK] LaTeX table saved (appendix): appendix_tables/SINR_multinode_table_distances.tex")

print("\nSINR by Distance:")
for _, row in df.iterrows():
    print(f"  {row['Distance_km']:3.0f} km: SINR = {row['SINR_dB']:6.1f} dB (SNR-only: {row['SNR_dB_Noise_Only']:6.1f} dB)")

print("\n" + "=" * 80)
print("Task 2.1 Complete [OK]")
print("=" * 80 + "\n")
