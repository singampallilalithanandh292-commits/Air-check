"""
Find CPCB station IDs for Visakhapatnam
Run this once to discover the station_id values you'll need for pulling historical data.
"""

import cpcbccr as cpcb

print("Fetching Visakhapatnam stations...\n")
try:
    stations = cpcb.get_stations(city='Visakhapatnam')
    print(stations)
except Exception as e:
    print("Error fetching stations:", e)
    print("\nTrying alternate spelling 'visakhapatnam' (lowercase)...")
    try:
        stations = cpcb.get_stations(city='visakhapatnam')
        print(stations)
    except Exception as e2:
        print("Still failed:", e2)

