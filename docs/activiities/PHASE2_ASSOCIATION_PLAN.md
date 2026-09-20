# Build the paper's actual Phase 2 model (3-HAPS per-user association) + a mathematical baseline

## Context

The user trained a DQN (`dqn_results/`) using `src/drl_dqn/haps_env.py` + `train_dqn_phase2.py`. That environment solves a *different* problem than the paper documents: 1 fixed HAPS + 3 mobile UAVs choosing movement/channel, reward = `fairness × served_fraction`. It has no battery model and no 3-HAPS constellation.

The paper's own **Section 2 (Network Topology)** and **"Phase 2: DRL for User Association"** section specify a different MDP:
- 3 HAPS in an equilateral triangle (65 km spacing, 1 serving + 2 interferers) + 1 static UAV relay (unmodeled, deferred).
- Each **user** (not UAV) independently picks which HAPS to associate with: action ∈ {HAPS1, HAPS2, HAPS3}.
- 12-dim per-user state: `[SINR_1,2,3, dist_1,2,3, SoC_1,2,3, rain, visibility, hour]`.
- Reward: `0.5·throughput + 0.3·Jain − 0.2·energy_penalty + outage/battery penalties`, computed on **linear** SINR.
- A battery/solar model (diurnal, weather-independent) drives per-HAPS SoC.

Two of the three needed pieces already exist in the repo but are **never imported anywhere**:
- [`src/drl_dqn/reward_function.py`](../src/drl_dqn/reward_function.py) — `compute_network_reward()` implements the exact reward formula above, unit-tested.
- [`src/models/battery_model.py`](../src/models/battery_model.py) — `HAPSBatteryModel` implements the diurnal solar/battery model, unit-tested. Also has `feeder_link_rain_effect_on_capacity()` for rain's effect on the 38 GHz feeder (backhaul), separate from the 2 GHz service-link SINR.
- What's missing: the **environment** that ties these together into the per-user MDP, using the existing 3-HAPS constellation geometry (`haps_constellation_geometry`, `haps_a2g_pathloss_db` in [`src/models/channel_model.py`](../src/models/channel_model.py)).

Goal: build that environment, retrain the DQN on it, and build the "plain mathematical evaluation" baseline the paper's own Motivation section names — "a simple always-pick-max-SINR rule" — so the DQN's advantage (or lack of one) can be measured, not asserted.

## Design decisions (flagged explicitly — not fully pinned down by the paper text)

