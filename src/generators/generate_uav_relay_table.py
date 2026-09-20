#!/usr/bin/env python3
"""
Generate UAV Relay Path Analysis: Direct (HAPS->UE) vs. Relay (HAPS->UAV->UE)

Companion to generate_relay_table.py (the HAPS->Gateway->UE relay), this
script covers the *other* relay path already described in the paper's
Section II ("Relay Link: HAPS to UAV to User") and modeled numerically by
uav_relay_two_hop_capacity_bps_hz(): a 38 GHz HAPS->UAV first hop (feeder-
style slant path with ITU-P.618 scintillation) bottlenecked, decode-and-
forward, against a 2 GHz, landscape-dependent UAV->UE second hop.

Sweeps HAPS->UAV horizontal distance (0-100 km, matching the Relay rows in
generate_pathloss_table.py) across the four ENVIRONMENTS landscapes, since
-- unlike the Gateway relay's access hop -- the UAV->UE hop uses the
building-blockage LoS/NLoS model and is landscape-dependent.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')  # Add parent dir to path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from models.channel_model import (
    haps_a2g_pathloss_db, rx_power_dbm, sinr_db, uav_relay_two_hop_capacity_bps_hz,
    HAPS_ALT_M, UAV_ALT_M, P_TX_HAPS_DBM, NOISE_DBM, ENVIRONMENTS,
)

# Output directories (matches generate_relay_table.py's convention: run from
# src/, write into src/appendix_data and src/appendix_tables, and a figure
# into src/output, all later copied to the project-root figures/ and
# appendix_tables/ directories).
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
os.makedirs('appendix_data', exist_ok=True)
os.makedirs('appendix_tables', exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

USER_ALT_M = 1.5
FREQ_SERVICE_HZ = 2.0e9

# HAPS->UAV horizontal distance sweep: same range/points as the "Relay
# (HAPS->UAV)" rows in generate_pathloss_table.py (DISTANCES_RELAY_KM).
DISTANCES_KM = [0, 10, 20, 30, 50, 75, 100]
LANDSCAPES = list(ENVIRONMENTS.keys())  # suburban, urban, dense_urban, high_rise

print("\n" + "=" * 80)
print("UAV Relay Path Analysis (Direct HAPS->UE vs. HAPS->UAV->UE, per landscape)")
print("=" * 80 + "\n")

rows = []
for env in LANDSCAPES:
    for dist_km in DISTANCES_KM:
        r_m = dist_km * 1000.0

        # Direct HAPS->UE (clear-sky, landscape-independent per III.C -- pure FSPL)
        pl_direct_db = float(np.asarray(
            haps_a2g_pathloss_db(r_m, HAPS_ALT_M, f_hz=FREQ_SERVICE_HZ, h_user_m=USER_ALT_M)
        ).flat[0])
        sinr_direct_db = float(np.asarray(
            sinr_db(rx_power_dbm(P_TX_HAPS_DBM, pl_direct_db), noise_dbm=NOISE_DBM)
        ).flat[0])
        capacity_direct = float(np.log2(1.0 + 10.0 ** (sinr_direct_db / 10.0)))

        # Relay HAPS->UAV->UE (clear-sky HAPS->UAV hop, landscape-dependent UAV->UE hop)
        relay = uav_relay_two_hop_capacity_bps_hz(r_m, env=env, include_scint=True)
        sinr_haps_uav_db = float(np.asarray(relay["sinr_haps_uav_db"]).flat[0])
        sinr_uav_ue_db = float(np.asarray(relay["sinr_uav_ue_db"]).flat[0])
        capacity_haps_uav = float(np.asarray(relay["capacity_haps_uav_bps_hz"]).flat[0])
        capacity_uav_ue = float(np.asarray(relay["capacity_uav_ue_bps_hz"]).flat[0])
        capacity_uav_relay = float(np.asarray(relay["capacity_uav_relay_bps_hz"]).flat[0])

        rows.append({
            'Landscape': env,
            'Distance_km': dist_km,
            'SINR_Direct_dB': round(sinr_direct_db, 1),
            'Capacity_Direct_bps_Hz': round(capacity_direct, 2),
            'SINR_HAPS_UAV_dB': round(sinr_haps_uav_db, 1),
            'SINR_UAV_UE_dB': round(sinr_uav_ue_db, 1),
            'Capacity_HAPS_UAV_bps_Hz': round(capacity_haps_uav, 2),
            'Capacity_UAV_UE_bps_Hz': round(capacity_uav_ue, 2),
            'Capacity_UAV_Relay_bps_Hz': round(capacity_uav_relay, 2),
            'Bottleneck_Hop': 'HAPS-UAV' if capacity_haps_uav <= capacity_uav_ue else 'UAV-UE',
            'Relay_Beats_Direct': bool(capacity_uav_relay > capacity_direct),
        })

df = pd.DataFrame(rows)
print(df.to_string(index=False))
print("\nNote: relay capacity is decode-and-forward, C_relay = min(C_haps_uav, C_uav_ue).")
print("HAPS->UAV hop (38 GHz, feeder-style, ITU-P.618 scintillation) is landscape-independent (pure FSPL).")
print("UAV->UE hop (2 GHz, access-style) uses the landscape-dependent LoS/NLoS blended model.")

# ============================================================================
# Export CSV
# ============================================================================

df.to_csv('UAV_relay_path_comparison.csv', index=False)
print("\n[OK] CSV saved (main document): UAV_relay_path_comparison.csv")

df.to_csv('appendix_data/UAV_relay_path_comparison.csv', index=False)
print("[OK] CSV saved (appendix): appendix_data/UAV_relay_path_comparison.csv")

# ============================================================================
# Export LaTeX table (suburban and high_rise only, to keep the printed table
# a manageable size -- best-case and worst-case landscapes for the
# landscape-dependent UAV->UE hop; full 4-landscape data is in the CSV)
# ============================================================================

df_print = df[df['Landscape'].isin(['suburban', 'high_rise'])].copy()
df_print = df_print[['Landscape', 'Distance_km', 'Capacity_Direct_bps_Hz',
                      'Capacity_HAPS_UAV_bps_Hz', 'Capacity_UAV_UE_bps_Hz',
                      'Capacity_UAV_Relay_bps_Hz', 'Bottleneck_Hop']]
# escape=False below leaves cell text as raw LaTeX, so underscores in values
# (e.g. "high_rise") must be escaped by hand -- LaTeX reads a bare "_" as a
# math-mode subscript outside math mode and errors ("Missing $ inserted").
df_print['Landscape'] = df_print['Landscape'].str.replace('_', ' ', regex=False)
df_print.columns = [c.replace('_', ' ') for c in df_print.columns]

latex_main = df_print.to_latex(
    index=False,
    escape=False,
    float_format=lambda x: f'{x:.2f}' if pd.notna(x) else ''
)

with open('UAV_relay_path_comparison.tex', 'w') as f:
    f.write(latex_main)
print("[OK] LaTeX table saved (main document): UAV_relay_path_comparison.tex")

latex_appendix = f"""\\begin{{table}}[htbp]
\\centering
\\small
{latex_main}
\\caption{{Table A.4: Direct (HAPS\\textrightarrow UE) vs. relay (HAPS\\textrightarrow UAV\\textrightarrow UE) link comparison, suburban and high-rise landscapes (best/worst case for the landscape-dependent second hop; full 4-landscape data in \\texttt{{appendix\\_data/UAV\\_relay\\_path\\_comparison.csv}}). The relay path is decode-and-forward: the 38\\,GHz HAPS\\textrightarrow UAV first hop (feeder-style slant path, UAV at {UAV_ALT_M:.0f}\\,m, with ITU-P.618 scintillation) is landscape-independent, while the 2\\,GHz UAV\\textrightarrow UE second hop uses the landscape-dependent LoS/NLoS blended model (\\S III.C). $C_{{\\text{{relay}}}} = \\min(C_{{\\text{{haps-uav}}}}, C_{{\\text{{uav-ue}}}})$, implemented in \\texttt{{uav\\_relay\\_two\\_hop\\_capacity\\_bps\\_hz()}}.}}
\\label{{table:app-uav-relay-comparison}}
\\end{{table}}
"""

with open('appendix_tables/UAV_relay_path_comparison.tex', 'w') as f:
    f.write(latex_appendix)
print("[OK] LaTeX table saved (appendix): appendix_tables/UAV_relay_path_comparison.tex")

# ============================================================================
# Figure: SINR (dB) vs. HAPS->UAV distance -- direct link vs. both relay
# hops. SINR (not capacity) is plotted because the HAPS->UAV hop collapses
# to near-zero capacity within ~20 km, which is the key finding, but that
# collapse is only legible on a dB scale; a linear bits/s/Hz axis compresses
# the two relay hops into an indistinguishable line at the bottom. Landscape
# only shifts the UAV->UE curve by <2 dB (see CSV for all 4 landscapes), so
# suburban (best case) and high_rise (worst case) bracket the full range.
# ============================================================================

COLOR_DIRECT = '#4C72B0'
COLOR_HAPS_UAV = '#DD8452'
COLOR_UAV_UE = '#55A868'

fig, ax = plt.subplots(figsize=(7.5, 5))

sub_subur = df[df['Landscape'] == 'suburban'].sort_values('Distance_km')
sub_hr = df[df['Landscape'] == 'high_rise'].sort_values('Distance_km')

ax.plot(sub_subur['Distance_km'], sub_subur['SINR_Direct_dB'], 'o-',
        color=COLOR_DIRECT, label='Direct (HAPS→UE)', linewidth=2)
ax.plot(sub_subur['Distance_km'], sub_subur['SINR_HAPS_UAV_dB'], 's-',
        color=COLOR_HAPS_UAV, label='Hop 1: HAPS→UAV (38 GHz)', linewidth=2)
ax.fill_between(sub_subur['Distance_km'], sub_subur['SINR_UAV_UE_dB'], sub_hr['SINR_UAV_UE_dB'],
                 color=COLOR_UAV_UE, alpha=0.15, label='Hop 2: UAV→UE (2 GHz), suburban–high-rise range')
ax.plot(sub_subur['Distance_km'], sub_subur['SINR_UAV_UE_dB'], '^--',
         color=COLOR_UAV_UE, linewidth=1.5, alpha=0.8)
ax.plot(sub_hr['Distance_km'], sub_hr['SINR_UAV_UE_dB'], '^--',
         color=COLOR_UAV_UE, linewidth=1.5, alpha=0.8)

ax.axhline(0, color='gray', linestyle=':', linewidth=1, label='0 dB (unity SINR)')

ax.set_xlabel('HAPS–UAV horizontal distance [km]')
ax.set_ylabel('SINR [dB]')
ax.set_title('Direct Link vs. HAPS→UAV→UE Relay Hops')
ax.grid(True, alpha=0.3)
ax.legend(loc='upper right', fontsize=9)
fig.tight_layout()

fig_path = os.path.join(OUTPUT_DIR, '12_uav_relay_comparison.png')
fig.savefig(fig_path, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f"[OK] Figure saved: {fig_path}")

print("\n" + "=" * 80)
print("UAV Relay Path Analysis Generation Complete [OK]")
print("=" * 80 + "\n")
