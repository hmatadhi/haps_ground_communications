"""
Charts for the DQN seed statistics (Table VIII) and the paired differences (Table IX).

Table VIII chart: per-seed DQN values with the mean and 95 % CI of the mean, for reward,
throughput Jain, outage and battery SoC.
Table IX chart: forest plot of paired differences (DQN minus each reference policy) with 95 % CI.

Inputs (data/processed/dqn_multiseed/): seed_results.csv, baselines_5seed.csv
Outputs (data/processed/figures/): seed_stats.png, paired_forest.png

Run in WSL (env ~/quantum_env): python src/drl_dqn/plot_seed_and_paired.py
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MULTISEED_DIR = os.path.join(ROOT, "data", "processed", "dqn_multiseed")
FIG_DIR = os.path.join(ROOT, "data", "processed", "figures")

METRICS = [
    ("reward_per_step", "Reward per step"),
    ("jain", "Jain (per-user throughput)"),
    ("outage", "Outage users of 50"),
    ("soc", "Battery SoC (%)"),
]


def ci95(x: np.ndarray):
    n = len(x)
    half = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n)
    return x.mean() - half, x.mean() + half


def seed_stats_chart(dqn: pd.DataFrame, out: str) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.8))
    for ax, (col, title) in zip(axes, METRICS):
        x = dqn[col].values
        seeds = dqn["seed"].values
        ax.scatter(seeds, x, color="tab:blue", zorder=3, label="seed")
        lo, hi = ci95(x)
        ax.axhline(x.mean(), color="tab:blue", lw=1.2, label="mean")
        ax.axhspan(lo, hi, color="tab:blue", alpha=0.15, label="95 % CI of mean")
        ax.set_xticks(seeds)
        ax.set_xlabel("seed")
        ax.set_title(title, fontsize=10)
        ax.grid(axis="y", alpha=0.3)
        if np.all(x == 0):  # degenerate scale: state the value instead of plotting it
            ax.set_ylim(-1, 1)
            ax.text(0.5, 0.5, "0 on every seed", transform=ax.transAxes, ha="center", va="center", fontsize=10)
    axes[0].legend(fontsize=8, loc="best")
    fig.suptitle("LSTM + DQN across five seeds (Table VIII)", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def paired_forest_chart(dqn: pd.DataFrame, base: pd.DataFrame, out: str) -> None:
    rows = []
    for name, sub in [("max-SINR (direct only)", "max-SINR"),
                      ("greedy throughput", "greedy-throughput")]:
        ref = base[base["base_policy"] == sub].set_index("seed")
        for col, title in METRICS:
            diff = dqn.set_index("seed")[col] - ref[col]
            lo, hi = ci95(diff.values)
            if col == "outage":
                better = int((diff < 0).sum())
                tie = bool(np.all(diff == 0))
            else:
                better = int((diff > 0).sum())
                tie = False
            rows.append((f"{title}\nvs {name}", diff.mean(), lo, hi, better, tie))
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(rows) + 1.5))
    y = np.arange(len(rows))[::-1]
    for yi, (label, m, lo, hi, better, tie) in zip(y, rows):
        ax.errorbar(m, yi, xerr=[[m - lo], [hi - m]], fmt="o", color="tab:blue", capsize=4)
        note = "tie (identical on all seeds)" if tie else f"{better}/5 seeds"
        ax.text(1.02, yi, note, transform=ax.get_yaxis_transform(), va="center", fontsize=8)
    ax.axvline(0, color="black", lw=0.8, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8)
    ax.set_xlabel("DQN minus reference policy (mean, 95 % CI); outage: negative is better")
    ax.set_title("Paired differences, LSTM + DQN (Table IX)", fontsize=11)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    os.makedirs(FIG_DIR, exist_ok=True)
    seeds = pd.read_csv(os.path.join(MULTISEED_DIR, "seed_results.csv"))
    dqn = seeds[seeds["policy"] == "DQN with LSTM"].reset_index(drop=True)
    base = pd.read_csv(os.path.join(MULTISEED_DIR, "baselines_5seed.csv"))
    base = base[base["eval_set"] == "real"]
    seed_out = os.path.join(FIG_DIR, "seed_stats.png")
    paired_out = os.path.join(FIG_DIR, "paired_forest.png")
    seed_stats_chart(dqn, seed_out)
    paired_forest_chart(dqn, base, paired_out)
    print(f"Wrote {seed_out}\nWrote {paired_out}")


if __name__ == "__main__":
    main()
