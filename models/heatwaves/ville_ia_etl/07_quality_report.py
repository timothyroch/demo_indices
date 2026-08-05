"""
VILLE_IA — Step 07: Data Quality Report
=========================================

Reads ``processed/<slug>/dataset.csv``, generates a comprehensive quality
report including date coverage, missing values, summary stats, heatwave
events per year, and class balance.

Usage:
    python -m ville_ia_etl.07_quality_report
"""

import logging
from datetime import datetime

import pandas as pd

from ville_ia_etl.config import (
    STATION_GROUPS, get_paths,
    SUMMER_MONTHS,
)

log = logging.getLogger(__name__)


def generate_report(station_group, paths):
    """Generate data quality report from the final dataset."""
    df = pd.read_csv(paths["dataset_csv"], parse_dates=["date"])
    lines = []

    lines.append("=" * 65)
    lines.append(f"VILLE_IA — Data Quality Report — {station_group['label']}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 65)
    lines.append("")

    # --- Overview ---
    station_str = ", ".join(
        f"{s['id']} ({s['name']})" for s in station_group["stations"]
    )
    lines.append(f"Station group: {station_group['slug']}")
    lines.append(f"Stations:      {station_str}")
    lines.append(f"Rows:          {len(df)}")
    lines.append(f"Columns:       {len(df.columns)}")
    date_min = pd.to_datetime(df["date"].min()).date()
    date_max = pd.to_datetime(df["date"].max()).date()
    lines.append(f"Date range:    {date_min} → {date_max}")
    lines.append("")

    # --- Date coverage (summer only) ---
    df_dates = pd.to_datetime(df["date"])
    full_range = pd.date_range(df_dates.min(), df_dates.max(), freq="D")
    expected = full_range[full_range.month.isin(SUMMER_MONTHS)]
    missing_dates = expected.difference(df_dates)
    lines.append(f"Expected summer days: {len(expected)}")
    lines.append(f"Actual days:          {len(df)}")
    lines.append(f"Missing days:         {len(missing_dates)}")
    if 0 < len(missing_dates) <= 20:
        for d in missing_dates:
            lines.append(f"  - {d.date()}")
    elif len(missing_dates) > 20:
        lines.append("  (first 20 shown)")
        for d in missing_dates[:20]:
            lines.append(f"  - {d.date()}")
    lines.append("")

    # --- Missing values ---
    lines.append("Missing values per column:")
    lines.append(f"  {'Column':<35s} {'Missing':>8s} {'%':>8s}")
    lines.append(f"  {'-'*35} {'-'*8} {'-'*8}")
    for col in df.columns:
        if col == "date":
            continue
        n = df[col].isna().sum()
        pct = 100 * n / len(df)
        if n > 0:
            lines.append(f"  {col:<35s} {n:>8d} {pct:>7.1f}%")
    lines.append("")

    # --- Summary stats for key columns ---
    key_cols = ["temp_max_c", "temp_min_c", "humidity_mean_pct",
                "wind_speed_mean_kmh", "humidex_max"]
    avail = [c for c in key_cols if c in df.columns]
    if avail:
        lines.append("Summary statistics (key columns):")
        stats = df[avail].describe().round(2)
        lines.append(stats.to_string())
        lines.append("")

    # --- Heatwave events per year ---
    if "heatwave_event" in df.columns:
        lines.append("Heatwave event days per year:")
        yearly = df.groupby(pd.to_datetime(df["date"]).dt.year)["heatwave_event"].sum()
        for year, count in yearly.items():
            marker = f"  {'█' * int(count)}" if count > 0 else ""
            lines.append(f"  {year}: {int(count):>3d} days{marker}")
        lines.append("")

    # --- Target class balance ---
    if "target_heatwave_3d" in df.columns:
        pos = int(df["target_heatwave_3d"].sum())
        neg = len(df) - pos
        pct = 100 * pos / len(df) if len(df) > 0 else 0
        lines.append("Target class balance (target_heatwave_3d):")
        lines.append(f"  Positive (heatwave coming): {pos:>6d} ({pct:.2f}%)")
        lines.append(f"  Negative (no heatwave):     {neg:>6d} ({100-pct:.2f}%)")
        lines.append("")

    report = "\n".join(lines)

    paths["processed_dir"].mkdir(parents=True, exist_ok=True)
    paths["quality_report_txt"].write_text(report, encoding="utf-8")
    log.info(f"Quality report saved → {paths['quality_report_txt']}")
    return report


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
        log.info(f"VILLE_IA — Step 07: Quality Report — {group['label']}")
        report = generate_report(group, paths)
        print("\n" + report)


if __name__ == "__main__":
    main()
