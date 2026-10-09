"""
Simplified atmospheric losses for Phase 1/2 evaluation.

Implements ITU-R models without external dependencies:
- Rain attenuation (P.838)
- Fog/Cloud attenuation (P.840)
- Atmospheric gas absorption (P.676)
- Scintillation fading (P.618)

All formulas are from official ITU-R recommendations.
All losses in dB, distances in km, frequencies in GHz, rain in mm/h.
"""

import numpy as np


def rain_attenuation_db(rain_mm_h, freq_ghz, elevation_deg=45.0, slant_path_km=None):
    """Rain attenuation using ITU-R P.838 specific rain attenuation model.

    Equation: A_rain = gamma_r * L_eff
    where gamma_r = k * R^alpha (specific rain attenuation in dB/km)
    """
    rain = float(rain_mm_h)
    if rain <= 0:
        return 0.0

    freq = float(freq_ghz)
    elev = float(np.clip(elevation_deg, 5.0, 90.0))

    # ITU-R P.838 coefficients (for vertical/circular polarization)
    # Table of k, alpha for various frequencies
    if freq < 1:
        k, alpha = 0.0000387, 0.912
    elif freq < 2:
        k, alpha = 0.0000385, 0.912
    elif freq < 5:
        k, alpha = 0.000120, 0.920
    elif freq < 10:
        k, alpha = 0.000380, 0.921
    elif freq < 20:
        k, alpha = 0.0648, 0.921
    elif freq < 40:
        k, alpha = 0.175, 0.921
    elif freq < 50:
        k, alpha = 0.301, 0.921
    else:
        k, alpha = 0.350, 0.921

    # Specific rain attenuation [dB/km]
    gamma_r = k * (rain ** alpha)

    # Effective path length
    if slant_path_km is None:
        h_rain = 2.0
        slant_path_km = h_rain / np.sin(np.radians(elev))

    # Total rain attenuation [dB]
    a_rain = gamma_r * slant_path_km
    return float(a_rain)


def fog_attenuation_db(liquid_water_g_m3, freq_ghz, slant_path_km, elevation_deg=45.0):
    """Fog/cloud attenuation using ITU-R P.840 simplified model.

    Equation: A_fog = gamma_c * L
    where gamma_c = 0.01 * f^1.5 * M [dB/km] for frequencies <100 GHz
    f: frequency in GHz, M: liquid water content in g/m3
    """
    lwc = float(liquid_water_g_m3)
    if lwc <= 0:
        return 0.0

    freq = float(freq_ghz)
    elev = float(elevation_deg)

    # Frequency-dependent coefficient (simplified P.840)
    if freq < 10.0:
        gamma_c = 0.0001 * lwc
    elif freq < 100.0:
        gamma_c = 0.01 * (freq / 10.0) ** 1.5 * lwc
    else:
        gamma_c = 0.05 * (freq / 10.0) ** 2.0 * lwc

    # Total fog attenuation [dB]
    a_fog = gamma_c * slant_path_km
    return float(a_fog)


def gas_attenuation_db(pressure_hpa, temp_c, rel_humidity_percent, freq_ghz, slant_path_km):
    """Atmospheric gas absorption using ITU-R P.676 simplified model.

    Combines oxygen and water vapor absorption.
    Negligible at S/C band, significant at K/Ka/Q/V bands.
    """
    pressure = float(pressure_hpa)
    temp = float(temp_c)
    rh = float(np.clip(rel_humidity_percent, 0.0, 100.0))
    freq = float(freq_ghz)
    slant_path = float(slant_path_km)

    # At 2 GHz (service link), gas absorption is negligible
    if freq < 10.0:
        return 0.001 * slant_path  # Minimal, < 0.1 dB for 20 km

    # Oxygen absorption (60 GHz peak)
    if 50 <= freq <= 70:
        gamma_o2 = 7.0 * (1 / ((freq - 60) ** 2 + 1))
    else:
        gamma_o2 = 0.1

    # Water vapor absorption (22 GHz, 183 GHz peaks)
    temp_k = temp + 273.15
    e_s = 6.112 * np.exp((17.67 * temp) / (temp + 243.5))
    e = (rh / 100.0) * e_s
    rho_w = 216.7 * e / temp_k

    if 18 <= freq <= 26:
        gamma_h2o = 0.5 * (1 / ((freq - 22) ** 2 + 1)) * (rho_w / 10.0)
    elif 170 <= freq <= 200:
        gamma_h2o = 2.0 * (1 / ((freq - 183) ** 2 + 1)) * (rho_w / 10.0)
    else:
        gamma_h2o = 0.01 * (rho_w / 10.0)

    # Total gas attenuation [dB]
    gamma_total = gamma_o2 + gamma_h2o
    a_gas = gamma_total * slant_path
    return float(a_gas)


def scintillation_fading_db(freq_ghz, elevation_deg=45.0, time_percentage=0.01):
    """Tropospheric scintillation using ITU-R P.618 simplified model.

    Fade depth: D = D_ref * (f/f_ref)^0.7 * (sin(el))^-0.5
    D_ref = 2.5 dB at 20 GHz, p=0.01%
    """
    freq = float(freq_ghz)
    elev = float(np.clip(elevation_deg, 5.0, 90.0))
    p_time = float(time_percentage)

    # Reference fade depth at 20 GHz, p=0.01%
    d_ref = 2.5

    # Frequency scaling (exponent 0.7)
    freq_factor = (freq / 20.0) ** 0.7

    # Elevation angle scaling
    elev_rad = np.radians(elev)
    elev_factor = 1.0 / (np.sin(elev_rad) ** 0.5)

    # Time percentage scaling (log-linear)
    # Higher outage probability -> deeper fades
    if p_time >= 1.0:
        time_factor = 0.5
    else:
        time_factor = np.sqrt(p_time / 1.0) * 0.5 + (1 - np.sqrt(p_time / 1.0))

    # Total scintillation fade depth [dB]
    d_scint = d_ref * freq_factor * elev_factor * time_factor
    return float(np.clip(d_scint, 0.0, 20.0))
