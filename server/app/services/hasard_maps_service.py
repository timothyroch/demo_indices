from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..constants.filenames import RISK_ZONE_FILES
from ..constants.partner_city import GEOJSON_PROPERTY_PARTNER_CITY
from ..models.fluvial_floods_model import predict_fluvial_flood
from ..models.pluvial_floods_model import predict_pluvial_flood
from ..providers.open_meteo import open_meteo_provider
from ..risk_assessors.heatwave import HeatwaveAssessor
from ..risk_assessors.snow import assess_snow_risk
from ..services.water_levels_service import get_active_stations, get_daily_wl_history
from ..services.weather_service import get_cached_weather_data, get_historical_weather
from ..utils.geometry_utils import centroid_wgs84
from ..utils.scoring import combined_humidex, combined_probability
from .partner_city_access_service import filter_features_by_partner_city

DATA_DIR = Path(__file__).parent.parent / "data"

# Cache en mémoire (TTL 30 min)
_all_hazards_cache: dict | None = None
_all_hazards_timestamp: float = 0.0

CACHE_TTL_SECONDS = 1800
ALL_HAZARDS: list[str] = ["pluvial", "crues", "canicules", "neige"]

_heatwave_assessor = HeatwaveAssessor()


def _load_features_raw(hazard_name: str) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    city_files = RISK_ZONE_FILES.get(hazard_name, {})

    for city, filename in city_files.items():
        path = DATA_DIR / filename
        if not path.exists():
            print(f"[load] Missing file: {path}")
            continue

        raw = json.loads(path.read_text(encoding="utf-8"))

        for feat in raw.get("features", []):
            props = feat.setdefault("properties", {})
            props[GEOJSON_PROPERTY_PARTNER_CITY] = city
            features.append(feat)

    return features


def _build_hazard_props_index(hazard_name: str) -> dict[str, dict]:
    props_dict: dict[str, dict] = {}
    for feat in _load_features_raw(hazard_name):
        props = feat.get("properties") or {}
        adidu = props.get("ADIDU")
        if adidu is not None:
            props_dict[str(adidu)] = props
    return props_dict


def _build_score_index(hazard_name: str) -> dict[str, float]:
    """Extracts risk scores (score_risque) for each adidu in a hazard."""
    score_dict: dict[str, float] = {}
    for feat in _load_features_raw(hazard_name):
        props = feat.get("properties") or {}
        adidu = props.get("ADIDU")
        if adidu is not None:
            try:
                score = float(props.get("score_risque", 0.0))
            except (TypeError, ValueError):
                score = 0.0
            score_dict[str(adidu)] = score
    return score_dict


def _display_band(score: float, hazard: str) -> str:
    if hazard == "canicules":
        if score < 29:
            return "vert"
        if score < 39:
            return "jaune"
        if score < 45:
            return "orange"
        return "rouge"
    else:
        if score < 20:
            return "vert"
        if score < 50:
            return "orange"
        return "rouge"


def _geographic_center(
    centroids: list[tuple[float, float]],
) -> tuple[float, float] | None:
    """Retourne le centroïde moyen de tous les centroïdes valides."""
    if not centroids:
        return None
    avg_lat = sum(c[0] for c in centroids) / len(centroids)
    avg_lng = sum(c[1] for c in centroids) / len(centroids)
    return (avg_lat, avg_lng)


def snap_to_grid(
    lat: float, lng: float, grid_step: float = 0.05
) -> tuple[float, float]:
    """
    Snaps a latitude and longitude to the nearest grid point
    based on the provided grid step resolution.
    """
    snapped_lat = round(lat / grid_step) * grid_step
    snapped_lng = round(lng / grid_step) * grid_step
    return (snapped_lat, snapped_lng)


def _build_spatial_mappings(
    base_features: list[dict], active_stations: list[dict]
) -> tuple:
    """Groups territories into weather grids and finds the nearest water station."""
    mappings = {}
    unique_stations = set()
    unique_grids = set()
    valid_centroids = []

    for feat in base_features:
        props = feat.get("properties") or {}
        adidu = str(props.get("ADIDU", ""))
        centroid = centroid_wgs84(feat.get("geometry") or {})

        if not adidu or not centroid:
            continue

        lat, lng = centroid
        valid_centroids.append(centroid)
        grid_pt = snap_to_grid(lat, lng)

        nearest_station = min(
            active_stations,
            key=lambda s: (s["latitude"] - grid_pt[0]) ** 2
            + (s["longitude"] - grid_pt[1]) ** 2,
        )
        station_id = nearest_station["id"]

        mappings[adidu] = {
            "lat": lat,
            "lng": lng,
            "station_id": station_id,
            "grid_pt": grid_pt,
        }
        unique_stations.add(station_id)
        unique_grids.add(grid_pt)

    return mappings, unique_stations, unique_grids, valid_centroids


