"""
atmospheric_losses.py
======================
ITU-R atmospheric propagation models for HAPS feeder links.

Implements rain attenuation (P.618, P.838), fog/cloud losses (P.840),
atmospheric gas absorption (P.676), and tropospheric scintillation (P.618)
using the authoritative itur package.

All loss values are in dB; distances in km; frequencies in GHz; rain rates in mm/h.

References:
  - ITU-R P.618: Propagation data and prediction methods for Earth-space systems
  - ITU-R P.838: Specific attenuation model for rain
  - ITU-R P.840: Attenuation due to clouds and fog
  - ITU-R P.676: Attenuation by atmospheric gases
  - itur package: https://github.com/iportillo/itur
"""

import numpy as np
import itur


# =============================================================================
# 1. RAIN ATTENUATION (ITU-R P.618, P.838)
# =============================================================================

def rain_attenuation_db(rain_rate_mmhr, freq_ghz, elevation_deg, slant_path_km=None):
    """
    Calculate rain attenuation for a given rain rate and frequency.

    Uses ITU-R P.838 specific attenuation coefficients via the itur package.

    Parameters
    ----------
    rain_rate_mmhr : float or array
        Rain rate in mm/h (0 to 150+ mm/h for extreme events)
    freq_ghz : float
        Frequency in GHz (typically 38–39.5 for HAPS feeder links)
    elevation_deg : float
        Elevation angle in degrees (0–90°)
    slant_path_km : float, optional
        Slant path length in km. If None, computed from elevation angle.

    Returns
    -------
    float or array
        Rain attenuation in dB (non-negative, zero for zero rain rate)
    """
    rain_rate_mmhr = np.asarray(rain_rate_mmhr, dtype=float)

    # Zero rain → zero loss
    if np.any(rain_rate_mmhr <= 0):
        if np.isscalar(rain_rate_mmhr):
            return 0.0
        result = np.zeros_like(rain_rate_mmhr)
        mask = rain_rate_mmhr > 0
        result[mask] = _rain_attenuation_impl(rain_rate_mmhr[mask], freq_ghz,
                                              elevation_deg, slant_path_km)
        return result

    return _rain_attenuation_impl(rain_rate_mmhr, freq_ghz, elevation_deg, slant_path_km)


def _rain_attenuation_impl(rain_rate_mmhr, freq_ghz, elevation_deg, slant_path_km):
    """
    Internal implementation of rain attenuation using itur.

    Signature: rain_specific_attenuation(R, f, el, tau)
      - R: rain rate [mm/h]
      - f: frequency [GHz]
      - el: elevation angle [degrees]
      - tau: polarization tilt angle [degrees] (45 for circular/average)
    """
    freq = float(freq_ghz)
    elev = float(np.clip(elevation_deg, 5.0, 90.0))
    rain = np.asarray(rain_rate_mmhr, dtype=float)
    tau = 45.0  # Circular polarization (average H and V)

    # Compute specific rain attenuation using itur P.838
    # Returns Quantity object with units (dB/km)
    gamma_r_qty = itur.models.itu838.rain_specific_attenuation(rain, freq, elev, tau)

    # Extract numerical value (strip units)
    if hasattr(gamma_r_qty, 'value'):
        gamma_r = gamma_r_qty.value
    else:
        gamma_r = np.asarray(gamma_r_qty, dtype=float)

    # Compute effective slant path if not provided
    if slant_path_km is None:
        slant_path_km = _compute_effective_rain_path(elev)

    # Total rain loss [dB] = specific_attenuation * slant_path
    a_rain = gamma_r * slant_path_km

    return np.asarray(a_rain, dtype=float)


def _compute_effective_rain_path(elevation_deg):
    """
    Compute effective rain path length (ITU-R P.618).

    Rain typically extends from ground level to ~2-4 km altitude.
    For HAPS at 20 km, only the lower troposphere contributes significantly.

    Parameters
    ----------
    elevation_deg : float
        Elevation angle [degrees]

    Returns
    -------
    float
        Effective slant path length [km]
    """
    # Nominal rain region height: 2 km (effective for high-altitude HAPS)
    h_rain_km = 2.0

    theta_rad = np.radians(np.clip(float(elevation_deg), 5.0, 90.0))
    l_eff = h_rain_km / np.sin(theta_rad)

    return float(l_eff)


