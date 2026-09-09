# Phase 2 DQN training run guide

This guide covers the weather-aware DQN workflow implemented in `src/drl_dqn/train_dqn_phase2.py`. The goal is to train a policy that adapts to site weather, user load, and channel state rather than relying on a fixed static equation.

## 1. What is being trained

The training stack is:

- `src/drl_dqn/train_dqn_phase2.py` — main training entry point
- `src/drl_dqn/haps_env.py` — HAPS/UAV environment and reward model
- `src/drl_dqn/weather_scenario_generator.py` — episode-level weather sampling
- `src/drl_dqn/dqn_agent.py` — DQN implementation and replay buffer
- `src/generators/generate_phase2_figures.py` — optional figure generation from the trained run

The environment uses a 3-UAV, 200-user, 3-channel setup with a fixed HAPS and a local state representation. The weather state is appended to the observation vector as:

- rain rate (mm/h)
- visibility (km)
- hour of day

This makes the policy learn how the reward changes under different atmospheric conditions instead of assuming a uniform environment.

## 2. Setup

From the repo root:

```bash
cd c:/Github/haps_ground_communications
python -m pip install -r src/requirements.txt
```

If the package is already set up, the actual run is:

```bash
cd c:/Github/haps_ground_communications
python -m drl_dqn.train_dqn_phase2
```

You can also execute the script directly from the folder:

```bash
cd c:/Github/haps_ground_communications/src/drl_dqn
python train_dqn_phase2.py
```

## 3. Training configuration

The script is configured as:

- `N_UAV = 3`
- `N_USERS = 200`
- `N_CH = 3`
- `EPISODES = 400`
- `EVAL_EVERY = 10`
- `EVAL_EPISODES = 8`
- `EVAL_SEED = 999`
- `SEED = 42`
- `max_steps = 50`
- `state_mode = "local"`
- `weather_generator = WeatherScenarioGenerator(mode="random_mix", seed=SEED)`

The environment samples a new weather condition once per episode, and the same weather remains fixed for the full 50-step episode. This matches the timescale of a short operational window and ensures the agent learns from realistic weather variance.

## 4. Weather parameters used in training

The weather generator uses the following realistic ranges:

- rain rate: `[0.0, 2.0, 5.0, 10.0, 20.0]` mm/h
- visibility: `[15.0, 7.5, 2.5, 0.5]` km
- hour of day: uniform in `[0, 24)` hours

Derived weather fields include:

- fog / liquid water content
- pressure
- temperature
- relative humidity
- scenario labels such as `clear_excellent_morning`, `moderate_rain_noon`, `heavy_rain_evening`, and `severe_rain_night`

This gives the policy exposure to both benign and severely degraded propagation states.

## 5. Output artifacts

The script writes the following files under the repo root `dqn_results/` folder:

```text
dqn_results/
  dqn_model_phase2.pt
  dqn_train_log_phase2.csv
  dqn_weather_log_phase2.csv
  training_config.json
  logs/
  figures/
    5_dqn_phase2_convergence.png
    6_dqn_phase2_reward_by_weather.png
    7_dqn_phase2_weather_coverage.png
```

The CSV logs capture:

- reward vs. episode
- fairness
- outage
- rain rate
- visibility
- hour of day
- weather scenario name

The JSON config stores the reproducible training parameters so a run can be repeated exactly.

## 6. Stopping criteria

The run has a hard stopping target of 400 episodes. In practice, the script evaluates every 10 episodes and reports:

- evaluation reward per step
- Jain fairness
- outage count / outage severity

A training run is considered successful when the evaluation reward and fairness have plateaued while outage remains low across several evaluation windows. There is no hidden early-stop branch in the script; the training terminates after the configured 400 episodes unless the user stops it manually.

