"""
Check the ITU-R P.618 path rain attenuation from itur at several rain rates, for the Delhi
feeder link (38 GHz, 11.3 deg elevation, 50 m gateway). Compares with the paper's
worked example (5.9 dB at 10 mm/h, 15.2 dB at 25 mm/h) and with the old placeholder
(66 km x gamma_R).

Run in WSL (env ~/quantum_env): python src/lstm/check_rain_attenuation.py
"""

import numpy as np
from itur.models.itu618 import rain_attenuation
from itur.models.itu838 import rain_specific_attenuation

SITE_LAT, SITE_LON = 28.61, 77.21
FREQ_GHZ = 38.0
ELEV_DEG = 11.3
GATEWAY_KM = 0.05
RAINS = [0.5, 1.0, 5.0, 10.0, 25.0]


def path_attenuation_db(rain_mm_h: float) -> float:
    """P.618 path attenuation exceeded 0.01 % for a rain rate of rain_mm_h (R0.01 set to it)."""
    a = rain_attenuation(SITE_LAT, SITE_LON, FREQ_GHZ, ELEV_DEG, hs=GATEWAY_KM,
                         p=0.01, R001=rain_mm_h)
    return float(np.asarray(getattr(a, "value", a)).ravel()[0])


def main() -> None:
    print(f"{'R (mm/h)':>9} {'gamma_R':>9} {'placeholder 66 km':>18} {'P.618 path':>11}")
    for r in RAINS:
        gamma = float(np.asarray(rain_specific_attenuation(r, FREQ_GHZ, ELEV_DEG, 0)).ravel()[0])
        print(f"{r:9.1f} {gamma:9.3f} {gamma * 66.0:18.2f} {path_attenuation_db(r):11.2f}")
    print("Paper example: 5.9 dB at 10 mm/h, 15.2 dB at 25 mm/h")


if __name__ == "__main__":
    main()
