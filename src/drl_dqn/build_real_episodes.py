"""
Build real-data DQN episodes from the hourly Delhi table (2023-2025).

One episode = 24 consecutive hourly steps, matching the paper's MDP (one step = one hour,
one episode = one day).

Training episodes: rolling 24-hour windows that start in 2023-2024. Starts are sampled
without replacement, so each episode is a distinct start hour. Windows overlap, which the
paper's write-up must state.

Evaluation episodes: calendar days in 2025 (out of sample for the LSTM), sampled without
replacement with the paper's evaluation seed (999).

Per hour, the episode carries:
  rain_mm_h, vis_km, hour_of_day (DQN state), temperature, humidity, cloud amount,
  cloud liquid water (ERA5), the LSTM 1-hour-ahead rain attenuation forecast, and the
  itur labels (rain attenuation, gas, scintillation).

Regime tags (per episode):
  rain   - max hourly precipitation >= RAIN_MM_H
  cloudy - mean cloud amount >= CLOUDY_PCT and no rain
  clear  - mean cloud amount <= CLEAR_PCT and no rain
  mixed  - anything else

Outputs (data/processed/episodes/):
  episodes_hourly.csv  - one row per episode-hour
  episodes_index.csv   - one row per episode with its regime and summary stats

Run in WSL (env ~/quantum_env): python src/drl_dqn/build_real_episodes.py
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lstm"))
from train_lstm import build_table  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ITUR_PATH = os.path.join(ROOT, "data", "processed", "itur", "itur_hourly_properties.csv")
LSTM_PATH = os.path.join(ROOT, "data", "processed", "lstm", "lstm_dqn_inputs.csv")
OUT_DIR = os.path.join(ROOT, "data", "processed", "episodes")

DATA_YEARS = [2023, 2024, 2025]
# Training uses 2024 only: its LSTM forecasts come from the 2023-only forward model (out of
# sample). 2023 has no out-of-sample forecasts, so it is not used for episodes.
TRAIN_YEARS = [2024]
EVAL_YEAR = 2025
EP_HOURS = 24
N_TRAIN_EP = 400      # rolling 2024 training episodes (multi-seed run)
N_EVAL_EP = 50        # paper's held-out episode count
TRAIN_SEED = 0
EVAL_SEED = 999
RAIN_MM_H = 1.0
CLOUDY_PCT = 70.0
CLEAR_PCT = 30.0


def load_hourly() -> pd.DataFrame:
    df = build_table(DATA_YEARS)
    itur = pd.read_csv(ITUR_PATH, parse_dates=["time_utc"], index_col="time_utc")
    df = df.join(itur[["gas_att_db", "scint_att_db"]], how="left")
    # The LSTM's pred_h1 issued at hour t-1 is its forecast for hour t.
    lstm = pd.read_csv(LSTM_PATH, parse_dates=["issue_time_utc"]).set_index("issue_time_utc")
    # All six horizons issued at hour t-1 (forecasts for hours t .. t+5). Issued before hour t,
    # so the agent at hour t sees no rain of hour t.
    horizons = [f"lstm_pred_h{h}" for h in range(1, 7)]
    for h in range(1, 7):
        df[f"lstm_pred_h{h}"] = lstm[f"pred_h{h}"].reindex(df.index - pd.Timedelta(hours=1)).values
    # The first 24 hours of 2023 have no LSTM forecast, so they are dropped.
    return df.dropna(subset=horizons)


def is_consecutive(index: pd.DatetimeIndex, start: pd.Timestamp) -> bool:
    """True if the 24 hours from start are all present. The hourly index is continuous
    after the leading rows are dropped, so checking the last hour is enough."""
    end = start + pd.Timedelta(hours=EP_HOURS - 1)
    return end in index


def regime_of(ep: pd.DataFrame) -> str:
    if ep["precip_mmh"].max() >= RAIN_MM_H:
        return "rain"
    cloud = ep["cloud_amt_pct"].mean()
    if cloud >= CLOUDY_PCT:
        return "cloudy"
    if cloud <= CLEAR_PCT:
        return "clear"
    return "mixed"


def episode_rows(df: pd.DataFrame, start: pd.Timestamp, split: str, ep_id: int) -> tuple[dict, pd.DataFrame]:
    ep = df.loc[start: start + pd.Timedelta(hours=EP_HOURS - 1)].copy()
    regime = regime_of(ep)
    ep.insert(0, "episode_id", ep_id)
    ep.insert(1, "split", split)
    ep.insert(2, "regime", regime)
    summary = {
        "episode_id": ep_id,
        "split": split,
        "start_utc": start,
        "regime": regime,
        "max_precip_mmh": ep["precip_mmh"].max(),
        "mean_cloud_pct": ep["cloud_amt_pct"].mean(),
        "mean_vis_km": ep["vis_km"].mean(),
        "rain_hours": int((ep["precip_mmh"] >= RAIN_MM_H).sum()),
        "mean_rain_att_db": ep["rain_att_db"].mean(),
        "max_rain_att_db": ep["rain_att_db"].max(),
        "mean_scint_att_db": ep["scint_att_db"].mean(),
    }
    return summary, ep.reset_index()


def main() -> None:
    df = load_hourly()
    index = df.index
    rng_train = np.random.default_rng(TRAIN_SEED)
    rng_eval = np.random.default_rng(EVAL_SEED)

    # Training candidates: any start hour where the 24-hour window lies in training years.
    train_starts = [
        t for t in index
        if t.year in TRAIN_YEARS and is_consecutive(index, t)
        and (t + pd.Timedelta(hours=EP_HOURS - 1)).year in TRAIN_YEARS
    ]
    # Evaluation candidates: calendar days in 2025 with all 24 hours present.
    eval_starts = [
        t for t in index
        if t.year == EVAL_YEAR and t.hour == 0 and is_consecutive(index, t)
    ]
    if len(train_starts) < N_TRAIN_EP or len(eval_starts) < N_EVAL_EP:
        raise RuntimeError(f"Not enough candidates: train {len(train_starts)}, eval {len(eval_starts)}")

    train_pick = sorted(rng_train.choice(len(train_starts), N_TRAIN_EP, replace=False))
    eval_pick = sorted(rng_eval.choice(len(eval_starts), N_EVAL_EP, replace=False))
    chosen = [("train", train_starts[i]) for i in train_pick] + [("eval", eval_starts[i]) for i in eval_pick]

    summaries, hourly = [], []
    for ep_id, (split, start) in enumerate(chosen):
        s, rows = episode_rows(df, start, split, ep_id)
        summaries.append(s)
        hourly.append(rows)

    os.makedirs(OUT_DIR, exist_ok=True)
    index_df = pd.DataFrame(summaries)
    hourly_df = pd.concat(hourly, ignore_index=True)
    index_df.to_csv(os.path.join(OUT_DIR, "episodes_index.csv"), index=False, float_format="%.4f")
    hourly_df.to_csv(os.path.join(OUT_DIR, "episodes_hourly.csv"), index=False, float_format="%.4f")

    print(f"Candidates: train {len(train_starts)} windows, eval {len(eval_starts)} days")
    print(f"Wrote {len(index_df)} episodes ({len(hourly_df)} hourly rows) to {OUT_DIR}")
    print("\nRegime counts by split:")
    print(index_df.groupby(["split", "regime"]).size().unstack(fill_value=0).to_string())
    print("\nPer-split means:")
    print(index_df.groupby("split")[["max_precip_mmh", "mean_cloud_pct", "mean_vis_km",
                                     "rain_hours", "mean_rain_att_db", "mean_scint_att_db"]]
          .mean().round(3).to_string())


if __name__ == "__main__":
    main()
