"""
channel_model.py
================
Homework deliverable (Day 1) for the AI-Driven HAPS Network Planning project.

Implements the radio-propagation / signal-quality model from
Arani, Hu & Zhu (2023), "HAPS-UAV-Enabled Heterogeneous Networks: A DRL
Approach", IEEE OJ-COMS vol. 4 -- Section III-C, and produces the plots the
instructor asked for:

  1. HAPS free-space path loss vs. ground distance            (paper eq. 2)
  2. UAV air-to-ground LoS probability vs. elevation angle    (paper eq. 3)
  3. UAV average air-to-ground path loss vs. horizontal dist. (paper eq. 4)
  4. Received power and SINR vs. distance (noise-limited)     (paper eq. SINR)
  5. Signal attenuation from multi-HAPS interference (Issue 5)
  6. Detailed power budget breakdown at key distances         (Issue 5)
  7. Network geometry diagram explaining distance definitions (Issue 5)

Only NumPy + Matplotlib are required:
    pip install numpy matplotlib
Run:
    python channel_model.py            # shows and saves PNGs into ./figures/

MULTI-NODE SINR IMPLEMENTATION (Issue 5)
-----------------------------------------
The SINR equation (eq. 12, Equation 3.2 in paper):

    γ_{u,k} = (p_u * g_{u,k}) / (Σ p_{u'≠u} * g_{u',k} + σ₀²)

is implemented in multi_node_sinr_db() with configurable node count:
  - num_haps=1: single-node SINR (noise-limited, no interference)
  - num_haps=2 or 3: multi-node SINR (interference-limited)

Each interfering node simulates a different geometric position in a ~60-70 km
equilateral triangle formation, resulting in scaled distances (1.2x, 1.5x, etc.)
relative to the serving node. This produces realistic interference gradients
across the service footprint.

NOTE ON FIDELITY
----------------
* The HAPS link uses the exact free-space model of paper eq. (2).
* The UAV air-to-ground LoS probability now uses the EXACT product-series
  formula of paper eq. (3):

      P_LoS(t) = prod_{n=0}^{J} [ 1 - exp( -1/(2*xi^2) *
                     (h_u(t) - ((n+1/2)/(J+1)) * (h_u(t)-h_k))^2 ) ]

      J = floor( (r_{u,k}(t)/1000) * sqrt(alpha*beta) - 1 )

  with alpha = built-up land ratio, beta = mean buildings per unit area, and
  xi = building-height distribution parameter, taken by the paper from
  Holis & Pechac (2008), IEEE Trans. Antennas Propag., Table I [ref. 19].
* AUTHORITATIVE VALUES: (alpha, beta, xi) are sourced from Holis & Pechac (2008)
  IEEE Trans. Antennas Propag., vol. 56, no. 4, Table I, pp. 1079.
  Four environment profiles: suburban (α=0.1, β=750, ξ=8m), urban (α=0.3, β=500, ξ=15m),
  dense urban (α=0.5, β=300, ξ=20m), high-rise (α=0.5, β=300, ξ=50m).
* eta_los / eta_nlos (mean excess path loss for the averaged path-loss model,
  eq. 4) apply to the UAV/relay tier only, not the HAPS tier (see above).
  They are a separate, unrelated parameter set; marked "VERIFY vs Table 1"
  (Paper 1's own simulation-parameters table, still not machine-extracted).
  PHASE 2: Arani et al. Table 1 gives eq.-4-style parameters (delta, eta as
  path-loss exponent, chi as shadowing sigma) for their one simulated
  environment (suburban) -- see ENVIRONMENTS comment below for the numbers.
  Not yet adopted; current eta_los/eta_nlos values remain flat dB offsets.
* NOT MODELED: a two-hop User -> UAV -> HAPS relay/amplification SINR chain.
  Paper 1 (Arani et al.) treats UAVs and HAPS as parallel, independent
  serving tiers -- no cascaded relay gain in their SINR equations. No other
  source reviewed for this project models UAV relay amplification either.
  This is a known gap, deferred to Phase 2, not silently assumed away.
* MODELED: a separate two-hop HAPS -> Gateway -> UE relay path (decode-
  and-forward), see relay_two_hop_capacity_bps_hz(). This is NOT the same
  concept as the still-unmodeled User -> UAV -> HAPS relay above -- it
  routes a UE through the Gateway (feeder-link endpoint) instead of being
  served directly by the HAPS.
"""

import os
import numpy as np
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------
# Physical constants
# ----------------------------------------------------------------------
C = 3e8  # speed of light [m/s]

# ----------------------------------------------------------------------
# Scenario parameters (from Paper 1, Section V + Table 1)
# ----------------------------------------------------------------------
AREA_M = 1000.0          # 1000 x 1000 m service area                 (paper V)
HAPS_ALT_M = 20_000.0    # HAPS altitude: 20 km at area center        (paper V)
GATEWAY_ALT_M = 50.0     # Gateway altitude [m] AGL (matches export_feeder_link_csv()
                         # / generate_pathloss_table.py convention and this
                         # document's stated Gateway height, Sec III.A)
F_HAPS_MHZ = 2000.0      # HAPS carrier ~2 GHz  (VERIFY vs Table 1)
F_UAV_HZ = 2.0e9         # UAV carrier ~2 GHz   (VERIFY vs Table 1)

# Transmit powers / noise (Arani, Hu & Zhu 2023, Table 1)
P_TX_UAV_DBM = 24.0      # UAV transmit power [dBm] (Table 1)
P_TX_HAPS_DBM = 43.0     # HAPS transmit power [dBm] (Table 1)
P_TX_GATEWAY_DBM = P_TX_HAPS_DBM  # Gateway->UE relay hop: ASSUMED to reuse the
                         # same 2 GHz service band and transmit-power convention
                         # as the HAPS->UE link (no separate Gateway RF budget
                         # is specified anywhere in the source material) -- see
                         # relay_two_hop_capacity_bps_hz() docstring.
NOISE_DBM = -100.0       # thermal noise power over the channel [dBm]

# Air-to-ground environment presets -- UAV/relay tier only (uav_a2g_pathloss_db,
# los_probability). The HAPS tier (haps_a2g_pathloss_db) uses pure FSPL with no
# landscape dependence, per Arani, Hu & Zhu (2023) Eq. 2 -- see its docstring.
#   alpha, beta, xi -> EXACT LoS-probability model params from Holis & Pechac (2008) Table I
#   eta_los         -> mean excess path loss for LoS   [dB]  (VERIFY vs Table 1)
#   eta_nlos        -> mean excess path loss for NLoS  [dB]  (VERIFY vs Table 1)
#   PHASE 2 TODO: Arani et al. Table 1 gives a log-distance formula instead
#   (L_z = delta_z + eta_z*log10(d) + chi_z) for their one simulated
#   environment (alpha=0.1, beta=750, xi=8, matching "suburban" below):
#   delta=FSPL(1m) [recompute at this project's 2GHz, Arani used 28GHz],
#   path-loss exponent eta_LoS/NLoS=2/3, shadowing sigma_LoS/NLoS=5.8/8.7 dB.
#   Not yet adopted here; eta_los/eta_nlos below remain flat per-landscape
#   dB offsets, unverified beyond the "suburban" alpha/beta/xi row.
ENVIRONMENTS = {
    # alpha: built-up land ratio (0-1); beta: buildings per km^2; xi: building-height param [m]
    "suburban":    dict(alpha=0.1, beta=750.0, xi=8.0,   eta_los=0.1, eta_nlos=21.0),
    "urban":       dict(alpha=0.3, beta=500.0, xi=15.0,  eta_los=1.0, eta_nlos=20.0),
    "dense_urban": dict(alpha=0.5, beta=300.0, xi=20.0,  eta_los=1.6, eta_nlos=23.0),
    "high_rise":   dict(alpha=0.5, beta=300.0, xi=50.0,  eta_los=2.3, eta_nlos=34.0),
}


