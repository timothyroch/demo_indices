import time
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

import requests
from fastapi.params import Query

from ..constants.weather import LAYERS
from ..providers.open_meteo import open_meteo_provider

GEOMET_WMS_API = "https://geo.weather.gc.ca/geomet/"
GEOMET_OGC_API = "https://api.weather.gc.ca/collections/climate-daily/items"
_STATION_SEARCH_DELTA = 0.2
_COORD_ROUND_PRECISION = 2


_current_weather_cache: dict[tuple[float, float], dict] = {}
_CURRENT_WEATHER_TTL = 300


def get_cached_weather_data(lat: float, lng: float) -> dict:
    entry = _current_weather_cache.get((lat, lng))
    if entry and (time.time() - entry["timestamp"]) < _CURRENT_WEATHER_TTL:
        return {
            "temperature": entry["temperature"],
            "precipitation": entry["precipitation"],
            "humidity": entry.get("humidity"),
            "source": entry.get("source", "Unknown"),
        }
    data = _get_weather_data(lat, lng)
    return {
        "temperature": data["temperature"],
        "precipitation": data["precipitation"],
        "humidity": data.get("humidity"),
        "source": data.get("source", "Unknown"),
    }


def _get_weather_data(
    lat: float = Query(...),
    lng: float = Query(...),
):
    try:
        openmeteo_temperature, openmeteo_precipitation = (
            open_meteo_provider.get_daily_weather(
                lat,
                lng,
            )
        )

        temperature_from_wms = float(openmeteo_temperature)
        precipitation_from_wms = float(openmeteo_precipitation)
        humidity_from_wms = None
        source = "Open-Meteo"
    except (requests.RequestException, ValueError, KeyError, TypeError):
        temperature_from_wms = get_feature_info(lat, lng, LAYERS["temperature"])
        precipitation_from_wms = get_feature_info(lat, lng, LAYERS["precipitation_24h"])
        humidity_from_wms = get_feature_info(lat, lng, LAYERS["humidity"])
        source = "Geomet"

    data = {
        "temperature": float(temperature_from_wms)
        if temperature_from_wms is not None
        else 0.0,
        "precipitation": float(precipitation_from_wms)
        if precipitation_from_wms is not None
        else 0.0,
        "humidity": float(humidity_from_wms) if humidity_from_wms is not None else None,
        "source": source,
    }

    _current_weather_cache[(lat, lng)] = {**data, "timestamp": time.time()}

    return data


def get_historical_weather(lat: float, lng: float, days: int = 6) -> list[dict]:
    lat_r = round(lat, _COORD_ROUND_PRECISION)
    lng_r = round(lng, _COORD_ROUND_PRECISION)
    today = datetime.now(timezone.utc).date()
    return list(_cached_historical_weather(lat_r, lng_r, days, today))


@lru_cache(maxsize=256)
def _cached_historical_weather(
    lat_r: float, lng_r: float, days: int, today: date
) -> tuple:
    today_utc = datetime.combine(today, datetime.min.time()).replace(
        hour=12, tzinfo=timezone.utc
    )
    yesterday_utc = today_utc - timedelta(days=1)
    start_date = today_utc - timedelta(days=days)
    observations = _fetch_daily_observations(lat_r, lng_r, start_date, yesterday_utc)

    records = []
    for offset in range(days - 1, -1, -1):
        date = yesterday_utc - timedelta(days=offset)
        date_key = date.strftime("%Y-%m-%d")
        record = {
            "date": date,
            **observations.get(date_key, {"temperature": 0.0, "precipitation": 0.0}),
        }
        records.append(record)
    return tuple(records)


def _fetch_daily_observations(
    lat: float,
    lng: float,
    start: datetime,
    end: datetime,
) -> dict[str, dict]:
    try:
        start_date = start.strftime("%Y-%m-%d")
        end_date = end.strftime("%Y-%m-%d")
        historical_data = open_meteo_provider.get_historical_weather_archive(
            lat=lat,
            lng=lng,
            start_date=start_date,
            end_date=end_date,
        )
        if not historical_data:
            raise ValueError("Open-Meteo archive returned no data")
        return {
            f.date[:10]: {
                "temperature": float(f.temperature_mean),
                "precipitation": float(f.precipitation),
            }
            for f in historical_data
        }
    except (requests.RequestException, ValueError, KeyError, TypeError):
        delta = _STATION_SEARCH_DELTA
        bbox = f"{lng - delta},{lat - delta},{lng + delta},{lat + delta}"
        params = {
            "bbox": bbox,
            "datetime": f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}",
            "limit": 500,
            "f": "json",
        }
        r = requests.get(GEOMET_OGC_API, params=params, timeout=15)
        r.raise_for_status()
        features = r.json().get("features", [])

        best_temp: dict[str, tuple[float, float]] = {}  # date_key -> (dist, temp)
        best_precip: dict[str, tuple[float, float]] = {}  # date_key -> (dist, precip)
        for feature in features:
            props = feature.get("properties", {})
            local_date = props.get("LOCAL_DATE")
            if local_date is None:
                continue

            date_key = str(local_date)[:10]
            coords = feature.get("geometry", {}).get("coordinates", [None, None])
            station_lng, station_lat = coords[0], coords[1]
            if station_lat is None or station_lng is None:
                continue

            dist = (station_lat - lat) ** 2 + (station_lng - lng) ** 2

            mean_temp = props.get("MEAN_TEMPERATURE")
            if mean_temp is not None:
                if date_key not in best_temp or dist < best_temp[date_key][0]:
                    best_temp[date_key] = (dist, float(mean_temp))

            total_precip = props.get("TOTAL_PRECIPITATION")
            if total_precip is not None:
                if date_key not in best_precip or dist < best_precip[date_key][0]:
                    best_precip[date_key] = (dist, float(total_precip))

        result = {}
        return result


def get_feature_info(lat: float, lng: float, layer: str):
    delta = _STATION_SEARCH_DELTA
    bbox = f"{lat - delta},{lng - delta},{lat + delta},{lng + delta}"
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": layer,
        "QUERY_LAYERS": layer,
        "CRS": "EPSG:4326",
        "BBOX": bbox,
        "WIDTH": 10,
        "HEIGHT": 10,
        "I": 5,
        "J": 5,
        "INFO_FORMAT": "application/json",
    }
    r = requests.get(GEOMET_WMS_API, params=params)
    r.raise_for_status()
    features = r.json().get("features")
    return features[0]["properties"]["value"] if features else None
