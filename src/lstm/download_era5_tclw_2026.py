"""
Download ERA5 total column cloud liquid water (tclw) for the Delhi box, 2026, January to
October. Requires ~/.cdsapirc.

ERA5 lags real time by a few days, so the last days of October may be missing. The loader
(train_lstm.load_era5_tclw) takes whatever hours are in the file, and the 2026 table is
trimmed to the hours that have ERA5 values.

Area is [North, West, South, East], multiples of 0.25 (same box as the 2023-2025 request).
Output: data/raw/era5/era5_tclw_delhi_2026.nc
"""

import os

import cdsapi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "raw", "era5")
OUT_PATH = os.path.join(OUT_DIR, "era5_tclw_delhi_2026.nc")

request = {
    "product_type": ["reanalysis"],
    "variable": ["total_column_cloud_liquid_water"],
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