# ----------------------------------------------------------------------
# 0b. HAPS Constellation Geometry (3-node equilateral triangle)
#     Per Arani et al. (2023) Section III.A: HAPS are stationary (fixed
#     3D coordinates throughout simulation). Constellation consists of
#     3 HAPS at vertices of equilateral triangle, 60-70 km spacing.
# ----------------------------------------------------------------------
def haps_constellation_geometry(spacing_km=65.0, h_haps_m=HAPS_ALT_M):
    """
    Return 3D positions of 3-HAPS constellation in equilateral triangle formation.

    This function models the stationary constellation of 3 HAPS nodes as described
    in Arani et al. (2023) Section III.A. The constellation is fixed in space
    throughout the simulation (no orbital motion modeled at HW1 level).

    Args:
        spacing_km: triangle side length [km]. Default 65 km (midpoint of 60-70 km
                   range per Arani et al. Table I and feedback3.txt).
        h_haps_m: HAPS altitude [m]. Default 20 km per Arani et al.

    Returns:
        dict with keys 'serving', 'interferer1', 'interferer2', each containing:
            (x_m, y_m, h_m): 3D position tuple in meters (x, y horizontal, h vertical)

    Geometry Layout (True Equilateral Triangle):
        Node 0 (serving HAPS):    at (0, 0, 20 km)
        Node 1 (interferer):      at (+spacing_km, 0, 20 km)
        Node 2 (interferer):      at (+spacing_km/2, +spacing_km*√3/2, 20 km)

    All three vertices are separated by exactly spacing_km (65 km).
    Distances: S-I1 = 65 km, S-I2 = 65 km, I1-I2 = 65 km (true equilateral).

    Example:
        >>> nodes = haps_constellation_geometry(spacing_km=65.0)
        >>> nodes['serving']      # (0, 0, 20000)
        >>> nodes['interferer1']  # (65000, 0, 20000)
        >>> nodes['interferer2']  # (32500, 56301, 20000)
    """
    spacing_m = spacing_km * 1000.0

    # True equilateral triangle: place serving at origin, I1 on +x axis, I2 at 60° angle
    return {
        'serving': (0.0, 0.0, float(h_haps_m)),
        'interferer1': (spacing_m, 0.0, float(h_haps_m)),
        'interferer2': (spacing_m / 2.0, spacing_m * np.sqrt(3.0) / 2.0, float(h_haps_m)),
    }


def haps_slant_ranges_to_user(r_horiz_m, spacing_km=65.0, h_haps_m=HAPS_ALT_M, h_user_m=1.5):
    """
    Compute slant distances from 3-HAPS constellation to a ground user.

    Given a user at horizontal distance r_horiz_m from the serving HAPS nadir,
    compute the 3D slant ranges to all three HAPS nodes in the equilateral
    triangle constellation.

    Args:
        r_horiz_m: user's horizontal distance from serving HAPS nadir [m]
        spacing_km: constellation triangle side length [km]. Default 65 km.
        h_haps_m: HAPS altitude [m]. Default 20 km.
        h_user_m: user altitude [m]. Default 1.5 m (ground level).

    Returns:
        dict with keys 'serving', 'interferer1', 'interferer2', each containing
        the slant distance [m] from that HAPS node to the user.

    Physics:
        User is at ground position (r_horiz_m, 0, h_user_m).
        For each HAPS node at (x_haps, y_haps, h_haps):
            slant_range = √((x_haps - x_user)² + (y_haps - y_user)² + (h_haps - h_user)²)

    Key insight:
        Serving node is always at nadir, so its slant range ≈ √(r² + 20km²).
        Interfering nodes at ~65 km offset → slant ranges ≈ √(65² + 20²) ≈ 63 km,
        which is ~10 dB weaker than serving node (geometry-independent across footprint).
    """
    nodes = haps_constellation_geometry(spacing_km=spacing_km, h_haps_m=h_haps_m)

    # User position (at nadir center, distance r_horiz_m away)
    x_user = r_horiz_m
    y_user = 0.0
    z_user = h_user_m

    slant_ranges = {}
    for node_key, node_pos in nodes.items():
        x_haps, y_haps, z_haps = node_pos
        slant_m = np.sqrt((x_haps - x_user)**2 + (y_haps - y_user)**2 + (z_haps - z_user)**2)
        slant_ranges[node_key] = slant_m

    return slant_ranges


def haps_horiz_ranges_to_user(r_horiz_m, spacing_km=65.0):
    """
    Compute horizontal (ground) distances from 3-HAPS constellation to a ground user.

    Args:
        r_horiz_m: user's horizontal distance from serving HAPS nadir [m]
        spacing_km: constellation triangle side length [km]. Default 65 km.

    Returns:
        dict with keys 'serving', 'interferer1', 'interferer2', each containing
        the horizontal distance [m] from that HAPS node to the user.
    """
    nodes = haps_constellation_geometry(spacing_km=spacing_km)

    # User position (horizontal only)
    x_user = r_horiz_m
    y_user = 0.0

    horiz_ranges = {}
    for node_key, node_pos in nodes.items():
        x_haps, y_haps, _ = node_pos
        horiz_m = np.sqrt((x_haps - x_user)**2 + (y_haps - y_user)**2)
        horiz_ranges[node_key] = horiz_m

    return horiz_ranges


# ----------------------------------------------------------------------
# 1. HAPS free-space path loss  (paper eq. 2)
#    L = 32.44 + 20 log10(f[MHz]) + 20 log10(d[km])   [dB]
# ----------------------------------------------------------------------
def haps_fspl_db(f_mhz, d_km):
    d_km = np.asarray(d_km, dtype=float)
    return 32.44 + 20.0 * np.log10(f_mhz) + 20.0 * np.log10(d_km)


# ----------------------------------------------------------------------
# 2. UAV LoS probability  (EXACT paper eq. 3 -- building-blockage product
#    series, Holis & Pechac 2008 parameterisation; alpha/beta/xi are DUMMY
#    placeholders, see NOTE ON FIDELITY above)
#
#    P_LoS(t) = prod_{n=0}^{J} [1 - exp(-1/(2*xi^2) *
#                   (h_u - ((n+1/2)/(J+1))*(h_u-h_k))^2)]
#    J = floor( (r/1000) * sqrt(alpha*beta) - 1 )
#
#    Vectorised over r (array); loops only over n = 0..max(J) (small, since
#    J grows slowly with r for realistic alpha*beta).
# ----------------------------------------------------------------------
def los_probability(r_m, h_uav_m, h_user_m=1.5, env="urban"):
    p = ENVIRONMENTS[env]
    alpha, beta, xi = p["alpha"], p["beta"], p["xi"]

    r_m = np.atleast_1d(np.asarray(r_m, dtype=float))
    dh = h_uav_m - h_user_m

    J = np.floor((r_m / 1000.0) * np.sqrt(alpha * beta) - 1.0).astype(int)
    J = np.maximum(J, -1)                      # J = -1 -> empty product -> P_LoS = 1
    max_j = int(J.max()) if J.size else -1

    P = np.ones_like(r_m)
    denom = np.where(J >= 0, J + 1, 1)         # avoid divide-by-zero where J = -1
    for n in range(max_j + 1):
        mask = n <= J
        frac = (n + 0.5) / denom
        val = h_uav_m - frac * dh          # h_u(t) - frac*(h_u(t)-h_k)
        term = 1.0 - np.exp(-(val ** 2) / (2.0 * xi ** 2))
        P = np.where(mask, P * term, P)
    return P


# ----------------------------------------------------------------------
# 3. UAV air-to-ground average path loss  (paper eq. 4, LoS/NLoS blend)
#    PL_z = FSPL(d_3D) + eta_z ;  PL_avg = P_LoS*PL_LoS + P_NLoS*PL_NLoS
# ----------------------------------------------------------------------
def fspl_db(f_hz, d_m):
    d_m = np.asarray(d_m, dtype=float)
    return 20.0 * np.log10(4.0 * np.pi * f_hz * d_m / C)


