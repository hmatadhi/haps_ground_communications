"""
Multi-seed DQN run with statistics.

For each seed: train the association DQN on the 400 real-data training episodes (one pass,
2024 rolling windows, LSTM forecast in the state), then evaluate the final policy greedily on
the 50 held-out 2025 days. The max-SINR and random baselines are evaluated on the same 50 days
for each seed, so paired differences can be reported.

Statistics across seeds (per metric): mean, standard deviation, median, min, max, and the 95 %
confidence interval of the mean (t distribution). Paired differences DQN - max-SINR are also
reported with the same interval.

Outputs (data/processed/dqn_multiseed/):
  seed_results.csv  one row per seed and policy
  stats.csv         statistics across seeds per policy and metric
  paired.csv        paired differences DQN minus max-SINR per seed and metric

Run in WSL (env ~/quantum_env): python src/drl_dqn/run_multiseed.py
"""

import os
import sys

import numpy as np
import pandas as pd
import torch
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dqn_agent import DQNAgent  # noqa: E402
from real_episode_env import RealEpisodeEnv, load_episodes  # noqa: E402
from train_dqn_real import MAX_STEPS, max_sinr_policy, random_policy, run_episode  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "processed", "dqn_multiseed")
SEEDS = [0, 1, 2, 3, 4]
METRICS = ["reward_per_step", "jain", "outage", "soc"]


def train_dqn(seed: int, train_eps, device: str) -> DQNAgent:
    np.random.seed(seed)
    torch.manual_seed(seed)
    env = RealEpisodeEnv(train_eps, seed=seed)
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


def evaluate(eval_eps, name: str, seed: int, policy_factory) -> list[dict]:
    env = RealEpisodeEnv(eval_eps, seed=seed + 1000)
    rows = []
    for _ in range(len(eval_eps)):
        m = run_episode(env, policy_factory())
        m.update({"seed": seed, "policy": name, "episode_id": env.episode_id, "regime": env.regime})
        rows.append(m)
    return rows


def ci95(x: np.ndarray):
    n = len(x)
    half = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n)
    return x.mean() - half, x.mean() + half


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    train_eps = load_episodes("train")
    eval_eps = load_episodes("eval")
    print(f"Train episodes: {len(train_eps)} | eval days: {len(eval_eps)} | seeds: {SEEDS} | {device}")

    rows = []
    for seed in SEEDS:
        agent = train_dqn(seed, train_eps, device)

        def dqn_policy(agent=agent):
            return lambda env, s: agent.act_batch(s)

        rows += evaluate(eval_eps, "DQN with LSTM", seed, dqn_policy)
        rows += evaluate(eval_eps, "max-SINR", seed, lambda: max_sinr_policy)
        rows += evaluate(eval_eps, "random", seed, lambda: random_policy)
        last = pd.DataFrame(rows)
        last = last[last["seed"] == seed]
        print(f"seed {seed}: DQN reward {last[(last.policy == 'DQN with LSTM')]['reward_per_step'].mean():.2f}, "
              f"max-SINR reward {last[(last.policy == 'max-SINR')]['reward_per_step'].mean():.2f}")

    results = pd.DataFrame(rows)
    per_seed = results.groupby(["policy", "seed"])[METRICS].mean().reset_index()
    per_seed.to_csv(os.path.join(OUT_DIR, "seed_results.csv"), index=False, float_format="%.4f")

    stat_rows = []
    for policy, grp in per_seed.groupby("policy"):
        for m in METRICS:
            x = grp[m].values
            lo, hi = ci95(x)
            stat_rows.append({"policy": policy, "metric": m, "n_seeds": len(x),
                              "mean": x.mean(), "std": x.std(ddof=1), "median": np.median(x),
                              "min": x.min(), "max": x.max(), "ci95_low": lo, "ci95_high": hi})
    stat_df = pd.DataFrame(stat_rows)
    stat_df.to_csv(os.path.join(OUT_DIR, "stats.csv"), index=False, float_format="%.4f")

    dqn = per_seed[per_seed.policy == "DQN with LSTM"].set_index("seed")
    mx = per_seed[per_seed.policy == "max-SINR"].set_index("seed")
    paired_rows = []
    for m in METRICS:
        d = (dqn[m] - mx[m]).values
        lo, hi = ci95(d)
        t_p = stats.ttest_1samp(d, 0.0).pvalue
        paired_rows.append({"metric": m, "mean_diff_dqn_minus_maxsinr": d.mean(),
                            "ci95_low": lo, "ci95_high": hi, "p_value_t_test": t_p,
                            "dqn_better_seeds": int(np.sum(d > 0)) if m in ("reward_per_step", "jain", "soc")
                            else int(np.sum(d < 0))})
    paired_df = pd.DataFrame(paired_rows)
    paired_df.to_csv(os.path.join(OUT_DIR, "paired.csv"), index=False, float_format="%.4f")

    print("\nStatistics across seeds:")
    print(stat_df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nPaired difference, DQN minus max-SINR:")
    print(paired_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
