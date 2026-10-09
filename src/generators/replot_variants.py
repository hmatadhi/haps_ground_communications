"""
replot_variants.py
==================
Regenerate figures 6 and 7 from the saved variant_compare_log.npz with corrected,
unambiguous labels (no re-training needed).

Labels clarify that the C-RAN reward role is present in ALL variants; the variants
differ only in what is injected into the DQN *state*:
  local  = Arani-faithful state
  cran   = broadcast fairness/load injected into the state (extends Arani)
  occupancy = other-UAV channels injected (deviation)
"""
import numpy as np
import matplotlib.pyplot as plt

d = np.load("variant_compare_log.npz")
MODES = ["local", "cran", "occupancy"]
COLORS = {"local": "tab:red", "cran": "tab:blue", "occupancy": "tab:green"}
LABELS = {"local": "local state (Arani-faithful)",
          "cran": "broadcast-in-state (extends Arani)",
          "occupancy": "occupancy (deviation)"}
BAR = {"local": "local\n(Arani-faithful)", "cran": "broadcast-in-state\n(extends Arani)",
       "occupancy": "occupancy\n(deviation)"}
LASTK = 5

# ---------- Fig 6: mean +- std curves ----------
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
for m in MODES:
    x = d[f"{m}_x"]; R = d[f"{m}_reward"]; O = d[f"{m}_outage"]
    Rm, Rs = R.mean(0), R.std(0); Om, Os = O.mean(0), O.std(0)
    ax[0].plot(x, Rm, "-o", ms=3, color=COLORS[m], label=LABELS[m])
    ax[0].fill_between(x, Rm - Rs, Rm + Rs, color=COLORS[m], alpha=0.15)
    ax[1].plot(x, Om, "-o", ms=3, color=COLORS[m], label=LABELS[m])
    ax[1].fill_between(x, Om - Os, Om + Os, color=COLORS[m], alpha=0.15)
ax[0].set_xlabel("Episode"); ax[0].set_ylabel("Eval reward / step")
ax[0].set_title("Reward convergence by design (4-seed)"); ax[0].grid(alpha=0.3); ax[0].legend(fontsize=8)
ax[1].set_xlabel("Episode"); ax[1].set_ylabel("Outage users")
ax[1].set_title("Outage by design (4-seed)"); ax[1].grid(alpha=0.3); ax[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig("figures/6_variant_comparison.png", dpi=150)

# ---------- Fig 7: single vs multi-seed bars ----------
def summ(metric):
    single, mm, ms = [], [], []
    for m in MODES:
        arr = d[f"{m}_{metric}"]
        single.append(arr[0, -LASTK:].mean())
        ps = arr[:, -LASTK:].mean(axis=1)
        mm.append(ps.mean()); ms.append(ps.std())
    return np.array(single), np.array(mm), np.array(ms)

fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
x = np.arange(len(MODES)); w = 0.38
for i, (metric, ylab, title) in enumerate(
        [("reward", "Eval reward / step", "Reward: single vs multi-seed"),
         ("outage", "Outage users", "Outage: single vs multi-seed")]):
    s, mm, ms = summ(metric)
    ax[i].bar(x - w/2, s, w, label="single seed (seed 0)", color="tab:orange")
    ax[i].bar(x + w/2, mm, w, yerr=ms, capsize=4,
              label="multi-seed (mean$\\pm$std)", color="tab:blue")
    ax[i].set_xticks(x); ax[i].set_xticklabels([BAR[m] for m in MODES], fontsize=8)
    ax[i].set_ylabel(ylab); ax[i].set_title(title); ax[i].grid(axis="y", alpha=0.3)
    ax[i].legend(fontsize=8)
fig.suptitle("Why multi-seed: a single seed misranks the designs", fontsize=11)
fig.tight_layout(); fig.savefig("figures/7_single_vs_multiseed.png", dpi=150)
print("Regenerated figures/6_variant_comparison.png and figures/7_single_vs_multiseed.png")