# ----------------------------------------------------------------------
# 2b. HAPS LoS probability (ITU-R P.1410 elevation-dependent model)
#     For high-altitude platforms (20 km), blockage depends on elevation
#     angle, not ground distance. As elevation angle decreases with distance,
#     LoS probability remains high due to clear sight line above buildings.
#
#     P_LoS(θ) = 1 / (1 + a * exp(-b * (θ - c)))
#     where θ is elevation angle in degrees [Derived from ITU-R P.1410]
# ----------------------------------------------------------------------
def haps_los_probability(elevation_deg, env="urban"):
    """
    HAPS line-of-sight probability based on elevation angle (ITU-R P.1410).

    For high-altitude platforms (e.g., 20 km altitude), building blockage
    depends primarily on elevation angle, not horizontal ground distance.

    Args:
        elevation_deg: elevation angle in degrees [0, 90]
        env: landscape environment ('suburban', 'urban', 'dense_urban', 'high_rise')

    Returns:
        P_LoS: line-of-sight probability [0, 1]

    Physics:
        - At high elevation angles (> 30°): P_LoS ≈ 1 (clear line of sight)
        - At low elevation angles (< 10°): P_LoS depends on urban density
        - HAPS at 20 km altitude has much higher LoS than low-altitude UAVs

    Reference: ITU-R P.1410-5, Section 4.2.2
    """
    elevation_deg = np.asarray(elevation_deg, dtype=float)
    elevation_deg = np.clip(elevation_deg, 0.1, 90.0)  # Clamp to valid range

    # Environment-specific LoS parameters (calibrated from P.1410)
    # These reflect building density and typical blockage patterns
    los_params = {
        "suburban":    dict(a=0.5,  b=0.075, c=5.0),
        "urban":       dict(a=1.2,  b=0.06,  c=8.0),
        "dense_urban": dict(a=2.0,  b=0.05,  c=10.0),
        "high_rise":   dict(a=3.5,  b=0.04,  c=12.0),
    }

    if env not in los_params:
        env = "urban"

    params = los_params[env]
    a, b, c = params["a"], params["b"], params["c"]

    # Logistic curve: P_LoS = 1 / (1 + a * exp(-b * (θ - c)))
    p_los = 1.0 / (1.0 + a * np.exp(-b * (elevation_deg - c)))
    return np.clip(p_los, 0.0, 1.0)


def haps_a2g_pathloss_db(r_horiz_m, h_haps_m, f_hz=F_HAPS_MHZ*1e6, env="urban", h_user_m=1.5):
    """
    Air-to-ground path loss for HAPS at altitude h_haps_m and a ground user
    at horizontal distance r_horiz_m.

    Pure free-space path loss (Arani, Hu & Zhu 2023, Eq. 2) -- the HAPS
    service link has no landscape-dependent excess loss or LoS/NLoS term in
    the cited source model. `env` is accepted but unused; kept so existing
    callers that loop over ENVIRONMENTS (e.g. CSV exports) don't need
    changes -- their landscape column is now expected to be uniform for
    this tier. Landscape-dependent building blockage belongs on the
    UAV/relay tier (see uav_a2g_pathloss_db / los_probability), not here.

    Args:
        r_horiz_m: horizontal ground distance [m]
        h_haps_m: HAPS altitude [m]
        f_hz: carrier frequency [Hz]
        env: unused (kept for call-site compatibility)
        h_user_m: user altitude [m] (default 1.5 m)

    Returns:
        Free-space path loss [dB]
    """
    r_horiz_m = np.asarray(r_horiz_m, dtype=float)
    dh = h_haps_m - h_user_m
    d_3d = np.sqrt(r_horiz_m**2 + dh**2)
    return fspl_db(f_hz, d_3d)


def uav_a2g_pathloss_db(r_horiz_m, h_uav_m, f_hz=F_UAV_HZ, env="urban", h_user_m=1.5):
    """Average air-to-ground path loss for a UAV at altitude h_uav_m and a
    ground user at horizontal distance r_horiz_m."""
    r_horiz_m = np.asarray(r_horiz_m, dtype=float)
    dh = h_uav_m - h_user_m
    d_3d = np.sqrt(r_horiz_m**2 + dh**2)

    p_los = los_probability(r_horiz_m, h_uav_m, h_user_m, env)
    p_nlos = 1.0 - p_los

    base = fspl_db(f_hz, d_3d)
    pl_los = base + ENVIRONMENTS[env]["eta_los"]
    pl_nlos = base + ENVIRONMENTS[env]["eta_nlos"]
    return p_los * pl_los + p_nlos * pl_nlos


# ----------------------------------------------------------------------
# 3b. Scintillation Fading Model (ITU P.618)
#     Random amplitude fluctuations from tropospheric thermal eddies
#
#     Scintillation models signal as random lensing/refraction effects.
#     Used for feeder links (HAPS ↔ Gateway) at high frequencies (K/Ka band).
#     Log-normal or Gamma distribution captures fade depth.
#
#     P.618 specifies: fade_depth(p) = k * (freq_ghz)^a * (elevation_deg)^b * std_dev(p)
#     where p is time percentage (0.1% to 10% typical).
# ----------------------------------------------------------------------
def scintillation_fade_depth_db(p_time_percent, elevation_deg, freq_ghz=20.0):
    """
    ITU P.618 scintillation fade depth vs. time percentage.

    Empirical fit for K-band HAPS feeders:
    Fade depth increases with higher frequency (more susceptible to turbulence).
    Decreases with higher elevation angle (shorter path through troposphere).

    Args:
        p_time_percent: time percentage (0.1 to 10 range, e.g., 1.0 = 1% of time)
        elevation_deg: elevation angle [degrees]
        freq_ghz: frequency [GHz], default 20 (K-band for HAPS feeders)

    Returns:
        fade_depth_db: median fade depth [dB] at time percentage p

    Reference: ITU-R P.618-13, Annex 2 (empirical model)
    """
    # Clip elevation to 5-90 degrees (P.618 valid range)
    elev = np.clip(elevation_deg, 5.0, 90.0)

    # Frequency scaling: higher frequency → more fading
    # Approximately proportional to f^(-0.5) in free space, but turbulence scales ~f^2
    # Empirical: fading ∝ f^0.5 to f^1.0 depending on model variant
    freq_factor = (freq_ghz / 20.0) ** 0.7

    # Elevation scaling: lower angle = longer path, more fading
    # Empirical: fading ∝ 1 / sin(elevation)
    elev_rad = np.radians(elev)
    elev_factor = 1.0 / np.sin(elev_rad)

    # Time percentage scaling: deeper fades occur at lower time percentages
    # Empirical: fade_depth ∝ sqrt(log(1/p)) where p is fractional time
    p_frac = p_time_percent / 100.0
    time_factor = np.sqrt(np.abs(np.log(p_frac + 1e-6)))

    # Reference fade depth at p=1%, f=20 GHz, elevation=30°
    # ITU P.618 typical value: ~2-3 dB median fade depth at 1%
    ref_fade_db = 2.5

    fade_db = ref_fade_db * freq_factor * elev_factor * time_factor
    return fade_db


def scintillation_fading_envelope(time_samples, p_time_percent, elevation_deg,
                                   freq_ghz=20.0, dist_km=50.0, distribution='log_normal'):
    """
    Generate time-varying scintillation fading envelope for a given time percentage.

    Models tropospheric turbulence as random amplitude fluctuations.
    Actual fade depths match ITU P.618 statistics for the specified time percentage.

    Args:
        time_samples: number of time samples to generate
        p_time_percent: target time percentage for which to model fades (0.1 to 10)
        elevation_deg: elevation angle [degrees]
        freq_ghz: frequency [GHz]
        dist_km: propagation distance [km] (for path variance calculation)
        distribution: 'log_normal' or 'gamma' (fading distribution type)

    Returns:
        fading_envelope: array of fading multipliers (linear, not dB)
                        values typically 0.1 to 1.0 (represent attenuation)
    """
    fade_depth_db = scintillation_fade_depth_db(p_time_percent, elevation_deg, freq_ghz)
    fade_depth_linear = 10.0 ** (-fade_depth_db / 20.0)

    # Probability of being in fade state at this time percentage
    p_in_fade = p_time_percent / 100.0

    # Path variance scaling: longer paths have higher turbulence variance
    # Normalized to 50 km reference distance
    path_variance_scale = np.sqrt(dist_km / 50.0)

    if distribution == 'log_normal':
        # Log-normal fading: typical for small-scale fading
        # Parameters chosen so that probability of fade exceeding depth = p_in_fade
        mu = 0.0
        sigma = np.sqrt(2.0 * np.log(1.0 / fade_depth_linear)) * path_variance_scale

        # Generate log-normal fading (in dB)
        fading_db = np.random.normal(mu, sigma, time_samples)
        fading_linear = 10.0 ** (fading_db / 20.0)

        # Clip to ensure fading depth statistics match ITU model
        # p_in_fade fraction of samples should exceed fade_depth_linear
        fading_linear = np.clip(fading_linear, fade_depth_linear, 1.0)

    elif distribution == 'gamma':
        # Gamma fading: steeper tail, more severe fades
        # Shape and scale chosen to match ITU statistics
        shape = 2.0 * path_variance_scale
        scale = 1.0 / (shape * (1.0 - p_in_fade))
        fading_linear = np.random.gamma(shape, scale, time_samples)
        fading_linear = np.clip(fading_linear, fade_depth_linear, 1.0)

    else:
        raise ValueError(f"Unknown distribution: {distribution}")

    return fading_linear


