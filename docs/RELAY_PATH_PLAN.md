# Add HAPS→Gateway→UE Relay Analysis (Phase 1 + Phase 2)

## Context

The repo currently models two independent radio links from the HAPS: the **service link** (HAPS→UE, 2 GHz) and the **feeder/backhaul link** (HAPS→Gateway, 38 GHz), both computed with `haps_a2g_pathloss_db()` in [src/models/channel_model.py](../src/models/channel_model.py). There is no model of a **relay path** where a UE is served indirectly — HAPS→Gateway (feeder) then Gateway→UE (access) — even though the paper's topology anticipates a relay concept (currently only a *different*, unmodeled "UAV relay" is referenced/deferred in the tex and in `haps_association_env.py`).

The goal: add a genuinely new two-hop relay path (**HAPS→Gateway→UE**) to both:
- **Phase 1** — the link-budget/channel-model analysis, tables and figures feeding `HAPS_AI_HW_ChannelModel.tex`.
- **Phase 2** — the DQN per-user association RL (`haps_association_env.py`), as a new routing option alongside direct HAPS association.

Design decisions already confirmed with the user:
- **Gateway→UE hop**: reuses the same 2 GHz service band and the same transmit-power/pathloss convention already used for HAPS→UE (i.e. `haps_a2g_pathloss_db()`, just with the Gateway's altitude instead of the HAPS's).
- **Two-hop combining**: **decode-and-forward** — end-to-end rate is the bottleneck of the two hops, `C_relay = min(C_feeder, C_access)`, since the Gateway is a real network node (not a bent-pipe repeater like the HAPS-feeder assumption).
- **Scope**: implement both Phase 1 and Phase 2 now.

## Phase 1: Channel model + tables/figures

### 1. `src/models/channel_model.py` — new relay primitives

Add near the other link-budget helpers (after `feeder_link_loss_with_scintillation`, ~L537):

- `P_TX_GATEWAY_DBM = P_TX_HAPS_DBM` — module constant; docstring notes this is the "same band/power convention as HAPS→UE" assumption the user confirmed, so it's trivially easy to change later.
- `relay_two_hop_capacity_bps_hz(feeder_dist_km, feeder_elevation_deg, gw_ue_dist_m, p_tx_gw_dbm=P_TX_GATEWAY_DBM, f_gw_ue_hz=F_HAPS_MHZ*1e6, h_gateway_m=GATEWAY_ALT_M, h_user_m=1.5, p_time_percent=1.0, include_scint=True, noise_dbm=NOISE_DBM)`:
  - Hop 1 (feeder, HAPS→Gateway): reuse `feeder_link_loss_with_scintillation()` → loss_db → `rx_power_dbm(P_TX_HAPS_DBM, loss_db)` → `sinr_db()` → `C_feeder = log2(1+SINR_feeder)`.
  - Hop 2 (access, Gateway→UE): reuse `haps_a2g_pathloss_db(gw_ue_dist_m, h_gateway_m, f_hz=f_gw_ue_hz, h_user_m=h_user_m)` (same function already used for the service link, just called with the Gateway's altitude instead of the HAPS's) → `rx_power_dbm(p_tx_gw_dbm, ...)` → `sinr_db()` → `C_access = log2(1+SINR_access)`.
  - Combine: `C_relay = min(C_feeder, C_access)` (decode-and-forward).
  - Return a dict with both hop SINRs/capacities and `C_relay`, so callers (tables, Phase 2 env) get full visibility, not just the bottleneck number.
  - Docstring must flag the modeling simplification: same-band reuse on both the service and Gateway→UE hops implies an implicit orthogonal-resource-allocation assumption (no self-interference modeled) — note this as a known limitation, consistent with how other simplifications are documented in this file (e.g. `env` unused in `haps_a2g_pathloss_db`).

### 2. `src/generators/generate_relay_table.py` — new generator script

Modeled on [src/generators/generate_pathloss_table.py](../src/generators/generate_pathloss_table.py) (which already computes service vs. feeder path loss side by side using the same distance-range convention: service 0–100 km, feeder 0–0.5 km). New script:
- Sweeps feeder distance (0–0.5 km, matching existing `DISTANCES_FEEDER_KM`) × Gateway→UE access distance (0–100 km, matching existing `DISTANCES_SERVICE_KM`) using `relay_two_hop_capacity_bps_hz()`.
- Also computes the direct HAPS→UE capacity at the same access distances (`haps_a2g_pathloss_db` + `sinr_db`, already the pattern in `generate_pathloss_table.py`) so the table can show **direct vs. relay** throughput side by side, and (optionally) a rain-derated relay case using `feeder_link_rain_effect_on_capacity()` from `src/models/battery_model.py` (already used the same way in `haps_association_env.step()`).
- Exports CSV to `appendix_data/` and a LaTeX table to `appendix_tables/`, following the exact export pattern in `generate_pathloss_table.py` (lines 111–150).

### 3. Paper/doc updates
- Add a short new subsection to `HAPS_AI_HW_ChannelModel.tex` (Section IV area, near the existing feeder-link subsection) describing the two-hop DF relay model, its parameters, and the same-band-reuse simplification; include the new table via `appendix_tables.tex`.
- Add the new script to `src/generate_all_wsl.sh` and mention it in `docs/PHASE1_RUN_GUIDE.md`.

