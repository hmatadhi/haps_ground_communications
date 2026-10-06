"""
Check that the LSTM pipeline libraries import and that the 2023 ERA5 file reads.
Also checks that h5py can open it (used on Windows, where netCDF4 is blocked).

Run in WSL (env ~/quantum_env): python src/lstm/check_library_read.py
"""

import os

import h5py
import itur
import netCDF4
import torch
import xarray as xr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ERA5_PATH = os.path.join(ROOT, "data", "raw", "era5", "era5_tclw_delhi_2023.nc")


def main() -> None:
    print(f"netCDF4 {netCDF4.__version__}, itur {itur.__version__}, torch {torch.__version__}")
    ds = xr.open_dataset(ERA5_PATH)
    print("xarray tclw shape:", ds.tclw.shape)
    print("valid_time:", str(ds.valid_time.values[0])[:19], "->", str(ds.valid_time.values[-1])[:19])
    with h5py.File(ERA5_PATH, "r") as f:
        print("h5py keys:", list(f.keys()))


if __name__ == "__main__":
    main()
