"""
eval_baseline_association.py
=============================
Answers "is the trained DQN actually better than plain mathematical
evaluation?" for the association MDP (haps_association_env.py), by running
the SAME held-out environment/weather distribution (EVAL_SEED=999, matching
train_dqn_association.py's evaluate()) under three policies:

  1. max_sinr  -- the paper's own named "naive" baseline (Motivation section):
                  each user always associates to argmax_p SINR_k,p. No
                  learning, pure closed-form physics.
  2. random    -- sanity floor.
  3. dqn       -- the trained model from dqn_association_results/, eps=0.

Run (after train_dqn_association.py has produced a model):
    python eval_baseline_association.py

Outputs (repo root):
    dqn_association_results/
      baseline_comparison.csv
      figures/9_baseline_comparison.png
"""

import os
import sys
import json
import csv

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import numpy as np
import torch
import matplotlib.pyplot as plt

from dqn_agent import DQNAgent
from haps_association_env import HAPSAssociationEnv, SINR_DB_MIN, SINR_DB_MAX, CAPACITY_BPS_HZ_MAX
from weather_scenario_generator import WeatherScenarioGenerator

N_USERS = 50
MAX_STEPS = 24
EVAL_SEED = 999
N_EVAL_EPISODES = 50  # more than the 8 used mid-training, for stable comparison stats

REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
RESULTS_DIR = os.path.join(REPO_ROOT, "dqn_association_results")
MODEL_PATH = os.path.join(RESULTS_DIR, "dqn_model_association.pt")
CONFIG_PATH = os.path.join(RESULTS_DIR, "training_config.json")


def make_env(seed):
    weather_gen = WeatherScenarioGenerator(mode="random_mix", seed=seed)
    return HAPSAssociationEnv(n_users=N_USERS, max_steps=MAX_STEPS,
                               weather_generator=weather_gen, seed=seed)


def max_sinr_policy(state, env):
    # Extended "naive" baseline: pick whichever of the 6 actions (direct to
    # HAPS 0-2, or relay via HAPS 0-2's Gateway) gives the highest Shannon
    # capacity. Direct capacity is derived from state columns 0:3 (normalised
    # SINR, denormalised back to dB); relay capacity is state columns 12:15
    # (normalised bps/Hz), both denormalised with haps_association_env's own
    # bounds so this stays consistent with however the env normalises them.
    sinr_db = state[:, 0:3] * (SINR_DB_MAX - SINR_DB_MIN) + SINR_DB_MIN
    direct_capacity = np.log2(1.0 + 10.0 ** (sinr_db / 10.0))
    relay_capacity = state[:, 12:15] * CAPACITY_BPS_HZ_MAX
    combined_capacity = np.concatenate([direct_capacity, relay_capacity], axis=1)  # (n_users, 6)
    return np.argmax(combined_capacity, axis=1)


def random_policy(state, env):
    return env.rng.integers(0, env.n_actions, size=env.n_users)


def dqn_policy_factory(agent):
    def _policy(state, env):
        return agent.act_batch(state)
    return _policy


def run_policy(policy_fn, n_episodes=N_EVAL_EPISODES):
    env = make_env(EVAL_SEED)
    rewards, jains, outages, socs, throughputs = [], [], [], [], []
    for _ in range(n_episodes):
        s = env.reset()
        tot_r, info = 0.0, {}
        for _ in range(env.max_steps):
            actions = policy_fn(s, env)
            s, r, done, info = env.step(actions)
            tot_r += r.mean()
        rewards.append(tot_r / env.max_steps)
        jains.append(info["jain_index"])
        outages.append(info["n_outage"])
        socs.append(info["battery_soc"].mean())
        throughputs.append(info["throughput_bps_hz"])
    return {
        "reward_mean": np.mean(rewards), "reward_std": np.std(rewards),
        "jain_mean": np.mean(jains), "jain_std": np.std(jains),
        "outage_mean": np.mean(outages), "outage_std": np.std(outages),
        "soc_mean": np.mean(socs), "soc_std": np.std(socs),
        "throughput_mean": np.mean(throughputs), "throughput_std": np.std(throughputs),
    }


def main():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"No trained model at {MODEL_PATH}. Run train_dqn_association.py first."
        )
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    agent = DQNAgent(config["state_dim"], config["n_actions"], device=device)
    agent.q.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    agent.eps = 0.0

    print(f"Evaluating over {N_EVAL_EPISODES} held-out episodes (seed={EVAL_SEED}), "
          f"{N_USERS} users, {MAX_STEPS}-hour days...\n")

    policies = {
        "random": random_policy,
        "max_sinr": max_sinr_policy,
        "dqn": dqn_policy_factory(agent),
    }

    results = {}
    for name, fn in policies.items():
        results[name] = run_policy(fn)
        r = results[name]
        print(f"{name:10s} | reward {r['reward_mean']:8.2f} +/- {r['reward_std']:6.2f} | "
              f"jain {r['jain_mean']:.3f} +/- {r['jain_std']:.3f} | "
              f"outage {r['outage_mean']:5.1f}/{N_USERS} +/- {r['outage_std']:4.1f} | "
              f"soc {r['soc_mean']:5.1f}% +/- {r['soc_std']:4.1f} | "
              f"throughput {r['throughput_mean']:7.2f} +/- {r['throughput_std']:5.2f} bits/s/Hz")

    csv_path = os.path.join(RESULTS_DIR, "baseline_comparison.csv")
    with open(csv_path, "w", newline="") as f:
        fieldnames = ["policy"] + list(next(iter(results.values())).keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for name, r in results.items():
            writer.writerow({"policy": name, **r})

    fig, ax = plt.subplots(2, 2, figsize=(7, 6))
    names = list(results.keys())
    colors = ["tab:gray", "tab:orange", "tab:blue"]

    metrics = [("reward", "Eval reward / hour"), ("jain", "Jain fairness"),
               ("outage", f"Outage (of {N_USERS} users)"), ("soc", "Mean battery SoC (%)")]
    for (key, title), axis in zip(metrics, ax.flat):
        means = [results[n][f"{key}_mean"] for n in names]
        stds = [results[n][f"{key}_std"] for n in names]
        axis.bar(names, means, yerr=stds, color=colors, capsize=4)
        axis.set_title(title)
        axis.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    os.makedirs(os.path.join(RESULTS_DIR, "figures"), exist_ok=True)
    fig.savefig(os.path.join(RESULTS_DIR, "figures", "9_baseline_comparison.png"), dpi=150)
    plt.close(fig)

    print(f"\nSaved comparison CSV: {csv_path}")
    print(f"Saved comparison figure: {os.path.join(RESULTS_DIR, 'figures', '9_baseline_comparison.png')}")


if __name__ == "__main__":
    main()
