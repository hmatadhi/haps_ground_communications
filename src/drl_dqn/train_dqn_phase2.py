"""
train_dqn_phase2.py
===================
Phase 2: Train DQN with weather-driven data generation.

Extends train_dqn.py with:
  - WeatherScenarioGenerator for multi-profile weather sampling
  - Per-episode weather state logging (rain, visibility, hour)
  - Weather-aware reward convergence tracking
  - Results saved to dqn_results/ folder (reproducible via config JSON)

Run:
    python train_dqn_phase2.py

Expected runtime: 30 min (GPU), 2 h (CPU)

Outputs:
    dqn_results/
      dqn_model_phase2.pt                 trained weights
      dqn_train_log_phase2.csv            per-episode metrics
      dqn_weather_log_phase2.csv          per-episode weather state
      training_config.json                hyperparams for reproducibility
      figures/5_dqn_phase2_convergence.png    reward/fairness/outage
      figures/6_dqn_phase2_reward_by_weather.png    reward scatter
      figures/7_dqn_phase2_weather_coverage.png     weather histogram
"""

import os
import json
import csv
import numpy as np
import torch
import matplotlib.pyplot as plt

from .dqn_agent import DQNAgent
# Note: haps_env and weather_scenario_generator should also be in drl_dqn/ or copied from AI-HAPS
try:
    from .haps_env import HAPSUAVEnv
    from .weather_scenario_generator import WeatherScenarioGenerator
except ImportError:
    # Fallback: try importing from parent src/ directory
    import sys
    sys.path.insert(0, '..')
    from haps_env import HAPSUAVEnv
    from weather_scenario_generator import WeatherScenarioGenerator

# ---- reproducibility ----
SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

# ---- config ----
N_UAV, N_USERS, N_CH = 3, 200, 3
EPISODES = 400
EVAL_EVERY = 10
EVAL_EPISODES = 8
EVAL_SEED = 999

# Output folder
RESULTS_DIR = "dqn_results"
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(os.path.join(RESULTS_DIR, "figures"), exist_ok=True)
os.makedirs(os.path.join(RESULTS_DIR, "logs"), exist_ok=True)


