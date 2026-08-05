"""
VILLE_IA — Step 04: Merge Daily + Hourly Aggregated Data
=========================================================

Left-joins daily_clean with hourly_agg on ``date``, exports
``processed/<slug>/merged.csv``.

Usage:
    python -m ville_ia_etl.04_merge
"""

import logging

import pandas as pd

from ville_ia_etl.config import STATION_GROUPS, get_paths

log = logging.getLogger(__name__)


def merge(paths):
    """Merge daily + hourly-aggregated datasets on date."""
    log.info("Reading inputs...")
    daily = pd.read_csv(paths["daily_clean_csv"], parse_dates=["date"])
    hourly = pd.read_csv(paths["hourly_agg_csv"], parse_dates=["date"])

    log.info(f"Daily:  {len(daily)} rows × {len(daily.columns)} cols")
    log.info(f"Hourly: {len(hourly)} rows × {len(hourly.columns)} cols")

    merged = daily.merge(hourly, on="date", how="left")

    hourly_missing = merged[hourly.columns.drop("date")].isna().all(axis=1).sum()
    log.info(
        f"Merged: {len(merged)} rows × {len(merged.columns)} cols  "
        f"({hourly_missing} days missing hourly data)"
    )
    return merged


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
        log.info(f"VILLE_IA — Step 04: Merge Daily + Hourly — {group['label']}")

        merged = merge(paths)

        paths["processed_dir"].mkdir(parents=True, exist_ok=True)
        merged.to_csv(paths["merged_csv"], index=False)
        log.info(f"Saved → {paths['merged_csv']}")


if __name__ == "__main__":
    main()
