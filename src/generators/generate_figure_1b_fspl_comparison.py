#!/usr/bin/env python3
"""
Generate Figure 1b: HAPS Free-Space Path Loss Comparison

Matches generate_pathloss_table.py's convention:
1. Service link: HAPS (20 km) -> UE (1.5 m), 2 GHz, swept 0-100 km horizontal
2. Relay link, 1st hop: HAPS (20 km) -> UAV (500 m AGL), 38 GHz -- a fixed,
   near-vertical hop (~19.5 km slant range); the UAV sits essentially below
   the HAPS, so this leg does not sweep with ground distance
3. Relay link, 2nd hop: UAV (500 m AGL) -> UE (1.5 m), 2 GHz, swept 0-100 km
   horizontal as the UAV relays outward toward the UE

The combined relay path (dB sum of hops 1 and 2) is intentionally NOT plotted.
FSPL is a per-hop quantity: the two relay hops are independent RF links with
their own transmit power, noise floor, and a decode/re-encode step at the
UAV, not losses that stack in series within one continuous chain. Summing
their dB values would misrepresent a two-hop decode-and-forward relay, whose
achievable end-to-end throughput is bottlenecked by the weaker hop (`min` of
per-hop capacities, not a sum of losses) -- see
`relay_two_hop_capacity_bps_hz()` in `generate_relay_table.py` for the
correct treatment.

All distances use the true 3D slant distance (horizontal distance plus the
altitude difference between the two endpoints), per Equation (1):

    L_FSPL = 32.44 + 20*log10(f_MHz) + 20*log10(d_3D_km) [dB]
"""

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'output'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Equation (1): Free-Space Path Loss
# ============================================================================


def fspl_db(f_mhz, d_km):
    """Calculate free-space path loss in dB given a 3D distance."""
    return 32.44 + 20 * np.log10(f_mhz) + 20 * np.log10(d_km)


def slant_dist_km(r_horiz_km, h_tx_m, h_rx_m):
    """3D slant distance [km] between a horizontal ground offset and two endpoint altitudes [m]."""
    dh_km = (h_tx_m - h_rx_m) / 1000.0
    return np.sqrt(r_horiz_km ** 2 + dh_km ** 2)


# ============================================================================
# Parameters and calculations
# ============================================================================

r_horiz_km = np.linspace(0, 100, 500)
f_2ghz = 2000
f_38ghz = 38000

HAPS_ALT_M = 20_000.0
UAV_ALT_M = 500.0
UE_ALT_M = 1.5

d_service_km = slant_dist_km(r_horiz_km, HAPS_ALT_M, UE_ALT_M)  # HAPS -> UE

# HAPS -> UAV is a fixed, near-vertical hop: the UAV sits essentially below
# the HAPS (horizontal offset ~0), so this leg does not sweep with distance --
# it is a constant ~19.5 km slant range (20 km - 0.5 km altitude difference).
d_relay1_km = slant_dist_km(0.0, HAPS_ALT_M, UAV_ALT_M)

# UAV -> UE is the leg that reaches outward as the UAV relays toward the UE.
d_relay2_km = slant_dist_km(r_horiz_km, UAV_ALT_M, UE_ALT_M)  # UAV -> UE

fspl_2ghz = fspl_db(f_2ghz, d_service_km)  # HAPS -> UE (2 GHz, service link)
fspl_38ghz = np.full_like(r_horiz_km, fspl_db(f_38ghz, d_relay1_km))  # HAPS -> UAV (38 GHz, relay link, 1st hop, fixed)
fspl_uav_ue = fspl_db(f_2ghz, d_relay2_km)  # UAV -> UE (2 GHz, relay link, 2nd hop)

# Indicative-only reference: 38 GHz FSPL if it were swept over the full 0-100 km
# range using the *service-link* geometry (HAPS -> ground point). The 38 GHz
# hop never actually extends past the UAV (~19.5 km) -- this line exists only
# to visualize the constant frequency-scaling offset vs. the 2 GHz service link.
fspl_38ghz_ref = fspl_db(f_38ghz, d_service_km)

fspl_diff = fspl_38ghz_ref - fspl_2ghz
fspl_diff_at_100km = fspl_diff[-1]

print(f"Fixed HAPS->UAV (38 GHz) slant distance: {d_relay1_km:.2f} km, path loss: {fspl_38ghz[0]:.2f} dB")
print(f"FSPL offset at 100 km (38 GHz indicative reference - 2 GHz Service, same geometry): {fspl_diff_at_100km:.2f} dB")
print(f"Theoretical frequency-only offset: 20*log10(38/2) = {20 * np.log10(38 / 2):.2f} dB")

# ============================================================================
# Generate Figure 1b
# ============================================================================

fig, ax = plt.subplots(figsize=(10, 6))

