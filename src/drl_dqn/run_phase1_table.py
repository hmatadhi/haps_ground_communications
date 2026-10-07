"""
Phase-1 association table (Table V): random, max-SINR (direct only) and max-throughput
(all six options), on the same held-out environment as eval_baseline_association.py
(EVAL_SEED = 999, 50 episodes).

Output: data/processed/phase1_table/phase1_table.csv

Run in WSL (env ~/quantum_env): python src/drl_dqn/run_phase1_table.py
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from eval_baseline_association import make_env, run_policy  # noqa: E402
from haps_association_env import CAPACITY_BPS_HZ_MAX, SINR_DB_MAX, SINR_DB_MIN  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "processed", "phase1_table")


def random_policy(state, env):
    return env.rng.integers(0, env.n_actions, size=env.n_users)


def max_sinr_direct(state, env):
    # Direct links only: the user is connected to the one HAPS with the highest SINR.
    sinr_db = state[:, 0:3] * (SINR_DB_MAX - SINR_DB_MIN) + SINR_DB_MIN
    return np.argmax(sinr_db, axis=1)


def max_throughput_all(state, env):
    # All six options: direct links (log2(1+SINR)) and UAV relays (capacity from the state).
    sinr_db = state[:, 0:3] * (SINR_DB_MAX - SINR_DB_MIN) + SINR_DB_MIN
    direct = np.log2(1.0 + 10.0 ** (sinr_db / 10.0))
    uav = state[:, 12:15] * CAPACITY_BPS_HZ_MAX
    return np.argmax(np.concatenate([direct, uav], axis=1), axis=1)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    for name, policy in [("Random", random_policy),
                         ("Max-SINR (direct only)", max_sinr_direct),
                         ("Max-throughput (all six)", max_throughput_all)]:
        r = run_policy(policy)
        rows.append({
            "policy": name,
            "reward_mean": r["reward_mean"], "reward_std": r["reward_std"],
            "jain_mean": r["jain_mean"], "jain_std": r["jain_std"],
            "outage_mean": r["outage_mean"], "outage_std": r["outage_std"],
        })
        print(rows[-1], flush=True)
    df = pd.DataFrame(rows)
    path = os.path.join(OUT_DIR, "phase1_table.csv")
    df.to_csv(path, index=False, float_format="%.4f")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
