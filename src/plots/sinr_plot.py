import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Environment excess loss parameters (Holis & Pechac 2008)
ENVIRONMENTS = {
    'suburban': dict(eta_los=0.1, eta_nlos=21.0),
    'urban': dict(eta_los=1.0, eta_nlos=20.0),
    'dense_urban': dict(eta_los=1.6, eta_nlos=23.0),
    'high_rise': dict(eta_los=2.3, eta_nlos=34.0),
}

def generate_haps_sinr_chart(csv_file, output_png=None):
    """
    Generate SINR analysis chart from CSV file.

    Expected columns:
    - Landscape: environment type
    - Distance_m: horizontal distance in meters
    - SINR_Single: ideal SINR (serving HAPS only, no interference)
    - SINR_Interferers: interference level (aggregated interfering HAPS vs noise)
    - SINR_Actual: serving advantage (SINR_Single - SINR_Interferers)
    """
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"Error: {csv_file} not found.")
        return

    landscapes = sorted(df['Landscape'].unique())

    # Setup 2x2 trellis with light theme
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor("#FFFFFF")
    axes = axes.flatten()

    for i, landscape in enumerate(landscapes):
        ax1 = axes[i]
        ax1.set_facecolor('#F5F5F5')
        data = df[df['Landscape'] == landscape].sort_values('Distance_m')

        x = np.arange(len(data))
        width = 0.35

        # Bars: SINR_Single (ideal) vs SINR_Actual (with interference)
        bars1 = ax1.bar(x - width/2, data['SINR_Single'], width,
                        label='SINR Single', color='#1976D2', alpha=0.85)
        bars2 = ax1.bar(x + width/2, data['SINR_Actual'], width,
                        label='SINR Actual', color='#1976D2',
                        hatch='///', alpha=0.6, edgecolor='#333333', linewidth=0.5)

        ax1.set_xlabel('Distance [m]', fontsize=10, color='#333333')
        ax1.set_ylabel('SINR [dB]', fontsize=10, color='#333333')
        env_key = landscape.lower()
        eta_los = ENVIRONMENTS.get(env_key, {}).get('eta_los', '?')
        eta_nlos = ENVIRONMENTS.get(env_key, {}).get('eta_nlos', '?')
        title_text = f"{landscape.replace('_', ' ').title()}\nη_LoS={eta_los} dB, η_NLoS={eta_nlos} dB"
        ax1.set_title(title_text, fontsize=10, fontweight='bold', color='#333333')
        ax1.set_xticks(x)
        ax1.set_xticklabels([f'{int(d/1000):,d}km' if d >= 1000 else f'{int(d)}m'
                            for d in data['Distance_m']], color='#333333', fontsize=9)
        ax1.tick_params(colors='#333333', labelsize=9)
        ax1.grid(axis='y', linestyle='--', alpha=0.3, color='#CCCCCC')

        # Determine y-axis limits based on data range
        min_val = min(data['SINR_Single'].min(), data['SINR_Actual'].min())
        max_val = max(data['SINR_Single'].max(), data['SINR_Actual'].max())
        y_margin = (max_val - min_val) * 0.1  # 10% margin
        ax1.set_ylim(min_val - y_margin, max_val + y_margin)

        # Secondary Y-axis: SINR_Interferers (red line with markers) - the loss/gap
        ax2 = ax1.twinx()
        ax2.plot(x, data['SINR_Interferers'], color='#D32F2F', marker='o',
                 markersize=7, linewidth=2.5, label='SINR Interferers (Loss)', zorder=3)
        ax2.set_ylabel('SINR Interferers [dB]', fontsize=10, color='#D32F2F')
        ax2.tick_params(axis='y', labelcolor='#D32F2F', labelsize=9)

        # Determine y-axis for secondary (SINR_Interferers/loss). Values can be
        # deeply negative (e.g. a noise-limited feeder link where interference
        # is far below the noise floor), so don't assume a positive-only range.
        interf_min = data['SINR_Interferers'].min()
        interf_max = data['SINR_Interferers'].max()
        span = max(abs(interf_max - interf_min), 1.0)
        margin = span * 0.2
        ax2.set_ylim(min(0.0, interf_min - margin), max(0.0, interf_max + margin))

        # Legend (first subplot only)
        if i == 0:
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            leg = ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
                      fontsize=9, framealpha=0.95, facecolor='#FFFFFF', edgecolor='#333333')
            for text in leg.get_texts():
                text.set_color('#333333')

    # Determine title based on distance range
    max_dist = df['Distance_m'].max()
    if max_dist < 1000:
        title = 'AI-HAPS Project: 38 GHz Feeder Link (HAPS-to-Gateway) Performance Analysis'
    else:
        title = 'AI-HAPS Project: 2 GHz Service Link SINR Performance Analysis Across Terrestrial Landscapes'

    plt.suptitle(title, fontsize=14, fontweight='bold', color='#333333', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    if output_png is None:
        output_png = 'haps_sinr_chart.png'

    plt.savefig(output_png, facecolor='#FFFFFF', dpi=150)
    print(f"Success: Chart '{output_png}' generated.")

# Generate charts for both service and feeder links
if __name__ == "__main__":
    generate_haps_sinr_chart('haps_sinr_data_2ghz_service_fixed.csv', 'haps_sinr_trellis.png')
    generate_haps_sinr_chart('haps_feeder_link_38ghz_fixed.csv', 'haps_feeder_link_38ghz.png')