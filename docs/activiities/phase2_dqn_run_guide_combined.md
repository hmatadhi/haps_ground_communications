# Phase 2 DQN run guide (combined)

This guide reflects the current repository state and the earlier memory notes for the Phase 2 weather-conditioned DQN training workflow.

## Verified repo entry points

The Phase 2 trainer is located at:

- src/drl_dqn/train_dqn_phase2.py
- src/drl_dqn/haps_env.py
- src/drl_dqn/weather_scenario_generator.py
- src/drl_dqn/reward_function.py
- src/drl_dqn/dqn_agent.py

The current repo also contains generated artifacts in:

- dqn_results/
  - dqn_model_phase2.pt
  - dqn_train_log_phase2.csv
  - dqn_weather_log_phase2.csv
  - training_config.json
  - figures/

## Why the Phase 2 DQN exists

The DQN is not optimizing a fixed analytic formula directly. It learns a control policy from a weather-conditioned state vector. This matters because:

- rain and fog change attenuation and outage risk
- visibility affects link quality and LOS reliability
- hour-of-day changes the environment through solar and atmospheric effects
- fairness and outage need a closed-loop control policy rather than a static budget calculation

The equation-based model explains the physics; the DQN learns how to act under variable conditions.

## Weather dimensions used in training

The weather generator in src/drl_dqn/weather_scenario_generator.py samples the following dimensions per episode:

- Rain rate: 0, 2, 5, 10, 20 mm/h
- Visibility: 15, 7.5, 2.5, 0.5 km
- Hour of day: 0-24 h
- Derived values: liquid water, humidity, pressure, temperature

Modes supported by the generator:

- random_mix: default for training
- fixed: repeat one scenario for debugging
- deterministic: cycle through predefined composite profiles

## Standard run

From the repo root, use the project source directory on PYTHONPATH and run the package entry point:

### Linux / macOS

```bash
cd /path/to/haps_ground_communications
export PYTHONPATH=$PWD/src:$PWD/src/models
python -m drl_dqn.train_dqn_phase2
```

### Windows PowerShell

```powershell
cd C:\Github\haps_ground_communications
$env:PYTHONPATH = "C:\Github\haps_ground_communications\src;C:\Github\haps_ground_communications\src\models"
python -m drl_dqn.train_dqn_phase2
```

## Quick smoke test

For a short debug run, edit the configuration in src/drl_dqn/train_dqn_phase2.py to a smaller case such as:

```python
N_UAV, N_USERS, N_CH = 3, 50, 3
EPISODES = 50
```

Then run the same command above. This is the best way to verify that imports, environment setup, and weather sampling are all working before a full run.

## Config used by the verified repo state

The current implementation uses:

```python
N_UAV, N_USERS, N_CH = 3, 200, 3
EPISODES = 400
EVAL_EVERY = 10
EVAL_EPISODES = 8
EVAL_SEED = 999
```

The script creates output directories automatically:

- dqn_results/
- dqn_results/figures
- dqn_results/logs

## Expected outputs

The training script saves the following artifacts:

- dqn_results/dqn_model_phase2.pt
- dqn_results/dqn_train_log_phase2.csv
- dqn_results/dqn_weather_log_phase2.csv
- dqn_results/training_config.json
- dqn_results/figures/5_dqn_phase2_convergence.png
- dqn_results/figures/6_dqn_phase2_reward_by_weather.png
- dqn_results/figures/7_dqn_phase2_weather_coverage.png

The script also prints evaluation statistics for reward, fairness, and outage on a held-out evaluation seed.

## What good training looks like

A healthy first-pass run has:

- evaluation reward that rises early and stabilizes by the end
- fairness that stays close to 1.0 when possible
- outage that no longer worsens materially
- logs and figures created without errors

Stop training once these metrics plateau across several evaluation checkpoints.

## Baseline validation

To claim that the DQN is useful, compare it against a non-learning baseline under identical conditions:

- random policy
- fixed channel / motion policy
- greedy SINR-maximizing policy

Measure:

- average reward
- Jain fairness index
- outage count or served fraction
- throughput if relevant

The DQN should show consistent improvement over the baseline using the same weather and evaluation setup.

## Practical notes

- This is a training script, not a generator. It is meant to be run once to create model and learning artifacts.
- The script is weather-aware and logs per-episode weather state.
- The repo already contains generated artifacts in dqn_results/, so you can inspect them immediately if the run has already been completed.
- If the repo is run from a clean environment, ensure the source directory is included on PYTHONPATH before launching the DQN trainer.

## Summary

The Phase 2 DQN run is the operational layer that follows the physics-driven HAPS/UAV model. The channel model tells us what is happening physically; the DQN learns the policy that decides what to do under changing weather and network conditions.

This is the correct workflow for Phase 2: train the DQN on weather-conditioned episodes, validate the learned policy against baselines, and then use the resulting logs and figures for performance interpretation.
