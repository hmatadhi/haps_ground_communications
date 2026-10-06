"""
Final rain-attenuation LSTM, trained on 2023-2025 only (no 2026 data).

Used to validate forecasts for 2026, which is out of sample for this model. Normalisation
statistics come from 2023-2025 only.

Output: models/lstm/rain_lstm_final.pt

Run in WSL (env ~/quantum_env): python src/lstm/train_final_lstm.py
"""

import os

import numpy as np
import torch
import torch.nn as nn

from train_lstm import FEATURES, MODEL_DIR, RainLSTM, build_table, make_windows

TRAIN_YEARS = [2023, 2024, 2025]
PAST = 24
HORIZON = 6
EPOCHS = 30
BATCH = 128
SEED = 0


def main() -> None:
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    df = build_table(TRAIN_YEARS)
    mean = df[FEATURES].mean()
    std = df[FEATURES].std().replace(0, 1.0)
    x = ((df[FEATURES] - mean) / std).values
    y = df["rain_att_db"].values
    xs, ys = make_windows(x, y, PAST, HORIZON)

    model = RainLSTM(len(FEATURES), HORIZON)
    opt = torch.optim.Adam(model.parameters(), lr=5e-4)
    loss_fn = nn.HuberLoss(delta=1.0)
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(torch.tensor(xs), torch.tensor(ys)),
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
    path = os.path.join(MODEL_DIR, "rain_lstm_final.pt")
    torch.save(model.state_dict(), path)
    print(f"Saved {path} (trained on {TRAIN_YEARS}, {len(xs)} windows)")


if __name__ == "__main__":
    main()
