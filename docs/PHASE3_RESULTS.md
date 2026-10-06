# Phase 3 Results: LSTM Validation, Real-Episode DQN, and Parameter Status

Status: initial. The 2026 validation covers the full year, with ERA5 cloud cover filling the
POWER gap from April. Single training seed for the DQN.

## 1. LSTM forecaster

### 1.1 Setup

- Target: ITU-R P.618 path rain attenuation (dB) at 38 GHz, 11.3° elevation, 50 m gateway,
  computed from the hourly NASA POWER precipitation (`train_lstm.rain_path_attenuation_db`).
- Inputs: 24 hours of temperature, humidity, pressure, wind, precipitation, cloud amount,
  visibility, METAR rain and fog flags, ERA5 cloud liquid water, and time-of-day and season.
- Horizon: 6 hours. Window: 24 hours.

### 1.2 Model versions

| Model | Trained on | Used for | Out of sample for |
|---|---|---|---|
| forward model | 2023 | forecasts of 2024 (`oof_2024`) | 2024 |
| test model | 2023–2024 | forecasts of 2025 (`test_2025`) | 2025 |
| final model | 2023–2025 | forecasts of 2026 (`verify_2026`) | 2026 |

2026 is not in the training data of any model that forecasts it.

### 1.3 2025 test (model trained on 2023–2024)

| Metric | LSTM | Persistence |
|---|---|---|
| MAE (6 h average) | 1.15 dB | 1.09 dB |
| RMSE (6 h average) | 3.67 dB | 4.16 dB |

The LSTM has lower RMSE (fewer large misses) but higher MAE (worse on typical hours).

### 1.4 2026 validation (final model, full Jan–Oct, 6,557 windows)

Cloud amount is POWER CLOUD_AMT where available, and ERA5 total cloud cover from 2026-04-05
(POWER has no value there). The fill is a different product and must be stated in the paper.

| Horizon | LSTM MAE | Persistence MAE | LSTM RMSE | Persistence RMSE |
|---|---|---|---|---|
| +1 h | 0.908 | 0.649 | 2.919 | 2.444 |
| +2 h | 1.252 | 1.090 | 3.817 | 3.549 |
| +3 h | 1.489 | 1.406 | 4.433 | 4.295 |
| +4 h | 1.614 | 1.631 | 4.780 | 4.867 |
| +5 h | 1.680 | 1.809 | 4.950 | 5.292 |
| +6 h | 1.711 | 1.945 | 5.005 | 5.607 |

Per regime at +1 h (MAE / RMSE, LSTM vs persistence):

| Regime | LSTM | Persistence |
|---|---|---|
| clear (1,848) | 0.055 / 0.194 | 0.017 / 0.184 |
| cloudy (480) | 0.441 / 1.003 | 0.279 / 0.962 |
| mixed (2,981) | 0.479 / 1.163 | 0.310 / 1.067 |
| rain (1,248) | 3.374 / 6.411 | 2.537 / 5.317 |

Reading:

- At +1 h, persistence wins in every regime. The LSTM adds no value at the shortest horizon.
- From +4 h, the LSTM is slightly better on both MAE and RMSE. The margin is small (about 0.1 dB).
- In rain hours, persistence is better at every horizon. The LSTM does not add value where
  it matters most.

The 2025 result (section 1.3) and this one agree on the pattern: the LSTM's advantage is at
longer horizons and on large errors, not at short horizons. The 2026 validation is the
out-of-sample check, so the paper should report it with the cloud-fill caveat.

## 2. Real-episode DQN

### 2.1 Setup

- Training: 300 rolling 24-hour episodes from 2024, each used once.
- Evaluation: 50 calendar days from 2025, greedy, same days for all methods.
- Real hourly rain and visibility in the state; ITU-R P.618 rain attenuation as the feeder
  rain loss; LSTM 1-hour forecast as one additional state feature (19 state features).
- Baselines on the same days: random, and max-SINR (best direct HAPS).

### 2.2 Results (held-out 2025, 50 days)

| Method | Reward per step | Jain fairness | Outage (users/50) | Mean SoC (%) |
|---|---|---|---|---|
| DQN | −2.45 | 0.066 | 0.0 | 59.4 |
| max-SINR | −16.53 | 0.694 | 1.0 | 59.5 |
| random | −51.28 | 0.074 | 20.3 | 59.4 |

By regime (reward / Jain / outage):

| Regime | DQN | max-SINR | random |
|---|---|---|---|
| clear | −2.31 / 0.058 / 0.0 | −15.73 / 0.692 / 0.8 | −49.99 / 0.075 / 20.0 |
| cloudy | −3.04 / 0.076 / 0.0 | −17.25 / 0.688 / 1.4 | −51.48 / 0.078 / 19.8 |
| mixed | −1.29 / 0.058 / 0.0 | −18.67 / 0.693 / 0.8 | −54.32 / 0.055 / 19.8 |
| rain | −3.62 / 0.085 / 0.0 | −14.03 / 0.708 / 1.1 | −49.36 / 0.091 / 22.5 |

### 2.3 What the DQN actually does

