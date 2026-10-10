"""
Download 2026 raw data for the Delhi site, up to the latest available day:
  - NASA POWER hourly (T2M, RH2M, PS, WS10M, PRECTOTCORR, CLOUD_AMT) -> data/raw/nasa_power/
  - VIDP METAR (Iowa Mesonet) -> data/raw/metar_vidp/vidp_2026.csv
  - ERA5 tclw for 2026 is downloaded separately by download_era5_tclw_2026.py (CDS account)

Run in WSL (env ~/quantum_env): python src/lstm/download_2026_raw.py
"""

import os
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
POWER_DIR = os.path.join(ROOT, "data", "raw", "nasa_power")
METAR_DIR = os.path.join(ROOT, "data", "raw", "metar_vidp")
START = "20260101"
END = "20261005"  # latest day with reanalysis; adjust if NASA POWER has a shorter lag


def fetch(url: str, path: str) -> None:
    with urllib.request.urlopen(url, timeout=300) as resp, open(path, "wb") as f:
        f.write(resp.read())
    print(f"saved {path} ({os.path.getsize(path)} bytes)")


def main() -> None:
    os.makedirs(POWER_DIR, exist_ok=True)
    os.makedirs(METAR_DIR, exist_ok=True)
    power_url = (
        "https://power.larc.nasa.gov/api/temporal/hourly/point?parameters="
        "T2M,RH2M,PS,WS10M,PRECTOTCORR,CLOUD_AMT&community=RE&longitude=77.21&latitude=28.61"
        f"&start={START}&end={END}&format=CSV&time-standard=UTC"
    )
    fetch(power_url, os.path.join(POWER_DIR, "power_hourly_delhi_2026.csv"))
    metar_url = (
        "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=VIDP&data=all"
        "&year1=2026&month1=1&day1=1&year2=2026&month2=10&day2=6&tz=Etc/UTC&format=onlycomma"
        "&latlon=no&elev=no&missing=null&trace=null&direct=no&report_type=3"
    )
    fetch(metar_url, os.path.join(METAR_DIR, "vidp_2026.csv"))


if __name__ == "__main__":
    main()
