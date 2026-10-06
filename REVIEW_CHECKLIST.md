# Paper Review Checklist: AI-Ready Air-to-Ground Channel Model (HAPS–UAV)

Source: `HAPS_AI_HW_ChannelModel.tex`. Verdict: **major revision**.
Mark an item `[x]` when fixed and verified (statically or by re-running the relevant script).

## 1. Technical errors

- [x] **1.1 Rain coefficients implausible.** *Done (option 1: report γ_R in dB/km):* intro (line ~103) and Eq. (3) text now use γ_R ≈ 3.0 / 6.8 dB/km at 10 / 25 mm/h. The 5.9 / 15.2 dB path values were removed. *Follow-up for the link budget:* P.618 path attenuation at 0.01 % exceedance is ≈53 / 88 dB, which must be addressed in the feasibility discussion (item 1.2 and the conclusion).
- Previous note:  *Progress:* verified in WSL `~/quantum_env` with `itur`: k ≈ 0.400, α ≈ 0.881 (11.3°, horizontal pol.); γ_R = 3.04 dB/km at 10 mm/h, 6.82 dB/km at 25 mm/h. Coefficient text at Eq. (2) corrected. **Open:** the 5.9/15.2 dB path values and intro 8–18 dB are not yet recomputed; `itur` P.618 at 0.01 % exceedance gives ≈53 dB (R=10) and ≈88 dB (R=25) over the slant path, which changes the 38 GHz feasibility argument. Needs a decision on the metric before editing. `k=0.0318, α=0.921` at 38 GHz (line ~245) is likely ~10× too small vs ITU-R P.838. Ratio 15.2/5.9 = 2.58 does not match α=0.921 (2.5^0.921 ≈ 2.3). Intro "8–18 dB" (line ~103) conflicts. *Fix:* verify with `itur.models.itu838`, correct k/α, recompute 10 and 25 mm/h values, make all three statements consistent.
- [ ] **1.2 Gateway interference claim contradicts link budget.** Paper says interferers ≈43 dB below noise. Using paper's numbers: desired ≈ −53.5 dBm, interferer (~68 km slant) ≈ −64 dBm, noise −100 dBm → interference ~36 dB *above* noise, SIR ≈ 11 dB. *Fix:* recompute with the code, state the interferer antenna model explicitly, and revise the noise-limited conclusion (abstract, §III.B, §IV summary, conclusion). Same check for the UAV feeder hop.
- [ ] **1.3 Scintillation mislabelled and inconsistent.** Eq. (scint_fade) is cited as P.618 Annex 2 but is the custom fit in `src/models/channel_model.py:449` (exponents 0.7 and 1/sinθ; P.618 uses 7/12 and sin^-1.2). Magnitudes conflict: 2–4 dB (line ~312), 7.6–13.1 dB (line ~1312), 10.53 dB (line ~1170). S-band 2.6–4.7 dB implausibly large. *Fix:* adopt one model (preferably `itur` via `src/lstm/scintillation_p618.py`), relabel, and unify all magnitudes.
- [ ] **1.4 Beamwidths inconsistent with 1 m aperture.** Line ~544: 3.2° at 2 GHz; 70λ/D gives ~10.5°. 0.2° at 38 GHz needs ~2.8 m. *Fix:* correct the numbers or the aperture.
- [ ] **1.5 Capacity bounds conflict.** 6.2 bits/s/Hz (lines ~836, ~1438) needs ~18.6 dB SINR, but stated direct-link max is +7.3 dB (≈2.7 bits/s/Hz). *Fix:* recompute the direct-link range from the data.
- [ ] **1.6 Path loss averaged in dB domain.** Eq. (pl) averages dB losses before forming the gain. Expected SINR ≠ SINR at average loss. η_LoS / η_NLoS values are missing from the paper (they are in `channel_model.py:163`). *Fix:* average linear gains (or SINR over states), and add a table of η values.
- [ ] **1.7 Citations to verify.** M.2101 for the 38–39.5 GHz HAPS allocation (line ~157) → cite the RR/WRC-19 provision. TS 38.821 for the 38 GHz NTN band (line ~87) → likely TS 38.101-5 (n256). "Cited in 300+ works" (line ~378) is unsupported: remove.

## 2. DQN and LSTM design