Action distribution (fraction of user-hour decisions, `analyze_dqn_actions.py`):

| Action | DQN | max-SINR |
|---|---|---|
| direct, HAPS 0 | 0.4 % | 68.1 % |
| direct, HAPS 1 or 2 | 0 % | 31.9 % |
| gateway relay, HAPS 0 | 81.3 % | 0 % |
| gateway relay, HAPS 1 or 2 | 17.9 % | 0 % |
| UAV relay | 0.4 % | 0 % |

Topology: the network has a single ground gateway. One serving HAPS relays through that gateway,
and the other HAPS contribute to the link without being the serving node. The DQN sends 81 % of
decisions through the gateway relay option tied to HAPS 0, which is the serving-node path. The
environment currently exposes one gateway relay option per HAPS, which does not match the single
gateway in the paper. This mismatch is listed as an open item (section 4). In this environment,
the relay option gives a high throughput value (the relay SINR is derived from `2^c − 1`), and
the reward rewards that throughput. So the DQN's higher reward comes from concentrating
users on one relay, which is why Jain fairness collapses to 0.07.

This is not a balanced allocation. Two things must be settled before any DQN claim:

1. The relay SINR formula in `cm.relay_two_hop_capacity_bps_hz` and the conversion
   `2^c − 1` may over-reward relaying. Check it against the paper.
2. The reward weights (0.5 throughput, 0.3 fairness, 0.2 energy) favour the throughput term.
   A policy that routes everyone through one relay can beat a fair policy on this reward.

Training is also not converged. Eval reward moves between −1.3 and −8.4 across checkpoints
(`train_log.csv`), and this is a single seed.

### 2.4 Comparison with the paper

The paper reports DQN reward −41.2 → −32 to −36, Jain 0.54 → 0.6–0.68, and outage 15.1 →
8–10 of 50 (synthetic weather, random mix). On real 2024 episodes the DQN reaches reward −2.5
and Jain 0.07, so the numbers are not comparable. The difference comes from the environment
(real weather, P.618 rain loss, LSTM state feature) and from the reward landscape, not from
a clean improvement.

Fairness did not rise. It fell.

## 3. Parameters

See `docs/MISSING_PARAMETERS.md` for the full analysis. Summary:

- Rain and visibility data are sufficient for hourly episodes.
- Scintillation: the `itur` 0.4.0 wet term carries an extra 1e-6 factor, which removes the
  humidity dependence. The P.618 steps were rewritten directly (`src/lstm/scintillation_p618.py`)
  using the P.453 wet term without that factor. The 1 % fade now responds to weather: at 38 GHz,
  11.3°, it is 0.90 dB at 20 % RH and 1.96 dB at 95 % RH, and 0.96 dB at 0 °C against 3.07 dB at
  35 °C. The hourly values over 2023–2025 range from 0.78 to 3.50 dB (mean 1.94 dB). The step
  for the path-length term (Eq. 46, x = 1.22 D² f / L) still needs checking against the ITU text.
- The paper's rain model is wrong. Its worked example (5.9 dB at 10 mm/h) does not match the
  standard P.618 path (53 dB), and its P.838 coefficient at 38 GHz (k = 0.0315) is off by about
  a factor of 13 from `itur` (k = 0.40).
- Gateway geometry, antenna diameter and efficiency, and the hourly cloud term still need
  confirming or writing.

## 4. Open items (in priority order)

1. Settle the relay SINR formula and reward weights before interpreting any DQN result.
2. Check the scintillation path-length term (Eq. 46) against the ITU-R P.618 text. The wet term
   and the fade steps are already corrected.
3. Test whether the LSTM's +4 h to +6 h advantage is real, using a bootstrap over days.
4. Run multiple DQN seeds and report the spread.
5. Correct the paper's rain model and worked example.

## 5. Future research: spatial and advective weather

The current forecaster uses only the site's own past record. That limits it: it can't see
weather that is arriving from upwind. Rain and fog reach the site by advection, so the next
few hours depend on what is happening in the cells upstream, not only on the site's history.

### 5.1 Proposed direction

Forecast weather at the site from neighbouring cells and the wind field:

1. Track cells across the region from the ERA5 grid (0.25°) or a denser source, estimating
   cell motion from successive fields.
2. Predict the wind field (speed and direction) from the upwind history.
3. Advect the upwind cell state to the site: the field expected at the site at time t+k is
   the field observed upwind at time t, displaced by wind speed times k.
4. Feed the advected fields into the LSTM as extra inputs (upwind rain, cloud liquid water,
   humidity) next to the site's own history.

Worked example: wind at 60 km/h from the northwest means a cell 60 km upwind reaches the site
in about 1 hour, and a cell 360 km upwind in about 6 hours. That matches the 1–6 h horizon,
so upwind cells are the information that could beat persistence at short leads.

### 5.2 Physical factors to model

- **Upper-level flow.** Winds at the cloud and rain layers can differ from the surface wind.
  The advecting velocity should be the layer-averaged wind, not the 10 m wind (WS10M) in
  NASA POWER.
