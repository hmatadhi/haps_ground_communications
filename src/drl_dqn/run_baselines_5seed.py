"""
Five-seed evaluation of the closed-form baselines (random, max-SINR), matched to run_multiseed.py.

The DQN rows come from run_multiseed.py (one trained DQN per seed). The baselines have no
training, so they are evaluated on the same 50 days per seed, with the same environment seed
(seed + 1000) as the DQN evaluation, so every row in the paper uses the same five seeds.

Two evaluation sets:
  real     : 50 held-out 2025 days (load_episodes("eval"))
  prelstm  : 50 synthetic days, hourly rain attenuation drawn from the ITU-R P.837 statistics
             (make_prelstm_episodes, PRELSTM_SEED + seed so each seed draws its own days)

Output: data/processed/dqn_multiseed/baselines_5seed.csv
  one row per seed, evaluation set and policy, with reward_per_step, jain, outage, soc.

Run in WSL (env ~/quantum_env): python src/drl_dqn/run_baselines_5seed.py
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from real_episode_env import load_episodes  # noqa: E402
from run_multiseed import OUT_DIR, SEEDS, evaluate  # noqa: E402
from train_dqn_real import greedy_throughput_policy, max_sinr_policy, random_policy  # noqa: E402
from compare_baselines import make_prelstm_episodes, N_PRELSTM_DAYS, PRELSTM_SEED  # noqa: E402

BASELINES = [
    ("real", "random", lambda: random_policy),
    ("real", "max-SINR", lambda: max_sinr_policy),
    ("prelstm", "random", lambda: random_policy),
    ("prelstm", "max-SINR", lambda: max_sinr_policy),
    ("real", "greedy-throughput", lambda: greedy_throughput_policy),
    ("prelstm", "greedy-throughput", lambda: greedy_throughput_policy),
]


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    eval_real = load_episodes("eval")
    rows = []
    for seed in SEEDS:
        sets = {
            "real": eval_real,
            "prelstm": make_prelstm_episodes(N_PRELSTM_DAYS, PRELSTM_SEED + seed),
        }
        for set_name, policy_name, factory in BASELINES:
            for m in evaluate(sets[set_name], f"{policy_name} ({set_name})", seed, factory):
                m["eval_set"] = set_name
                m["base_policy"] = policy_name
                rows.append(m)

    df = pd.DataFrame(rows)
    per_seed = (df.groupby(["eval_set", "base_policy", "seed"])
                  [["reward_per_step", "jain", "outage", "soc"]].mean().reset_index())
    out = os.path.join(OUT_DIR, "baselines_5seed.csv")
    per_seed.to_csv(out, index=False, float_format="%.4f")
    print(per_seed.to_string(index=False))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
