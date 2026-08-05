# VILLE_IA — Montreal Heatwave Prediction ETL

Downloads 25 years (2000–2025) of weather data from Environment Canada (Station 51157), engineers features, and labels heatwave events for machine learning.

## Setup

```bash
poetry install
```

## Usage

```bash
# Step 1 — Download raw CSVs (skips existing files, resumable)
poetry run download

# Step 2 — Run full processing pipeline (skip download)
poetry run process -- --skip-download
```

Or run individual steps:

```bash
python -m ville_ia_etl.02_parse_daily
python -m ville_ia_etl.03_parse_hourly
python -m ville_ia_etl.04_merge
python -m ville_ia_etl.05_engineer_features
python -m ville_ia_etl.06_label_target
python -m ville_ia_etl.07_quality_report
```

## Pipeline

| Step | Script | Input | Output |
|------|--------|-------|--------|
| 01 | `01_download.py` | ECCC API | `raw_data/daily/`, `raw_data/hourly/` |
| 02 | `02_parse_daily.py` | `raw_data/daily/*.csv` | `processed/daily_clean.csv` |
| 03 | `03_parse_hourly.py` | `raw_data/hourly/*.csv` | `processed/hourly_agg.csv` |
| 04 | `04_merge.py` | daily_clean + hourly_agg | `processed/merged.csv` |
| 05 | `05_engineer_features.py` | merged.csv | `processed/features.csv` |
| 06 | `06_label_target.py` | features.csv | `processed/dataset.csv` |
| 07 | `07_quality_report.py` | dataset.csv | `processed/quality_report.txt` |

## Heatwave Definition (Strict Combined Rule — Option 3)

After extensive auditing against historical events (2000–2025), the strict INSPQ definition was found to miss severe events, and the standard ECCC alert was found to be too broad.

This pipeline uses a **Custom ECCC-inspired Threshold** focusing on Humidex to accurately capture true deadly heatwaves in an Urban Heat Island (UHI) context:

- **(Tmax ≥ 32°C AND Tmin ≥ 20°C) OR (Humidex ≥ 41)** for **2 consecutive days**.
- Target: `target_heatwave_3d` — "is a heatwave starting in the next 3 days?"

*Note: This specific threshold guarantees capture of 100% of the major historical heatwaves while keeping false-positive meteorological "hot spells" to a minimum.*

## Final Dataset Columns

**From daily data:** date, temp_max_c, temp_min_c, temp_mean_c, total_rain_mm, total_snow_cm, total_precip_mm, snow_on_ground_cm, max_gust_speed_kmh

**From hourly (aggregated to daily):** humidity_mean/min/max_pct, wind_speed_mean/max_kmh, dew_point_mean/max_c, humidex_max, pressure_mean_kpa, visibility_mean_km

**Engineered features (~28):** rolling means, persistence streaks, precipitation deficit, temperature anomaly, heat accumulation, seasonal indicators

**Target:** hot_day, heatwave_event, target_heatwave_3d

## Data Source

Environment Canada Historical Climate Data (free, open)
https://climate.weather.gc.ca/
