#!/usr/bin/env python3
"""
Generate UAV Relay Path Analysis: Direct (HAPS->UE) vs. Relay (HAPS->UAV->UE)

Companion to generate_relay_table.py (the HAPS->Gateway->UE relay), this
script covers the *other* relay path already described in the paper's
Section II ("Relay Link: HAPS to UAV to User") and modeled numerically by
uav_relay_two_hop_capacity_bps_hz(): a 38 GHz HAPS->UAV first hop (feeder-
style slant path with ITU-P.618 scintillation) bottlenecked, decode-and-
forward, against a 2 GHz, landscape-dependent UAV->UE second hop.

The single relay UAV is static (Table 1: count=1, no mobility) and fixed at
the HAPS triangle's centroid -- so the HAPS->UAV feeder distance is now a
CONSTANT (R_HAPS_UAV_M, the triangle's circumradius), not the sweep variable.
This replaces an earlier version of this script that (incorrectly) assumed
the UAV always hovers within a small fixed offset of whichever user it
serves, which made the UAV->UE hop unrealistically good at every distance.

Sweeps horizontal distance from the serving HAPS (0-100 km, matching the
Relay rows in generate_pathloss_table.py), azimuth-averaged around that HAPS
(matching the direct-link SINR's existing averaging convention just above),
across the four ENVIRONMENTS landscapes. Since the UAV sits off-axis from
the serving HAPS's nadir, a given azimuth/radius determines a different
real UAV->UE distance -- that distance, not the sweep variable itself,
now drives the access hop.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')  # Add parent dir to path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from models.channel_model import (
    haps_a2g_pathloss_db, rx_power_dbm, sinr_db, uav_relay_two_hop_capacity_bps_hz,
    haps_constellation_geometry, multi_node_sinr_db_spatial,
    HAPS_ALT_M, UAV_ALT_M, P_TX_HAPS_DBM, NOISE_DBM, ENVIRONMENTS,
)

# Single static relay UAV (Table 1: count=1, no mobility), fixed at the HAPS triangle's
# centroid -- matches haps_association_env.py's fix for the same previously-incorrect
# "UAV always ~hovers next to whichever user it serves" assumption (reviewer feedback:
# Table 1 says 1 static UAV, but that assumption made the UAV->UE hop unrealistically
# good at every distance). With the UAV fixed at the centroid, the HAPS->UAV feeder
# distance is CONSTANT (circumradius of the equilateral triangle, ~37.5 km at 65 km
# spacing, the same for all three HAPS), while the UAV->UE access hop now varies with
# each user's real distance from that one fixed point.
_NODES = haps_constellation_geometry(spacing_km=65.0)
_UAV_XY_M = np.mean([[_NODES[k][0], _NODES[k][1]] for k in ('serving', 'interferer1', 'interferer2')], axis=0)
R_HAPS_UAV_M = float(np.linalg.norm(_UAV_XY_M - np.array([_NODES['serving'][0], _NODES['serving'][1]])))

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
        # Co-channel interference from the two other HAPS included. Averaged in dB over 24
        # azimuths around the serving HAPS, as the Phase-1 table (table:app-sinr-multinode-distances).
        azimuths = np.linspace(0.0, 2.0 * np.pi, 24, endpoint=False)
        sinr_direct_db = float(np.mean([
            float(np.asarray(multi_node_sinr_db_spatial(r_m * np.cos(a), r_m * np.sin(a),
                                                        env=env)["SINR_dB"]).flat[0])
            for a in azimuths]))
        capacity_direct = float(np.log2(1.0 + 10.0 ** (sinr_direct_db / 10.0)))

        # Relay HAPS->UAV->UE, with the UAV fixed at the centroid (see R_HAPS_UAV_M above):
        # the feeder hop (HAPS->UAV) is now a constant distance, not r_m -- r_m instead
        # drives the UAV->UE access hop's real distance, azimuth-averaged around the
        # serving HAPS (same azimuthal averaging convention as the direct-link SINR
        # just above), since the UAV sits off-axis from the serving HAPS's nadir.
        uav_ue_dists_m = np.sqrt(
            (r_m * np.cos(azimuths) - _UAV_XY_M[0]) ** 2 + (r_m * np.sin(azimuths) - _UAV_XY_M[1]) ** 2
        )
        relay_per_az = [uav_relay_two_hop_capacity_bps_hz(
            r_horiz_m=R_HAPS_UAV_M, uav_ue_horiz_m=float(d), env=env, include_scint=True)
            for d in uav_ue_dists_m]
        sinr_haps_uav_db = float(np.mean([float(np.asarray(r["sinr_haps_uav_db"]).flat[0]) for r in relay_per_az]))
        sinr_uav_ue_db = float(np.mean([float(np.asarray(r["sinr_uav_ue_db"]).flat[0]) for r in relay_per_az]))
        capacity_haps_uav = float(np.mean([float(np.asarray(r["capacity_haps_uav_bps_hz"]).flat[0]) for r in relay_per_az]))
        capacity_uav_ue = float(np.mean([float(np.asarray(r["capacity_uav_ue_bps_hz"]).flat[0]) for r in relay_per_az]))
        capacity_uav_relay = float(np.mean([float(np.asarray(r["capacity_uav_relay_bps_hz"]).flat[0]) for r in relay_per_az]))

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
\\caption{{Table A.4: Direct (HAPS\\textrightarrow UE) vs. relay (HAPS\\textrightarrow UAV\\textrightarrow UE) link comparison, suburban and high-rise landscapes, as a function of distance from the serving HAPS, azimuth-averaged (best/worst case for the landscape-dependent second hop; full 4-landscape data in \\texttt{{appendix\\_data/UAV\\_relay\\_path\\_comparison.csv}}). The relay UAV is static, fixed at the HAPS triangle's centroid ({UAV_ALT_M:.0f}\\,m altitude, {R_HAPS_UAV_M/1000:.1f}\\,km from each HAPS); the 38\\,GHz HAPS\\textrightarrow UAV feeder hop is therefore a constant, landscape-independent link, while the 2\\,GHz UAV\\textrightarrow UE access hop uses each user's real, azimuth-dependent distance to that fixed point with the landscape-dependent LoS/NLoS blended model (\\S III.C). $C_{{\\text{{relay}}}} = \\min(C_{{\\text{{haps-uav}}}}, C_{{\\text{{uav-ue}}}})$, implemented in \\texttt{{uav\\_relay\\_two\\_hop\\_capacity\\_bps\\_hz()}}.}}
\\label{{table:app-uav-relay-comparison}}
\\end{{table}}
"""

