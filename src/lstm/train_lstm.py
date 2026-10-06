"""
Phase 3 LSTM: hourly rain-attenuation forecaster for the Delhi feeder link.

Pipeline (run in WSL, env ~/quantum_env):
  1. Merge the hourly base table (NASA POWER + METAR) with ERA5 cloud liquid water
     (nearest grid cell 28.50N, 77.25E) for every year that has an ERA5 file.
  2. Label: rain attenuation (dB) = ITU-R P.838 specific attenuation at R = precip_mmh,
     times an effective slant path length L_EFF_KM (config constant, see note below).
  3. Windows: past L hours -> next H hours of rain attenuation.
  4. Chronological split (last year = test). Model: 2-layer LSTM, outputs H steps.
  5. Metrics vs persistence baseline (repeat last label). Writes forecasts CSV and model.

Note: L_EFF_KM is a placeholder for the slant-path length. It must be replaced with the
P.618 effective path length for the chosen geometry before results go in the paper.
"""

import argparse
import os

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import xarray as xr
from itur.models.itu618 import rain_attenuation as p618_rain_attenuation

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BASE_CSV = os.path.join(ROOT, "data", "processed", "delhi_hourly_TEMP.csv")
ERA5_DIR = os.path.join(ROOT, "data", "raw", "era5")
OUT_DIR = os.path.join(ROOT, "data", "processed", "lstm")
MODEL_DIR = os.path.join(ROOT, "models", "lstm")

SITE_LAT, SITE_LON = 28.61, 77.21
ERA5_LAT, ERA5_LON = 28.50, 77.25
FREQ_GHZ = 38.0
ELEV_DEG = 11.3          # worst-case feeder elevation from the paper
GATEWAY_KM = 0.05        # ground gateway height (50 m)

_path_cache: dict[float, float] = {}


def rain_path_attenuation_db(rain_mm_h: np.ndarray) -> np.ndarray:
    """ITU-R P.618 path rain attenuation (dB) for each hourly rain rate.

    The P.618 path runs from the gateway up to the rain height (P.839, 5.28 km at Delhi),
    so the path length comes from itur, not from a fixed constant. Results are cached by rate.
    """
    out = np.zeros(len(rain_mm_h))
    for i, rate in enumerate(np.round(rain_mm_h, 2)):
        if rate not in _path_cache:
            if rate <= 0:
                _path_cache[rate] = 0.0
            else:
                a = p618_rain_attenuation(SITE_LAT, SITE_LON, FREQ_GHZ, ELEV_DEG,
                                          hs=GATEWAY_KM, p=0.01, R001=float(rate))
                _path_cache[rate] = float(np.asarray(getattr(a, "value", a)).ravel()[0])
        out[i] = _path_cache[rate]
    return out

FEATURES = [
    "t2m_c", "rh2m_pct", "ps_kpa", "ws10m_ms", "precip_mmh", "cloud_amt_pct",
    "vis_km", "vis_missing", "wx_rain", "wx_fog", "cloud_liquid_water_kgm2", "hour_sin", "hour_cos",
    "doy_sin", "doy_cos",
]


def load_era5_tclw(years) -> pd.Series:
    """Hourly tclw at the nearest ERA5 grid cell, for the years with a file present."""
    parts = []
    for year in years:
        path = os.path.join(ERA5_DIR, f"era5_tclw_delhi_{year}.nc")
        if not os.path.exists(path):
            continue
        ds = xr.open_dataset(path)
        series = ds["tclw"].sel(latitude=ERA5_LAT, longitude=ERA5_LON, method="nearest")
        parts.append(pd.Series(series.values, index=pd.to_datetime(ds["valid_time"].values)))
    if not parts:
        raise FileNotFoundError("No ERA5 tclw files found in data/raw/era5/")
    return pd.concat(parts).sort_index()


def load_era5_tcc(years) -> pd.Series:
    """Hourly ERA5 total cloud cover in percent, used only where POWER CLOUD_AMT is missing."""
    parts = []
    for year in years:
        path = os.path.join(ERA5_DIR, f"era5_tcc_delhi_{year}.nc")
        if not os.path.exists(path):
            continue
        ds = xr.open_dataset(path)
        series = ds["tcc"].sel(latitude=ERA5_LAT, longitude=ERA5_LON, method="nearest") * 100.0
        parts.append(pd.Series(series.values, index=pd.to_datetime(ds["valid_time"].values)))
    return pd.concat(parts).sort_index() if parts else pd.Series(dtype=float)


