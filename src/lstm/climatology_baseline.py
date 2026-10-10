"""
Climatology baseline for the feeder rain-attenuation forecast.

For each forecast hour, the climatological value is the mean rain attenuation over the training
years (2023-2025) for the same calendar month and hour of day. It uses no recent observations,
so it shows how much the LSTM gains from the current weather state.

Scored on the same 2026 forecast hours as the LSTM and persistence (verify_2026 split of
lstm_dqn_inputs.csv). Output: data/processed/verify_2026/climatology_summary.csv

Run in WSL (env ~/quantum_env): python src/lstm/climatology_baseline.py
"""

import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ITUR_CSV = os.path.join(ROOT, "data", "processed", "itur", "itur_hourly_properties.csv")
INPUTS_CSV = os.path.join(ROOT, "data", "processed", "lstm", "lstm_dqn_inputs.csv")
OUT_DIR = os.path.join(ROOT, "data", "processed", "verify_2026")
TRAIN_YEARS = [2023, 2024, 2025]
TEST_SPLIT = "verify_2026"


def main() -> None:
    lab = pd.read_csv(ITUR_CSV, parse_dates=["time_utc"]).set_index("time_utc")["rain_att_db"]
    train = lab[lab.index.year.isin(TRAIN_YEARS)]
    clim = train.groupby([train.index.month, train.index.hour]).mean()

    inp = pd.read_csv(INPUTS_CSV, parse_dates=["issue_time_utc"])
    inp = inp[inp["split"] == TEST_SPLIT].copy()
    rows = []
    for h in range(1, 7):
        # The forecast for hour issue_time + h (the LSTM's pred_h for that issue time).
        target_time = inp["issue_time_utc"] + pd.Timedelta(hours=h)
        clim_pred = np.array([clim.get((t.month, t.hour), np.nan) for t in target_time])
        truth = inp[f"true_h{h}"].values
        ok = ~np.isnan(clim_pred) & ~np.isnan(truth)
        err = clim_pred[ok] - truth[ok]
        rows.append({
            "horizon_h": h,
            "climatology_mae_db": float(np.mean(np.abs(err))),
            "climatology_rmse_db": float(np.sqrt(np.mean(err ** 2))),
            "n": int(ok.sum()),
        })
    out = pd.DataFrame(rows)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "climatology_summary.csv")
    out.to_csv(path, index=False, float_format="%.4f")
    print(out.round(3).to_string(index=False))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
