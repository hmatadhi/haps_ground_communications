"""
train_dqn_association.py
=========================
Train a DQN on the paper's actual Phase-2 MDP: per-user association to one of
3 constellation HAPS, with battery/weather state (haps_association_env.py).

This is separate from train_dqn_phase2.py, which trains on a different,
unrelated MDP (1 fixed HAPS + 3 mobile UAVs choosing movement/channel) -- see
docs/PHASE2_ASSOCIATION_PLAN.md for why these are two different problems and
why this script exists.

Run:
    python train_dqn_association.py

Outputs (repo root):
    dqn_association_results/
      dqn_model_association.pt
      dqn_train_log_association.csv
      training_config.json
      figures/8_dqn_association_convergence.png
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
from haps_association_env import HAPSAssociationEnv
from weather_scenario_generator import WeatherScenarioGenerator

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

N_USERS = 50
EPISODES = 300
EVAL_EVERY = 10
EVAL_EPISODES = 8
EVAL_SEED = 999
MAX_STEPS = 24  # hours per simulated day

REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
RESULTS_DIR = os.path.join(REPO_ROOT, "dqn_association_results")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(os.path.join(RESULTS_DIR, "figures"), exist_ok=True)


def make_env(seed):
    weather_gen = WeatherScenarioGenerator(mode="random_mix", seed=seed)
    return HAPSAssociationEnv(n_users=N_USERS, max_steps=MAX_STEPS,
                               weather_generator=weather_gen, seed=seed)


def evaluate(agent, n_ep=EVAL_EPISODES):
    """Greedy evaluation on a held-out seed, same convention as train_dqn_phase2.py."""
    eval_env = make_env(EVAL_SEED)
    saved_eps, agent.eps = agent.eps, 0.0
    R, J, O, SOC = [], [], [], []
    for _ in range(n_ep):
        s = eval_env.reset()
        tot_r, info = 0.0, {}
        for _ in range(eval_env.max_steps):
            actions = agent.act_batch(s)
            s, r, done, info = eval_env.step(actions)
            tot_r += r.mean()
        R.append(tot_r / eval_env.max_steps)
        J.append(info["jain_index"])
        O.append(info["n_outage"])
        SOC.append(info["battery_soc"].mean())
    agent.eps = saved_eps
    return np.mean(R), np.mean(J), np.mean(O), np.mean(SOC)


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device}" + (f" ({torch.cuda.get_device_name(0)})" if device == "cuda" else ""))

    env = make_env(SEED)
    agent = DQNAgent(env.state_dim, env.n_actions, seed=SEED, device=device)

    print(f"State dim: {env.state_dim} | n_actions: {env.n_actions} | n_users: {N_USERS}")
    print(f"Training for {EPISODES} episodes ({MAX_STEPS}-hour days)...\n")

    xs, ev_reward, ev_jain, ev_outage, ev_soc = [], [], [], [], []
    train_log = []

    for ep in range(EPISODES):
        s = env.reset()
        for step in range(env.max_steps):
            actions = agent.act_batch(s)
            s2, r, done, info = env.step(actions)
            for k in range(env.n_users):
                agent.remember(s[k], actions[k], r[k], s2[k], done)
            agent.train_step()
            s = s2
        agent.decay_eps()

        if (ep + 1) % EVAL_EVERY == 0:
            R, J, O, SOC = evaluate(agent)
            xs.append(ep + 1)
            ev_reward.append(R)
            ev_jain.append(J)
            ev_outage.append(O)
            ev_soc.append(SOC)
            train_log.append({"episode": ep + 1, "eval_reward": R, "jain_index": J,
                               "n_outage": O, "mean_battery_soc": SOC})
            print(f"ep {ep+1:3d} | eval reward {R:8.2f} | jain {J:.3f} | "
                  f"outage {O:4.1f}/{N_USERS} | soc {SOC:5.1f}% | eps {agent.eps:.3f}")

    model_path = os.path.join(RESULTS_DIR, "dqn_model_association.pt")
    torch.save(agent.q.state_dict(), model_path)

    config = {
        "n_users": N_USERS, "episodes": EPISODES, "eval_every": EVAL_EVERY,
        "eval_episodes": EVAL_EPISODES, "eval_seed": EVAL_SEED, "training_seed": SEED,
        "max_steps": MAX_STEPS, "weather_mode": "random_mix", "device": device,
        "state_dim": env.state_dim, "n_actions": env.n_actions,
    }
    with open(os.path.join(RESULTS_DIR, "training_config.json"), "w") as f:
        json.dump(config, f, indent=2)

    log_path = os.path.join(RESULTS_DIR, "dqn_train_log_association.csv")
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", "eval_reward", "jain_index",
                                                "n_outage", "mean_battery_soc"])
        writer.writeheader()
        writer.writerows(train_log)

    fig, ax = plt.subplots(1, 4, figsize=(18, 3.5))
    ax[0].plot(xs, ev_reward, "-o", ms=4, color="tab:blue")
    ax[0].set_title("Eval reward"); ax[0].set_xlabel("Episode"); ax[0].grid(alpha=0.3)
    ax[1].plot(xs, ev_jain, "-o", ms=4, color="tab:green")
    ax[1].set_title("Jain fairness"); ax[1].set_xlabel("Episode"); ax[1].set_ylim(0, 1.05); ax[1].grid(alpha=0.3)
    ax[2].plot(xs, ev_outage, "-o", ms=4, color="tab:red")
    ax[2].set_title("Outage (users)"); ax[2].set_xlabel("Episode"); ax[2].grid(alpha=0.3)
    ax[3].plot(xs, ev_soc, "-o", ms=4, color="tab:orange")
    ax[3].set_title("Mean battery SoC (%)"); ax[3].set_xlabel("Episode"); ax[3].set_ylim(0, 100); ax[3].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "figures", "8_dqn_association_convergence.png"), dpi=150)
    plt.close(fig)

    print(f"\nSaved model:  {model_path}")
    print(f"Saved log:    {log_path}")
    print(f"Final: reward={ev_reward[-1]:.2f} jain={ev_jain[-1]:.3f} "
          f"outage={ev_outage[-1]:.1f}/{N_USERS} soc={ev_soc[-1]:.1f}%")


if __name__ == "__main__":
    main()
