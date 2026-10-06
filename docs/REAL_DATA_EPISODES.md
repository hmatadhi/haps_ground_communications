# Real-Data DQN Episodes: Analysis and Initial Results

Status: initial. The DQN has not been retrained on these episodes yet. This document covers
the episode data, what it can and cannot support, and the three design questions.

## 1. Questions addressed

1. Does the paper's DQN use real past data for rainfall, visibility, and scintillation?
2. Can the paper's DQN training be repeated on our data, and how does that compare with the
   paper's reported reward and Jain fairness?
3. Is the data enough for the LSTM and DQN, or is interpolation or LSTM-generated data needed?

## 2. Answers

### Q1. Real data in the paper's DQN

No. The DQN state holds rain rate, visibility, and hour of day, but these come from
`WeatherScenarioGenerator` (`random_mix`), which draws synthetic composite profiles. The paper
says weather is drawn once per episode and held fixed for its 24 steps.

- Scintillation is excluded from the DQN. The paper defers it to Phase 3 (lines ~1118–1123).
- The scintillation section of the paper uses the ITU-R P.618 formula, not measured or
  forecast time series.
- The LSTM forecaster is listed as Phase 3, so it is not part of the current paper results.

Code inconsistency to fix: the environment docstring in `haps_association_env.py` says weather
evolves hour to hour, while the paper and `weather_scenario_generator.py` say it is fixed per
episode. The paper's version is the one the reported results used.

### Q2. Repeating the paper's training on our data

The paper's numbers are:

| Quantity | Paper (synthetic weather) |
|---|---|
| Episodes | 300 training, 50 held-out evaluation (seed 999) |
| Reward | −41.2 at start, plateau −32 to −36 |
| Jain fairness | 0.54 to about 0.6–0.68 |
| Outage | 15.1/50 falling to about 8–10/50 |

Our episodes are built from real days (`src/drl_dqn/build_real_episodes.py`):

- **Training:** 300 rolling 24-hour windows starting in 2023–2024, sampled without replacement.
  The candidate pool is 17,497 windows, so the 300 are distinct start hours.
- **Evaluation:** 50 calendar days from 2025, sampled with seed 999. The candidate pool is
  364 days (see section 5).

Expected difference from the paper:

- Real Delhi weather is mostly dry. Only 39 of 300 training episodes (13 %) and 4 of 50
  evaluation episodes (8 %) contain rain. The paper's synthetic profiles contain rain far
  more often. With little rain, the rain penalties and feeder-capacity effects rarely trigger,
  so the DQN has little weather signal to learn from. Jain fairness may therefore rise less than
  the paper's 0.54 → 0.6–0.68.
- The fix is to report results separately for rain, cloudy, clear, and mixed episodes, and to
  consider oversampling rain episodes in training.

We have not yet run the DQN on these episodes. The result is a prediction, not a finding, until
it is run.

### Q3. Is the data enough?

For the paper's timescale, yes. The paper takes one step per hour and one episode per day, which
matches our hourly table. There are 26,304 hourly rows, or 1,096 full days, so nothing needs
interpolating.

- **Episode count:** 3 years give 1,096 distinct days. With rolling windows, the training
  pool is 17,497 start hours, so 300 episodes need no repetition of a start hour.
- **Interpolation:** not needed. Interpolation would invent intermediate hours with no
  observed weather behind them.
- **LSTM-generated intermediate data:** not recommended. The LSTM predicts only rain
  attenuation, not the inputs the DQN needs (temperature, humidity, rain, visibility). A second
  pass would not produce those inputs. Training the DQN on LSTM-generated weather would also be
  circular, since the DQN would learn the LSTM's smoothing rather than real weather.
- **Missing `itur` quantities:** these are parameters and formula decisions, not data gaps.
  They are the path-reduction factor and real slant geometry, the antenna diameter and
  efficiency, and a per-hour P.840 cloud term that still needs a formula using ERA5 `tclw`.
- **Real data gap:** sub-hour rain and scintillation. No public 10-minute data exists for this
  site. This stays a stated limitation.

## 3. Rolling episodes: what they allow and what they cost

Rolling windows let the training pool be much larger than 300 episodes, so every episode can
start at a different hour.

- **Overlap:** two windows shifted by one hour share 23 of their 24 hours. Sampling without
  replacement avoids repeating a start hour, but neighbouring episodes still share most of their
  weather. The write-up must state this.
- **Within-episode weather change:** real weather changes through the day, while the paper holds
  it fixed per episode. Rolling-window episodes therefore include rain starting or stopping
  partway through, which is more realistic but a different setup from the paper's.
- **Evaluation stays on calendar days:** 2025 days do not overlap, so the evaluation is clean.

## 4. Episode data produced

Files in `data/processed/episodes/`:

- `episodes_index.csv`: one row per episode, with split, start time, regime, maximum
  precipitation, mean cloud and visibility, rain-hour count, and summary itur values.
- `episodes_hourly.csv`: 8,400 rows (350 episodes × 24 hours), with the DQN state variables,
  the LSTM 1-hour-ahead forecast, and the itur labels.

Regime counts (regime thresholds: rain if max precipitation ≥ 1 mm/h; cloudy if mean cloud ≥ 70 %;
clear if mean cloud ≤ 30 %; otherwise mixed):

| Split | clear | cloudy | mixed | rain | total |
|---|---|---|---|---|---|
| train (2023–2024) | 126 | 52 | 83 | 39 | 300 |
| eval (2025) | 20 | 14 | 12 | 4 | 50 |

Per-split means:

| Split | max precip (mm/h) | mean cloud (%) | mean visibility (km) | rain hours | mean rain att. (dB) | mean scint. (dB) |
|---|---|---|---|---|---|---|
| train | 0.39 | 47.0 | 2.87 | 0.61 | 1.07 | 1.897 |
| eval | 0.97 | 48.2 | 3.39 | 0.56 | 1.10 | 1.968 |

The rain-attenuation means are not usable yet, for the reason in section 6.

## 5. Caveats specific to this run

1. **Training forecasts are in-sample.** The LSTM was trained on 2023–2024, so the LSTM forecasts
   used by training episodes are optimistic. The DQN will learn from forecasts that are better
   than it would get at deployment. Fix: produce out-of-fold forecasts for the training years
   before training the DQN.
2. **Last hours of 2025 have no forecast.** The export stops 6 hours before the end of the
   record, so 2025-12-31 is missing from the 364 eval days. The gap is small but should be
   fixed or stated.
3. **The 2023 start is dropped.** The first 24 hours have no LSTM forecast and are excluded.
4. **Evaluation regime sample is small.** Only 4 rain episodes exist in evaluation, so any
   rain-specific result will be noisy.

## 6. Known issue carried over: the rain-attenuation label

`L_EFF_KM = 66` is a placeholder. It gives rain attenuation up to 453 dB at 25 mm/h. Any DQN
reward or penalty that uses this label will be dominated by rain episodes. Do not train the DQN
on it until the path-reduction factor and real slant geometry are in place.

## 7. Next steps

1. Fix the path length (P.618 reduction factor and geometry) and re-run the label computation.
2. Produce out-of-fold LSTM forecasts for 2023–2024.
3. Add a DQN training script that reads `episodes_hourly.csv` and reports reward, Jain fairness,
   and outage, both overall and per regime.
4. Run it and compare against the paper's table, with the synthetic-weather caveat stated.
5. Decide whether to oversample rain episodes, and report the result both ways.