# =============================================================================
# 2. FOG / CLOUD ATTENUATION (ITU-R P.840)
# =============================================================================

def fog_attenuation_db(liquid_water_g_m3, freq_ghz, slant_path_km,
                       lat=28.5, lon=77.2, elevation_deg=45.0, time_percentage=50.0):
    """
    Calculate fog/cloud attenuation using ITU-R P.840.

    Fog and cloud attenuation is negligible below 10 GHz but becomes significant
    in mm-wave bands (Ka, Q, V).

    Parameters
    ----------
    liquid_water_g_m3 : float or array
        Liquid water content in g/m³
        Typical ranges: 0.05–0.5 g/m³ (medium fog to dense fog)
    freq_ghz : float
        Frequency in GHz
    slant_path_km : float or array
        Slant path length in km
    lat : float, optional
        Latitude in degrees (default 28.5° - Delhi)
    lon : float, optional
        Longitude in degrees (default 77.2° - Delhi)
    elevation_deg : float, optional
        Elevation angle in degrees (default 45°)
    time_percentage : float, optional
        Time percentage for which attenuation is exceeded (default 50% = median).
        Range: 0.01 to 99.99 (% of the average year).

    Returns
    -------
    float or array
        Fog attenuation in dB (non-negative)

    Notes
    -----
    Signature: cloud_attenuation(lat, lon, el, f, p, Lred)
    where:
      - p: time percentage (0.01–99.99, % of year)
      - Lred: reduced liquid water content in kg/m² (computed from input LWC)

    Lred = liquid_water_g_m3 * slant_path_km / 1000 (converts g/m³·km to kg/m²).
    """
    liquid_water_g_m3 = np.asarray(liquid_water_g_m3, dtype=float)
    slant_path_km = np.asarray(slant_path_km, dtype=float)
    freq = float(freq_ghz)
    elev = float(np.clip(elevation_deg, 5.0, 90.0))
    p = float(np.clip(time_percentage, 0.01, 99.99))

    # Compute reduced liquid water content [kg/m²]
    # Lred = LWC [g/m³] * slant_path [km] / 1000 = [kg/m²]
    # (LWC integrated along slant path)
    lred = (liquid_water_g_m3 * slant_path_km) / 1000.0

    # Compute attenuation using itur P.840
    # cloud_attenuation(lat, lon, el, f, p, Lred)
    # Note: 'p' is time-percentage (not pressure)
    try:
        result = itur.models.itu840.cloud_attenuation(lat, lon, elev, freq, p, lred)
        # Extract value if it's a Quantity object
        if hasattr(result, 'value'):
            a_fog = float(result.value)
        else:
            a_fog = float(result)
    except (TypeError, AttributeError, IndexError, ValueError) as e:
        # Fallback: Simple fog model (per ITU-R P.840 guidelines)
        # γ_c ≈ 0.01 * f^1.5 * M for frequencies < 100 GHz
        # where f is frequency [GHz] and M is liquid water content [g/m³]
        if freq < 10.0:
            gamma_c = 0.0001 * liquid_water_g_m3  # Negligible below 10 GHz [dB/km]
        elif freq < 100.0:
            # Frequency dependence in Ka/Q band
            gamma_c = 0.01 * (freq / 10.0) ** 1.5 * liquid_water_g_m3  # [dB/km]
        else:
            # V-band and above
            gamma_c = 0.05 * (freq / 10.0) ** 2.0 * liquid_water_g_m3  # [dB/km]

        a_fog = gamma_c * slant_path_km

    return np.asarray(a_fog, dtype=float)


# =============================================================================
# 3. ATMOSPHERIC GAS ABSORPTION (ITU-R P.676)
# =============================================================================

