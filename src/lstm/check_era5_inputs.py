"""
Check the per-year ERA5 tclw files: time coverage, checksums (to catch duplicated years),
grid coordinates, and values at the nearest cell to the Delhi site.

Run in WSL (env ~/quantum_env): python src/lstm/check_era5_inputs.py
"""

import glob
import hashlib
import os

import numpy as np
import pandas as pd
import xarray as xr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ERA5_DIR = os.path.join(ROOT, "data", "raw", "era5")
SITE_LAT, SITE_LON = 28.61, 77.21


def md5(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def main() -> None:
    files = sorted(glob.glob(os.path.join(ERA5_DIR, "era5_tclw_delhi_*.nc")))
    checksums = {}
    for fn in files:
        ds = xr.open_dataset(fn)
        times = pd.to_datetime(ds["valid_time"].values)
        lat = ds["latitude"].values
        lon = ds["longitude"].values
        i = np.abs(lat - SITE_LAT).argmin()
        j = np.abs(lon - SITE_LON).argmin()
        series = ds["tclw"].values[:, i, j]
        checksums[os.path.basename(fn)] = md5(fn)
        print(os.path.basename(fn))
        print(f"  time: {times.min()} -> {times.max()} ({len(times)} hours)")
        print(f"  grid lat {lat}, lon {lon}")
        print(f"  nearest cell: {lat[i]}N, {lon[j]}E")
        print(f"  tclw kg/m2 min {series.min():.4f} max {series.max():.4f} mean {series.mean():.4f}")

    dupes = [k for k, v in checksums.items() if list(checksums.values()).count(v) > 1]
    print("Duplicate files (same checksum):", dupes if dupes else "none")


if __name__ == "__main__":
    main()