- **User mobility**: none. Users get fixed random positions at episode reset (uniform in radius/angle around the serving HAPS's nadir, 0–100 km, matching the `r_k,p ∈ [0,100] km` state bound). Since HAPS and users are both static, each user's raw SINR-to-each-HAPS is constant for the whole episode — only battery/weather evolve. This matches the paper's state vector, which has no velocity term.
- **Episode = 1 simulated day**, `max_steps=24`, one step = one hour, `hour_of_day = (weather.hour_of_day_at_reset + t) mod 24`. This is what makes the diurnal battery model (and its low-SoC penalty) actually exercised, vs. the earlier 50-step/no-battery design.
- **Per-user power draw**: `P_PER_USER_W = 1.0 W` (ASSUMED — paper defines `P_{k,user}` symbolically but gives no value). Aggregated per HAPS as `count_assigned × P_PER_USER_W` and fed into `HAPSBatteryModel.update_battery_soc`.
- **Rain → feeder capacity, not service SINR**: per paper text ("rainfall & visibility for feeder margin planning"), rain does not touch the 2 GHz user-facing SINR. Instead, `feeder_link_rain_effect_on_capacity(rain_mm_h)` gives a dB loss converted to a capacity fraction (1.0 at no rain) that scales the final network reward — representing a backhaul bottleneck. This is an explicit modeling choice since the paper doesn't give an exact coupling formula.
- **Initial battery SoC**: randomized U(30%, 100%) per HAPS per episode (not fixed at 100%), so the low-battery penalty and load-balancing behavior actually get exercised during training/eval instead of rarely triggering.
- **N_USERS**: default 50 for the new training script (vs. 200 in the old unrelated script) — each of the `max_steps=24` steps requires one action per user, so smaller N keeps training tractable. Configurable.
- Scintillation and the UAV relay are correctly left out — the paper explicitly defers both.

## Outcome (post-implementation — this section documents what actually happened, not just what was planned)

Two things in the plan above turned out to be wrong once real numbers came back, both now fixed and written up in the paper as "Error 5" and "Error 6" (`HAPS_AI_HW_ChannelModel.tex`, Critical Implementation Fixes):

- **Reward was NOT left as a flat broadcast.** Using `reward_function.py`'s own flat `-100 × count` outage penalty produced reward magnitudes in the thousands (unbounded in `n_users`), which swamped any single user's own action and collapsed training into a constant always-pick-HAPS-1 policy — verified by inspecting the learned policy's action distribution directly, not just the training curve. Switching to the paper's own fractional two-tier penalty (`-100 × fraction`) fixed the scale, but the policy *still* collapsed, for a second, more fundamental reason: broadcasting one fully-aggregated scalar reward to all 50 users' transitions buries any single user's own contribution under the other 49 users' noise. Fix: decompose `L_agg` and the outage penalties (both literally sums/fractions over users in the paper's own formula) into a genuine per-user share; `J_fair` and `P_eng` stay a shared network-level term since they aren't decomposable. Reward totals are unchanged — only attribution for learning.
- **`battery_model.py`'s `update_battery_soc` has a units bug**: it adds `ΔE_Wh / capacity` (a dimensionless fraction) directly onto a percentage, missing a `×100`. This under-scaled every SoC update by 100×, so battery state was pinned near its initial value regardless of policy — silently disabling the entire energy/battery term of the reward. Fixed (added the `×100`), and switched the env to `battery_capacity_wh=12,000` matching the paper's own Table value (the module's own default, 1000 Wh, produced implausible full-charge/full-drain swings within a single simulated hour once the units bug was fixed).

**Final measured result** (50 held-out episodes, seed 999): DQN reward `-34.1±13.8` sits between random (`-82.2±17.0`) and the closed-form max-SINR baseline (`-19.3±17.5`) — the DQN clearly beats random but does **not** beat plain mathematical evaluation on this MDP/training budget (300 episodes). The learned policy agrees with max-SINR on 92% of users; disagreements are net losses, not gains. This is reported honestly in the paper (`sec:phase2-results`) as a real finding, not smoothed over — likely because users/geometry are static per episode (so instantaneous best-SINR is already close to optimal for most users most of the time) and the assumed per-user power draw (1 W) is small relative to the fixed 700 W platform draw, so the battery/fairness trade-offs where DRL should have an edge are a minority of cases a modest training budget hasn't reliably captured. Closing that gap is future work.

## Implementation

**1. New environment** — `src/drl_dqn/haps_association_env.py` (mirrors the structure/style of `haps_env.py`):
  - `HAPSAssociationEnv(n_users=50, n_haps=3, constellation_spacing_km=65.0, service_radius_km=100.0, env="urban", max_steps=24, weather_generator=None, seed=0, p_per_user_w=1.0, soc_init_range=(30.0,100.0))`
  - `reset()`: sample user (x,y) positions once (fixed for episode); sample weather via `weather_generator.sample()`; sample per-HAPS initial SoC; compute and cache the static `(n_users, 3)` SINR-dB matrix once (reuses `haps_constellation_geometry` + `haps_a2g_pathloss_db` from `channel_model.py`, computing signal/interference directly rather than `multi_node_sinr_db_spatial`, since that helper hardcodes which node is "serving" — here every user needs SINR against all 3 candidates).
  - `step(actions)`: gather each user's SINR to their chosen HAPS from the cached matrix; update 3 SoC values via `HAPSBatteryModel.update_battery_soc`; call `reward_function.compute_network_reward(chosen_sinr_db, soc_array)` unmodified; scale by the rain/feeder capacity fraction; build next per-user state (SINR/dist normalized + updated SoC + weather); advance simulated hour.
  - State dim = 12, `n_actions=3`, matching the paper exactly.
  - Include an `if __name__ == "__main__":` smoke test (random actions, print shapes/metrics), same pattern as `haps_env.py`'s own smoke test.

**2. Small reusable addition** — `DQNAgent.act_batch(states)` in [`src/drl_dqn/dqn_agent.py`](../src/drl_dqn/dqn_agent.py): one batched forward pass for all N users' epsilon-greedy action selection per step, instead of N separate `act()` calls. Additive only — existing `act()` stays untouched so `train_dqn_phase2.py` is unaffected.

**3. New training script** — `src/drl_dqn/train_dqn_association.py`, structurally copied from `train_dqn_phase2.py` (same episode/eval-loop shape, same CSV/JSON/figure output pattern) but wired to `HAPSAssociationEnv` and `act_batch`. Writes to a new `dqn_association_results/` folder (kept separate from the old `dqn_results/` — that run stays as-is since it answers a different question).
  - `N_USERS=50, EPISODES=300, EVAL_EVERY=10, EVAL_EPISODES=8, EVAL_SEED=999, SEED=42, max_steps=24`.

**4. Baseline comparison script** — `src/drl_dqn/eval_baseline_association.py`:
  - Builds the *identical* eval environment the training script's `evaluate()` uses (same `EVAL_SEED=999`, same weather generator construction) for three policies over N=50 eval episodes each:
    - **Max-SINR** (the paper's own named "naive" baseline): each user picks `argmax_p SINR_k,p` — no learning, pure closed-form.
    - **Random**: sanity floor.
    - **DQN**: loads `dqn_association_results/dqn_model_association.pt`, `agent.eps=0`.
  - Logs mean ± std of reward, Jain index, throughput, outage count, mean battery SoC across the eval episodes for all three, to a CSV, plus a bar-chart figure, plus a printed summary table.

## Verification

1. Run the new env's smoke test directly to confirm no crashes and sane value ranges (SINR in a plausible dB range, SoC moving with day/night, reward finite).
2. Do a short smoke run of `train_dqn_association.py` (few episodes) to confirm the train/eval loop and logging work end-to-end before committing to the full 300-episode run.
3. Run the full training (background — this is the actual compute step) and confirm `dqn_association_results/` outputs are produced.
4. Run `eval_baseline_association.py` and report the actual max-SINR vs. random vs. DQN numbers — this is the concrete evidence for "is DQN better than plain mathematical evaluation," replacing the current assertion-only guide text.
