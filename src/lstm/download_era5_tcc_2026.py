"""
Download ERA5 total cloud cover (tcc, fraction 0-1) for the Delhi box, 2026 January-October.

Used only to fill cloud_amt_pct where NASA POWER CLOUD_AMT is missing (from 2026-04-05 on).
ERA5 total cloud cover is a different product from POWER CLOUD_AMT, so 2026 filled values
must be reported as a substitute in the paper.

Output: data/raw/era5/era5_tcc_delhi_2026.nc
Run in WSL (env ~/quantum_env) or Windows Python with cdsapi configured.
"""

import os

import cdsapi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "raw", "era5")
OUT_PATH = os.path.join(OUT_DIR, "era5_tcc_delhi_2026.nc")

request = {
    "product_type": ["reanalysis"],
    "variable": ["total_cloud_cover"],
    "year": ["2026"],
    "month": [f"{m:02d}" for m in range(1, 11)],
    "day": [f"{d:02d}" for d in range(1, 32)],
    "time": [f"{h:02d}:00" for h in range(24)],
    "data_format": "netcdf",
    "download_format": "unarchived",
    "area": [29, 76.5, 28.25, 77.5],
}


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    client = cdsapi.Client()
    client.retrieve("reanalysis-era5-single-levels", request).download(OUT_PATH)
    print(f"Saved {OUT_PATH}")


if __name__ == "__main__":
    main()
