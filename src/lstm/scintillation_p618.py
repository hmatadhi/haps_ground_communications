"""
ITU-R P.618 tropospheric scintillation, written out step by step, for checking itur.

itur 0.4.0 computes the wet term of P.453 with an extra factor of 1e-6, which makes N_wet
(and so the humidity dependence of scintillation) effectively zero. This module uses the
P.453 wet term without that factor, so the weather inputs take effect.

Inputs: T_c (deg C), RH (%), P (hPa), frequency f (GHz), elevation el (deg), time
percentage p (%), antenna diameter D (m), efficiency eta, effective layer height hL (m).

Used by check_scintillation_weather.py to compare with itur.
"""

import numpy as np
from itur.models.itu453 import water_vapour_pressure


def wet_term_N(t_c, rh, p_hpa):
    """Wet term of refractivity N_wet (N-units), ITU-R P.453: 72 e/T + 3.75e5 e/T^2."""
    e = float(np.asarray(getattr(water_vapour_pressure(t_c, p_hpa, rh), "value",
                                 water_vapour_pressure(t_c, p_hpa, rh))).ravel()[0])
    t_k = t_c + 273.15
    return 72.0 * e / t_k + 3.75e5 * e / t_k ** 2


def scintillation_fade_db(t_c, rh, p_hpa, f_ghz, el_deg, p_percent, d_m, eta=0.5, hL=1000.0):
    """P.618 fade depth (dB) exceeded for p_percent of the time."""
    n_wet = wet_term_N(t_c, rh, p_hpa)
    sigma_ref = 3.6e-3 + 1e-4 * n_wet                                    # Eq. 43
    sin_el = np.sin(np.deg2rad(el_deg))
    L = 2 * hL / (np.sqrt(sin_el ** 2 + 2.35e-4) + sin_el)               # Eq. 44
    d_eff = np.sqrt(eta) * d_m                                           # Eq. 45
    x = 1.22 * d_eff ** 2 * f_ghz / L                                    # as written in itur
    if x >= 7.0:
        g = 0.0
    else:
        g = np.sqrt(3.86 * (x ** 2 + 1) ** (11.0 / 12) * np.sin(11.0 / 6 * np.arctan2(1, x))
                    - 7.08 * x ** (5.0 / 6))                             # Eq. 46
    sigma = sigma_ref * f_ghz ** (7.0 / 12) * g / sin_el ** 1.2          # Eq. 42
    a = -0.061 * np.log10(p_percent) ** 3 + 0.072 * np.log10(p_percent) ** 2 \
        - 1.71 * np.log10(p_percent) + 3                                 # Eq. 48
    return float(a * sigma)                                              # Eq. 49
