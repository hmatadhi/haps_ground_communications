"""
Compute the hourly ITU-Rpy (itur) propagation quantities for the Delhi feeder link
(38 GHz, 11.3 deg elevation) over 2023-2025 from the same inputs the LSTM sees.

Columns written to data/processed/itur/itur_hourly_properties.csv:
  rain_att_db      ITU-R P.838 specific rain attenuation x L_EFF_KM (the LSTM label)
  gas_att_db       ITU-R P.676 slant-path gaseous attenuation (from T, P, humidity)
  scint_att_db     ITU-R P.618 tropospheric scintillation at p = 1 % exceedance
  cloud_att_db_p1  ITU-R P.840 cloud/fog attenuation at p = 1 % (site statistic, constant)

Placeholders that still need values before paper use:
  L_EFF_KM   - effective rain path length (see train_lstm.py)
  ANT_D_M    - antenna diameter for scintillation averaging (1 m assumed)
  ETA        - antenna efficiency (0.5 assumed)

Run in WSL (env ~/quantum_env): python src/lstm/compute_itur_hourly.py
"""

import os

import numpy as np
import pandas as pd
from scintillation_p618 import scintillation_fade_db
from itur.models.itu676 import gaseous_attenuation_slant_path
from itur.models.itu838 import rain_specific_attenuation
from itur.models.itu840 import cloud_attenuation

from train_lstm import ELEV_DEG, FREQ_GHZ, SITE_LAT, SITE_LON, build_table, rain_path_attenuation_db

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "processed", "itur")
OUT_PATH = os.path.join(OUT_DIR, "itur_hourly_properties.csv")

YEARS = [2023, 2024, 2025]
ANT_D_M = 1.0
ETA = 0.5


def vapour_density(t_c: np.ndarray, rh_pct: np.ndarray) -> np.ndarray:
    """Water-vapour density (g/m^3) from temperature and relative humidity (Magnus formula)."""
    e_s = 6.1078 * np.exp(17.27 * t_c / (t_c + 237.3))  # hPa
    e = rh_pct / 100.0 * e_s
    return 216.7 * e / (t_c + 273.15)


def scint_one(t_c: float, rh_pct: float, p_hpa: float) -> float:
    """P.618 scintillation fade (dB) at 1 % exceedance for one hour.

    Uses scintillation_p618.py, because itur 0.4.0's wet term drops the humidity dependence
    (see that module). Temperature is in degrees Celsius, as the P.453 functions expect.
    """
    return scintillation_fade_db(t_c, rh_pct, p_hpa, FREQ_GHZ, ELEV_DEG, 1.0, ANT_D_M, ETA)


def main() -> None:
    df = build_table(YEARS)
    t_c = df["t2m_c"].values
    t_k = t_c + 273.15
    p_hpa = df["ps_kpa"].values * 10.0
    rh = df["rh2m_pct"].values
    rho = vapour_density(t_c, rh)

    gamma = np.asarray(rain_specific_attenuation(df["precip_mmh"].values, FREQ_GHZ, ELEV_DEG, 0))
    rain_db = rain_path_attenuation_db(df["precip_mmh"].values)

    gas_db = np.array([
        float(np.asarray(gaseous_attenuation_slant_path(FREQ_GHZ, ELEV_DEG, r, p, t, mode="approx")).ravel()[0])
        for r, p, t in zip(rho, p_hpa, t_k)
    ])

    scint_db = np.array([scint_one(t, h, p) for t, h, p in zip(t_c, rh, p_hpa)])

    cloud_p1 = float(np.asarray(cloud_attenuation(SITE_LAT, SITE_LON, ELEV_DEG, FREQ_GHZ, 1.0)).ravel()[0])

    out = pd.DataFrame({
        "time_utc": df.index,
        "precip_mmh": df["precip_mmh"].values,
        "gamma_r_db_km": gamma,
        "rain_att_db": rain_db,
        "gas_att_db": gas_db,
        "scint_att_db": scint_db,
        "cloud_att_db_p1": cloud_p1,
    })
    os.makedirs(OUT_DIR, exist_ok=True)
    out.to_csv(OUT_PATH, index=False, float_format="%.6f")
    print(f"Wrote {OUT_PATH} ({len(out)} rows)")
    print(out.describe().T[["mean", "min", "max"]])


if __name__ == "__main__":
    main()
