"""
Quick check: does a per-user switching-cost penalty make the LSTM rain forecast valuable?

Hypothesis under test (user's, discussed in session): today's MDP lets every user react to
the CURRENT hour's rain for free, every hour -- so a forecast of FUTURE rain has nothing to
add. Adding a cost for changing action vs. last hour should make anticipating (what the
forecast enables) worth more than reacting late. But with only one UAV, there may not be a
genuine "penalty-free alternative" to switch to -- that might only appear once there are
multiple UAVs to choose among (future work). This script tests `lstm` vs `none` under a
non-zero switch_cost, fewer seeds than run_ablations.py for a fast, directional read.

Output: data/processed/dqn_ablation/switchcost_check.csv
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
SEEDS = [0, 1, 2]
VARIANTS = ["lstm", "none"]
N_TRAIN_EPISODES = 2400
SWITCH_COST = 2.0  # comparable in magnitude to a typical throughput difference between options


def train_dqn(seed: int, train_eps, forecast: str, device: str) -> DQNAgent:
    np.random.seed(seed)
    torch.manual_seed(seed)
    env = RealEpisodeEnv(train_eps, seed=seed, forecast=forecast, switch_cost=SWITCH_COST)
    agent = DQNAgent(env.state_dim, env.n_actions, seed=seed, device=device)
    for _ in range(N_TRAIN_EPISODES):
        s = env.reset()
        for _ in range(MAX_STEPS):
            actions = agent.act_batch(s)
            feeder_ctx = s.mean(axis=0)
            feeder_raw = agent.act(feeder_ctx)
            feeder_choice = feeder_raw % env.n_haps
            s2, r, done, _ = env.step(actions, feeder_choice=feeder_choice)
            feeder_ctx2 = s2.mean(axis=0)
            for k in range(env.n_users):
                agent.remember(s[k], actions[k], r[k], s2[k], done)
            agent.remember(feeder_ctx, feeder_raw, float(r.mean()), feeder_ctx2, done)
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
            np.random.seed(seed + 1000)
            env = RealEpisodeEnv(eval_eps, seed=seed + 1000, forecast=variant, switch_cost=SWITCH_COST)
            policy = lambda e, s: agent.act_batch(s)  # noqa: E731
            per_episode = [run_episode(env, policy, agent=agent) for _ in range(len(eval_eps))]
            df = pd.DataFrame(per_episode)
            row = {
                "variant": variant, "seed": seed,
                "reward_per_step": df["reward_per_step"].mean(),
                "jain": df["jain"].mean(),
                "outage": df["outage"].mean(),
                "soc": df["soc"].mean(),
            }
            if "frac_switched" in df.columns:
                row["frac_switched"] = df["frac_switched"].mean()
            rows.append(row)
            print(row, flush=True)
    results = pd.DataFrame(rows)
    out = os.path.join(OUT_DIR, "switchcost_check.csv")
    results.to_csv(out, index=False, float_format="%.4f")
    summary = results.groupby("variant")[["reward_per_step", "jain", "outage", "soc"]].agg(["mean", "std"])
    print(summary.round(3).to_string())
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
