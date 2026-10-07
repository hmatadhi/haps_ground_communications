"""
Evaluate the LSTM + DQN and the three comparison policies on the 2026 validation days.

The DQN is trained exactly as in run_multiseed.py (five seeds, 400 episodes from 2024) and is
never trained on 2026. The 2026 days are the same days on which the LSTM was validated
(episodes_hourly_2026.csv, built by build_eval2026.py).

Output: data/processed/dqn_eval2026/eval2026_results.csv (one row per seed and policy)

Run in WSL (env ~/quantum_env): python src/drl_dqn/run_eval2026.py
"""

import os
import sys

import numpy as np
import pandas as pd
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from real_episode_env import load_episodes  # noqa: E402
from run_multiseed import SEEDS, evaluate, train_dqn  # noqa: E402
from train_dqn_real import greedy_throughput_policy, max_sinr_policy, random_policy  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
EP_2026 = os.path.join(ROOT, "data", "processed", "episodes", "episodes_hourly_2026.csv")
OUT_DIR = os.path.join(ROOT, "data", "processed", "dqn_eval2026")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    train_eps = load_episodes("train")
    eval_eps = load_episodes("eval2026", path=EP_2026)
    print(f"train episodes: {len(train_eps)} | 2026 evaluation days: {len(eval_eps)}", flush=True)

    rows = []
    for seed in SEEDS:
        agent = train_dqn(seed, train_eps, device)
        np.random.seed(seed + 1000)  # same reseed as run_multiseed.evaluate
        rows += evaluate(eval_eps, "DQN with LSTM", seed, lambda: (lambda e, s: agent.act_batch(s)))
        for name, factory in [("random", lambda: random_policy),
                              ("max-SINR", lambda: max_sinr_policy),
                              ("greedy-throughput", lambda: greedy_throughput_policy)]:
            rows += evaluate(eval_eps, name, seed, factory)
        print(f"seed {seed} done", flush=True)

    df = pd.DataFrame(rows)
    per_seed = df.groupby(["policy", "seed"])[["reward_per_step", "jain", "outage", "soc"]].mean().reset_index()
    path = os.path.join(OUT_DIR, "eval2026_results.csv")
    per_seed.to_csv(path, index=False, float_format="%.4f")
    summary = per_seed.groupby("policy")[["reward_per_step", "jain", "outage", "soc"]].agg(["mean", "std"])
    print(summary.round(3).to_string())
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
