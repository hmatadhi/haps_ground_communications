"""
make_seed_figure.py
===================
Methodology figure: single-seed vs multi-seed conclusions for the three DQN
designs, from variant_compare_log.npz (4 seeds x 30 eval checkpoints).

Shows that a single seed can rank the designs differently from the seed-averaged
result -- the reason we report multi-seed means with variance.

Output: figures/7_single_vs_multiseed.png
"""
import numpy as np
import matplotlib.pyplot as plt

d = np.load("variant_compare_log.npz")
MODES = ["local", "cran", "occupancy"]
LABELS = ["local\n(Arani)", "C-RAN\n(Arani)", "occupancy\n(deviation)"]
LASTK = 5   # average the last K checkpoints for a stable converged estimate

def summ(metric):
    single, multi_m, multi_s = [], [], []
    for m in MODES:
        arr = d[f"{m}_{metric}"]                 # seeds x checkpoints
        single.append(arr[0, -LASTK:].mean())    # seed 0 only
        per_seed = arr[:, -LASTK:].mean(axis=1)  # each seed's converged value
        multi_m.append(per_seed.mean())
        multi_s.append(per_seed.std())
    return np.array(single), np.array(multi_m), np.array(multi_s)

fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
x = np.arange(len(MODES)); w = 0.38

for i, (metric, ylab, title) in enumerate(
        [("reward", "Eval reward / step", "Reward: single vs multi-seed"),
         ("outage", "Outage users", "Outage: single vs multi-seed")]):
    s, mm, ms = summ(metric)
    ax[i].bar(x - w/2, s, w, label="single seed (seed 0)", color="tab:orange")
    ax[i].bar(x + w/2, mm, w, yerr=ms, capsize=4, label="multi-seed (mean$\\pm$std)",
              color="tab:blue")
    ax[i].set_xticks(x); ax[i].set_xticklabels(LABELS)
    ax[i].set_ylabel(ylab); ax[i].set_title(title); ax[i].grid(axis="y", alpha=0.3)
    ax[i].legend(fontsize=8)

fig.suptitle("Why multi-seed: a single seed misranks the designs", fontsize=11)
fig.tight_layout()
fig.savefig("figures/7_single_vs_multiseed.png", dpi=150)
print("Saved figures/7_single_vs_multiseed.png")
for m, metric in [(m, "reward") for m in MODES]:
    pass
s, mm, ms = summ("reward")
print("reward  single:", np.round(s,3), " multi:", np.round(mm,3), "+-", np.round(ms,3))
s, mm, ms = summ("outage")
print("outage  single:", np.round(s,1), " multi:", np.round(mm,1), "+-", np.round(ms,1))
