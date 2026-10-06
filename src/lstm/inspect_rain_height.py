"""
Check the ITU-R P.839 rain-height function in itur and its value for the Delhi site.
The P.618 slant path through rain runs from the ground up to the rain height, not up to
the HAPS altitude, so the rain height is needed for the effective path length.

Run in WSL (env ~/quantum_env): python src/lstm/inspect_rain_height.py
"""

import inspect

from itur.models import itu839

SITE_LAT, SITE_LON = 28.61, 77.21


def main() -> None:
    print("P.839 functions:")
    for name, fn in inspect.getmembers(itu839, inspect.isfunction):
        if fn.__module__ == itu839.__name__ and not name.startswith("_"):
            print(f"  {name}{inspect.signature(fn)}")
    h_r = itu839.rain_height(SITE_LAT, SITE_LON)
    print(f"Rain height at Delhi: {float(h_r.value if hasattr(h_r, 'value') else h_r):.3f} km")


if __name__ == "__main__":
    main()
