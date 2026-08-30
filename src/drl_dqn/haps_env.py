"""
haps_env.py
===========
Step 1 deliverable: a self-contained HAPS-UAV access-network environment (no gym
dependency) that realises the MDP of Arani et al. (2023), Section IV-B.

The environment provides the reward-bearing physics for the DQN in Step 2:
  * one fixed HAPS + several UAVs act as aerial base stations (ABSs);
  * ground users follow a random-walk mobility model;
  * each user associates to the ABS giving the best SINR;
  * per-ABS load is estimated by a fixed-point iteration;
  * per-UAV reward = mu * Jain-fairness  +  nu * (1 - load).

State  (per UAV): normalised (x, y, h) + one-hot(channel)
Action (per UAV): one of 7 moves {up,down,left,right,forward,backward,fixed}
                  x  one of the channels                  -> 7 * n_channels
Reward (per UAV): mu * F(t) + nu * (1 - rho_u(t))         (paper eq. 31)

Channel physics come from channel_model.py (paper eqs. 2-5).

NOTE: parameters marked "ASSUMED" are reasonable defaults; replace with Paper 1
Table 1 values when available. They do not change the code, only the numbers.
"""

import numpy as np
import channel_model as cm

MOVES = ["up", "down", "left", "right", "forward", "backward", "fixed"]


