-- =====================================================
-- Visakhapatnam Air Quality Project — SQL Queries
-- "Where you live shouldn't decide how long you live."
-- =====================================================

-- =======================================================
-- 01_avg_pollutants_by_city
-- =======================================================
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


-- =======================================================
-- 02_yearly_trend_by_city
-- =======================================================
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


-- =======================================================
-- 03_monthly_seasonal_pattern
-- =======================================================
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


-- =======================================================
-- 04_worst_days_vizag
-- =======================================================
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


-- =======================================================
-- 05_aqi_category_breakdown
-- =======================================================
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


-- =======================================================
-- 06_winter_vs_summer
-- =======================================================
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


-- =======================================================
-- 07_pollutant_exceedance_days
-- =======================================================
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


-- =======================================================
-- 08_vizag_monthly_pm25_by_year
-- =======================================================
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
