"""
Train the association DQN on 300 real-data episodes and compare with baselines.

Training: 300 rolling 24-hour episodes from 2024 (out-of-sample LSTM forecasts from the
2023-only forward model). Each episode is used once, in order.
Evaluation: 50 calendar days from 2025 (LSTM test forecasts), greedy policy, no training.
Baselines on the same 50 days: random action, and max-SINR (best direct HAPS).

Metrics follow the paper's convention: reward per step averaged over users and hours, and
Jain fairness, outage count, and battery SoC at the final hour.

Outputs (data/processed/dqn_real/):
  train_log.csv     eval metrics every EVAL_EVERY training episodes
  eval_episodes.csv per-episode metrics for DQN, random, max-SINR, with regime tags
  summary.csv       means per method, overall and per regime
  dqn_real.pt       trained Q-network

Run in WSL (env ~/quantum_env, torch available): python src/drl_dqn/train_dqn_real.py
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

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "processed", "dqn_real")

SEED = 42
N_USERS = 50
EPISODES = 300
EVAL_EVERY = 10
MAX_STEPS = 24


def run_episode(env, policy, agent=None):
    """Run one episode with policy(env, states) -> actions. Returns per-episode metrics."""
    s = env.reset()
    rewards, info = [], {}
    for _ in range(MAX_STEPS):
        actions = policy(env, s)
        s, r, done, info = env.step(actions)
        rewards.append(r.mean())
    return {
        "reward_per_step": float(np.mean(rewards)),
        "jain": float(info["jain_index"]),
        "outage": int(info["n_outage"]),
        "soc": float(np.mean(info["battery_soc"])),
    }


def dqn_policy(agent):
    def policy(env, s):
        return agent.act_batch(s)
    return policy


def random_policy(env, s):
    return np.random.randint(0, env.n_actions, size=env.n_users)


def max_sinr_policy(env, s):
    # Best direct HAPS by SINR (actions 0..n_haps-1); the paper's closed-form baseline.
    return np.argmax(env._sinr_db, axis=1)


def evaluate_method(eval_eps, policy_name, make_policy, agent=None):
    env = RealEpisodeEnv(eval_eps, seed=SEED + 1)
    rows = []
    for _ in range(len(eval_eps)):
        policy = make_policy(agent)
        m = run_episode(env, policy)
        m.update({"method": policy_name, "episode_id": env.episode_id, "regime": env.regime})
        rows.append(m)
    return rows


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    train_eps = load_episodes("train")
    eval_eps = load_episodes("eval")
    print(f"Train episodes: {len(train_eps)} | eval episodes: {len(eval_eps)} | device: {device}")

    env = RealEpisodeEnv(train_eps, seed=SEED)
    agent = DQNAgent(env.state_dim, env.n_actions, seed=SEED, device=device)
    print(f"State dim: {env.state_dim} | n_actions: {env.n_actions} | n_users: {N_USERS}")

    log = []
    for ep in range(EPISODES):
        s = env.reset()
        for _ in range(MAX_STEPS):
            actions = agent.act_batch(s)
            s2, r, done, _ = env.step(actions)
            for k in range(env.n_users):
                agent.remember(s[k], actions[k], r[k], s2[k], done)
            agent.train_step()
            s = s2
        agent.decay_eps()

        if (ep + 1) % EVAL_EVERY == 0:
            saved_eps, agent.eps = agent.eps, 0.0
            rows = evaluate_method(eval_eps, "dqn", dqn_policy, agent)
            agent.eps = saved_eps
            df = pd.DataFrame(rows)
            log.append({"episode": ep + 1, "eval_reward": df["reward_per_step"].mean(),
                        "jain": df["jain"].mean(), "outage": df["outage"].mean(),
                        "soc": df["soc"].mean()})
            print(f"ep {ep + 1:3d} | eval reward {log[-1]['eval_reward']:8.2f} | "
                  f"jain {log[-1]['jain']:.3f} | outage {log[-1]['outage']:4.1f}/{N_USERS} | "
                  f"soc {log[-1]['soc']:5.1f}% | eps {agent.eps:.3f}")

    torch.save(agent.q.state_dict(), os.path.join(OUT_DIR, "dqn_real.pt"))
    pd.DataFrame(log).to_csv(os.path.join(OUT_DIR, "train_log.csv"), index=False, float_format="%.4f")

    # Final comparison on the same 50 held-out days.
    saved_eps, agent.eps = agent.eps, 0.0
    all_rows = []
    all_rows += evaluate_method(eval_eps, "dqn", dqn_policy, agent)
    agent.eps = saved_eps
    all_rows += evaluate_method(eval_eps, "max_sinr", lambda a: max_sinr_policy)
    all_rows += evaluate_method(eval_eps, "random", lambda a: random_policy)
    results = pd.DataFrame(all_rows)
    results.to_csv(os.path.join(OUT_DIR, "eval_episodes.csv"), index=False, float_format="%.4f")

    cols = ["reward_per_step", "jain", "outage", "soc"]
    overall = results.groupby("method")[cols].mean()
    overall.insert(0, "regime", "all")
    per_regime = results.groupby(["method", "regime"])[cols].mean().reset_index()
    summary = pd.concat([overall.reset_index(), per_regime], ignore_index=True)
    summary.to_csv(os.path.join(OUT_DIR, "summary.csv"), index=False, float_format="%.4f")
    print("\nFinal comparison on held-out 2025 days:")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