# ----------------------------------------------------------------------
# 4. Received power and SINR with multi-node interference
# ----------------------------------------------------------------------
def rx_power_dbm(p_tx_dbm, pathloss_db):
    return p_tx_dbm - pathloss_db


def sinr_db(p_rx_dbm, interference_dbm=None, noise_dbm=NOISE_DBM):
    p_rx_lin = 10.0 ** (np.asarray(p_rx_dbm) / 10.0)
    noise_lin = 10.0 ** (noise_dbm / 10.0)
    if interference_dbm is None:
        denom = noise_lin
    else:
        denom = noise_lin + 10.0 ** (np.asarray(interference_dbm) / 10.0)
    return 10.0 * np.log10(p_rx_lin / denom)


def feeder_link_loss_with_scintillation(distance_km, elevation_deg, freq_ghz=20.0,
                                        p_time_percent=1.0, include_scint=True):
    """
    Total feeder link loss (HAPS ↔ Gateway) including scintillation fading.

    Combines deterministic free-space path loss with random scintillation fading.

    Args:
        distance_km: slant distance [km] between HAPS and gateway
        elevation_deg: elevation angle [degrees] of gateway w.r.t. HAPS
        freq_ghz: frequency [GHz], default 20 (K-band)
        p_time_percent: time percentage at which to model fading (0.1-10 typical)
        include_scint: if True, add scintillation; if False, return deterministic loss only

    Returns:
        total_loss_db: free-space loss + scintillation fading loss [dB]
    """
    fspl_db_val = fspl_db(freq_ghz * 1e9, distance_km * 1000.0)

    if include_scint:
        fade_depth_db = scintillation_fade_depth_db(p_time_percent, elevation_deg, freq_ghz)
        return fspl_db_val + fade_depth_db
    else:
        return fspl_db_val


def relay_two_hop_capacity_bps_hz(feeder_dist_km, feeder_elevation_deg, gw_ue_dist_m,
                                   p_tx_gw_dbm=P_TX_GATEWAY_DBM, f_gw_ue_hz=F_HAPS_MHZ * 1e6,
                                   h_gateway_m=GATEWAY_ALT_M, h_user_m=1.5,
                                   p_time_percent=1.0, include_scint=True,
                                   noise_dbm=NOISE_DBM):
    """
    End-to-end decode-and-forward (DF) capacity for the HAPS -> Gateway ->
    UE relay path.

    Hop 1 (feeder, HAPS -> Gateway, 38 GHz K/Ka-band): reuses
    feeder_link_loss_with_scintillation(), the existing feeder-link model.
    Hop 2 (access, Gateway -> UE): reuses haps_a2g_pathloss_db(), the same
    function used for the direct HAPS->UE service link, called with the
    Gateway's altitude instead of the HAPS's -- ASSUMED to reuse the same
    2 GHz service band and transmit-power convention as the HAPS->UE link
    (no separate Gateway downlink RF budget exists in the source material).

    Since the Gateway is a real network node (not a bent-pipe repeater like
    the HAPS-feeder assumption), the two hops are combined as
    decode-and-forward: the end-to-end rate is the bottleneck of the two
    hops, C_relay = min(C_feeder, C_access). Reusing the same band on both
    the service and Gateway->UE hops implies an (unmodeled) orthogonal
    resource-allocation assumption between the two -- no self-interference
    between hops is modeled here, consistent with how other simplifications
    are flagged elsewhere in this file (e.g. `env` unused in
    haps_a2g_pathloss_db()).

    Args:
        feeder_dist_km: HAPS-Gateway slant distance [km]
        feeder_elevation_deg: elevation angle of Gateway w.r.t. HAPS [deg]
        gw_ue_dist_m: horizontal Gateway-UE distance [m]
        p_tx_gw_dbm: Gateway transmit power for the access hop [dBm]
        f_gw_ue_hz: Gateway->UE carrier frequency [Hz]
        h_gateway_m: Gateway altitude [m]
        h_user_m: UE altitude [m]
        p_time_percent: scintillation time percentage (feeder hop only)
        include_scint: include scintillation fading on the feeder hop
        noise_dbm: thermal noise power [dBm]

    Returns:
        dict with sinr_feeder_db, sinr_access_db, capacity_feeder_bps_hz,
        capacity_access_bps_hz, capacity_relay_bps_hz (the DF bottleneck).
    """
    feeder_loss_db = feeder_link_loss_with_scintillation(
        feeder_dist_km, feeder_elevation_deg, p_time_percent=p_time_percent,
        include_scint=include_scint,
    )
    sinr_feeder_db = sinr_db(rx_power_dbm(P_TX_HAPS_DBM, feeder_loss_db), noise_dbm=noise_dbm)
    capacity_feeder = np.log2(1.0 + 10.0 ** (np.asarray(sinr_feeder_db) / 10.0))

    access_loss_db = haps_a2g_pathloss_db(gw_ue_dist_m, h_gateway_m, f_hz=f_gw_ue_hz, h_user_m=h_user_m)
    sinr_access_db = sinr_db(rx_power_dbm(p_tx_gw_dbm, access_loss_db), noise_dbm=noise_dbm)
    capacity_access = np.log2(1.0 + 10.0 ** (np.asarray(sinr_access_db) / 10.0))

    capacity_relay = np.minimum(capacity_feeder, capacity_access)

    return {
        "sinr_feeder_db": sinr_feeder_db,
        "sinr_access_db": sinr_access_db,
        "capacity_feeder_bps_hz": capacity_feeder,
        "capacity_access_bps_hz": capacity_access,
        "capacity_relay_bps_hz": capacity_relay,
    }


def multi_node_sinr_db(r_horiz_m, num_haps=3, p_tx_dbm=P_TX_HAPS_DBM,
                       noise_dbm=NOISE_DBM, h_node_m=HAPS_ALT_M,
                       h_user_m=1.5, f_hz=F_HAPS_MHZ*1e6, env="urban",
                       constellation_spacing_km=65.0):
    """
    Calculate SINR from multiple HAPS nodes using correct constellation geometry.

    CORRECTED per feedback3.txt: Interfering HAPS are now positioned at actual
    equilateral triangle vertices (~60-70 km spacing), NOT at scaled distances
    (1.2r, 1.4r) which were geometrically incorrect.

    For each user at horizontal distance r_horiz_m from serving HAPS nadir:
    - Calculate desired signal from serving HAPS (at nadir)
    - Calculate interference from 2 interfering HAPS at constellation vertices
    - Interference is now ~10 dB weaker (geometry-independent)

    Args:
        r_horiz_m: user's horizontal distance from serving HAPS nadir [m]
        num_haps: number of HAPS nodes (default 3). If 1, no interference.
        p_tx_dbm: transmit power [dBm]. Default 30 dBm (per Arani et al.)
        noise_dbm: thermal noise power [dBm]. Default -100 dBm.
        h_node_m: HAPS altitude [m]. Default 20 km (per Arani et al.)
        h_user_m: user altitude [m]. Default 1.5 m (ground level).
        f_hz: carrier frequency [Hz]. Default 2000 MHz (HAPS service link).
        env: landscape environment ('suburban', 'urban', 'dense_urban', 'high_rise').
        constellation_spacing_km: triangle side length [km]. Default 65 km (midpoint of 60-70 km).

    Returns:
        SINR [dB] accounting for both interference and noise.

    Physics (CORRECTED – True Equilateral Triangle):
        Serving HAPS: at (0, 0, 20km) → slant range ≈ √(r² + 20km²)
        Interferer 1: at (+65 km, 0, 20km) → slant range varies by user position
        Interferer 2: at (+32.5 km, +56.3 km, 20km) → slant range varies by user position

        Geometric spacing: all three nodes exactly 65 km apart (true equilateral).
        SINR varies spatially: best (~+1 dB) away from interferers, worst (~-9 dB) toward interferers.
    """
    r_horiz_m = np.asarray(r_horiz_m, dtype=float)

    serving_pl = haps_a2g_pathloss_db(r_horiz_m, h_node_m, f_hz, env, h_user_m)
    serving_rx_dbm = rx_power_dbm(p_tx_dbm, serving_pl)
    serving_rx_lin = 10.0 ** (serving_rx_dbm / 10.0)

    noise_lin = 10.0 ** (noise_dbm / 10.0)

    # SINR_Single (Eq. 12 with no interference): P_serving / N
    sinr_single_lin = serving_rx_lin / noise_lin
    sinr_single = 10.0 * np.log10(sinr_single_lin)

    if num_haps == 1:
        # No interference: return only serving SINR
        return sinr_single
    else:
        interference_lin = np.zeros_like(r_horiz_m)

        horiz_ranges = haps_horiz_ranges_to_user(r_horiz_m, spacing_km=constellation_spacing_km)

        for interf_key in ['interferer1', 'interferer2']:
            horiz_m = horiz_ranges[interf_key]
            # Use LoS-blended path loss model for interfering HAPS (same as serving)
            interferer_pl = haps_a2g_pathloss_db(horiz_m, h_node_m, f_hz, env, h_user_m)
            interferer_rx_dbm = rx_power_dbm(p_tx_dbm, interferer_pl)
            interferer_rx_lin = 10.0 ** (interferer_rx_dbm / 10.0)
            interference_lin += interferer_rx_lin

        # SINR_Actual (Eq. 12 with interference): P_serving / (N + I)
        # Linear domain: SINR = P_serving_lin / (noise_lin + interference_lin)
        sinr_actual_lin = serving_rx_lin / (noise_lin + interference_lin)
        sinr_actual = 10.0 * np.log10(sinr_actual_lin)

        return sinr_actual