with open('appendix_tables/UAV_relay_path_comparison.tex', 'w') as f:
    f.write(latex_appendix)
print("[OK] LaTeX table saved (appendix): appendix_tables/UAV_relay_path_comparison.tex")

# ============================================================================
# Figure: SINR (dB) vs. distance from the serving HAPS -- direct link vs.
# both relay hops. SINR (not capacity) is plotted because the UAV->UE hop
# collapses to near-zero capacity within ~20 km of the fixed UAV, which is
# the key finding, but that collapse is only legible on a dB scale; a linear
# bits/s/Hz axis compresses the relay curve into an indistinguishable line at
# the bottom. Landscape only shifts the UAV->UE curve by <2 dB (see CSV for
# all 4 landscapes), so suburban (best case) and high_rise (worst case)
# bracket the full range. The HAPS->UAV hop is now flat (fixed UAV position).
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

ax.set_xlabel('Distance from serving HAPS [km]')
ax.set_ylabel('SINR [dB]')
ax.set_title('Direct Link vs. HAPS→UAV→UE Relay Hops (static UAV at centroid)')
ax.grid(True, alpha=0.3)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=9, frameon=False)
fig.tight_layout()

fig_path = os.path.join(OUTPUT_DIR, '12_uav_relay_comparison.png')
fig.savefig(fig_path, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f"[OK] Figure saved: {fig_path}")

print("\n" + "=" * 80)
print("UAV Relay Path Analysis Generation Complete [OK]")
print("=" * 80 + "\n")
