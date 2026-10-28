#!/usr/bin/env python3
"""
Single-UAV coverage-radius study, and a covering-number estimate for the
service area -- supporting evidence for the paper's future-work conclusion
that a single static UAV (Table 1: count=1) leaves most of the 100 km
service area without usable relay capacity, and that more study is needed
on deploying several UAVs.

Deliberately evaluates only ONE UAV at a time (never several simultaneously):
placing multiple UAVs together would require modeling cross-UAV / UAV-UAV
interference, which this paper does not do, so a joint multi-UAV simulation
here would overstate what's actually been validated. Instead:

  1. Sweep one UAV's distance from the user it serves (0-30 km) and find
     R_eff, the distance at which relay capacity crosses a usable floor
     (0.5 bits/s/Hz) -- i.e. a single UAV's effective coverage radius.
  2. Use R_eff as a non-overlapping tile size and compute, by simple
     geometry (not simulation), how many such UAVs would be needed to
     tile the full service-area disk: rings spaced 2*R_eff apart out to
     the service radius, each ring's circumference divided by 2*R_eff for
     the UAVs needed around that ring.

This is an idealized covering-number estimate (no interference, no
mobility, no selection policy) -- a sizing argument for *how much* future
work is implied, not a deployable design.

Run: python src/generators/generate_uav_placement_study.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
from models.channel_model import haps_constellation_geometry, uav_relay_two_hop_capacity_bps_hz

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT_DIR = os.path.join(ROOT, 'data', 'processed', 'uav_placement')
os.makedirs(OUT_DIR, exist_ok=True)

ENV = "urban"
USABLE_BPS_HZ = 0.5
SERVICE_RADIUS_KM = 100.0

# Single, fixed HAPS->UAV feeder distance (circumradius of the 65 km-spacing
# equilateral triangle, same convention as haps_association_env.py / the main
# model) -- not the bottleneck here; the access hop collapses well before it.
nodes = haps_constellation_geometry(spacing_km=65.0)
haps_xy = np.array([[nodes[k][0], nodes[k][1]] for k in ('serving', 'interferer1', 'interferer2')])
R_HAPS_UAV_KM = float(np.linalg.norm(haps_xy[0] - haps_xy.mean(axis=0))) / 1000.0

# ---- Step 1: single-UAV radial sweep ----
dists_km = np.arange(0.0, 30.01, 0.25)
caps = np.array([
    float(np.asarray(uav_relay_two_hop_capacity_bps_hz(
        r_horiz_m=R_HAPS_UAV_KM * 1000.0, uav_ue_horiz_m=d_km * 1000.0, env=ENV
    )["capacity_uav_relay_bps_hz"]).flat[0])
    for d_km in dists_km
])

below = np.where(caps < USABLE_BPS_HZ)[0]
i = below[0]
d0, d1, c0, c1 = dists_km[i - 1], dists_km[i], caps[i - 1], caps[i]
R_EFF_KM = d0 + (USABLE_BPS_HZ - c0) * (d1 - d0) / (c1 - c0)

sweep_df = pd.DataFrame({"distance_km": dists_km, "capacity_uav_relay_bps_hz": caps})
sweep_df.to_csv(os.path.join(OUT_DIR, "single_uav_radial_sweep.csv"), index=False, float_format="%.4f")

print(f"Single-UAV radial sweep (feeder fixed @ {R_HAPS_UAV_KM:.1f} km from nearest HAPS):")
for d in (0, 2, 4, 6, 8, 10, 12, 15, 20):
    idx = int(np.argmin(np.abs(dists_km - d)))
    print(f"  distance {d:>3} km -> capacity {caps[idx]:.3f} bits/s/Hz")
print(f"\nR_eff (capacity crosses {USABLE_BPS_HZ} bits/s/Hz): {R_EFF_KM:.2f} km")

# ---- Step 2: covering-number calculation (geometry, not simulation) ----
spacing_km = 2 * R_EFF_KM  # neighboring non-overlapping coverage disks just touch
ring_radii = np.arange(R_EFF_KM, SERVICE_RADIUS_KM + 1e-9, spacing_km)

rows = []
total = 0
for r in ring_radii:
    circumference_km = 2 * np.pi * r
    n = max(1, int(np.ceil(circumference_km / spacing_km)))
    total += n
    rows.append({"ring_radius_km": round(r, 1), "circumference_km": round(circumference_km, 1),
                 "uavs_this_ring": n})

cover_df = pd.DataFrame(rows)
cover_df.to_csv(os.path.join(OUT_DIR, "covering_estimate.csv"), index=False)

print(f"\nCovering-number estimate, {SERVICE_RADIUS_KM:.0f} km-radius service area, "
      f"non-overlapping {R_EFF_KM:.1f} km-radius UAV coverage disks "
      f"(ring spacing {spacing_km:.1f} km):")
print(cover_df.to_string(index=False))
print(f"\nUAVs needed along a single radius (rings): {len(ring_radii)}")
print(f"Total UAVs needed to tile the full service area: {total}")
print("\nThis is an idealized sizing estimate: no cross-UAV interference, mobility, or")
print("selection policy modeled -- it bounds how much future work 'multiple UAVs' implies,")
print("not a deployable design.")
