"""
VILLE_IA — Shared configuration for the ETL pipeline.

Supports multiple station groups. Each group produces an independent
dataset under its own folder (raw_data/<slug>/, processed/<slug>/).
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Station groups
# ---------------------------------------------------------------------------
# Each group is a logical weather station that may comprise several ECCC
# station IDs (renumbered over time).  The ``slug`` is used as the folder
# name in raw_data/ and processed/.
#
# Naming convention:  {TC_ID}_{location_slug}
# ---------------------------------------------------------------------------
STATION_GROUPS = [
    {
        "slug": "YUL_montreal_airport",
        "label": "Montreal / Trudeau Airport",
        "stations": [
            {"id": 5415,  "name": "TRUDEAU INTL (old)",  "start": 2000, "end": 2012},
            {"id": 51157, "name": "MONTREAL INTL A",     "start": 2013, "end": 2025},
        ],
        "start_year": 2000,
        "end_year": 2025,
    },
    {
        "slug": "WTA_mctavish",
        "label": "McGill / McTavish",
        "stations": [
            {"id": 10761, "name": "MCTAVISH", "start": 2000, "end": 2025},
        ],
        "start_year": 2000,
        "end_year": 2025,
    },
]

# Legacy alias — first group's stations (backward compat)
STATIONS = STATION_GROUPS[0]["stations"]
START_YEAR = STATION_GROUPS[0]["start_year"]
END_YEAR = STATION_GROUPS[0]["end_year"]

# ---------------------------------------------------------------------------
# ECCC download URL template
# ---------------------------------------------------------------------------
BASE_URL = (
    "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"
    "?format=csv"
    "&stationID={station_id}"
    "&Year={year}"
    "&Month={month}"
    "&Day=1"
    "&timeframe={timeframe}"
    "&submit=Download+Data"
)
TIMEFRAME_DAILY = 2
TIMEFRAME_HOURLY = 1

# ---------------------------------------------------------------------------
# HTTP settings
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT = 30
DELAY_BETWEEN_REQUESTS = 1
MAX_RETRIES = 3
RETRY_BACKOFF = 2

# ---------------------------------------------------------------------------
# Directories (relative to project root — run from heatwaves/)
# ---------------------------------------------------------------------------
RAW_DIR = Path("raw_data")
PROCESSED_DIR = Path("processed")

# Legacy flat paths (for backward compat — prefer get_paths())
RAW_DAILY_DIR = RAW_DIR / "daily"
RAW_HOURLY_DIR = RAW_DIR / "hourly"


def get_paths(slug: str) -> dict:
    """Return all I/O paths for a station group, namespaced by *slug*."""
    raw = RAW_DIR / slug
    proc = PROCESSED_DIR / slug
    return {
        "raw_daily_dir":     raw / "daily",
        "raw_hourly_dir":    raw / "hourly",
        "processed_dir":     proc,
        "daily_clean_csv":   proc / "daily_clean.csv",
        "hourly_agg_csv":    proc / "hourly_agg.csv",
        "merged_csv":        proc / "merged.csv",
        "features_csv":      proc / "features.csv",
        "dataset_csv":       proc / "dataset.csv",
        "quality_report_txt": proc / "quality_report.txt",
    }


# ---------------------------------------------------------------------------
# Intermediate & final output files  (legacy — prefer get_paths())
# ---------------------------------------------------------------------------
DAILY_CLEAN_CSV = PROCESSED_DIR / "daily_clean.csv"
HOURLY_AGG_CSV = PROCESSED_DIR / "hourly_agg.csv"
MERGED_CSV = PROCESSED_DIR / "merged.csv"
FEATURES_CSV = PROCESSED_DIR / "features.csv"
DATASET_CSV = PROCESSED_DIR / "dataset.csv"
QUALITY_REPORT_TXT = PROCESSED_DIR / "quality_report.txt"

# ---------------------------------------------------------------------------
# Columns to drop (too sparse or irrelevant for heatwave prediction)
# ---------------------------------------------------------------------------
DROP_COLUMNS = [
    "snow_on_ground_cm",     # 34.6% missing — winter-only
    "wind_chill_min",        # 63.1% missing — winter-only
    "heat_deg_days",         # heating degree days — winter metric
    "cool_deg_days",         # redundant with temp_mean_c
    "max_gust_dir_10deg",    # 61.9% missing — old station gap
    "max_gust_speed_kmh",    # 61.9% missing — old station gap
]

# ---------------------------------------------------------------------------
# Column rename mappings  (raw ECCC name → clean snake_case)
# ---------------------------------------------------------------------------
DAILY_COLUMNS_RENAME = {
    # Classic per-year downloads
    "Date/Time":                 "date",
    "Max Temp (°C)":             "temp_max_c",
    "Min Temp (°C)":             "temp_min_c",
    "Mean Temp (°C)":            "temp_mean_c",
    "Total Rain (mm)":           "total_rain_mm",
    "Total Snow (cm)":           "total_snow_cm",
    "Total Precip (mm)":         "total_precip_mm",
    # Bulk downloads (uppercase)
    "LOCAL_DATE":                "date",
    "MAX_TEMPERATURE":           "temp_max_c",
    "MIN_TEMPERATURE":           "temp_min_c",
    "MEAN_TEMPERATURE":          "temp_mean_c",
    "TOTAL_RAIN":                "total_rain_mm",
    "TOTAL_SNOW":                "total_snow_cm",
    "TOTAL_PRECIPITATION":       "total_precip_mm",
}

HOURLY_COLUMNS_OF_INTEREST = {
    # Classic per-month downloads
    "Temp (°C)":             "temp_c",
    "Dew Point Temp (°C)":   "dew_point_c",
    "Rel Hum (%)":           "rel_hum_pct",
    "Wind Dir (10s deg)":    "wind_dir_10deg",
    "Wind Spd (km/h)":       "wind_spd_kmh",
    "Visibility (km)":       "visibility_km",
    "Stn Press (kPa)":       "stn_press_kpa",
    # Bulk downloads (uppercase)
    "TEMP":                  "temp_c",
    "DEW_POINT_TEMP":        "dew_point_c",
    "RELATIVE_HUMIDITY":     "rel_hum_pct",
    "WIND_DIRECTION":        "wind_dir_10deg",
    "WIND_SPEED":            "wind_spd_kmh",
    "VISIBILITY":            "visibility_km",
    "STATION_PRESSURE":      "stn_press_kpa",
}

# Hourly → daily aggregation spec  (clean col → list of agg funcs)
HOURLY_AGG_SPEC = {
    "rel_hum_pct":   ["mean", "min", "max"],
    "wind_spd_kmh":  ["mean", "max"],
    "dew_point_c":   ["mean", "max"],
    "stn_press_kpa": ["mean"],
    "visibility_km": ["mean"],
    "temp_c":        ["mean"],
}

# Flat rename after multi-level aggregation
HOURLY_AGG_RENAME = {
    ("rel_hum_pct", "mean"):   "humidity_mean_pct",
    ("rel_hum_pct", "min"):    "humidity_min_pct",
    ("rel_hum_pct", "max"):    "humidity_max_pct",
    ("wind_spd_kmh", "mean"):  "wind_speed_mean_kmh",
    ("wind_spd_kmh", "max"):   "wind_speed_max_kmh",
    ("dew_point_c", "mean"):   "dew_point_mean_c",
    ("dew_point_c", "max"):    "dew_point_max_c",
    ("stn_press_kpa", "mean"): "pressure_mean_kpa",
    ("visibility_km", "mean"): "visibility_mean_km",
    ("temp_c", "mean"):        "temp_hourly_mean_c",
}

# ---------------------------------------------------------------------------
# Heatwave thresholds  (Strict Combined Rule — Option 3)
# ---------------------------------------------------------------------------
HEATWAVE_TMAX_THRESHOLD = 32       # °C daytime
HEATWAVE_TMIN_THRESHOLD = 20       # °C nighttime
HEATWAVE_HUMIDEX_THRESHOLD = 41    # Humidex peak
HEATWAVE_CONSECUTIVE_DAYS = 2

# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
ROLLING_WINDOWS = [2, 3, 7, 14]
LOOKAHEAD_DAYS = 3

# Summer filter — INSPQ chaleur estivale analysis period
SUMMER_MONTHS = [5, 6, 7, 8, 9]    # May–September

# Persistence counters (°C thresholds)
HOT_DAY_THRESHOLD = 30             # for consecutive_hot_days counter
DRY_DAY_PRECIP_THRESHOLD = 1.0     # mm — below this counts as "dry"
PRECIP_DEFICIT_THRESHOLD = 5.0     # mm / 7 days

# ---------------------------------------------------------------------------
# Scenario thresholds  (from SRS)
# ---------------------------------------------------------------------------
GREEN_MAX = 0.30
YELLOW_MAX = 0.65

# ---------------------------------------------------------------------------
# Date column auto-detection candidates
# ---------------------------------------------------------------------------
DATE_COLUMN_CANDIDATES = [
    "Date/Time (LST)",
    "Date/Time (UTC)",
    "Date/Time",
    "Date/Heure (HNE)",
    "Date/Heure",
    "LOCAL_DATE",
]