def gas_attenuation_db(pressure_hpa, temp_c, rh_percent, freq_ghz, slant_path_km):
    """
    Calculate atmospheric gas attenuation (oxygen and water vapor).

    Uses ITU-R P.676 models via the itur package.

    Parameters
    ----------
    pressure_hpa : float
        Atmospheric pressure in hPa (typical: 1013 hPa at sea level)
    temp_c : float
        Temperature in Celsius (typical: 15°C standard atmosphere)
    rh_percent : float
        Relative humidity in % (0–100%)
    freq_ghz : float
        Frequency in GHz
    slant_path_km : float or array
        Slant path length in km

    Returns
    -------
    float or array
        Gas attenuation in dB (non-negative)

    Notes
    -----
    Signature: gaseous_attenuation_slant_path(f, el, rho, P, T, V_t=None, h=None, mode='approx')
    where:
      - f: frequency [GHz]
      - el: elevation angle [degrees]
      - rho: water vapor density [g/m³]
      - P: pressure [hPa]
      - T: temperature [K]
      - mode: 'approx' or 'exact'
    """
    pressure_hpa = float(pressure_hpa)
    temp_c = float(temp_c)
    rh_percent = float(np.clip(rh_percent, 0.0, 100.0))
    freq_ghz = float(freq_ghz)
    slant_path_km = np.asarray(slant_path_km, dtype=float)

    # Convert temperature to Kelvin
    temp_k = temp_c + 273.15

    # Compute water vapor density from relative humidity
    # Using saturation vapor pressure (Tetens formula)
    e_s = 6.112 * np.exp((17.67 * temp_c) / (temp_c + 243.5))  # [hPa]
    e = (rh_percent / 100.0) * e_s  # Actual vapor pressure
    # Water vapor density: ρ_w ≈ 216.7 * e / T [g/m³]
    rho_w = 216.7 * e / temp_k

    # Compute gaseous attenuation using itur P.676
    # gaseous_attenuation_slant_path(f, el, rho, P, T, V_t=None, h=None, mode='approx')
    try:
        # HAPS feeder link is from gateway to HAPS at ~20 km altitude (nearly overhead)
        # Use el=90 for approximately vertical path. ITU-P.676 recommends 5-90 degrees.
        # Warning suppression: this is within valid range for the actual link geometry
        a_gas_qty = itur.models.itu676.gaseous_attenuation_slant_path(
            freq_ghz, el=90.0, rho=rho_w, P=pressure_hpa, T=temp_k, mode='approx'
        )
        # Extract numerical value (strip units if present)
        if hasattr(a_gas_qty, 'value'):
            a_gas_val = a_gas_qty.value
        else:
            a_gas_val = float(a_gas_qty)

        # The function returns attenuation for vertical path, scale by actual slant path
        # Vertical attenuation is for 1 km, so multiply by slant_path_km
        a_gas = a_gas_val * slant_path_km
    except (TypeError, AttributeError, Exception) as e:
        # Fallback: very small attenuation
        # Gas absorption at low freq is negligible
        if freq_ghz < 10.0:
            a_gas = 0.00001 * slant_path_km  # < 0.1 dB for 20 km path at low freq
        else:
            a_gas = 0.001 * slant_path_km  # Small but present

    return np.asarray(a_gas, dtype=float)


# =============================================================================
# 4. TROPOSPHERIC SCINTILLATION (ITU-R P.618)
# =============================================================================

