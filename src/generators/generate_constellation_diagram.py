#!/usr/bin/env python3
"""
Phase 4: Generate Constellation Geometry Diagram

Shows:
- Fixed constellation positions (S, I1, I2)
- User positions at r=50 km for all angles
- SINR zones (green=good, red=bad)
- Interference "shadows"

Output: constellation_with_sectors.png

For integration into LaTeX Figure 11 (Constellation Geometry with Spatial Sectors)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch
from matplotlib.collections import PatchCollection
import matplotlib.patches as mpatches

def load_spatial_data_50km():
    """Load SINR data at r=50 km only"""
    df = pd.read_csv('output/sinr_multinode_spatial_table.csv')
    df = df[(df['distance_km'] == 50) & (df['environment'] == 'suburban')]
    return df

def create_constellation_diagram():
    """Generate constellation map with spatial sectors"""

    df = load_spatial_data_50km()

    # Compute worst/best dynamically from the loaded data (was previously
    # hardcoded and went stale across geometry/path-loss fixes)
    worst_row = df.loc[df['SINR_dB'].idxmin()]
    best_row = df.loc[df['SINR_dB'].idxmax()]

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 12))

    # Constellation positions (in km) -- true 65km equilateral triangle,
    # matching haps_constellation_geometry() in channel_model.py. Previously
    # hardcoded as (37.5, +/-21.7), an older non-equilateral layout that no
    # longer matches the data being plotted.
    SPACING_KM = 65.0
    S = np.array([0.0, 0.0])
    I1 = np.array([SPACING_KM, 0.0])
    I2 = np.array([SPACING_KM / 2.0, SPACING_KM * np.sqrt(3.0) / 2.0])

    # Draw constellation
    ax.plot(*S, 'b*', markersize=40, markeredgewidth=2, markeredgecolor='darkblue',
            label='S (Serving HAPS)', zorder=10)
    ax.plot(*I1, 'rs', markersize=15, markeredgewidth=2, markeredgecolor='darkred',
            label='I1 (Interferer)', zorder=10)
    ax.plot(*I2, 'rs', markersize=15, markeredgewidth=2, markeredgecolor='darkred',
            label='I2 (Interferer)', zorder=10)

    # Draw triangle
    triangle = np.array([S, I1, I2, S])
    ax.plot(triangle[:, 0], triangle[:, 1], 'k--', linewidth=1.5, alpha=0.4, label='Constellation (65 km triangle)')

    # Plot user positions at r=50 km with SINR color coding
    sinr_values = df.sort_values('angle_deg')['SINR_dB'].values
    angles = np.radians(df.sort_values('angle_deg')['angle_deg'].values)
    r = 50

    # Normalize SINR for coloring (-15 to +5 dB range)
    sinr_normalized = np.clip((sinr_values + 15) / 20, 0, 1)

    for angle, sinr, sinr_norm in zip(angles, sinr_values, sinr_normalized):
        user_x = r * np.cos(angle)
        user_y = r * np.sin(angle)

        # Color: red (bad) -> yellow (marginal) -> green (good)
        if sinr < -5:
            color = '#d73027'  # Dark red
        elif sinr < 0:
            color = '#fee08b'  # Yellow
        elif sinr < 2:
            color = '#91bfdb'  # Light blue
        else:
            color = '#1a9850'  # Green

        # Plot user as circle with SINR color
        circle = Circle((user_x, user_y), radius=1.5, color=color, alpha=0.8, zorder=5, edgecolor='black', linewidth=0.5)
        ax.add_patch(circle)

        # Add SINR value label (every 45 degrees for clarity)
        angle_deg = np.degrees(angle)
        if angle_deg % 45 == 0 or abs(angle_deg - 30) < 5:  # Label key angles
            ax.text(user_x * 1.12, user_y * 1.12, f'{sinr:.1f}dB', fontsize=8, ha='center', va='center',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'))

    # Draw coverage circle at r=50 km
    circle_50 = Circle((0, 0), 50, fill=False, edgecolor='gray', linestyle=':', linewidth=2, alpha=0.6)
    ax.add_patch(circle_50)
    ax.text(50, 5, 'r = 50 km', fontsize=11, fontweight='bold', color='gray')

    # Add annotations for best and worst locations (dynamic, computed above)
    worst_angle_rad = np.radians(worst_row['angle_deg'])
    worst_x = 50 * np.cos(worst_angle_rad)
    worst_y = 50 * np.sin(worst_angle_rad)
    ax.annotate(f"WORST\n({worst_row['SINR_dB']:.2f} dB)", xy=(worst_x, worst_y), xytext=(worst_x-20, worst_y+15),
               fontsize=11, fontweight='bold', color='darkred',
               bbox=dict(boxstyle='round', facecolor='#ffcccc', edgecolor='darkred', linewidth=2),
               arrowprops=dict(arrowstyle='->', color='darkred', lw=2))

    best_angle_rad = np.radians(best_row['angle_deg'])
    best_x = 50 * np.cos(best_angle_rad)
    best_y = 50 * np.sin(best_angle_rad)
    ax.annotate(f"BEST\n(+{best_row['SINR_dB']:.2f} dB)", xy=(best_x, best_y), xytext=(best_x-20, best_y-15),
               fontsize=11, fontweight='bold', color='darkgreen',
               bbox=dict(boxstyle='round', facecolor='#ccffcc', edgecolor='darkgreen', linewidth=2),
               arrowprops=dict(arrowstyle='->', color='darkgreen', lw=2))

    # Add sector zones as background shading (optional, centered dynamically
    # on the actual best/worst angles rather than a hardcoded assumption --
    # the true equilateral triangle (I1 @ 0 deg, I2 @ 60 deg) is asymmetric,
    # unlike the old (37.5, +/-21.7) layout this used to assume)
    good_center = np.radians(best_row['angle_deg'])
    theta_good = np.linspace(good_center - np.radians(60), good_center + np.radians(60), 100)
    x_good = 60 * np.cos(theta_good)
    y_good = 60 * np.sin(theta_good)
    ax.fill(x_good, y_good, color='green', alpha=0.05, zorder=1)
    ax.text(x_good.mean(), y_good.mean(), 'GOOD\nSECTOR', fontsize=11, fontweight='bold', color='darkgreen', alpha=0.6)

    bad_center = np.radians(worst_row['angle_deg'])
    theta_bad = np.linspace(bad_center - np.radians(60), bad_center + np.radians(60), 100)
    x_bad = 60 * np.cos(theta_bad)
    y_bad = 60 * np.sin(theta_bad)
    ax.fill(x_bad, y_bad, color='red', alpha=0.05, zorder=1)
    ax.text(x_bad.mean(), y_bad.mean(), 'BAD SECTOR', fontsize=11, fontweight='bold', color='darkred', alpha=0.6)

    # Labels and formatting
    ax.set_xlabel('X Distance from Nadir [km]', fontsize=13, fontweight='bold')
    ax.set_ylabel('Y Distance from Nadir [km]', fontsize=13, fontweight='bold')
    ax.set_title('HAPS Constellation Geometry with Spatial SINR Sectors\n' +
                 'User positions at r = 50 km | Circle color = SINR value\n' +
                 f"Red=Bad ({worst_row['SINR_dB']:.2f} dB) | Yellow=Marginal | Green=Good (+{best_row['SINR_dB']:.2f} dB)",
                 fontsize=14, fontweight='bold', pad=20)

    ax.set_xlim(-80, 80)
    ax.set_ylim(-80, 80)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.2, linestyle=':', color='gray')

    # Legend with SINR color scale
    red_patch = mpatches.Patch(color='#d73027', label='SINR < -5 dB (Severe)')
    yellow_patch = mpatches.Patch(color='#fee08b', label='-5 ≤ SINR < 0 dB (Marginal)')
    blue_patch = mpatches.Patch(color='#91bfdb', label='0 ≤ SINR < 2 dB (Acceptable)')
    green_patch = mpatches.Patch(color='#1a9850', label='SINR ≥ 2 dB (Good)')

    ax.legend(handles=[
        mpatches.Patch(color='b', label='S (Serving)', alpha=0.7),
        mpatches.Patch(color='r', label='I1, I2 (Interferers)', alpha=0.7),
        red_patch, yellow_patch, blue_patch, green_patch
    ], fontsize=11, loc='upper left', framealpha=0.95)

    plt.tight_layout()
    plt.savefig('output/constellation_with_sectors.png', dpi=150, bbox_inches='tight', facecolor='white')
    print("[OK] Saved: constellation_with_sectors.png")

    return fig, ax

def main():
    print("Generating Constellation Geometry Diagram...")
    print()

    df = load_spatial_data_50km()
    print(f"Loaded {len(df)} user positions at r = 50 km")
    print()

    print("SINR Statistics at r = 50 km:")
    print(f"  Minimum SINR: {df['SINR_dB'].min():.2f} dB at angle {df.loc[df['SINR_dB'].idxmin(), 'angle_deg']:.0f}°")
    print(f"  Maximum SINR: {df['SINR_dB'].max():.2f} dB at angle {df.loc[df['SINR_dB'].idxmax(), 'angle_deg']:.0f}°")
    print(f"  Mean SINR:    {df['SINR_dB'].mean():.2f} dB")
    print(f"  Variation:    {df['SINR_dB'].max() - df['SINR_dB'].min():.2f} dB")
    print()

    create_constellation_diagram()

    print("=" * 90)
    print("Phase 4: Constellation Diagram Generation COMPLETE")
    print("=" * 90)
    print()
    print("Output file: constellation_with_sectors.png")
    print("Use in LaTeX: \\includegraphics[width=0.9\\textwidth]{figures/constellation_with_sectors.png}")
    print()

if __name__ == '__main__':
    main()
