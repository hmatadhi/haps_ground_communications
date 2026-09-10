# Phase 2 run guide: per-user HAPS association DRL

This guide covers the workflow that implements `HAPS_AI_HW_ChannelModel.tex`'s
own **"Phase 2: DRL for User Association"** section: a 3-HAPS equilateral-triangle
constellation in which each **user** (not a mobile relay) independently picks which
HAPS to associate with, observing a 12-dimensional per-user state (SINR/distance/
battery-SoC to each HAPS, plus weather) and a diurnal battery/solar model. This is
the DRL experiment the paper's Motivation section, Section III.D (state and baseline
policy definitions), and Section IV.D (closed-form baseline results) all build toward.

## 1. What this is, and how it maps to the paper

Full narrative write-up in `HAPS_AI_HW_ChannelModel.tex`, in dependency order:

- Section III.D (`sec:assoc-baseline-setup`) — state/policy definitions and the
  random/max-SINR experiment setup, written to stand on its own (no DQN, no forward
  dependency on Phase 2).
- Section IV.D (`sec:assoc-baseline-results`) — the random-vs-max-SINR baseline
  results only (Table `tab:assoc-baseline-results`); this is the closed-form,
  no-DRL result.
- "Phase 2: DRL for User Association" (`sec:phase2-motivation` /
  `sec:phase2-results`) — adopts III.D's state, trains the DQN, and extends IV.D's
  baseline table with the DQN row (Table `tab:phase2-results`) plus the full
  discussion. Phase 2 cites III.D/IV.D; they do not reference each other's DQN.

Design rationale and the two bugs found and fixed along the way (reward credit
assignment, battery SoC unit conversion — the paper's "Error 5" and "Error 6" in
its Critical Implementation Fixes) are written up in
[`docs/PHASE2_ASSOCIATION_PLAN.md`](PHASE2_ASSOCIATION_PLAN.md).

## 2. The stack

- `src/drl_dqn/haps_association_env.py` — the per-user, 3-HAPS association MDP
- `src/drl_dqn/train_dqn_association.py` — DQN training entry point
- `src/drl_dqn/eval_baseline_association.py` — random / max-SINR / DQN comparison
- `src/drl_dqn/dqn_agent.py` — DQN implementation, with an `act_batch()` method
  that batches all users' epsilon-greedy action selection into one forward pass
  per step
- `src/models/battery_model.py` — `HAPSBatteryModel`, diurnal solar/battery model
- `src/drl_dqn/reward_function.py` — `compute_network_reward()`, the paper's reward
  formula
- `src/drl_dqn/weather_scenario_generator.py` — episode-level weather sampling
- `src/models/channel_model.py` — `haps_constellation_geometry()`, the 3-HAPS
  65 km equilateral-triangle geometry behind `HAPS_AI_HW_ChannelModel.tex` Table
  A.3 and the multi-HAPS interference figures

## 3. Setup and run commands

From the repo root:

```bash
cd c:/Github/haps_ground_communications
python -m pip install -r src/requirements.txt
```

Then, from `src/drl_dqn/`:

```bash
cd c:/Github/haps_ground_communications/src/drl_dqn

# 1. Smoke test the environment alone (random policy, one simulated day, 10 users)
python haps_association_env.py

# 2. Train the DQN (300 episodes, ~a few minutes on GPU)
python train_dqn_association.py

# 3. Compare random vs. max-SINR vs. the trained DQN (50 held-out episodes)
python eval_baseline_association.py
```

Step 3 requires step 2's model to already exist at
`dqn_association_results/dqn_model_association.pt`.

## 4. Configuration

`train_dqn_association.py` / `eval_baseline_association.py`:

- `N_USERS = 50` (configurable; each of the 24 hourly steps requires one action
  per user, so this is kept tractable for a shared-network DQN without a
  hyperparameter search)
- `EPISODES = 300`, `EVAL_EVERY = 10`, `EVAL_EPISODES = 8` (mid-training),
  `SEED = 42`
- `EVAL_SEED = 999`, `N_EVAL_EPISODES = 50` (final baseline comparison — more than
  the 8 used mid-training, for stable statistics)
- `max_steps = 24` — one episode = one simulated day, one step = one hour, so the
  diurnal battery/solar cycle is actually exercised
- 3-HAPS constellation: 65 km equilateral spacing, from
  `channel_model.haps_constellation_geometry()`
- Per-episode, held fixed for the whole episode: user positions (uniform, 0–100 km
  radius from the serving HAPS's nadir), initial per-HAPS battery SoC
  (`U(30, 100)%`)
- Per-episode, resampled: weather (`WeatherScenarioGenerator`, `random_mix` mode)

## 5. Output artifacts

```text
dqn_association_results/
  dqn_model_association.pt
  dqn_train_log_association.csv
  training_config.json
  baseline_comparison.csv
  figures/
    8_dqn_association_convergence.png
    9_baseline_comparison.png
```

`baseline_comparison.csv` and `figures/9_baseline_comparison.png` are the direct
answer to "is the DQN better than plain mathematical evaluation" for this MDP —
copies of the same two figures are embedded in the paper
(`HAPS_AI_HW_ChannelModel.tex`, Section IV.D and the Phase 2 results subsection).

## 6. Measured result

50 held-out episodes, seed 999, 50 users:

| Policy | Reward | Jain fairness | Outage (/50) | Throughput [bits/s/Hz] |
|---|---|---|---|---|
| Random | −82.2 ± 17.0 | 0.331 ± 0.046 | 33.7 ± 3.3 | 33.95 ± 4.75 |
| **Max-SINR (no DRL)** | **−19.3 ± 17.5** | **0.700 ± 0.027** | **1.0 ± 0.9** | **76.18 ± 3.57** |
| DQN | −34.1 ± 13.8 | 0.607 ± 0.045 | 9.8 ± 3.3 | 66.99 ± 5.39 |

The DQN clearly beats random but **does not beat the closed-form max-SINR baseline**
— it agrees with max-SINR's choice for 92% of users, and the disagreements are net
losses. This is a genuine result, not a bug: users and the constellation are static
for the whole episode, so the instantaneous best-SINR choice is already close to
optimal for most users most of the time, and the assumed per-user power draw (1 W) is
small relative to the fixed 700 W platform draw — so the battery/fairness trade-off
situations where a learned policy should have an edge are a minority this training
budget (300 episodes, no hyperparameter search) hasn't reliably captured. See
`HAPS_AI_HW_ChannelModel.tex`'s Phase 2 results subsection for the full discussion,
and `docs/PHASE2_ASSOCIATION_PLAN.md` for what was tried (and what fixed two real
bugs along the way) before reaching this number.

## 7. Recommended developer workflow

1. Run `python haps_association_env.py` and sanity-check the printed metrics (SINR
   in a plausible dB range, battery SoC swinging with day/night, no crashes).
2. Run `python train_dqn_association.py`; confirm `dqn_association_results/` is
   populated and the printed eval reward/Jain/outage trend improves over the 300
   episodes (not frozen at an identical value for 100+ consecutive checkpoints —
   that pattern means the policy collapsed to a constant action, as it did twice
   during development; see `docs/PHASE2_ASSOCIATION_PLAN.md`).
3. Run `python eval_baseline_association.py` and compare against Section 6's
   numbers above.
4. If you change the reward, `p_per_user_w`, or `N_USERS`, re-run both 2 and 3 —
   the comparison in Section 6 is only valid for the exact configuration it was
   measured under.