- [ ] **2.1 LSTM horizon vs DQN input.** Motivation is a 6-hour lead time (line ~1083) but the DQN uses the 1-hour forecast (line ~1324). At +1 h the LSTM is worse than persistence. *Fix:* either feed the horizon the DQN actually uses and justify it, or reword the motivation.
- [ ] **2.2 State vector omits the forecast.** Eq. (state-vector) has 12 features, no LSTM term, yet text says the forecast is a state feature (line ~1090). *Fix:* add the forecast to the equation and the observation space (13-dim), or remove the claim.
- [ ] **2.3 Action space inconsistent.** 4 choices (line ~1137) vs a ∈ {0,1,2} (line ~1178); "relay options" (line ~1397) vs "modelled per HAPS" (line ~1401). *Fix:* one definition throughout.
- [ ] **2.4 Reward not reproducible.** 0.5·L_agg ≈ +38 for max-SINR (throughput 76), yet reported reward is −16.5. Penalties described as network-average (line ~1190) but per-user in Error 5 (line ~1229). *Fix:* a worked example reconciling the reward with the code; make the aggregation consistent.
- [ ] **2.5 Headline reward win is partly circular.** DQN is trained on the reward that penalises outage. *Fix:* report throughput, outage, fairness and SoC as separate primary metrics.
- [ ] **2.6 Missing ablations.** Need: DQN without LSTM feature; DQN with oracle rain; a battery/load-balancing heuristic; a proportional-fair baseline. *Fix:* run them (scripts in `src/drl_dqn/`) and add to Table.
- [ ] **2.7 Energy claims unsupported.** 1 W/user (ASSUMED, line ~1013) gives 50 W against a 700 W load; SoC difference −0.001 (p=0.95). *Fix:* make user load meaningful, or drop the energy-efficiency claim (line ~1078).
- [ ] **2.8 Weak statistics.** Significance over 5 seeds, not 50 days. LSTM vs persistence has no test; "about 0.1 dB" understates the gap (RMSE 0.09–0.6 dB, line ~1119); "rain hours" claim has no table. *Fix:* paired bootstrap / Wilcoxon over days; Diebold–Mariano for the LSTM; name the 50 evaluation days and sampling method.
- [ ] **2.9 Two different random baselines.** Jain 0.331 / outage 33.7 (line ~1059) vs Jain 0.071 / outage 19.4 (line ~1335). "PreLSTM" undefined. *Fix:* unify or explain; define PreLSTM.
- [ ] **2.10 Missing DQN hyperparameters.** Architecture, lr, ε schedule, replay size, target update, γ, episodes, training time. *Fix:* add a table.
- [ ] **2.11 Jain index quantity varies.** Applied to linear SINR (reward, Error 1) vs throughput T_k (line ~1034). *Fix:* state which is reported and use it consistently.
- [ ] **2.12 P.618 used for hourly rain.** P.618 is a long-term statistical method. *Fix:* justify as an empirical rain-rate → attenuation mapping; add a stronger forecasting baseline; state single-site (Delhi) limitation.

## 3. Internal contradictions

- [ ] **3.1 SINR range.** [−7.4, +7.3] dB (line ~1152) vs [−11.27, +7.25] dB (line ~1174). Unify.
- [ ] **3.2 Stale references.** "Section IV.B" (doesn't exist); "§2.1" (line ~108); "§II/§III" labels. Fix all `\ref`s and textual section numbers.
- [ ] **3.3 Battery SoC.** "pinned at ≈65%" (line ~1240) vs 59.9% in results. Reconcile.
- [ ] **3.4 Notation.** Eq. (sinr) uses UAV index u for a HAPS association; use one notation.
- [ ] **3.5 Visibility bound.** `[0,10k]` (line ~1163) → `[0,10000]` m.
- [ ] **3.6 Abstract vs body.** Abstract says six-hour forecast; DQN uses one-hour (see 2.1). Align after 2.1 is resolved.

## 4. Structure and presentation

- [ ] **4.1 Project-log tone.** Remove "Phase" labels, "Error 1–6" list (line ~1201), "Key finding", "Critical principle", "ASSUMED". Move bug log to an appendix.
- [ ] **4.2 Repetition.** 9.94 dB spread, sector result and relay numbers repeated 3–4 times. Keep one statement each.
- [ ] **4.3 Contributions and related work.** Add an explicit contribution list and a related-work section (HAPS/UAV association, DRL). Clarify novelty vs Arani et al. and Holis & Pechac.
- [ ] **4.4 Affiliation.** A diploma programme is not an institution; check venue author-format rules.
- [ ] **4.5 Figures.** Define "landscape-independent" once; match trellis figure name to content; consistent dB vs dBm.

## 5. Reproducibility

- [ ] **5.1 Code and data link.** Add repository link (and DOI if possible); map each table/figure to its script.
- [ ] **5.2 Seeds and splits.** Publish seeds, the 50 evaluation days, LSTM hyperparameters, train/val/test date splits.
- [ ] **5.3 Parameters.** State η values, rain coefficients used, and the scintillation model actually run.