ax.plot(r_horiz_km, fspl_2ghz, linewidth=2.5, label='2 GHz (Service Link, HAPS-UE)', color='#2E86AB', linestyle='-')
ax.plot(r_horiz_km, fspl_38ghz, linewidth=2.5, label=f'38 GHz (Relay Link, HAPS-UAV, 1st hop, fixed {d_relay1_km:.1f} km)', color='#A23B72', linestyle='--')
ax.plot(r_horiz_km, fspl_uav_ue, linewidth=2.5, label='2 GHz (Relay Link, UAV-UE, 2nd hop)', color='#3B9C4A', linestyle='--')
ax.plot(r_horiz_km, fspl_38ghz_ref, linewidth=1.5, label='38 GHz (indicative full-range reference, same geometry as Service Link)', color='#888888', linestyle='--', alpha=0.7)

ax.set_xlabel('Horizontal Ground Distance (UAV to UE) [km]', fontsize=12, fontweight='bold')
ax.set_ylabel('Free-Space Path Loss [dB]', fontsize=12, fontweight='bold')
ax.set_title('HAPS/UAV Free-Space Path Loss: Frequency Comparison (Eq. 1)', fontsize=13, fontweight='bold')
ax.grid(True, alpha=0.3, linestyle='--')
ax.legend(fontsize=10, loc='upper left', framealpha=0.95)

mid_point = 50
offset_y_2 = fspl_db(f_2ghz, slant_dist_km(mid_point, HAPS_ALT_M, UE_ALT_M))
offset_y_38ref = fspl_db(f_38ghz, slant_dist_km(mid_point, HAPS_ALT_M, UE_ALT_M))
ax.annotate('', xy=(mid_point, offset_y_38ref), xytext=(mid_point, offset_y_2),
            arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
ax.text(mid_point + 5, (offset_y_2 + offset_y_38ref) / 2,
        f'{offset_y_38ref - offset_y_2:.2f} dB (at {mid_point} km)', fontsize=10, fontweight='bold', va='center')

feeder_distance_km = 0.5
ax.axvline(x=feeder_distance_km, color='red', linestyle='--', linewidth=2, alpha=0.6,
           label=f'Feeder link range (0-{feeder_distance_km} km, separate short backhaul hop, not plotted)')
ax.text(feeder_distance_km, 175, f'  Feeder link range (0-{feeder_distance_km} km)',
        fontsize=9, color='red', weight='bold', va='top')

'''
note = ('Note: the two relay hops (HAPS-UAV, UAV-UE) are not summed here.\n'
        'FSPL is per-hop; the hops are independent RF links (separate Tx power,\n'
        'noise floor, decode/re-encode at the UAV), not series losses in one chain.\n'
        'Summing their dB values misrepresents relay performance -- a two-hop\n'
        'decode-and-forward relay is bottlenecked by the weaker hop (min of\n'
        'per-hop capacities), not a sum of path losses.')
ax.text(0.02, 0.02, note, transform=ax.transAxes, fontsize=8, style='italic',
        color='#444444', va='bottom', ha='left',
        bbox=dict(boxstyle='round', facecolor='white', edgecolor='#cccccc', alpha=0.85))
'''

ax.set_ylim([60, 300])
ax.set_xlim([0, 100])
plt.tight_layout()
output_path = OUTPUT_DIR / '1b_haps_fspl_2ghz_vs_38ghz.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f'[OK] Figure saved: {output_path}')
plt.close(fig)

# ============================================================================
# Summary
# ============================================================================

print('=' * 70)
print('Figure 1b Summary')
print('=' * 70)
print('HAPS Altitude: 20 km, UAV Altitude: 500 m AGL, UE Altitude: 1.5 m')
print('Horizontal Ground Distance Range: 0-100 km, measured UAV to UE (3D slant distance used in FSPL)')
print('Curve 1 (Service Link, HAPS->UE): 2 GHz, sweeps 0-100 km')
print(f'Curve 2 (Relay Link, HAPS->UAV, 1st hop): 38 GHz, fixed at {d_relay1_km:.2f} km (near-vertical, UAV below HAPS)')
print('Curve 3 (Relay Link, UAV->UE, 2nd hop): 2 GHz, sweeps 0-100 km')
print('Curve 4 (38 GHz indicative full-range reference): same geometry as Service Link, for offset visualization only')
print('Combined relay path (dB sum of hop 1 + hop 2) intentionally not plotted --')
print('  summing per-hop FSPL misrepresents a decode-and-forward relay, which is')
print('  bottlenecked by the weaker hop, not the sum of both hops\' losses.')
print(f'FSPL, Curve 1 (Service, HAPS->UE) at 0 km:        {fspl_2ghz[0]:.2f} dB')
print(f'FSPL, Curve 2 (Relay, HAPS->UAV), fixed:          {fspl_38ghz[0]:.2f} dB')
print(f'FSPL, Curve 3 (Relay, UAV->UE) at 0 km:           {fspl_uav_ue[0]:.2f} dB')
print(f'FSPL, Curve 4 (38 GHz indicative ref) at 0 km:    {fspl_38ghz_ref[0]:.2f} dB')
print(f'FSPL, Curve 1 (Service, HAPS->UE) at 100 km:      {fspl_2ghz[-1]:.2f} dB')
print(f'FSPL, Curve 3 (Relay, UAV->UE) at 100 km:         {fspl_uav_ue[-1]:.2f} dB')
print(f'FSPL, Curve 4 (38 GHz indicative ref) at 100 km:  {fspl_38ghz_ref[-1]:.2f} dB')
print('=' * 70)
