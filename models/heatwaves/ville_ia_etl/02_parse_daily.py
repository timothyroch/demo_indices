"""
VILLE_IA — Step 02: Parse & Clean Daily Data
==============================================

Reads raw daily CSVs from a station group's folder, renames columns,
cleans types, exports ``processed/<slug>/daily_clean.csv``.

Usage:
    python -m ville_ia_etl.02_parse_daily
"""

import logging

import pandas as pd

from ville_ia_etl.config import (
    STATION_GROUPS, SUMMER_MONTHS,
    DAILY_COLUMNS_RENAME, DATE_COLUMN_CANDIDATES,
    get_paths,
)

log = logging.getLogger(__name__)


def _find_date_column(columns):
    """Auto-detect date column from ECCC CSV headers."""
    for c in DATE_COLUMN_CANDIDATES:
        if c in columns:
            return c
    raise KeyError(f"No date column found. Available: {list(columns)}")


def parse_daily(paths):
    """Parse all daily CSVs → single clean DataFrame."""
    raw_daily_dir = paths["raw_daily_dir"]
    files = sorted(raw_daily_dir.glob("daily_*.csv"))
    if not files:
        raise FileNotFoundError(f"No daily CSVs in {raw_daily_dir}")

    log.info(f"Parsing {len(files)} daily files from {raw_daily_dir}...")
    frames = []
    for f in files:
        try:
            frames.append(pd.read_csv(f, encoding="utf-8-sig"))
        except Exception as e:
            log.warning(f"Could not read {f.name}: {e}")

    if not frames:
        raise RuntimeError("No daily files parsed successfully.")

    daily = pd.concat(frames, ignore_index=True)

    # Normalise date column name
    date_col = _find_date_column(daily.columns)
    if date_col != "Date/Time":
        daily = daily.rename(columns={date_col: "Date/Time"})

    # Keep & rename mapped columns only
    available = [c for c in DAILY_COLUMNS_RENAME if c in daily.columns]
    daily = daily[available].rename(columns=DAILY_COLUMNS_RENAME)

    # Types
    daily["date"] = pd.to_datetime(daily["date"], errors="coerce")
    numeric_cols = [c for c in daily.columns if c != "date"]
    for col in numeric_cols:
        daily[col] = pd.to_numeric(daily[col], errors="coerce")

    daily = daily.dropna(subset=["date"])
    daily = daily.sort_values("date").reset_index(drop=True)
    daily = daily.drop_duplicates(subset=["date"], keep="first")

    log.info(
        f"Daily clean: {len(daily)} rows, "
        f"{daily['date'].min().date()} → {daily['date'].max().date()}"
    )
    return daily


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
        log.info(f"VILLE_IA — Step 02: Parse Daily Data — {group['label']}")

        daily = parse_daily(paths)

        # Keep only summer months (May–Sep) and respect end_year cutoff
        pre = len(daily)
        daily = daily[daily["date"].dt.month.isin(SUMMER_MONTHS)].reset_index(drop=True)
        end_date = pd.Timestamp(f"{group['end_year']}-09-30")
        daily = daily[daily["date"] <= end_date].reset_index(drop=True)
        log.info(
            f"Filtered May–Sep up to {end_date.date()}: {pre} → {len(daily)} rows"
        )

        paths["processed_dir"].mkdir(parents=True, exist_ok=True)
        daily.to_csv(paths["daily_clean_csv"], index=False)
        log.info(f"Saved → {paths['daily_clean_csv']}")


if __name__ == "__main__":
    main()
