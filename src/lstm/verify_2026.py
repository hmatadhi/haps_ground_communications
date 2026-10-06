"""
Verify the LSTM forecaster and the real 2026 data (out of sample: 2026 is not in training).

Checks:
  1. Input coverage for 2026: hours with NASA POWER, METAR, and ERA5 tclw.
  2. Rain consistency: NASA POWER precipitation vs METAR rain codes, hour by hour.
  3. LSTM forecast skill on 2026 against persistence, per horizon and per regime.

Writes data/processed/verify_2026/verify_2026_summary.csv and prints the summary.

Run in WSL (env ~/quantum_env): python src/lstm/verify_2026.py
(Run export_lstm_forecasts.py first, after the 2026 ERA5 file is in data/raw/era5/.)
"""

import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BASE_CSV = os.path.join(ROOT, "data", "processed", "delhi_hourly_TEMP.csv")
FORECASTS = os.path.join(ROOT, "data", "processed", "lstm", "lstm_dqn_inputs.csv")
OUT_DIR = os.path.join(ROOT, "data", "processed", "verify_2026")
ERA5_2026 = os.path.join(ROOT, "data", "raw", "era5", "era5_tclw_delhi_2026.nc")
RAIN_MM_H = 0.1  # hour counts as rain in POWER above this rate


def regime(row) -> str:
    if row["max_precip"] >= 1.0:
        return "rain"
    if row["mean_cloud"] >= 70:
        return "cloudy"
    if row["mean_cloud"] <= 30:
        return "clear"
    return "mixed"


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    base = pd.read_csv(BASE_CSV, parse_dates=["time_utc"])
    base26 = base[base["time_utc"].dt.year == 2026].copy()
    print(f"2026 hours in base table: {len(base26)}")
    print(f"ERA5 2026 file present: {os.path.exists(ERA5_2026)}")
    print("Missing values in 2026 base table:")
    print(base26[["t2m_c", "rh2m_pct", "precip_mmh", "vis_km", "cloud_liquid_water_kgm2"]]
          .isna().sum().to_string())

    # Rain consistency: POWER rain hour vs METAR rain code, on hours that have both.
    both = base26.dropna(subset=["precip_mmh", "wx_rain"])
    power_rain = both["precip_mmh"] >= RAIN_MM_H
    metar_rain = both["wx_rain"] == 1
    agree = (power_rain == metar_rain).mean()
    print(f"\nPOWER vs METAR rain agreement (2026, {len(both)} hours): {agree:.1%}")
    print(f"  POWER rain hours: {int(power_rain.sum())}   METAR rain hours: {int(metar_rain.sum())}")

    fc = pd.read_csv(FORECASTS, parse_dates=["issue_time_utc"])
    v = fc[fc["split"] == "verify_2026"].reset_index(drop=True)
    if v.empty:
        print("\nNo verify_2026 forecasts yet. Waiting for ERA5 2026 and re-running the export.")
        return

    # Persistence: last observed label, i.e. the previous hour's true_h1.
    last_observed = v["true_h1"].shift(1).bfill().values

    rows = []
    for h in range(1, 7):
        pred = v[f"pred_h{h}"].values
        true = v[f"true_h{h}"].values
        ok = ~np.isnan(true)
        rows.append({
            "scope": "all",
            "horizon_h": h,
            "lstm_mae_db": float(np.mean(np.abs(pred[ok] - true[ok]))),
            "persist_mae_db": float(np.mean(np.abs(last_observed[ok] - true[ok]))),
            "lstm_rmse_db": float(np.sqrt(np.mean((pred[ok] - true[ok]) ** 2))),
            "persist_rmse_db": float(np.sqrt(np.mean((last_observed[ok] - true[ok]) ** 2))),
            "n": int(ok.sum()),
        })

    # Per-regime skill at the 1-hour horizon, using the same day-level tags as the episodes.
    v["day"] = v["issue_time_utc"].dt.floor("D")
    day_stats = base26.assign(day=base26["time_utc"].dt.floor("D")).groupby("day").agg(
        max_precip=("precip_mmh", "max"), mean_cloud=("cloud_amt_pct", "mean"))
    v = v.merge(day_stats, left_on="day", right_index=True, how="left")
    v["regime"] = v.apply(lambda r: regime({"max_precip": r["max_precip"],
                                            "mean_cloud": r["mean_cloud"]}), axis=1)
    for reg, grp in v.groupby("regime"):
        ok = ~grp["true_h1"].isna()
        if ok.sum() == 0:
            continue
        lo = grp.index.values
        rows.append({
            "scope": f"regime:{reg}",
            "horizon_h": 1,
            "lstm_mae_db": float(np.mean(np.abs(grp["pred_h1"][ok] - grp["true_h1"][ok]))),
            "persist_mae_db": float(np.mean(np.abs(last_observed[lo][ok.values] - grp["true_h1"][ok]))),
            "lstm_rmse_db": float(np.sqrt(np.mean((grp["pred_h1"][ok] - grp["true_h1"][ok]) ** 2))),
            "persist_rmse_db": float(np.sqrt(np.mean((last_observed[lo][ok.values] - grp["true_h1"][ok]) ** 2))),
            "n": int(ok.sum()),
        })

    summary = pd.DataFrame(rows)
    summary.to_csv(os.path.join(OUT_DIR, "verify_2026_summary.csv"), index=False, float_format="%.4f")
    print("\nLSTM vs persistence on 2026 (out of sample):")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
