"""
Stage 1: early-stopping selection for the rain-attenuation LSTM, done honestly.

Problem found: the paper's current model trains for a fixed 30 epochs. Training
loss keeps falling throughout, but test RMSE is best around epoch 10 and gets
worse after that (classic overfitting) -- so 30 epochs is already past the
best point.

Fix, done without peeking at the test set to choose the stopping point:
  train: 2023-2024
  validation: 2025 (used ONLY to pick the best epoch)
  test: 2026 (untouched until the final, chosen epoch is evaluated on it --
        this is the same year Table 2 already reports on)

Output: prints validation RMSE per epoch, the chosen epoch, and that epoch's
final test-set MAE/RMSE per horizon (to compare against the current Table 2).
Saves the chosen model to models/lstm/rain_lstm_earlystop.pt and per-horizon
test predictions to data/processed/lstm/lstm_earlystop_test_2026.csv.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from train_lstm import build_table, make_windows, RainLSTM, FEATURES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_DIR = os.path.join(ROOT, "models", "lstm")
OUT_DIR = os.path.join(ROOT, "data", "processed", "lstm")
PAST, HORIZON = 24, 6
MAX_EPOCHS = 100
CHECK_EVERY = 2

torch.manual_seed(0)
np.random.seed(0)

df = build_table([2023, 2024, 2025, 2026])
train_df = df[df.index.year.isin([2023, 2024])]
val_df = df[df.index.year == 2025]
test_df = df[df.index.year == 2026]

mean = train_df[FEATURES].mean()
std = train_df[FEATURES].std().replace(0, 1.0)


def to_windows(d):
    x = ((d[FEATURES] - mean) / std).values
    y = d["rain_att_db"].values
    xs, ys = make_windows(x, y, PAST, HORIZON)
    # Drop windows that touch any missing input/label (weather gaps), matching
    # export_lstm_forecasts.py's convention -- otherwise a handful of NaN rows
    # silently poison every aggregate metric computed over the full array.
    valid = ~np.isnan(xs).any(axis=(1, 2)) & ~np.isnan(ys).any(axis=1)
    return xs[valid], ys[valid]


xtr, ytr = to_windows(train_df)
xva, yva = to_windows(val_df)
xte, yte = to_windows(test_df)
print(f"train windows: {len(xtr)}  val windows: {len(xva)}  test windows: {len(xte)}")

model = RainLSTM(len(FEATURES), HORIZON)
opt = torch.optim.Adam(model.parameters(), lr=5e-4)
loss_fn = nn.HuberLoss(delta=1.0)
ds = torch.utils.data.TensorDataset(torch.tensor(xtr), torch.tensor(ytr))
loader = torch.utils.data.DataLoader(ds, batch_size=128, shuffle=True)

xva_t, xte_t = torch.tensor(xva), torch.tensor(xte)
best_val_rmse, best_epoch, best_state = np.inf, 0, None
history = []

for epoch in range(1, MAX_EPOCHS + 1):
    model.train()
    for xb, yb in loader:
        opt.zero_grad()
        loss = loss_fn(model(xb), yb)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        opt.step()
    if epoch % CHECK_EVERY == 0:
        model.eval()
        with torch.no_grad():
            pred_val = model(xva_t).numpy()
        val_rmse = np.sqrt(np.mean((pred_val - yva) ** 2))
        history.append((epoch, val_rmse))
        print(f"epoch {epoch:3d}  val_RMSE={val_rmse:.4f}")
        if val_rmse < best_val_rmse:
            best_val_rmse = val_rmse
            best_epoch = epoch
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

print(f"\nBest epoch by validation (2025): {best_epoch}  val_RMSE={best_val_rmse:.4f}")

model.load_state_dict(best_state)
model.eval()
with torch.no_grad():
    pred_test = model(xte_t).numpy()

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
torch.save(model.state_dict(), os.path.join(MODEL_DIR, "rain_lstm_earlystop.pt"))

out = pd.DataFrame(pred_test, columns=[f"pred_h{h+1}" for h in range(HORIZON)])
for h in range(HORIZON):
    out[f"true_h{h+1}"] = yte[:, h]
out.to_csv(os.path.join(OUT_DIR, "lstm_earlystop_test_2026.csv"), index=False)

print(f"\nFinal test (2026, {len(xte)} windows) at chosen epoch {best_epoch}:")
for h in range(HORIZON):
    err = pred_test[:, h] - yte[:, h]
    mae = np.mean(np.abs(err))
    rmse = np.sqrt(np.mean(err ** 2))
    print(f"  +{h+1}h  MAE={mae:.3f}  RMSE={rmse:.3f}")