class HAPSUAVEnv:
    def __init__(self,
                 n_uav=3,
                 n_users=100,
                 n_channels=3,
                 area_m=1000.0,
                 haps_alt_m=20_000.0,
                 uav_h_min=100.0, uav_h_max=500.0,
                 step_xy=50.0, step_h=50.0,
                 bw_per_channel_hz=10e6,      # ASSUMED
                 p_uav_dbm=30.0,              # ASSUMED
                 p_haps_dbm=46.0,             # ASSUMED
                 noise_dbm=-100.0,            # ASSUMED
                 rate_req_bps=5e5,            # ASSUMED per-user demand (learnable regime)
                 user_speed_max=5.0,          # m/s, ASSUMED
                 mu=1.0, nu=1.0,
                 max_steps=50,
                 with_haps=True,
                 state_mode="local",       # "local" | "cran" | "occupancy"
                                           # "local" = Arani-faithful & most robust (see step2b)
                 weather_generator=None,
                 seed=0):
        self.n_uav = n_uav
        self.n_users = n_users
        self.n_channels = n_channels
        self.area = area_m
        self.haps_alt = haps_alt_m
        self.uav_h_min, self.uav_h_max = uav_h_min, uav_h_max
        self.step_xy, self.step_h = step_xy, step_h
        self.bw = bw_per_channel_hz
        self.p_uav, self.p_haps, self.noise = p_uav_dbm, p_haps_dbm, noise_dbm
        self.rate_req = rate_req_bps
        self.user_speed_max = user_speed_max
        self.mu, self.nu = mu, nu
        self.max_steps = max_steps
        self.with_haps = with_haps
        self.rng = np.random.default_rng(seed)
        self.weather_generator = weather_generator
        self.weather_state = None

        self.state_mode = state_mode
        self.n_actions = len(MOVES) * n_channels
        # state variants (the C-RAN's reward role is present in ALL of them; these
        # differ only in what enters the DQN *state*):
        #   local     : (x,y,h) + own one-hot channel                 (Arani-faithful state)
        #   cran      : local + broadcast [fairness, mean load] in state (extends Arani)
        #   occupancy : local + other-UAV channel occupancy           (our deviation)
        # Phase 2: add weather features (rain, visibility, hour)
        base = 3 + n_channels
        weather_features = 3 if weather_generator is not None else 0
        self.state_dim = {"local": base,
                          "cran": base + 2,
                          "occupancy": base + n_channels}[state_mode] + weather_features

    # ------------------------------------------------------------------
    def _init_weather(self):
        """Sample weather scenario for this episode."""
        if self.weather_generator is not None:
            self.weather_state = self.weather_generator.sample()
        else:
            self.weather_state = None

    # ------------------------------------------------------------------
    def reset(self):
        self.t = 0
        self.last_fairness = 0.0        # C-RAN broadcast signals (prev slot)
        self.last_load_mean = 0.0
        # UAVs: random horizontal position, mid altitude, random channel
        self.uav_xy = self.rng.uniform(0, self.area, size=(self.n_uav, 2))
        self.uav_h = np.full(self.n_uav, 0.5 * (self.uav_h_min + self.uav_h_max))
        self.uav_ch = self.rng.integers(0, self.n_channels, size=self.n_uav)
        # HAPS at centre
        self.haps_xy = np.array([self.area / 2, self.area / 2])
        # Users: random position, fixed height
        self.user_xy = self.rng.uniform(0, self.area, size=(self.n_users, 2))
        # Phase 2: sample weather for this episode
        self._init_weather()
        return self._states()

    # ------------------------------------------------------------------
    def _states(self):
        """Per-UAV normalised state, per self.state_mode."""
        nc = self.n_channels
        s = np.zeros((self.n_uav, self.state_dim))
        s[:, 0] = self.uav_xy[:, 0] / self.area
        s[:, 1] = self.uav_xy[:, 1] / self.area
        s[:, 2] = (self.uav_h - self.uav_h_min) / (self.uav_h_max - self.uav_h_min)
        s[np.arange(self.n_uav), 3 + self.uav_ch] = 1.0            # own channel

        # Compute offset for mode-specific features (before weather)
        if self.state_mode == "cran":
            # C-RAN broadcast of the previous slot's global signals
            s[:, 3 + nc] = self.last_fairness
            s[:, 3 + nc + 1] = self.last_load_mean
            mode_offset = 3 + nc + 2
        elif self.state_mode == "occupancy":
            chan_counts = np.bincount(self.uav_ch, minlength=nc).astype(float)
            denom = max(1, self.n_uav - 1)
            for u in range(self.n_uav):                            # others' occupancy
                occ = chan_counts.copy()
                occ[self.uav_ch[u]] -= 1.0
                s[u, 3 + nc: 3 + 2 * nc] = occ / denom
            mode_offset = 3 + 2 * nc
        else:  # "local"
            mode_offset = 3 + nc

        # Phase 2: Append weather features (normalized)
        if self.weather_state is not None:
            rain_norm = min(self.weather_state.rain_mm_h / 25.0, 1.0)
            visibility_norm = min(self.weather_state.visibility_km / 20.0, 1.0)
            hour_norm = self.weather_state.hour_of_day / 24.0
            s[:, mode_offset] = rain_norm
            s[:, mode_offset + 1] = visibility_norm
            s[:, mode_offset + 2] = hour_norm

        return s

    # ------------------------------------------------------------------
    def _apply_action(self, u, action):
        move = action // self.n_channels
        ch = action % self.n_channels
        self.uav_ch[u] = ch
        m = MOVES[move]
        if m == "left":
            self.uav_xy[u, 0] -= self.step_xy
        elif m == "right":
            self.uav_xy[u, 0] += self.step_xy
        elif m == "forward":
            self.uav_xy[u, 1] += self.step_xy
        elif m == "backward":
            self.uav_xy[u, 1] -= self.step_xy
        elif m == "up":
            self.uav_h[u] += self.step_h
        elif m == "down":
            self.uav_h[u] -= self.step_h
        # "fixed": no move
        self.uav_xy[u] = np.clip(self.uav_xy[u], 0, self.area)
        self.uav_h[u] = np.clip(self.uav_h[u], self.uav_h_min, self.uav_h_max)

    # ------------------------------------------------------------------
    def _rx_power_dbm(self):
        """Return received power [dBm] matrices: users x UAVs, and users x 1 (HAPS)."""
        # UAV links
        dx = self.user_xy[:, 0:1] - self.uav_xy[None, :, 0]     # users x UAV
        dy = self.user_xy[:, 1:2] - self.uav_xy[None, :, 1]
        r = np.sqrt(dx**2 + dy**2)
        prx_uav = np.zeros((self.n_users, self.n_uav))
        for u in range(self.n_uav):
            pl = cm.uav_a2g_pathloss_db(r[:, u], h_uav_m=self.uav_h[u], env="urban")
            prx_uav[:, u] = self.p_uav - pl
        # HAPS link (orthogonal channel, no UAV interference)
        dxh = self.user_xy[:, 0] - self.haps_xy[0]
        dyh = self.user_xy[:, 1] - self.haps_xy[1]
        d3d_km = np.sqrt(dxh**2 + dyh**2 + self.haps_alt**2) / 1000.0
        pl_h = cm.haps_fspl_db(cm.F_HAPS_MHZ, d3d_km)
        prx_haps = self.p_haps - pl_h
        return prx_uav, prx_haps

    # ------------------------------------------------------------------
    def _compute_sinr_metrics(self):
        """Compute SINR and interference metrics for PRIMARY metric tracking.

        Returns:
            sinr_mean_db: Mean SINR across all users (dB)
            interference_power_dbm: Mean interference power (dBm)
            angle_sep_deg: Mean angle separation between nodes (degrees)
        """
        prx_uav, prx_haps = self._rx_power_dbm()
        prx_uav_lin = 10 ** (prx_uav / 10.0)
        noise_lin = 10 ** (self.noise / 10.0)

        n_abs = self.n_uav + (1 if self.with_haps else 0)
        sinr_matrix = np.zeros((self.n_users, n_abs))

        # Compute SINR for each user-node pair
        for u in range(self.n_uav):
            same = (self.uav_ch == self.uav_ch[u])
            same[u] = False
            interf = prx_uav_lin[:, same].sum(axis=1) if same.any() else 0.0
            sinr_lin = prx_uav_lin[:, u] / (noise_lin + interf)
            sinr_matrix[:, u] = 10 * np.log10(np.maximum(sinr_lin, 1e-10))

        # HAPS SINR
        if self.with_haps:
            prx_haps_lin = 10 ** (prx_haps / 10.0)
            sinr_haps = prx_haps_lin / noise_lin
            sinr_matrix[:, self.n_uav] = 10 * np.log10(np.maximum(sinr_haps, 1e-10))

        # Metrics for logging
        sinr_mean = float(np.mean(sinr_matrix))

        # Interference power (estimate from SINR)
        interference_mean = float(np.mean(np.maximum(prx_uav - 20 * np.log10(np.maximum(prx_uav_lin / (noise_lin + 1e-10), 1e-10)), -100)))

        # Angle separation (rough approximation from node positions)
        if self.n_uav > 1:
            angle_seps = []
            for i in range(self.n_uav):
                for j in range(i + 1, self.n_uav):
                    dx = self.uav_xy[i, 0] - self.uav_xy[j, 0]
                    dy = self.uav_xy[i, 1] - self.uav_xy[j, 1]
                    dist = np.sqrt(dx**2 + dy**2)
                    angle_sep = np.degrees(2 * np.arctan(dist / (2 * 1000))) if dist > 0 else 0
                    angle_seps.append(angle_sep)
            angle_sep_mean = float(np.mean(angle_seps)) if angle_seps else 90.0
        else:
            angle_sep_mean = 90.0

        return sinr_mean, interference_mean, angle_sep_mean

    # ------------------------------------------------------------------
    def _evaluate(self):
        """Association, SINR, rates, loads, fairness, outage.

        Uses a load-coupled fixed point: an ABS shares its channel bandwidth
        among the users it serves, so serving many users lowers each user's rate.
        This makes UAV placement/offloading matter (a lone HAPS serving everyone
        gives each user a tiny share), and yields the fixed point of eq. (13)-(15)
        in a simplified, stable form.
        """
        prx_uav, prx_haps = self._rx_power_dbm()
        prx_uav_lin = 10 ** (prx_uav / 10.0)
        noise_lin = 10 ** (self.noise / 10.0)

        n_abs = self.n_uav + (1 if self.with_haps else 0)
        base = np.zeros((self.n_users, n_abs))   # full-bandwidth (unshared) rate

        # UAV spectral-efficiency-based full rate (with co-channel interference)
        for u in range(self.n_uav):
            same = (self.uav_ch == self.uav_ch[u])
            same[u] = False
            interf = prx_uav_lin[:, same].sum(axis=1) if same.any() else 0.0
            sinr = prx_uav_lin[:, u] / (noise_lin + interf)
            base[:, u] = self.bw * np.log2(1.0 + sinr)

        # HAPS full rate (orthogonal channel -> noise-limited)
        if self.with_haps:
            prx_haps_lin = 10 ** (prx_haps / 10.0)
            base[:, self.n_uav] = self.bw * np.log2(1.0 + prx_haps_lin / noise_lin)

        # --- load-coupled fixed point: bandwidth shared among associated users
        assoc = np.argmax(base, axis=1)
        for _ in range(6):
            counts = np.bincount(assoc, minlength=n_abs).astype(float)
            share = base / np.maximum(counts[None, :], 1.0)      # per-user shared rate
            assoc = np.argmax(share, axis=1)
        counts = np.bincount(assoc, minlength=n_abs).astype(float)
        share = base / np.maximum(counts[None, :], 1.0)
        served_rate = share[np.arange(self.n_users), assoc]

        # per-UAV load = fraction of capacity demanded by its users (capped)
        load = np.zeros(self.n_uav)
        for u in range(self.n_uav):
            users_u = np.where(assoc == u)[0]
            if len(users_u):
                load[u] = min(1.0, (self.rate_req / np.maximum(base[users_u, u], 1.0)).sum())

        # Jain's fairness over all users' served rates
        s1 = served_rate.sum()
        s2 = (served_rate**2).sum()
        fairness = (s1**2) / (self.n_users * s2) if s2 > 0 else 0.0

        # outage: served (shared) rate below the requirement
        outage = int((served_rate < self.rate_req).sum())
        return fairness, load, outage, served_rate

    # ------------------------------------------------------------------
    def step(self, actions):
        """actions: array of length n_uav (one discrete action per UAV)."""
        for u in range(self.n_uav):
            self._apply_action(u, int(actions[u]))

        # user random-walk mobility
        speed = self.rng.uniform(0, self.user_speed_max, size=self.n_users)
        ang = self.rng.uniform(0, 2 * np.pi, size=self.n_users)
        self.user_xy[:, 0] = np.clip(self.user_xy[:, 0] + speed * np.cos(ang), 0, self.area)
        self.user_xy[:, 1] = np.clip(self.user_xy[:, 1] + speed * np.sin(ang), 0, self.area)

        fairness, load, outage, _ = self._evaluate()
        # Compute PRIMARY metrics for DQN training
        sinr_mean, interference_mean, angle_sep_mean = self._compute_sinr_metrics()

        # Aligned cooperative reward: fairness x served-fraction, in [0,1].
        # (The paper's mu*F + nu*(1-load) is reward-hackable under our load-
        #  coupling model -- the agent minimises load by serving nobody, giving
        #  F=1 on uniformly-tiny rates. The product form is 0 if nobody is
        #  served, so it forces the agent to actually cover users fairly.)
        served_fraction = 1.0 - outage / self.n_users
        reward_scalar = fairness * served_fraction

        # Phase 2: Rain penalty for heavy weather
        rain_penalty = 0.0
        if self.weather_state is not None and self.weather_state.rain_mm_h > 5.0:
            # Heavy rain reduces feeder capacity (38 GHz HAPS link)
            rain_penalty = -0.1 * (self.weather_state.rain_mm_h / 25.0)

        reward_scalar += rain_penalty
        rewards = np.full(self.n_uav, reward_scalar)

        # update C-RAN broadcast signals for the next state
        self.last_fairness = float(fairness)
        self.last_load_mean = float(load.mean())

        self.t += 1
        done = self.t >= self.max_steps
        info = {
            "fairness": fairness,
            "outage": outage,
            "load_mean": float(load.mean()),
            # PRIMARY metrics for Phase 2
            "sinr_mean_db": sinr_mean,
            "interference_power_dbm": interference_mean,
            "angle_sep_mean_deg": angle_sep_mean,
        }
        return self._states(), rewards, done, info


if __name__ == "__main__":
    # smoke test: random policy for a few steps
    env = HAPSUAVEnv(n_uav=3, n_users=100, seed=1)
    s = env.reset()
    print("state_dim", env.state_dim, "n_actions", env.n_actions)
    for _ in range(5):
        a = env.rng.integers(0, env.n_actions, size=env.n_uav)
        s, r, done, info = env.step(a)
        print(f"reward(mean)={r.mean():.3f}  fairness={info['fairness']:.3f}  "
              f"outage={info['outage']}  load={info['load_mean']:.3f}")
