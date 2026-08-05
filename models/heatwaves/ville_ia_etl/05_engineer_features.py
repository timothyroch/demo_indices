"""
VILLE_IA — Step 05: Engineer Features
=======================================

Reads ``processed/<slug>/merged.csv``, computes ~28 engineered features
(seasonal, rolling, persistence, precipitation deficit, temperature
dynamics, heat accumulation), exports ``processed/<slug>/features.csv``.

Usage:
    python -m ville_ia_etl.05_engineer_features
"""

import logging

import numpy as np
import pandas as pd

from ville_ia_etl.config import (
    STATION_GROUPS, get_paths,
    ROLLING_WINDOWS, HOT_DAY_THRESHOLD,
    HEATWAVE_TMIN_THRESHOLD, DRY_DAY_PRECIP_THRESHOLD,
    PRECIP_DEFICIT_THRESHOLD,
)

log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _add_seasonal(df):
    """month, day_of_year, is_summer."""
    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    df["is_summer"] = df["month"].isin([6, 7, 8]).astype(int)
    log.info("  + seasonal features (3)")
    return df


def _add_rolling(df):
    """Rolling means for temp_max, temp_min, humidity, dew_point over windows."""
    count = 0
    for w in ROLLING_WINDOWS:
        if "temp_max_c" in df.columns:
            df[f"tmax_roll_{w}d"] = df["temp_max_c"].rolling(w, min_periods=1).mean()
            count += 1
        if "temp_min_c" in df.columns:
            df[f"tmin_roll_{w}d"] = df["temp_min_c"].rolling(w, min_periods=1).mean()
            count += 1
        if "humidity_mean_pct" in df.columns:
            df[f"humidity_roll_{w}d"] = df["humidity_mean_pct"].rolling(w, min_periods=1).mean()
            count += 1
        if "dew_point_mean_c" in df.columns:
            df[f"dew_point_roll_{w}d"] = df["dew_point_mean_c"].rolling(w, min_periods=1).mean()
            count += 1
        if "humidex" in df.columns:
            df[f"humidex_roll_{w}d"] = df["humidex"].rolling(w, min_periods=1).mean()
            count += 1
    log.info(f"  + rolling features ({count})")
    return df


def _add_persistence(df):
    """Consecutive hot days, warm nights, and dry days (iterative streak counter)."""
    count = 0

    # Consecutive hot days (Tmax >= 30)
    if "temp_max_c" in df.columns:
        streak = np.zeros(len(df), dtype=int)
        for i in range(len(df)):
            val = df["temp_max_c"].iat[i]
            if pd.notna(val) and val >= HOT_DAY_THRESHOLD:
                streak[i] = (streak[i - 1] + 1) if i > 0 else 1
        df["consecutive_hot_days"] = streak
        count += 1

    # Consecutive warm nights (Tmin >= 20)
    if "temp_min_c" in df.columns:
        streak = np.zeros(len(df), dtype=int)
        for i in range(len(df)):
            val = df["temp_min_c"].iat[i]
            if pd.notna(val) and val >= HEATWAVE_TMIN_THRESHOLD:
                streak[i] = (streak[i - 1] + 1) if i > 0 else 1
        df["consecutive_warm_nights"] = streak
        count += 1

    # Consecutive dry days (precip < 1mm)
    if "total_precip_mm" in df.columns:
        streak = np.zeros(len(df), dtype=int)
        for i in range(len(df)):
            val = df["total_precip_mm"].iat[i]
            if pd.notna(val) and val < DRY_DAY_PRECIP_THRESHOLD:
                streak[i] = (streak[i - 1] + 1) if i > 0 else 1
        df["consecutive_dry_days"] = streak
        count += 1

    log.info(f"  + persistence counters ({count})")
    return df


def _add_precip_deficit(df):
    """Rolling precip sums and deficit flag."""
    count = 0
    if "total_precip_mm" in df.columns:
        df["precip_7d"] = df["total_precip_mm"].rolling(7, min_periods=1).sum()
        df["precip_14d"] = df["total_precip_mm"].rolling(14, min_periods=1).sum()
        df["precip_deficit_flag"] = (df["precip_7d"] < PRECIP_DEFICIT_THRESHOLD).astype(int)
        count = 3
    log.info(f"  + precipitation deficit ({count})")
    return df


def _add_temp_dynamics(df):
    """Temperature change and anomaly from historical day-of-year mean."""
    count = 0
    if "temp_max_c" in df.columns:
        df["tmax_change_1d"] = df["temp_max_c"].diff(1)
        df["tmax_change_3d"] = df["temp_max_c"].diff(3)
        count += 2

        # Anomaly: deviation from historical mean Tmax for that day_of_year
        if "day_of_year" in df.columns:
            doy_mean = df.groupby("day_of_year")["temp_max_c"].transform("mean")
            df["temp_anomaly"] = df["temp_max_c"] - doy_mean
            count += 1

    log.info(f"  + temperature dynamics ({count})")
    return df


def _add_heat_accumulation(df):
    """Excess heat above 30°C, computed humidex, and rolling accumulation."""
    count = 0
    if "temp_max_c" in df.columns:
        df["heat_degree_above_30"] = (df["temp_max_c"] - 30).clip(lower=0)
        df["heat_accumulation_7d"] = (
            df["heat_degree_above_30"].rolling(7, min_periods=1).sum()
        )
        count += 2

    # Compute humidex from temp and dew point (Canadian formula)
    # Humidex = T + (5/9) * (6.11 * exp(5417.7530 * (1/273.16 - 1/(273.15+Td))) - 10)
    if "temp_max_c" in df.columns and "dew_point_max_c" in df.columns:
        T = df["temp_max_c"]
        Td = df["dew_point_max_c"]
        e = 6.11 * np.exp(5417.7530 * (1 / 273.16 - 1 / (273.15 + Td)))
        df["humidex"] = T + (5 / 9) * (e - 10)
        # Only meaningful when temp > 20°C — set to NaN in cold weather
        df.loc[df["temp_max_c"] < 20, "humidex"] = np.nan
        df["humidex_roll_3d"] = df["humidex"].rolling(3, min_periods=1).mean()
        count += 2

    log.info(f"  + heat accumulation ({count})")
    return df


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def engineer_features(paths):
    """Read merged data, add all engineered features."""
    log.info("Reading merged data...")
    df = pd.read_csv(paths["merged_csv"], parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    log.info(f"Input: {len(df)} rows × {len(df.columns)} cols")

    log.info("Engineering features...")
    df = _add_seasonal(df)
    df = _add_rolling(df)
    df = _add_persistence(df)
    df = _add_precip_deficit(df)
    df = _add_temp_dynamics(df)
    df = _add_heat_accumulation(df)

    # NOTE: Summer filter (May–Sep) is applied upstream in steps 02/03.
    # Data arriving here is already summer-only.

    log.info(f"Output: {len(df)} rows × {len(df.columns)} cols")
    return df


def main(station_group=None):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    groups = [station_group] if station_group else STATION_GROUPS

    for group in groups:
        slug = group["slug"]
        paths = get_paths(slug)
        log.info(f"VILLE_IA — Step 05: Engineer Features — {group['label']}")

        df = engineer_features(paths)

        paths["processed_dir"].mkdir(parents=True, exist_ok=True)
        df.to_csv(paths["features_csv"], index=False)
        log.info(f"Saved → {paths['features_csv']}")


if __name__ == "__main__":
    main()
