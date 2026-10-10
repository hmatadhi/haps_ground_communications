"""
Bar charts of the policy comparison over the five training seeds, with standard deviation bars
(std across seeds). Three panels: reward per step (higher is better), Jain fairness (higher is
better), outage users of 50 (lower is better).

Inputs (data/processed/dqn_multiseed/):
  seed_results.csv     DQN with LSTM, one row per seed (run_multiseed.py)
  baselines_5seed.csv  random and max-SINR on the real and PreLSTM days, per seed
                       (run_baselines_5seed.py)
Output: data/processed/figures/policy_comparison.png

Run in WSL (env ~/quantum_env): python src/drl_dqn/plot_comparison.py
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MULTISEED_DIR = os.path.join(ROOT, "data", "processed", "dqn_multiseed")
SEED_RESULTS = os.path.join(MULTISEED_DIR, "seed_results.csv")
BASELINES = os.path.join(MULTISEED_DIR, "baselines_5seed.csv")
OUT_PATH = os.path.join(ROOT, "data", "processed", "figures", "policy_comparison.png")

# (label on the axis, colour)
POLICIES = [
    ("Random", "0.6"),
    ("Max-SINR\n(direct only)", "tab:orange"),
    ("Greedy\nthroughput", "tab:olive"),
    ("DQN with\nLSTM", "tab:blue"),
]
METRICS = [
    ("reward_per_step", "Reward per step (higher is better)"),
    ("jain", "Jain fairness index (higher is better)"),
    ("outage", "Outage users of 50 (lower is better)"),
]


def per_seed_table() -> pd.DataFrame:
    """One row per (policy, seed) with the metrics, in the order of POLICIES."""
    dqn = pd.read_csv(SEED_RESULTS)
    dqn = dqn[dqn["policy"] == "DQN with LSTM"]  # seed_results also holds baseline rows
    dqn = dqn.assign(policy="DQN with\nLSTM")[["policy", "seed", "reward_per_step", "jain", "outage"]]
    base = pd.read_csv(BASELINES)
    base = base[base["eval_set"] == "real"]  # the real 2025 days only
    names = {"random": "Random", "max-SINR": "Max-SINR\n(direct only)",
             "greedy-throughput": "Greedy\nthroughput"}
    base["policy"] = [names[b] for b in base["base_policy"]]
    base = base[["policy", "seed", "reward_per_step", "jain", "outage"]]
    return pd.concat([base, dqn], ignore_index=True)


def main() -> None:
    df = per_seed_table()
    order = [label for label, _ in POLICIES]
    colours = [c for _, c in POLICIES]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    for ax, (col, title) in zip(axes, METRICS):
        grp = df.groupby("policy")[col].agg(["mean", "std"]).reindex(order)
        x = range(len(order))
        ax.bar(x, grp["mean"], yerr=grp["std"], color=colours, capsize=4, edgecolor="black", lw=0.6)
        ax.set_xticks(list(x))
        ax.set_xticklabels(order, fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.axhline(0, color="black", lw=0.6)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Policy comparison on 50 held-out days, five seeds (error bars: 1 std across seeds)",
                 fontsize=11)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