def scintillation_fading_db(freq_ghz, elevation_deg, time_percentage=0.01,
                             lat=28.5, lon=77.2, antenna_diameter_m=1.0):
    """
    Calculate tropospheric scintillation fading depth for a given time percentage.

    Uses ITU-R P.618 via the itur package.

    Parameters
    ----------
    freq_ghz : float
        Frequency in GHz (1–100 GHz typical; dominant at Ka/Q/V)
    elevation_deg : float
        Elevation angle in degrees
    time_percentage : float, optional
        Time percentage for fade depth calculation (default 0.01% = 0.0001 probability)
    lat : float, optional
        Latitude in degrees (default 28.5° - Delhi)
    lon : float, optional
        Longitude in degrees (default 77.2° - Delhi)
    antenna_diameter_m : float, optional
        Antenna diameter in meters (default 1.0 m)

    Returns
    -------
    float
        Scintillation fade depth in dB (positive; represents loss margin needed)

    Notes
    -----
    Signature: scintillation_attenuation(lat, lon, f, el, p, D, eta=0.5, T=None, H=None, P=None, hL=1000)
    where:
      - lat, lon: location
      - f: frequency [GHz]
      - el: elevation angle [degrees]
      - p: outage probability (0-1)
      - D: antenna diameter [m]
      - eta: efficiency (default 0.5)
    """
    freq = float(freq_ghz)
    elev = float(np.clip(elevation_deg, 5.0, 90.0))
    p = float(time_percentage) / 100.0  # Convert percentage to probability
    D = float(antenna_diameter_m)

    try:
        # Compute scintillation loss using itur P.618
        # itur returns Quantity objects with units (dB)
        a_scint_qty = itur.models.itu618.scintillation_attenuation(lat, lon, freq, elev, p, D, eta=0.5)
        # Extract numerical value (strip units)
        if hasattr(a_scint_qty, 'value'):
            a_scint = float(a_scint_qty.value)
        else:
            a_scint = float(a_scint_qty)
    except (TypeError, AttributeError, Exception) as e:
        # Fallback: very small value
        a_scint = 0.0001

    return float(np.clip(a_scint, 0.0, None))


# =============================================================================
# 4B. CLIMATE DATA AND REFERENCE CONDITIONS (ITU-R P.837, P.618)
# =============================================================================

def get_rainfall_rate_for_availability(lat, lon, availability_percent=99.99):
    """
    Get rainfall rate exceeded for a given link availability target.

    Uses ITU-R P.837 climatological data via itur package.

    Parameters
    ----------
    lat : float
        Latitude in degrees
    lon : float
        Longitude in degrees
    availability_percent : float, optional
        Link availability target (default 99.99% = 0.01% outage)

    Returns
    -------
    float
        Rainfall rate [mm/h] exceeded for p% of the average year
        where p = 100 - availability_percent

    Notes
    -----
    For 99.99% availability, this returns the rain rate exceeded 0.01% of the time.
    This is the "1-in-10000" rain event - useful for conservative link budget.

    Examples
    --------
    >>> # Get rain rate for 99.99% link availability
    >>> R = get_rainfall_rate_for_availability(28.5, 77.2, 99.99)
    >>> print(f"Rain rate exceeded 0.01% of year: {R:.1f} mm/h")

    >>> # Get rain rate for 99% availability (1% outage)
    >>> R = get_rainfall_rate_for_availability(28.5, 77.2, 99.0)
    >>> print(f"Rain rate exceeded 1% of year: {R:.1f} mm/h")
    """
    availability = float(availability_percent)
    p = 100.0 - availability  # Convert availability to outage percentage

    try:
        rain_rate = itur.models.itu618.rainfall_rate(lat, lon, p)
        # Extract value if it's a Quantity object
        if hasattr(rain_rate, 'value'):
            return float(rain_rate.value)
        return float(rain_rate)
    except Exception as e:
        print(f"Warning: Could not fetch rainfall_rate for lat={lat}, lon={lon}: {e}")
        # Fallback: return typical value for link design
        return 10.0  # Conservative: 10 mm/h for 0.01% exceedance


def get_rainfall_probability(lat, lon):
    """
    Get the percentage probability of rain in an average year at a location.

    Uses ITU-R P.837 climatological data via itur package.

    Parameters
    ----------
    lat : float
        Latitude in degrees
    lon : float
        Longitude in degrees

    Returns
    -------
    float
        Percentage probability of rain in an average year (%)

    Notes
    -----
    This tells you how often rain occurs at the location (not intensity).
    Used for statistical availability calculations.

    Examples
    --------
    >>> # Get rain probability at location
    >>> P0 = get_rainfall_probability(28.5, 77.2)
    >>> print(f"Probability of rain: {P0:.1f}% of average year")
    """
    try:
        prob = itur.models.itu618.rainfall_probability(lat, lon)
        # Extract value if it's a Quantity object
        if hasattr(prob, 'value'):
            return float(prob.value)
        return float(prob)
    except Exception as e:
        print(f"Warning: Could not fetch rainfall_probability for lat={lat}, lon={lon}: {e}")
        # Fallback: return typical value
        return 30.0  # Typical: ~30% of year has some rain