## Phase 2: DQN association env

### 4. `src/drl_dqn/haps_association_env.py` — relay as a routing action

- **Gateway placement**: one Gateway per HAPS, colocated at each HAPS's ground nadir point (consistent with the existing short 10–500 m feeder-distance convention in `generate_pathloss_table.py`). This means the existing per-user horizontal distance array `dist_m` (`_compute_static_sinr_and_distance`, L126–128) can be reused directly for the Gateway→UE hop distance — no new geometry needed.
- **Action space**: expand from 3 (direct to HAPS 0/1/2) to **6** actions — `{0,1,2}` = direct to HAPS *p*, `{3,4,5}` = relay via HAPS *p*'s Gateway. Symmetric with the existing per-HAPS loop structure (`NODE_KEYS`, L56), so `n_haps=3` stays put and `n_actions` becomes `2 * n_haps`.
- **New precompute** in `_compute_static_sinr_and_distance()` (or a new `_compute_relay_capacity()` called from `reset()`): for each user × HAPS, compute `C_access[u,p]` via `haps_a2g_pathloss_db(dist_m[:,p], GATEWAY_ALT_M, ...)` (Gateway altitude instead of HAPS altitude), and `C_feeder[p]` via `feeder_link_loss_with_scintillation()` at the fixed near-zero feeder distance/elevation (same convention as the Phase 1 table). `C_relay[u,p] = min(C_feeder[p], C_access[u,p])`.
- **State**: extend `state_dim` from 12 → 15, adding 3 normalized relay-capacity (or relay-SINR-equivalent) features per HAPS, following the same clip/normalize pattern as SINR/dist/SoC (L158–160).
- **Reward** (`step()`, L170–236): for users whose action ≥ 3 (relay), replace `chosen_sinr_db`-based throughput with the precomputed `C_relay[u,p]`; derive an "effective SINR" `2**C_relay - 1` so the existing Jain-fairness helper (`compute_jain_fairness_index`, unchanged) keeps working on a single unified SINR-equivalent array across both direct and relay users. Keep the existing rain→feeder-capacity de-rate (`feeder_link_rain_effect_on_capacity`, L214-217) applied uniformly (all traffic still ultimately needs the feeder backhaul, direct or relay) — this is unchanged.
- Battery/energy: no change — relay adds no new battery draw in this pass (Gateway assumed grid-powered, no `HAPSBatteryModel` needed for it); `p_per_user_w` load still attributed to the serving HAPS regardless of direct/relay choice.
- Update the module docstring (L1–39) to remove the now-inaccurate note that a relay path is unmodeled/deferred — replace with a description of the Gateway-relay design (careful to keep noting the *separate*, still-unmodeled UAV-relay concept from the paper, since that's a different thing).

### 5. `src/drl_dqn/eval_baseline_association.py`
Extend the max-SINR/max-capacity baseline to compare across all 6 actions (direct + relay) instead of 3, so the DQN-vs-baseline comparison stays fair.

### 6. Config / docs
- `dqn_association_results/training_config.json` is written from `env.state_dim`/`env.n_actions` by `train_dqn_association.py` — no manual edit needed, but note that old results in `dqn_association_results/` are for the 3-action/12-dim model and are not shape-compatible; retraining from scratch is required.
- Update `docs/activiities/PHASE2_ASSOCIATION_PLAN.md` to document the new relay design, replacing the current explicit "relay deferred" notes.

## Verification
- Phase 1: run `python src/generators/generate_relay_table.py` and inspect the generated CSV/LaTeX for sane numbers (relay capacity ≤ min of the two hop capacities; direct-vs-relay crossover behaves sensibly, e.g. relay wins when direct HAPS→UE distance is large but access-from-Gateway distance is short).
- Phase 2: run `python src/drl_dqn/haps_association_env.py` (existing `__main__` smoke test) after the edit — confirm it prints `n_actions=6 state_dim=15` and runs 24 steps without error; then run a short `train_dqn_association.py` (few episodes) to confirm training loop works end-to-end with the new action/state dims before doing a full 300-episode retrain.

## Implementation status (as of this pass)
- [x] `channel_model.py`: added `GATEWAY_ALT_M`, `P_TX_GATEWAY_DBM`, `relay_two_hop_capacity_bps_hz()`
- [x] `generate_relay_table.py`: created, verified output looks sane
- [x] `generate_pathloss_table.py`: deduplicated `GATEWAY_ALT_M` to import from channel_model
- [x] `generate_all_wsl.sh` / `PHASE1_RUN_GUIDE.md`: new script wired into pipeline
- [x] `appendix_tables.tex`: new relay subsection + table include added
- [x] `haps_association_env.py`: action space 3→6, state_dim 12→15, reward updated for relay users; smoke test passes (`n_actions=6 state_dim=15`, 24 steps)
- [x] `eval_baseline_association.py`: baseline policy extended to compare all 6 actions
- [ ] `docs/activiities/PHASE2_ASSOCIATION_PLAN.md`: not yet updated to reflect the new relay design
- [ ] `HAPS_AI_HW_ChannelModel.tex`: relay subsection prose not yet added (only appendix table wired in)
- [ ] End-to-end `train_dqn_association.py` smoke test with the new 6-action/15-dim env not yet run to completion
- [ ] Old `dqn_association_results/` (3-action/12-dim) not yet retrained against the new env
