"""
Reward-term decomposition, 5 seeds, matched to run_multiseed.py / run_baselines_5seed.py.

Additive sanity-check script: does NOT modify or overwrite the existing
data/processed/dqn_multiseed/*.csv outputs. It retrains the DQN with the same
seeds (0..4) and evaluates on the same 50 held-out 2025 days used for
Table tab:dqn-all-policies, so reward_per_step/jain/outage/soc here should
match stats.csv / baselines_5seed.csv within training noise -- that agreement
is the sanity check. The new output adds the per-term reward decomposition
(throughput / severe / degraded / fairness / energy / low-battery) that those
files don't carry, so a reviewer-facing table can show *why* max-throughput's
higher raw throughput still loses on total reward.

Output: data/processed/dqn_multiseed/reward_decomposition.csv
  one row per policy, mean over 5 seeds (50 eval days each) of:
  reward_per_step, jain, outage, soc, term_throughput, term_severe,
  term_degraded, term_fairness, term_energy, term_low_battery,
  frac_severe, frac_degraded

Run: python src/drl_dqn/run_reward_decomposition.py
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from real_episode_env import load_episodes  # noqa: E402
from run_multiseed import OUT_DIR, SEEDS, train_dqn, evaluate  # noqa: E402
from train_dqn_real import greedy_throughput_policy, max_sinr_policy, random_policy  # noqa: E402

DECOMP_COLS = ["reward_per_step", "jain", "outage", "soc",
               "term_throughput", "term_severe", "term_degraded",
               "term_fairness", "term_energy", "term_low_battery",
               "frac_severe", "frac_degraded"]


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    train_eps = load_episodes("train")
    eval_eps = load_episodes("eval")
    print(f"Train episodes: {len(train_eps)} | eval days: {len(eval_eps)} | seeds: {SEEDS}")

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device}")

    rows = []
    for seed in SEEDS:
        agent = train_dqn(seed, train_eps, device=device)

        def dqn_policy(agent=agent):
            return lambda env, s: agent.act_batch(s)

        rows += evaluate(eval_eps, "LSTM + DQN", seed, dqn_policy)
        rows += evaluate(eval_eps, "Max-SINR", seed, lambda: max_sinr_policy)
        rows += evaluate(eval_eps, "Max-throughput", seed, lambda: greedy_throughput_policy)
        rows += evaluate(eval_eps, "Random", seed, lambda: random_policy)
        print(f"seed {seed} done")

    df = pd.DataFrame(rows)
    present_cols = [c for c in DECOMP_COLS if c in df.columns]
    per_seed = df.groupby(["policy", "seed"])[present_cols].mean().reset_index()
    summary = per_seed.groupby("policy")[present_cols].agg(["mean", "std"])

    out = os.path.join(OUT_DIR, "reward_decomposition.csv")
    per_seed.to_csv(out, index=False, float_format="%.4f")
    print(f"\nWrote {out}")
    print("\nPer-seed decomposition:")
    print(per_seed.to_string(index=False))
    print("\nSummary (mean over 5 seeds):")
    print(summary.to_string(float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