> **Note:** Sections 7–8 below describe the *intended* validation pattern for
> `train_dqn_phase2.py`'s environment, but no baseline was actually run against it —
> the claims were asserted, not measured. That gap is closed in
> [Section 10](#10-phase-2b-per-user-haps-association-experiment-matches-the-papers-mdp)
> below, for the paper's actual 3-HAPS per-user association MDP (a different, unrelated
> environment from `haps_env.py`/`train_dqn_phase2.py` — see Section 10.1). The measured
> result there: the DQN beats a random baseline but **does not** beat a closed-form
> max-SINR baseline at the current training budget. Read Section 10 before treating
> Sections 7–8's claims as validated for either environment.

## 7. Validation against no-DRL baselines

The evaluation helper inside `train_dqn_phase2.py` runs a held-out evaluation with `agent.eps = 0.0` on a fixed seed (`EVAL_SEED = 999`) for 8 episodes. This is the repo's built-in validation pattern for comparing the DQN against a no-DRL/static policy.

The comparison should be done with the same environment and same weather distribution, but with a baseline policy that uses only static equations or fixed heuristics instead of learned action selection. In practice, the DQN is expected to do better because:

- it reacts to current weather conditions
- it adapts to user distribution and per-step load imbalance
- it balances fairness and outage in real time, instead of applying one fixed rule to every episode

The key validation numbers are the average evaluation reward, fairness, and outage over those held-out episodes.

## 8. Why DQN is better than static equations

Static equation-based controllers are useful for steady-state analysis, but they are not robust to changing conditions. They assume a closed-form operating point and do not learn from repeated environment feedback.

The DQN improves because it directly optimizes the reward signal:

```text
reward = mu * fairness + nu * (1 - load)
```

This reward jointly encourages:

- fair service across users
- good load balancing across UAVs
- lower outage in degraded weather
- policy adaptation under rain, visibility loss, and time-of-day variation

In other words, the DQN is not just solving a fixed geometry problem; it is learning a control policy for a dynamic stochastic network. That is why it outperforms static equation-driven placement or channel-selection logic under realistic weather variation.

## 9. Recommended developer workflow

1. Run the training from the repo root:
   `python -m drl_dqn.train_dqn_phase2`
2. Confirm the `dqn_results/` files are created.
3. Inspect the convergence PNG and weather coverage plot.
4. Compare DQN evaluation metrics with a no-DRL baseline on the same weather mix.
5. If needed, rerun with a different seed or weather mode and compare the trajectory.

This workflow is the intended Phase 2 validation path for the repo and is the cleanest way to verify that the learned controller is truly outperforming the static-equation baseline.

## 10. Phase 2b: Per-user HAPS association experiment (matches the paper's MDP)

### 10.1 What this is, and how it differs from Sections 1–9

Everything above trains on `haps_env.py`: 1 fixed HAPS + 3 *mobile* UAVs choosing
movement/channel, reward = `fairness × served_fraction`. That environment does **not**
match `HAPS_AI_HW_ChannelModel.tex`'s own "Phase 2: DRL for User Association" section,
which specifies: a 3-HAPS equilateral-triangle constellation, each **user** (not UAV)
independently picking which HAPS to associate with, a 12-dim per-user state
(SINR/distance/battery-SoC to each HAPS + weather), and a battery/solar model. Two
pieces that section's reward and battery model depend on already existed in the repo
but were never wired into any environment: `src/drl_dqn/reward_function.py` and
`src/models/battery_model.py`.

This section documents the environment that actually implements that MDP, and the
baseline/DQN comparison the paper's own Motivation section calls for. Full narrative
write-up in `HAPS_AI_HW_ChannelModel.tex`, in dependency order:
- Section III.D — state/policy definitions and the random/max-SINR experiment setup,
  written to stand on its own (no DQN, no forward dependency on Phase 2).
- Section IV.D — the random-vs-max-SINR baseline results only (Table
  `tab:assoc-baseline-results`); this is the closed-form, no-DRL result.
