"""
Check how itur's P.618 scintillation depends on surface weather (T, RH, P), step by step:
  e (water vapour pressure), N_wet, sigma_ref, sigma, and the 1 % fade.

Run in WSL (env ~/quantum_env): python src/lstm/check_scintillation_weather.py
"""

import numpy as np
from itur.models.itu618 import scintillation_attenuation, scintillation_attenuation_sigma
from itur.models.itu453 import water_vapour_pressure, wet_term_radio_refractivity

SITE_LAT, SITE_LON = 28.61, 77.21
F, EL, D, ETA = 38.0, 11.3, 1.0, 0.5


def scalar(x) -> float:
    if isinstance(x, tuple):
        x = x[0]
    return float(np.asarray(getattr(x, "value", x)).ravel()[0])


def main() -> None:
    # itur's P.453 functions take temperature in degrees Celsius (they add 273.15 internally).
    print(f"{'T (C)':>7} {'RH %':>6} {'P hPa':>7} {'e hPa':>8} {'N_wet':>8} {'sigma':>10} {'fade 1% dB':>11}")
    for t_c, rh, p in [(15, 20, 1010), (15, 60, 1010), (15, 95, 1010),
                       (35, 60, 1010), (0, 60, 1010), (15, 60, 980)]:
        e = scalar(water_vapour_pressure(t_c, p, rh))
        nwet = scalar(wet_term_radio_refractivity(e, t_c))
        sig = scalar(scintillation_attenuation_sigma(SITE_LAT, SITE_LON, F, EL, 1.0, D, ETA,
                                                     T=t_c, H=rh, P=p))
        fade = scalar(scintillation_attenuation(SITE_LAT, SITE_LON, F, EL, 1.0, D, ETA,
                                                T=t_c, H=rh, P=p))
        print(f"{t_c:7.1f} {rh:6.1f} {p:7.1f} {e:8.3f} {nwet:8.3f} {sig:10.6f} {fade:11.4f}")


if __name__ == "__main__":
    main()
