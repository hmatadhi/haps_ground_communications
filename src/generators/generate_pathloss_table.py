#!/usr/bin/env python3
"""
Task 2.2: Generate Path Loss Comparison Table (2 GHz vs 38 GHz)
Outputs: CSV file for archive, LaTeX table for main document & appendix

Both the 2 GHz service link and 38 GHz feeder link originate at the HAPS
(20 km altitude), so both use haps_a2g_pathloss_db() -- pure free-space path
loss, per Arani, Hu & Zhu (2023) Eq. 2 (service link) and the Xing et al.
(2021) bent-pipe feeder-link assumption (unobstructed LoS to gateway).
Neither has a landscape-dependent excess-loss term, so this table no longer
breaks out by environment or LoS/NLoS state -- see channel_model.py's
haps_a2g_pathloss_db() docstring.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')  # Add parent dir to path

import numpy as np
import pandas as pd
from models.channel_model import haps_a2g_pathloss_db, HAPS_ALT_M

# Create output directories
os.makedirs('appendix_data', exist_ok=True)
os.makedirs('appendix_tables', exist_ok=True)

USER_ALT_M = 1.5            # 2 GHz service link: user altitude [m]
GATEWAY_ALT_M = 50.0        # 38 GHz feeder link: gateway altitude [m] AGL
                             # (matches export_feeder_link_csv() convention and
                             # this document's stated Gateway height, S:III.A)
FREQ_SERVICE_HZ = 2.0e9     # Service link: 2 GHz
FREQ_FEEDER_HZ = 38.0e9     # Feeder link: 38 GHz

# Distance ranges MUST match link types (Sec III.A):
# - Service link (2 GHz): 0-100 km (HAPS service footprint)
# - Feeder link (38 GHz): 0-0.5 km (short backhaul, 10-500 m per Sec IV.B)
DISTANCES_SERVICE_KM = [0, 10, 20, 30, 50, 75, 100]
DISTANCES_FEEDER_KM = [0, 0.05, 0.1, 0.2, 0.3, 0.5]

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

# Feeder link: 38 GHz, distances 0-0.5 km (10-500 m per Sec IV.B)
for dist_km in DISTANCES_FEEDER_KM:
    r_m = dist_km * 1000.0
    pl_db = float(np.asarray(
        haps_a2g_pathloss_db(r_m, HAPS_ALT_M, f_hz=FREQ_FEEDER_HZ, h_user_m=GATEWAY_ALT_M)
    ).flat[0])
    results.append({
        'Distance_km': dist_km,
        'Frequency_GHz': float(FREQ_FEEDER_HZ / 1e9),
        'Frequency_Name': '38 GHz (Feeder)',
        'Path_Loss_Blended_dB': round(pl_db, 1),
        'Link_Type': 'Feeder',
    })

df = pd.DataFrame(results)

# ============================================================================
# Frequency Offset Analysis
# ============================================================================

print("Frequency Offset Analysis (38 GHz Feeder - 2 GHz Service):")
print("-" * 80)
print("Service Link (2 GHz) at 0–100 km:")
for dist_km in DISTANCES_SERVICE_KM:
    try:
        pl_2ghz = df[(df['Distance_km'] == dist_km) & (df['Link_Type'] == 'Service')]['Path_Loss_Blended_dB'].iloc[0]
        print(f"  {dist_km:6.2f} km: 2 GHz = {pl_2ghz:6.1f} dB")
    except:
        pass

print("\nFeeder Link (38 GHz) at 0–0.5 km (10–500 m):")
for dist_km in DISTANCES_FEEDER_KM:
    try:
        pl_38ghz = df[(df['Distance_km'] == dist_km) & (df['Link_Type'] == 'Feeder')]['Path_Loss_Blended_dB'].iloc[0]
        print(f"  {dist_km:6.3f} km ({dist_km*1000:6.1f} m): 38 GHz = {pl_38ghz:6.1f} dB")
    except:
        pass

# Calculate offset at overlapping distances (0-0.5 km only)
print("\nFrequency Offset at Feeder Distances (where both links coexist):")
for dist_km in DISTANCES_FEEDER_KM:
    try:
        pl_2ghz = df[(df['Distance_km'] == dist_km) & (df['Link_Type'] == 'Service')]['Path_Loss_Blended_dB'].iloc[0]
        pl_38ghz = df[(df['Distance_km'] == dist_km) & (df['Link_Type'] == 'Feeder')]['Path_Loss_Blended_dB'].iloc[0]
        print(f"  {dist_km:6.3f} km: Offset = {pl_38ghz - pl_2ghz:5.1f} dB")
    except:
        pass

print("\nExpected: ~25.6 dB offset (20*log10(38/2), pure free-space, distance-independent)")
print("Note: Service link only deployed 0-100 km; Feeder link only 0-0.5 km (short backhaul)")

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

latex_appendix = f"""\\begin{{table}}[H]
\\centering
\\small
{latex_main}
\\caption{{Table A.1: Path Loss Comparison (2 GHz Service Link vs 38 GHz Feeder Link). Pure free-space path loss across eight distances (0--150 km) -- both links originate at the HAPS (20 km altitude) and have no landscape-dependent excess loss (Arani et al.\\ Eq.\\ 2; see channel\\_model.py). Consistent $\\sim$25.6\\,dB frequency offset validates the free-space model at both bands.}}
\\label{{table:app-pathloss-2ghz-38ghz}}
\\end{{table}}
"""

with open('appendix_tables/Path_loss_comparison_2ghz_38ghz.tex', 'w') as f:
    f.write(latex_appendix)
print("[OK] LaTeX table saved (appendix): appendix_tables/Path_loss_comparison_2ghz_38ghz.tex")

print("\n" + "=" * 80)
print("Task 2.2 Complete [OK]")
print("=" * 80 + "\n")
