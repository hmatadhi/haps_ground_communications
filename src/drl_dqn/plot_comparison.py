"""
Bar charts of the five-policy comparison (compare_baselines.py), with standard deviation bars.
Three panels: reward per step (higher is better), Jain fairness (higher is better), outage
users of 50 (lower is better).

Output: data/processed/figures/policy_comparison.png

Run in WSL (env ~/quantum_env): python src/drl_dqn/plot_comparison.py
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EPISODES = os.path.join(ROOT, "data", "processed", "dqn_real", "comparison_episodes.csv")
OUT_PATH = os.path.join(ROOT, "data", "processed", "figures", "policy_comparison.png")

LABELS = {
    "1 Phase1 random (real)": "Phase 1\nrandom",
    "2 Phase1 max-SINR (real)": "Phase 1\nmax-SINR",
    "3 PreLSTM random": "PreLSTM\nrandom",
    "4 PreLSTM max-SINR": "PreLSTM\nmax-SINR",
    "5 DQN with LSTM (real)": "DQN with\nLSTM",
}
COLOURS = ["0.6", "tab:orange", "0.8", "tab:brown", "tab:blue"]
METRICS = [
    ("reward_per_step", "Reward per step (higher is better)"),
    ("jain", "Jain fairness index (higher is better)"),
    ("outage", "Outage users of 50 (lower is better)"),
]


def main() -> None:
    df = pd.read_csv(EPISODES)
    order = list(LABELS.keys())
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    for ax, (col, title) in zip(axes, METRICS):
        grp = df.groupby("policy")[col].agg(["mean", "std"]).reindex(order)
        x = range(len(order))
        ax.bar(x, grp["mean"], yerr=grp["std"], color=COLOURS, capsize=4, edgecolor="black", lw=0.6)
        ax.set_xticks(list(x))
        ax.set_xticklabels([LABELS[p] for p in order], fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.axhline(0, color="black", lw=0.6)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Five-policy comparison on 50 held-out evaluation days (error bars: 1 std)", fontsize=11)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
