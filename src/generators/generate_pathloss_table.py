#!/usr/bin/env python3
"""
Task 2.2: Generate Path Loss Comparison Table (2 GHz vs 38 GHz)
Outputs: CSV file for archive, LaTeX table for main document & appendix

The 2 GHz service link and 38 GHz backhaul link both originate at the HAPS
(20 km altitude), so both use haps_a2g_pathloss_db() -- pure free-space path
loss, per Arani, Hu & Zhu (2023) Eq. 2 (service link) and the Xing et al.
(2021) bent-pipe backhaul-link assumption (unobstructed LoS to gateway).
Neither has a landscape-dependent excess-loss term, so this table no longer
breaks out by environment or LoS/NLoS state -- see channel_model.py's
haps_a2g_pathloss_db() docstring.

The 38 GHz feeder link (HAPS -> UAV, first hop of the relay path) also uses
haps_a2g_pathloss_db() -- same carrier as the backhaul link, but the far end
is a UAV at 500 m altitude instead of the ~50 m gateway, and the horizontal
distance is swept over the full 0-100 km service footprint (the UAV can
range as far from the HAPS nadir as the UE it is relaying for).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')  # Add parent dir to path

import numpy as np
import pandas as pd
from models.channel_model import haps_a2g_pathloss_db, HAPS_ALT_M, GATEWAY_ALT_M

# Create output directories
os.makedirs('appendix_data', exist_ok=True)
os.makedirs('appendix_tables', exist_ok=True)

USER_ALT_M = 1.5            # 2 GHz service link: user altitude [m]
UAV_ALT_M = 500.0           # 38 GHz feeder link: UAV altitude [m]
FREQ_SERVICE_HZ = 2.0e9     # Service link: 2 GHz
FREQ_BACKHAUL_HZ = 38.0e9   # Backhaul link (HAPS->Gateway): 38 GHz
FREQ_FEEDER_HZ = 38.0e9     # Feeder link (HAPS->UAV): 38 GHz, same as backhaul

# Distance ranges MUST match link types (Sec III.A):
# - Service link (2 GHz): 0-100 km (HAPS service footprint)
# - Backhaul link (38 GHz): 0-0.5 km (short backhaul, 10-500 m per Sec IV.B)
# - Feeder link (38 GHz, HAPS->UAV): 0-100 km (UAV ranges over the full
#   service footprint as it relays out toward the UE)
DISTANCES_SERVICE_KM = [0, 10, 20, 30, 50, 75, 100]
DISTANCES_BACKHAUL_KM = [0, 0.05, 0.1, 0.2, 0.3, 0.5]
DISTANCES_FEEDER_KM = [0, 10, 20, 30, 50, 75, 100]

print("\n" + "=" * 80)
print("Task 2.2: Path Loss Comparison Table Generation (2 GHz vs 38 GHz)")
print("=" * 80 + "\n")

results = []

# Service link: 2 GHz, distances 0-100 km
for dist_km in DISTANCES_SERVICE_KM:
    r_m = dist_km * 1000.0
    pl_db = float(np.asarray(
        haps_a2g_pathloss_db(r_m, HAPS_ALT_M, f_hz=FREQ_SERVICE_HZ, h_user_m=USER_ALT_M)
    ).flat[0])
    results.append({
        'Distance_km': dist_km,
        'Frequency_GHz': float(FREQ_SERVICE_HZ / 1e9),
        'Frequency_Name': '2 GHz (Service)',
        'Path_Loss_Blended_dB': round(pl_db, 1),
        'Link_Type': 'Service',
    })

# Backhaul link: 38 GHz, distances 0-0.5 km (10-500 m per Sec IV.B)
for dist_km in DISTANCES_BACKHAUL_KM:
    r_m = dist_km * 1000.0
    pl_db = float(np.asarray(
        haps_a2g_pathloss_db(r_m, HAPS_ALT_M, f_hz=FREQ_BACKHAUL_HZ, h_user_m=GATEWAY_ALT_M)
    ).flat[0])
    results.append({
        'Distance_km': dist_km,
        'Frequency_GHz': float(FREQ_BACKHAUL_HZ / 1e9),
        'Frequency_Name': '38 GHz (Backhaul)',
        'Path_Loss_Blended_dB': round(pl_db, 1),
        'Link_Type': 'Backhaul',
    })

# Feeder link: HAPS -> UAV, 38 GHz, distances 0-100 km
for dist_km in DISTANCES_FEEDER_KM:
    r_m = dist_km * 1000.0
    pl_db = float(np.asarray(
        haps_a2g_pathloss_db(r_m, HAPS_ALT_M, f_hz=FREQ_FEEDER_HZ, h_user_m=UAV_ALT_M)
    ).flat[0])
    results.append({
        'Distance_km': dist_km,
        'Frequency_GHz': float(FREQ_FEEDER_HZ / 1e9),
        'Frequency_Name': '38 GHz (Feeder, HAPS-UAV)',
        'Path_Loss_Blended_dB': round(pl_db, 1),
        'Link_Type': 'Feeder',
    })

df = pd.DataFrame(results)

# ============================================================================
# Frequency Offset Analysis
# ============================================================================

print("Frequency Offset Analysis (38 GHz Backhaul - 2 GHz Service):")
print("-" * 80)
print("Service Link (2 GHz) at 0–100 km:")
for dist_km in DISTANCES_SERVICE_KM:
    try:
        pl_2ghz = df[(df['Distance_km'] == dist_km) & (df['Link_Type'] == 'Service')]['Path_Loss_Blended_dB'].iloc[0]
        print(f"  {dist_km:6.2f} km: 2 GHz = {pl_2ghz:6.1f} dB")
    except:
        pass

print("\nBackhaul Link (38 GHz) at 0–0.5 km (10–500 m):")
for dist_km in DISTANCES_BACKHAUL_KM:
    try:
        pl_38ghz = df[(df['Distance_km'] == dist_km) & (df['Link_Type'] == 'Backhaul')]['Path_Loss_Blended_dB'].iloc[0]
        print(f"  {dist_km:6.3f} km ({dist_km*1000:6.1f} m): 38 GHz = {pl_38ghz:6.1f} dB")
    except:
        pass

print("\nFeeder Link (38 GHz, HAPS->UAV) at 0-100 km:")
for dist_km in DISTANCES_FEEDER_KM:
    try:
        pl_relay = df[(df['Distance_km'] == dist_km) & (df['Link_Type'] == 'Feeder')]['Path_Loss_Blended_dB'].iloc[0]
        print(f"  {dist_km:6.2f} km: 38 GHz (Feeder) = {pl_relay:6.1f} dB")
    except:
        pass

# Calculate offset at overlapping distances (0-0.5 km only)
print("\nFrequency Offset at Backhaul Distances (where both links coexist):")
for dist_km in DISTANCES_BACKHAUL_KM:
    try:
        pl_2ghz = df[(df['Distance_km'] == dist_km) & (df['Link_Type'] == 'Service')]['Path_Loss_Blended_dB'].iloc[0]
        pl_38ghz = df[(df['Distance_km'] == dist_km) & (df['Link_Type'] == 'Backhaul')]['Path_Loss_Blended_dB'].iloc[0]
        print(f"  {dist_km:6.3f} km: Offset = {pl_38ghz - pl_2ghz:5.1f} dB")
    except:
        pass

# Offset between Service (2 GHz) and Feeder (38 GHz) over the shared 0-100 km range
print("\nFrequency Offset at Service/Feeder Distances (0-100 km, both share the same geometry):")
for dist_km in DISTANCES_SERVICE_KM:
    try:
        pl_2ghz = df[(df['Distance_km'] == dist_km) & (df['Link_Type'] == 'Service')]['Path_Loss_Blended_dB'].iloc[0]
        pl_relay = df[(df['Distance_km'] == dist_km) & (df['Link_Type'] == 'Feeder')]['Path_Loss_Blended_dB'].iloc[0]
        print(f"  {dist_km:6.2f} km: Offset = {pl_relay - pl_2ghz:5.1f} dB")
    except:
        pass

print("\nExpected: ~25.6 dB offset (20*log10(38/2), pure free-space, distance-independent)")
print("Note: Service link deployed 0-100 km; Backhaul link only 0-0.5 km (short range);")
print("      Feeder link (HAPS->UAV, 38 GHz) deployed 0-100 km (UAV at 500 m altitude)")

# ============================================================================
# Export CSV
# ============================================================================

df.to_csv('Path_loss_comparison_2ghz_38ghz.csv', index=False)
print("\n[OK] CSV saved (main document): Path_loss_comparison_2ghz_38ghz.csv")

df.to_csv('appendix_data/Path_loss_comparison_2ghz_38ghz.csv', index=False)
print("[OK] CSV saved (appendix): appendix_data/Path_loss_comparison_2ghz_38ghz.csv")

# ============================================================================
# Export LaTeX Table
# ============================================================================

# Rename columns to replace underscores with spaces for readability in LaTeX
df_latex = df.copy()
df_latex.columns = [col.replace('_', ' ') for col in df_latex.columns]

latex_main = df_latex.to_latex(
    index=False,
    escape=False,
    float_format=lambda x: f'{x:.1f}' if pd.notna(x) else ''
)

with open('Path_loss_comparison_2ghz_38ghz.tex', 'w') as f:
    f.write(latex_main)
print("[OK] LaTeX table saved (main document): Path_loss_comparison_2ghz_38ghz.tex")

# NOTE: no \begin{table}/\caption/\label wrapper here -- appendix_tables.tex
# already wraps this \input in its own \begin{table}...\end{table} (with its
# own Table A.1 caption/label) alongside Table A.2's SINR table; wrapping it
# again here would nest \begin{table} inside \begin{table}, which LaTeX
# rejects (fatal "Type H <return> for immediate help" error at \begin{table}).
latex_appendix = f"""\\centering
\\small
{latex_main}"""

with open('appendix_tables/Path_loss_comparison_2ghz_38ghz.tex', 'w') as f:
    f.write(latex_appendix)
print("[OK] LaTeX table saved (appendix): appendix_tables/Path_loss_comparison_2ghz_38ghz.tex")

print("\n" + "=" * 80)
print("Task 2.2 Complete [OK]")
print("=" * 80 + "\n")