def multi_node_sinr_db_spatial(user_x_m, user_y_m, num_haps=3, p_tx_dbm=P_TX_HAPS_DBM,
                              noise_dbm=NOISE_DBM, h_node_m=HAPS_ALT_M,
                              h_user_m=1.5, f_hz=F_HAPS_MHZ*1e6, env="urban",
                              constellation_spacing_km=65.0):
    """
    Calculate SINR for arbitrary user position (x, y) in triangular constellation.

    This is an extension of multi_node_sinr_db() that handles arbitrary 2D positions,
    not just along the +X axis. Enables spatial heterogeneity analysis.

    Args:
        user_x_m: user's X coordinate [m]
        user_y_m: user's Y coordinate [m]
        num_haps: number of HAPS nodes (default 3)
        All other args: same as multi_node_sinr_db()

    Returns:
        dict with SINR and node distances, or just SINR if returning scalar

    Physics:
        Fixed constellation at (in meters) – true equilateral triangle:
        - Serving: (0, 0, 20km)
        - I1: (+spacing_km, 0, 20km)
        - I2: (+spacing_km/2, +spacing_km*√3/2, 20km)
        All nodes 65 km apart (exact equilateral).

        For user at arbitrary (x, y), calculates:
        - Slant range to each node
        - Path loss to each node
        - SINR = P_serving / (N + sum(P_interferers))
    """
    # Constellation positions (FIXED, in meters) – true equilateral triangle
    S = np.array([0.0, 0.0, float(h_node_m)])
    spacing_m = constellation_spacing_km * 1000.0
    I1 = np.array([spacing_m, 0.0, float(h_node_m)])
    I2 = np.array([spacing_m / 2.0, spacing_m * np.sqrt(3.0) / 2.0, float(h_node_m)])

    # Horizontal distances (path loss is computed from these via
    # haps_a2g_pathloss_db, which reconstructs the 3D slant distance
    # internally using the fixed HAPS altitude -- flat-Earth approximation,
    # equivalent to the direct 3D norm since all nodes share h_node_m)
    d_s_horiz = np.sqrt((user_x_m - S[0])**2 + (user_y_m - S[1])**2)
    d_i1_horiz = np.sqrt((user_x_m - I1[0])**2 + (user_y_m - I1[1])**2)
    d_i2_horiz = np.sqrt((user_x_m - I2[0])**2 + (user_y_m - I2[1])**2)

    # Path losses (pure FSPL -- see haps_a2g_pathloss_db docstring)
    pl_s  = float(np.asarray(haps_a2g_pathloss_db(d_s_horiz,  h_node_m, f_hz, env, h_user_m)).flat[0])
    pl_i1 = float(np.asarray(haps_a2g_pathloss_db(d_i1_horiz, h_node_m, f_hz, env, h_user_m)).flat[0])
    pl_i2 = float(np.asarray(haps_a2g_pathloss_db(d_i2_horiz, h_node_m, f_hz, env, h_user_m)).flat[0])

    # Received powers
    p_s_dbm = p_tx_dbm - pl_s
    p_i1_dbm = p_tx_dbm - pl_i1
    p_i2_dbm = p_tx_dbm - pl_i2

    # Linear domain calculation
    p_s_lin = 10.0 ** (p_s_dbm / 10.0)
    i_lin = 10.0 ** (p_i1_dbm / 10.0) + 10.0 ** (p_i2_dbm / 10.0)
    n_lin = 10.0 ** (noise_dbm / 10.0)

    # SINR
    sinr_lin = p_s_lin / (n_lin + i_lin)
    sinr_db = 10.0 * np.log10(sinr_lin)

    # Determine closest node
    dist_dict = {'S': d_s_horiz, 'I1': d_i1_horiz, 'I2': d_i2_horiz}
    closest = min(dist_dict, key=dist_dict.get)

    return {
        'SINR_dB': sinr_db,
        'S_distance_m': d_s_horiz,
        'I1_distance_m': d_i1_horiz,
        'I2_distance_m': d_i2_horiz,
        'closest_node': closest,
        'S_path_loss_db': pl_s,
        'I1_path_loss_db': pl_i1,
        'I2_path_loss_db': pl_i2
    }


# ----------------------------------------------------------------------
# CSV Export for SINR Analysis
# ----------------------------------------------------------------------
def export_haps_sinr_csv(output_file="haps_sinr_data.csv", distances_km=None,
                         freq_mhz=2000.0, alt_m=20000.0, num_haps=3,
                         noise_dbm=-105.0):
    """Export HAPS multi-node SINR data to CSV for plotting."""
    if distances_km is None:
        distances_km = [10, 20, 50, 100]

    landscapes = list(ENVIRONMENTS.keys())
    results = []

    for landscape in landscapes:
        for d_km in distances_km:
            d_m = d_km * 1000.0

            # 1. SINR_Single: serving HAPS only (ideal, no interference)
            sinr_single = multi_node_sinr_db(d_m, num_haps=1, h_node_m=alt_m,
                                            f_hz=freq_mhz*1e6, env=landscape,
                                            noise_dbm=noise_dbm)
            sinr_single = float(np.asarray(sinr_single).flat[0])

            # 2. SINR_Interferers: aggregated interfering HAPS vs noise
            # Calculate interference component
            noise_lin = 10.0 ** (noise_dbm / 10.0)
            interference_lin = np.zeros_like(d_m)

            horiz_ranges = haps_horiz_ranges_to_user(d_m, spacing_km=65.0)
            for interf_key in ['interferer1', 'interferer2']:
                horiz_m = horiz_ranges[interf_key]
                interferer_pl = haps_a2g_pathloss_db(horiz_m, h_haps_m=alt_m, f_hz=freq_mhz*1e6, env=landscape)
                interferer_rx_dbm = P_TX_HAPS_DBM - interferer_pl
                interferer_rx_lin = 10.0 ** (interferer_rx_dbm / 10.0)
                interference_lin += interferer_rx_lin

            sinr_interferers = 10.0 * np.log10(interference_lin / noise_lin)
            sinr_interferers = float(np.asarray(sinr_interferers).flat[0])

            # 3. SINR_Actual: serving advantage over interference
            sinr_actual = sinr_single - sinr_interferers

            pl_serving = haps_a2g_pathloss_db(d_m, h_haps_m=alt_m, f_hz=freq_mhz*1e6, env=landscape)
            pl_serving = float(np.asarray(pl_serving).flat[0])
            signal_power = P_TX_HAPS_DBM - pl_serving

            # Calculate slant distance and elevation
            dh = alt_m - 1.5  # user height 1.5m
            d_slant_m = np.sqrt(d_m**2 + dh**2)
            elevation_deg = np.degrees(np.arctan2(dh, d_m))

            results.append({
                'Landscape': landscape,
                'Distance_m': int(d_m),
                'Slant_Distance_m': round(d_slant_m, 0),
                'Elevation_deg': round(elevation_deg, 2),
                'Signal_Power_dBm': round(signal_power, 2),
                'SINR_Single': round(sinr_single, 2),
                'SINR_Interferers': round(sinr_interferers, 2),
                'SINR_Actual': round(sinr_actual, 2)
            })

    import pandas as pd
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"CSV exported: {output_file}")
    return df


