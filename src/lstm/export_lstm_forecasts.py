"""
Export causal LSTM forecasts for the DQN, with out-of-sample status for every year.

Forecast sources:
  2024  - forward model trained on 2023 only (models/lstm/rain_lstm_fwd2023.pt)
          split = "oof_2024"
  2025  - model trained on 2023-2024 (models/lstm/rain_lstm.pt)
          split = "test_2025"
  2026  - same model as 2025 (no 2026 in training)
          split = "verify_2026"  (only where ERA5 2026 exists, otherwise the hour is dropped)

Each row is one issue time t: the forecast uses only the 24 hours up to and including t.
pred_h1..h6 forecast rain attenuation (P.618 label, dB) for t+1..t+6.
true_h1..h6 are the labels for those hours (NaN past the end of the record).

Run in WSL (env ~/quantum_env): python src/lstm/export_lstm_forecasts.py
"""

import os

import numpy as np
import pandas as pd
import torch

from train_lstm import FEATURES, MODEL_DIR, OUT_DIR, RainLSTM, build_table

PAST = 24
HORIZON = 6
SOURCES = [
    # (model file, normalisation years, forecast years, split label)
    ("rain_lstm_fwd2023.pt", [2023], [2024], "oof_2024"),
    ("rain_lstm.pt", [2023, 2024], [2025], "test_2025"),
    ("rain_lstm_final.pt", [2023, 2024, 2025], [2026], "verify_2026"),
]


def load_model(name: str) -> RainLSTM:
    model = RainLSTM(len(FEATURES), HORIZON)
    model.load_state_dict(torch.load(os.path.join(MODEL_DIR, name), map_location="cpu"))
    model.eval()
    return model


def padded_windows(x: np.ndarray, y: np.ndarray):
    """Windows for every issue time, including the last ones whose future labels are missing.

    Inputs are padded with HORIZON zero rows and labels with NaN, so window t uses only real
    rows (the padding is never inside an input window).
    """
    x_pad = np.vstack([x, np.zeros((HORIZON, x.shape[1]))]).astype(np.float32)
    y_pad = np.concatenate([y, np.full(HORIZON, np.nan)]).astype(np.float32)
    n = len(x)
    xs = np.stack([x_pad[t - PAST:t] for t in range(PAST, n + 1)])
    ys = np.stack([y_pad[t:t + HORIZON] for t in range(PAST, n + 1)])
    issue = np.arange(PAST - 1, n)  # last input hour of each window
    return xs, ys, issue


def main() -> None:
    df = build_table([2023, 2024, 2025, 2026])
    rows = []
    for model_file, norm_years, fc_years, fixed_split in SOURCES:
        train_df = df[df.index.year.isin(norm_years)]
        mean = train_df[FEATURES].mean()
        std = train_df[FEATURES].std().replace(0, 1.0)
        x_all = ((df[FEATURES] - mean) / std).values
        y_all = df["rain_att_db"].values
        xs, ys, issue = padded_windows(x_all, y_all)
        times = df.index[issue]
        # Skip windows with a missing input (POWER gaps); their outputs would be NaN.
        has_input = ~np.isnan(xs).any(axis=(1, 2))
        keep = np.isin(times.year, fc_years) & has_input

        model = load_model(model_file)
        with torch.no_grad():
            pred = model(torch.tensor(xs[keep])).numpy()

        out = pd.DataFrame({"issue_time_utc": times[keep]})
        out["model"] = model_file
        for h in range(HORIZON):
            out[f"pred_h{h + 1}"] = pred[:, h]
        for h in range(HORIZON):
            out[f"true_h{h + 1}"] = ys[keep][:, h]
        out["split"] = fixed_split
        rows.append(out)

    result = pd.concat(rows, ignore_index=True).sort_values("issue_time_utc")
    # 2026 rows exist only where ERA5 tclw exists; the base table drops the rest.
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "lstm_dqn_inputs.csv")
    result.to_csv(path, index=False, float_format="%.6f")
    print(f"Wrote {path} ({len(result)} issue times)")
    print(result.groupby("split").size())


if __name__ == "__main__":
    main()
