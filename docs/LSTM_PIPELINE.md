# Phase 3 LSTM Pipeline: Initial Documentation

Status: initial, pre-paper. Values marked PLACEHOLDER must be replaced before any number is
reported.

## 1. Purpose

Forecast the Ka-band (38 GHz) feeder-link rain attenuation over the next 6 hours at a Delhi
site, so the DQN association agent can see forecast fade margins instead of static weather.
Scintillation is the planned second output head and is not built yet.

Data flow is one-way: LSTM forecast -> DQN state. The DQN never feeds the LSTM.

## 2. Site and period

- Site: Delhi, 28.61 N, 77.21 E (Safdarjung, VIDP).
- Period: 2023-01-01 to 2025-12-31, hourly, UTC.
- Split: train 2023-2024, test 2025. Normalisation statistics come from the training years
  only.

## 3. Inputs (what the LSTM receives)

| Feature | Source | Native resolution | Notes |
|---|---|---|---|
| t2m_c | NASA POWER | hourly | air temperature, deg C |
| rh2m_pct | NASA POWER | hourly | relative humidity |
| ps_kpa | NASA POWER | hourly | surface pressure |
| ws10m_ms | NASA POWER | hourly | 10 m wind speed |
| precip_mmh | NASA POWER | hourly | reanalysis precipitation; weak on heavy rain |
| cloud_amt_pct | NASA POWER | hourly | cloud fraction |
| vis_km | METAR (VIDP) | irregular, hourly | 3 h forward fill, then 10 km default |
| vis_missing | derived | hourly | 1 where visibility was imputed |
| wx_rain | METAR weather codes | irregular | RA/DZ/TS in the hour |
| wx_fog | METAR weather codes | irregular | FG/BR in the hour |
| cloud_liquid_water_kgm2 | ERA5 `tclw` | hourly | nearest cell 28.50 N, 77.25 E, 0.25 deg grid |
| hour_sin, hour_cos | derived | hourly | time of day |
| doy_sin, doy_cos | derived | hourly | season |

Window: 24 input hours, forecasting 6 hours ahead.

## 4. Target (what the LSTM predicts)

Rain attenuation in dB per hour:

    rain_att_db = gamma_R(precip_mmh, 38 GHz, 11.3 deg) x L_EFF_KM

- gamma_R: ITU-R P.838 specific attenuation, computed by `itur`.
- L_EFF_KM = 66 km. PLACEHOLDER. This is the paper's worst-case slant length without the
  P.618 path-reduction factor. Result: the label reaches 453 dB at 25 mm/h, which is not
  physical. See section 7.

Scintillation (planned second head): ITU-R P.618 tropospheric scintillation at 1 % exceedance.
Not yet trained.

## 5. Scripts (run in WSL, env `~/quantum_env`)

All scripts live in `src/lstm/`.

| Script | What it does | Output |
|---|---|---|
| build_hourly_temp.py | Merges NASA POWER and METAR into the hourly base table. Writes a placeholder cloud-water column. | data/processed/delhi_hourly_TEMP.csv |
| download_era5_tclw.py | Downloads ERA5 `tclw` per year from CDS. Skips years already on disk. | data/raw/era5/era5_tclw_delhi_{year}.nc |
| build_era5_csv.py | Extracts the nearest cell to one CSV. | data/raw/era5/weatherDataTCLWEra5Delhi.csv |
| train_lstm.py | Builds the table (real ERA5 `tclw`), labels, windows, trains the LSTM, prints metrics. | models/lstm/rain_lstm.pt, data/processed/lstm/lstm_test_forecasts.csv |
| export_lstm_forecasts.py | Runs the trained model over the full record. | data/processed/lstm/lstm_dqn_inputs.csv |
| compute_itur_hourly.py | Hourly itur quantities: P.838, P.676, P.618, P.840. | data/processed/itur/itur_hourly_properties.csv |
| compare_properties.py | Compares LSTM and itur properties and computes persistence errors. | data/processed/comparison/properties_comparison.csv |
| inspect_itur.py | Lists itur function signatures. | stdout |
| check_era5_inputs.py | Checks coverage, checksums, and nearest-cell values. | stdout |
| check_base_nans.py | Missing values per column in the base table. | stdout |
| check_library_read.py | Library versions and the ERA5 read. | stdout |

Run order: build_hourly_temp -> download_era5_tclw -> build_era5_csv -> train_lstm ->
export_lstm_forecasts -> compute_itur_hourly -> compare_properties.

## 6. Results so far

Test split = 2025, 6-hour horizon, MAE in dB. Persistence repeats the last observed label.

