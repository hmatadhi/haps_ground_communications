"""
Generate Phase 2 figures for LaTeX integration.

Figures:
1. Battery SoC profile over 24 hours (diurnal solar cycle)
2. Reward function landscape (Jain's index vs Throughput)
3. LSTM forecast validation (optional, for debugging)
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
import os

# Set matplotlib for publication quality
rcParams['font.size'] = 10
rcParams['font.family'] = 'serif'
rcParams['figure.dpi'] = 150
rcParams['savefig.dpi'] = 300
rcParams['lines.linewidth'] = 1.5
rcParams['axes.labelsize'] = 10
rcParams['axes.titlesize'] = 11
rcParams['xtick.labelsize'] = 9
rcParams['ytick.labelsize'] = 9

# Import battery and reward modules
from models.battery_model import HAPSBatteryModel
from drl_dqn.reward_function import convert_sinr_db_to_linear, compute_jain_fairness_index, compute_aggregate_throughput

# Output directory (create if needed)
os.makedirs('output', exist_ok=True)

# =====================================================================
# Figure 1: Battery SoC Profile Over 24 Hours
# =====================================================================

def generate_battery_profile():
    """Generate 24-hour battery SoC, solar power, and load profile."""
    battery = HAPSBatteryModel()

    hours = np.arange(24)
    soc_profile = []
    solar_profile = []
    load_profile = []
    net_power = []

    soc = 100.0
    user_load = 50.0  # Moderate constant user load

    for hour in hours:
        solar = battery.solar_power_generated(float(hour))
        load = 500 + 200 + user_load  # Feeder + platform + user
        net = solar - load

        soc, debug = battery.update_battery_soc(
            current_soc_percent=soc,
            hour_of_day=float(hour),
            user_load_watts=user_load
        )

        soc_profile.append(soc)
        solar_profile.append(solar)
        load_profile.append(load)
        net_power.append(net)

    soc_profile = np.array(soc_profile)
    solar_profile = np.array(solar_profile)
    load_profile = np.array(load_profile)
    net_power = np.array(net_power)

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.5, 4.5), sharex=True)

    # Subplot 1: Battery SoC and Solar Power
    ax1_twin = ax1.twinx()
    line1 = ax1.plot(hours, soc_profile, 'b-o', label='Battery SoC (%)', linewidth=2, markersize=4)
    line2 = ax1_twin.plot(hours, solar_profile / 1000, 'orange', label='Solar Power (kW)', linewidth=2)

    ax1.set_ylabel('Battery SoC (%)', color='b', fontsize=10)
    ax1_twin.set_ylabel('Solar Power (kW)', color='orange', fontsize=10)
    ax1.tick_params(axis='y', labelcolor='b')
    ax1_twin.tick_params(axis='y', labelcolor='orange')
    ax1.set_ylim([0, 105])
    ax1_twin.set_ylim([0, 2.5])
    ax1.grid(True, alpha=0.3)

    # Combine legends
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=9)

    # Subplot 2: Power Balance
    ax2.plot(hours, load_profile, 'r-s', label='Load (W)', linewidth=2, markersize=4)
    ax2.plot(hours, solar_profile, 'orange', label='Solar (W)', linewidth=2)
    ax2.plot(hours, net_power, 'g--', label='Net Power (W)', linewidth=1.5)
    ax2.axhline(0, color='k', linestyle='-', linewidth=0.5, alpha=0.5)

    ax2.set_xlabel('Hour of Day', fontsize=10)
    ax2.set_ylabel('Power (W)', fontsize=10)
    ax2.set_xlim([0, 23])
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right', fontsize=9)

    # Shade day/night regions
    ax2.axvspan(0, 6, alpha=0.1, color='gray', label='Night')
    ax2.axvspan(18, 24, alpha=0.1, color='gray')

    plt.tight_layout()
    plt.savefig('output/fig_battery_profile_24h.pdf', bbox_inches='tight')
    plt.savefig('output/fig_battery_profile_24h.png', bbox_inches='tight', dpi=150)
    print("[OK] Generated: 1: Battery Profile (figures/fig_battery_profile_24h.pdf)")
    plt.close()


# =====================================================================
# Figure 2: Reward Function Landscape (Jain vs Throughput)
# =====================================================================

def generate_reward_landscape():
    """Generate 3D and 2D visualizations of reward function."""

    # Sweep SINR values (3 users)
    sinr_range = np.linspace(0, 15, 12)  # 0 to 15 dB

    jain_values = []
    throughput_values = []
    reward_values = []

    for sinr_user1 in sinr_range[::2]:  # Sample every 2
        for sinr_user2 in sinr_range[::2]:
            sinr_db = [sinr_user1, sinr_user2, 5.0]  # Fix user 3 at 5 dB

            jain = compute_jain_fairness_index(sinr_db)
            throughput = compute_aggregate_throughput(sinr_db)
            reward = 0.5 * throughput + 0.3 * jain  # Simple reward

            jain_values.append(jain)
            throughput_values.append(throughput)
            reward_values.append(reward)

    jain_values = np.array(jain_values)
    throughput_values = np.array(throughput_values)
    reward_values = np.array(reward_values)

    # Create 2D scatter plot
    fig, ax = plt.subplots(1, 1, figsize=(6, 5))

    scatter = ax.scatter(throughput_values, jain_values, c=reward_values,
                         cmap='RdYlGn', s=100, alpha=0.7, edgecolors='black', linewidth=0.5)

    ax.set_xlabel('Aggregate Throughput L_agg (bits/s/Hz)', fontsize=10)
    ax.set_ylabel('Jain Fairness Index J', fontsize=10)
    ax.set_title('Multi-Objective Reward Landscape', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Reward R = 0.5*L_agg + 0.3*J', fontsize=9)

    # Add annotations for key points
    idx_best = np.argmax(reward_values)
    ax.scatter(throughput_values[idx_best], jain_values[idx_best],
               marker='*', s=500, color='red', edgecolors='darkred', linewidth=2,
               label='Pareto Front', zorder=5)

    ax.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig('output/fig_reward_landscape.pdf', bbox_inches='tight')
    plt.savefig('output/fig_reward_landscape.png', bbox_inches='tight', dpi=150)
    print("[OK] Generated: 2: Reward Landscape (figures/fig_reward_landscape.pdf)")
    plt.close()


# =====================================================================
# Figure 3: Observation Space Visualization (SINR Bounds)
# =====================================================================

def generate_observation_space():
    """Visualize the 12-dim observation space with emphasis on SINR bounds."""

    fig, ax = plt.subplots(1, 1, figsize=(7, 5))

    # Define features
    features = [
        'SINR_H1', 'SINR_H2', 'SINR_H3',
        'dist_H1', 'dist_H2', 'dist_H3',
        'batt_H1', 'batt_H2', 'batt_H3',
        'rain', 'visibility', 'hour'
    ]

    low_bounds = np.array([-20, -20, -20, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=float)
    high_bounds = np.array([30, 30, 30, 100, 100, 100, 100, 100, 100, 50, 10, 1], dtype=float)

    # Normalize to [0, 1] for visualization
    bounds_span = high_bounds - low_bounds
    y_pos = np.arange(len(features))

    # Plot bounds as horizontal bars
    for i, (low, high, span) in enumerate(zip(low_bounds, high_bounds, bounds_span)):
        ax.barh(i, span, left=low, height=0.6, color='skyblue', edgecolor='navy', linewidth=1)
        ax.text(low - 5, i, f'{low:.0f}', ha='right', va='center', fontsize=8)
        ax.text(high + 5, i, f'{high:.0f}', ha='left', va='center', fontsize=8)

    # Highlight SINR bounds (allows negative)
    ax.barh([0, 1, 2], high_bounds[[0, 1, 2]] - low_bounds[[0, 1, 2]],
            left=low_bounds[[0, 1, 2]], height=0.6,
            color='lightcoral', alpha=0.7, edgecolor='darkred', linewidth=2)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(features, fontsize=9)
    ax.set_xlabel('Observation Value (original units)', fontsize=10)
    ax.set_title('12-Dim Observation Space Definition\n(Red: Negative SINR Preserved)',
                 fontsize=11, fontweight='bold')
    ax.axvline(0, color='k', linestyle='--', linewidth=0.8, alpha=0.5)
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    plt.savefig('output/fig_observation_space.pdf', bbox_inches='tight')
    plt.savefig('output/fig_observation_space.png', bbox_inches='tight', dpi=150)
    print("[OK] Generated: 3: Observation Space (figures/fig_observation_space.pdf)")
    plt.close()


# =====================================================================
# Main
# =====================================================================

if __name__ == "__main__":
    print("Generating Phase 2 figures for LaTeX integration...\n")

    generate_battery_profile()
    generate_reward_landscape()
    generate_observation_space()

    print("\n[DONE] Phase 2 figures generated in figures/ directory")
    print("\nLaTeX commands to include:")
    print("  \\includegraphics[width=0.9\\columnwidth]{figures/fig_battery_profile_24h.pdf}")
    print("  \\includegraphics[width=0.9\\columnwidth]{figures/fig_reward_landscape.pdf}")
    print("  \\includegraphics[width=0.9\\columnwidth]{figures/fig_observation_space.pdf}")
