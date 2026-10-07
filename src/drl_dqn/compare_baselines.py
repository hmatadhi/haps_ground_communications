"""
Compare five policies on the same held-out evaluation days:

  1. Phase 1 random           real 2025 days (observed weather), random association
  2. Phase 1 max-SINR         real 2025 days, best direct HAPS by SINR
  3. PreLSTM random           synthetic days, random association
  4. PreLSTM max-SINR         synthetic days, best direct HAPS by SINR
  5. DQN with LSTM            real 2025 days, trained DQN (dqn_real.pt), LSTM forecast in state

PreLSTM days: each hour's rain rate is drawn at random from the ITU-R P.837 rain-rate
statistics for the Delhi site (exceedance level drawn uniformly), converted to attenuation with
ITU-R P.618. Visibility is set to 10 km and hour of day runs 0-23. No observed data is used.
The random and max-SINR policies do not read the state, so PreLSTM affects them only through
the rain loss in the reward.

Metrics (per episode, then averaged): reward per step, Jain fairness of chosen SINR, outage
users at the final hour, and mean battery state of charge.

Output (data/processed/dqn_real/):
  comparison_episodes.csv  per-episode metrics for each policy
  comparison_summary.csv   mean and standard deviation per policy

Run in WSL (env ~/quantum_env): python src/drl_dqn/compare_baselines.py
"""

import os
import sys

import numpy as np
import pandas as pd
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "lstm"))
from dqn_agent import DQNAgent  # noqa: E402
from real_episode_env import RealEpisodeEnv, load_episodes  # noqa: E402
from train_dqn_real import (MAX_STEPS, OUT_DIR, SEED, max_sinr_policy,  # noqa: E402
                            random_policy, run_episode)
from plot_forecast_windows import prelstm_series  # noqa: E402

N_PRELSTM_DAYS = 50
PRELSTM_SEED = 999


def make_prelstm_episodes(n_days: int, seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    episodes = []
    for ep_id in range(n_days):
        att = prelstm_series(MAX_STEPS, rng)
        # Rain rates are recovered from the same draws for the state: derive from attenuation
        # is not invertible, so the rain state is the attenuation-consistent rate via P.838 is
        # avoided; the state uses zero rain and 10 km visibility, and the reward uses att.
        episodes.append({
            "episode_id": ep_id,
            "regime": "prelstm",
            "rain_mm_h": np.zeros(MAX_STEPS),
            "vis_km": np.full(MAX_STEPS, 10.0),
            "hour": np.arange(MAX_STEPS, dtype=float),
            "rain_att_db": att,
            # Persistence surrogate for the six forecast horizons (PreLSTM days have no
            # forecast; the baselines do not read the forecast features).
            "lstm_db": np.repeat(att[:, None], 6, axis=1),
        })
    return episodes


def evaluate(eps, name, policy_factory, agent=None):
    env = RealEpisodeEnv(eps, seed=SEED + 1)
    rows = []
    for _ in range(len(eps)):
        policy = policy_factory(agent)
        m = run_episode(env, policy)
        m.update({"policy": name, "episode_id": env.episode_id, "regime": env.regime})
        rows.append(m)
    return rows


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    real_eval = load_episodes("eval")
    prelstm_eval = make_prelstm_episodes(N_PRELSTM_DAYS, PRELSTM_SEED)

    env_probe = RealEpisodeEnv(real_eval, seed=SEED)
    agent = DQNAgent(env_probe.state_dim, env_probe.n_actions, seed=SEED, device="cpu")
    agent.q.load_state_dict(torch.load(os.path.join(OUT_DIR, "dqn_real.pt"), map_location="cpu"))
    agent.eps = 0.0

    rows = []
    rows += evaluate(real_eval, "1 Phase1 random (real)", lambda a: random_policy)
    rows += evaluate(real_eval, "2 Phase1 max-SINR (real)", lambda a: max_sinr_policy)
    rows += evaluate(prelstm_eval, "3 PreLSTM random", lambda a: random_policy)
    rows += evaluate(prelstm_eval, "4 PreLSTM max-SINR", lambda a: max_sinr_policy)
    rows += evaluate(real_eval, "5 DQN with LSTM (real)", lambda a: (lambda env, s: a.act_batch(s)), agent)

    results = pd.DataFrame(rows)
    results.to_csv(os.path.join(OUT_DIR, "comparison_episodes.csv"), index=False, float_format="%.4f")

    cols = ["reward_per_step", "jain", "outage", "soc"]
    summary = results.groupby("policy")[cols].agg(["mean", "std"])
    summary.columns = [f"{c}_{s}" for c, s in summary.columns]
    summary = summary.reset_index()
    summary.to_csv(os.path.join(OUT_DIR, "comparison_summary.csv"), index=False, float_format="%.4f")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
