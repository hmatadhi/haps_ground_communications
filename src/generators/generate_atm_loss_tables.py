#!/usr/bin/env python3
"""
Generate nominal and worst-case atmospheric loss tables for the 38 GHz feeder link.

Fills in tab:atm_losses_nominal / tab:atm_losses_worstcase -- referenced in
HAPS_AI_HW_ChannelModel.tex (S III.B) since the document was first written,
but never generated. Geometry matches the existing text: nominal = 50km
horizontal / 21.75 deg elevation / 54km slant path; worst-case = 100km
horizontal / 11.3 deg elevation / 102km slant path (100km service-radius
edge, per S "Feeder Link Geometry").
"""

import os
import pandas as pd
from plots.atmospheric_losses import total_feeder_loss_db

os.makedirs('appendix_data', exist_ok=True)
os.makedirs('appendix_tables', exist_ok=True)

FREQ_GHZ = 38.0
RAIN_RATE_MMHR = 10.0       # Design rain rate, matches fig_atm_loss_nominal_frequency.png
LIQUID_WATER_G_M3 = 0.05    # Medium fog
PRESSURE_HPA = 1013.0
TEMP_C = 15.0
RH_PERCENT = 60.0
TIME_PERCENTAGE = 0.01      # 0.01% outage allowance
LAT, LON = 28.5, 77.2       # Delhi

SCENARIOS = {
    'nominal':   dict(label='Nominal',    elevation_deg=21.75, horiz_km=50,  slant_km=54),
    'worstcase': dict(label='Worst-case', elevation_deg=11.3,  horiz_km=100, slant_km=102),
}

print("=" * 70)
print("Atmospheric Loss Tables: Nominal vs Worst-Case (38 GHz feeder link)")
print("=" * 70)

rows = []
for key, geo in SCENARIOS.items():
    losses = total_feeder_loss_db(
        rain_rate_mmhr=RAIN_RATE_MMHR,
        liquid_water_g_m3=LIQUID_WATER_G_M3,
        pressure_hpa=PRESSURE_HPA,
        temp_c=TEMP_C,
        rh_percent=RH_PERCENT,
        freq_ghz=FREQ_GHZ,
        elevation_deg=geo['elevation_deg'],
        time_percentage=TIME_PERCENTAGE,
        lat=LAT, lon=LON,
    )
    row = {
        'Scenario': geo['label'],
        'Elevation_deg': geo['elevation_deg'],
        'Horizontal_km': geo['horiz_km'],
        'Slant_path_km': geo['slant_km'],
        'Rain_dB': round(losses['rain'], 2),
        'Fog_dB': round(losses['fog'], 2),
        'Gas_dB': round(losses['gas'], 2),
        'Scintillation_dB': round(losses['scintillation'], 2),
        'Total_dB': round(losses['total'], 2),
    }
    rows.append(row)
    print(f"\n{geo['label']} ({geo['elevation_deg']} deg elevation, {geo['slant_km']} km slant path):")
    print(f"  Rain:          {row['Rain_dB']:7.2f} dB")
    print(f"  Fog:           {row['Fog_dB']:7.2f} dB")
    print(f"  Gas:           {row['Gas_dB']:7.2f} dB")
    print(f"  Scintillation: {row['Scintillation_dB']:7.2f} dB")
    print(f"  TOTAL:         {row['Total_dB']:7.2f} dB")

df = pd.DataFrame(rows)
df.to_csv('appendix_data/atm_losses_nominal_worstcase.csv', index=False)
print(f"\n[OK] CSV saved: appendix_data/atm_losses_nominal_worstcase.csv")

if len(rows) == 2 and rows[1]['Total_dB'] > 0:
    ratio = rows[1]['Total_dB'] / max(rows[0]['Total_dB'], 1e-9)
    print(f"\nWorst-case / nominal total-loss ratio: {ratio:.2f}x")


def make_table(row, label, scenario_name):
    return f"""\\begin{{table}}[h!]
\\centering
\\small
\\begin{{tabular}}{{lr}}
\\hline
\\textbf{{Component}} & \\textbf{{Loss [dB]}} \\\\
\\hline
Rain (P.618/P.838) & {row['Rain_dB']:.2f} \\\\
Fog/cloud (P.840) & {row['Fog_dB']:.2f} \\\\
Atmospheric gas (P.676) & {row['Gas_dB']:.2f} \\\\
Scintillation (P.618, {TIME_PERCENTAGE:g}\\% outage) & {row['Scintillation_dB']:.2f} \\\\
\\hline
\\textbf{{Total}} & \\textbf{{{row['Total_dB']:.2f}}} \\\\
\\hline
\\end{{tabular}}
\\caption{{Atmospheric loss breakdown, {scenario_name}: 38\\,GHz feeder link, {row['Elevation_deg']:.2f}$^\\circ$ elevation, {row['Slant_path_km']:.0f}\\,km slant path, {RAIN_RATE_MMHR:.0f}\\,mm/h rain, Delhi.}}
\\label{{{label}}}
\\end{{table}}
"""


nominal_row = df[df['Scenario'] == 'Nominal'].iloc[0]
worstcase_row = df[df['Scenario'] == 'Worst-case'].iloc[0]

with open('appendix_tables/atm_losses_nominal.tex', 'w') as f:
    f.write(make_table(nominal_row, 'tab:atm_losses_nominal', 'nominal case'))
print("[OK] LaTeX table saved: appendix_tables/atm_losses_nominal.tex")

with open('appendix_tables/atm_losses_worstcase.tex', 'w') as f:
    f.write(make_table(worstcase_row, 'tab:atm_losses_worstcase', 'worst case'))
print("[OK] LaTeX table saved: appendix_tables/atm_losses_worstcase.tex")

print("\n" + "=" * 70)
print("Done. Add \\input{appendix_tables/atm_losses_nominal.tex} and")
print("\\input{appendix_tables/atm_losses_worstcase.tex} to the .tex document.")
print("=" * 70)
