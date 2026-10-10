"""
Build a TEMPORARY hourly Delhi dataset for the Phase 3 LSTM pipeline.

Merges:
  - NASA POWER hourly (2023-2025): T2M, RH2M, PS, WS10M, PRECTOTCORR, CLOUD_AMT
  - VIDP METAR (Iowa Mesonet): visibility (statute miles -> km), weather-code flags

cloud_liquid_water_kgm2 is a DUMMY placeholder (0.0) until ERA5 `tclw` is downloaded.
tclw_is_placeholder = 1 marks every such row so it cannot be mistaken for real data.

Output: data/processed/delhi_hourly_TEMP.csv
"""

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
POWER_DIR = os.path.join(ROOT, "data", "raw", "nasa_power")
METAR_PATHS = [
    os.path.join(ROOT, "data", "raw", "metar_vidp", "vidp_2023_2025.csv"),
    os.path.join(ROOT, "data", "raw", "metar_vidp", "vidp_2026.csv"),
]
OUT_PATH = os.path.join(ROOT, "data", "processed", "delhi_hourly_TEMP.csv")

YEARS = [2023, 2024, 2025, 2026]
POWER_MISSING = -999.0
POWER_HEADER_LINES = 14  # NASA POWER prints a header block before the column row
STATUTE_MILE_KM = 1.609344


def load_power() -> pd.DataFrame:
    frames = []
    for year in YEARS:
        path = os.path.join(POWER_DIR, f"power_hourly_delhi_{year}.csv")
        df = pd.read_csv(path, skiprows=POWER_HEADER_LINES)
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["time_utc"] = pd.to_datetime(
        dict(year=df["YEAR"], month=df["MO"], day=df["DY"], hour=df["HR"])
    )
    df = df.replace(POWER_MISSING, np.nan)
    return df.rename(columns={
        "T2M": "t2m_c",
        "RH2M": "rh2m_pct",
        "PS": "ps_kpa",
        "WS10M": "ws10m_ms",
        "PRECTOTCORR": "precip_mmh",
        "CLOUD_AMT": "cloud_amt_pct",
    })[["time_utc", "t2m_c", "rh2m_pct", "ps_kpa", "ws10m_ms", "precip_mmh", "cloud_amt_pct"]]


def load_metar() -> pd.DataFrame:
    df = pd.concat(
        [pd.read_csv(p, na_values=["null"], low_memory=False) for p in METAR_PATHS if os.path.exists(p)],
        ignore_index=True,
    )
    df["time_utc"] = pd.to_datetime(df["valid"]).dt.floor("h")
    wx = df["wxcodes"].fillna("")
    df["vis_km"] = pd.to_numeric(df["vsby"], errors="coerce") * STATUTE_MILE_KM
    df["wx_rain"] = wx.str.contains("RA|DZ|TS").astype(int)
    df["wx_fog"] = wx.str.contains("FG|BR").astype(int)
    # Several METARs can fall in one hour; keep the first one per hour.
    return df.sort_values("time_utc").drop_duplicates("time_utc", keep="first")[
        ["time_utc", "vis_km", "wx_rain", "wx_fog"]
    ]


def main() -> None:
    power = load_power()
    metar = load_metar()

    full_index = pd.date_range(power["time_utc"].min(), power["time_utc"].max(), freq="h")
    df = pd.DataFrame({"time_utc": full_index})
    df = df.merge(power, on="time_utc", how="left").merge(metar, on="time_utc", how="left")

    # DUMMY placeholder until ERA5 tclw is downloaded.
    df["cloud_liquid_water_kgm2"] = 0.0
    df["tclw_is_placeholder"] = 1

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df.to_csv(OUT_PATH, index=False, float_format="%.4f")

    n = len(df)
    print(f"Wrote {OUT_PATH}")
    print(f"Rows: {n} (expected 26304)")
    for col in ["t2m_c", "rh2m_pct", "precip_mmh", "vis_km"]:
        print(f"  {col}: {df[col].isna().sum()} missing ({df[col].isna().mean():.1%})")


if __name__ == "__main__":
    main()
