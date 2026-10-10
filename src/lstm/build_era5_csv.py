"""
Build data/raw/era5/weatherDataTCLWEra5Delhi.csv from the per-year ERA5 tclw files.

Takes the nearest ERA5 grid cell to the Delhi site (28.50N, 77.25E) and writes one
row per UTC hour: time_utc, tclw_kgm2.

Run in WSL (env ~/quantum_env): python src/lstm/build_era5_csv.py
"""

import glob
import os

import pandas as pd
import xarray as xr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ERA5_DIR = os.path.join(ROOT, "data", "raw", "era5")
OUT_PATH = os.path.join(ERA5_DIR, "weatherDataTCLWEra5Delhi.csv")
ERA5_LAT, ERA5_LON = 28.50, 77.25


def main() -> None:
    parts = []
    for fn in sorted(glob.glob(os.path.join(ERA5_DIR, "era5_tclw_delhi_*.nc"))):
        ds = xr.open_dataset(fn)
        cell = ds["tclw"].sel(latitude=ERA5_LAT, longitude=ERA5_LON, method="nearest")
        times = pd.to_datetime(ds["valid_time"].values)
        print(f"{os.path.basename(fn)}: {times.min()} -> {times.max()} ({len(times)} hours)")
        parts.append(pd.DataFrame({"time_utc": times, "tclw_kgm2": cell.values}))
    out = pd.concat(parts).sort_values("time_utc")
    out.to_csv(OUT_PATH, index=False, float_format="%.6f")
    print(f"Wrote {OUT_PATH} ({len(out)} rows)")


if __name__ == "__main__":
    main()
