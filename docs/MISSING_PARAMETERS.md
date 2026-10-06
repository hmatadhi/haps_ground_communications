# Missing Parameters: Analysis and Actions

Question: is the data enough? Rain and scintillation data should be available. Which
parameters are still missing, and what should be done about each?

Short answer: the observed data is sufficient for the hourly work. Most of what is still
missing is model parameters and model behaviour, not data. Scintillation was a model problem:
the `itur` 0.4.0 wet term drops the humidity dependence, and the fade steps have been rewritten
directly (`src/lstm/scintillation_p618.py`), so it now responds to weather.

## 1. Data that exists

| Quantity | Source | Resolution | Status |
|---|---|---|---|
| Rain rate | NASA POWER PRECTOTCORR | hourly | complete 2023–2025; 2026 has 24 h gap |
| Rain occurrence | METAR weather codes (RA, DZ, TS) | ~hourly | complete; 85 % agreement with POWER on 2026 |
| Visibility | METAR | ~hourly | 0.5 % missing, imputed (flagged) |
| Temperature, humidity, pressure, wind | NASA POWER | hourly | complete 2023–2025 |
| Cloud amount | NASA POWER CLOUD_AMT | hourly | missing from 2026-04-05; ERA5 total cloud cover fill pending |
| Cloud liquid water | ERA5 tclw | hourly, 0.25° | complete 2023–2026 |
| Rain rate statistics | itur P.837 (model) | statistical | available |

Conclusion: rain and visibility data are enough for hourly episodes. Nothing needs
interpolating for the paper's one-hour step.

## 2. What is actually missing

### 2.1 Scintillation: a library problem, now corrected

No measured scintillation time series exists for this site, and none is needed, since the
paper uses the ITU-R P.618 formula. The original `itur` 0.4.0 output did not respond to weather
because of two problems:

- Our calls passed temperature in kelvin. The P.453 functions take degrees Celsius.
- `itur`'s wet-term function multiplies N_wet by 1e-6, so the humidity effect is effectively
  zero, and the fade stayed at about 0.62 dB.

The P.618 steps are now written out in `src/lstm/scintillation_p618.py`, using the P.453 wet
term without that factor. The corrected 1 % fade at 38 GHz, 11.3°:

| Change | Fade (dB), corrected |
|---|---|
| baseline (15 °C, 60 % RH, 1010 hPa) | 1.47 |
| relative humidity 20 % / 95 % | 0.90 / 1.96 |
| temperature 0 °C / 35 °C | 0.96 / 3.07 |
| elevation 30° (instead of 11.3°) | 0.47 |

Previously reported values (0.62 dB, flat) came from the library bug and are superseded.

Temperature, humidity, and pressure change the result by less than 0.001 dB. A physical
scintillation model should respond to humidity, because wet refractivity drives scintillation.
So the implementation is either not using those inputs at this frequency, or the inputs are
being passed in a form it ignores.

Other concerns:

- The paper's scintillation figure is 2–4 dB at 0.01 % (line ~312), and the penalty of
  8.95 dB (line ~502). The itur value is 0.62 dB at 1 %. These are not the same
  exceedance level, but the gap is large enough that the scintillation section needs a
  second check against the P.618 text.
- The scintillation head of the LSTM now has a weather-dependent target (0.78–3.50 dB hourly).

Action: check the itur P.618 scintillation implementation against the ITU-R P.618 text
(wet refractivity, sigma-ref, and the time-percentage scaling). If it still ignores weather,
either fix the call (units and argument order) or implement the sigma-ref calculation
directly from the recommendation.

### 2.2 Rain path: the paper's model is wrong

| Rain rate | P.618 path (itur) | Paper environment model | Paper worked example |
|---|---|---|---|
| 1 mm/h | 12.4 dB | 2.1 dB | – |
| 10 mm/h | 53.0 dB | 17.4 dB | 5.9 dB |
| 25 mm/h | 88.0 dB | 40.5 dB | 15.2 dB |

The paper's worked example (5.9 dB at 10 mm/h) is not reproduced by the standard model,
either in the paper's own geometry or in ours. The environment model (`k = 0.0315`,
`alpha = 0.921`, 66.3 km) also differs from the P.838 value at 38 GHz (k = 0.40, alpha = 0.88).

Action: replace the environment's rain-loss model with the P.618 path attenuation. This is
done for the real-episode environment (`rain_att_override_db`). The paper's synthetic-weather
environment still uses the old model and should be corrected, which changes the paper's
reported rain losses.

### 2.3 Path geometry

- Rain height: 5.28 km at the site (P.839). The path through rain is
  (5.28 − 0.05) / sin(11.3°) ≈ 26.7 km, not the 102 km × 0.65 used in the environment.
- Gateway height: 50 m (paper).
- Elevation: 11.3° (paper's worst case). The gateway elevation for the real link is not
  yet confirmed, and it drives both the rain path and the scintillation (see 2.1).

Action: confirm the gateway location and elevation before the rain numbers go into the paper.

### 2.4 Antenna parameters

Scintillation depends on antenna diameter (0.60 to 2.00 m gives 0.63 to 0.60 dB) and
efficiency. Both are assumed (1 m, 0.5). These are design choices, not measured quantities.

Action: state the assumed values in the paper, or take them from the feeder-link design.

### 2.5 Cloud attenuation

`itur` P.840 gives a site statistic (16.7 dB at 1 %), not an hourly value. The hourly term
needs a formula that uses the ERA5 cloud liquid water. The P.840 specific attenuation
depends on temperature and frequency and is not yet wired into the model. This is a
formula to write, not data to collect.

Action: write the hourly P.840 term from tclw and temperature, and check it against the
site statistic.

### 2.6 Sub-hour variability

Scintillation and short rain bursts vary within the hour. No public 10-minute data exists for
this site. The hourly model cannot capture these.

Action: state this as a limitation. If 10-minute data is needed later, it has to come from a
local station or a measurement campaign.

## 3. Priority

1. Scintillation model check (2.1): blocks the second LSTM head.
2. Rain model in the paper (2.2): changes the paper's reported numbers.
3. Gateway geometry (2.3): drives both rain and scintillation.
4. Hourly P.840 cloud term (2.5): completes the feeder-link budget.
5. Antenna values (2.4): stated assumptions only.
6. Sub-hour data (2.6): limitation, no action now.
