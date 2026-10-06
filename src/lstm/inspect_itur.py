"""
List the public functions in the itur (ITU-Rpy) models used by the feeder-link analysis,
with their signatures. Used to decide which quantities the LSTM must forecast versus
which ones itur can compute directly.

Run in WSL (env ~/quantum_env): python src/lstm/inspect_itur.py
"""

import importlib
import inspect

MODULES = ["itu618", "itu676", "itu835", "itu836", "itu837", "itu838", "itu840"]


def main() -> None:
    for name in MODULES:
        mod = importlib.import_module(f"itur.models.{name}")
        print(f"== {name}")
        for fn_name, fn in inspect.getmembers(mod, inspect.isfunction):
            if fn.__module__ != mod.__name__ or fn_name.startswith("_"):
                continue
            print(f"  {fn_name}{inspect.signature(fn)}")


if __name__ == "__main__":
    main()
