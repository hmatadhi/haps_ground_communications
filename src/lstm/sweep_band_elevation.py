"""
Sensitivity sweep of the feeder-link rain and scintillation attenuation over the paper's
Ka-band feeder range (38.0-39.5 GHz) and elevation (11-30 deg), for the Delhi site.

Rain: ITU-R P.618 path attenuation (itur) at rain rates 1, 10, 25 mm/h (p = 0.01 %).
Scintillation: ITU-R P.618 at 1 % exceedance, with the 1 m antenna and 0.5 efficiency assumed.

Output: data/processed/parameter_analysis/band_elevation_sweep.csv

Run in WSL (env ~/quantum_env): python src/lstm/sweep_band_elevation.py
"""

import os

import numpy as np
import pandas as pd
from itur.models.itu618 import rain_attenuation, scintillation_attenuation

SITE_LAT, SITE_LON = 28.61, 77.21
GATEWAY_KM = 0.05
FREQS_GHZ = [38.0, 38.5, 39.0, 39.5]
ELEVS_DEG = [11.0, 15.0, 20.0, 30.0]
RAIN_RATES = [1.0, 10.0, 25.0]
ANT_D_M = 1.0
ETA = 0.5
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "processed", "parameter_analysis")


def scalar(x) -> float:
    return float(np.asarray(getattr(x, "value", x)).ravel()[0])


def scint_db(f, el):
    r = scintillation_attenuation(SITE_LAT, SITE_LON, f, el, 1.0, ANT_D_M, eta=ETA,
                                  T=288.15, H=60.0, P=1010.0)
    if isinstance(r, tuple):
        r = r[0]
    return scalar(r)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    for f in FREQS_GHZ:
        for el in ELEVS_DEG:
            row = {"freq_ghz": f, "elev_deg": el, "scint_db_1pct": scint_db(f, el)}
            for rate in RAIN_RATES:
                a = rain_attenuation(SITE_LAT, SITE_LON, f, el, hs=GATEWAY_KM, p=0.01, R001=rate)
                row[f"rain_{rate:g}mmh_db"] = scalar(a)
            rows.append(row)
    out = pd.DataFrame(rows)
    path = os.path.join(OUT_DIR, "band_elevation_sweep.csv")
    out.to_csv(path, index=False, float_format="%.3f")
    print(f"Wrote {path}")
    print(out.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
