"""
Count missing values per column in the base hourly table (NASA POWER + METAR).

Run in WSL (env ~/quantum_env): python src/lstm/check_base_nans.py
"""

import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
BASE_CSV = os.path.join(ROOT, "data", "processed", "delhi_hourly_TEMP.csv")


def main() -> None:
    df = pd.read_csv(BASE_CSV)
    print(df.isna().sum())


if __name__ == "__main__":
    main()
