"""
Compare the propagation properties produced by the LSTM and by itur (ITU-Rpy).

Writes data/processed/comparison/properties_comparison.csv with one row per property:
  source            - where the value comes from (LSTM, itur, or input data)
  hourly            - whether it varies hour to hour in the data
  used_by_lstm      - whether it is an LSTM input feature
  test_mae_db       - LSTM-vs-label MAE on the 2025 test split (LSTM rows only)
  persist_mae_db    - persistence-baseline MAE on the same test split
  note              - caveat for the paper

Run in WSL (env ~/quantum_env): python src/lstm/compare_properties.py
"""

import os

import numpy as np
import pandas as pd

from train_lstm import FEATURES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LSTM_PATH = os.path.join(ROOT, "data", "processed", "lstm", "lstm_dqn_inputs.csv")
ITUR_PATH = os.path.join(ROOT, "data", "processed", "itur", "itur_hourly_properties.csv")
OUT_DIR = os.path.join(ROOT, "data", "processed", "comparison")
OUT_PATH = os.path.join(OUT_DIR, "properties_comparison.csv")


def lstm_error_rows(lstm: pd.DataFrame) -> list[dict]:
    """MAE of the LSTM and of persistence, per horizon, on the test split."""
    test = lstm[lstm["split"] == "test"].reset_index(drop=True)
    # Last observed label at each issue time is the previous row's true_h1.
    last_observed = test["true_h1"].shift(1).bfill().values
    rows = []
    for h in range(1, 7):
        pred = test[f"pred_h{h}"].values
        true = test[f"true_h{h}"].values
        persist = last_observed
        rows.append({
            "property": f"rain_att_forecast_h{h}",
            "source": "LSTM",
            "hourly": True,
            "used_by_lstm": False,
            "test_mae_db": float(np.mean(np.abs(pred - true))),
            "persist_mae_db": float(np.mean(np.abs(persist - true))),
            "note": "Forecast of P.838 x L_EFF rain attenuation, h hours ahead",
        })
    return rows


def main() -> None:
    lstm = pd.read_csv(LSTM_PATH, parse_dates=["issue_time_utc"])
    itur = pd.read_csv(ITUR_PATH, parse_dates=["time_utc"])

    rows = lstm_error_rows(lstm)
    rows += [
        {"property": "rain_att_label (P.838 x L_EFF)", "source": "itur", "hourly": True,
         "used_by_lstm": False, "test_mae_db": np.nan, "persist_mae_db": np.nan,
         "note": f"max {itur['rain_att_db'].max():.0f} dB: L_EFF placeholder, no path-reduction factor"},
        {"property": "gas_att (P.676)", "source": "itur", "hourly": True,
         "used_by_lstm": False, "test_mae_db": np.nan, "persist_mae_db": np.nan,
         "note": f"range {itur['gas_att_db'].min():.2f}-{itur['gas_att_db'].max():.2f} dB"},
        {"property": "scint_att (P.618, 1 %)", "source": "itur", "hourly": True,
         "used_by_lstm": False, "test_mae_db": np.nan, "persist_mae_db": np.nan,
         "note": f"range {itur['scint_att_db'].min():.4f}-{itur['scint_att_db'].max():.4f} dB: "
                 "near constant, units/inputs need checking"},
        {"property": "cloud_att (P.840, 1 %)", "source": "itur", "hourly": False,
         "used_by_lstm": False, "test_mae_db": np.nan, "persist_mae_db": np.nan,
         "note": f"site statistic {itur['cloud_att_db_p1'].iloc[0]:.2f} dB, not hourly"},
    ]
    for f in FEATURES:
        rows.append({
            "property": f"input: {f}",
            "source": "NASA POWER / METAR / ERA5 / derived",
            "hourly": True,
            "used_by_lstm": True,
            "test_mae_db": np.nan,
            "persist_mae_db": np.nan,
            "note": "",
        })

    os.makedirs(OUT_DIR, exist_ok=True)
    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH, index=False, float_format="%.4f")
    print(f"Wrote {OUT_PATH} ({len(out)} rows)")
    print(out[["property", "source", "test_mae_db", "persist_mae_db"]].head(8).to_string(index=False))


if __name__ == "__main__":
    main()
