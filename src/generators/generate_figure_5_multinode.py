#!/usr/bin/env python3
"""
Generate Figure 5: Multi-HAPS Interference across 100 km service footprint.

Shows mean SINR (single line -- landscape-independent at the HAPS tier, S:III.C)
with a shaded min-max envelope showing angular variation around the constellation.
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Load spatial SINR data
df = pd.read_csv('output/sinr_multinode_spatial_table.csv')

print("Generating Figure 5: Multi-HAPS Interference (100 km Service Footprint)...")

fig, ax = plt.subplots(figsize=(12, 7))
fig.patch.set_facecolor('#FFFFFF')
ax.set_facecolor('#F5F5F5')

# Landscape-independent (S:III.C; Arani et al. Eq. 2): all four environments
# produce numerically identical SINR at the HAPS tier, so a single line is
# the honest representation -- four overlapping lines with a 4-entry legend
# previously hid three of them behind whichever was drawn last.
landscapes = ['suburban', 'urban', 'dense_urban', 'high_rise']
df_check = df[df['environment'].isin(landscapes)]
assert df_check.groupby(['distance_km', 'angle_deg'])['SINR_dB'].nunique().max() == 1, \
    "Landscapes are no longer identical -- revert to per-landscape plotting"

stats = df[df['environment'] == 'suburban'].groupby('distance_km')['SINR_dB'].agg(['min', 'mean', 'max'])
distances = stats.index.values

ax.plot(distances, stats['mean'], linewidth=2.5, label='Mean SINR (identical for all 4 landscapes)',
        marker='o', markersize=6, color='#1976D2', markeredgecolor='white', markeredgewidth=0.5)
ax.fill_between(distances, stats['min'], stats['max'], alpha=0.15, color='#1976D2',
                label='Angular min-max spread (24 positions)')

# Secondary right-hand axis: elevation angle at the user (HAPS-UE-Origin),
# arctan(altitude/horizontal distance) -- same distances as the x-axis above.
HAPS_ALT_KM = 20.0
elevation_deg = np.degrees(np.arctan2(HAPS_ALT_KM, distances))
ax2 = ax.twinx()
ax2.plot(distances, elevation_deg, linestyle=':', linewidth=1.5, color='#555555', alpha=0.7)
ax2.set_ylabel('Elevation Angle [deg]', fontsize=12, fontweight='bold', color='#555555')
ax2.tick_params(axis='y', labelcolor='#555555')
ax2.set_ylim([0, 95])

# Labels and title
ax.set_xlabel('Effective Distance from Nadir [km]', fontsize=12, fontweight='bold', color='#333333')
ax.set_ylabel('SINR [dB]', fontsize=12, fontweight='bold', color='#333333')

ax.set_title('Figure 5: Multi-HAPS Interference – Signal Power Attenuation Across 100 km Service Footprint\n' +
             'Mean SINR (landscape-independent, S:III.C); shaded band = spatial variation (min-max) across 24 angles\n' +
             'around the fixed 65 km equilateral 3-HAPS constellation (interferer geometry, not landscape)',
             fontsize=13, fontweight='bold', color='#333333', pad=20)

ax.grid(True, alpha=0.3, linestyle='--', color='#CCCCCC', linewidth=0.8)
ax.tick_params(colors='#333333', labelsize=10)

# Styling
ax.set_xlim([0, 105])
ax.set_ylim([-15, 6])

# Legend
legend = ax.legend(fontsize=10, loc='lower left', framealpha=0.95, facecolor='#FFFFFF', edgecolor='#333333', ncol=1)
for text in legend.get_texts():
    text.set_color('#333333')

plt.tight_layout()
plt.savefig('output/5_multi_node_sinr.png', facecolor='#FFFFFF', dpi=150, bbox_inches='tight')
print("Success: Chart '5_multi_node_sinr.png' generated.")
plt.close()

# Print statistics for all landscapes
print("\nFigure 5 Statistics (All Landscapes):")
print("=" * 90)
for env in landscapes:
    df_env = df[df['environment'] == env]
    stats = df_env.groupby('distance_km')['SINR_dB'].agg(['min', 'mean', 'max'])
    print(f"\n{env.upper()}:")
    print(f"{'Distance (km)':>12} | {'Min SINR':>10} | {'Mean SINR':>10} | {'Max SINR':>10} | {'Variation':>10}")
    print("-" * 60)
    for idx, dist in enumerate(stats.index):
        var = stats['max'].iloc[idx] - stats['min'].iloc[idx]
        print(f"{dist:>12.1f} | {stats['min'].iloc[idx]:>10.2f} | {stats['mean'].iloc[idx]:>10.2f} | {stats['max'].iloc[idx]:>10.2f} | {var:>10.2f}")
print("=" * 90)
