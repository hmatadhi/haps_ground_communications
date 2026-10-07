"""
Build 2026 evaluation episodes (split "eval2026") on the same days as the LSTM 2026 validation.

Forecasts: the LSTM forecasts issued at hour t-1 for hours t..t+5 (lstm_dqn_inputs.csv, split
verify_2026, which the LSTM never trained on). Truth: the observed attenuation for hour t, which is
the true_h1 value of the forecast issued at hour t-1 (the same file).

Days: 50 calendar days in 2026 with all 24 hours and all forecasts present, drawn at random with
the evaluation seed (999), the same rule as the 2025 evaluation days.

Output: data/processed/episodes/episodes_hourly_2026.csv

Run in WSL (env ~/quantum_env): python src/drl_dqn/build_eval2026.py
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "lstm"))

from train_lstm import build_table  # noqa: E402
from build_real_episodes import EP_HOURS, EVAL_SEED, LSTM_PATH, OUT_DIR, episode_rows  # noqa: E402

N_EVAL_EP = 50
HORIZONS = [f"lstm_pred_h{h}" for h in range(1, 7)]


def main() -> None:
    df = build_table([2026])
    if "time_utc" in df.columns:
        df = df.set_index("time_utc")
    df = df.sort_index()

    lstm = pd.read_csv(LSTM_PATH, parse_dates=["issue_time_utc"])
    lstm = lstm[lstm["split"] == "verify_2026"].set_index("issue_time_utc")
    prev = df.index - pd.Timedelta(hours=1)
    for h in range(1, 7):
        df[f"lstm_pred_h{h}"] = lstm[f"pred_h{h}"].reindex(prev).values
    df["rain_att_db"] = lstm["true_h1"].reindex(prev).values
    df["scint_att_db"] = 0.0  # not used by the DQN environment
    df = df.dropna(subset=HORIZONS + ["rain_att_db"])

    index = df.index
    starts = [
        t for t in index
        if t.hour == 0 and (t + pd.Timedelta(hours=EP_HOURS - 1)) in index
    ]
    rng = np.random.default_rng(EVAL_SEED)
    pick = sorted(rng.choice(len(starts), N_EVAL_EP, replace=False))
    chosen = [starts[i] for i in pick]
    print(f"2026 candidate days: {len(starts)}; chosen: {len(chosen)}")

    summaries, hourly = [], []
    for ep_id, start in enumerate(chosen):
        s, rows = episode_rows(df, start, "eval2026", ep_id)
        summaries.append(s)
        hourly.append(rows)
    hourly_df = pd.concat(hourly, ignore_index=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "episodes_hourly_2026.csv")
    hourly_df.to_csv(path, index=False, float_format="%.4f")
    print(f"Wrote {path} ({len(chosen)} days, {len(hourly_df)} hours)")


if __name__ == "__main__":
    main()
