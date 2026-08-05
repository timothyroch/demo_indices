"""
VILLE_IA — Step 06: Label Heatwave Target
==========================================

Reads ``processed/<slug>/features.csv``, identifies heatwave events using
INSPQ methodology (3-day moving averages of Tmax and Tmin), creates
a 3-day look-ahead prediction target, exports ``processed/<slug>/dataset.csv``.

INSPQ definition (Section 2.1.1):
    «Une vague de chaleur extrême est définie comme une période d'au minimum
    trois jours consécutifs pendant laquelle les moyennes mobiles sur trois
    jours des températures maximales et minimales atteignent les valeurs
    seuils de chaleur extrême.»

Implementation:
    - tmax_roll_3d and tmin_roll_3d (trailing 3-day means) are computed in
      step 05 (engineer_features).
    - When tmax_roll_3d >= 33 AND tmin_roll_3d >= 20, the 3-day window
      ending at that day meets the criteria.
    - All 3 days in that window are labeled as heatwave_event = 1.
    - No separate consecutive-streak check is needed — the rolling average
      already encodes the 3-day requirement.

Usage:
    python -m ville_ia_etl.06_label_target
"""

import logging

import numpy as np
import pandas as pd

from ville_ia_etl.config import (
    STATION_GROUPS, get_paths,
    HEATWAVE_TMAX_THRESHOLD, HEATWAVE_TMIN_THRESHOLD,
    HEATWAVE_HUMIDEX_THRESHOLD, HEATWAVE_CONSECUTIVE_DAYS,
    LOOKAHEAD_DAYS,
)

log = logging.getLogger(__name__)


def label_target(paths):
    """Identify heatwave events and create prediction target."""
    log.info("Reading features data...")
    df = pd.read_csv(paths["features_csv"], parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # ------------------------------------------------------------------
    # Step 1: Find trigger days — checking the Strict Combined Rule
    # Use the specific rolling windows matching HEATWAVE_CONSECUTIVE_DAYS
    # ------------------------------------------------------------------
    w = HEATWAVE_CONSECUTIVE_DAYS
    
    # Thermal rule: Tmax >= threshold AND Tmin >= threshold
    thermal_trigger = (
        (df[f"tmax_roll_{w}d"] >= HEATWAVE_TMAX_THRESHOLD) &
        (df[f"tmin_roll_{w}d"] >= HEATWAVE_TMIN_THRESHOLD)
    )
    
    # Humidex rule: Humidex >= threshold
    humidex_trigger = df[f"humidex_roll_{w}d"] >= HEATWAVE_HUMIDEX_THRESHOLD
    
    df["hot_day"] = (thermal_trigger | humidex_trigger).astype(int)

    trigger_count = df["hot_day"].sum()
    log.info(
        f"Trigger days ({w}d-avg (Tmax>={HEATWAVE_TMAX_THRESHOLD} & Tmin>={HEATWAVE_TMIN_THRESHOLD}) "
        f"OR Humidex>={HEATWAVE_HUMIDEX_THRESHOLD}): {trigger_count}"
    )

    # ------------------------------------------------------------------
    # Step 2: Back-label heatwave events.
    # Each trigger day marks the END of a consecutive window. 
    # ------------------------------------------------------------------
    df["heatwave_event"] = 0

    back_steps = HEATWAVE_CONSECUTIVE_DAYS - 1
    for i in df.index[df["hot_day"] == 1]:
        start_idx = max(0, i - back_steps)
        df.loc[start_idx:i, "heatwave_event"] = 1

    total_hw_days = df["heatwave_event"].sum()
    log.info(f"Heatwave event days (Strict Combined method): {total_hw_days}")

    # ------------------------------------------------------------------
    # Step 3: Look-ahead target — is a heatwave coming in next N days?
    # ------------------------------------------------------------------
    target = np.zeros(len(df), dtype=int)
    for i in range(len(df) - LOOKAHEAD_DAYS):
        window = df["heatwave_event"].iloc[i + 1: i + 1 + LOOKAHEAD_DAYS]
        if window.any():
            target[i] = 1
    df["target_heatwave_3d"] = target

    # ------------------------------------------------------------------
    # Step 4: Drop last N rows (cannot compute their target)
    # ------------------------------------------------------------------
    df = df.iloc[:-LOOKAHEAD_DAYS].reset_index(drop=True)

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    pos = df["target_heatwave_3d"].sum()
    neg = len(df) - pos
    pct = 100 * pos / len(df) if len(df) > 0 else 0

    log.info(f"Dataset: {len(df)} rows")
    log.info(f"Target class balance:  positive={pos} ({pct:.2f}%)  negative={neg}")

    # Per-year breakdown
    yearly = df.groupby(df["date"].dt.year)["heatwave_event"].sum()
    for year, count in yearly.items():
        if count > 0:
            bar = "█" * int(count)
            log.info(f"  {year}: {int(count)} heatwave days  {bar}")

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
        log.info(f"VILLE_IA — Step 06: Label Heatwave Target — {group['label']}")

        df = label_target(paths)

        paths["processed_dir"].mkdir(parents=True, exist_ok=True)
        df.to_csv(paths["dataset_csv"], index=False)
        log.info(f"Saved → {paths['dataset_csv']}")


if __name__ == "__main__":
    main()