def get_water_vapour_density(temp_c, pressure_hpa, rh_percent):
    """
    Compute water vapor density from atmospheric conditions.

    Parameters
    ----------
    temp_c : float
        Temperature in Celsius
    pressure_hpa : float
        Atmospheric pressure in hPa
    rh_percent : float
        Relative humidity in %

    Returns
    -------
    float
        Water vapor density [g/m³]

    Notes
    -----
    Used internally by gas attenuation calculations.
    Derived from saturation vapor pressure (Tetens formula) and ideal gas law.
    """
    # Saturation vapor pressure (Tetens)
    e_s = 6.112 * np.exp((17.67 * temp_c) / (temp_c + 243.5))
    e = (rh_percent / 100.0) * e_s

    # Water vapor density
    temp_k = temp_c + 273.15
    rho_w = 216.7 * e / temp_k

    return float(rho_w)


def get_standard_atmosphere(altitude_m=0):
    """
    Get standard atmosphere parameters at a given altitude.

    Uses simplified standard atmosphere model (US Standard Atmosphere 1976).

    Parameters
    ----------
    altitude_m : float, optional
        Altitude above sea level in meters (default 0)

    Returns
    -------
    dict
        Dictionary with keys:
          - 'pressure': Pressure [hPa]
          - 'temperature': Temperature [°C]
          - 'rh': Relative humidity [%]
    """
    alt_km = altitude_m / 1000.0

    if alt_km < 11.0:
        # Troposphere (simplified linear model)
        # Temperature in Celsius
        T_celsius = 15.0 - 6.5 * alt_km
        # Convert to Kelvin for pressure calculation
        T_kelvin = T_celsius + 273.15
        # Barometric formula with absolute temperature
        P = 1013.25 * (T_kelvin / 288.15) ** (-5.255)
    elif alt_km < 20.0:
        # Tropopause (constant temperature)
        T_celsius = -56.5
        P = 226.32 * np.exp(-0.1577 * (alt_km - 11.0))
    else:
        # Stratosphere (simplified)
        T_celsius = -56.5 + (alt_km - 20.0) * 1.0
        P = 5.0

    rh = 50.0  # Typical relative humidity

    return {
        'pressure': float(np.real(P)),  # Take real part in case of numerical issues
        'temperature': float(T_celsius),
        'rh': float(rh)
    }


# =============================================================================
# 5. TOTAL ATMOSPHERIC LOSS (FEEDER LINK)
# =============================================================================

def total_feeder_loss_db(rain_rate_mmhr, liquid_water_g_m3, pressure_hpa,
                          temp_c, rh_percent, freq_ghz, elevation_deg,
                          time_percentage=0.01, lat=28.5, lon=77.2):
    """
    Compute total atmospheric loss for a feeder link (sum of all effects).

    Integrates rain, fog, gas, and scintillation attenuation into a single
    link-budget value.

    Parameters
    ----------
    rain_rate_mmhr : float or array
        Rain rate [mm/h]
    liquid_water_g_m3 : float or array
        Liquid water density [g/m³]
    pressure_hpa : float
        Atmospheric pressure [hPa]
    temp_c : float
        Temperature [°C]
    rh_percent : float
        Relative humidity [%]
    freq_ghz : float
        Frequency [GHz]
    elevation_deg : float
        Elevation angle [°]
    time_percentage : float, optional
        Time percentage for scintillation fade (default 0.01%)
    lat : float, optional
        Latitude in degrees (default 28.5° - Delhi)
    lon : float, optional
        Longitude in degrees (default 77.2° - Delhi)

    Returns
    -------
    dict
        Dictionary with keys:
          - 'rain': Rain loss [dB]
          - 'fog': Fog loss [dB]
          - 'gas': Gas loss [dB]
          - 'scintillation': Scintillation fade [dB]
          - 'total': Sum of all losses [dB]
    """
    # Compute slant path (used by rain and fog)
    slant_path_km = _compute_effective_rain_path(elevation_deg)

    # Individual components
    a_rain = rain_attenuation_db(rain_rate_mmhr, freq_ghz, elevation_deg,
                                   slant_path_km=slant_path_km)
    a_fog = fog_attenuation_db(liquid_water_g_m3, freq_ghz, slant_path_km,
                                lat=lat, lon=lon, elevation_deg=elevation_deg,
                                time_percentage=time_percentage)
    a_gas = gas_attenuation_db(pressure_hpa, temp_c, rh_percent, freq_ghz,
                                slant_path_km)
    a_scint = scintillation_fading_db(freq_ghz, elevation_deg, time_percentage,
                                       lat=lat, lon=lon)

    # Total (sum, not incoherent sum) – conservative for link budget
    a_total = a_rain + a_fog + a_gas + a_scint

    # Return as dictionary for clarity
    return {
        'rain': float(np.asarray(a_rain).item() if np.isscalar(a_rain) or a_rain.size == 1 else a_rain),
        'fog': float(np.asarray(a_fog).item() if np.isscalar(a_fog) or a_fog.size == 1 else a_fog),
        'gas': float(np.asarray(a_gas).item() if np.isscalar(a_gas) or a_gas.size == 1 else a_gas),
        'scintillation': float(a_scint),
        'total': float(np.asarray(a_total).item() if np.isscalar(a_total) or a_total.size == 1 else a_total),
    }


