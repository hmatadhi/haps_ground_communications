"""
Forecast ablations for the DQN (five seeds, same training and evaluation days as run_multiseed.py).

Variants:
  lstm    : six LSTM forecasts issued at hour t-1 (the paper's model)
  none    : no forecast features (tests whether the LSTM adds anything)
  oracle  : true rain attenuation for hours t..t+5 (upper bound on any forecast)

Output: data/processed/dqn_ablation/ablation_results.csv (one row per variant, seed)
        and ablation_summary.csv (mean and standard deviation per variant)

Run in WSL (env ~/quantum_env): python src/drl_dqn/run_ablations.py
"""

import os
import sys

import numpy as np
import pandas as pd
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from dqn_agent import DQNAgent  # noqa: E402
from real_episode_env import RealEpisodeEnv, load_episodes  # noqa: E402
from train_dqn_real import MAX_STEPS, run_episode  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "processed", "dqn_ablation")
SEEDS = [0, 1, 2, 3, 4]
VARIANTS = ["lstm", "none", "oracle"]


def train_dqn(seed: int, train_eps, forecast: str, device: str) -> DQNAgent:
    np.random.seed(seed)
    torch.manual_seed(seed)
    env = RealEpisodeEnv(train_eps, seed=seed, forecast=forecast)
    agent = DQNAgent(env.state_dim, env.n_actions, seed=seed, device=device)
    for _ in range(len(train_eps)):
        s = env.reset()
        for _ in range(MAX_STEPS):
            actions = agent.act_batch(s)
            s2, r, done, _ = env.step(actions)
            for k in range(env.n_users):
                agent.remember(s[k], actions[k], r[k], s2[k], done)
            agent.train_step()
            s = s2
        agent.decay_eps()
    agent.eps = 0.0
    return agent


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    train_eps = load_episodes("train")
    eval_eps = load_episodes("eval")
    rows = []
    for variant in VARIANTS:
        for seed in SEEDS:
            agent = train_dqn(seed, train_eps, variant, device)
            np.random.seed(seed + 1000)  # same reseed as run_multiseed.evaluate, for matching results
            env = RealEpisodeEnv(eval_eps, seed=seed + 1000, forecast=variant)
            policy = lambda e, s: agent.act_batch(s)  # noqa: E731
            per_episode = [run_episode(env, policy) for _ in range(len(eval_eps))]
            df = pd.DataFrame(per_episode)
            rows.append({
                "variant": variant, "seed": seed,
                "reward_per_step": df["reward_per_step"].mean(),
                "jain": df["jain"].mean(),
                "outage": df["outage"].mean(),
                "soc": df["soc"].mean(),
            })
            print(rows[-1], flush=True)
    results = pd.DataFrame(rows)
    results.to_csv(os.path.join(OUT_DIR, "ablation_results.csv"), index=False, float_format="%.4f")
    summary = results.groupby("variant")[["reward_per_step", "jain", "outage", "soc"]].agg(["mean", "std"])
    summary.to_csv(os.path.join(OUT_DIR, "ablation_summary.csv"), float_format="%.4f")
    print(summary.round(3).to_string())


if __name__ == "__main__":
    main()
