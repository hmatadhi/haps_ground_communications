import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def generate_haps_sinr_chart_with_los(csv_file, output_png=None):
    """
    Generate SINR analysis chart with LoS blockage from CSV file.

    Expected columns:
    - Landscape: environment type
    - Distance_m: horizontal distance in meters
    - SINR_Single: ideal SINR (serving HAPS only, no interference)
    - SINR_Interferers: interference level (aggregated interfering HAPS vs noise)
    - SINR_Actual: serving advantage (with interference, no blockage)
    - LoS_Probability_dB: LoS blockage probability in dB (10*log10(P_LoS))
    - SINR_With_LoS: SINR accounting for LoS blockage degradation
    """
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"Error: {csv_file} not found.")
        return

    landscapes = sorted(df['Landscape'].unique())

    # Setup 2x2 trellis with dark theme
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor("#282843")
    axes = axes.flatten()

    for i, landscape in enumerate(landscapes):
        ax1 = axes[i]
        ax1.set_facecolor('#16213e')
        data = df[df['Landscape'] == landscape].sort_values('Distance_m')

        x = np.arange(len(data))
        width = 0.35

        # Bars: SINR_Single (ideal) vs SINR_With_LoS (with blockage)
        bars1 = ax1.bar(x - width/2, data['SINR_Single'], width,
                        label='SINR Single (No Blockage)', color='#2196F3', alpha=0.85)
        bars2 = ax1.bar(x + width/2, data['SINR_With_LoS'], width,
                        label='SINR With LoS', color='#2196F3',
                        hatch='///', alpha=0.6, edgecolor='white', linewidth=0.5)

        ax1.set_xlabel('Distance [m]', fontsize=10, color='white')
        ax1.set_ylabel('SINR [dB]', fontsize=10, color='white')
        ax1.set_title(landscape.replace('_', ' ').title(), fontsize=11, fontweight='bold', color='white')
        ax1.set_xticks(x)
        ax1.set_xticklabels([f'{int(d/1000):,d}km' if d >= 1000 else f'{int(d)}m'
                            for d in data['Distance_m']], color='white', fontsize=9)
        ax1.tick_params(colors='white', labelsize=9)
        ax1.grid(axis='y', linestyle='--', alpha=0.3, color='white')

        # Determine y-axis limits based on data range
        min_val = min(data['SINR_Single'].min(), data['SINR_With_LoS'].min())
        max_val = max(data['SINR_Single'].max(), data['SINR_With_LoS'].max())
        y_margin = (max_val - min_val) * 0.1  # 10% margin
        ax1.set_ylim(min_val - y_margin, max_val + y_margin)

        # Secondary Y-axis: Two lines
        # 1. SINR_Interferers (orange) - interference level
        # 2. LoS_Probability_dB (green) - LoS blockage in dB
        ax2 = ax1.twinx()

        line1 = ax2.plot(x, data['SINR_Interferers'], color='#FF9800', marker='o',
                         markersize=7, linewidth=2.5, label='SINR Interferers', zorder=3)
        line2 = ax2.plot(x, data['LoS_Probability_dB'], color='#4CAF50', marker='s',
                         markersize=7, linewidth=2.5, linestyle='--', label='LoS Probability (dB)', zorder=2)

        ax2.set_ylabel('Interference & LoS [dB]', fontsize=10, color='white')
        ax2.tick_params(axis='y', labelcolor='white', labelsize=9)
        ax2.axhline(y=0, color='gray', linestyle=':', linewidth=1, alpha=0.5)

        # Determine y-axis range for secondary axis
        min_interf = data['SINR_Interferers'].min()
        max_los_db = data['LoS_Probability_dB'].max()
        y2_min = min(min_interf, -5)
        y2_max = max(max_los_db, 5)
        y2_margin = (y2_max - y2_min) * 0.15
        ax2.set_ylim(y2_min - y2_margin, y2_max + y2_margin)

        # Legend (combined from both axes) - first subplot only
        if i == 0:
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            leg = ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
                      fontsize=8, framealpha=0.9, facecolor='#16213e', edgecolor='white')
            for text in leg.get_texts():
                text.set_color('white')

    # Determine title based on distance range
    max_dist = df['Distance_m'].max()
    if max_dist < 1000:
        title = 'AI-HAPS Project: 38 GHz Feeder Link with LoS Blockage Analysis'
    else:
        title = 'AI-HAPS Project: 2 GHz Service Link SINR with LoS Blockage (Terrestrial Landscapes)'

    plt.suptitle(title, fontsize=14, fontweight='bold', color='white', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    if output_png is None:
        output_png = 'haps_sinr_chart_with_los.png'

    plt.savefig(output_png, facecolor='#1a1a2e', dpi=150)
    print(f"Success: Chart '{output_png}' generated.")
    plt.close()

# Generate charts for both service and feeder links with LoS blockage
if __name__ == "__main__":
    generate_haps_sinr_chart_with_los('haps_sinr_data_2ghz_service_with_los.csv',
                                      'haps_sinr_trellis_with_los.png')
    generate_haps_sinr_chart_with_los('haps_feeder_link_38ghz_with_los.csv',
                                      'haps_feeder_link_38ghz_with_los.png')
