"""
Download ERA5 total column cloud liquid water (tclw) for the Delhi box, 2023-2025.

Requires ~/.cdsapirc (url + key). Area is [North, West, South, East], multiples of 0.25.
The full 3-year request exceeds the CDS cost limit (157,824 > 121,000), so it is
split into one request per year. Output: data/raw/era5/era5_tclw_delhi_{year}.nc
"""

import os

import cdsapi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "raw", "era5")

YEARS = ["2023", "2024", "2025"]

dataset = "reanalysis-era5-single-levels"
request = {
    "product_type": ["reanalysis"],
    "variable": ["total_column_cloud_liquid_water"],
    "year": YEARS,
    "month": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12"
    ],
    "day": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12",
        "13", "14", "15",
        "16", "17", "18",
        "19", "20", "21",
        "22", "23", "24",
        "25", "26", "27",
        "28", "29", "30",
        "31"
    ],
    "time": [
        "00:00", "01:00", "02:00",
        "03:00", "04:00", "05:00",
        "06:00", "07:00", "08:00",
        "09:00", "10:00", "11:00",
        "12:00", "13:00", "14:00",
        "15:00", "16:00", "17:00",
        "18:00", "19:00", "20:00",
        "21:00", "22:00", "23:00"
    ],
    "data_format": "netcdf",
    "download_format": "unarchived",
    "area": [29, 76.5, 28.25, 77.5]
}


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    client = cdsapi.Client()
    for year in YEARS:
        out_path = os.path.join(OUT_DIR, f"era5_tclw_delhi_{year}.nc")
        if os.path.exists(out_path):
            print(f"Skipping {year}: {out_path} already exists")
            continue
        client.retrieve(dataset, dict(request, year=[year])).download(out_path)
        print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