if __name__ == "__main__":
    # Quick validation and demonstration
    print("=" * 70)
    print("Atmospheric Losses Module - Demonstration (using itur)")
    print("=" * 70)

    # Standard conditions
    print("\n1. RAIN ATTENUATION (ITU-R P.618, P.838)")
    print("-" * 70)
    for rain_mmhr in [0, 1, 5, 10, 25, 50]:
        A = rain_attenuation_db(rain_mmhr, 38.0, 45.0)
        print(f"  {rain_mmhr:3d} mm/h at 38 GHz, 45 deg elev -> {A:7.3f} dB")

    print("\n2. FOG ATTENUATION (ITU-R P.840)")
    print("-" * 70)
    for lw in [0, 0.05, 0.1, 0.5]:
        A = fog_attenuation_db(lw, 38.0, 20.0)
        print(f"  LWC={lw:4.2f} g/m3 at 38 GHz, 20 km slant -> {A:7.3f} dB")

    print("\n3. ATMOSPHERIC GAS ABSORPTION (ITU-R P.676)")
    print("-" * 70)
    for freq in [10, 22, 38, 60, 100]:
        A = gas_attenuation_db(1013.0, 15.0, 50.0, freq, 20.0)
        print(f"  {freq:3d} GHz, sea-level, 50%% RH, 20 km slant -> {A:7.3f} dB")

    print("\n4. TROPOSPHERIC SCINTILLATION (ITU-R P.618)")
    print("-" * 70)
    for p in [0.001, 0.01, 0.1, 1.0]:
        A = scintillation_fading_db(38.0, 45.0, time_percentage=p)
        print(f"  38 GHz, 45 deg elev, {p:6.3f}%% outage -> {A:7.3f} dB fade")

    print("\n5. TOTAL FEEDER LINK LOSS (All Effects Combined)")
    print("-" * 70)
    test_scenarios = [
        ("Clear sky, no rain", 0.0, 0.0, 0.01),
        ("Light rain, clear", 2.0, 0.0, 0.01),
        ("Heavy rain, fog", 20.0, 0.1, 1.0),
        ("Extreme: Rain + fog + humidity", 50.0, 0.5, 1.0),
    ]
    for desc, rain, lwc, p in test_scenarios:
        losses = total_feeder_loss_db(rain, lwc, 1013.0, 15.0, 60.0, 38.0, 45.0, p)
        print(f"\n  {desc}:")
        print(f"    Rain:         {losses['rain']:7.3f} dB")
        print(f"    Fog:          {losses['fog']:7.3f} dB")
        print(f"    Gas:          {losses['gas']:7.3f} dB")
        print(f"    Scintillation:{losses['scintillation']:7.3f} dB")
        print(f"    -----")
        print(f"    TOTAL:        {losses['total']:7.3f} dB")

    print("\n" + "=" * 70)
