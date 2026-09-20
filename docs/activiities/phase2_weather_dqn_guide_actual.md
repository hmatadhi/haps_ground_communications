# Phase 2 DQN run guide (verified repo state)

This version reflects the current repository state as of the verified Phase 2 DQN implementation and generated outputs.

## Repository state

The active training script is:

- src/drl_dqn/train_dqn_phase2.py

The supporting modules are:

- src/drl_dqn/dqn_agent.py
- src/drl_dqn/haps_env.py
- src/drl_dqn/weather_scenario_generator.py
- src/drl_dqn/reward_function.py

The repo already contains generated artifacts in:

- dqn_results/
  - dqn_model_phase2.pt
  - dqn_train_log_phase2.csv
  - dqn_weather_log_phase2.csv
  - training_config.json
  - figures/

## Weather generator behavior

The weather generator produces per-episode weather using these ranges:

- rain_mm_h: 0.0, 2.0, 5.0, 10.0, 20.0
- visibility_km: 15.0, 7.5, 2.5, 0.5
- hour_of_day: 0.0 to 24.0

The default mode is `random_mix`, which samples a weather state at the start of each episode and keeps it fixed during that episode.

## Verified run command

From the repo root, the working command is:

```bash
cd /path/to/haps_ground_communications
export PYTHONPATH=$PWD/src:$PWD/src/models
python -m drl_dqn.train_dqn_phase2
```

For Windows PowerShell:

```powershell
cd C:\Github\haps_ground_communications
$env:PYTHONPATH = "C:\Github\haps_ground_communications\src;C:\Github\haps_ground_communications\src\models"
python -m drl_dqn.train_dqn_phase2
```

## Verified default config

The training script currently configures:

```python
N_UAV, N_USERS, N_CH = 3, 200, 3
EPISODES = 400
EVAL_EVERY = 10
EVAL_EPISODES = 8
EVAL_SEED = 999
```

It creates output folders automatically under the repo root:

- dqn_results/
- dqn_results/figures/
- dqn_results/logs/

## Generated outputs

The script produces:

- dqn_results/dqn_model_phase2.pt
- dqn_results/dqn_train_log_phase2.csv
- dqn_results/dqn_weather_log_phase2.csv
- dqn_results/training_config.json
- dqn_results/figures/5_dqn_phase2_convergence.png
- dqn_results/figures/6_dqn_phase2_reward_by_weather.png
- dqn_results/figures/7_dqn_phase2_weather_coverage.png

## Interpretation

The training logs capture:

- evaluation reward
- Jain fairness index
- outage count
- episode weather name and parameters

The plots show:

- convergence of reward, fairness, and outage over training
- reward vs weather, colored by rain rate
- weather coverage across the sampled episodes

## Practical checklist

1. Set PYTHONPATH to include src and src/models.
2. Run the trainer from the repo root.
3. Check dqn_results/ for new logs and plot files.
4. Validate that reward improves and fairness/outage stabilize.
5. Compare the learned policy against a baseline if you plan to claim an advantage.

## Bottom line

The Phase 2 DQN workflow is a closed-loop learning stage layered on top of the propagation and channel model. The environment and weather generator create realistic operating states, while the DQN learns a policy that adapts to those states rather than relying on a static equation-based decision rule.
