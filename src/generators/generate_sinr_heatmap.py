#!/usr/bin/env python3
"""
Phase 4: Generate SINR Spatial Heatmap

Creates 2D heatmap showing SINR variation across:
- X-axis: Direction angle (0-360°)
- Y-axis: Distance radius (0-100 km)

Output: sinr_heatmap_spatial.png

For integration into LaTeX Figure 10 (Multi-Distance SINR Heatmap)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patches as mpatches

def load_spatial_data():
    """Load SINR spatial table (from Phase 3.2)"""
    df = pd.read_csv('output/sinr_multinode_spatial_table.csv')
    # Filter to suburban landscape for clarity
    df = df[df['environment'] == 'suburban']
    return df

def create_heatmap():
    """Generate 2D SINR heatmap (distance vs angle)"""

    # Load data
    df = load_spatial_data()

    # Compute worst/best dynamically at r=50km (was previously hardcoded and
    # went stale across geometry/path-loss fixes)
    df_50 = df[df['distance_km'] == 50]
    worst_row = df_50.loc[df_50['SINR_dB'].idxmin()]
    best_row = df_50.loc[df_50['SINR_dB'].idxmax()]
    variation_50 = best_row['SINR_dB'] - worst_row['SINR_dB']

    # Pivot to create grid
    # X = angle, Y = distance, Z = SINR
    pivot_data = df.pivot_table(
        values='SINR_dB',
        index='distance_km',
        columns='angle_deg',
        aggfunc='mean'
    )

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))

    # Custom colormap: red (bad) -> yellow (marginal) -> green (good)
    colors_list = ['#d73027', '#fee08b', '#91bfdb', '#1a9850']  # Red, Yellow, Light Blue, Green
    n_bins = 100
    cmap = LinearSegmentedColormap.from_list('sinr', colors_list, N=n_bins)

    # Plot heatmap
    im = ax.imshow(
        pivot_data.values,
        aspect='auto',
        cmap=cmap,
        origin='lower',
        extent=[0, 360, 0, 100],
        vmin=-15,
        vmax=5,
        interpolation='bilinear'
    )

    # Colorbar
    cbar = plt.colorbar(im, ax=ax, label='SINR [dB]')
    cbar.set_ticks([-15, -10, -5, 0, 5])

    # Labels
    ax.set_xlabel('Direction Angle from Nadir [degrees]', fontsize=13, fontweight='bold')
    ax.set_ylabel('Distance from Nadir [km]', fontsize=13, fontweight='bold')
    ax.set_title('SINR Spatial Heterogeneity: 2D Distribution in Triangular Constellation\n' +
                 'Landscape-independent (pure FSPL) | HAPS Altitude 20 km | Frequency 2 GHz',
                 fontsize=14, fontweight='bold', pad=20)

    # Add grid
    ax.grid(True, alpha=0.3, linestyle=':', color='white', linewidth=0.5)

    # Angle ticks
    ax.set_xticks([0, 45, 90, 135, 180, 225, 270, 315, 360])
    ax.set_xticklabels(['0° (I1)', '45°', '90°', '135°', '180° (Away)', '225°', '270°', '315°', '360°'])

    # Distance ticks
    ax.set_yticks([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])

    # Add annotations for key points (computed dynamically above, not hardcoded)
    ax.plot(worst_row['angle_deg'], 50, 'r*', markersize=20, markeredgewidth=2, markeredgecolor='darkred',
            label=f"Worst (r=50, θ={worst_row['angle_deg']:.0f}°, SINR={worst_row['SINR_dB']:.2f} dB)", zorder=5)

    ax.plot(best_row['angle_deg'], 50, 'g*', markersize=20, markeredgewidth=2, markeredgecolor='darkgreen',
            label=f"Best (r=50, θ={best_row['angle_deg']:.0f}°, SINR={best_row['SINR_dB']:.2f} dB)", zorder=5)

    # Add text box with findings
    textstr = 'Spatial Heterogeneity:\n' + \
              f'At r = 50 km: SINR varies {variation_50:.2f} dB\n' + \
              f"Worst: θ = {worst_row['angle_deg']:.0f}°\n" + \
              f"Best: θ = {best_row['angle_deg']:.0f}°\n" + \
              'Variation is geometric (interferer proximity), not landscape-dependent'

    props = dict(boxstyle='round', facecolor='wheat', alpha=0.9, edgecolor='black', linewidth=2)
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
           verticalalignment='top', bbox=props, family='monospace')

    ax.legend(fontsize=11, loc='lower right', framealpha=0.95)

    plt.tight_layout()
    plt.savefig('output/sinr_heatmap_spatial.png', dpi=150, bbox_inches='tight', facecolor='white')
    print("[OK] Saved: sinr_heatmap_spatial.png")

    return fig, ax, pivot_data

def print_statistics(df):
    """Print summary statistics"""
    print()
    print("=" * 90)
    print("SINR SPATIAL HEATMAP STATISTICS")
    print("=" * 90)
    print()

    # Overall stats
    print(f"Overall SINR range: {df['SINR_dB'].min():.2f} to {df['SINR_dB'].max():.2f} dB")
    print(f"Overall SINR mean: {df['SINR_dB'].mean():.2f} dB")
    print()

    # By distance
    print("SINR Statistics by Distance:")
    print("-" * 90)
    print(f"{'Distance':>8} | {'Min':>8} | {'Max':>8} | {'Mean':>8} | {'Std':>8} | {'Variation':>10}")
    print("-" * 90)

    for r in sorted(df['distance_km'].unique()):
        df_r = df[df['distance_km'] == r]
        sinrs = df_r['SINR_dB'].values
        print(f"{r:>8.0f} | {np.min(sinrs):>8.2f} | {np.max(sinrs):>8.2f} | {np.mean(sinrs):>8.2f} | {np.std(sinrs):>8.2f} | {np.max(sinrs)-np.min(sinrs):>10.2f}")

    print()
    print("=" * 90)

if __name__ == '__main__':
    print("Generating SINR Spatial Heatmap...")
    print()

    # Load and plot
    df = load_spatial_data()
    print_statistics(df)

    fig, ax, pivot = create_heatmap()
    plt.close()

    print()
    print("=" * 90)
    print("Phase 4: SINR Heatmap Generation COMPLETE")
    print("=" * 90)
    print()
    print("Output file: sinr_heatmap_spatial.png")
    print("Use in LaTeX: \\includegraphics[width=0.9\\textwidth]{figures/sinr_heatmap_spatial.png}")
    print()
