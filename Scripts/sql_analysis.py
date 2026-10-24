"""
Visakhapatnam Air Quality Project
Phase 3: SQL Analysis
Motto: "Where you live shouldn't decide how long you live."

This script:
1. Loads your clean CSV into a local SQLite database
2. Runs key analytical SQL queries
3. Saves query results as CSVs for Tableau import
4. Saves all SQL queries to a .sql file for your portfolio

Run: python scripts/sql_analysis.py
"""

import os
import sqlite3
import pandas as pd

# ── Paths ──
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CLEAN_DIR    = os.path.join(PROJECT_ROOT, "data", "clean")
SQL_DIR      = os.path.join(PROJECT_ROOT, "sql")
os.makedirs(SQL_DIR, exist_ok=True)

CLEAN_CSV = os.path.join(CLEAN_DIR, "ap_air_quality_clean.csv")
DB_PATH   = os.path.join(SQL_DIR, "air_quality.db")
SQL_FILE  = os.path.join(SQL_DIR, "queries.sql")

# ─────────────────────────────────────────────
# STEP 1: LOAD CLEAN CSV INTO SQLITE
# ─────────────────────────────────────────────
def build_database():
    print("[DB] Loading clean CSV into SQLite...")
    df = pd.read_csv(CLEAN_CSV)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Year']  = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    df['MonthName'] = df['Date'].dt.strftime('%b')

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("air_quality", conn, if_exists="replace", index=False)
    print(f"[DB] Saved to {DB_PATH}")
    print(f"[DB] Rows: {len(df)} | Columns: {list(df.columns)}")
    conn.close()
    return df