- **Buildings and tunnelling.** Tall buildings channel and block flow and create wake and
  canyon effects. This matters for the urban ground links and for the gateway siting. It is
  a local effect, so it needs a building-height model and cannot come from reanalysis.
- **Terrain.** Hills lift air and force orographic rain on the windward side. They also
  shelter the lee side. Terrain height is needed for both.
- **Fog.** Radiation fog forms in winter nights and is local. Visibility from METAR is the
  only direct observation, and fog attenuation depends on liquid water, which ERA5 does not
  resolve well at the surface.
- **Stubble burning.** Agricultural burning in the surrounding plains adds smoke and aerosol
  to the lower atmosphere in autumn. Its effect on 38 GHz attenuation is expected to be small
  compared with rain and cloud, but it lowers visibility and may affect the fog and
  scintillation terms. This has not been quantified. It needs a smoke or aerosol source
  (for example, satellite fire or aerosol products) and an attenuation model for aerosol.

### 5.3 What is needed for this

| Need | Source | Status |
|---|---|---|
| Wind field at several levels | ERA5 pressure levels (u, v at 850, 500 hPa) | not downloaded |
| Cloud and rain fields over the region | ERA5 or a regional NWP product | partly (site cell only) |
| Terrain height | SRTM / Copernicus DEM | not downloaded |
| Building heights | city GIS data | not available |
| Fire and smoke | satellite fire and aerosol products | not downloaded |
| Aerosol attenuation at 38 GHz | model to be chosen | not implemented |

### 5.4 Test to run before building it

Check whether upwind information helps. Add the advected upwind rain (from ERA5, at the
advection speed) as one feature and compare the 2025 and 2026 skill with the current model,
at +1 h to +6 h, with the same bootstrap over days. If it does not help, the wind term is not
worth the added complexity.

## 6. Band and elevation coverage (done, see section 7)

The attenuation analysis so far uses 38.0 GHz at 11.3° only. The paper's feeder band is
38.0–39.5 GHz, and its elevation range is wider. A sensitivity sweep over the band and over
elevation (for example 11°–30°) is needed before the rain and scintillation numbers are
reported as a range. The 2 GHz service link is not weather-sensitive at this level and is out
of scope for the forecaster.

## 7. Scope: why the LSTM is limited to 38 GHz

The forecaster and its targets are set for the 38.0 GHz feeder link. This is a deliberate
scope decision, with the following reasons.

1. **The feeder is the weather-sensitive link.** The paper places the HAPS-to-gateway feeder in
   the 38.0–39.5 GHz Ka-band (ITU-R M.2101). The service and relay links use 2 GHz (S-band).
   At S-band, rain and gas attenuation are small per the paper's ITU-R P.618 discussion, so
   there is no weather-driven fade for a forecaster to predict on those links.
2. **The DQN's weather-dependent decision is the feeder's capacity.** The rain loss enters the
   reward only through the feeder capacity (section 2 of `PHASE3_RESULTS.md`), so a forecast
   for 38 GHz is the one the controller can use.
3. **Only the upper end of the band is needed for the design.** Sweeping 38.0–39.5 GHz changes
   the result by a few percent (below), so one frequency is sufficient for the forecaster. The
   band matters for capacity planning, not for the forecast target.
4. **Elevation matters more than frequency.** Elevation changes the rain path by a factor of
   about 2 between 11° and 30°. The elevation of the actual link must be confirmed (section 2.3
   of `MISSING_PARAMETERS.md`) before the rain numbers are reported as final.

The limitation is stated so the reader does not read the forecaster as covering the whole
band or the service link.

### 7.1 Sweep results (`sweep_band_elevation.py`)

Rain attenuation (ITU-R P.618, dB) and scintillation (ITU-R P.618 at 1 %, dB), Delhi site, 1 m
antenna, 0.5 efficiency assumed:

| Freq (GHz) | Elev (°) | Scint (dB) | Rain 1 mm/h | Rain 10 mm/h | Rain 25 mm/h |
|---|---|---|---|---|---|
| 38.0 | 11 | 0.643 | 12.6 | 53.8 | 89.3 |
| 38.0 | 15 | 0.443 | 9.9 | 45.1 | 75.5 |
| 38.0 | 20 | 0.315 | 7.8 | 38.6 | 65.2 |
| 38.0 | 30 | 0.197 | 5.8 | 31.7 | 54.5 |
| 39.5 | 11 | 0.657 | 13.6 | 56.7 | 93.5 |
| 39.5 | 30 | 0.202 | 6.2 | 33.5 | 57.3 |

Reading:

- Frequency across 38.0–39.5 GHz changes rain attenuation by about 4–8 % and scintillation by
  about 2 %.
- Elevation from 11° to 30° roughly halves the rain attenuation and cuts scintillation by about
  70 %. This dominates the band effect.
- The 25 mm/h rain figures (54–94 dB) are far above the paper's worked example. They are the
  P.618 path values; this is the open issue in section 2.2 of `MISSING_PARAMETERS.md`.

### 7.2 Consequence

The LSTM and the labels stay at 38.0 GHz and 11.3°. The sweep is reported so that the
conclusions hold across the band. The elevation is the parameter to settle before the paper
states a rain or scintillation number.
