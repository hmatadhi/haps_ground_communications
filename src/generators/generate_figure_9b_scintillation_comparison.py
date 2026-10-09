#!/usr/bin/env python3
"""
Generate Figure 9b: Scintillation Fade Depth Comparison (2 GHz vs 38 GHz)
Equation (12): D(p, θ, f) = D_ref * (f/f_ref)^0.7 * (1/sin(θ)) * sqrt(log(1/p)) [dB]
Reference: ITU-R P.618-13 Annex 2
"""

import numpy as np
import matplotlib.pyplot as plt

# ============================================================================
# Equation (12): Scintillation Fade Depth (ITU P.618)
# ============================================================================
def scintillation_fade_depth_db(p_time_percent, elevation_deg, freq_ghz):
    """
    Calculate scintillation fade depth per ITU-R P.618-13.

    Args:
        p_time_percent: Time percentage [0.1 to 10]
        elevation_deg: Elevation angle [5 to 85] degrees
        freq_ghz: Frequency in GHz

    Returns:
        Fade depth in dB
    """
    # Reference conditions: D_ref = 2.5 dB at p=1%, θ=30°, f=20 GHz reference
    # Note: f_ref = 20 GHz is the ITU standard reference; we still use it for normalization
    D_ref = 2.5
    f_ref = 20.0
    p_ref = 1.0

    # Clip elevation to valid range
    elev_rad = np.radians(np.clip(elevation_deg, 5.0, 85.0))

    # Frequency scaling: (f/f_ref)^0.7
    freq_factor = (freq_ghz / f_ref) ** 0.7

    # Elevation scaling: 1/sin(θ)
    elev_factor = 1.0 / np.sin(elev_rad)

    # Time percentage scaling: sqrt(log(1/p))
    p_frac = p_time_percent / 100.0
    time_factor = np.sqrt(np.abs(np.log(p_frac)))

    return D_ref * freq_factor * elev_factor * time_factor

# ============================================================================
# Generate Figure 9b with Two Subplots
# ============================================================================

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

# --------
# Subplot A: Fade depth vs. time percentage at fixed elevations
# --------
ax = axes[0]

p_time = np.linspace(0.1, 10, 100)  # Time percentage: 0.1% to 10%
elevations = [11.3, 30.0, 45.0]  # Three representative elevations
freq_2ghz = 2.0
freq_38ghz = 38.0

for elev in elevations:
    fade_2ghz = [scintillation_fade_depth_db(p, elev, freq_2ghz) for p in p_time]
    fade_38ghz = [scintillation_fade_depth_db(p, elev, freq_38ghz) for p in p_time]

    ax.plot(p_time, fade_2ghz, linewidth=2.0, linestyle='-',
            label=f'2 GHz, {elev}°', color=f'C{elevations.index(elev)}')
    ax.plot(p_time, fade_38ghz, linewidth=2.0, linestyle='--',
            label=f'38 GHz, {elev}°', color=f'C{elevations.index(elev)}')

ax.set_xlabel('Time Percentage [%]', fontsize=11, fontweight='bold')
ax.set_ylabel('Fade Depth [dB]', fontsize=11, fontweight='bold')
ax.set_title('Fade Depth vs. Time Percentage (Eq. 12)', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, linestyle='--')
ax.legend(fontsize=9, loc='upper left', ncol=2, framealpha=0.95)
ax.set_xscale('log')

# --------
# Subplot B: Fade depth vs. elevation angle at fixed time percentages
# --------
ax = axes[1]

theta_deg = np.linspace(5, 85, 100)  # Elevation angle: 5° to 85°
time_percentages = [0.1, 1.0, 10.0]  # Three representative time percentages

for p_time in time_percentages:
    fade_2ghz = [scintillation_fade_depth_db(p_time, theta, freq_2ghz) for theta in theta_deg]
    fade_38ghz = [scintillation_fade_depth_db(p_time, theta, freq_38ghz) for theta in theta_deg]

    ax.plot(theta_deg, fade_2ghz, linewidth=2.0, linestyle='-',
            label=f'2 GHz, {p_time}%', color=f'C{time_percentages.index(p_time)}')
    ax.plot(theta_deg, fade_38ghz, linewidth=2.0, linestyle='--',
            label=f'38 GHz, {p_time}%', color=f'C{time_percentages.index(p_time)}')

ax.set_xlabel('Elevation Angle [degrees]', fontsize=11, fontweight='bold')
ax.set_ylabel('Fade Depth [dB]', fontsize=11, fontweight='bold')
ax.set_title('Fade Depth vs. Elevation Angle (Eq. 12)', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, linestyle='--')
ax.legend(fontsize=9, loc='upper right', ncol=2, framealpha=0.95)

# Overall title
fig.suptitle('Scintillation Fade Depth: Frequency Comparison (2 GHz Service vs 38 GHz Feeder)',
             fontsize=13, fontweight='bold', y=1.00)

plt.tight_layout()
plt.savefig('output/9b_scintillation_fade_2ghz_vs_38ghz.png', dpi=300, bbox_inches='tight')
print("[OK] Figure saved: 9b_scintillation_fade_2ghz_vs_38ghz.png")
plt.close()

# ============================================================================
# Print summary and key values
# ============================================================================
print("\n" + "="*75)
print("Figure 9b Summary")
print("="*75)

# Calculate ratio at reference conditions
fade_2_ref = scintillation_fade_depth_db(p_time_percent=1.0, elevation_deg=30.0, freq_ghz=2.0)
fade_38_ref = scintillation_fade_depth_db(p_time_percent=1.0, elevation_deg=30.0, freq_ghz=38.0)
ratio = fade_38_ref / fade_2_ref
theoretical_ratio = (38/2)**0.7

print(f"\nReference Conditions (p=1%, elevation=30 deg):")
print(f"  2 GHz Fade Depth: {fade_2_ref:.2f} dB")
print(f"  38 GHz Fade Depth: {fade_38_ref:.2f} dB")
print(f"  Ratio (38 GHz / 2 GHz): {ratio:.3f}")
print(f"  Theoretical Ratio: (38/2)^0.7 = {theoretical_ratio:.3f}")

# Key values at different conditions
print(f"\nKey Values at Different Conditions:")
print(f"{'Elevation':<12} {'Time %':<8} {'2 GHz':<10} {'38 GHz':<10} {'Ratio':<8}")
print("-" * 50)
for elev in [11.3, 30.0, 45.0]:
    for p in [0.1, 1.0, 10.0]:
        fade_2 = scintillation_fade_depth_db(p, elev, 2.0)
        fade_38 = scintillation_fade_depth_db(p, elev, 38.0)
        ratio_val = fade_38 / fade_2
        print(f"{elev:>6} deg {p:>6}%{'':<1} {fade_2:>8.2f}{'':<1} {fade_38:>8.2f}{'':<1} {ratio_val:>6.3f}")

print("="*75)
print("Notes:")
print("  - Solid lines: 2 GHz (Service links, resilient to atmospheric effects)")
print("  - Dashed lines: 38 GHz (Feeder links, vulnerable to atmospheric effects)")
print("  - Higher elevations => Lower fade depth (shorter atmospheric path)")
print("  - Rarer events => Higher fade depth (lower time percentage)")
print("  - 38 GHz consistently deeper fades than 2 GHz due to f^0.7 scaling")
print("="*75)