# ─────────────────────────────────────────────
# STEP 2: RUN QUERIES AND SAVE RESULTS
# ─────────────────────────────────────────────
QUERIES = {

    "01_avg_pollutants_by_city": """
        -- Average pollutant levels per city (overall)
        SELECT
            City,
            ROUND(AVG("PM2.5"), 2)  AS avg_pm25,
            ROUND(AVG(PM10),   2)   AS avg_pm10,
            ROUND(AVG(NO2),    2)   AS avg_no2,
            ROUND(AVG(SO2),    2)   AS avg_so2,
            ROUND(AVG(CO),     2)   AS avg_co,
            ROUND(AVG(O3),     2)   AS avg_o3,
            ROUND(AVG(AQI),    2)   AS avg_aqi,
            COUNT(*)                AS total_days
        FROM air_quality
        GROUP BY City
        ORDER BY avg_pm25 DESC
    """,

    "02_yearly_trend_by_city": """
        -- Year-over-year PM2.5 trend per city
        SELECT
            City,
            Year,
            ROUND(AVG("PM2.5"), 2) AS avg_pm25,
            ROUND(AVG(AQI),    2)  AS avg_aqi,
            COUNT(*)               AS days_recorded
        FROM air_quality
        GROUP BY City, Year
        ORDER BY City, Year
    """,

    "03_monthly_seasonal_pattern": """
        -- Seasonal pattern — avg PM2.5 by month across all AP stations
        SELECT
            Month,
            MonthName,
            ROUND(AVG("PM2.5"), 2) AS avg_pm25,
            ROUND(MAX("PM2.5"), 2) AS max_pm25,
            ROUND(MIN("PM2.5"), 2) AS min_pm25,
            COUNT(*)               AS days_recorded
        FROM air_quality
        GROUP BY Month, MonthName
        ORDER BY Month
    """,

    "04_worst_days_vizag": """
        -- Top 20 worst air quality days in Visakhapatnam
        SELECT
            Date,
            City,
            "PM2.5",
            PM10,
            NO2,
            SO2,
            AQI,
            AQI_Bucket
        FROM air_quality
        WHERE City = 'Visakhapatnam'
          AND AQI IS NOT NULL
        ORDER BY AQI DESC
        LIMIT 20
    """,

    "05_aqi_category_breakdown": """
        -- How many days in each AQI category per city
        SELECT
            City,
            AQI_Bucket,
            COUNT(*) AS days,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY City), 1) AS pct
        FROM air_quality
        WHERE AQI_Bucket IS NOT NULL
        GROUP BY City, AQI_Bucket
        ORDER BY City,
            CASE AQI_Bucket
                WHEN 'Good'         THEN 1
                WHEN 'Satisfactory' THEN 2
                WHEN 'Moderate'     THEN 3
                WHEN 'Poor'         THEN 4
                WHEN 'Very Poor'    THEN 5
                WHEN 'Severe'       THEN 6
            END
    """,

    "06_winter_vs_summer": """
        -- Winter (Nov-Feb) vs Summer (Mar-Jun) PM2.5 comparison
        SELECT
            City,
            CASE
                WHEN Month IN (11,12,1,2) THEN 'Winter (Nov-Feb)'
                WHEN Month IN (3,4,5,6)   THEN 'Summer (Mar-Jun)'
                WHEN Month IN (7,8,9,10)  THEN 'Monsoon (Jul-Oct)'
            END AS Season,
            ROUND(AVG("PM2.5"), 2) AS avg_pm25,
            ROUND(AVG(AQI),    2)  AS avg_aqi,
            COUNT(*)               AS days
        FROM air_quality
        GROUP BY City, Season
        ORDER BY City, avg_pm25 DESC
    """,

    "07_pollutant_exceedance_days": """
        -- Days exceeding India NAQI thresholds for PM2.5 (>60 = Poor)
        SELECT
            City,
            Year,
            COUNT(*) AS total_days,
            SUM(CASE WHEN "PM2.5" > 60  THEN 1 ELSE 0 END) AS days_poor_or_worse,
            SUM(CASE WHEN "PM2.5" > 120 THEN 1 ELSE 0 END) AS days_very_poor_or_worse,
            ROUND(SUM(CASE WHEN "PM2.5" > 60 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_poor
        FROM air_quality
        WHERE "PM2.5" IS NOT NULL
        GROUP BY City, Year
        ORDER BY City, Year
    """,

    "08_vizag_monthly_pm25_by_year": """
        -- Vizag monthly PM2.5 breakdown by year (for multi-year seasonal chart in Tableau)
        SELECT
            Year,
            Month,
            MonthName,
            ROUND(AVG("PM2.5"), 2) AS avg_pm25,
            COUNT(*)               AS days
        FROM air_quality
        WHERE City = 'Visakhapatnam'
        GROUP BY Year, Month, MonthName
        ORDER BY Year, Month
    """
}


def run_queries():
    print("\n[SQL] Running queries...\n")
    conn = sqlite3.connect(DB_PATH)
    sql_export = []

    for name, query in QUERIES.items():
        try:
            df = pd.read_sql_query(query, conn)
            out_path = os.path.join(SQL_DIR, f"{name}.csv")
            df.to_csv(out_path, index=False)
            print(f"  ✓ {name}  ({len(df)} rows)")
            print(df.to_string(index=False))
            print()
            sql_export.append(f"-- {'='*55}\n-- {name}\n-- {'='*55}\n{query.strip()}\n")
        except Exception as e:
            print(f"  ✗ {name}: {e}\n")

    conn.close()

    # Save all queries to a single .sql portfolio file
    with open(SQL_FILE, "w") as f:
        f.write("-- =====================================================\n")
        f.write("-- Visakhapatnam Air Quality Project — SQL Queries\n")
        f.write('-- "Where you live shouldn\'t decide how long you live."\n')
        f.write("-- =====================================================\n\n")
        f.write("\n\n".join(sql_export))
    print(f"[SQL] All queries saved to {SQL_FILE}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("AIR QUALITY PROJECT — PHASE 3: SQL ANALYSIS")
    print("="*60)
    build_database()
    run_queries()
    print("\n✓ Done! Check your sql/ folder for:")
    print("  • air_quality.db     — SQLite database")
    print("  • queries.sql        — all queries (for portfolio)")
    print("  • 08 CSV files       — query results (for Tableau)")
    print("\nNext step: Phase 4 — Tableau Dashboard!")
