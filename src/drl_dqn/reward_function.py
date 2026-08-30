"""
Phase 2: Reward Function with Critical Fixes

CRITICAL FIX #1: Jain's Index and Throughput Computation
=========================================================
All computations MUST use LINEAR SINR, never dB values.

WRONG (Silent Poisoning):
    sinr_db_array = [10, -5, 8, 12, -2]  # dB values
    jain = (sum(sinr_db_array))^2 / (N * sum(x^2 for x in sinr_db_array))
    # Result: Jain computed on arbitrary dB scale, meaningless numerically
    # Agent learns from poisoned reward signals → days of debugging

CORRECT (This Implementation):
    Convert to linear first: sinr_linear = [10^(x/10) for x in sinr_db]
    Jain = (sum(sinr_linear))^2 / (N * sum(sinr_linear^2))
    Throughput = sum(log2(1 + sinr_linear))

Verification:
    Jain(all_equal) = 1.0  ✓
    Jain(one_user_only) = 1/N  ✓
    Both hold under linear computation, not dB.
"""

import numpy as np


def convert_sinr_db_to_linear(sinr_db_array):
    """Convert SINR from dB to linear domain.

    Args:
        sinr_db_array: Array of SINR values in dB

    Returns:
        Array of SINR values in linear domain
    """
    return 10 ** (np.array(sinr_db_array) / 10.0)


def compute_aggregate_throughput(sinr_db_array):
    """Compute aggregate throughput using Shannon capacity formula.

    CRITICAL: Must use LINEAR SINR, not dB.
    L_agg = sum_k log2(1 + SINR_k_linear)  [bits/s/Hz]

    Args:
        sinr_db_array: Per-user SINR in dB

    Returns:
        Aggregate throughput in bits/s/Hz
    """
    sinr_linear = convert_sinr_db_to_linear(sinr_db_array)
    throughput = np.sum(np.log2(1.0 + sinr_linear))
    return throughput


def compute_jain_fairness_index(sinr_db_array):
    """Compute Jain's fairness index using LINEAR SINR.

    CRITICAL: Must use LINEAR SINR, not dB.
    Jain = (sum SINR_linear)^2 / (N * sum SINR_linear^2)

    Args:
        sinr_db_array: Per-user SINR in dB

    Returns:
        Jain's fairness index in range [0, 1]
        - 1.0: perfect fairness (all users equal)
        - 1/N: worst fairness (one user only)
    """
    sinr_linear = convert_sinr_db_to_linear(sinr_db_array)
    n_users = len(sinr_linear)

    jain_numerator = np.sum(sinr_linear) ** 2
    jain_denominator = n_users * np.sum(sinr_linear ** 2)

    if jain_denominator == 0:
        return 0.5  # Fallback for edge case

    jain = jain_numerator / jain_denominator
    return np.clip(jain, 0.0, 1.0)


def compute_network_reward(sinr_db_array, battery_soc, outage_threshold_db=5.0,
                          omega_1=0.5, omega_2=0.3, omega_3=0.2):
    """Compute multi-objective network reward.

    R(assignments) = ω₁·L_agg + ω₂·Jain - ω₃·P_energy + Penalties

    Args:
        sinr_db_array: Per-user SINR in dB
        battery_soc: Array of HAPS battery state-of-charge (%)
        outage_threshold_db: SINR threshold for outage (default 5 dB)
        omega_1: Throughput weight (default 0.5)
        omega_2: Fairness weight (default 0.3)
        omega_3: Energy weight (default 0.2)

    Returns:
        Scalar reward value and dict of component metrics
    """
    # Component 1: Aggregate Throughput (bits/s/Hz)
    throughput = compute_aggregate_throughput(sinr_db_array)

    # Component 2: Fairness (Jain's index)
    jain = compute_jain_fairness_index(sinr_db_array)

    # Component 3: Energy (battery state)
    battery_soc_array = np.array(battery_soc)
    energy_penalty = 1.0 - np.mean(battery_soc_array) / 100.0

    # Penalties
    n_outage = np.sum(np.array(sinr_db_array) < outage_threshold_db)
    outage_penalty = -100.0 * n_outage  # -100 per outage

    n_low_battery = np.sum(battery_soc_array < 10.0)
    low_battery_penalty = -50.0 * n_low_battery  # -50 per low-battery HAPS

    # Aggregate reward
    reward = (
        omega_1 * throughput +
        omega_2 * jain -
        omega_3 * energy_penalty +
        outage_penalty +
        low_battery_penalty
    )

    metrics = {
        "throughput_bps_hz": throughput,
        "jain_index": jain,
        "energy_penalty": energy_penalty,
        "n_outage": n_outage,
        "outage_penalty": outage_penalty,
        "n_low_battery": n_low_battery,
        "low_battery_penalty": low_battery_penalty,
        "reward": reward
    }

    return reward, metrics


# ===== Unit Tests (Verification) =====

def test_jain_perfect_equality():
    """Test: Jain(all equal) = 1.0"""
    sinr_db = [5.0, 5.0, 5.0, 5.0, 5.0]
    jain = compute_jain_fairness_index(sinr_db)
    assert np.isclose(jain, 1.0), f"Expected 1.0, got {jain}"
    print("[PASS] test_jain_perfect_equality")


def test_jain_one_user_only():
    """Test: Jain(one user) = 1/N"""
    sinr_db = [10.0, -100.0, -100.0, -100.0, -100.0]  # Only user 0 active
    jain = compute_jain_fairness_index(sinr_db)
    expected = 1.0 / 5.0
    assert np.isclose(jain, expected, atol=0.01), f"Expected {expected}, got {jain}"
    print("[PASS] test_jain_one_user_only")


def test_throughput_linear_conversion():
    """Test: Throughput computed correctly in linear domain"""
    sinr_db = [10.0, 5.0, 0.0]  # Three users
    throughput = compute_aggregate_throughput(sinr_db)

    # Manual verification:
    # sinr_linear = [10, 3.16, 1.0]
    # throughput = log2(1+10) + log2(1+3.16) + log2(1+1.0)
    #            = log2(11) + log2(4.16) + log2(2)
    #            ≈ 3.46 + 2.06 + 1.0 = 6.52
    expected = 3.46 + 2.06 + 1.0
    assert np.isclose(throughput, expected, atol=0.1), f"Expected ~{expected}, got {throughput}"
    print("[PASS] test_throughput_linear_conversion")


if __name__ == "__main__":
    print("Running verification tests for Reward Function (FIX #1)...\n")
    test_jain_perfect_equality()
    test_jain_one_user_only()
    test_throughput_linear_conversion()
    print("\n[PASS] All tests passed! Jain's index & throughput correctly computed on LINEAR SINR.\n")

    # Example usage
    print("Example: Computing reward for 3-user scenario")
    sinr_example = [10.0, -2.0, 8.0]  # User 1 in outage
    battery_example = [85.0, 90.0, 50.0]
    reward, metrics = compute_network_reward(sinr_example, battery_example)

    print(f"  SINR (dB): {sinr_example}")
    print(f"  Battery SoC (%): {battery_example}")
    print(f"  Throughput: {metrics['throughput_bps_hz']:.2f} bits/s/Hz")
    print(f"  Jain Index: {metrics['jain_index']:.3f}")
    print(f"  Outage Count: {metrics['n_outage']} (penalty: {metrics['outage_penalty']})")
    print(f"  Final Reward: {reward:.2f}")
