"""
Provisional comparison: does the DQN beat a *realistic* max-SINR baseline, not just the
free, instantaneous, all-link one?

max_sinr_policy reads env._sinr_db directly (every HAPS, every hour, for free) -- not
something a real UE could do. BoundedPollMaxSINR (train_dqn_real.py) gets a fresh reading
for only one HAPS per hour, round-robin, and must act on stale readings for the other two --
a crude but concrete model of a UE's actual measurement budget.

Loads whatever DQN checkpoint is already at data/processed/dqn_real/dqn_real.pt (no
retraining here -- this is a quick, no-training re-evaluation on the same held-out 2025
days). Run: python src/drl_dqn/eval_bounded_poll.py
"""

import os
import sys

import pandas as pd
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dqn_agent import DQNAgent  # noqa: E402
from real_episode_env import load_episodes  # noqa: E402
from train_dqn_real import (BoundedPollMaxSINR, OUT_DIR, SEED, dqn_policy,  # noqa: E402
                             evaluate_method, greedy_throughput_policy, max_sinr_policy,
                             random_policy)

MODEL_PATH = os.path.join(OUT_DIR, "dqn_real.pt")


def main():
    eval_eps = load_episodes("eval")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Need state_dim/n_actions to build the agent before loading weights; get them from a
    # throwaway env the same way train_dqn_real.py does.
    from real_episode_env import RealEpisodeEnv
    probe_env = RealEpisodeEnv(eval_eps, seed=SEED + 1)
    agent = DQNAgent(probe_env.state_dim, probe_env.n_actions, seed=SEED, device=device)
    agent.q.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    agent.eps = 0.0

    rows = []
    rows += evaluate_method(eval_eps, "dqn", dqn_policy, agent)
    rows += evaluate_method(eval_eps, "max_sinr (free, all-link)", lambda a: max_sinr_policy)
    rows += evaluate_method(eval_eps, "bounded_poll_sinr (1 link/hr)", lambda a: BoundedPollMaxSINR())
    rows += evaluate_method(eval_eps, "oracle max-throughput", lambda a: greedy_throughput_policy)
    rows += evaluate_method(eval_eps, "random", lambda a: random_policy)
    results = pd.DataFrame(rows)

    cols = ["reward_per_step", "jain", "outage", "soc"]
    summary = results.groupby("method")[cols].mean()
    print(summary.to_string(float_format=lambda x: f"{x:.3f}"))
    out_path = os.path.join(OUT_DIR, "bounded_poll_comparison.csv")
    summary.to_csv(out_path, float_format="%.4f")
    print(f"\nSaved: {out_path}")
    print("\n(Provisional, and now doubly stale: this loads data/processed/dqn_real/dqn_real.pt, "
          "a 400-episode checkpoint trained before this session's feeder-choice, UAV-feeder-rain, "
          "and contention-sharing fixes to haps_association_env.py -- it reflects none of them. "
          "run_ablations.py's 'lstm' variant is the properly-trained, up-to-date model but doesn't "
          "save its checkpoints. Do not cite this script's output; if bounded-poll numbers are ever "
          "needed for the paper, retrain one agent under the current env with torch.save enabled "
          "and rerun this script against that checkpoint.)")


if __name__ == "__main__":
    main()
