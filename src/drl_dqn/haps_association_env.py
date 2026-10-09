"""
haps_association_env.py
========================
Per-user platform-association MDP for the 3-HAPS constellation, matching the
paper's "Phase 2: DRL for User Association" section (HAPS_AI_HW_ChannelModel.tex):

  * 3 HAPS nodes, fixed, equilateral-triangle constellation (65 km spacing),
    geometry from channel_model.haps_constellation_geometry().
  * N ground users, static for the episode, each independently picks each
    hour how to be served: directly by one of the 3 HAPS (action 0-2), via a
    decode-and-forward relay through that HAPS's Gateway (action 3-5), or via
    a decode-and-forward relay through a UAV hovering near the user (action
    6-8), i.e. action in {0, ..., 8} = 3 * n_haps.
  * Per-user state (18-dim): SINR to each of the 3 HAPS (dB), horizontal
    distance to each (km), each HAPS's battery SoC (%), rain rate, visibility,
    hour of day, relay capacity via each HAPS's Gateway (bps/Hz, normalized),
    and relay capacity via a UAV served by each HAPS (bps/Hz, normalized) --
    see relay design note below.
  * Reward: the paper's exact eq. (Phase 2, Reward Function) --
    0.5*L_agg + 0.3*Jain - 0.2*P_eng + severe/degraded/low-battery penalties,
    computed once per step on the SINR (or SINR-equivalent, for relay users)
    each user actually gets from its chosen path, then de-rated for
    rain-degraded feeder (backhaul) capacity.
    L_agg and Jain reuse reward_function.py's linear-SINR helpers (tested);
    the outage penalties are implemented here as the paper's own two-tier
    *fractional* penalty (-100 x fraction severe, -20 x fraction degraded),
    NOT reward_function.py's own compute_network_reward(), whose flat
    "-100 x raw count" blows up with N_USERS and empirically collapsed
    training into a degenerate always-pick-HAPS-0 policy (see
    docs/PHASE2_ASSOCIATION_PLAN.md) -- a single user's action then barely
    moves the aggregate reward, so the network never learns to discriminate
    between users.
  * Battery: battery_model.HAPSBatteryModel, updated once per simulated hour
    per HAPS from the aggregate load of its currently-associated users
    (direct or relay -- both draw from the serving HAPS's battery).

Relay design (HAPS -> Gateway -> UE): each HAPS has one Gateway, colocated at
its ground nadir point (matching the short feeder-distance convention used in
src/generators/generate_pathloss_table.py and generate_relay_table.py), so the
existing per-user/per-HAPS horizontal distance is reused directly as the
Gateway->UE access-hop distance. End-to-end relay capacity is
decode-and-forward, C_relay = min(C_feeder, C_access), via
channel_model.relay_two_hop_capacity_bps_hz().

Relay design (HAPS -> UAV -> UE): each HAPS can also serve a user via a
relaying UAV hovering near that user's location (horizontal distance from the
serving HAPS reused directly as the UAV's HAPS-relative position, matching
generate_pathloss_table.py's "Relay (HAPS->UAV)" sweep convention). Hop 1
(HAPS->UAV, 38 GHz) reuses the feeder-style scintillation model; Hop 2
(UAV->UE, 2 GHz) reuses the landscape-dependent LoS/NLoS UAV access model.
End-to-end capacity is again decode-and-forward via
channel_model.uav_relay_two_hop_capacity_bps_hz(). This is the paper's
previously-unmodeled User -> UAV -> HAPS relay tier, now added as a routing
decision (an alternative path to the serving HAPS) rather than as a cascaded
amplification gain within a single SINR equation -- see channel_model.py's
module docstring ("NOT MODELED" / "MODELED" notes).

Unlike haps_env.py (a different, unrelated 1-HAPS/3-mobile-UAV MDP), users
and HAPS are both static within an episode, so each user's raw SINR to each
HAPS is constant for the whole episode -- only battery state-of-charge and
weather evolve hour to hour. That's intentional: the paper's MDP is about
choosing (and rebalancing) association under a changing energy budget, not
about tracking user mobility.
"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR = os.path.join(_THIS_DIR, "..", "models")
for _p in (_THIS_DIR, _MODELS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import channel_model as cm
from battery_model import HAPSBatteryModel, feeder_link_rain_effect_on_capacity
from reward_function import compute_aggregate_throughput, compute_jain_fairness_index

NODE_KEYS = ["serving", "interferer1", "interferer2"]  # HAPS 0, 1, 2

# Paper eq. (obs-space) bounds, used only to normalise state features.
SINR_DB_MIN, SINR_DB_MAX = -20.0, 30.0
DIST_KM_MAX = 100.0
RAIN_MM_H_MAX = 50.0
VIS_M_MAX = 10_000.0
CAPACITY_BPS_HZ_MAX = 20.0  # normalisation bound for relay capacity features

# Fixed feeder-hop geometry for the Gateway relay path: the Gateway is
# colocated near each HAPS's ground nadir point, matching the short
# feeder-distance convention in generate_pathloss_table.py /
# generate_relay_table.py, so elevation is close to 90 deg regardless of the
# (short) horizontal offset.
RELAY_FEEDER_DIST_KM = 0.1
RELAY_FEEDER_ELEVATION_DEG = 89.0


class HAPSAssociationEnv:
    def __init__(self,
                 n_users=50,
                 constellation_spacing_km=65.0,
                 service_radius_km=100.0,
                 env="urban",
                 max_steps=24,                 # one step = one simulated hour
                 p_per_user_w=1.0,             # ASSUMED per-user serving power draw
                 soc_init_range=(30.0, 100.0),
                 severe_threshold_db=-2.0,    # paper's "severe outage" threshold
                 degraded_threshold_db=0.0,   # paper's "degraded service" threshold
                 low_battery_soc_pct=10.0,    # paper's low-battery penalty threshold
                 omega_1=0.5, omega_2=0.3, omega_3=0.2,
                 weather_generator=None,
                 seed=0):
        self.n_users = n_users
        self.spacing_km = constellation_spacing_km
        self.service_radius_m = service_radius_km * 1000.0
        self.env = env
        self.max_steps = max_steps
        self.p_per_user_w = p_per_user_w
        self.soc_init_range = soc_init_range
        self.severe_threshold_db = severe_threshold_db
        self.degraded_threshold_db = degraded_threshold_db
        self.low_battery_soc_pct = low_battery_soc_pct
        self.omega_1, self.omega_2, self.omega_3 = omega_1, omega_2, omega_3
        self.weather_generator = weather_generator
        self.rng = np.random.default_rng(seed)

        self.n_haps = 3
        self.n_actions = 3 * self.n_haps  # direct {0,1,2} + relay-via-Gateway {3,4,5} + relay-via-UAV {6,7,8}
        self.state_dim = 3 + 3 + 3 + 3 + 3 + 3  # SINR + dist + SoC + (rain, vis, hour) + gw relay capacity + uav relay capacity

        self.battery_model = HAPSBatteryModel(battery_capacity_wh=12_000.0)  # paper's C_battery (eq. battery-balance)

        nodes = cm.haps_constellation_geometry(spacing_km=self.spacing_km, h_haps_m=cm.HAPS_ALT_M)
        self.node_xy_m = np.array([[nodes[k][0], nodes[k][1]] for k in NODE_KEYS])  # (3, 2)

        self.weather_state = None
        self.t = 0
        self.hour_of_day = 0.0
        self.soc = np.zeros(self.n_haps)
        self.user_xy_m = None
        self._sinr_db = None   # (n_users, 3), cached per episode (static geometry)
        self._dist_km = None   # (n_users, 3)
        self._relay_capacity = None  # (n_users, 3) bps/Hz, cached per episode (Gateway relay)
        self._uav_relay_capacity = None  # (n_users, 3) bps/Hz, cached per episode (UAV relay)

    # ------------------------------------------------------------------
    def _init_weather(self):
        if self.weather_generator is not None:
            self.weather_state = self.weather_generator.sample()
        else:
            self.weather_state = None

    # ------------------------------------------------------------------
    def _compute_static_sinr_and_distance(self):
        """SINR (dB) and horizontal distance (km) from every user to every
        HAPS. Static for the episode since neither users nor HAPS move."""
        r = self.rng.uniform(0.0, self.service_radius_m, size=self.n_users)
        theta = self.rng.uniform(0.0, 2 * np.pi, size=self.n_users)
        self.user_xy_m = np.stack([r * np.cos(theta), r * np.sin(theta)], axis=1)

        dist_m = np.linalg.norm(
            self.user_xy_m[:, None, :] - self.node_xy_m[None, :, :], axis=2
        )  # (n_users, 3)

        rx_lin = np.zeros((self.n_users, self.n_haps))
        for p in range(self.n_haps):
            pl_db = cm.haps_a2g_pathloss_db(dist_m[:, p], h_haps_m=cm.HAPS_ALT_M,
                                             f_hz=cm.F_HAPS_MHZ * 1e6, env=self.env, h_user_m=1.5)
            rx_dbm = cm.P_TX_HAPS_DBM - pl_db
            rx_lin[:, p] = 10.0 ** (rx_dbm / 10.0)

        noise_lin = 10.0 ** (cm.NOISE_DBM / 10.0)
        total_lin = rx_lin.sum(axis=1, keepdims=True)
        interference_lin = total_lin - rx_lin  # sum over the other two HAPS
        sinr_lin = rx_lin / (noise_lin + interference_lin)
        sinr_db = 10.0 * np.log10(np.maximum(sinr_lin, 1e-15))

        self._sinr_db = sinr_db
        self._dist_km = dist_m / 1000.0

        relay_capacity = np.zeros((self.n_users, self.n_haps))
        for p in range(self.n_haps):
            relay = cm.relay_two_hop_capacity_bps_hz(
                feeder_dist_km=RELAY_FEEDER_DIST_KM,
                feeder_elevation_deg=RELAY_FEEDER_ELEVATION_DEG,
                gw_ue_dist_m=dist_m[:, p],
            )
            relay_capacity[:, p] = relay["capacity_relay_bps_hz"]
        self._relay_capacity = relay_capacity

        uav_relay_capacity = np.zeros((self.n_users, self.n_haps))
        for p in range(self.n_haps):
            uav_relay = cm.uav_relay_two_hop_capacity_bps_hz(
                r_horiz_m=dist_m[:, p],
                env=self.env,
            )
            uav_relay_capacity[:, p] = uav_relay["capacity_uav_relay_bps_hz"]
        self._uav_relay_capacity = uav_relay_capacity

    # ------------------------------------------------------------------
    def reset(self):
        self.t = 0
        self._init_weather()
        self.hour_of_day = float(self.weather_state.hour_of_day) if self.weather_state else 0.0
        self.soc = self.rng.uniform(self.soc_init_range[0], self.soc_init_range[1], size=self.n_haps)
        self._compute_static_sinr_and_distance()
        return self._states()

    # ------------------------------------------------------------------
    def _states(self):
        s = np.zeros((self.n_users, self.state_dim))
        s[:, 0:3] = np.clip((self._sinr_db - SINR_DB_MIN) / (SINR_DB_MAX - SINR_DB_MIN), 0.0, 1.0)
        s[:, 3:6] = np.clip(self._dist_km / DIST_KM_MAX, 0.0, 1.0)
        s[:, 6:9] = self.soc[None, :] / 100.0

        rain = self.weather_state.rain_mm_h if self.weather_state else 0.0
        vis_m = (self.weather_state.visibility_km if self.weather_state else 15.0) * 1000.0
        s[:, 9] = np.clip(rain / RAIN_MM_H_MAX, 0.0, 1.0)
        s[:, 10] = np.clip(vis_m / VIS_M_MAX, 0.0, 1.0)
        s[:, 11] = self.hour_of_day / 24.0
        s[:, 12:15] = np.clip(self._relay_capacity / CAPACITY_BPS_HZ_MAX, 0.0, 1.0)
        s[:, 15:18] = np.clip(self._uav_relay_capacity / CAPACITY_BPS_HZ_MAX, 0.0, 1.0)
        return s

    # ------------------------------------------------------------------
    def step(self, actions):
        """actions: array of length n_users, each in {0, ..., n_actions-1}.
        Actions 0..n_haps-1 = direct association with that HAPS; actions
        n_haps..2*n_haps-1 = relay via that HAPS's Gateway; actions
        2*n_haps..3*n_haps-1 = relay via a UAV served by that HAPS."""
        actions = np.asarray(actions, dtype=int)
        is_gw_relay = (actions >= self.n_haps) & (actions < 2 * self.n_haps)
        is_uav_relay = actions >= 2 * self.n_haps
        serving_haps = actions % self.n_haps  # direct/gw-relay/uav-relay all load the same HAPS's battery
        user_idx = np.arange(self.n_users)

        # Direct users get their raw SINR; relay users (Gateway or UAV) get
        # an SINR-equivalent derived from their DF relay capacity, so all
        # three share one array for the downstream throughput/Jain-fairness
        # computations.
        direct_sinr_db = self._sinr_db[user_idx, serving_haps]
        gw_relay_capacity = self._relay_capacity[user_idx, serving_haps]
        gw_relay_sinr_db = 10.0 * np.log10(np.maximum(2.0 ** gw_relay_capacity - 1.0, 1e-15))
        uav_relay_capacity = self._uav_relay_capacity[user_idx, serving_haps]
        uav_relay_sinr_db = 10.0 * np.log10(np.maximum(2.0 ** uav_relay_capacity - 1.0, 1e-15))
        chosen_sinr_db = np.where(
            is_uav_relay, uav_relay_sinr_db,
            np.where(is_gw_relay, gw_relay_sinr_db, direct_sinr_db),
        )

        counts = np.bincount(serving_haps, minlength=self.n_haps).astype(float)
        user_load_w = counts * self.p_per_user_w

        new_soc = np.zeros(self.n_haps)
        for p in range(self.n_haps):
            new_soc[p], _ = self.battery_model.update_battery_soc(
                current_soc_percent=self.soc[p],
                hour_of_day=self.hour_of_day,
                user_load_watts=user_load_w[p],
            )
        self.soc = new_soc

        # Paper eq. (Phase 2, Reward Function). L_agg and the outage penalty
        # are both literally SUMS (resp. fractions) over users, so they are
        # decomposed here into a per-user share -- each user gets its own
        # throughput/outage term, while Jain fairness and the battery/energy
        # penalty are genuinely network-level and stay a shared broadcast term.
        # This changes nothing about the paper's aggregate formula (the totals
        # are identical either way); it fixes credit assignment for learning --
        # broadcasting the fully-aggregated scalar to all 50 users buried each
        # user's own action under the other 49 users' noise and collapsed
        # training into a constant always-pick-HAPS-0 policy (see
        # docs/PHASE2_ASSOCIATION_PLAN.md).
        sinr_lin = 10.0 ** (chosen_sinr_db / 10.0)
        individual_throughput = np.log2(1.0 + sinr_lin)          # per-user L_agg share
        l_agg = float(np.sum(individual_throughput))              # paper's L_agg, for logging/de-rating

        jain = compute_jain_fairness_index(chosen_sinr_db)
        energy_penalty = 1.0 - float(np.mean(self.soc)) / 100.0

        severe = chosen_sinr_db < self.severe_threshold_db
        degraded = (~severe) & (chosen_sinr_db < self.degraded_threshold_db)
        individual_severe_penalty = np.where(severe, -100.0, 0.0)      # per-user share of -100*fraction
        individual_degraded_penalty = np.where(degraded, -20.0, 0.0)   # per-user share of -20*fraction
        low_battery_penalty = -50.0 * float(np.sum((self.soc < self.low_battery_soc_pct) & (counts > 0)))

        # Rain degrades the 38 GHz feeder (backhaul) link, not the 2 GHz
        # service-link SINR above -- so it de-rates only the throughput
        # credit, leaving fairness/energy/outage penalties untouched.
        rain = self.weather_state.rain_mm_h if self.weather_state else 0.0
        feeder = feeder_link_rain_effect_on_capacity(rain)
        capacity_fraction = float(np.clip(10.0 ** (-feeder["total_rain_loss_db"] / 10.0), 0.05, 1.0))
        effective_throughput = individual_throughput * capacity_fraction

        shared_term = self.omega_2 * jain - self.omega_3 * energy_penalty + low_battery_penalty
        rewards = (self.omega_1 * effective_throughput
                   + individual_severe_penalty + individual_degraded_penalty
                   + shared_term)

        self.t += 1
        self.hour_of_day = (self.hour_of_day + 1.0) % 24.0
        done = self.t >= self.max_steps

        info = {
            "jain_index": jain,
            "throughput_bps_hz": l_agg,
            "n_outage": int(np.sum(severe)),
            "battery_soc": self.soc.copy(),
            "assoc_counts": counts,
            "feeder_capacity_fraction": capacity_fraction,
            "n_gw_relay": int(np.sum(is_gw_relay)),
            "n_uav_relay": int(np.sum(is_uav_relay)),
        }
        return self._states(), rewards, done, info


if __name__ == "__main__":
    # Smoke test: random policy for one simulated day.
    from weather_scenario_generator import WeatherScenarioGenerator

    weather_gen = WeatherScenarioGenerator(mode="random_mix", seed=1)
    env = HAPSAssociationEnv(n_users=10, max_steps=24, weather_generator=weather_gen, seed=1)
    s = env.reset()
    print(f"state_dim={env.state_dim} n_actions={env.n_actions} state shape={s.shape}")
    print(f"weather: {env.weather_state.scenario_name}")
    for hour in range(24):
        a = env.rng.integers(0, env.n_actions, size=env.n_users)
        s, r, done, info = env.step(a)
        if hour % 6 == 0:
            print(f"hour {hour:2d} | reward={r.mean():7.2f} | jain={info['jain_index']:.3f} | "
                  f"outage={info['n_outage']:2d} | soc={np.round(info['battery_soc'], 1)} | "
                  f"feeder_frac={info['feeder_capacity_fraction']:.2f} | "
                  f"n_gw_relay={info['n_gw_relay']} | n_uav_relay={info['n_uav_relay']}")
    print("done" if done else "not done (unexpected)")
