"""
Forward (out-of-sample) LSTM forecasts for 2024.

Trains a model on 2023 only, then forecasts every 2024 issue time from causal input windows.
2024 is therefore out of sample for this model, so the DQN can train on 2024 episodes with
forecasts that match what it would see at deployment.

2025 and 2026 forecasts come from the 2023-2024 model (models/lstm/rain_lstm.pt), which is
also out of sample for those years.

Outputs:
  models/lstm/rain_lstm_fwd2023.pt
  data/processed/lstm/lstm_forward_2024.csv  (issue_time_utc, pred_h1..pred_h6, true_h1..true_h6)

Run in WSL (env ~/quantum_env): python src/lstm/train_forward_lstm.py
"""

import os

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from train_lstm import (
    FEATURES,
    MODEL_DIR,
    OUT_DIR,
    RainLSTM,
    build_table,
    make_windows,
)

TRAIN_YEAR = 2023
FORECAST_YEAR = 2024
PAST = 24
HORIZON = 6
EPOCHS = 30
BATCH = 128
SEED = 0


def main() -> None:
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    df = build_table([TRAIN_YEAR, FORECAST_YEAR])

    train_df = df[df.index.year == TRAIN_YEAR]
    mean = train_df[FEATURES].mean()
    std = train_df[FEATURES].std().replace(0, 1.0)
    x_all = ((df[FEATURES] - mean) / std).values
    y_all = df["rain_att_db"].values

    x_tr, y_tr = make_windows(x_all[: len(train_df)], y_all[: len(train_df)], PAST, HORIZON)
    model = RainLSTM(len(FEATURES), HORIZON)
    opt = torch.optim.Adam(model.parameters(), lr=5e-4)
    loss_fn = nn.HuberLoss(delta=1.0)
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(torch.tensor(x_tr), torch.tensor(y_tr)),
        batch_size=BATCH, shuffle=True,
    )
    for epoch in range(EPOCHS):
        model.train()
        for xb, yb in loader:
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            opt.step()
        if (epoch + 1) % 10 == 0:
            print(f"epoch {epoch + 1}: last batch loss {loss.item():.4f}")

    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(MODEL_DIR, "rain_lstm_fwd2023.pt"))
    print(f"Saved rain_lstm_fwd2023.pt (2024 forecasts are written by export_lstm_forecasts.py)")


if __name__ == "__main__":
    main()