def _fetch_concurrent_data(unique_stations: set, unique_grids: set) -> tuple:
    """Fetches water levels, historical weather, and current weather concurrently."""
    wl_data = {}
    hw_data = {}
    curr_weather = {}

    with ThreadPoolExecutor(max_workers=20) as executor:
        wl_futures = {
            executor.submit(get_daily_wl_history, station_id=s_id, days=7): s_id
            for s_id in unique_stations
        }
        hw_futures = {
            executor.submit(get_historical_weather, pt[0], pt[1], days=6): pt
            for pt in unique_grids
        }
        curr_futures = {
            executor.submit(get_cached_weather_data, pt[0], pt[1]): pt
            for pt in unique_grids
        }

        for future in as_completed(wl_futures):
            wl_data[wl_futures[future]] = future.result()
        for future in as_completed(hw_futures):
            hw_data[hw_futures[future]] = future.result()
        for future in as_completed(curr_futures):
            curr_weather[curr_futures[future]] = future.result()

    return wl_data, hw_data, curr_weather


def _fetch_macro_forecasts(valid_centroids: list, sample_adidu: str) -> tuple:
    """Fetches heatwave and snow forecasts for the geographic center of the map."""
    center = _geographic_center(valid_centroids)
    heatwave_forecasts = open_meteo_provider.get_heatwave_forecast(
        center[0], center[1], days=7
    )
    snow_forecasts = open_meteo_provider.get_snow_forecast(center[0], center[1], days=8)

    heatwave_assessment = _heatwave_assessor.assess(heatwave_forecasts, sample_adidu)
    if not heatwave_assessment.daily_details:
        return 0.0, 0.0
    raw_heatwave = float(heatwave_assessment.daily_details[0].raw_prediction_value)

    snow_assessment = assess_snow_risk(snow_forecasts, sample_adidu)
    if not snow_assessment.daily_details:
        return 0.0, 0.0
    raw_snow = float(snow_assessment.daily_details[0].raw_prediction_value)

    return raw_heatwave, raw_snow


def _precalculate_ml_probabilities(
    mappings: dict,
    historical_weather_data: dict,
    water_level_data: dict,
    curr_weather: dict,
) -> tuple:
    """Runs the heavy ML models once per unique grid/station pair."""
    raw_pluvial = {}
    raw_fluvial = {}

    unique_pairs = set((m["station_id"], m["grid_pt"]) for m in mappings.values())

    for station_id, grid_pt in unique_pairs:
        lat, lng = grid_pt
        hist_weather = historical_weather_data.get(grid_pt)
        water_level = water_level_data.get(station_id)
        curr_w = curr_weather.get(grid_pt, {"temperature": 0.0, "precipitation": 0.0})

        r_pluv = predict_pluvial_flood(
            lat, lng, curr_w["temperature"], curr_w["precipitation"], hist_weather
        )
        r_fluv = predict_fluvial_flood(
            lat,
            lng,
            curr_w["temperature"],
            curr_w["precipitation"],
            water_level,
            hist_weather,
        )

        raw_pluvial[grid_pt] = r_pluv
        raw_fluvial[(station_id, grid_pt)] = r_fluv

    return raw_pluvial, raw_fluvial


