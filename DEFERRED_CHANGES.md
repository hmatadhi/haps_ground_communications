# Deferred Changes: Code, Figures, Results and Summary

Purpose: items where the paper text is already corrected but the code, figures, tables, results or summary still reflect the old values. These are handled together at the end, not one by one, because a single code change can move several results.

Status key: `[ ]` open, `[x]` done and verified end to end.

## Rain attenuation (checklist 1.1)

Paper text is done: Eq. (2) coefficients, intro rain figure, Eq. (3) text.

- [!] **D1.1a (updated after investigation): the real pipeline uses the wrong P.618 convention.** `src/lstm/train_lstm.py:42–58` computes the rain loss as `itur` P.618 with **R001 = the hourly rain rate** (p = 0.01 %). P.618 expects R0.01, the rate exceeded 0.01 % of the time, so each hour's rate is treated as the extreme climate. This inflates the attenuation (10 mm/h gives about 53 dB at 11.3°, against about 13 dB for the physical hourly path). The same function gives the **LSTM training target** and the **DQN rain loss** (`real_episode_env.py`, via `rain_att_db`). So the DQN results were produced with the inflated rain loss, and the LSTM target is also inflated.
  - **Done so far:** `src/models/battery_model.py` `feeder_link_rain_effect_on_capacity` now uses the stated P.618 slant-path model: γ_R = 0.3923·R^0.8687 dB/km (P.838, 89.86°), rain height 5.278 km (P.839, Delhi), L_s = (h_R − 0.05)/sin θ, reduction factor r = 1/(1 + 0.78√(L_G γ) − 0.38(1 − e^(−2L_G))), A = γ·L_s·r. Values: 13.3 dB at 10 mm/h, 27.7 dB at 25 mm/h. This edit affects only the fallback path in `haps_association_env.py`; the real pipeline does not use it.
  - **Retrain run (5 seeds, `run_multiseed.py`):** DQN reward −4.25 ± 1.61, Jain 0.097, outage 0.0, SoC 59.9; max-SINR reward −14.5, Jain 0.696, outage 0.87. These differ from the paper's numbers, although the real pipeline does not use the edited function. The cause (run variability, or an earlier code state) is **not yet established**; check before quoting. Previous outputs are backed up in WSL `~/dqn_backup_before_P618/`.
  - `compare_baselines.py` reran with an unchanged max-SINR (−16.5) and a single-model DQN (−5.66, Jain 0.228). It loads `dqn_real.pt`, which was trained for 300 episodes.
  - **Decision needed (scope has grown):** to fix the rain loss in the real pipeline, change `train_lstm.rain_path_attenuation_db` to the P.618 hourly method above, then (1) recompute the LSTM targets, (2) retrain the LSTM and regenerate the 2026 validation table and forecast figure, (3) rebuild the episodes, (4) retrain the DQN and rerun the baselines, and (5) update every DQN, LSTM and rain number in the paper. This is a larger batch than option 1 as stated. Confirm before I start.
  - **Progress (approved, "yes"):**
    1. `src/lstm/train_lstm.py`: label replaced with the P.618 hourly method at the **gateway geometry (89.86°)**, same constants as `battery_model.py` (the paper's text currently says 11.3°; change it when the text is batched). The `itur` call and its cache are removed. Label check: max 27.9 dB at 25.2 mm/h, mean 0.20 dB.
    2. Retrained: `train_forward_lstm.py` (2023-only, for 2024 forecasts), `train_final_lstm.py` (2023–2025, for 2026), `export_lstm_forecasts.py`, `verify_2026.py`.
    3. **New 2026 validation (MAE / RMSE, dB), LSTM vs persistence:** +1 h 0.196 / 0.645 vs 0.124 / 0.530 (persistence better); +2 h 0.273 / 0.862 vs 0.205 / 0.750 (persistence better); +3 h 0.313 / 0.963 vs 0.263 / 0.901 (persistence better); +4 h 0.331 / 0.996 vs 0.304 / 1.020 (RMSE better for LSTM); +5 h 0.337 / 1.003 vs 0.337 / 1.108 (MAE tied, RMSE better); +6 h 0.347 / 1.017 vs 0.362 / 1.171 (LSTM better on both). **The paper's claim "more accurate than persistence at four to six hours" must change to "at five to six hours (MAE) and four to six hours (RMSE)".** The old table (tab:lstm-2026) and abstract need replacing. Rain-hours: LSTM worse at all horizons (regime:rain +1 h MAE 0.71 vs 0.51).
    4. `build_real_episodes.py` rebuilt; `train_dqn_real.py` set to **400 episodes** (matches the paper and `run_multiseed.py`); then `run_multiseed.py` and `compare_baselines.py` rerun (background job; logs in WSL `~/step_*.log`).
    - Figure `lstm_forecast_2026.png` and the rain-attenuation figures are **not yet regenerated** (figures batch at the end).
  - Original note (superseded):  `battery_model.py:144–173` computes A = k·R^α (dB/km) × 66.3 km (a 102 km slant path × a fixed 0.65 factor). Rain occupies only a few km of the path, so this overstates the loss. With the itur coefficients (k ≈ 0.400, α ≈ 0.881) it gives about 200 dB at 10 mm/h, which would make the DQN permanently in outage during rain. Changing only the coefficients is therefore wrong. **Decision needed:** replace the path model with the P.618 slant-path attenuation (rain-height and reduction-factor based, as in itur) and define the per-hour rain input. Until then, the DQN retrain (D1.1c) is blocked. (Original note follows.) `src/models/battery_model.py:157–159` sets k = 0.0315, α = 0.921 at 38 GHz. `feeder_link_rain_effect_on_capacity` feeds `src/drl_dqn/haps_association_env.py:304`. Decide the new values (itur: k ≈ 0.400, α ≈ 0.881) and whether the DQN is retrained.
- [ ] **D1.1b Relay table.** `src/generators/generate_relay_table.py:68` uses the same function. Regenerate the relay comparison table and check the Figure 12 caption numbers (+29.3 dB at nadir, 45 km / 60 km crossings).
- [ ] **D1.1c DQN results.** If D1.1a changes the rain loss, rerun the training and the multi-seed evaluation (`src/drl_dqn/run_multiseed.py`, `train_dqn_real.py`, `compare_baselines.py`). Update Tables (policy comparison, seed statistics, paired differences), the Results text, the abstract, the Summary and the Conclusion.
- [ ] **D1.1d Atmospheric-loss plot.** `src/plots/atmospheric_losses_simple.py:39–47` uses α = 0.921 with different k values. Regenerate `figures/fig_atm_loss_nominal_frequency.png` and check its caption and the "Atmospheric loss vs frequency" observations.
- [ ] **D1.1e Check scripts.** `src/lstm/check_rain_attenuation.py` and `src/lstm/analyze_parameters.py` still compare against the old 5.9 / 15.2 dB example and k = 0.0315. Update their reference values.
- [ ] **D1.1f Feasibility claim.** Eq. (3) text says the path attenuation is evaluated "in the link-budget analysis rather than here", but no such analysis exists. Needs Delhi R0.01 from ITU-R P.837 (not the 10 or 25 mm/h scenario used in the earlier check, which overstates the rain climate). Then either add the P.618 path analysis (new subsection, code, abstract and Conclusion updated) or soften the 38 GHz feasibility wording in the intro, Section III.B and the Summary.

## Related items from the checklist (to review at the same time)

- [ ] **D1.2 Gateway interference** (checklist 1.2): the "−43 dB below noise" conclusion and the noise-limited claim in the Summary, Section III.B and Conclusion. Depends on the link-budget code in `src/models/channel_model.py`.
  - Recomputed from the paper's own numbers (equal antenna gains for desired and interferer, FSPL only): desired −53.5 dBm, interferer at 68 km slant −64.2 dBm, noise −100 dBm → SNR 46.5 dB, INR 35.8 dB, **SIR ≈ 10.7 dB**. The gateway is therefore interference-limited, not noise-limited, unless the interferers are modelled with a directional pattern that the paper does not describe.
  - Also reconcile the "+38 dB" backhaul SINR (line ~986) with the SIR above, and the 38 GHz "−43 dB" statement (line ~986) and the Summary "approximately constant at +38 dB" (line ~1306).
  - **Stated assumption (agreed with the author, to confirm with professor/TA):** each HAPS steers its main beam at its own service area. The gateway lies in the serving HAPS's beam, so an interferer illuminates the gateway only through its sidelobes. The interferer gain toward the gateway is therefore the sidelobe gain, not the 13.8 dBi main-beam gain.
  - With sidelobe gain 0 dBi (placeholder; not in the paper) and two interferers: interference ≈ −75.0 dBm, **SIR ≈ 21.4 dB**, SINR ≈ 21.4 dB before atmospheric losses. The backhaul is then still interference-affected but no longer at the "+38 dB" level, so the Summary's "+38 dB, noise-limited" statement must change.
  - Still to decide: the sidelobe value (cite a pattern, e.g. ITU-R F.699/F.1245-style envelope, or state it as an assumption) and whether the gateway's own gain toward the interferers is also relevant.
  - Action items when we batch: state the beam-steering assumption in Section III.B; replace "−43 dB below noise" with the sidelobe-based figure; update the +38 dB statements (line ~986, Summary ~1306, Conclusion).
- [ ] **D1.3 Scintillation model** (checklist 1.3): one model across code, figures (`figures/9a`, `9b`, `10b`, `11a–d`), the Summary margins (2–4 dB vs 7.6–13.1 dB vs 10.53 dB) and the Eq. (scint_fade) label.
  - `itur` P.618 results (Delhi, D=1 m, η=0.5): 2.1 GHz at 30°: 0.09 dB (0.01 %), 0.04 dB (1 %); 2.1 GHz at 60°: 0.05 dB (0.01 %). 38 GHz at 11.3°: 1.49 dB (0.01 %), 0.62 dB (1 %); 38 GHz at 30°: 0.47 dB (0.01 %).
  - None of the paper's ranges match. The S-band 2.6–4.7 dB is about 50× too large. The 38 GHz values (2–4 dB, 7.6–13.1 dB, 10.53 dB) are inconsistent with each other and with `itur`.
  - Decision needed: use `itur` P.618 throughout (recommended), and retire the custom Eq. (scint_fade) fit at `src/models/channel_model.py:449`. Figures 9a, 9b, 10b and 11a–d must be regenerated, and the static fading values used in the DQN (3.65 dB service, 10.53 dB backhaul at p = 1 %, lines ~1169–1170) and in the Summary must be recomputed from the `itur` values.
  - Also the paper's antenna diameter (1 m) and efficiency (η=0.5) must be stated, because they set the fade.
- [ ] **D1.4 Beamwidths** (checklist 1.4): the 3.2° and 0.2° figures in Section III.B.
  - Using θ₃dB ≈ 70λ/D with D = 1 m: 2.1 GHz → 10.0°, 38 GHz → 0.55°.
  - The paper's values imply D ≈ 3.1 m (2 GHz, 3.2°) and D ≈ 2.8 m (38 GHz, 0.2°), which contradicts the stated 1 m antenna.
  - Decision: correct the beamwidths to 10.0° and 0.55° for 1 m (recommended), or state the larger apertures used.
  - Check whether the "beam-tracking" and "interference rejection" statements in Section III.B depend on these values.

  **Working set (adopted, to be confirmed with TA):** each node's aperture and beamwidth follow from the gain the link budget already uses (η ≈ 0.6, θ ≈ √(41253/G)):

  | Node | Gain (paper) | Aperture (η = 0.6) | 3 dB beamwidth (from gain) |
  |---|---|---|---|
  | Gateway, 38 GHz | 39.7 dBi | ≈ 0.31 m dish | ≈ 2.1° |
  | UAV array, 38 GHz | 30.7 dBi | ≈ 0.11 m array | ≈ 5.9° |
  | HAPS, 38 GHz | 13.8 dBi | ≈ 2 cm patch | ≈ 41° |
  | Service/UE, 2 GHz | 0 dBi (isotropic, per paper) | not applicable | not applicable |

  - Replace the "3.2° at 2 GHz with a 1 m antenna" and "0.2° at 38 GHz" sentences in Section III.B with the table above, and remove the claim that a 1 m dish is used.
  - The 2 GHz "beamwidth" comparison is no longer needed for the link budget, because the service link is isotropic in the paper.
  - **Question for TA:** is a 0.31 m gateway dish and a ~0.11 m UAV array an acceptable antenna choice for 38 GHz HAPS feeder and backhaul in this study, given the gains already used?
- [ ] **D1.5 Capacity bounds** (checklist 1.5): 6.2 bits/s/Hz vs +7.3 dB maximum SINR; the Summary and relay-table ranges.
  - Root cause: `appendix_tables/UAV_relay_path_comparison.tex` (and the `uav_relay_two_hop_capacity_bps_hz()` function behind it) uses noise-only SNR. Implied SNR: direct 6.17 bits/s/Hz = 18.5 dB at nadir; 1.90 bits/s/Hz = 4.4 dB at 100 km; relay HAPS→UAV 9.72 = 29.3 dB; UAV→UE 10.45 = 31.5 dB.
  - The paper text calls these SINR values, and the "−5 dB floor" and "+7.3 dB maximum" are SINR. The two sets of numbers mix SNR and SINR.
  - Decision: (a) recompute capacities with the interference term (SINR) for the direct and feeder hops, which also resolves D1.2 for the relay, then regenerate the table, the Figure 12 caption and the Summary/Conclusion ranges; or (b) relabel the table as SNR and state that interference is excluded. Option (a) is recommended.
  - Check the `uav_relay_two_hop_capacity_bps_hz` code path and `src/generators/generate_relay_table.py` when regenerating.
- [ ] **D1.6 Path-loss averaging** (checklist 1.6): averaging in the dB domain versus linear gains; η values to be tabulated (`src/models/channel_model.py:163`).
  - Code averages in dB at `src/models/channel_model.py:435`, matching paper Eq. (pl). Linear averaging of gains changes the result where P_LoS is intermediate: suburban 10 km (P_LoS 0.066) → 8.2 dB difference; high-rise 1 km (P_LoS 0.046) → 16.9 dB difference. Zero difference where P_LoS is 0 or 1.
  - η naming: the code's η_los / η_nlos (`channel_model.py:163–166`) are flat excess-loss offsets marked "VERIFY vs Table 1". The code comment at lines ~152–159 says Arani's η is a path-loss exponent. Either the code's parameters come from a different source, or the naming is wrong. The paper must state the source for each value.
  - Decision: (a) switch to linear-domain averaging of gains (the correct expected-gain form) and regenerate the affected SINR and capacity results, or (b) keep dB averaging and state that it is an approximation with the size of the error above. Option (a) is recommended.
  - Also check: P_LoS is 0.07 at 10 km for suburban and 0 by 50 km; for high-rise it is 0.05 at 1 km and 0 by 10 km. Confirm this is the intended product-series output before using it for the relay second hop.
- [ ] **D1.7 Citations** (checklist 1.7): M.2101 vs RR/WRC-19; TS 38.821 vs TS 38.101-5.
  - **M.2101 is not the source** for the 38–39.5 GHz HAPS allocation. The search results point to the WRC-19 outcome (fixed service, identified for HAPS). Cite the Radio Regulations footnote or WRC-19 resolution, and check the exact wording against the RR text.
  - **Direction issue (substantive, not only a citation):** the same search result says HAPS use of this fixed-service allocation is limited to the **ground-to-HAPS direction**. The paper models HAPS→Gateway (backhaul) and HAPS→UAV (feeder) links, which run the other way. Verify in the RR text. If confirmed, the backhaul and feeder links need a different direction or an allocation justification, which changes Sections III.B and IV and the abstract.
  - **2 GHz band:** TS 38.101-5 band n256 is 1980–2010 MHz uplink and 2170–2200 MHz downlink, which matches the paper's 2 GHz service link. Cite n256 there, and drop TS 38.821 as the band source.
  - **HAPS bands at WRC-19 (checked against the ITU hub page and APT WRC-19 reports):** WRC-19 identified **31–31.3 GHz and 38–39.5 GHz** for HAPS worldwide, and confirmed **47.2–47.5 GHz and 47.9–48.2 GHz** for HAPS worldwide. WRC-19 also set **limitations on link directions** for HAPS, which bears on W4. The pasted note's "38 GHz approved at WRC-97" is **dropped**: WRC-19 is the source for 38–39.5 GHz, so WRC-97 is not cited. The 47 GHz bands are a possible alternative for the gateway and feeder links if the direction limit rules out 38 GHz.
  - **Pasted note on TR 38.821 (checked):** the note calls it "TS 38.821, Release 17, September 2022" with "HAPS frequency allocations". The document is a **Technical Report** (TR 38.821, a study), not a Technical Specification. The search did not show TR 38.821 listing the 38–39.5 GHz or 2.1–2.2 GHz allocations. Use TR 38.821 only for NTN context. Band sources: 38–39.5 GHz → WRC-19 (fixed service, identified for HAPS); 2 GHz HAPS service use → WRC-23 (HIBS in IMT bands); 2 GHz band definition → TS 38.101-5 n256. Do not cite TR 38.821 for the bands unless the report's table is checked and quoted.
  - **38 GHz NTN attribution:** no 3GPP NTN band for 38–39.5 GHz was found in the search. Remove the "3GPP NTN" attribution for the Ka band (lines ~87, ~93, ~96, ~172, ~203).
  - **Holis & Pechac 2008:** confirmed as IEEE TAP vol. 56, no. 4, pp. 1078–1084 (2008), titled "Elevation dependent shadowing model for mobile communications via high altitude platforms in built-up areas". Check the bib entry against this title.
  - **"Cited in 300+ works"** (line ~378): unsupported, remove.
- [ ] **D1.8 "Margin" terminology** (checklist section 1 / intro): the phrase "manageable link margins" is already removed from line 103. Remaining uses ("implementation margin", "scintillation margin", "fading margin", "8.7 dB margin") need the paper-wide decision: define once, or rename per use. Affects Sections II–IV and the Summary.

## DQN and LSTM (checklist section 2)

- [~] **D2.1 LSTM horizon. Option (a) applied to the paper text** (abstract, section opening, motivation paragraph, Limitations): the LSTM predicts up to six horizons, and the agent uses only the one-hour output. Still to check: the window description (line ~1088) and the Summary/Conclusion for any six-hour wording (none found by search). Ablation D2.6 is still needed to show whether the one-hour forecast adds value. (Original note follows.) The agent uses only `pred_h1`, the one-hour forecast (`src/drl_dqn/build_real_episodes.py:66–68`, `src/drl_dqn/real_episode_env.py:43, 78`). The six-hour motivation (paper ~line 1083, abstract line 70, Summary, Conclusion) must match. Options: (a) reword the motivation so the one-hour horizon is the design choice and justify it, which is the lower-cost option; or (b) rerun the DQN with a six-hour input and report it. Note that at +1 h the LSTM is worse than persistence (MAE 0.91 vs 0.65 dB), so a one-hour input may add little. Test that with an ablation (D2.6).
- [ ] **D2.1b Episode count.** The paper says 400 rolling training episodes (line ~1090, ~1324). `src/drl_dqn/train_dqn_real.py:4` says 300. Use the count that was actually run, and state it everywhere.
- [ ] **D2.1c Leakage check.** `pred_h1` issued at t−1 is used at hour t, so the agent never sees hour t's rain. State this in the Methods, since a reader will ask.

## Queued computation (stacked, not yet run)

- [x] **Q1 Delhi R0.01 and P.618 path attenuation (for D1.1f).** *Run (WSL `~/quantum_env`, `itur` 837/618/838):* **R0.01 = 61.8 mm/h** at 28.61° N, 77.21° E. At 0.01 % of the time, 38 GHz: γ_R = 15.1 dB/km; path attenuation **141 dB** at 11.3° (102 km slant) and **97 dB** at 89.86° (gateway geometry). **Caveat:** these are very large, and the 97 dB near-zenith value looks high for a ~4–5 km rain height. Check the rain-height and reduction-factor inputs in `itur` before quoting. Even so, the order of magnitude (≫ 30 dB) means rain alone cannot be covered by a fixed margin at 0.01 %. The feasibility wording depends on the availability target, which the paper does not state (see W7).
- [x] **W7 Availability target: 0.1 % exceedance (99.9 % availability).** Decided by the user; state it in the paper.
  - Computed (WSL `itur`): **R0.1 = 15.7 mm/h** for Delhi; γ_R at that rate = **4.5 dB/km** (38 GHz, 11.3°).
  - P.618 path rain attenuation exceeded 0.1 % of the time: **93 dB** at 11.3° (102 km worst-case slant) and **45 dB** at 89.86° (gateway near-zenith geometry).
  - **Consequence:** the gateway's clear-sky SNR is about 46.5 dB (FSPL and antenna gains only, earlier calculation). A 45 dB rain loss at 0.1 % leaves about 1.5 dB before gas absorption and scintillation. The 38 GHz gateway link therefore has essentially no rain margin at 99.9 % availability, and the feasibility sentences must say so.
  - **Caveat:** the `itur` P.618 path call should be checked against the rain-height input before the numbers go into the paper (same check as Q1). The 0.1 % values use the 0.01 % rate as R001, so re-check that input as well.
  - Paper text change (batched): state the 0.1 % target in Section III.B and the intro, and replace the "manageable" feasibility wording with the 1.5 dB result. Compute R0.01 with `itur.models.itu837.rainfall_rate` at 28.61° N, 77.21° E in WSL `~/quantum_env`, then P.618 rain attenuation at 0.01 % for 38 GHz at 11.3° (worst-case path) and at the gateway's near-zenith geometry. Record the results here before editing the feasibility text.

## Section 2 status (latest)

- [x] DQN state is 24-dim: 18 base features (SINR, distance, SoC, rain/vis/hour, gateway and UAV relay capacities) plus six forecasts for hours t..t+5 issued at t−1. Equation and feature list updated.
- [x] Action space is nine actions (direct, gateway relay, UAV relay for each HAPS). MDP, action-space and limitation text corrected.
- [x] Reported Jain is over per-user delivered throughput; the reward keeps Jain over linear SINR (stated separately).
- [x] Greedy-throughput baseline added (same nine actions, no learning). Max-SINR is labelled direct-only. PreLSTM rows removed from the table and explained in one sentence.
- [x] Final 5-seed results in the policy, seed and paired tables, and in the fairness, reward, baseline and conclusion paragraphs.
- [x] Episode count is 400 in code and paper. The 300 was only in the single-model script, changed to 400. Confirm with the author.
- [ ] Diebold–Mariano test for LSTM vs persistence, and naming the 50 evaluation days (deferred to the end, per the author).
- [ ] DQN without the LSTM feature (the with/without-forecast ablation) and oracle rain. Needed to show the LSTM's contribution.
- [ ] Reward worked example (2.4), hyperparameter table (2.10).
- [ ] Forecasting baseline (climatology or gradient-boosted model) and single-site limitation for Delhi (kept open, per the author).

## Section 1 status (final pass)

- [x] **D1.1a–c** rain model: `battery_model.py` and `train_lstm.py` use the P.618 slant-path model at 89.86° (γ_R·L_s·r, P.839 rain height 5.28 km). LSTM retrained and DQN retrained (5 seeds, 400 episodes). Results in the paper updated.
- [x] **D1.1d** atmospheric-loss plot: the paper's figure already comes from `plots/atmospheric_losses.py`, which uses `itur` P.838. The stale `atmospheric_losses_simple.py` (α = 0.921) is now replaced with the itur coefficients.
- [x] **D1.1e** check scripts: `check_rain_attenuation.py` and `analyze_parameters.py` now quote the P.618 gateway values (13.3 and 27.7 dB).
- [x] **D1.1f** feasibility: the paper states the 0.1 % result. **Correction to W7:** the 45 dB figure came from a mismatched `itur` call. The physical model gives 19 dB at R0.1 = 15.7 mm/h, leaving about 27 dB of the 46 dB clear-sky SNR (about 22 dB after an approximate 5 dB gas loss). The 38 GHz gateway link closes at 99.9 % availability. The gas figure is approximate and should be checked with `itur`.
- [x] **D1.2** gateway interference: the paper now gives about −35 dB INR (not −43), with the F.699 sidelobe (−10 dBi floor) on the interferer and the −10 dBi gateway off-axis gain. **Correction:** the earlier SIR of 21–31 dB left out the gateway receive pattern. With that pattern the gateway is noise-limited, which matches the paper's original claim.
- [x] **D1.3** scintillation: `channel_model.py` uses the `itur` P.618 table (38 GHz at D = 0.31 m, 2.1 GHz at D = 1 m); Eq. (scint_fade) removed; text, table and figure caption updated; figures 9a, 9b, 10a, 10b, 11a–d regenerated.
- [x] **D1.4** beamwidths: Section III.B uses the gain-derived working set (2.1°, 5.9°, 41°).
- [x] **D1.5** capacities: relay HAPS→UAV SINR includes co-channel interference from the two other HAPS (F.699 sidelobe and receive pattern, azimuth-averaged); the direct column uses `multi_node_sinr_db`. Table, Figure 12, relay text and Conclusion rewritten. Result: the relay outperforms the direct link at every distance. The feeder hop is above the +8 dB floor out to 100 km.
- [x] **D1.6** averaging: linear-gain averaging with Holis & Pechac Eq. (4) and Table IV (NLoS μ, σ; LoS zero-mean σ = 4 dB). η values removed from the code and from `sinr_plot.py`. Eq. (pl) text rewritten.
- [x] **D1.8** margin: "implementation margin" kept (3 dB design allowance); other uses renamed (fade values, fade allowance, bound distances).
- [ ] **D1.7** citations: **reserved**, per the author. Still to do: M.2101 → WRC-19, TS 38.821 → TS 38.101-5 n256, removing the 3GPP attribution for 38 GHz, Holis & Pechac citation for the product-series LoS equation, and the DOI.
- [ ] **D-C1** undefined references: for the author's local compile.

**Closed in the last pass:**
- **Gas loss (ITU-R P.676, `itur`):** 0.33 dB at 89.86° and 1.7 dB at 11.3° (ρ = 7.5 g/m³). The paper uses 0.4 dB at 89.86° (ρ = 10 g/m³). The 5 dB figure was wrong and is removed; the remaining budget after rain is about 26 dB.
- **Direct-link azimuth:** the relay table's direct column is now the dB average over 24 azimuths (as in Phase 1). At 100 km the direct SINR is −4.3 dB (0.5 bits/s/Hz), consistent with the Phase-1 value of −4.3 dB. The paper text and the Figure 12 caption are updated to match.
- **Figure 12 legend:** moved below the plot. It no longer overlaps any curve.

**Known open issues for the author:**
- Gas attenuation at 89.86° (≈5 dB) is approximate; check with `itur` before publication.
- The relay SINR at the direct link uses a single azimuth (`multi_node_sinr_db`); the paper's Phase-1 values are azimuth means.
- The relay figure legend overlaps the green curve (cosmetic; not changed).
- The 2026 LSTM validation is kept (held out from training); this needs the author's decision.

## Status after the DQN and LSTM text update (this step)

- [x] Paper text: DQN intro, policy table (5-seed means, std across seeds), seed-statistics table, paired table (5-seed), reward/fairness/baselines/limitation paragraphs, policy figure caption, Conclusion numbers, abstract LSTM clause (RMSE, minimal change), LSTM target description (89.86° gateway geometry, P.838/P.839/P.618), 2026 LSTM table and validation paragraph, LSTM figure caption.
- [x] Figures regenerated and copied: `figures/policy_comparison.png` (5-seed, DQN rows filtered), `figures/lstm_forecast_2026.png`.
- [x] Scripts: `run_baselines_5seed.py` (new), `plot_comparison.py` (5-seed input), `run_multiseed.py` (seeded evaluation), `train_dqn_real.py` (400 episodes).
- **Open question from the author:** whether to keep the 2026 LSTM validation at all, given "we don't validate LSTM against real values of 2026?". It is currently kept as a held-out test (no 2026 data in training). Confirm before removing.
- **Still open in Section 1 (not done by this step):** D1.1d (atmospheric-loss plot), D1.1e (check scripts), D1.2 (gateway interference text, Summary and Conclusion), D1.3 (scintillation model), D1.4 (working-set table in the paper), D1.5 (capacities with interference, relay table, Figure 12), D1.6 (linear averaging; Holis & Pechac Eq. 4 η replacement; product-series citation), D1.8 ("margin" wording). Citation wording (W4, M.2101, TS 38.821, n256) reserved for later per the author.

## Future work (agreed, not in this revision)

- [ ] **FW1b Spatio-temporal graph forecaster (extension of FW1).** A GNN-LSTM (DCRNN, T-GCN or Graph WaveNet style): each region is a node, edges link neighbouring regions, an LSTM runs over time at each node, and edge weights are learned to estimate how much each neighbour contributes to the target. Requirements before any work: (a) time series for every node (ERA5 or station data from the sea, desert, plains and Himalayan regions), with licensing confirmed; (b) a held-out check that the learned edges are physically plausible (distance, wind direction), since learned graphs can be spurious; (c) benchmarks against the current LSTM, persistence and climatology on the same 2026 hours; (d) a separate DQN retrain if the forecast changes. Not in this revision.

- [ ] **FW1 Neighbouring-region inputs for the LSTM.** Add current observations from neighbouring regions, refreshed periodically, and learn the relationship between them and the site's rain attenuation (spatial lag features). Accepted that the LSTM's gain over persistence is modest for now. Write this as future work in the Conclusion, and do not claim it as a result.

- [ ] **FW2 Local land-surface and aerosol effects on rain (out of scope).** Proposed by the author, not verified: (a) vegetation and evapotranspiration feeding back on local rainfall; (b) lakes and other water bodies adding moisture; (c) stubble-burning smoke suppressing or shifting cloud formation (aerosol effects on condensation). None is modelled here. Note them as untested hypotheses in the Conclusion's future work, with a pointer to a better weather model (borrowed or external) as the route to test them. Do not present them as findings.

## Points waiting on the user

- [x] **W1** D1.2: **Decided (revised, with basis):** interferer sidelobe gain toward the gateway from the ITU-R F.699 reference envelope, G = 32 − 25 log₁₀(φ) dBi for 1° ≤ φ < 48°, floored at −10 dBi. Basis: each interferer's main beam points at its own nadir service area, so the gateway (about 65 km horizontal, 20 km height) is about 73° off-boresight, which gives the −10 dBi floor. Result: two interferers give interference ≈ −85.0 dBm and **SIR ≈ 31.4 dB** before atmospheric losses. State F.699 as the pattern basis, and note that F.699 is a point-to-point reference pattern used here as a proxy for the HAPS antenna. The earlier 0 dBi placeholder is superseded.
- [x] **W1b** F.699 as the proxy pattern for the HAPS antenna: **accepted** as a stated assumption. TA to advise if a HAPS-specific pattern should replace it.
- [x] **W2** D1.4: **Decided (not gated on TA):** use the working set, gateway dish 0.31 m (39.7 dBi), UAV array 0.11 m (30.7 dBi), HAPS 13.8 dBi. **Basis:** the gains are the paper's own cited values (Karaman et al. 2025 for the HAPS and gateway gains; Anim et al. 2021 for the UAV array gain); the apertures are derived from those gains with η ≈ 0.6 (standard aperture efficiency). TA feedback is pending and can revise them.
- [x] **W3a** D1.6: **Resolved from the source.** Holis & Pechac, "Elevation Dependent Shadowing Model for Mobile Communications via High Altitude Platforms in Built-Up Areas", IEEE TAP 56(4), April 2008, pp. 1078–1084, DOI 10.1109/TAP.2008.919209 (PDF in `Downloads`). Read from the PDF:
  - **Table I** (ITU-R P.1410 parameters α, β, γ): suburban 0.1 / 750 / 8 m; urban 0.3 / 500 / 15 m; dense urban 0.5 / 300 / 20 m; urban high-rise 0.5 / 300 / 50 m. These match `channel_model.py` (γ is the code's ξ). **Verified basis for the building parameters.**
  - **Eq. (2) and Table II** (LoS probability vs elevation, P_LoS(θ) = a − (a−b)/(1+((θ−c)/d)^e), percent): suburban a=101.6, b=0, c=0, d=3.25, e=1.241; urban 120.0, 0, 0, 24.30, 1.229; dense urban 187.3, 0, 0, 82.10, 1.478; high-rise 352.0, −1.37, −53, 173.80, 4.670.
  - **Eq. (4) and Table IV** (2 GHz, **all environments**): μ(θ) = (g+θ)/(h+iθ), σ(θ) likewise. For 10° ≤ θ < 90°: μ: g = −94.20, h = −3.44, i = 0.0318; σ: g = −89.55, h = −8.87, i = 0.0927. Check: μ(70°) ≈ 19.9 dB and σ(70°) ≈ 8.2 dB, against Table III values 19.5 dB and 8.1 dB (paper's rounding).
  - **Table III** (70°, 2 GHz): mean NLoS additional shadowing 19.8 / 19.5 / 19.5 / 19.5 dB and σ 8.0 / 8.1 / 8.1 / 8.1 dB (suburban / urban / dense urban / high-rise). The paper says the environment dependence is insignificant.
  - **Eq. (5)–(6):** L_LoS = L_FSL + ζ_LoS; L_NLoS = L_FSL + L_s + ζ_NLoS; L_FSL = 20 log d_km + 20 log f_GHz + 92.4 (consistent with our FSPL constant). The paper gives location variability σ = 3–5 dB for LoS and 8–12 dB for NLoS, with zero mean.
  - **Validated at 2.0, 3.5 and 5.5 GHz** in dense urban (Prague airship measurements), with a 5 dB error bound on the measurements.
  - **Consequences for the code and paper:**
    - The paper gives **no per-landscape η**. The mean NLoS excess loss is elevation-dependent (≈19.5–20 dB at 70°), the same for all environments.
    - **LoS mean excess loss is zero** (zero-mean ζ_LoS); the code's η_los values (0.1, 1.0, 1.6, 2.3 dB) have no basis.
    - The code's **η_nlos = 34 dB for high-rise** is not supported (Table III gives 19.5 dB).
    - Replace the flat η values with μ(θ) from Eq. (4) and σ from Eq. (4), and cite Table IV.
    - **Citation issue:** the paper's Eq. (los), the product series with α, β, ξ, is **not** in this 2008 paper. The 2008 paper gives the Table II elevation fit instead. Our Eq. (8)–(9) cite `holispechac2008` for the product series, so the citation or the equation must change.
    - **Title issue:** the paper's title is "...in Built-Up Areas", which matches the bib and the reference notes. The "Mountainous Terrain" title in `AI-HAPS-WrongPic/CLAUDE.md` is wrong.
  - **Applicability (corrected):** the UE is at street level, which is the model's scope, so the model applies to the UAV→UE hop. The UAV altitude (500 m) only sets the elevation angle, and the model covers 1°–89°. The 2.1 GHz hop is inside the model's 2–6 GHz range. The model does **not** cover the 38 GHz feeder or backhaul hops, which need their own treatment (the Ka-band atmospheric model already in the paper).
- [~] **W3a-old** (superseded) D1.6: **Option (a) chosen; blocked on the paper's equations.** Holis & Pechac 2008 gives an empirical, elevation-dependent additional shadowing loss for NLoS HAP-to-street links, computed with the uniform theory of diffraction, validated at 2.0, 3.5 and 5.5 GHz with an airship. Web search confirmed this form but did not return the equations or the parameter table. **Needed:** the full text of Holis & Pechac 2008 (IEEE TAP 56(4):1078–1084), specifically the shadowing-loss equation and its per-environment parameters. Until then, the η values in `channel_model.py` are not used in any paper claim. Also note the model is for street-level users at 2–5.5 GHz, so check its applicability to the 2.1 GHz UAV→UE hop.
- [~] **W3** D1.6: **Retracted, no basis yet.** The η_los / η_nlos values in `channel_model.py:163–166` (suburban 0.1 / 21 dB, urban 1.0 / 20 dB, dense urban 1.6 / 23 dB, high-rise 2.3 / 34 dB) are marked "VERIFY vs Table 1" and have no verified source in the repository. They must not be presented as assumptions with a basis. **Options with a real basis to pursue:** (a) take the excess-loss values from Holis & Pechac 2008, whose model gives an elevation-dependent shadowing loss as a best fit to simulation results; (b) take Arani et al.'s Table 1 values (the code comment says it has per-environment parameters, but the η there is a path-loss exponent, so the model form would also change); (c) drop the excess-loss term and use the pure LoS/NLoS FSPL model, stating the omission. Pick one, and the source must be checked against the original paper before use. The P_LoS product series is the Holis & Pechac model and can stay as the stated LoS model.
- [~] **W4** D1.7: HAPS direction limit (ground-to-HAPS only, 38–39.5 GHz). **Verified by the user** (reference links provided separately). **Pending:** paste the links or the RR footnote number and wording, so the exact citation and quotation go into the paper. Affects the backhaul and feeder model (HAPS→Gateway and HAPS→UAV run the opposite way).
- [x] **W5** Section 1 options **accepted (recommended):** D1.3 itur P.618 throughout; D1.5 recompute with interference; D1.6 linear-domain averaging; D1.8 define "margin" once. TA to advise if any should change.
- [ ] **W6** Permission to retrain the DQN, since headline numbers change.

## Compile issues to resolve at the end

- [ ] **D-C1 Undefined references.** The main file `\input`s `appendix_tables.tex`, `appendix_code.tex`, `phase3.tex`, `abbreviations.tex` and `bibliography.tex`. Any `??` in the compiled PDF means a missing label or citation. Check that all five files are present and that every `\ref` and `\cite` key resolves (e.g. `table:app-uav-relay-comparison`, `sec:app-uav-relay`, `sec:app-spatial-sinr`, the `itu_p838` and `karaman2025haps` keys). Fix these at the end, together with the code and figure changes above, since several labels live in the appendix and move when results are regenerated.

## Rule for this file

When a deferred item is done, tick it here and in `REVIEW_CHECKLIST.md`. Nothing in this file is committed or pushed until the user approves.