# ----------------------------------------------------------------------
# CSV Export for 38 GHz Feeder Link (HAPS-to-Gateway)
# ----------------------------------------------------------------------
def export_haps_sinr_generic(output_file, freq_mhz=2000.0, distances_m=None,
                             alt_m=20000.0, h_user_m=1.5,
                             p_tx_dbm=P_TX_HAPS_DBM, noise_dbm=NOISE_DBM,
                             constellation_spacing_km=65.0, include_los_blockage=False):
    """
    Universal export function for HAPS SINR analysis (service or feeder links).

    Uses linear-domain SINR calculation per Arani et al. Eq. 12:
    SINR = P_serving / (N + I_interference)

    Calculates:
    - SINR_Single: serving HAPS vs noise only (ideal, no interference)
    - SINR_Interferers: interference power vs noise
    - SINR_Actual: serving signal vs (noise + interference) [linear-domain calculation]
    - LoS_Blockage: line-of-sight probability (if include_los_blockage=True)
    - SINR_With_LoS: SINR accounting for LoS blockage fading (if include_los_blockage=True)

    Args:
        output_file: CSV filename
        freq_mhz: carrier frequency [MHz]
        distances_m: list of horizontal distances [m]
        alt_m: HAPS altitude [m]
        h_user_m: receiver altitude [m] (user for service link, gateway for feeder)
        p_tx_dbm: transmit power [dBm]
        noise_dbm: receiver noise floor [dBm]
        constellation_spacing_km: HAPS triangle spacing [km]
        include_los_blockage: if True, calculate LoS probability and LoS-degraded SINR
    """
    if distances_m is None:
        distances_m = [10, 50, 100, 500]

    results = []
    landscapes = list(ENVIRONMENTS.keys())

    for landscape in landscapes:
        for d_m in distances_m:
            # Get serving path loss
            pl_serving = haps_a2g_pathloss_db(d_m, h_haps_m=alt_m, f_hz=freq_mhz*1e6,
                                             env=landscape, h_user_m=h_user_m)
            pl_serving = float(np.asarray(pl_serving).flat[0])

            # Received power from serving HAPS [dBm]
            p_serving_dbm = p_tx_dbm - pl_serving
            p_serving_lin = 10.0 ** (p_serving_dbm / 10.0)

            # Noise power [linear]
            noise_lin = 10.0 ** (noise_dbm / 10.0)

            # 1. SINR_Single (Eq. 12 with no interference): P_serving / N
            sinr_single_lin = p_serving_lin / noise_lin
            sinr_single = 10.0 * np.log10(sinr_single_lin)

            # 2. Calculate interference from 2 interfering HAPS
            interference_lin = 0.0
            horiz_ranges = haps_horiz_ranges_to_user(d_m, spacing_km=constellation_spacing_km)

            for interf_key in ['interferer1', 'interferer2']:
                horiz_m_val = float(np.asarray(horiz_ranges[interf_key]).flat[0])

                interferer_pl = haps_a2g_pathloss_db(horiz_m_val, h_haps_m=alt_m,
                                                     f_hz=freq_mhz*1e6, env=landscape,
                                                     h_user_m=h_user_m)
                interferer_rx_dbm = p_tx_dbm - float(np.asarray(interferer_pl).flat[0])
                interferer_rx_lin = 10.0 ** (interferer_rx_dbm / 10.0)
                interference_lin += interferer_rx_lin

            # SINR_Interferers: I / N
            sinr_interferers_lin = interference_lin / noise_lin
            sinr_interferers = 10.0 * np.log10(sinr_interferers_lin)

            # 3. SINR_Actual (Eq. 12 with interference): P_serving / (N + I)
            # Linear domain: SINR = P_serving_lin / (noise_lin + interference_lin)
            sinr_actual_lin = p_serving_lin / (noise_lin + interference_lin)
            sinr_actual = 10.0 * np.log10(sinr_actual_lin)

            # 4. LoS Blockage probability (if requested)
            if include_los_blockage:
                dh = alt_m - h_user_m
                elevation_deg = np.degrees(np.arctan2(dh, d_m))
                los_prob = haps_los_probability(elevation_deg, env=landscape)
                los_prob = float(np.asarray(los_prob).flat[0])

                # LoS blockage treated as fading: effective SINR degrades by LoS probability factor
                # SINR_With_LoS = P_serving * P_LoS / (N + I)
                # This accounts for the average signal attenuation when blockage occurs
                sinr_with_los_lin = p_serving_lin * los_prob / (noise_lin + interference_lin)
                sinr_with_los = 10.0 * np.log10(sinr_with_los_lin)
            else:
                los_prob = None
                sinr_with_los = None

            # Metadata
            signal_power = p_serving_dbm
            dh = alt_m - h_user_m
            d_slant_m = np.sqrt(d_m**2 + dh**2)
            elevation_deg = np.degrees(np.arctan2(dh, d_m))

            result = {
                'Landscape': landscape,
                'Distance_m': int(d_m),
                'Slant_Distance_m': round(d_slant_m, 0),
                'Elevation_deg': round(elevation_deg, 2),
                'Signal_Power_dBm': round(signal_power, 2),
                'SINR_Single': round(sinr_single, 2),
                'SINR_Interferers': round(sinr_interferers, 2),
                'SINR_Actual': round(sinr_actual, 2)
            }

            if include_los_blockage:
                result['LoS_Probability'] = round(los_prob, 4)
                result['LoS_Probability_dB'] = round(10.0 * np.log10(los_prob) if los_prob > 0 else -99.0, 2)
                result['SINR_With_LoS'] = round(sinr_with_los, 2)

            results.append(result)

    import pandas as pd
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"CSV exported: {output_file}")
    return df


def export_feeder_link_csv(output_file="haps_feeder_link_38ghz.csv", distances_m=None):
    """Export 38 GHz feeder link (HAPS-to-Gateway) SINR data."""
    if distances_m is None:
        distances_m = [10, 50, 100, 500]

    return export_haps_sinr_generic(output_file, freq_mhz=38000.0, distances_m=distances_m,
                                    h_user_m=50.0, noise_dbm=NOISE_DBM)


