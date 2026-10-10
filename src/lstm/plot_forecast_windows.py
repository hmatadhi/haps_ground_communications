"""
One chart over a 300-hour window of 2026, with four series in different colours:

  1. Real (downloaded): observed P.618 rain attenuation from downloaded NASA POWER precipitation.
  2. LSTM predicted: the LSTM 1-hour-ahead forecast for each hour, made from the past 24 hours.
  3. Persistence: the value of the previous hour (P.618 from the observed rain one hour earlier).
  4. PreLSTM: synthetic. Hourly rain rates drawn at random from the ITU-R P.837 rain-rate
     statistics for the Delhi site, converted to attenuation with ITU-R P.618. No observed data.

The window is the 300 consecutive hours of 2026 with the largest total rain attenuation. The
301st hour (first hour after the window) is marked for each series.

Output: data/processed/figures/forecast_comparison_300h.png

Run in WSL (env ~/quantum_env): python src/lstm/plot_forecast_windows.py
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from itur.models.itu837 import rainfall_rate  # noqa: E402

from train_lstm import SITE_LAT, SITE_LON, rain_path_attenuation_db  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FORECASTS = os.path.join(ROOT, "data", "processed", "lstm", "lstm_dqn_inputs.csv")
OUT_DIR = os.path.join(ROOT, "data", "processed", "figures")
OUT_PATH = os.path.join(OUT_DIR, "forecast_comparison_300h.png")
WINDOW = 300
SEED = 0


def scalar(x) -> float:
    return float(np.asarray(getattr(x, "value", x)).ravel()[0])


def prelstm_series(n: int, rng: np.random.Generator) -> np.ndarray:
    """Random hourly rain rates from P.837 exceedance statistics, converted by P.618."""
    p_percent = rng.uniform(0.001, 100.0, size=n)  # exceedance level drawn uniformly
    rates = np.array([max(scalar(rainfall_rate(SITE_LAT, SITE_LON, p)), 0.0) for p in p_percent])
    return rain_path_attenuation_db(rates)


def main() -> None:
    fc = pd.read_csv(FORECASTS, parse_dates=["issue_time_utc"])
    v = fc[fc["split"] == "verify_2026"].sort_values("issue_time_utc").reset_index(drop=True)

    # Row i: issue time t_i; true_h1 is the P.618 value for hour t_i + 1; pred_h1 is the LSTM
    # forecast for that hour. Persistence for hour t_i + 1 is the previous hour's P.618 value.
    v["real"] = v["true_h1"]
    v["lstm"] = v["pred_h1"]
    v["persist"] = v["true_h1"].shift(1)
    v["hour"] = v["issue_time_utc"] + pd.Timedelta(hours=1)
    v = v.dropna(subset=["real", "lstm", "persist"]).reset_index(drop=True)

    rain_sum = v["real"].rolling(WINDOW + 1).sum().shift(-WINDOW)
    start = max(0, int(rain_sum.idxmax()) - WINDOW + 1)
    window = v.iloc[start:start + WINDOW + 1].reset_index(drop=True)
    main_part = window.iloc[:WINDOW]
    last = window.iloc[WINDOW]

    rng = np.random.default_rng(SEED)
    pre = prelstm_series(WINDOW + 1, rng)
    x = np.arange(WINDOW + 1)

    mae_persist = np.mean(np.abs(main_part["persist"] - main_part["real"]))
    mae_lstm = np.mean(np.abs(main_part["lstm"] - main_part["real"]))
    mae_pre = np.mean(np.abs(pre[:WINDOW] - main_part["real"]))

    title_range = (f"{window['hour'].iloc[0]:%Y-%m-%d %H:%M} to "
                   f"{window['hour'].iloc[WINDOW - 1]:%Y-%m-%d %H:%M} UTC")

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(x[:WINDOW], main_part["real"], "-", color="black", lw=1.4,
            label="Real (downloaded P.618)")
    ax.scatter(x[:WINDOW], main_part["lstm"], s=12, color="tab:blue",
               label=f"LSTM predicted (MAE {mae_lstm:.2f} dB)")
    ax.scatter(x[:WINDOW], main_part["persist"], s=12, color="tab:orange",
               label=f"Persistence, previous hour (MAE {mae_persist:.2f} dB)")
    ax.scatter(x[:WINDOW], pre[:WINDOW], s=12, color="tab:green", marker="s",
               label=f"PreLSTM, random from ITU P.837 (MAE {mae_pre:.2f} dB)")
    ax.scatter([WINDOW], [last["real"]], s=90, marker="*", color="black", zorder=6,
               label="301st hour: real")
    ax.scatter([WINDOW], [last["lstm"]], s=50, marker="o", facecolors="none",
               edgecolors="tab:blue", zorder=6, label="301st hour: LSTM")
    ax.scatter([WINDOW], [last["persist"]], s=50, marker="o", facecolors="none",
               edgecolors="tab:orange", zorder=6, label="301st hour: persistence")
    ax.scatter([WINDOW], [pre[WINDOW]], s=50, marker="s", facecolors="none",
               edgecolors="tab:green", zorder=6, label="301st hour: PreLSTM")

    ax.set_title(f"Real, LSTM, persistence and PreLSTM over 300 hours\n{title_range}")
    ax.set_xlabel("Hour in window")
    ax.set_ylabel("Rain attenuation (dB, P.618 at 38 GHz, 11.3°)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    fig.tight_layout()
    os.makedirs(OUT_DIR, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150)
    plt.close(fig)

    print(f"Window: {title_range}")
    print(f"MAE over 300 h: LSTM {mae_lstm:.3f} dB | persistence {mae_persist:.3f} dB | "
          f"PreLSTM {mae_pre:.3f} dB")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