def _assemble_geojson_features(
    base_features: list,
    mappings: dict,
    score_indexes: dict,
    raw_pluvial: dict,
    raw_fluvial: dict,
    raw_heatwave: float,
    raw_snow: float,
) -> list:
    """Combines pre-calculated probabilities with individual territory risk scores."""
    computed_features = []

    for feat in base_features:
        props = feat.get("properties") or {}
        adidu = str(props.get("ADIDU", ""))
        mapping = mappings.get(adidu)

        # Check if val_crues is valid (1-5) for this zone
        is_valid_val_crues = True
        val_crues = props.get("val_crues")
        try:
            val_crues_float = float(val_crues)
            is_valid_val_crues = 1 <= val_crues_float <= 5
        except (TypeError, ValueError):
            is_valid_val_crues = False

        hazards = {}
        for hazard in ALL_HAZARDS:
            zone_score = score_indexes[hazard].get(adidu, 0.0)
            combined_val, raw_val = 0.0, 0.0

            if mapping:
                station_id = mapping["station_id"]
                grid_pt = mapping["grid_pt"]

                if hazard == "pluvial":
                    raw_val = raw_pluvial.get(grid_pt, 0.0)
                    combined_val = combined_probability(zone_score, raw_val)
                elif hazard == "crues":
                    raw_val = raw_fluvial.get((station_id, grid_pt), 0.0)
                    # For crues, only calculate probability if val_crues is valid (1-5)
                    if is_valid_val_crues:
                        combined_val = combined_probability(zone_score, raw_val)
                    else:
                        raw_val = 0.0
                        combined_val = 0.0
                elif hazard == "canicules":
                    raw_val = raw_heatwave
                    combined_val = combined_humidex(zone_score, raw_val)
                elif hazard == "neige":
                    raw_val = raw_snow
                    combined_val = combined_probability(zone_score, raw_val)

            if hazard == "canicules":
                final_m, raw_m = round(combined_val, 2), round(raw_val, 2)
            else:
                final_m, raw_m = (
                    round(max(0.0, min(1.0, combined_val)) * 100, 2),
                    round(raw_val, 4),
                )

            hazards[hazard] = {
                "zone_risk_score": round(zone_score, 2),
                "raw_probability": raw_m,
                "combined_probability": final_m,
                "display_band": _display_band(final_m, hazard),
            }

        computed_features.append(
            {
                "type": "Feature",
                "geometry": feat.get("geometry"),
                "properties": {
                    "adidu": props.get("ADIDU"),
                    "partner_city": props.get(GEOJSON_PROPERTY_PARTNER_CITY),
                    "pct_65_plus": props.get("pct_65_plus"),
                    "revenu_median_menage": props.get("revenu_median_menage"),
                    "gini": props.get("gini"),
                    "logement_reparations_majeures": props.get(
                        "logement_reparations_majeures"
                    ),
                    "val_crues": val_crues,
                    "hazards": hazards,
                },
            }
        )

    return computed_features


def _compute_all_hazards_full() -> dict:
    global _all_hazards_cache, _all_hazards_timestamp

    now = time.time()
    if _all_hazards_cache and (now - _all_hazards_timestamp) < CACHE_TTL_SECONDS:
        return _all_hazards_cache

    print("[Hazards Compute] Starting full map generation pipeline...")
    t_start = time.time()

    # 1. Load Base Geometries and Risk Scores
    base_features = _load_features_raw("pluvial")
    score_indexes = {hazard: _build_score_index(hazard) for hazard in ALL_HAZARDS}

    print(
        f"[Hazards Compute] Phase 1/5: Loaded {len(base_features)} base territories in \
            {time.time() - t_start:.2f}s"
    )
    t_step = time.time()

    # 2. Spatial Indexing
    mappings, unique_stations, unique_grids, valid_centroids = _build_spatial_mappings(
        base_features, get_active_stations()
    )
    print(
        f"[Hazards Compute] Phase 2/5: Mapped to {len(unique_stations)} stations and \
            {len(unique_grids)} grids in {time.time() - t_step:.2f}s"
    )
    t_step = time.time()

    # 3. Concurrent API Fetching
    wl_data, hw_data, curr_weather = _fetch_concurrent_data(
        unique_stations, unique_grids
    )

    sample_adidu = (
        str(base_features[0].get("properties", {}).get("ADIDU", ""))
        if base_features
        else ""
    )
    raw_heatwave, raw_snow = _fetch_macro_forecasts(valid_centroids, sample_adidu)

    print(
        f"[Hazards Compute] Phase 3/5: API network fetching completed in \
            {time.time() - t_step:.2f}s"
    )
    t_step = time.time()

    # 4. ML Inference
    raw_pluvial, raw_fluvial = _precalculate_ml_probabilities(
        mappings, hw_data, wl_data, curr_weather
    )
    print(
        f"[Hazards Compute] Phase 4/5: ML inference pre-calculated in \
              {time.time() - t_step:.2f}s"
    )
    t_step = time.time()

    # 5. Assembly and Formatting
    computed_zone_features = _assemble_geojson_features(
        base_features,
        mappings,
        score_indexes,
        raw_pluvial,
        raw_fluvial,
        raw_heatwave,
        raw_snow,
    )
    print(
        f"[Hazards Compute] Phase 5/5: GeoJSON assembly completed in \
            {time.time() - t_step:.2f}s"
    )
    print(
        f"[Hazards Compute] Total pipeline execution time: {time.time() - t_start:.2f}s"
    )

    result = {"type": "FeatureCollection", "features": computed_zone_features}
    _all_hazards_cache, _all_hazards_timestamp = result, time.time()
    return result


def compute_all_hazard_zones(partner_city: str | None = None) -> dict:
    full = _compute_all_hazards_full()
    if partner_city is None:
        return full
    return filter_features_by_partner_city(full, partner_city)
