#!/usr/bin/env python3
"""
Generate Relay Path Comparison Table: Direct (HAPS->UE) vs. Relay (HAPS->Gateway->UE)

Both links reuse the same 2 GHz service band and haps_a2g_pathloss_db()
convention (see generate_pathloss_table.py); the relay path additionally
bottlenecks against the 38 GHz HAPS->Gateway feeder link via
relay_two_hop_capacity_bps_hz() (decode-and-forward), including feeder
scintillation and an optional rain-derated feeder scenario.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')  # Add parent dir to path

import numpy as np
import pandas as pd
from models.channel_model import (
    haps_a2g_pathloss_db, rx_power_dbm, sinr_db, relay_two_hop_capacity_bps_hz,
    HAPS_ALT_M, GATEWAY_ALT_M, P_TX_HAPS_DBM, NOISE_DBM,
)
from models.battery_model import feeder_link_rain_effect_on_capacity

# Create output directories
os.makedirs('appendix_data', exist_ok=True)
os.makedirs('appendix_tables', exist_ok=True)

USER_ALT_M = 1.5
FREQ_SERVICE_HZ = 2.0e9

# Fixed feeder-hop geometry: Gateway is co-located near the HAPS ground
# nadir point (matches generate_pathloss_table.py's 10-500 m feeder-distance
# convention), so the elevation angle from the HAPS to the Gateway is close
# to 90 degrees regardless of the (short) horizontal offset.
FEEDER_DIST_KM = 0.1
FEEDER_ELEVATION_DEG = 89.0

# Access-hop (Gateway->UE) distances: same range as the direct service link,
# so the two paths are directly comparable.
DISTANCES_ACCESS_KM = [0, 10, 20, 30, 50, 75, 100]

print("\n" + "=" * 80)
print("Relay Path Comparison Table Generation (Direct HAPS->UE vs. HAPS->Gateway->UE)")
print("=" * 80 + "\n")

results = []
for dist_km in DISTANCES_ACCESS_KM:
    r_m = dist_km * 1000.0

    # Direct HAPS->UE (clear-sky)
    pl_direct_db = float(np.asarray(
        haps_a2g_pathloss_db(r_m, HAPS_ALT_M, f_hz=FREQ_SERVICE_HZ, h_user_m=USER_ALT_M)
    ).flat[0])
    sinr_direct_db = float(np.asarray(
        sinr_db(rx_power_dbm(P_TX_HAPS_DBM, pl_direct_db), noise_dbm=NOISE_DBM)
    ).flat[0])
    capacity_direct = float(np.log2(1.0 + 10.0 ** (sinr_direct_db / 10.0)))

    # Relay HAPS->Gateway->UE (clear-sky feeder)
    relay_clear = relay_two_hop_capacity_bps_hz(
        feeder_dist_km=FEEDER_DIST_KM, feeder_elevation_deg=FEEDER_ELEVATION_DEG,
        gw_ue_dist_m=r_m, include_scint=True,
    )
    capacity_relay_clear = float(np.asarray(relay_clear["capacity_relay_bps_hz"]).flat[0])

    # Relay with a rain-derated feeder hop (10 mm/h moderate rain)
    rain_mm_h = 10.0
    feeder_rain = feeder_link_rain_effect_on_capacity(rain_mm_h)
    capacity_relay_rain = capacity_relay_clear * float(
        np.clip(10.0 ** (-feeder_rain["total_rain_loss_db"] / 10.0), 0.05, 1.0)
    )

    results.append({
        'Distance_km': dist_km,
        'SINR_Direct_dB': round(sinr_direct_db, 1),
        'Capacity_Direct_bps_Hz': round(capacity_direct, 2),
        'SINR_Access_dB': round(float(np.asarray(relay_clear["sinr_access_db"]).flat[0]), 1),
        'Capacity_Relay_ClearSky_bps_Hz': round(capacity_relay_clear, 2),
        'Capacity_Relay_Rain10mmh_bps_Hz': round(capacity_relay_rain, 2),
        'Relay_Beats_Direct_ClearSky': bool(capacity_relay_clear > capacity_direct),
    })

df = pd.DataFrame(results)

print(df.to_string(index=False))
print(f"\nFeeder hop (fixed): dist={FEEDER_DIST_KM} km, elevation={FEEDER_ELEVATION_DEG} deg")
print("Note: relay capacity is decode-and-forward, bottlenecked by min(feeder, access) capacity.")

# ============================================================================
# Export CSV
# ============================================================================

df.to_csv('Relay_path_comparison.csv', index=False)
print("\n[OK] CSV saved (main document): Relay_path_comparison.csv")

df.to_csv('appendix_data/Relay_path_comparison.csv', index=False)
print("[OK] CSV saved (appendix): appendix_data/Relay_path_comparison.csv")

# ============================================================================
# Export LaTeX Table
# ============================================================================

df_latex = df.copy()
df_latex.columns = [col.replace('_', ' ') for col in df_latex.columns]

latex_main = df_latex.to_latex(
    index=False,
    escape=False,
    float_format=lambda x: f'{x:.2f}' if pd.notna(x) else ''
)

with open('Relay_path_comparison.tex', 'w') as f:
    f.write(latex_main)
print("[OK] LaTeX table saved (main document): Relay_path_comparison.tex")

latex_appendix = f"""\\begin{{table}}[H]
\\centering
\\small
{latex_main}
\\caption{{Table A.2: Direct (HAPS\\textrightarrow UE) vs. relay (HAPS\\textrightarrow Gateway\\textrightarrow UE) link comparison. The relay path is decode-and-forward, combining the 38\\,GHz feeder hop (fixed at {FEEDER_DIST_KM}\\,km, {FEEDER_ELEVATION_DEG}$^\\circ$ elevation, with ITU-P.618 scintillation) and the 2\\,GHz Gateway\\textrightarrow UE access hop (same band/power convention as the direct service link) as $C_{{\\text{{relay}}}} = \\min(C_{{\\text{{feeder}}}}, C_{{\\text{{access}}}})$. A 10\\,mm/h rain scenario de-rates the feeder hop per ITU-R P.838.}}
\\label{{table:app-relay-comparison}}
\\end{{table}}
"""

with open('appendix_tables/Relay_path_comparison.tex', 'w') as f:
    f.write(latex_appendix)
print("[OK] LaTeX table saved (appendix): appendix_tables/Relay_path_comparison.tex")

print("\n" + "=" * 80)
print("Relay Path Comparison Table Generation Complete [OK]")
print("=" * 80 + "\n")
