#!/usr/bin/env python
"""
Generate atmospheric loss vs frequency figures (both nominal and worst-case elevations).

Produces 2 figures with 4 subplots each:
  - Nominal (21.75° elev): fig_atm_loss_nominal_frequency.png
  - Worst-case (11.3° elev): fig_atm_loss_worstcase_frequency.png
"""

import numpy as np
import matplotlib.pyplot as plt
from atmospheric_losses import total_feeder_loss_db

# Common parameters
lat, lon = 28.5, 77.2
pressure_hpa = 1013.0
temp_c = 15.0
rh_percent = 60.0
slant_path_km = 20.0
rain_rate_mmhr = 10.0
time_percentage = 1.0

# Define two scenarios
scenarios = [
    ("nominal", 21.75, "Nominal (50 km horizontal)"),
    ("worstcase", 11.3, "Worst-Case (100 km service edge)"),
]

for scenario_name, elevation_deg, scenario_label in scenarios:
    print(f"\n{'='*70}")
    print(f"Generating frequency plot: {scenario_label}")
    print(f"Elevation angle: {elevation_deg}°")
    print(f"{'='*70}")

    # Create combined 2x2 figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Band 1: 10-40 GHz (Ka-band, includes H2O peak at 22 GHz)
    freq_band1 = np.linspace(10, 40, 80)
    rain_b1, fog_b1, gas_b1, scint_b1, total_b1 = [], [], [], [], []

    for freq in freq_band1:
        losses = total_feeder_loss_db(
            rain_rate_mmhr=rain_rate_mmhr, liquid_water_g_m3=0.05,
            pressure_hpa=pressure_hpa, temp_c=temp_c, rh_percent=rh_percent,
            freq_ghz=freq, elevation_deg=elevation_deg, time_percentage=time_percentage,
            lat=lat, lon=lon
        )
        rain_b1.append(losses['rain'])
        fog_b1.append(losses['fog'])
        gas_b1.append(losses['gas'])
        scint_b1.append(losses['scintillation'])
        total_b1.append(losses['total'])

    ax = axes[0, 0]
    ax.plot(freq_band1, rain_b1, 'r-', linewidth=2.5, label='Rain (P.838)')
    ax.plot(freq_band1, fog_b1, 'b--', linewidth=2, label='Fog (P.840)')
    ax.plot(freq_band1, gas_b1, 'g-', linewidth=2.5, label='Gas (P.676)')
    ax.plot(freq_band1, scint_b1, 'm--', linewidth=2, label='Scintillation (P.618)')
    ax.plot(freq_band1, total_b1, 'k-', linewidth=3, label='Total')
    ax.axvline(x=22.235, color='orange', linestyle=':', linewidth=2.5, alpha=0.7, label='H$_2$O peak (22.2 GHz)')
    ax.axvline(x=38.0, color='red', linestyle='--', linewidth=2, alpha=0.5, label='HAPS feeder (38 GHz)')
    ax.set_xlabel('Frequency (GHz)', fontsize=11)
    ax.set_ylabel('Attenuation (dB)', fontsize=11)
    ax.set_title('Ka-Band: 10--40 GHz\n(Water Vapor Resonance)', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim([10, 40])

    # Band 2: 40-80 GHz (Q-band, includes O2 peak at 60 GHz)
    freq_band2 = np.linspace(40, 80, 80)
    rain_b2, fog_b2, gas_b2, scint_b2, total_b2 = [], [], [], [], []

    for freq in freq_band2:
        losses = total_feeder_loss_db(
            rain_rate_mmhr=rain_rate_mmhr, liquid_water_g_m3=0.05,
            pressure_hpa=pressure_hpa, temp_c=temp_c, rh_percent=rh_percent,
            freq_ghz=freq, elevation_deg=elevation_deg, time_percentage=time_percentage,
            lat=lat, lon=lon
        )
        rain_b2.append(losses['rain'])
        fog_b2.append(losses['fog'])
        gas_b2.append(losses['gas'])
        scint_b2.append(losses['scintillation'])
        total_b2.append(losses['total'])

    ax = axes[0, 1]
    ax.plot(freq_band2, rain_b2, 'r-', linewidth=2.5, label='Rain (P.838)')
    ax.plot(freq_band2, fog_b2, 'b--', linewidth=2, label='Fog (P.840)')
    ax.plot(freq_band2, gas_b2, 'g-', linewidth=2.5, label='Gas (P.676)')
    ax.plot(freq_band2, scint_b2, 'm--', linewidth=2, label='Scintillation (P.618)')
    ax.plot(freq_band2, total_b2, 'k-', linewidth=3, label='Total')
    ax.axvline(x=60.0, color='cyan', linestyle=':', linewidth=2.5, alpha=0.7, label='O$_2$ peak (60 GHz)')
    ax.set_xlabel('Frequency (GHz)', fontsize=11)
    ax.set_ylabel('Attenuation (dB)', fontsize=11)
    ax.set_title('Q-Band: 40--80 GHz\n(Oxygen Resonance)', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim([40, 80])

    # Band 3: 80-100 GHz (V-band)
    freq_band3 = np.linspace(80, 100, 40)
    rain_b3, fog_b3, gas_b3, scint_b3, total_b3 = [], [], [], [], []

    for freq in freq_band3:
        losses = total_feeder_loss_db(
            rain_rate_mmhr=rain_rate_mmhr, liquid_water_g_m3=0.05,
            pressure_hpa=pressure_hpa, temp_c=temp_c, rh_percent=rh_percent,
            freq_ghz=freq, elevation_deg=elevation_deg, time_percentage=time_percentage,
            lat=lat, lon=lon
        )
        rain_b3.append(losses['rain'])
        fog_b3.append(losses['fog'])
        gas_b3.append(losses['gas'])
        scint_b3.append(losses['scintillation'])
        total_b3.append(losses['total'])

    ax = axes[1, 0]
    ax.plot(freq_band3, rain_b3, 'r-', linewidth=2.5, label='Rain (P.838)')
    ax.plot(freq_band3, fog_b3, 'b--', linewidth=2, label='Fog (P.840)')
    ax.plot(freq_band3, gas_b3, 'g-', linewidth=2.5, label='Gas (P.676)')
    ax.plot(freq_band3, scint_b3, 'm--', linewidth=2, label='Scintillation (P.618)')
    ax.plot(freq_band3, total_b3, 'k-', linewidth=3, label='Total')
    ax.text(90, max(total_b3)*0.9, 'O$_2$ line at 118 GHz\n(beyond plot range)', fontsize=10, ha='center',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    ax.set_xlabel('Frequency (GHz)', fontsize=11)
    ax.set_ylabel('Attenuation (dB)', fontsize=11)
    ax.set_title('V-Band: 80--100 GHz\n(Continuum)', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim([80, 100])

    # Band 4: Full range with log scale
    freq_full = np.linspace(10, 100, 200)
    rain_full, fog_full, gas_full, scint_full, total_full = [], [], [], [], []

    for freq in freq_full:
        losses = total_feeder_loss_db(
            rain_rate_mmhr=rain_rate_mmhr, liquid_water_g_m3=0.05,
            pressure_hpa=pressure_hpa, temp_c=temp_c, rh_percent=rh_percent,
            freq_ghz=freq, elevation_deg=elevation_deg, time_percentage=time_percentage,
            lat=lat, lon=lon
        )
        rain_full.append(losses['rain'])
        fog_full.append(losses['fog'])
        gas_full.append(losses['gas'])
        scint_full.append(losses['scintillation'])
        total_full.append(losses['total'])

    ax = axes[1, 1]
    ax.semilogy(freq_full, np.array(rain_full) + 0.01, 'r-', linewidth=2.5, label='Rain (P.838)')
    ax.semilogy(freq_full, np.array(fog_full) + 0.01, 'b--', linewidth=2, label='Fog (P.840)')
    ax.semilogy(freq_full, np.array(gas_full) + 0.01, 'g-', linewidth=2.5, label='Gas (P.676)')
    ax.semilogy(freq_full, np.array(scint_full) + 0.01, 'm--', linewidth=2, label='Scintillation (P.618)')
    ax.semilogy(freq_full, np.array(total_full) + 0.01, 'k-', linewidth=3, label='Total')
    ax.axvline(x=22.235, color='orange', linestyle=':', linewidth=2, alpha=0.7, label='H$_2$O (22.2 GHz)')
    ax.axvline(x=60.0, color='cyan', linestyle=':', linewidth=2, alpha=0.7, label='O$_2$ (60 GHz)')
    ax.set_xlabel('Frequency (GHz)', fontsize=11)
    ax.set_ylabel('Attenuation (dB) [log scale]', fontsize=11)
    ax.set_title('Full Spectrum: 10--100 GHz\n(Logarithmic Y-Axis)', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3, which='both')
    ax.set_xlim([10, 100])
    ax.set_ylim([0.01, 500])

    plt.suptitle(f'Atmospheric Loss vs Frequency — {scenario_label}\n10 mm/h Rain, {elevation_deg}° Elevation, Delhi',
                 fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(f'fig_atm_loss_{scenario_name}_frequency.png', dpi=300, bbox_inches='tight')
    print(f"Saved: fig_atm_loss_{scenario_name}_frequency.png")

    # Save individual subfigures for LaTeX
    print(f"\nGenerating individual subfigures for {scenario_label}...")

    # Subfigure 1a: Ka-band
    fig_1a = plt.figure(figsize=(10, 7))
    ax_1a = fig_1a.add_subplot(111)
    ax_1a.plot(freq_band1, rain_b1, 'r-', linewidth=2.5, label='Rain (P.838)')
    ax_1a.plot(freq_band1, fog_b1, 'b--', linewidth=2, label='Fog (P.840)')
    ax_1a.plot(freq_band1, gas_b1, 'g-', linewidth=2.5, label='Gas (P.676)')
    ax_1a.plot(freq_band1, scint_b1, 'm--', linewidth=2, label='Scintillation (P.618)')
    ax_1a.plot(freq_band1, total_b1, 'k-', linewidth=3, label='Total')
    ax_1a.axvline(x=22.235, color='orange', linestyle=':', linewidth=2.5, alpha=0.7, label='H$_2$O peak (22.2 GHz)')
    ax_1a.axvline(x=38.0, color='red', linestyle='--', linewidth=2, alpha=0.5, label='HAPS feeder (38 GHz)')
    ax_1a.set_xlabel('Frequency (GHz)', fontsize=11)
    ax_1a.set_ylabel('Attenuation (dB)', fontsize=11)
    ax_1a.set_title('Ka-Band: 10–40 GHz (Water Vapor Resonance)', fontsize=12, fontweight='bold')
    ax_1a.legend(loc='best', fontsize=9)
    ax_1a.grid(True, alpha=0.3)
    ax_1a.set_xlim([10, 40])
    plt.tight_layout()
    filename_1a = f'fig_atm_loss_{scenario_name}_1a.png'
    fig_1a.savefig(filename_1a, dpi=300, bbox_inches='tight')
    print(f"Saved: {filename_1a}")
    plt.close(fig_1a)

    # Subfigure 1b: Q-band
    fig_1b = plt.figure(figsize=(10, 7))
    ax_1b = fig_1b.add_subplot(111)
    ax_1b.plot(freq_band2, rain_b2, 'r-', linewidth=2.5, label='Rain (P.838)')
    ax_1b.plot(freq_band2, fog_b2, 'b--', linewidth=2, label='Fog (P.840)')
    ax_1b.plot(freq_band2, gas_b2, 'g-', linewidth=2.5, label='Gas (P.676)')
    ax_1b.plot(freq_band2, scint_b2, 'm--', linewidth=2, label='Scintillation (P.618)')
    ax_1b.plot(freq_band2, total_b2, 'k-', linewidth=3, label='Total')
    ax_1b.axvline(x=60.0, color='cyan', linestyle=':', linewidth=2.5, alpha=0.7, label='O$_2$ peak (60 GHz)')
    ax_1b.set_xlabel('Frequency (GHz)', fontsize=11)
    ax_1b.set_ylabel('Attenuation (dB)', fontsize=11)
    ax_1b.set_title('Q-Band: 40–80 GHz (Oxygen Resonance)', fontsize=12, fontweight='bold')
    ax_1b.legend(loc='best', fontsize=9)
    ax_1b.grid(True, alpha=0.3)
    ax_1b.set_xlim([40, 80])
    plt.tight_layout()
    filename_1b = f'fig_atm_loss_{scenario_name}_1b.png'
    fig_1b.savefig(filename_1b, dpi=300, bbox_inches='tight')
    print(f"Saved: {filename_1b}")
    plt.close(fig_1b)

    # Subfigure 1c: V-band
    fig_1c = plt.figure(figsize=(10, 7))
    ax_1c = fig_1c.add_subplot(111)
    ax_1c.plot(freq_band3, rain_b3, 'r-', linewidth=2.5, label='Rain (P.838)')
    ax_1c.plot(freq_band3, fog_b3, 'b--', linewidth=2, label='Fog (P.840)')
    ax_1c.plot(freq_band3, gas_b3, 'g-', linewidth=2.5, label='Gas (P.676)')
    ax_1c.plot(freq_band3, scint_b3, 'm--', linewidth=2, label='Scintillation (P.618)')
    ax_1c.plot(freq_band3, total_b3, 'k-', linewidth=3, label='Total')
    ax_1c.text(90, max(total_b3)*0.9, 'O$_2$ line at 118 GHz\n(beyond plot range)', fontsize=10, ha='center',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    ax_1c.set_xlabel('Frequency (GHz)', fontsize=11)
    ax_1c.set_ylabel('Attenuation (dB)', fontsize=11)
    ax_1c.set_title('V-Band: 80–100 GHz (Continuum)', fontsize=12, fontweight='bold')
    ax_1c.legend(loc='best', fontsize=9)
    ax_1c.grid(True, alpha=0.3)
    ax_1c.set_xlim([80, 100])
    plt.tight_layout()
    filename_1c = f'fig_atm_loss_{scenario_name}_1c.png'
    fig_1c.savefig(filename_1c, dpi=300, bbox_inches='tight')
    print(f"Saved: {filename_1c}")
    plt.close(fig_1c)

    # Subfigure 1d: Full spectrum (log scale)
    fig_1d = plt.figure(figsize=(10, 7))
    ax_1d = fig_1d.add_subplot(111)
    ax_1d.semilogy(freq_full, np.array(rain_full) + 0.01, 'r-', linewidth=2.5, label='Rain (P.838)')
    ax_1d.semilogy(freq_full, np.array(fog_full) + 0.01, 'b--', linewidth=2, label='Fog (P.840)')
    ax_1d.semilogy(freq_full, np.array(gas_full) + 0.01, 'g-', linewidth=2.5, label='Gas (P.676)')
    ax_1d.semilogy(freq_full, np.array(scint_full) + 0.01, 'm--', linewidth=2, label='Scintillation (P.618)')
    ax_1d.semilogy(freq_full, np.array(total_full) + 0.01, 'k-', linewidth=3, label='Total')
    ax_1d.axvline(x=22.235, color='orange', linestyle=':', linewidth=2, alpha=0.7, label='H$_2$O (22.2 GHz)')
    ax_1d.axvline(x=60.0, color='cyan', linestyle=':', linewidth=2, alpha=0.7, label='O$_2$ (60 GHz)')
    ax_1d.set_xlabel('Frequency (GHz)', fontsize=11)
    ax_1d.set_ylabel('Attenuation (dB) [log scale]', fontsize=11)
    ax_1d.set_title('Full Spectrum: 10–100 GHz (Logarithmic Y-Axis)', fontsize=12, fontweight='bold')
    ax_1d.legend(loc='best', fontsize=9)
    ax_1d.grid(True, alpha=0.3, which='both')
    ax_1d.set_xlim([10, 100])
    ax_1d.set_ylim([0.01, 500])
    plt.tight_layout()
    filename_1d = f'fig_atm_loss_{scenario_name}_1d.png'
    fig_1d.savefig(filename_1d, dpi=300, bbox_inches='tight')
    print(f"Saved: {filename_1d}")
    plt.close(fig_1d)

    plt.close()

print("\n" + "="*70)
print("Atmospheric loss plots generated (combined + individual subfigures):")
print("\nCombined 2x2 figures:")
print("  - fig_atm_loss_nominal_frequency.png (21.75°)")
print("  - fig_atm_loss_worstcase_frequency.png (11.3°)")
print("\nIndividual subfigures (for LaTeX):")
print("  - fig_atm_loss_nominal_1a.png (Ka-Band)")
print("  - fig_atm_loss_nominal_1b.png (Q-Band)")
print("  - fig_atm_loss_nominal_1c.png (V-Band)")
print("  - fig_atm_loss_nominal_1d.png (Full Spectrum)")
print("  - fig_atm_loss_worstcase_1a.png (Ka-Band)")
print("  - fig_atm_loss_worstcase_1b.png (Q-Band)")
print("  - fig_atm_loss_worstcase_1c.png (V-Band)")
print("  - fig_atm_loss_worstcase_1d.png (Full Spectrum)")
print("="*70)
