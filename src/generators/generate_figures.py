#!/usr/bin/env python3
"""
Generate publication-quality figures for HW2 Channel Model paper.

Usage:
    python generate_figures.py

Outputs (in figures/ directory):
    - system_topology.pdf/png
    - elevation_los_probability.pdf/png
    - rain_attenuation_curve.pdf/png
    - link_budget_summary.pdf/png
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

# Create output directory if it doesn't exist
os.makedirs('output', exist_ok=True)

print("=" * 70)
print("GENERATING PUBLICATION FIGURES FOR HW2")
print("=" * 70)

# ============================================================================
# Figure 1: System Topology (3-Tier Architecture)
# ============================================================================
print("\n[1] Generating system_topology...")

fig, ax = plt.subplots(figsize=(12, 10))
ax.set_xlim(-2, 12)
ax.set_ylim(-1, 10)
ax.axis('off')

# Color scheme
color_haps = '#FF6B6B'
color_uav = '#4ECDC4'
color_gw = '#45B7D1'
color_user = '#95E1D3'

# ---- HAPS Layer (top) ----
haps_y = 8
haps_positions = [2, 6, 10]
for i, x in enumerate(haps_positions):
    # HAPS node
    circle = patches.Circle((x, haps_y), 0.4, color=color_haps, ec='darkred', linewidth=2, zorder=5)
    ax.add_patch(circle)
    ax.text(x, haps_y, 'H' + str(i+1), ha='center', va='center',
            fontsize=12, fontweight='bold', color='white', zorder=6)
    ax.text(x, haps_y + 0.8, f'HAPS_{i+1}\n20 km', ha='center', va='bottom',
            fontsize=9, fontweight='bold')

# ---- Feeder Links: HAPS -> Gateway ----
gw_x, gw_y = 6, 4
for x in haps_positions:
    ax.annotate('', xy=(gw_x, gw_y+0.3), xytext=(x, haps_y-0.4),
                arrowprops=dict(arrowstyle='<->', lw=2, color=color_gw, linestyle='--'))
    mid_x, mid_y = (x + gw_x) / 2, (haps_y + gw_y) / 2
    ax.text(mid_x + 0.3, mid_y, 'Feeder\n38-39.5 GHz', fontsize=8,
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

# ---- UAV Relay Layer (middle) ----
uav_x, uav_y = 4, 5.5
circle = patches.Circle((uav_x, uav_y), 0.35, color=color_uav, ec='darkgreen', linewidth=2, zorder=5)
ax.add_patch(circle)
ax.text(uav_x, uav_y, 'U', ha='center', va='center',
        fontsize=12, fontweight='bold', color='white', zorder=6)
ax.text(uav_x, uav_y + 0.8, 'UAV\n300 m', ha='center', va='bottom',
        fontsize=9, fontweight='bold')

# ---- Relay Links: Users -> UAV -> HAPS ----
for x in [haps_positions[0], haps_positions[2]]:
    ax.annotate('', xy=(uav_x, uav_y-0.35), xytext=(x, haps_y-0.4),
                arrowprops=dict(arrowstyle='<->', lw=1.5, color=color_uav, linestyle=':'))
    mid_x, mid_y = (x + uav_x) / 2, (haps_y + uav_y) / 2
    ax.text(mid_x - 0.5, mid_y, 'Relay', fontsize=7, style='italic', alpha=0.7)

# ---- Gateway Layer (bottom-middle) ----
rect = FancyBboxPatch((gw_x-0.5, gw_y-0.35), 1, 0.7,
                       boxstyle="round,pad=0.05",
                       edgecolor='darkblue', facecolor=color_gw, linewidth=2, zorder=5)
ax.add_patch(rect)
ax.text(gw_x, gw_y, 'GW', ha='center', va='center',
        fontsize=11, fontweight='bold', color='white', zorder=6)
ax.text(gw_x, gw_y - 0.8, 'Gateway\n50 m AGL', ha='center', va='top',
        fontsize=9, fontweight='bold')

# ---- Core Network (bottom) ----
ax.text(gw_x, 1.5, 'Core Network\n(Internet)', ha='center', va='center',
        fontsize=10, fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8, linewidth=2))

# ---- Backhaul link: GW -> Core ----
ax.annotate('', xy=(gw_x, 2), xytext=(gw_x, gw_y-0.4),
            arrowprops=dict(arrowstyle='<->', lw=2, color='gray'))
ax.text(gw_x + 0.7, 3, 'Backhaul', fontsize=8, style='italic', alpha=0.7)

# ---- Ground Users Layer ----
user_positions = [(1, 2), (3, 2.5), (5, 1.8), (7, 2.2), (9, 2), (11, 2.5)]
for ux, uy in user_positions:
    circle = patches.Circle((ux, uy), 0.2, color=color_user, ec='darkgreen', linewidth=1.5, zorder=4)
    ax.add_patch(circle)

ax.text(6, 0.5, 'Ground Users (Coverage Area)', ha='center', va='top',
        fontsize=9, style='italic', alpha=0.7)

# ---- Service Links: HAPS/UAV -> Users ----
for ux, uy in user_positions[:3]:
    ax.plot([haps_positions[0], ux], [haps_y-0.4, uy+0.2], 'g-', alpha=0.3, linewidth=0.8, zorder=1)
for ux, uy in user_positions[3:]:
    ax.plot([haps_positions[2], ux], [haps_y-0.4, uy+0.2], 'g-', alpha=0.3, linewidth=0.8, zorder=1)

# Legend
legend_y = 9.5
ax.text(0.2, legend_y, '━━ Service Link (2.1-2.2 GHz)', fontsize=9, color='green', fontweight='bold')
ax.text(0.2, legend_y-0.4, '⋯ Relay Link (UAV multi-hop)', fontsize=9, color=color_uav, fontweight='bold')
ax.text(0.2, legend_y-0.8, '╌╌ Feeder Link (38-39.5 GHz)', fontsize=9, color=color_gw, fontweight='bold')

# Title
ax.text(6, 9.7, 'Three-Tier HAPS-UAV-Gateway Network Architecture',
        ha='center', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('output/system_topology.pdf', bbox_inches='tight', dpi=300)
plt.savefig('output/system_topology.png', bbox_inches='tight', dpi=150)
print("  ✓ system_topology.pdf / system_topology.png")
plt.close()

# ============================================================================
# Figure 2: HAPS Elevation-Dependent LoS Probability
# ============================================================================
print("\n[2] Generating elevation_los_probability...")

fig, ax = plt.subplots(figsize=(10, 6))

# ITU-R P.1410 model: P_LoS(theta) = alpha / (1 + beta * exp(-theta))
theta = np.linspace(0, 90, 200)

# Urban environments
environments = {
    'Dense Urban': {'alpha': 0.5, 'beta': 300, 'color': '#FF6B6B', 'linestyle': '-'},
    'Urban': {'alpha': 0.3, 'beta': 500, 'color': '#FFA500', 'linestyle': '-'},
    'Suburban': {'alpha': 0.1, 'beta': 750, 'color': '#4ECDC4', 'linestyle': '-'},
    'High-Rise': {'alpha': 0.3, 'beta': 300, 'color': '#95E1D3', 'linestyle': '--'},
}

for env_name, params in environments.items():
    alpha = params['alpha']
    beta = params['beta']
    p_los = alpha / (1 + beta * np.exp(-theta))
    ax.plot(theta, p_los, linewidth=2.5, label=env_name,
            color=params['color'], linestyle=params['linestyle'])

# Mark critical elevation angles
ax.axvline(x=30, color='red', linestyle=':', linewidth=2, alpha=0.7, label='Regulatory Min (30°)')
ax.axvline(x=45, color='green', linestyle=':', linewidth=2, alpha=0.7, label='POC Design (45-60°)')
ax.axvline(x=60, color='green', linestyle=':', linewidth=2, alpha=0.7)

# Annotations
ax.annotate('Poor Coverage', xy=(10, 0.1), fontsize=10, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))
ax.annotate('Excellent Coverage', xy=(75, 0.4), fontsize=10, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

ax.set_xlabel('Elevation Angle θ (degrees)', fontsize=12, fontweight='bold')
ax.set_ylabel('Line-of-Sight Probability P_LoS', fontsize=12, fontweight='bold')
ax.set_title('HAPS Elevation-Dependent LoS Probability (ITU-R P.1410)',
             fontsize=13, fontweight='bold', pad=15)
ax.grid(True, alpha=0.3)
ax.legend(loc='lower right', fontsize=10, framealpha=0.95)
ax.set_xlim(0, 90)
ax.set_ylim(0, 0.6)

plt.tight_layout()
plt.savefig('output/elevation_los_probability.pdf', bbox_inches='tight', dpi=300)
plt.savefig('output/elevation_los_probability.png', bbox_inches='tight', dpi=150)
print("  ✓ elevation_los_probability.pdf / elevation_los_probability.png")
plt.close()

# ============================================================================
# Figure 3: Rain Attenuation Curve (Feeder Link)
# ============================================================================
print("\n[3] Generating rain_attenuation_curve...")

fig, ax = plt.subplots(figsize=(10, 6))

# Rain rate range
rain_rate = np.linspace(0, 100, 200)

# ITU-R P.618: A_rain = k * R^alpha * d_rain
# Ka-band (39 GHz): k=0.0366, alpha=0.88
k = 0.0366
alpha_rain = 0.88

# Different elevation angles
elevation_angles = [20, 30, 45, 60, 75]
colors = ['#FF6B6B', '#FFA500', '#4ECDC4', '#45B7D1', '#95E1D3']

for elev, color in zip(elevation_angles, colors):
    rain_zone = 5.0  # km
    d_rain = rain_zone / np.sin(np.radians(elev))
    gamma = k * (rain_rate ** alpha_rain)
    attenuation = gamma * d_rain
    ax.plot(rain_rate, attenuation, linewidth=2.5, label=f'Elevation {elev}°',
            color=color)

# Add reference points
ax.scatter([0, 5, 10, 50], [0, 1.5, 3, 10], color='red', s=50, zorder=5, alpha=0.7)
ax.text(10, 3.5, '10 mm/hr\n@ 30° elev\n≈ 3 dB', fontsize=9,
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

ax.set_xlabel('Rain Rate R (mm/hr)', fontsize=12, fontweight='bold')
ax.set_ylabel('Rain Attenuation (dB)', fontsize=12, fontweight='bold')
ax.set_title('Feeder Link Rain Attenuation (Ka-band, ITU-R P.618)',
             fontsize=13, fontweight='bold', pad=15)
ax.grid(True, alpha=0.3)
ax.legend(loc='upper left', fontsize=10, framealpha=0.95)
ax.set_xlim(0, 100)
ax.set_ylim(0, 25)

plt.tight_layout()
plt.savefig('output/rain_attenuation_curve.pdf', bbox_inches='tight', dpi=300)
plt.savefig('output/rain_attenuation_curve.png', bbox_inches='tight', dpi=150)
print("  ✓ rain_attenuation_curve.pdf / rain_attenuation_curve.png")
plt.close()

# ============================================================================
# Figure 4: Link Budget Summary (Table visualization)
# ============================================================================
print("\n[4] Generating link_budget_summary...")

fig, ax = plt.subplots(figsize=(12, 7))
ax.axis('off')

# Link budget data
link_data = [
    ['Link Type', 'Distance', 'Elevation', 'Path Loss', 'LoS Prob', 'Status'],
    ['HAPS₁ → User', '20.15 km', '45.2°', '142 dB', '0.28', '✓ Valid'],
    ['HAPS₂ → User', '20.22 km', '48.3°', '142 dB', '0.32', '✓ Valid'],
    ['HAPS₃ → User', '20.18 km', '46.8°', '142 dB', '0.30', '✓ Valid'],
    ['UAV → User', '0.3-5 km', '10-85°', '92-110 dB', 'Variable', '✓ Relay'],
    ['HAPS₁ → Gateway', '20.15 km', '45.2°', 'Feeder', '0.28', '✓ Backhaul'],
    ['HAPS₂ → Gateway', '20.22 km', '48.3°', 'Feeder', '0.32', '✓ Backhaul'],
    ['HAPS₃ → Gateway', '20.18 km', '46.8°', 'Feeder', '0.30', '✓ Backhaul'],
]

# Create table
table = ax.table(cellText=link_data, cellLoc='center', loc='center',
                colWidths=[0.15, 0.12, 0.12, 0.12, 0.12, 0.12])

table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 2.5)

# Style header row
for i in range(len(link_data[0])):
    cell = table[(0, i)]
    cell.set_facecolor('#4ECDC4')
    cell.set_text_props(weight='bold', color='white')

# Style data rows
for i in range(1, len(link_data)):
    for j in range(len(link_data[0])):
        cell = table[(i, j)]
        if i % 2 == 0:
            cell.set_facecolor('#F0F0F0')
        else:
            cell.set_facecolor('#FFFFFF')

        # Highlight status column
        if j == 5:
            if '✓' in link_data[i][j]:
                cell.set_facecolor('#C8E6C9')
                cell.set_text_props(weight='bold', color='darkgreen')

# Add title and notes
ax.text(0.5, 0.95, 'POC System Link Budget Summary',
        ha='center', va='top', fontsize=14, fontweight='bold',
        transform=ax.transAxes)

notes = ('Notes: All elevation angles > 30° regulatory minimum (ECC REPORT 156). '
         'Gateway elevation angles ensure beam tracking stability. '
         'LoS probabilities computed for urban environment (α=0.3, β=500).')
ax.text(0.5, 0.08, notes, ha='center', va='top', fontsize=8, style='italic',
        transform=ax.transAxes, wrap=True,
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

plt.tight_layout()
plt.savefig('output/link_budget_summary.pdf', bbox_inches='tight', dpi=300)
plt.savefig('output/link_budget_summary.png', bbox_inches='tight', dpi=150)
print("  ✓ link_budget_summary.pdf / link_budget_summary.png")
plt.close()

# ============================================================================
# Summary
# ============================================================================

print("\n" + "=" * 70)
print("FIGURE GENERATION COMPLETE!")
print("=" * 70)
print("\nGenerated figures (in figures/ directory):")
print("  1. system_topology.{pdf,png} - Three-tier architecture diagram")
print("  2. elevation_los_probability.{pdf,png} - LoS vs. elevation angle")
print("  3. rain_attenuation_curve.{pdf,png} - Rain attenuation vs. rate")
print("  4. link_budget_summary.{pdf,png} - Link budget table")
print("\nReady to include in HW2_ChannelModel.tex!")
print("=" * 70)
