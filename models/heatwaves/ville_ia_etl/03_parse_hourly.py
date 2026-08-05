"""
VILLE_IA — Step 03: Parse & Aggregate Hourly Data
===================================================

Reads raw hourly CSVs from a station group's folder, aggregates to
daily granularity, exports ``processed/<slug>/hourly_agg.csv``.

Usage:
    python -m ville_ia_etl.03_parse_hourly
"""

import logging

import pandas as pd
from tqdm import tqdm

from ville_ia_etl.config import (
    STATION_GROUPS, SUMMER_MONTHS,
    HOURLY_COLUMNS_OF_INTEREST, HOURLY_AGG_SPEC, HOURLY_AGG_RENAME,
    DATE_COLUMN_CANDIDATES,
    get_paths,
)

log = logging.getLogger(__name__)


def _find_date_column(columns):
    for c in DATE_COLUMN_CANDIDATES:
        if c in columns:
            return c
    raise KeyError(f"No date column found. Available: {list(columns)}")


def parse_and_aggregate_hourly(paths):
    """Read hourly CSVs, aggregate to daily summary stats."""
    raw_hourly_dir = paths["raw_hourly_dir"]
    files = sorted(raw_hourly_dir.glob("hourly_*.csv"))
    if not files:
        raise FileNotFoundError(f"No hourly CSVs in {raw_hourly_dir}")

    log.info(f"Parsing {len(files)} hourly files from {raw_hourly_dir}...")
    frames = []
    for f in tqdm(files, desc="Reading hourly", unit="file", leave=False):
        try:
            frames.append(pd.read_csv(f, encoding="utf-8-sig"))
        except Exception as e:
            log.warning(f"Could not read {f.name}: {e}")

    if not frames:
        raise RuntimeError("No hourly files parsed successfully.")

    hourly = pd.concat(frames, ignore_index=True)

    # Auto-detect date column
    date_col = _find_date_column(hourly.columns)
    log.info(f"Hourly date column: '{date_col}'")
    hourly["date"] = pd.to_datetime(hourly[date_col], errors="coerce").dt.date
    hourly["date"] = pd.to_datetime(hourly["date"])

    # Keep & rename columns of interest
    available = {k: v for k, v in HOURLY_COLUMNS_OF_INTEREST.items()
                 if k in hourly.columns}
    hourly = hourly[["date"] + list(available.keys())].rename(columns=available)

    # Coerce to numeric
    for col in [c for c in hourly.columns if c != "date"]:
        hourly[col] = pd.to_numeric(hourly[col], errors="coerce")

    # Build agg spec from what's actually present
    agg = {col: funcs for col, funcs in HOURLY_AGG_SPEC.items()
           if col in hourly.columns}

    daily_agg = hourly.groupby("date").agg(agg)

    # Flatten multi-level column index
    daily_agg.columns = [
        HOURLY_AGG_RENAME.get(col, f"{col[0]}_{col[1]}")
        for col in daily_agg.columns
    ]
    daily_agg = daily_agg.reset_index()

    log.info(
        f"Hourly aggregated: {len(daily_agg)} days, "
        f"columns: {list(daily_agg.columns)}"
    )
    return daily_agg


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
        log.info(f"VILLE_IA — Step 03: Parse & Aggregate Hourly Data — {group['label']}")

        hourly_agg = parse_and_aggregate_hourly(paths)

        # Keep only summer months (May–Sep) and respect end_year cutoff
        pre = len(hourly_agg)
        hourly_agg = hourly_agg[hourly_agg["date"].dt.month.isin(SUMMER_MONTHS)].reset_index(drop=True)
        end_date = pd.Timestamp(f"{group['end_year']}-09-30")
        hourly_agg = hourly_agg[hourly_agg["date"] <= end_date].reset_index(drop=True)
        log.info(
            f"Filtered May–Sep up to {end_date.date()}: {pre} → {len(hourly_agg)} rows"
        )

        paths["processed_dir"].mkdir(parents=True, exist_ok=True)
        hourly_agg.to_csv(paths["hourly_agg_csv"], index=False)
        log.info(f"Saved → {paths['hourly_agg_csv']}")


if __name__ == "__main__":
    main()
