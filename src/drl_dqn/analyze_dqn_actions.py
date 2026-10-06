"""
Action distribution of the trained real-episode DQN on the held-out 2025 days, versus
max-SINR. Shows which association options the policy uses, to check whether the reward gain
comes from a few options rather than a balanced allocation.

Actions: 0-2 direct HAPS, 3-5 relay via Gateway, 6-8 relay via UAV.

Output: data/processed/dqn_real/action_distribution.csv

Run in WSL (env ~/quantum_env): python src/drl_dqn/analyze_dqn_actions.py
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
from train_dqn_real import MAX_STEPS, OUT_DIR, SEED, max_sinr_policy  # noqa: E402

ACTION_NAMES = ["direct_HAPS0", "direct_HAPS1", "direct_HAPS2",
                "gw_relay_HAPS0", "gw_relay_HAPS1", "gw_relay_HAPS2",
                "uav_relay_HAPS0", "uav_relay_HAPS1", "uav_relay_HAPS2"]


def collect(policy_name, policy, eval_eps, env_seed):
    env = RealEpisodeEnv(eval_eps, seed=env_seed)
    counts = np.zeros(env.n_actions)
    for _ in range(len(eval_eps)):
        s = env.reset()
        for _ in range(MAX_STEPS):
            a = policy(env, s)
            counts += np.bincount(a, minlength=env.n_actions)
            s, _, _, _ = env.step(a)
    frac = counts / counts.sum()
    return pd.Series(frac, index=ACTION_NAMES, name=policy_name)


def main() -> None:
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    eval_eps = load_episodes("eval")
    env = RealEpisodeEnv(eval_eps, seed=SEED)
    agent = DQNAgent(env.state_dim, env.n_actions, seed=SEED, device="cpu")
    agent.q.load_state_dict(torch.load(os.path.join(OUT_DIR, "dqn_real.pt"), map_location="cpu"))
    agent.eps = 0.0

    def dqn_policy(e, s):
        return agent.act_batch(s)

    table = pd.concat([
        collect("dqn", dqn_policy, eval_eps, SEED + 1),
        collect("max_sinr", max_sinr_policy, eval_eps, SEED + 1),
    ], axis=1)
    table.to_csv(os.path.join(OUT_DIR, "action_distribution.csv"), float_format="%.4f")
    print("Fraction of user-hour decisions per action:")
    print(table.to_string(float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