def evaluate(agent, env_config, n_ep=EVAL_EPISODES):
    """Greedy evaluation on held-out env seed with weather logging."""
    eval_env = HAPSUAVEnv(**env_config, seed=EVAL_SEED)
    saved_eps, agent.eps = agent.eps, 0.0
    R, F, O = [], [], []
    for _ in range(n_ep):
        s = eval_env.reset()
        tot_r, info = 0.0, {}
        for _ in range(eval_env.max_steps):
            actions = [agent.act(s[u]) for u in range(eval_env.n_uav)]
            s, r, done, info = eval_env.step(actions)
            tot_r += r.mean()
        R.append(tot_r / eval_env.max_steps)
        F.append(info["fairness"])
        O.append(info["outage"])
    agent.eps = saved_eps
    return np.mean(R), np.mean(F), np.mean(O)


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device}"
          + (f" ({torch.cuda.get_device_name(0)})" if device == "cuda" else ""))

    # Configuration
    env_config = {
        "n_uav": N_UAV,
        "n_users": N_USERS,
        "n_channels": N_CH,
        "max_steps": 50,
        "with_haps": True,
        "state_mode": "local",
    }

    # Create environment with weather generator
    weather_gen = WeatherScenarioGenerator(mode="random_mix", seed=SEED)
    env_config["weather_generator"] = weather_gen

    env = HAPSUAVEnv(**env_config, seed=SEED)
    agent = DQNAgent(env.state_dim, env.n_actions, seed=SEED, device=device)

    print(f"State dim: {env.state_dim} | n_actions: {env.n_actions}")
    print(f"Weather generator: random_mix mode, seed={SEED}")
    print(f"Training for {EPISODES} episodes...\n")

    # Training logs
    xs = []
    ev_reward, ev_fair, ev_out = [], [], []

    # Per-episode logs (training)
    train_log = []
    weather_log = []

    for ep in range(EPISODES):
        s = env.reset()
        ep_reward = 0.0
        ep_weather = env.weather_state

        for step in range(env.max_steps):
            actions = [agent.act(s[u]) for u in range(env.n_uav)]
            s2, r, done, info = env.step(actions)
            ep_reward += r.mean()
            for u in range(env.n_uav):
                agent.remember(s[u], actions[u], r[u], s2[u], done)
            agent.train_step()
            s = s2

        agent.decay_eps()

        # Evaluation every EVAL_EVERY episodes
        if (ep + 1) % EVAL_EVERY == 0:
            R, F, O = evaluate(agent, env_config)
            xs.append(ep + 1)
            ev_reward.append(R)
            ev_fair.append(F)
            ev_out.append(O)

            # Log evaluation metrics
            train_log.append({
                "episode": ep + 1,
                "eval_reward": R,
                "fairness": F,
                "outage": O,
            })

            print(f"ep {ep+1:3d} | eval reward {R:.3f} | fairness {F:.3f} | "
                  f"outage {O:5.1f} | weather {ep_weather.scenario_name} | eps {agent.eps:.3f}")

        # Log per-episode weather (for all episodes, not just eval)
        weather_log.append({
            "episode": ep + 1,
            "scenario_name": ep_weather.scenario_name if ep_weather else "none",
            "rain_mm_h": ep_weather.rain_mm_h if ep_weather else 0.0,
            "visibility_km": ep_weather.visibility_km if ep_weather else 0.0,
            "hour_of_day": ep_weather.hour_of_day if ep_weather else 0.0,
        })

    # ---- Save artifacts ----
    model_path = os.path.join(RESULTS_DIR, "dqn_model_phase2.pt")
    torch.save(agent.q.state_dict(), model_path)

    # Save training config
    config_to_save = {
        "n_uav": N_UAV,
        "n_users": N_USERS,
        "n_channels": N_CH,
        "episodes": EPISODES,
        "eval_every": EVAL_EVERY,
        "eval_episodes": EVAL_EPISODES,
        "eval_seed": EVAL_SEED,
        "training_seed": SEED,
        "weather_mode": "random_mix",
        "device": device,
    }
    config_path = os.path.join(RESULTS_DIR, "training_config.json")
    with open(config_path, "w") as f:
        json.dump(config_to_save, f, indent=2)

    # Save training log CSV
    train_log_path = os.path.join(RESULTS_DIR, "dqn_train_log_phase2.csv")
    if train_log:
        with open(train_log_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["episode", "eval_reward", "fairness", "outage"])
            writer.writeheader()
            writer.writerows(train_log)

    # Save weather log CSV
    weather_log_path = os.path.join(RESULTS_DIR, "dqn_weather_log_phase2.csv")
    if weather_log:
        with open(weather_log_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["episode", "scenario_name", "rain_mm_h", "visibility_km", "hour_of_day"]
            )
            writer.writeheader()
            writer.writerows(weather_log)

    # ---- Convergence figures ----
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.5))

    ax[0].plot(xs, ev_reward, "-o", ms=4, color="tab:blue", linewidth=1.5)
    ax[0].set_xlabel("Episode")
    ax[0].set_ylabel("Eval reward / step")
    ax[0].set_title("Phase 2 DQN Reward Convergence")
    ax[0].grid(alpha=0.3)

    ax[1].plot(xs, ev_fair, "-o", ms=4, color="tab:green", linewidth=1.5)
    ax[1].set_xlabel("Episode")
    ax[1].set_ylabel("Jain's fairness")
    ax[1].set_title("Fairness vs. Training")
    ax[1].grid(alpha=0.3)
    ax[1].set_ylim(0, 1.05)

    ax[2].plot(xs, ev_out, "-o", ms=4, color="tab:red", linewidth=1.5)
    ax[2].set_xlabel("Episode")
    ax[2].set_ylabel("Outage users")
    ax[2].set_title("Outage vs. Training")
    ax[2].grid(alpha=0.3)

    fig.tight_layout()
    fig_path = os.path.join(RESULTS_DIR, "figures", "5_dqn_phase2_convergence.png")
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    # ---- Reward vs Weather scatter ----
    if len(weather_log) > 0 and len(train_log) > 0:
        # Match episodes: weather_log has all episodes, train_log has eval episodes only
        eval_episodes = [t["episode"] for t in train_log]
        eval_rewards = [t["eval_reward"] for t in train_log]

        rains = []
        for ep in eval_episodes:
            # Find matching weather entry
            weather_entry = next((w for w in weather_log if w["episode"] == ep), None)
            if weather_entry:
                rains.append(weather_entry["rain_mm_h"])
            else:
                rains.append(0.0)

        fig, ax = plt.subplots(figsize=(8, 5))
        scatter = ax.scatter(eval_episodes, eval_rewards, c=rains, cmap="RdYlBu_r", s=100, alpha=0.7, edgecolors="black")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Eval Reward")
        ax.set_title("Reward vs Weather (colored by rain rate)")
        ax.grid(alpha=0.3)
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label("Rain Rate (mm/h)")
        fig.tight_layout()
        fig_path = os.path.join(RESULTS_DIR, "figures", "6_dqn_phase2_reward_by_weather.png")
        fig.savefig(fig_path, dpi=150)
        plt.close(fig)

    # ---- Weather coverage histogram ----
    if len(weather_log) > 0:
        rains = [w["rain_mm_h"] for w in weather_log]
        visibilities = [w["visibility_km"] for w in weather_log]

        fig, ax = plt.subplots(1, 2, figsize=(12, 4))

        ax[0].hist(rains, bins=15, color="steelblue", alpha=0.7, edgecolor="black")
        ax[0].set_xlabel("Rain Rate (mm/h)")
        ax[0].set_ylabel("Frequency")
        ax[0].set_title("Rain Distribution Across 400 Episodes")
        ax[0].grid(alpha=0.3, axis="y")

        ax[1].hist(visibilities, bins=15, color="forestgreen", alpha=0.7, edgecolor="black")
        ax[1].set_xlabel("Visibility (km)")
        ax[1].set_ylabel("Frequency")
        ax[1].set_title("Visibility Distribution Across 400 Episodes")
        ax[1].grid(alpha=0.3, axis="y")

        fig.tight_layout()
        fig_path = os.path.join(RESULTS_DIR, "figures", "7_dqn_phase2_weather_coverage.png")
        fig.savefig(fig_path, dpi=150)
        plt.close(fig)

    # Print summary
    print(f"\n{'='*70}")
    print(f"Training complete!")
    print(f"{'='*70}")
    print(f"Saved model:       {model_path}")
    print(f"Saved config:      {config_path}")
    print(f"Saved train log:   {train_log_path}")
    print(f"Saved weather log: {weather_log_path}")
    print(f"Saved figures to:  {os.path.join(RESULTS_DIR, 'figures')}")
    print(f"\nFinal metrics (episode {EPISODES}):")
    print(f"  Eval Reward: {ev_reward[-1]:.3f}")
    print(f"  Fairness:    {ev_fair[-1]:.3f}")
    print(f"  Outage:      {ev_out[-1]:.1f} users")
    print(f"\nWeather coverage stats:")
    stats = weather_gen.get_coverage_stats(n_samples=400)
    print(f"  Rain bins:       {dict(list(stats['rain_mm_h'].items())[:3])} ...")
    print(f"  Visibility bins: {dict(list(stats['visibility_km'].items())[:2])} ...")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
