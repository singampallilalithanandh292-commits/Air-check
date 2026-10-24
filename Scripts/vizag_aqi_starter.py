"""
Visakhapatnam Air Quality & Public Health Project — Starter Script
Motto: "Where you live shouldn't decide how long you live."

SETUP (do this first):
1. Get a free token: https://aqicn.org/data-platform/token  (just needs an email, instant)
2. Paste your token into TOKEN below
3. Install dependencies: pip install requests pandas
4. Run: python vizag_aqi_starter.py

NOTE: We use a geo-coordinate lookup (lat/lon) instead of name search,
because the WAQI /search/ endpoint was unreliable for this token —
geo lookup is confirmed working and finds the nearest real station
(GVM Corporation, Visakhapatnam — CPCB station, idx 12443).
"""

import os
import requests
import pandas as pd
from datetime import datetime

# ---- STEP 1: Your free API token ----
TOKEN = "1ae310f1dcfd6a7c3d970267d67638e8a51af571"

# Save log file into data/raw/ next to the project root, regardless of
# what folder you run this script from
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # assumes script lives in /scripts
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
os.makedirs(DATA_DIR, exist_ok=True)
LOG_FILE = os.path.join(DATA_DIR, "vizag_aqi_log.csv")

# Visakhapatnam coordinates — confirmed working via geo lookup
VIZAG_LAT = 17.6868
VIZAG_LON = 83.2185

# Known Vizag-area stations. Geo lookup finds the NEAREST station to each
# coordinate pair, so pointing it at each station's specific location
# pulls that station's own readings.
VIZAG_STATIONS = {
    "GVM Corporation": (17.6868, 83.2185),
    "Ram Nagar-APPCB": (17.7305, 83.3074),  # Tenneti Bhavan / GVMC building area
}


def get_current_aqi(lat=VIZAG_LAT, lon=VIZAG_LON, token=TOKEN):
    """Fetch the current live AQI reading for the nearest station to given coordinates."""
    url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"
    response = requests.get(url, timeout=10)
    data = response.json()
    if data["status"] != "ok":
        print("Error fetching data:", data.get("data"))
        return None
    return data["data"]


def get_nearby_stations(lat1=15.5, lon1=78.5, lat2=19.5, lon2=85.5, token=TOKEN):
    """
    Fetch ALL monitoring stations within a bounding box.
    Default box covers most of coastal Andhra Pradesh — Vizag, Vijayawada,
    Rajahmundry, Srikakulam, Kakinada, etc.
    Box format: (lat1, lon1) = bottom-left corner, (lat2, lon2) = top-right corner.
    """
    url = f"https://api.waqi.info/map/bounds/?latlng={lat1},{lon1},{lat2},{lon2}&token={token}"
    response = requests.get(url, timeout=10)
    data = response.json()
    if data["status"] != "ok":
        print("Error fetching nearby stations:", data.get("data"))
        return []
    return data["data"]


def log_snapshot(aqi_data, log_file=LOG_FILE):
    """Append today's reading to a running CSV log (run this daily/periodically to build your own time series)."""
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "station": aqi_data.get("_station_label", aqi_data["city"]["name"]),
        "aqi": aqi_data["aqi"],
        "dominant_pollutant": aqi_data.get("dominentpol"),
    }
    for pollutant, values in aqi_data.get("iaqi", {}).items():
        snapshot[pollutant] = values["v"]

    df = pd.DataFrame([snapshot])
    file_exists = os.path.isfile(log_file)
    df.to_csv(log_file, mode="a", header=not file_exists, index=False)
    print(f"Snapshot appended to {log_file}")


def clean_historical_data(filepath):
    """
    Use this once you've downloaded a historical CSV from the CPCB portal
    or AQICN data platform. Handles common CPCB data quality issues.
    """
    df = pd.read_csv(filepath)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    date_cols = [c for c in df.columns if "date" in c or "time" in c]
    if date_cols:
        df[date_cols[0]] = pd.to_datetime(df[date_cols[0]], errors="coerce")

    # CPCB convention: 0, negative, and 999 readings usually indicate sensor error
    numeric_cols = df.select_dtypes(include="number").columns
    for col in numeric_cols:
        df.loc[(df[col] <= 0) | (df[col] >= 999), col] = pd.NA

    df = df.dropna(subset=list(numeric_cols), how="all")
    return df


if __name__ == "__main__":
    print("Fetching current Visakhapatnam stations...\n")

    for station_label, (lat, lon) in VIZAG_STATIONS.items():
        print("-" * 50)
        aqi_data = get_current_aqi(lat=lat, lon=lon)

        if aqi_data:
            actual_name = aqi_data["city"]["name"]
            print(f"Target: {station_label}  (resolved to: {actual_name})")
            print(f"Current AQI: {aqi_data['aqi']}")
            print(f"Dominant pollutant: {aqi_data.get('dominentpol', 'N/A')}")
            print(f"Coordinates: {aqi_data['city']['geo']}")
            print(f"Reading time: {aqi_data['time']['s']} ({aqi_data['time']['tz']})")
            print("Pollutant readings:")
            for pollutant, values in aqi_data.get("iaqi", {}).items():
                print(f"  {pollutant.upper()}: {values['v']}")

            # Tag which station this snapshot belongs to before logging
            aqi_data["_station_label"] = station_label
            log_snapshot(aqi_data)
        else:
            print(f"Could not fetch data for {station_label}.")
        print()

    # ---- Nearby cities comparison ----
    print("\n" + "=" * 50)
    print("Fetching nearby Andhra Pradesh stations...\n")
    nearby = get_nearby_stations()

    if nearby:
        # Sort worst to best AQI
        nearby_sorted = sorted(
            [s for s in nearby if str(s.get("aqi", "-")).isdigit()],
            key=lambda s: int(s["aqi"]),
            reverse=True,
        )
        print(f"Found {len(nearby_sorted)} stations with valid readings:\n")
        for s in nearby_sorted:
            print(f"  AQI {s['aqi']:>4}  —  {s['station']['name']}")
    else:
        print("Could not fetch nearby stations.")
