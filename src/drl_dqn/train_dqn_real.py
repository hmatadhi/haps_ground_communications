"""
Train the association DQN on 400 real-data episodes and compare with baselines.

Training: 400 rolling 24-hour episodes from 2024 (out-of-sample LSTM forecasts from the
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
EPISODES = 400
EVAL_EVERY = 10
MAX_STEPS = 24


_DECOMP_KEYS = ("term_throughput", "term_severe", "term_degraded", "term_fairness",
                "term_energy", "term_low_battery", "frac_severe", "frac_degraded",
                "term_switch", "frac_switched")


def run_episode(env, policy, agent=None):
    """Run one episode with policy(env, states) -> actions. Returns per-episode metrics.

    If `agent` is given, the SAME agent also makes the per-UAV feeder-HAPS choice each
    hour (see haps_association_env.step()'s `feeder_choice`), via one extra forward pass
    on a step-level feeder-context state (the per-user states' mean) -- not a per-user
    action, and not a second network. Rule-based baselines (agent=None) fall back to
    env.step()'s majority-vote default."""
    s = env.reset()
    rewards, info = [], {}
    decomp = {k: [] for k in _DECOMP_KEYS}
    for _ in range(MAX_STEPS):
        actions = policy(env, s)
        feeder_choice = int(agent.act(s.mean(axis=0))) % env.n_haps if agent is not None else None
        s, r, done, info = env.step(actions, feeder_choice=feeder_choice)
        rewards.append(r.mean())
        for k in _DECOMP_KEYS:
            if k in info:
                decomp[k].append(info[k])
    out = {
        "reward_per_step": float(np.mean(rewards)),
        "jain": float(info["jain_throughput"]),   # reported: Jain over per-user throughput
        "jain_sinr": float(info["jain_index"]),   # reward term: Jain over linear SINR
        "outage": int(info["n_outage"]),
        "soc": float(np.mean(info["battery_soc"])),
    }
    # Additive: mean per-step reward-term decomposition, only when the env provides it.
    for k, v in decomp.items():
        if v:
            out[k] = float(np.mean(v))
    return out


def dqn_policy(agent):
    def policy(env, s):
        return agent.act_batch(s)
    return policy


def random_policy(env, s):
    return np.random.randint(0, env.n_actions, size=env.n_users)


def max_sinr_policy(env, s):
    # Best direct HAPS by SINR (actions 0..n_haps-1); the paper's closed-form baseline.
    # NOTE: this reads env._sinr_db directly -- a free, instantaneous, noiseless SINR
    # reading to all three HAPS, every hour. No real UE gets that for free (it would need
    # to retune/measure each HAPS's beam and report back); see BoundedPollMaxSINR below
    # for the same rule under a measurement budget a UE could actually meet.
    return np.argmax(env._sinr_db, axis=1)


class BoundedPollMaxSINR:
    """Max-SINR baseline under a realistic measurement budget: each user can only get a
    fresh SINR reading for ONE of the three HAPS per hour (round-robin), and must act on
    the last-known (possibly up to two hours stale) reading for the other two. Picks the
    best among its currently-known readings, same decision rule as max_sinr_policy, but
    without that policy's free, all-link, every-hour measurement.

    Construct a new instance per episode (its memory must reset at episode boundaries);
    passing `lambda a: BoundedPollMaxSINR()` as `make_policy` to evaluate_method does this.

    INCOMPLETE as a measurement-overhead model -- do not treat a win/loss against this
    baseline as a settled comparison. It still omits: the UE's battery/power draw from
    doing the polling itself; how many antennas/RF chains the UE has (a UE with more
    chains could measure more than one HAPS per hour, changing this budget entirely);
    and cross-interference effects once many UEs are polling and switching at once (this
    class runs each user independently with no multi-UE coupling). It also doesn't
    capture the DQN's own structural advantage here: the DQN is software running in a
    control-plane entity, not on the UE, so unlike this UE-side heuristic it isn't
    bounded by any single UE's measurement/antenna/battery budget and can scale to
    however many UEs the deployment has without each one needing to poll anything itself.
    """

    def __init__(self, n_haps=3):
        self.n_haps = n_haps
        self._last = None

    def __call__(self, env, s):
        if self._last is None:
            self._last = env._sinr_db.copy()  # hour 0: no history yet, bootstrap with a full read
        else:
            poll_idx = env.t % self.n_haps
            self._last[:, poll_idx] = env._sinr_db[:, poll_idx]
        return np.argmax(self._last, axis=1)


def greedy_throughput_policy(env, s):
    # Same action set as the DQN (direct and UAV relay for each HAPS). Each user takes the action
    # with the highest throughput, with no learning and no battery or fairness term.
    direct = np.log2(1.0 + 10.0 ** (env._sinr_db / 10.0))
    tp = np.concatenate([direct, env._uav_relay_capacity], axis=1)
    return np.argmax(tp, axis=1)


def evaluate_method(eval_eps, policy_name, make_policy, agent=None):
    env = RealEpisodeEnv(eval_eps, seed=SEED + 1)
    rows = []
    for _ in range(len(eval_eps)):
        policy = make_policy(agent)
        m = run_episode(env, policy, agent=agent)
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
            feeder_ctx = s.mean(axis=0)
            feeder_raw = agent.act(feeder_ctx)
            feeder_choice = feeder_raw % env.n_haps
            s2, r, done, _ = env.step(actions, feeder_choice=feeder_choice)
            feeder_ctx2 = s2.mean(axis=0)
            for k in range(env.n_users):
                agent.remember(s[k], actions[k], r[k], s2[k], done)
            # Same shared network/buffer learns the per-UAV feeder choice too, off the
            # step-level (mean) reward, since it's one decision shared by all relay users
            # that hour, not a per-user one.
            agent.remember(feeder_ctx, feeder_raw, float(r.mean()), feeder_ctx2, done)
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
    all_rows += evaluate_method(eval_eps, "bounded_poll_sinr", lambda a: BoundedPollMaxSINR())
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
