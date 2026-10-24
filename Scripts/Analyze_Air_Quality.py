"""
Visakhapatnam Air Quality & Public Health Project
Phase 2: Data Cleaning, Merging & Exploratory Analysis
Motto: "Where you live shouldn't decide how long you live."

HOW TO USE:
1. Update the file paths in the CONFIG section below to match your actual filenames
2. Run: python scripts/analyze_air_quality.py
3. Check data/clean/ for the cleaned CSV
4. Check data/charts/ for the output charts
"""

import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIG — update these paths to match your files
# ─────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RAW_DIR      = os.path.join(PROJECT_ROOT, "data", "raw")
CLEAN_DIR    = os.path.join(PROJECT_ROOT, "data", "clean")
CHARTS_DIR   = os.path.join(PROJECT_ROOT, "data", "charts")

os.makedirs(CLEAN_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

# ── Update these filenames if yours are different ──
STATIONS_FILE  = os.path.join(RAW_DIR, "stations.csv")

# The script will auto-detect your main data files — just make sure they are
# inside data/raw/. It looks for any CSV with 'station_day' or 'city_day'
# in the name, or you can hardcode them below.
def find_data_files():
    """Auto-detect dataset files in data/raw/"""
    all_csvs = glob.glob(os.path.join(RAW_DIR, "*.csv"))
    station_day_files = [f for f in all_csvs if "station_day" in os.path.basename(f).lower()]
    city_day_files    = [f for f in all_csvs if "city_day"    in os.path.basename(f).lower()]
    other_files       = [f for f in all_csvs
                         if f not in station_day_files + city_day_files
                         and "station" not in os.path.basename(f).lower().replace("stations", "")]
    print(f"\nFiles found in data/raw/:")
    for f in all_csvs:
        print(f"  {os.path.basename(f)}")
    return station_day_files, city_day_files

# ─────────────────────────────────────────────
# STEP 1: LOAD STATIONS LOOKUP
# ─────────────────────────────────────────────
def load_stations():
    df = pd.read_csv(STATIONS_FILE, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    ap = df[df["State"] == "Andhra Pradesh"].copy()
    print(f"\n[Stations] Total stations: {len(df)} | AP stations: {len(ap)}")
    print(ap[["StationId", "StationName", "City", "Status"]].to_string(index=False))
    return df, ap


# ─────────────────────────────────────────────
# STEP 2: LOAD & CLEAN MAIN DATA FILES
# ─────────────────────────────────────────────
def load_and_clean(filepath):
    """Load a station_day CSV, standardize columns, fix data types, remove bad readings."""
    print(f"\n[Loading] {os.path.basename(filepath)}")
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    print(f"  Shape: {df.shape} | Columns: {list(df.columns)}")

    # Standardize date column
    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df.rename(columns={date_col: "Date"}, inplace=True)

    # Standardize StationId column
    id_col = next((c for c in df.columns if "station" in c.lower() and "id" in c.lower()), None)
    if id_col and id_col != "StationId":
        df.rename(columns={id_col: "StationId"}, inplace=True)

    # Replace known sensor-error sentinel values with NaN
    numeric_cols = df.select_dtypes(include="number").columns
    for col in numeric_cols:
        df[col] = df[col].replace([-999, -9999, 999, 9999, 0], pd.NA)
        df.loc[df[col] < 0, col] = pd.NA

    # Drop rows where date is missing
    if "Date" in df.columns:
        df = df.dropna(subset=["Date"])

    print(f"  After cleaning: {df.shape}")
    return df


# ─────────────────────────────────────────────
# STEP 3: MERGE DATASETS + FILTER FOR AP
# ─────────────────────────────────────────────
def merge_and_filter(dfs, ap_stations):
    """Combine multiple datasets and filter for AP station IDs."""
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["StationId", "Date"])
    combined = combined.sort_values(["StationId", "Date"])

    ap_ids = ap_stations["StationId"].tolist()
    ap_data = combined[combined["StationId"].isin(ap_ids)].copy()

    # Merge in station name + city
    ap_data = ap_data.merge(
        ap_stations[["StationId", "StationName", "City"]],
        on="StationId", how="left"
    )

    print(f"\n[Merged] Total rows: {len(combined)} | AP rows: {len(ap_data)}")
    print(f"  Date range: {ap_data['Date'].min()} → {ap_data['Date'].max()}")
    print(f"  AP stations found in data: {ap_data['StationId'].unique().tolist()}")
    return ap_data


# ─────────────────────────────────────────────
# STEP 4: EDA — PRINT SUMMARY
# ─────────────────────────────────────────────
def print_summary(df):
    print("\n" + "="*60)
    print("EXPLORATORY ANALYSIS — ANDHRA PRADESH AIR QUALITY")
    print("="*60)

    pollutants = [c for c in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"]
                  if c in df.columns]

    print(f"\nPollutants available: {pollutants}")
    print(f"\nMissing value % per pollutant:")
    for p in pollutants:
        pct = df[p].isna().mean() * 100
        print(f"  {p:8s}: {pct:.1f}% missing")

    print(f"\nAverage AQI by City:")
    if "AQI" in df.columns and "City" in df.columns:
        city_aqi = (df.groupby("City")["AQI"]
                      .agg(["mean", "max", "count"])
                      .round(1)
                      .sort_values("mean", ascending=False))
        print(city_aqi.to_string())

    print(f"\nAverage PM2.5 by Station:")
    if "PM2.5" in df.columns:
        stn_pm25 = (df.groupby(["City", "StationName"])["PM2.5"]
                      .mean().round(1)
                      .sort_values(ascending=False))
        print(stn_pm25.to_string())


# ─────────────────────────────────────────────
# STEP 5: CHARTS
# ─────────────────────────────────────────────
def plot_charts(df):
    pollutants = [c for c in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]
                  if c in df.columns]
    if not pollutants:
        print("\nNo pollutant columns found for charting — check column names.")
        return

    sns.set_theme(style="whitegrid", palette="muted")
    primary_pollutant = "PM2.5" if "PM2.5" in pollutants else pollutants[0]

    # ── Chart 1: Average pollutant levels by city (bar chart) ──
    fig, ax = plt.subplots(figsize=(10, 5))
    city_means = df.groupby("City")[primary_pollutant].mean().sort_values(ascending=False)
    bars = ax.bar(city_means.index, city_means.values, color=sns.color_palette("muted"))
    ax.set_title(f"Average {primary_pollutant} by City — Andhra Pradesh", fontsize=14, fontweight="bold")
    ax.set_xlabel("City")
    ax.set_ylabel(f"{primary_pollutant} (µg/m³)")
    ax.axhline(60, color="orange", linestyle="--", linewidth=1.2, label="India NAQI Moderate threshold (60)")
    ax.axhline(120, color="red", linestyle="--", linewidth=1.2, label="India NAQI Poor threshold (120)")
    ax.legend()
    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "01_avg_pm25_by_city.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"\n[Chart saved] {path}")

    # ── Chart 2: PM2.5 trend over time for Visakhapatnam ──
    vizag = df[df["City"] == "Visakhapatnam"].copy()
    if not vizag.empty and "Date" in vizag.columns:
        vizag_monthly = vizag.set_index("Date")[primary_pollutant].resample("ME").mean()
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(vizag_monthly.index, vizag_monthly.values, color="#2196F3", linewidth=2)
        ax.fill_between(vizag_monthly.index, vizag_monthly.values, alpha=0.15, color="#2196F3")
        ax.set_title(f"Visakhapatnam — Monthly Average {primary_pollutant} Over Time", fontsize=14, fontweight="bold")
        ax.set_xlabel("Month")
        ax.set_ylabel(f"{primary_pollutant} (µg/m³)")
        ax.axhline(60, color="orange", linestyle="--", linewidth=1, label="Moderate threshold")
        ax.axhline(120, color="red", linestyle="--", linewidth=1, label="Poor threshold")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.xticks(rotation=45)
        ax.legend()
        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, "02_vizag_pm25_trend.png")
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"[Chart saved] {path}")

    # ── Chart 3: Monthly seasonal pattern (all AP stations) ──
    if "Date" in df.columns:
        df["Month"] = df["Date"].dt.month
        monthly_avg = df.groupby("Month")[primary_pollutant].mean()
        month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(monthly_avg.index, monthly_avg.values,
               color=["#EF5350" if v > 60 else "#42A5F5" for v in monthly_avg.values])
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(month_labels)
        ax.set_title(f"Seasonal Pattern — Average {primary_pollutant} by Month (Andhra Pradesh)", fontsize=14, fontweight="bold")
        ax.set_xlabel("Month")
        ax.set_ylabel(f"{primary_pollutant} (µg/m³)")
        ax.axhline(60, color="orange", linestyle="--", linewidth=1.2, label="Moderate threshold")
        ax.legend()
        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, "03_seasonal_pattern.png")
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"[Chart saved] {path}")

    # ── Chart 4: Pollutant correlation heatmap ──
    if len(pollutants) >= 3:
        fig, ax = plt.subplots(figsize=(8, 6))
        corr = df[pollutants].corr()
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm",
                    center=0, ax=ax, linewidths=0.5)
        ax.set_title("Pollutant Correlation — Andhra Pradesh", fontsize=14, fontweight="bold")
        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, "04_pollutant_correlation.png")
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"[Chart saved] {path}")

    # ── Chart 5: AP city comparison box plot ──
    if len(df["City"].unique()) > 1:
        fig, ax = plt.subplots(figsize=(10, 5))
        city_order = df.groupby("City")[primary_pollutant].median().sort_values(ascending=False).index
        df.boxplot(column=primary_pollutant, by="City", ax=ax,
                   order=city_order, patch_artist=True)
        ax.set_title(f"{primary_pollutant} Distribution by City — Andhra Pradesh", fontsize=13, fontweight="bold")
        plt.suptitle("")
        ax.set_xlabel("City")
        ax.set_ylabel(f"{primary_pollutant} (µg/m³)")
        plt.xticks(rotation=30)
        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, "05_city_comparison_boxplot.png")
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"[Chart saved] {path}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("AIR QUALITY ANALYSIS — VISAKHAPATNAM & ANDHRA PRADESH")
    print("Where you live shouldn't decide how long you live.")
    print("="*60)

    # 1. Load stations
    all_stations, ap_stations = load_stations()

    # 2. Find and load data files
    station_day_files, city_day_files = find_data_files()

    if not station_day_files:
        print("\n[ERROR] No station_day CSV found in data/raw/")
        print("Make sure your main data file is in data/raw/ and has 'station_day' in the filename.")
        print("If it has a different name, rename it to include 'station_day' e.g. 'station_day_2023.csv'")
        exit()

    # 3. Load and clean all station_day files found
    dfs = []
    for f in station_day_files:
        try:
            cleaned = load_and_clean(f)
            dfs.append(cleaned)
        except Exception as e:
            print(f"  [Warning] Could not load {os.path.basename(f)}: {e}")

    if not dfs:
        print("\n[ERROR] Could not load any data files. Check file formats.")
        exit()

    # 4. Merge and filter for AP
    ap_data = merge_and_filter(dfs, ap_stations)

    # 5. Save clean file
    clean_path = os.path.join(CLEAN_DIR, "ap_air_quality_clean.csv")
    ap_data.to_csv(clean_path, index=False)
    print(f"\n[Saved] Clean data → {clean_path}")
    print(f"  Rows: {len(ap_data)} | Columns: {list(ap_data.columns)}")

    # 6. Print EDA summary
    print_summary(ap_data)

    # 7. Generate charts
    print("\n[Generating charts...]")
    try:
        plot_charts(ap_data)
        print(f"\nAll charts saved to: {CHARTS_DIR}")
    except Exception as e:
        print(f"[Chart error] {e}")

    print("\n✓ Done! Next step: open data/charts/ to review your visualizations.")
    print("  Then upload the charts here and we'll move to Phase 3 (SQL).\n")