def build_table(years) -> pd.DataFrame:
    df = pd.read_csv(BASE_CSV, parse_dates=["time_utc"])
    df = df[df["time_utc"].dt.year.isin(years)].copy()
    tclw = load_era5_tclw(years)
    df["cloud_liquid_water_kgm2"] = df["time_utc"].map(tclw)
    df = df.set_index("time_utc")
    # POWER CLOUD_AMT is missing from 2026-04-05 on; fill those hours from ERA5 total cloud cover.
    tcc = load_era5_tcc(years)
    missing_cloud = df["cloud_amt_pct"].isna()
    df["cloud_filled_era5"] = 0.0
    if missing_cloud.any() and not tcc.empty:
        fill_mask = missing_cloud & df.index.isin(tcc.index)
        df.loc[fill_mask, "cloud_amt_pct"] = tcc.reindex(df.index[fill_mask]).values
        df.loc[fill_mask, "cloud_filled_era5"] = 1.0
    # Visibility gaps (METAR) are forward-filled for up to 3 hours only.
    df["vis_km"] = df["vis_km"].ffill(limit=3)
    # Remaining gaps get a clear-visibility default, flagged so the model can tell.
    df["vis_missing"] = df["vis_km"].isna().astype(float)
    df["vis_km"] = df["vis_km"].fillna(10.0)
    # No METAR report means no observed weather code; flags default to 0 (see vis_missing).
    df[["wx_rain", "wx_fog"]] = df[["wx_rain", "wx_fog"]].fillna(0.0)
    # Rows with missing POWER values are kept (not dropped), so the 24-hour windows stay
    # contiguous. Windows that touch a missing value are skipped by the window builder.
    hour = df.index.hour
    doy = df.index.dayofyear
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    # Label: ITU-R P.618 path rain attenuation for the hourly rain rate (NaN where rain is missing).
    precip = df["precip_mmh"].values
    label = rain_path_attenuation_db(np.nan_to_num(precip, nan=0.0))
    df["rain_att_db"] = np.where(np.isnan(precip), np.nan, label)
    return df


def make_windows(x: np.ndarray, y: np.ndarray, past: int, horizon: int):
    xs, ys = [], []
    for t in range(past, len(x) - horizon + 1):
        xs.append(x[t - past:t])
        ys.append(y[t:t + horizon])
    return np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32)


class RainLSTM(nn.Module):
    def __init__(self, n_in: int, horizon: int, hidden: int = 64, layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(n_in, hidden, num_layers=layers, batch_first=True, dropout=0.1)
        self.head = nn.Linear(hidden, horizon)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--years", nargs="+", type=int, default=[2023, 2024, 2025])
    p.add_argument("--past", type=int, default=24)
    p.add_argument("--horizon", type=int, default=6)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch", type=int, default=128)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    df = build_table(args.years)
    years_present = sorted(df.index.year.unique())
    print(f"Rows: {len(df)}  years: {years_present}")

    # Chronological split. With 2+ years the last year is test; with one year, 70/15/15.
    if len(years_present) >= 2:
        train_df = df[df.index.year < years_present[-1]]
        test_df = df[df.index.year == years_present[-1]]
    else:
        n = len(df)
        train_df = df.iloc[: int(0.7 * n)]
        test_df = df.iloc[int(0.85 * n) - args.past:]

    mean = train_df[FEATURES].mean()
    std = train_df[FEATURES].std().replace(0, 1.0)
    x_train = ((train_df[FEATURES] - mean) / std).values
    x_test = ((test_df[FEATURES] - mean) / std).values
    y_train = train_df["rain_att_db"].values
    y_test = test_df["rain_att_db"].values

    xtr, ytr = make_windows(x_train, y_train, args.past, args.horizon)
    xte, yte = make_windows(x_test, y_test, args.past, args.horizon)
    print(f"Train windows: {len(xtr)}  Test windows: {len(xte)}")

    model = RainLSTM(len(FEATURES), args.horizon)
    opt = torch.optim.Adam(model.parameters(), lr=5e-4)
    # Huber loss: the rain-attenuation label is heavy-tailed, so squared error reacts too strongly to spikes.
    loss_fn = nn.HuberLoss(delta=1.0)
    ds = torch.utils.data.TensorDataset(torch.tensor(xtr), torch.tensor(ytr))
    loader = torch.utils.data.DataLoader(ds, batch_size=args.batch, shuffle=True)

    for epoch in range(args.epochs):
        model.train()
        for xb, yb in loader:
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            opt.step()
        if (epoch + 1) % 5 == 0:
            print(f"epoch {epoch + 1}: last batch loss {loss.item():.4f}")

    model.eval()
    with torch.no_grad():
        pred = model(torch.tensor(xte)).numpy()

    mae = np.mean(np.abs(pred - yte))
    rmse = np.sqrt(np.mean((pred - yte) ** 2))
    # Persistence baseline: repeat the last observed label over the horizon.
    last_label = y_test[args.past - 1: len(y_test) - args.horizon]
    persist = np.repeat(last_label[: len(yte)][:, None], args.horizon, axis=1)
    p_mae = np.mean(np.abs(persist - yte))
    p_rmse = np.sqrt(np.mean((persist - yte) ** 2))

    print(f"LSTM       MAE {mae:.4f} dB  RMSE {rmse:.4f} dB")
    print(f"Persistence MAE {p_mae:.4f} dB  RMSE {p_rmse:.4f} dB")

    torch.save(model.state_dict(), os.path.join(MODEL_DIR, "rain_lstm.pt"))
    out = pd.DataFrame(pred, columns=[f"pred_h{h + 1}" for h in range(args.horizon)])
    out.insert(0, "true_h1", yte[:, 0])
    out.to_csv(os.path.join(OUT_DIR, "lstm_test_forecasts.csv"), index=False)
    print(f"Saved model -> {MODEL_DIR}, forecasts -> {OUT_DIR}")


if __name__ == "__main__":
    main()
