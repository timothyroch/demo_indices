"""
VILLE_IA — Step 01: Download Raw CSVs from Environment Canada
==============================================================

Downloads daily + hourly weather data for each station group defined
in ``config.STATION_GROUPS``.  Stores files under station-specific
sub-folders (``raw_data/<slug>/daily/``, ``raw_data/<slug>/hourly/``).

Skips already-downloaded files (resumable).

Usage:
    poetry run download
    python -m ville_ia_etl.01_download
"""

import time
import logging

import requests
from tqdm import tqdm

from ville_ia_etl.config import (
    STATION_GROUPS,
    BASE_URL, TIMEFRAME_DAILY, TIMEFRAME_HOURLY,
    REQUEST_TIMEOUT, DELAY_BETWEEN_REQUESTS, MAX_RETRIES, RETRY_BACKOFF,
    get_paths,
)

log = logging.getLogger(__name__)


def download_file(url, dest):
    """Download a single CSV with retry logic.  Skips if file exists."""
    if dest.exists() and dest.stat().st_size > 500:
        return True

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            if len(resp.content) < 200:
                log.warning(f"Empty response for {dest.name} (attempt {attempt})")
                if attempt == MAX_RETRIES:
                    return False
                time.sleep(DELAY_BETWEEN_REQUESTS * RETRY_BACKOFF * attempt)
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
            return True

        except requests.RequestException as e:
            log.warning(f"Download failed: {dest.name}: {e} (attempt {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                time.sleep(DELAY_BETWEEN_REQUESTS * RETRY_BACKOFF * attempt)

    return False


def download_daily(station_group, paths):
    """Download daily CSVs for a station group, one file per year."""
    files = []
    raw_daily_dir = paths["raw_daily_dir"]

    for station in station_group["stations"]:
        sid = station["id"]
        name = station["name"]
        years = list(range(station["start"], station["end"] + 1))
        log.info(f"Daily — {name} (ID {sid}): {station['start']}–{station['end']}")

        for year in tqdm(years, desc=f"Daily {sid}", unit="year"):
            url = BASE_URL.format(
                station_id=sid, year=year, month=1, timeframe=TIMEFRAME_DAILY,
            )
            dest = raw_daily_dir / f"daily_{sid}_{year}.csv"
            if download_file(url, dest):
                files.append(dest)
            else:
                log.error(f"Failed to download daily {year} from {name}")
            time.sleep(DELAY_BETWEEN_REQUESTS)

    log.info(f"Daily total: {len(files)} files downloaded")
    return files


def download_hourly(station_group, paths):
    """Download hourly CSVs for a station group, one file per month."""
    files = []
    raw_hourly_dir = paths["raw_hourly_dir"]

    for station in station_group["stations"]:
        sid = station["id"]
        name = station["name"]
        tasks = [
            (y, m)
            for y in range(station["start"], station["end"] + 1)
            for m in range(1, 13)
        ]
        log.info(f"Hourly — {name} (ID {sid}): {station['start']}–{station['end']} ({len(tasks)} files)")

        for year, month in tqdm(tasks, desc=f"Hourly {sid}", unit="month"):
            url = BASE_URL.format(
                station_id=sid, year=year, month=month, timeframe=TIMEFRAME_HOURLY,
            )
            dest = raw_hourly_dir / f"hourly_{sid}_{year}_{month:02d}.csv"
            if download_file(url, dest):
                files.append(dest)
            else:
                log.warning(f"Failed: hourly {year}-{month:02d} from {name}")
            time.sleep(DELAY_BETWEEN_REQUESTS)

    log.info(f"Hourly total: {len(files)} files downloaded")
    return files


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

        log.info("=" * 60)
        log.info(f"VILLE_IA — Step 01: Download Weather Data — {group['label']}")
        for s in group["stations"]:
            log.info(f"  Station {s['id']} ({s['name']}): {s['start']}–{s['end']}")
        log.info(f"  Output → raw_data/{slug}/")
        log.info("=" * 60)

        daily_files = download_daily(group, paths)
        hourly_files = download_hourly(group, paths)

        log.info(
            f"Download complete for {slug} — {len(daily_files)} daily + "
            f"{len(hourly_files)} hourly files"
        )

    log.info("Next step:  poetry run process -- --skip-download")


if __name__ == "__main__":
    main()
