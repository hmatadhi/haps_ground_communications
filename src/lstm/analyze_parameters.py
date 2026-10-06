"""
Sensitivity checks for the propagation parameters still in the model, using itur directly.

1. Scintillation (P.618, 1 %): how it responds to temperature, humidity, pressure, antenna
   diameter, and efficiency. Checks whether the near-constant hourly values come from the
   inputs or from the model.
2. Rain: itur path attenuation (P.618) against the paper's environment model
   (k*R^alpha over 66.3 km, in haps_association_env / battery_model) and the paper's worked
   example.
3. Specific attenuation: itur P.838 gamma_R against the paper's k = 0.3923, alpha = 0.8687 (89.86 deg).

Output: data/processed/parameter_analysis/parameter_sensitivity.csv

Run in WSL (env ~/quantum_env): python src/lstm/analyze_parameters.py
"""

import os

import numpy as np
import pandas as pd
from itur.models.itu618 import rain_attenuation, scintillation_attenuation
from itur.models.itu838 import rain_specific_attenuation, rain_specific_attenuation_coefficients

SITE_LAT, SITE_LON = 28.61, 77.21
FREQ_GHZ = 38.0
ELEV_DEG = 11.3
GATEWAY_KM = 0.05
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "processed", "parameter_analysis")

PAPER_K, PAPER_ALPHA = 0.3923, 0.8687          # P.838, 38 GHz, 89.86 deg (gateway geometry)
PAPER_H_RAIN_KM, PAPER_H_GW_KM, PAPER_ELEV_DEG = 5.278, 0.05, 89.86   # P.839 rain height, gateway


def paper_rain_db(rate):
    """Rain attenuation of the paper's model: gamma_R * L_s * r (P.618 reduction factor)."""
    gamma = PAPER_K * rate ** PAPER_ALPHA
    sin_t, cos_t = np.sin(np.radians(PAPER_ELEV_DEG)), np.cos(np.radians(PAPER_ELEV_DEG))
    l_s = (PAPER_H_RAIN_KM - PAPER_H_GW_KM) / sin_t
    l_g = l_s * cos_t
    r = 1.0 / (1.0 + 0.78 * np.sqrt(l_g * gamma) - 0.38 * (1.0 - np.exp(-2.0 * l_g)))
    return gamma * l_s * r


def scalar(x) -> float:
    return float(np.asarray(getattr(x, "value", x)).ravel()[0])


def scint(t_k, rh, p_hpa, d_m=1.0, eta=0.5, el=ELEV_DEG):
    r = scintillation_attenuation(SITE_LAT, SITE_LON, FREQ_GHZ, el, 1.0, d_m, eta=eta,
                                  T=t_k, H=rh, P=p_hpa)
    if isinstance(r, tuple):
        r = r[0]
    return scalar(r)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []

    base = dict(t_k=288.15, rh=60.0, p_hpa=1010.0)
    rows.append({"check": "scint baseline (T=15C, RH=60, P=1010, D=1m, eta=0.5)",
                 "value_db": scint(**base)})
    for label, kw in [
        ("T = 35 C (308.15 K)", dict(t_k=308.15, rh=60.0, p_hpa=1010.0)),
        ("T = 35 C given in C (not K)", dict(t_k=35.0, rh=60.0, p_hpa=1010.0)),
        ("RH = 95 %", dict(t_k=288.15, rh=95.0, p_hpa=1010.0)),
        ("P = 980 hPa", dict(t_k=288.15, rh=60.0, p_hpa=980.0)),
        ("elevation 30 deg", dict(t_k=288.15, rh=60.0, p_hpa=1010.0, el=30.0)),
        ("antenna D = 0.6 m", dict(t_k=288.15, rh=60.0, p_hpa=1010.0, d_m=0.6)),
        ("antenna D = 2.0 m", dict(t_k=288.15, rh=60.0, p_hpa=1010.0, d_m=2.0)),
        ("efficiency eta = 0.7", dict(t_k=288.15, rh=60.0, p_hpa=1010.0, eta=0.7)),
    ]:
        rows.append({"check": f"scint: {label}", "value_db": scint(**kw)})

    k_itur, a_itur = rain_specific_attenuation_coefficients(FREQ_GHZ, ELEV_DEG, 0)
    rows.append({"check": "P.838 k (itur)", "value_db": scalar(k_itur)})
    rows.append({"check": "P.838 alpha (itur)", "value_db": scalar(a_itur)})
    rows.append({"check": "P.838 k (paper env model)", "value_db": PAPER_K})
    rows.append({"check": "P.838 alpha (paper env model)", "value_db": PAPER_ALPHA})

    for rate in [1.0, 10.0, 25.0]:
        gamma = scalar(rain_specific_attenuation(rate, FREQ_GHZ, ELEV_DEG, 0))
        paper_env = paper_rain_db(rate)
        path = scalar(rain_attenuation(SITE_LAT, SITE_LON, FREQ_GHZ, ELEV_DEG,
                                       hs=GATEWAY_KM, p=0.01, R001=rate))
        rows.append({"check": f"rain {rate:g} mm/h: P.618 path (itur)", "value_db": path})
        rows.append({"check": f"rain {rate:g} mm/h: gamma_R (itur, dB/km)", "value_db": gamma})
        rows.append({"check": f"rain {rate:g} mm/h: paper env model", "value_db": paper_env})
    rows.append({"check": "rain 10 mm/h: paper worked example", "value_db": paper_rain_db(10.0)})

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(OUT_DIR, "parameter_sensitivity.csv"), index=False, float_format="%.4f")
    print(out.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