| Horizon | LSTM MAE | Persistence MAE |
|---|---|---|
| +1 h | 2.06 | 1.45 |
| +2 h | 2.40 | 2.33 |
| +3 h | 2.66 | 2.87 |
| +4 h | 2.86 | 3.21 |
| +5 h | 2.98 | 3.49 |
| +6 h | 3.05 | 3.73 |

Interpretation: the LSTM beats persistence from 2 h onward and loses at 1 h. The earlier
headline (LSTM 2.68 vs persistence 2.85 dB) is the average over all six horizons. Overall
RMSE is 11.6 dB against 14.1 dB for persistence. That is dominated by a few extreme hours
caused by the placeholder path length.

## 7. Known issues

1. **L_EFF_KM = 66 km was a placeholder (now replaced).** The label was specific rain
   attenuation (dB/km, ITU-R P.838) multiplied by a fixed 66 km path. The units are dB of
   signal loss along the feeder path caused by rain. The largest hourly value was 453 dB, at
   a peak rain rate of about 25 mm/h (6.86 dB/km × 66 km). A loss of that size leaves
   essentially no signal at the receiver, so the placeholder was physically meaningless.
   It also ignored the rain height (5.28 km at Delhi), so the path was far too long. The
   label is now the P.618 path attenuation, which gives about 88 dB at 25 mm/h.
2. **Scintillation was a library problem, now corrected.** The original `itur` output was flat
   at about 0.62 dB because of a 1e-6 factor in its wet-term function, and our calls passed
   temperature in kelvin. The steps are now written in `scintillation_p618.py`, which gives
   0.78–3.50 dB hourly over 2023–2025. The path-length term (Eq. 46) still needs checking
   against the ITU text.
3. **Antenna parameters are assumed:** diameter 1 m and efficiency 0.5 (ANT_D_M, ETA) for
   the scintillation averaging. PLACEHOLDER.
4. **Precipitation is reanalysis (NASA POWER).** It is weak on heavy rain and should be
   checked against the METAR rain codes.
5. **Visibility gaps.** 160 hours (0.6 %) have no METAR. They are imputed as 10 km and
   flagged with vis_missing.
6. **Cloud liquid water is a site-grid value** at 0.25 deg resolution. It is a regional
   average, not a point measurement.
7. **Hourly resolution.** The LSTM cannot capture sub-hour scintillation. The paper must state
   this.
8. **Only one test year and one site.** The results describe 2025 at Delhi and nothing else.

## 8. itur quantities: what is computed and what is still missing

| Quantity | itur model | Hourly | In LSTM | Status |
|---|---|---|---|---|
| Specific rain attenuation | P.838 | yes | label | computed, path length placeholder |
| Path rain attenuation | P.618 rain_attenuation | statistical | no | not computed; needs path reduction |
| Gaseous slant-path attenuation | P.676 | yes | no | computed, 0.9-4.4 dB |
| Scintillation (1 %) | P.618 steps in scintillation_p618.py | yes | planned head | computed, weather-dependent (0.78–3.50 dB) |
| Cloud/fog (1 %) | P.840 cloud_attenuation | site constant | no | computed, 16.7 dB constant |
| Rain-rate statistics | P.837 rainfall_rate | statistical | no | not computed |
| Water-vapour statistics | P.836 / P.835 | statistical | no | not used |

Cloud attenuation hourly (P.840 with tclw) is not computed. The `itur` P.840 API gives a
site statistic, not a per-hour value. A per-hour formula needs to be written.

## 9. Before the paper

- [ ] Replace L_EFF_KM with the P.618 path-reduction result and real geometry.
- [x] Verify scintillation input units against itur and check the output (corrected; see item 2).
- [ ] Check the scintillation path-length term (Eq. 46) against the ITU-R P.618 text.
- [ ] Replace ANT_D_M and ETA with the real feeder antenna values.
- [ ] Decide whether the LSTM is also trained on a per-hour P.840 cloud term.
- [ ] Add 2-3 test years, or cross-validate by year, before claiming generality.
- [ ] Add the scintillation head or state that it's future work.
- [ ] Phase 3 section in `phase3.tex` (currently commented out).

## 10. References used

- ITU-R P.838, P.618, P.676, P.840, P.837, P.835, P.836 (via `itur` 0.4.0)
- ERA5: Hersbach et al. (2020), Copernicus Climate Change Service (C3S), data on CDS
- NASA POWER hourly meteorology
- Iowa Mesonet ASOS/METAR archive (VIDP)
- Ka-band rain-fade LSTM: arXiv 2110.00695
- Tropospheric scintillation RNN: BGU, "Deep Learning based Scintillation Prediction for
  Satellite Link using Measured Data"
