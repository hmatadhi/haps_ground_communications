#!/usr/bin/env python
"""
Generate Table B.1 scenarios for LaTeX (nominal and worst-case).
Output saved to: TABLE_B1_NOMINAL.txt, TABLE_B1_LATEX_NOMINAL.txt
                 TABLE_B1_WORSTCASE.txt, TABLE_B1_LATEX_WORSTCASE.txt
"""

from atmospheric_losses import total_feeder_loss_db

# Standard parameters
freq_ghz = 38.0
pressure_hpa = 1013.0
temp_c = 15.0
rh_percent = 60.0
lat, lon = 28.5, 77.2

# Six scenarios: clear sky to worst case
scenarios = [
    ("Clear sky, no rain", 0.0, 0.0, 50.0),
    ("Light rain (2 mm/h)", 2.0, 0.0, 1.0),
    ("Moderate rain (10 mm/h)", 10.0, 0.0, 0.1),
    ("Heavy rain (25 mm/h)", 25.0, 0.0, 0.01),
    ("Moderate rain + light fog", 10.0, 0.05, 0.1),
    ("Heavy rain + dense fog", 25.0, 0.5, 0.01),
]

# Two elevation scenarios
elevation_cases = [
    ("NOMINAL", 21.75, "Nominal (50 km horizontal distance)"),
    ("WORSTCASE", 11.3, "Worst-Case (100 km service radius edge)"),
]

for case_name, elevation_deg, case_label in elevation_cases:
    slant_path_km = 20.0  # Approximate; actual slant path is sqrt(horiz² + alt²)

    # Write human-readable table
    output_file = f"TABLE_B1_{case_name}.txt"
    latex_file = f"TABLE_B1_LATEX_{case_name}.txt"

    with open(output_file, "w") as f:
        f.write(f"\nTable B.1: Typical Atmospheric Loss Values ({case_label})\n")
        f.write("=" * 100 + "\n")
        f.write(f"Frequency: {freq_ghz} GHz | Elevation: {elevation_deg}° | Slant path: {slant_path_km} km\n")
        f.write(f"Location: {lat}°N, {lon}°E | P={pressure_hpa} hPa, T={temp_c}°C, RH={rh_percent}%\n")
        f.write("\n")
        f.write(f"{'Scenario':<30} | {'Rain':<8} | {'Fog':<8} | {'Gas':<8} | {'Scint':<8} | {'Total':<8}\n")
        f.write(f"{'':30} | {'(dB)':<8} | {'(dB)':<8} | {'(dB)':<8} | {'(dB)':<8} | {'(dB)':<8}\n")
        f.write("-" * 100 + "\n")

        for scenario_name, rain_rate, lwc, time_pct in scenarios:
            losses = total_feeder_loss_db(
                rain_rate_mmhr=rain_rate,
                liquid_water_g_m3=lwc,
                pressure_hpa=pressure_hpa,
                temp_c=temp_c,
                rh_percent=rh_percent,
                freq_ghz=freq_ghz,
                elevation_deg=elevation_deg,
                time_percentage=time_pct,
                lat=lat,
                lon=lon
            )
            f.write(f"{scenario_name:<30} | {losses['rain']:>7.2f} | {losses['fog']:>7.2f} | {losses['gas']:>7.2f} | {losses['scintillation']:>7.2f} | {losses['total']:>7.2f}\n")

    # Write LaTeX table
    with open(latex_file, "w") as f:
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\begin{tabularx}{\\textwidth}{|l|c|c|c|c|c|}\n")
        f.write("\\hline\n")
        f.write("\\textbf{Scenario} & \\textbf{Rain (dB)} & \\textbf{Fog (dB)} & \\textbf{Gas (dB)} & \\textbf{Scint. (dB)} & \\textbf{Total (dB)} \\\\\n")
        f.write("\\hline\n")

        for scenario_name, rain_rate, lwc, time_pct in scenarios:
            losses = total_feeder_loss_db(
                rain_rate_mmhr=rain_rate,
                liquid_water_g_m3=lwc,
                pressure_hpa=pressure_hpa,
                temp_c=temp_c,
                rh_percent=rh_percent,
                freq_ghz=freq_ghz,
                elevation_deg=elevation_deg,
                time_percentage=time_pct,
                lat=lat,
                lon=lon
            )
            f.write(f"{scenario_name} & {losses['rain']:.2f} & {losses['fog']:.2f} & {losses['gas']:.2f} & {losses['scintillation']:.2f} & {losses['total']:.2f} \\\\\n")

        f.write("\\hline\n")
        f.write("\\end{tabularx}\n")
        f.write(f"\\caption{{Typical atmospheric loss values at 38 GHz, {elevation_deg}° elevation angle, 20 km slant path ({case_label}), Delhi 28.5°N 77.2°E.}}\n")
        f.write("\\label{tab:atm_losses}\n")
        f.write("\\end{table}\n")

    print(f"Generated: {output_file} and {latex_file}")

print("\nTables generated:")
print("  Nominal:    TABLE_B1_NOMINAL.txt, TABLE_B1_LATEX_NOMINAL.txt")
print("  Worst-case: TABLE_B1_WORSTCASE.txt, TABLE_B1_LATEX_WORSTCASE.txt")
