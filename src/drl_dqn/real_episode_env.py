"""
RealEpisodeEnv: the paper's association MDP driven by real hourly data.

Each episode is one 24-hour window from data/processed/episodes/episodes_hourly.csv. Per hour
the environment uses the real values:
  - rain rate (NASA POWER precipitation) and visibility (METAR) as the DQN weather state,
  - the ITU-R P.618 path rain attenuation (train_lstm.rain_path_attenuation_db) as the feeder
    rain loss, replacing the paper's k*R^alpha model (see haps_association_env.py),
  - the LSTM's 1-hour-ahead rain-attenuation forecast as one extra state feature.

Users, HAPS geometry, and battery dynamics are as in HAPSAssociationEnv. Episodes are served
in list order and wrap around.
"""

import os
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from haps_association_env import HAPSAssociationEnv, RAIN_MM_H_MAX, VIS_M_MAX  # noqa: E402

LSTM_DB_MAX = 100.0  # normalises the LSTM forecast (dB) into [0, 1]
EPISODES_CSV = os.path.abspath(os.path.join(HERE, "..", "..", "data", "processed", "episodes", "episodes_hourly.csv"))


def load_episodes(split: str, path: str = EPISODES_CSV) -> list[dict]:
    """Return the episodes of one split as dicts of per-hour arrays, in episode_id order."""
    df = pd.read_csv(path, parse_dates=["time_utc"])
    df = df[df["split"] == split].sort_values(["episode_id", "time_utc"])
    episodes = []
    for ep_id, grp in df.groupby("episode_id", sort=True):
        episodes.append({
            "episode_id": int(ep_id),
            "regime": grp["regime"].iloc[0],
            "rain_mm_h": grp["precip_mmh"].fillna(0.0).values,
            "vis_km": grp["vis_km"].fillna(10.0).values,
            "hour": grp["time_utc"].dt.hour.values.astype(float),
            "rain_att_db": grp["rain_att_db"].values,
            "lstm_db": grp["lstm_pred_h1"].values,
        })
    return episodes


class RealEpisodeEnv(HAPSAssociationEnv):
    def __init__(self, episodes, use_lstm=True, **kwargs):
        super().__init__(weather_generator=None, **kwargs)
        self.episodes = episodes
        self.use_lstm = use_lstm
        self._next = 0
        self.ep = None
        # The base class allocates its state with state_dim, so keep its width for slicing.
        self.base_state_dim = self.state_dim
        if use_lstm:
            self.state_dim += 1
        self.rain_att_override_db = None
        # Original design: each HAPS relays through its own Gateway (no shared-capacity model).
        self.shared_gateway = False

    def _set_weather(self, k: int) -> None:
        """Load hour k of the current episode into the environment's weather fields."""
        ep = self.ep
        self.weather_state = SimpleNamespace(
            rain_mm_h=float(ep["rain_mm_h"][k]),
            visibility_km=float(ep["vis_km"][k]),
            hour_of_day=float(ep["hour"][k]),
        )
        self.hour_of_day = float(ep["hour"][k])
        self.rain_att_override_db = float(ep["rain_att_db"][k])
        self._lstm_db = float(ep["lstm_db"][k])

    def _states_real(self) -> np.ndarray:
        s = super()._states()[:, : self.base_state_dim]
        if self.use_lstm:
            lstm_col = np.full((self.n_users, 1), np.clip(self._lstm_db / LSTM_DB_MAX, 0.0, 1.0))
            s = np.hstack([s, lstm_col])
        return s

    def reset(self):
        self.ep = self.episodes[self._next % len(self.episodes)]
        self.episode_id = self.ep["episode_id"]
        self.regime = self.ep["regime"]
        self._next += 1
        self.t = 0
        self.soc = self.rng.uniform(self.soc_init_range[0], self.soc_init_range[1], size=self.n_haps)
        self._compute_static_sinr_and_distance()
        self._set_weather(0)
        return self._states_real()

    def step(self, actions):
        self._set_weather(self.t)  # current hour's real values for the reward
        _, rewards, done, info = super().step(actions)
        if not done:
            self._set_weather(self.t)  # next hour's real values for the returned state
        return self._states_real(), rewards, done, info


__all__ = ["RealEpisodeEnv", "load_episodes", "RAIN_MM_H_MAX", "VIS_M_MAX"]