- "Phase 2: DRL for User Association" — adopts III.D's state, trains the DQN, and
  extends IV.D's baseline table with the DQN row (Table `tab:phase2-results`) plus
  the full discussion. Phase 2 cites III.D/IV.D; they do not reference Phase 2's DQN.

Design rationale and the two bugs found/fixed along the way (reward credit assignment,
battery SoC unit conversion): `docs/PHASE2_ASSOCIATION_PLAN.md`.

The stack:

- `src/drl_dqn/haps_association_env.py` — the per-user, 3-HAPS association MDP
- `src/drl_dqn/train_dqn_association.py` — DQN training entry point
- `src/drl_dqn/eval_baseline_association.py` — random / max-SINR / DQN comparison
- `src/drl_dqn/dqn_agent.py` — same DQN as Sections 1–9, plus an added `act_batch()`
  method (batches all users' epsilon-greedy action selection into one forward pass
  per step; `act()` is unchanged and still used by `train_dqn_phase2.py`)
- `src/models/battery_model.py`, `src/drl_dqn/reward_function.py` — reused, not reimplemented

### 10.2 Setup and run commands

Same environment/PYTHONPATH prerequisites as Sections 1–9. From `src/drl_dqn/`:

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

### 10.3 Configuration

`train_dqn_association.py` / `eval_baseline_association.py`:

- `N_USERS = 50` (configurable; smaller than Sections 1–9's 200 because each of the
  24 hourly steps requires one action per user — kept tractable for a shared-network
  DQN without a hyperparameter search)
- `EPISODES = 300`, `EVAL_EVERY = 10`, `EVAL_EPISODES = 8` (mid-training), `SEED = 42`
- `EVAL_SEED = 999`, `N_EVAL_EPISODES = 50` (final baseline comparison — more than the
  8 used mid-training, for stable statistics)
- `max_steps = 24` — one episode = one simulated day, one step = one hour, so the
  diurnal battery/solar cycle is actually exercised (Sections 1–9's environment has
  no battery model at all)
- 3-HAPS constellation: 65 km equilateral spacing, from
  `channel_model.haps_constellation_geometry()` (the same function behind
  `HAPS_AI_HW_ChannelModel.tex` Table A.3 / the multi-HAPS interference figures)
- Per-episode, held fixed for the whole episode: user positions (uniform, 0–100 km
  radius from the serving HAPS's nadir), initial per-HAPS battery SoC (`U(30, 100)%`)
- Per-episode, resampled: weather (`WeatherScenarioGenerator`, `random_mix` mode) —
  same generator as Sections 1–9

### 10.4 Output artifacts

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
answer to "is the DQN better than plain mathematical evaluation" for this MDP — copies
of the same two figures are embedded in the paper
(`HAPS_AI_HW_ChannelModel.tex`, Section IV.D).

### 10.5 Measured result (do not re-assert Section 8's claim for this environment either)

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
`HAPS_AI_HW_ChannelModel.tex` Section IV.D for the full discussion, and
`docs/PHASE2_ASSOCIATION_PLAN.md` for what was tried (and what fixed two real bugs
along the way) before reaching this number.

### 10.6 Recommended developer workflow

1. Run `python haps_association_env.py` and sanity-check the printed metrics (SINR
   in a plausible dB range, battery SoC swinging with day/night, no crashes).
2. Run `python train_dqn_association.py`; confirm `dqn_association_results/` is populated
   and the printed eval reward/Jain/outage trend improves over the 300 episodes (not
   frozen at an identical value for 100+ consecutive checkpoints — that pattern means
   the policy collapsed to a constant action, as it did twice during development; see
   `docs/PHASE2_ASSOCIATION_PLAN.md`).
3. Run `python eval_baseline_association.py` and compare against Section 10.5's numbers.
4. If you change the reward, `p_per_user_w`, or `N_USERS`, re-run both 2 and 3 — the
   comparison in Section 10.5 is only valid for the exact configuration it was measured
   under.
