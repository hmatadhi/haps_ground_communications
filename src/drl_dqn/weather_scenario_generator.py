"""
weather_scenario_generator.py
=============================
Weather profile generation for Phase 2 DQN training.

Generates synthetic weather scenarios covering:
  - Rain rates: 0, 2, 5, 10, 20 mm/h (ITU-R P.838 range)
  - Visibility: >10, 5-10, <5, <1 km
  - Diurnal cycles: 0-24h (affects scintillation, solar gain, wind)
  - Composite profiles: rain + visibility + time-of-day

Weather is sampled ONCE per episode (static for episode duration), matching
the timescale of a 50-step episode (~5 min simulation time).
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class WeatherScenario:
    """Immutable weather state for one episode.

    Includes all atmospheric effects per ITU-R models:
    - Rain (P.838)
    - Fog/Cloud (P.840)
    - Atmospheric Gas (P.676)
    - Scintillation (P.618)

    Attributes:
        rain_mm_h (float): Rainfall rate [0-25 mm/h]. ITU-R P.838 typical max.
        visibility_km (float): Line-of-sight range [0.1-20 km]. Controls LoS prob.
        hour_of_day (float): Hour [0-24). Affects HAPS solar / scintillation.
        liquid_water_g_m3 (float): Fog/cloud liquid water content [g/m3]. ITU-R P.840.
        pressure_hpa (float): Atmospheric pressure [hPa]. Standard 1013 at sea level.
        temp_c (float): Temperature [C]. Affects gas absorption, scintillation.
        rel_humidity_percent (float): Relative humidity [%]. Affects gas, fog.
        scenario_name (str): Descriptive label for logging.

    Example:
        >>> weather = WeatherScenario(
        ...     rain_mm_h=10.0,
        ...     visibility_km=2.0,
        ...     hour_of_day=19.5,
        ...     liquid_water_g_m3=0.15,
        ...     pressure_hpa=1013,
        ...     temp_c=25,
        ...     rel_humidity_percent=70,
        ...     scenario_name="heavy_rain_night"
        ... )
    """
    rain_mm_h: float
    visibility_km: float
    hour_of_day: float
    liquid_water_g_m3: float = 0.0
    pressure_hpa: float = 1013.0
    temp_c: float = 15.0
    rel_humidity_percent: float = 50.0
    scenario_name: str = "custom"


class WeatherScenarioGenerator:
    """Generate weather scenarios for training episodes.

    Modes:
      - "random_mix": Random sampling from all profiles (default for training)
      - "fixed": Return a single fixed scenario (for testing)
      - "deterministic": Cycle through predefined profiles

    Reproducibility: All sampling uses internal RNG seeded at initialization.
    """

    # Predefined profiles covering the weather space
    RAIN_PROFILES = [0.0, 2.0, 5.0, 10.0, 20.0]         # mm/h
    VISIBILITY_PROFILES = [15.0, 7.5, 2.5, 0.5]         # km
    DIURNAL_PROFILE = np.linspace(0, 24, 24, endpoint=False)  # hours

    # Composite scenarios (rain, visibility, hour, name)
    COMPOSITE_PROFILES = [
        (0.0, 15.0, 12.0, "clear_noon"),
        (0.0, 15.0, 6.0, "clear_dawn"),
        (0.0, 15.0, 18.0, "clear_dusk"),
        (2.0, 10.0, 9.0, "light_rain_morning"),
        (5.0, 7.5, 12.0, "moderate_rain_noon"),
        (10.0, 2.5, 18.0, "heavy_rain_evening"),
        (20.0, 0.5, 22.0, "severe_rain_night"),
        (5.0, 5.0, 0.0, "rain_midnight"),
    ]

    def __init__(self, mode="random_mix", seed=42, fixed_scenario=None):
        """Initialize generator.

        Args:
            mode (str): "random_mix", "fixed", or "deterministic"
            seed (int): RNG seed for reproducibility
            fixed_scenario (WeatherScenario): Used if mode="fixed"
        """
        self.mode = mode
        self.rng = np.random.default_rng(seed)
        self.fixed_scenario = fixed_scenario
        self.composite_index = 0  # For deterministic mode

        if mode == "fixed" and fixed_scenario is None:
            raise ValueError("mode='fixed' requires fixed_scenario argument")

    def sample(self) -> WeatherScenario:
        """Return a weather scenario.

        Sampling strategy depends on mode:
          - random_mix: Uniformly pick from all profiles and diurnal hours
          - fixed: Return the fixed scenario every time
          - deterministic: Cycle through composite profiles

        Returns:
            WeatherScenario with (rain_mm_h, visibility_km, hour_of_day, name)
        """
        if self.mode == "fixed":
            return self.fixed_scenario

        if self.mode == "deterministic":
            # Cycle through predefined composites
            rain, vis, hour, name = self.COMPOSITE_PROFILES[
                self.composite_index % len(self.COMPOSITE_PROFILES)
            ]
            self.composite_index += 1
            return WeatherScenario(
                rain_mm_h=rain,
                visibility_km=vis,
                hour_of_day=hour,
                scenario_name=name
            )

        # random_mix (default for training)
        # Sample independently from each dimension (allows composites)
        rain = float(self.rng.choice(self.RAIN_PROFILES))
        visibility = float(self.rng.choice(self.VISIBILITY_PROFILES))
        hour = float(self.rng.uniform(0, 24))

        # Derive atmospheric parameters from rain and visibility
        # Higher rain correlates with higher humidity and fog
        liquid_water_g_m3 = self._derive_liquid_water(rain, visibility)
        temp_c = self._derive_temperature(hour)
        pressure_hpa = self._derive_pressure(rain)
        rel_humidity_percent = self._derive_humidity(rain, visibility)

        # Generate descriptive name
        rain_label = {
            0.0: "clear", 2.0: "light", 5.0: "moderate", 10.0: "heavy", 20.0: "severe"
        }[rain]

        vis_label = {
            15.0: "excellent",
            7.5: "good",
            2.5: "poor",
            0.5: "very_poor"
        }[visibility]

        if hour < 6:
            time_label = "night"
        elif hour < 12:
            time_label = "morning"
        elif hour < 18:
            time_label = "afternoon"
        else:
            time_label = "evening"

        scenario_name = f"{rain_label}_{vis_label}_{time_label}"

        return WeatherScenario(
            rain_mm_h=rain,
            visibility_km=visibility,
            hour_of_day=hour,
            liquid_water_g_m3=liquid_water_g_m3,
            pressure_hpa=pressure_hpa,
            temp_c=temp_c,
            rel_humidity_percent=rel_humidity_percent,
            scenario_name=scenario_name
        )

    def _derive_liquid_water(self, rain_mm_h: float, visibility_km: float) -> float:
        """Derive fog liquid water content from rain rate and visibility.

        Physical correlation:
        - Heavy rain (>5 mm/h) often occurs with low-level fog/stratus
        - Low visibility (<2 km) indicates fog/cloud presence
        """
        if visibility_km < 1.0:
            # Dense fog: 0.3-0.5 g/m3
            lwc = 0.4
        elif visibility_km < 2.5:
            # Moderate fog: 0.1-0.3 g/m3
            lwc = 0.2
        elif rain_mm_h > 10.0:
            # Heavy rain with some cloud: 0.05-0.15 g/m3
            lwc = 0.1
        elif rain_mm_h > 5.0:
            # Moderate rain: 0.02-0.05 g/m3
            lwc = 0.03
        else:
            # Clear sky: negligible fog
            lwc = 0.0
        return float(lwc)

    def _derive_temperature(self, hour_of_day: float) -> float:
        """Derive temperature from diurnal cycle (simple cosine model)."""
        # Typical: 5°C at 6am (sunrise), 25°C at 2pm (noon), 10°C at 6pm (sunset)
        hour_rad = 2 * np.pi * (hour_of_day - 6) / 24.0
        temp = 15.0 + 10.0 * np.cos(hour_rad)  # 5-25°C range
        return float(np.clip(temp, 0.0, 40.0))

    def _derive_pressure(self, rain_mm_h: float) -> float:
        """Derive atmospheric pressure (rain systems lower pressure)."""
        # Typical: 1013 hPa clear, 1008 hPa moderate rain, 1000 hPa heavy rain
        if rain_mm_h > 10.0:
            pressure = 1000.0  # Low-pressure system
        elif rain_mm_h > 5.0:
            pressure = 1005.0  # Moderate rain
        elif rain_mm_h > 2.0:
            pressure = 1010.0  # Light rain
        else:
            pressure = 1013.0  # Clear
        return float(pressure)

    def _derive_humidity(self, rain_mm_h: float, visibility_km: float) -> float:
        """Derive relative humidity from rain and visibility."""
        # Rain and fog imply high humidity
        if rain_mm_h > 10.0 or visibility_km < 1.0:
            humidity = 90.0  # Very humid
        elif rain_mm_h > 5.0 or visibility_km < 2.5:
            humidity = 80.0  # Humid
        elif rain_mm_h > 2.0 or visibility_km < 5.0:
            humidity = 70.0  # Moderate humidity
        else:
            humidity = 50.0  # Dry
        return float(humidity)

    def get_coverage_stats(self, n_samples=1000) -> dict:
        """Compute distribution of scenarios over n_samples.

        Useful for verifying that training covers all weather profiles.

        Returns:
            Dictionary with counts/proportions per profile.
        """
        if self.mode == "fixed":
            return {"fixed": {self.fixed_scenario.scenario_name: 1.0}}

        rain_counts = {r: 0 for r in self.RAIN_PROFILES}
        vis_counts = {v: 0 for v in self.VISIBILITY_PROFILES}
        hour_bins = {f"{h}-{h+2}h": 0 for h in range(0, 24, 2)}

        scenarios = [self.sample() for _ in range(n_samples)]

        for scenario in scenarios:
            rain_counts[round(scenario.rain_mm_h, 1)] += 1
            vis_counts[round(scenario.visibility_km, 1)] += 1
            hour_bin = f"{int(scenario.hour_of_day // 2) * 2}-{int(scenario.hour_of_day // 2) * 2 + 2}h"
            if hour_bin in hour_bins:
                hour_bins[hour_bin] += 1

        # Normalize to proportions
        rain_props = {k: v / n_samples for k, v in rain_counts.items()}
        vis_props = {k: v / n_samples for k, v in vis_counts.items()}
        hour_props = {k: v / n_samples for k, v in hour_bins.items()}

        return {
            "rain_mm_h": rain_props,
            "visibility_km": vis_props,
            "hour_bins": hour_props,
        }


if __name__ == "__main__":
    # Smoke test
    print("Testing WeatherScenarioGenerator...")

    # Test random_mix mode
    gen_random = WeatherScenarioGenerator(mode="random_mix", seed=42)
    weather = gen_random.sample()
    print(f"Random scenario: {weather}")

    # Test deterministic mode
    gen_det = WeatherScenarioGenerator(mode="deterministic", seed=42)
    for i in range(3):
        w = gen_det.sample()
        print(f"Deterministic {i}: {w.scenario_name}")

    # Test fixed mode
    fixed = WeatherScenario(
        rain_mm_h=5.0,
        visibility_km=10.0,
        hour_of_day=12.0,
        scenario_name="test_noon"
    )
    gen_fixed = WeatherScenarioGenerator(mode="fixed", fixed_scenario=fixed)
    print(f"Fixed scenario: {gen_fixed.sample()}")

    # Coverage stats
    gen = WeatherScenarioGenerator(mode="random_mix", seed=123)
    stats = gen.get_coverage_stats(n_samples=400)
    print("\nWeather coverage over 400 samples:")
    print(f"  Rain: {stats['rain_mm_h']}")
    print(f"  Visibility: {stats['visibility_km']}")
    print(f"  Hours: {stats['hour_bins']}")

    print("\n[PASS] WeatherScenarioGenerator smoke test")
