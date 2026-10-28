"""
Stage 2: horizon-weighted ensembling of the early-stopped LSTM (Stage 1) with
persistence. Weights are chosen per horizon on the 2025 validation set only
(never touching 2026 until the final evaluation), then applied once to the
2026 test set. Reports the exact window count used at every step.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import torch

from train_lstm import build_table, RainLSTM, FEATURES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_DIR = os.path.join(ROOT, "models", "lstm")
PAST, HORIZON = 24, 6


def make_windows_with_persist(x, y, past, horizon):
    xs, ys, persist = [], [], []
    for t in range(past, len(x) - horizon + 1):
        xs.append(x[t - past:t])
        ys.append(y[t:t + horizon])
        persist.append(y[t - 1])  # last known actual value before the window
    xs, ys, persist = np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32), np.asarray(persist, dtype=np.float32)
    valid = ~np.isnan(xs).any(axis=(1, 2)) & ~np.isnan(ys).any(axis=1) & ~np.isnan(persist)
    return xs[valid], ys[valid], persist[valid]


torch.manual_seed(0)
np.random.seed(0)

df = build_table([2023, 2024, 2025, 2026])
train_df = df[df.index.year.isin([2023, 2024])]
val_df = df[df.index.year == 2025]
test_df = df[df.index.year == 2026]

mean = train_df[FEATURES].mean()
std = train_df[FEATURES].std().replace(0, 1.0)


def prep(d):
    x = ((d[FEATURES] - mean) / std).values
    y = d["rain_att_db"].values
    return make_windows_with_persist(x, y, PAST, HORIZON)


xva, yva, persist_va = prep(val_df)
xte, yte, persist_te = prep(test_df)
print(f"validation windows (2025, all available): {len(xva)}")
print(f"test windows (2026, all available): {len(xte)}")

model = RainLSTM(len(FEATURES), HORIZON)
model.load_state_dict(torch.load(os.path.join(MODEL_DIR, "rain_lstm_earlystop.pt")))
model.eval()

with torch.no_grad():
    pred_va = model(torch.tensor(xva)).numpy()
    pred_te = model(torch.tensor(xte)).numpy()

# Persistence prediction for every horizon = the one "last known value" repeated.
persist_pred_va = np.repeat(persist_va[:, None], HORIZON, axis=1)
persist_pred_te = np.repeat(persist_te[:, None], HORIZON, axis=1)

weights = np.linspace(0.0, 1.0, 101)  # weight on LSTM; (1-w) on persistence
rows = []
for h in range(HORIZON):
    best_w, best_rmse = None, np.inf
    for w in weights:
        ens_va = w * pred_va[:, h] + (1 - w) * persist_pred_va[:, h]
        rmse = np.sqrt(np.mean((ens_va - yva[:, h]) ** 2))
        if rmse < best_rmse:
            best_rmse, best_w = rmse, w

    ens_te = best_w * pred_te[:, h] + (1 - best_w) * persist_pred_te[:, h]
    lstm_rmse = np.sqrt(np.mean((pred_te[:, h] - yte[:, h]) ** 2))
    persist_rmse = np.sqrt(np.mean((persist_pred_te[:, h] - yte[:, h]) ** 2))
    ens_rmse = np.sqrt(np.mean((ens_te - yte[:, h]) ** 2))
    lstm_mae = np.mean(np.abs(pred_te[:, h] - yte[:, h]))
    persist_mae = np.mean(np.abs(persist_pred_te[:, h] - yte[:, h]))
    ens_mae = np.mean(np.abs(ens_te - yte[:, h]))

    rows.append({"horizon": h + 1, "weight_on_lstm": round(best_w, 2),
                 "val_rmse_at_weight": round(best_rmse, 4),
                 "test_LSTM_MAE": round(lstm_mae, 3), "test_LSTM_RMSE": round(lstm_rmse, 3),
                 "test_Persist_MAE": round(persist_mae, 3), "test_Persist_RMSE": round(persist_rmse, 3),
                 "test_Ensemble_MAE": round(ens_mae, 3), "test_Ensemble_RMSE": round(ens_rmse, 3)})

out = pd.DataFrame(rows)
print(f"\n{out.to_string(index=False)}")
out.to_csv(os.path.join(ROOT, "data", "processed", "lstm", "ensemble_weighted_results.csv"), index=False)