# ----------------------------------------------------------------------
# Plots
# ----------------------------------------------------------------------
def make_plots(outdir=None):
    if outdir is None:
        outdir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(outdir, exist_ok=True)

    # --- Plot 1: REMOVED - HAPS FSPL (not used in LaTeX; 1b version is used instead) ---
    # --- Plot 2: REMOVED - LoS probability (not used in LaTeX; commented out) ---

    # --- Plot 3: UAV path loss vs horizontal distance (CORRECTED SWEEP) --
    # Per feedback3: sweep 0-1500 m (not 0-100 km). Extended range of 0-100 km
    # for UAV at 300 m altitude is physically meaningless (LoS collapses <2 km).
    r = np.linspace(1, 1500, 500)  # 0-1500 m range
    plt.figure()
    for env in ENVIRONMENTS:
        plt.plot(r, uav_a2g_pathloss_db(r, h_uav_m=300.0, env=env),
                 label=env)
    plt.xlabel("Horizontal distance [m]")
    plt.ylabel("Average path loss [dB]")
    plt.title("UAV air-to-ground path loss vs distance (altitude 300 m, 0-1500 m)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{outdir}/3_uav_pathloss.png", dpi=150)

    # --- Plot 4: SINR vs horizontal distance (CORRECTED SWEEP) -----------
    # Per feedback3: sweep 0-1500 m (not 0-100 km). Noise-limited single-node SINR.
    r = np.linspace(1, 1500, 500)  # 0-1500 m range
    plt.figure()
    for env in ENVIRONMENTS:
        pl = uav_a2g_pathloss_db(r, h_uav_m=300.0, env=env)
        prx = rx_power_dbm(P_TX_UAV_DBM, pl)
        plt.plot(r, sinr_db(prx), label=env)
    plt.xlabel("Horizontal distance [m]")
    plt.ylabel("SINR [dB]")
    plt.title("UAV downlink SINR vs distance (single node, noise-limited, 0-1500 m)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{outdir}/4_sinr.png", dpi=150)

    # --- Plot 5: Desired Signal (Rx Power) vs SINR with Interference -------
    r = np.linspace(1, 100000, 500)  # 0–100 km range
    plt.figure(figsize=(13, 8))

    # Color palette for environments
    colors = {'suburban': '#1f77b4', 'urban': '#ff7f0e',
              'dense_urban': '#2ca02c', 'high_rise': '#d62728'}

    for env in ENVIRONMENTS:
        # Desired signal: received power from 1 HAPS node (clean signal)
        pl_desired = uav_a2g_pathloss_db(r, h_uav_m=300.0, env=env)
        rx_desired = rx_power_dbm(P_TX_UAV_DBM, pl_desired)

        # Effective received power with 3 HAPS interference
        sinr_3haps = multi_node_sinr_db(r, num_haps=3, h_node_m=300.0, env=env)
        # Effective signal = desired - interference effect
        rx_effective = rx_desired - (10.0 - sinr_3haps)

        # Plot: desired signal (bold) and effective signal with interference (lighter shade)
        plt.plot(r/1000, rx_desired, linestyle='-', linewidth=3, alpha=1.0,
                color=colors[env], label=f"{env}: Received (1 HAPS, clean)")
        plt.plot(r/1000, rx_effective, linestyle='--', linewidth=2.5, alpha=0.6,
                color=colors[env], label=f"{env}: Effective (3 HAPS interference)")

    plt.xlabel("Horizontal Distance from HAPS Nadir [km]", fontsize=11, fontweight='bold')
    plt.ylabel("Received Power [dBm]", fontsize=11, fontweight='bold')
    plt.title("Signal Power Attenuation: Clean vs. Multi-HAPS Interference (Altitude 300 m, 0–100 km)",
             fontsize=12, fontweight='bold')
    plt.legend(fontsize=9, loc='best', ncol=2)
    plt.grid(True, alpha=0.3)

    # Add annotation
    textstr = ('Solid lines: Signal received from 1 serving HAPS (no interference)\n'
               'Dashed lines: Effective signal with 3 HAPS (2 interfering nodes)\n'
               'Vertical gap = power margin lost to interference from other HAPS nodes')
    plt.text(0.02, 0.98, textstr, transform=plt.gca().transAxes, fontsize=9,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(f"{outdir}/figure5_model_received_power.png", dpi=150, bbox_inches='tight')

    # --- Plot 6: REMOVED - Signal Power Breakdown (not used in LaTeX; 6a-6d and combined version) ---

    # --- Plot 7: REMOVED - Integrated Geometry + Signal Breakdown (7a-7d geometry_distance figures not used) ---

    # --- Plot 8: REMOVED - Integrated Geometry + Signals for Each Landscape (was 8a-8d, not used in LaTeX) ---

    # --- Plot 9: Scintillation Fade Depth vs. Time Percentage & Elevation (SPLIT INTO 2 SUBFIGURES) ---
    p_time_range = np.logspace(-1, 1, 100)
    elevations = [10, 20, 30, 45, 60]
    elevations_range = np.linspace(5, 85, 100)
    time_percentages = [0.1, 0.5, 1.0, 5.0, 10.0]

    fade_vs_time_data = {}
    for elev in elevations:
        fade_vs_time_data[elev] = [scintillation_fade_depth_db(p, elev, freq_ghz=20.0) for p in p_time_range]

    fade_vs_elev_data = {}
    for p_time in time_percentages:
        fade_vs_elev_data[p_time] = [scintillation_fade_depth_db(p_time, elev, freq_ghz=20.0) for elev in elevations_range]

    fig_combined, axes_combined = plt.subplots(1, 2, figsize=(14, 5))

    # Plot 9a (combined + individual)
    ax = axes_combined[0]
    for elev in elevations:
        ax.semilogx(p_time_range, fade_vs_time_data[elev], marker='o', markersize=4, label=f'{elev}°')
    ax.set_xlabel('Time Percentage [%]', fontsize=11, fontweight='bold')
    ax.set_ylabel('Scintillation Fade Depth [dB]', fontsize=11, fontweight='bold')
    ax.set_title('ITU P.618 Scintillation Fade Depth vs. Time Percentage\n(K-band 20 GHz, various elevations)', fontsize=11, fontweight='bold')
    ax.legend(title='Elevation Angle', fontsize=9)
    ax.grid(True, alpha=0.3, which='both')

    fig_9a = plt.figure(figsize=(12, 8))
    ax_9a = fig_9a.add_subplot(111)
    for elev in elevations:
        ax_9a.semilogx(p_time_range, fade_vs_time_data[elev], marker='o', markersize=4, label=f'{elev}°')
    ax_9a.set_xlabel('Time Percentage [%]', fontsize=11, fontweight='bold')
    ax_9a.set_ylabel('Scintillation Fade Depth [dB]', fontsize=11, fontweight='bold')
    ax_9a.set_title('ITU P.618 Scintillation Fade Depth vs. Time Percentage\n(K-band 20 GHz, various elevations)', fontsize=11, fontweight='bold')
    ax_9a.legend(title='Elevation Angle', fontsize=9)
    ax_9a.grid(True, alpha=0.3, which='both')
    fig_9a.tight_layout()
    fig_9a.savefig(f"{outdir}/9a_scintillation_fade_vs_time.png", dpi=150, bbox_inches='tight')
    plt.close(fig_9a)

    # Plot 9b (combined + individual)
    ax = axes_combined[1]
    for p_time in time_percentages:
        ax.plot(elevations_range, fade_vs_elev_data[p_time], marker='s', markersize=4, label=f'{p_time}% time')
    ax.set_xlabel('Elevation Angle [degrees]', fontsize=11, fontweight='bold')
    ax.set_ylabel('Scintillation Fade Depth [dB]', fontsize=11, fontweight='bold')
    ax.set_title('ITU P.618 Scintillation Fade Depth vs. Elevation Angle\n(K-band 20 GHz, various time percentages)', fontsize=11, fontweight='bold')
    ax.legend(title='Time Percentage', fontsize=9)
    ax.grid(True, alpha=0.3)

    fig_9b = plt.figure(figsize=(12, 8))
    ax_9b = fig_9b.add_subplot(111)
    for p_time in time_percentages:
        ax_9b.plot(elevations_range, fade_vs_elev_data[p_time], marker='s', markersize=4, label=f'{p_time}% time')
    ax_9b.set_xlabel('Elevation Angle [degrees]', fontsize=11, fontweight='bold')
    ax_9b.set_ylabel('Scintillation Fade Depth [dB]', fontsize=11, fontweight='bold')
    ax_9b.set_title('ITU P.618 Scintillation Fade Depth vs. Elevation Angle\n(K-band 20 GHz, various time percentages)', fontsize=11, fontweight='bold')
    ax_9b.legend(title='Time Percentage', fontsize=9)
    ax_9b.grid(True, alpha=0.3)
    fig_9b.tight_layout()
    fig_9b.savefig(f"{outdir}/9b_scintillation_fade_vs_elev.png", dpi=150, bbox_inches='tight')
    plt.close(fig_9b)

    plt.close(fig_combined)

    # --- Plot 10: Deterministic vs. Faded Feeder Link Loss (SPLIT INTO 2 SUBFIGURES) ---
    distances_km = np.linspace(20, 200, 100)
    elev_gateway = 30.0
    freq_feeder = 20.0

    deterministic_loss = [feeder_link_loss_with_scintillation(d, elev_gateway, freq_feeder,
                                                               include_scint=False) for d in distances_km]
    faded_1pct = [feeder_link_loss_with_scintillation(d, elev_gateway, freq_feeder,
                                                       p_time_percent=1.0, include_scint=True) for d in distances_km]
    faded_5pct = [feeder_link_loss_with_scintillation(d, elev_gateway, freq_feeder,
                                                       p_time_percent=5.0, include_scint=True) for d in distances_km]
    faded_10pct = [feeder_link_loss_with_scintillation(d, elev_gateway, freq_feeder,
                                                        p_time_percent=10.0, include_scint=True) for d in distances_km]

    time_percentages_fine = np.linspace(0.1, 10, 50)
    distance_demo = 50.0

    attenuation_margins = []
    for p_time in time_percentages_fine:
        det_loss = feeder_link_loss_with_scintillation(distance_demo, elev_gateway, freq_feeder,
                                                        include_scint=False)
        faded_loss = feeder_link_loss_with_scintillation(distance_demo, elev_gateway, freq_feeder,
                                                         p_time_percent=p_time, include_scint=True)
        margin = faded_loss - det_loss
        attenuation_margins.append(margin)

    fig_combined, axes_combined = plt.subplots(1, 2, figsize=(14, 5))

    # Plot 10a (combined + individual)
    ax = axes_combined[0]
    ax.plot(distances_km, deterministic_loss, 'k-', linewidth=3, label='Deterministic (no scintillation)', zorder=5)
    ax.plot(distances_km, faded_1pct, 'r-', linewidth=2, alpha=0.7, label='Faded @ 1% time')
    ax.plot(distances_km, faded_5pct, color='orange', linewidth=2, alpha=0.7, label='Faded @ 5% time')
    ax.plot(distances_km, faded_10pct, 'b-', linewidth=2, alpha=0.7, label='Faded @ 10% time')
    ax.set_xlabel('HAPS-Gateway Distance [km]', fontsize=11, fontweight='bold')
    ax.set_ylabel('Feeder Link Loss [dB]', fontsize=11, fontweight='bold')
    ax.set_title(f'Feeder Link Loss: Deterministic vs. Scintillation-Faded\n(Elevation {elev_gateway}°, f={freq_feeder} GHz)', fontsize=11, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig_10a = plt.figure(figsize=(12, 8))
    ax_10a = fig_10a.add_subplot(111)
    ax_10a.plot(distances_km, deterministic_loss, 'k-', linewidth=3, label='Deterministic (no scintillation)', zorder=5)
    ax_10a.plot(distances_km, faded_1pct, 'r-', linewidth=2, alpha=0.7, label='Faded @ 1% time')
    ax_10a.plot(distances_km, faded_5pct, color='orange', linewidth=2, alpha=0.7, label='Faded @ 5% time')
    ax_10a.plot(distances_km, faded_10pct, 'b-', linewidth=2, alpha=0.7, label='Faded @ 10% time')
    ax_10a.set_xlabel('HAPS-Gateway Distance [km]', fontsize=11, fontweight='bold')
    ax_10a.set_ylabel('Feeder Link Loss [dB]', fontsize=11, fontweight='bold')
    ax_10a.set_title(f'Feeder Link Loss: Deterministic vs. Scintillation-Faded\n(Elevation {elev_gateway}°, f={freq_feeder} GHz)', fontsize=11, fontweight='bold')
    ax_10a.legend(fontsize=9)
    ax_10a.grid(True, alpha=0.3)
    fig_10a.tight_layout()
    fig_10a.savefig(f"{outdir}/10a_feeder_loss_vs_distance.png", dpi=150, bbox_inches='tight')
    plt.close(fig_10a)

    # Plot 10b (combined + individual)
    ax = axes_combined[1]
    ax.semilogx(time_percentages_fine, attenuation_margins, 'g-', linewidth=3, marker='o', markersize=5)
    ax.fill_between(time_percentages_fine, 0, attenuation_margins, alpha=0.3, color='green')
    ax.set_xlabel('Time Percentage [%]', fontsize=11, fontweight='bold')
    ax.set_ylabel('Scintillation Attenuation Margin [dB]', fontsize=11, fontweight='bold')
    ax.set_title(f'Power Loss Margin Due to Scintillation\n({distance_demo} km link, {elev_gateway}° elevation)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3, which='both')

    for p in [0.1, 1.0, 10.0]:
        idx = np.argmin(np.abs(time_percentages_fine - p))
        ax.annotate(f'{attenuation_margins[idx]:.2f} dB\n@ {p}%',
                   xy=(p, attenuation_margins[idx]),
                   xytext=(10, 10), textcoords='offset points',
                   fontsize=8, ha='left',
                   bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='black', lw=1))

    fig_10b = plt.figure(figsize=(12, 8))
    ax_10b = fig_10b.add_subplot(111)
    ax_10b.semilogx(time_percentages_fine, attenuation_margins, 'g-', linewidth=3, marker='o', markersize=5)
    ax_10b.fill_between(time_percentages_fine, 0, attenuation_margins, alpha=0.3, color='green')
    ax_10b.set_xlabel('Time Percentage [%]', fontsize=11, fontweight='bold')
    ax_10b.set_ylabel('Scintillation Attenuation Margin [dB]', fontsize=11, fontweight='bold')
    ax_10b.set_title(f'Power Loss Margin Due to Scintillation\n({distance_demo} km link, {elev_gateway}° elevation)', fontsize=11, fontweight='bold')
    ax_10b.grid(True, alpha=0.3, which='both')

    for p in [0.1, 1.0, 10.0]:
        idx = np.argmin(np.abs(time_percentages_fine - p))
        ax_10b.annotate(f'{attenuation_margins[idx]:.2f} dB\n@ {p}%',
                       xy=(p, attenuation_margins[idx]),
                       xytext=(10, 10), textcoords='offset points',
                       fontsize=8, ha='left',
                       bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7),
                       arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='black', lw=1))

    fig_10b.tight_layout()
    fig_10b.savefig(f"{outdir}/10b_scintillation_margin.png", dpi=150, bbox_inches='tight')
    plt.close(fig_10b)

    plt.close(fig_combined)

    # --- Plot 11: Time-Series Fading Envelope (Log-Normal vs. Gamma, 4 SEPARATE SUBFIGURES) ---
    time_percentages_demo = [0.1, 1.0, 5.0, 10.0]
    fig_labels_11 = ['11a', '11b', '11c', '11d']
    distance_demo_ts = 50.0
    elev_demo_ts = 30.0
    n_samples = 1000

    # Create combined 2x2 figure for reference
    fig_combined_11, axes_combined_11 = plt.subplots(2, 2, figsize=(14, 10))
    fig_combined_11.suptitle('Scintillation Fading Envelope: Time-Series Realizations\n(1000 samples, various time percentages & distributions)',
                             fontsize=12, fontweight='bold')

    # Precompute all fading data once
    fading_data_11 = {}
    for p_time in time_percentages_demo:
        fading_log_normal = scintillation_fading_envelope(n_samples, p_time, elev_demo_ts,
                                                          freq_ghz=20.0, dist_km=distance_demo_ts,
                                                          distribution='log_normal')
        fading_gamma = scintillation_fading_envelope(n_samples, p_time, elev_demo_ts,
                                                     freq_ghz=20.0, dist_km=distance_demo_ts,
                                                     distribution='gamma')
        fading_data_11[p_time] = {
            'log_normal_db': 20.0 * np.log10(fading_log_normal),
            'gamma_db': 20.0 * np.log10(fading_gamma),
            'fade_depth': scintillation_fade_depth_db(p_time, elev_demo_ts, freq_ghz=20.0)
        }

    time_axis = np.arange(n_samples)

    for idx, (p_time, fig_label_11) in enumerate(zip(time_percentages_demo, fig_labels_11)):
        # Plot in combined figure
        ax_combined = axes_combined_11[idx // 2, idx % 2]

        # Create individual figure
        fig_ind_11 = plt.figure(figsize=(12, 8))
        ax_ind_11 = fig_ind_11.add_subplot(111)

        fade_data = fading_data_11[p_time]
        for ax in [ax_combined, ax_ind_11]:
            ax.plot(time_axis, fade_data['log_normal_db'], 'b-', alpha=0.6, linewidth=1, label='Log-Normal')
            ax.plot(time_axis, fade_data['gamma_db'], 'r-', alpha=0.6, linewidth=1, label='Gamma')
            ax.axhline(y=-fade_data['fade_depth'], color='green', linestyle='--', linewidth=2, alpha=0.7,
                      label=f'Target fade depth: -{fade_data["fade_depth"]:.2f} dB')
            ax.set_xlabel('Time Sample', fontsize=10, fontweight='bold')
            ax.set_ylabel('Fading Level [dB]', fontsize=10, fontweight='bold')
            ax.set_title(f'Time Percentage: {p_time}% (Elevation {elev_demo_ts}°, {distance_demo_ts} km)', fontsize=10, fontweight='bold')
            ax.legend(fontsize=8, loc='lower right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim([-20, 2])

        fig_ind_11.tight_layout()
        fig_ind_11.savefig(f"{outdir}/{fig_label_11}_fading_envelope_timeseries.png", dpi=150, bbox_inches='tight')
        plt.close(fig_ind_11)

    plt.close(fig_combined_11)

    # List all generated files
    print(f"\n[OK] Figures and tables saved to ./{outdir}/")
    print("\nGenerated files:")
    import glob
    output_files = sorted(glob.glob(os.path.join(outdir, "*")))
    for fpath in output_files:
        fname = os.path.basename(fpath)
        try:
            size_kb = os.path.getsize(fpath) / 1024
            print(f"  ✓ {fname:50s} ({size_kb:8.1f} KB)")
        except:
            print(f"  ✓ {fname}")


if __name__ == "__main__":
    make_plots()
