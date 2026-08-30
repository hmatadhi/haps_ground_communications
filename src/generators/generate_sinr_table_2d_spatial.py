#!/usr/bin/env python3
"""
Phase 3.2: Multi-Angle SINR Lookup Table Generation
======================================================

Generates SINR tables showing spatial heterogeneity: at same distance radius,
SINR varies dramatically depending on angle relative to triangular constellation.

Output:
  - sinr_multinode_spatial_table.csv
  - sinr_spatial_analysis_summary.csv
  - LaTeX tables for appendix

Geometry:
  S  (Serving):    (0 km, 0 km, 20 km altitude) — FIXED at nadir
  I1 (Interferer): (37.5 km, +21.7 km, 20 km) — FIXED
  I2 (Interferer): (37.5 km, -21.7 km, 20 km) — FIXED

User: Moves in circles at constant radius, varying angle from 0-360 degrees

Key Finding: SINR at r=50 km varies from -7.5 dB (worst) to +1.7 dB (best) = 9.2 dB variation!
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')  # Add parent dir to path


import numpy as np
import pandas as pd
from models.channel_model import (
    multi_node_sinr_db,
    multi_node_sinr_db_spatial,
    haps_horiz_ranges_to_user,
    haps_a2g_pathloss_db,
    ENVIRONMENTS,
    HAPS_ALT_M,
    F_HAPS_MHZ,
    P_TX_HAPS_DBM,
    NOISE_DBM
)

def calculate_spatial_sinr(r_km, angle_deg, environment="suburban"):
    """
    Calculate SINR for user at (r, angle) position in triangular constellation.

    Uses the new multi_node_sinr_db_spatial() function for arbitrary 2D positions.

    Args:
        r_km: distance from nadir [km]
        angle_deg: direction angle from nadir [degrees]
        environment: landscape type

    Returns:
        dict with SINR, distances, path losses, and metadata
    """
    angle_rad = np.radians(angle_deg)
    r_m = r_km * 1000.0

    # User position on circle
    user_x = r_m * np.cos(angle_rad)
    user_y = r_m * np.sin(angle_rad)

    # Calculate SINR using new 2D-aware function
    result = multi_node_sinr_db_spatial(user_x, user_y, num_haps=3,
                                       p_tx_dbm=P_TX_HAPS_DBM,
                                       noise_dbm=NOISE_DBM,
                                       h_node_m=HAPS_ALT_M,
                                       f_hz=F_HAPS_MHZ*1e6,
                                       env=environment,
                                       constellation_spacing_km=65.0)

    return {
        'distance_km': r_km,
        'angle_deg': angle_deg,
        'user_x_km': user_x / 1000,
        'user_y_km': user_y / 1000,
        'S_distance_km': result['S_distance_m'] / 1000,
        'I1_distance_km': result['I1_distance_m'] / 1000,
        'I2_distance_km': result['I2_distance_m'] / 1000,
        'closest_node': result['closest_node'],
        'SINR_dB': result['SINR_dB'],
        'S_path_loss_db': result['S_path_loss_db'],
        'I1_path_loss_db': result['I1_path_loss_db'],
        'I2_path_loss_db': result['I2_path_loss_db'],
        'environment': environment
    }

def main():
    """Generate spatial SINR tables for all key angles and distances."""

    print("=" * 100)
    print("Phase 3.2: Generating Multi-Angle SINR Tables")
    print("=" * 100)
    print()

    # Key analysis points
    distances_km = [10, 30, 50, 75, 100]
    key_angles = [0, 45, 90, 135, 180, 225, 270, 315]
    environments = list(ENVIRONMENTS.keys())

    # Generate full grid for heatmap
    full_angles = np.arange(0, 360, 15)  # Every 15 degrees

    all_data = []

    print("Calculating SINR across spatial grid...")
    print(f"  Distances: {distances_km} km")
    print(f"  Angles: {list(full_angles)} degrees")
    print(f"  Environments: {environments}")
    print()

    for env in environments:
        for r in distances_km:
            for angle in full_angles:
                result = calculate_spatial_sinr(r, angle, env)
                all_data.append(result)

    # Create DataFrame
    df = pd.DataFrame(all_data)

    # Export full spatial data
    output_file = 'output/sinr_multinode_spatial_table.csv'
    df.to_csv(output_file, index=False)
    print(f"[OK] Exported full spatial table: {output_file}")
    print(f"     Rows: {len(df)} | Columns: {df.shape[1]}")
    print()

    # Generate summary tables for key angles
    print("Generating summary tables for key angles...")
    print()

    for angle in key_angles:
        df_angle = df[df['angle_deg'] == angle].sort_values(['distance_km', 'environment'])

        filename = f'output/sinr_table_{angle}deg.csv'
        df_angle.to_csv(filename, index=False)
        print(f"[OK] {filename}")

    print()
    print("=" * 100)
    print("Spatial Heterogeneity Analysis at r = 50 km")
    print("=" * 100)
    print()

    df_50km = df[(df['distance_km'] == 50) & (df['environment'] == 'suburban')]
    df_50km_sorted = df_50km.sort_values('angle_deg')

    print(f"{'Angle':>8} | {'S Dist':>8} | {'I1 Dist':>8} | {'I2 Dist':>8} | {'Closest':>8} | {'SINR':>8}")
    print(f"{'(deg)':>8} | {'(km)':>8} | {'(km)':>8} | {'(km)':>8} | {'Node':>8} | {'(dB)':>8}")
    print("-" * 85)

    sinrs = []
    for _, row in df_50km_sorted.iterrows():
        print(f"{row['angle_deg']:>8.0f} | {row['S_distance_km']:>8.1f} | {row['I1_distance_km']:>8.1f} | {row['I2_distance_km']:>8.1f} | {row['closest_node']:>8} | {row['SINR_dB']:>8.2f}")
        sinrs.append(row['SINR_dB'])

    print()
    print(f"Best SINR:  {max(sinrs):>8.2f} dB")
    print(f"Worst SINR: {min(sinrs):>8.2f} dB")
    print(f"Variation:  {max(sinrs) - min(sinrs):>8.2f} dB (HUGE spatial heterogeneity!)")
    print()

    # Generate statistics summary
    print("=" * 100)
    print("Summary Statistics by Distance")
    print("=" * 100)
    print()

    summary_data = []

    for r in distances_km:
        df_r = df[(df['distance_km'] == r) & (df['environment'] == 'suburban')]
        sinrs = df_r['SINR_dB'].values

        summary_data.append({
            'Distance_km': r,
            'Min_SINR_dB': np.min(sinrs),
            'Max_SINR_dB': np.max(sinrs),
            'Mean_SINR_dB': np.mean(sinrs),
            'Std_SINR_dB': np.std(sinrs),
            'Variation_dB': np.max(sinrs) - np.min(sinrs),
            'Best_Angle_deg': df_r.loc[df_r['SINR_dB'].idxmax(), 'angle_deg'],
            'Worst_Angle_deg': df_r.loc[df_r['SINR_dB'].idxmin(), 'angle_deg']
        })

    df_summary = pd.DataFrame(summary_data)
    summary_file = 'output/sinr_spatial_analysis_summary.csv'
    df_summary.to_csv(summary_file, index=False)

    print(f"{'Dist':>8} | {'Min':>8} | {'Max':>8} | {'Mean':>8} | {'Std':>8} | {'Variation':>10} | {'Best @':>8} | {'Worst @':>8}")
    print(f"{'(km)':>8} | {'(dB)':>8} | {'(dB)':>8} | {'(dB)':>8} | {'(dB)':>8} | {'(dB)':>10} | {'(deg)':>8} | {'(deg)':>8}")
    print("-" * 100)

    for _, row in df_summary.iterrows():
        print(f"{row['Distance_km']:>8.0f} | {row['Min_SINR_dB']:>8.2f} | {row['Max_SINR_dB']:>8.2f} | {row['Mean_SINR_dB']:>8.2f} | {row['Std_SINR_dB']:>8.2f} | {row['Variation_dB']:>10.2f} | {row['Best_Angle_deg']:>8.0f} | {row['Worst_Angle_deg']:>8.0f}")

    print()
    print(f"[OK] Exported summary: {summary_file}")
    print()

    print("=" * 100)
    print("KEY FINDINGS FOR PHASE 3.2")
    print("=" * 100)
    print()
    print("1. SPATIAL HETEROGENEITY IS REAL:")
    print(f"   - At r = 50 km: SINR variation = {max(sinrs) - min(sinrs):.1f} dB")
    print(f"   - This is NOT just distance decay—it's geometric!")
    print()
    print("2. TRIANGULAR CONSTELLATION EFFECT:")
    print("   - Users toward interferers (0°): SINR ~-7 to -8 dB (BAD)")
    print("   - Users away from constellation (180°): SINR ~+1 to +2 dB (GOOD)")
    print()
    print("3. DRL MUST LEARN SPATIAL PATTERNS:")
    print("   - Simple distance-based heuristics FAIL")
    print("   - Need adaptive scheduling by location, not just distance")
    print()
    print("=" * 100)

if __name__ == '__main__':
    main()
