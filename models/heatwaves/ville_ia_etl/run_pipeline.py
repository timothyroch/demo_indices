"""
VILLE_IA — Pipeline Orchestrator
==================================

Runs steps 01 → 07 in order for each station group.

Flags:
    --skip-download   Start from step 02 (raw data already present).
    --station SLUG    Run only the given station group (e.g. WTA_mctavish).

Usage:
    poetry run process
    poetry run process -- --skip-download
    poetry run process -- --station WTA_mctavish --skip-download
    python -m ville_ia_etl.run_pipeline --skip-download
"""

import argparse
import logging
import time

from ville_ia_etl.config import STATION_GROUPS

log = logging.getLogger(__name__)

# Steps as (module_path, callable_attr, label)
# Each step's main() now accepts an optional station_group kwarg.
STEP_MODULES = [
    ("ville_ia_etl.01_download",          "01 — Download raw CSVs"),
    ("ville_ia_etl.02_parse_daily",       "02 — Parse daily data"),
    ("ville_ia_etl.03_parse_hourly",      "03 — Parse & aggregate hourly"),
    ("ville_ia_etl.04_merge",             "04 — Merge daily + hourly"),
    ("ville_ia_etl.05_engineer_features", "05 — Engineer features"),
    ("ville_ia_etl.06_label_target",      "06 — Label heatwave target"),
    ("ville_ia_etl.07_quality_report",    "07 — Quality report"),
]


def main():
    parser = argparse.ArgumentParser(description="VILLE_IA ETL Pipeline")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip step 01 (download). Assumes raw data already exists.",
    )
    parser.add_argument(
        "--station",
        type=str,
        default=None,
        help="Run only the station group with this slug (e.g. WTA_mctavish).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Resolve station groups to process
    if args.station:
        matched = [g for g in STATION_GROUPS if g["slug"] == args.station]
        if not matched:
            valid = ", ".join(g["slug"] for g in STATION_GROUPS)
            parser.error(f"Unknown station '{args.station}'. Choose from: {valid}")
        groups = matched
    else:
        groups = STATION_GROUPS

    steps = STEP_MODULES if not args.skip_download else STEP_MODULES[1:]
    total_start = time.time()

    for group in groups:
        log.info("")
        log.info("=" * 65)
        log.info(f"STATION GROUP: {group['label']}  ({group['slug']})")
        log.info("=" * 65)

        for module_path, label in steps:
            log.info("")
            log.info(f"{'─' * 50}")
            log.info(f"▶  {label}")
            log.info(f"{'─' * 50}")

            step_start = time.time()
            try:
                import importlib
                mod = importlib.import_module(module_path)
                mod.main(station_group=group)
            except Exception as e:
                log.error(f"✗  {label} failed for {group['slug']}: {e}")
                raise
            elapsed = time.time() - step_start
            log.info(f"✓  {label}  ({elapsed:.1f}s)")

    total = time.time() - total_start
    log.info("")
    log.info("=" * 65)
    log.info(f"Pipeline complete in {total:.1f}s  ✓")
    log.info("=" * 65)


if __name__ == "__main__":
    main()
