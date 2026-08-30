#!/usr/bin/env python3
"""Generate compact LaTeX tables for appendix (narrow columns to fit margins)"""

import pandas as pd

print("[OK] Generating compact tables for appendix...")

# ========== SINR Table (Compact) ==========
# NOTE: no per-landscape breakdown -- HAPS-tier path loss is landscape-independent
# (pure FSPL, Arani et al. Eq. 2), so there is no Environment/LoS_Prob column here.
df_sinr = pd.read_csv('SINR_multinode_table_distances.csv')

# Keep only essential columns
sinr_compact = df_sinr[['Distance_km', 'Desired_Signal_dBm', 'Interference_dBm', 'SINR_dB']]
sinr_compact.columns = ['Dist', 'Signal(dBm)', 'Interf(dBm)', 'SINR(dB)']

latex_sinr = sinr_compact.to_latex(
    index=False,
    escape=True,
    float_format=lambda x: f'{x:.1f}' if pd.notna(x) else ''
)

with open('SINR_multinode_table_distances.tex', 'w', encoding='utf-8') as f:
    f.write(latex_sinr)

print("[OK] SINR table: 4 columns (compact)")

# ========== Path Loss Table (Compact) ==========
df_pl = pd.read_csv('Path_loss_comparison_2ghz_38ghz.csv')

# Keep only essential columns: distance, frequency, blended path loss
pl_compact = df_pl[['Distance_km', 'Frequency_Name', 'Path_Loss_Blended_dB']]
pl_compact.columns = ['Dist', 'Freq', 'PL(dB)']

latex_pl = pl_compact.to_latex(
    index=False,
    escape=True,
    float_format=lambda x: f'{x:.1f}' if pd.notna(x) else ''
)

with open('Path_loss_comparison_2ghz_38ghz.tex', 'w', encoding='utf-8') as f:
    f.write(latex_pl)

print("[OK] Path Loss table: 3 columns (compact)")
print("\n[OK] Tables regenerated for better margin fit")
