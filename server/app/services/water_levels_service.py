import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

IWLS_URL = "https://api-iwls.dfo-mpo.gc.ca/api/v1/stations"
OPEN_METEO_FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"

# Unified Station Cache (24 hours)
_ACTIVE_STATIONS_CACHE: list[dict] = []
_ACTIVE_STATIONS_TIMESTAMP: float = 0.0
STATIONS_TTL_SECONDS = 86400  # 24 hours

STATIONS_TO_IGNORE = {
    "5cebf1e03d0f4a073c4bbe04",  # Varennes
    "5dd3064de0fdc4b9b4be664b",  # Barrage Fryer
    "5dd3064fe0fdc4b9b4be69f8",  # Saint-Jean-sur-Richelieu
    "5cebf1e43d0f4a073c4bc48d",  # Pointe-des-Cascades
    "5cebf1e03d0f4a073c4bbe1b",  # Contrecoeur IOC
    "5dd3064de0fdc4b9b4be6647",  # Lanoraie
    "5cebf1e03d0f4a073c4bbe32",  # Sorel
    "5cebf1e03d0f4a073c4bbe49",  # Lac Saint-Pierre
    "5cebf1e03d0f4a073c4bbd76",  # Summerstown
}


def get_active_stations() -> list[dict]:
    global _ACTIVE_STATIONS_CACHE, _ACTIVE_STATIONS_TIMESTAMP
    now = time.time()

    if (
        _ACTIVE_STATIONS_CACHE
        and (now - _ACTIVE_STATIONS_TIMESTAMP) < STATIONS_TTL_SECONDS
    ):
        return _ACTIVE_STATIONS_CACHE

    try:
        response = requests.get(IWLS_URL, timeout=10)
        response.raise_for_status()
        _ACTIVE_STATIONS_CACHE = [
            s
            for s in response.json()
            if s.get("operating") is True
            and s.get("latitude")
            and s.get("longitude")
            and s.get("id") not in STATIONS_TO_IGNORE
        ]
        _ACTIVE_STATIONS_TIMESTAMP = now
        return _ACTIVE_STATIONS_CACHE
    except Exception as exc:
        print(f"[IWLS] Failed to fetch station list: {exc}")
        return _ACTIVE_STATIONS_CACHE if _ACTIVE_STATIONS_CACHE else []


def get_nearest_station(lat: float, lng: float) -> dict | None:
    stations = get_active_stations()
    if not stations:
        return None

    # Euclidean distance
    nearest = min(
        stations, key=lambda s: (s["latitude"] - lat) ** 2 + (s["longitude"] - lng) ** 2
    )
    return {
        "id": nearest["id"],
        "name": nearest.get("officialName") or nearest.get("name", "Unknown"),
        "latitude": nearest["latitude"],
        "longitude": nearest["longitude"],
    }


def _resolve_station(
    lat: float | None,
    lng: float | None,
    station_id: str | None,
) -> dict | None:
    if station_id:
        return {"id": station_id, "name": "Unknown station"}
    if lat is not None and lng is not None:
        return get_nearest_station(lat, lng)
    return None


def get_latest_water_level(
    lat: float | None = None,
    lng: float | None = None,
    station_id: str | None = None,
) -> dict | None:
    station = _resolve_station(lat, lng, station_id)
    if station is None:
        return None

    now = datetime.now(timezone.utc)
    from_dt = now - timedelta(hours=2)

    params = {
        "time-series-code": "wlo",
        "resolution": "SIXTY_MINUTES",
        "from": from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    try:
        response = requests.get(
            f"{IWLS_URL}/{station['id']}/data",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            return None

        latest = max(data, key=lambda x: x["eventDate"])
        return {
            "value": float(latest["value"]),
            "station_id": station["id"],
            "station_name": station["name"],
            "timestamp": latest["eventDate"],
        }

    except Exception as exc:
        print(f"[IWLS] Failed to fetch water level for {station['id']}: {exc}")
        return None


def get_hourly_wl_history(
    lat: float | None = None,
    lng: float | None = None,
    station_id: str | None = None,
    hours_back: int = 72,
) -> list[dict]:
    station = _resolve_station(lat=lat, lng=lng, station_id=station_id)
    if station is None:
        return []

    now = datetime.now(timezone.utc)
    from_dt = now - timedelta(hours=hours_back)

    params = {
        "time-series-code": "wlo",
        "resolution": "SIXTY_MINUTES",
        "from": from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    try:
        response = requests.get(
            f"{IWLS_URL}/{station['id']}/data",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        rows = [
            {
                "timestamp": row["eventDate"],
                "value": float(row["value"]),
                "station_id": station["id"],
                "station_name": station["name"],
            }
            for row in data
            if row.get("value") is not None
        ]

        if not rows:
            print(f"[IWLS] No water level data returned for station {station['id']}")
            return []

        return sorted(rows, key=lambda x: x["timestamp"])

    except Exception as exc:
        print(
            f"[IWLS] Failed to fetch water level history for {station.get('id')}: {exc}"
        )
        return []


def get_daily_wl_history(
    lat: float | None = None,
    lng: float | None = None,
    station_id: str | None = None,
    days: int = 7,
) -> pd.Series:
    """
    Fetches hourly water levels and aggregates them into a daily mean.
    Can be called with either (lat, lng) or a direct station_id.
    """
    raw = get_hourly_wl_history(
        lat=lat, lng=lng, station_id=station_id, hours_back=days * 24
    )
    if not raw:
        return pd.Series(dtype=float)

    df = pd.DataFrame(raw)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.date.astype(str)

    daily = df.groupby("date")["value"].mean().sort_index()
    return daily


def get_water_level_forecast(
    lat: float,
    lng: float,
    days: int = 7,
    station_id: str | None = None,
) -> list[dict]:
    station = _resolve_station(lat, lng, station_id)

    current_water_level: float | None = None
    station_name = station["name"] if station else "Unknown station"
    if station:
        obs = get_latest_water_level(station_id=station["id"])
        if obs:
            current_water_level = obs["value"]

    # --- river discharge forecast from Open-Meteo ---
    discharge_series = _fetch_river_discharge(lat, lng, days)

    if not discharge_series:
        # Fallback: flat forecast
        today = datetime.now(timezone.utc).date()
        return [
            {
                "date": (today + timedelta(days=i)).isoformat(),
                "water_level": current_water_level,
                "river_discharge": None,
                "station_name": station_name,
            }
            for i in range(days)
        ]

    # --- scale discharge to water-level using Manning approximation ---
    forecast = _discharge_to_water_level(
        discharge_series, current_water_level, station_name
    )
    return forecast[:days]


def _fetch_river_discharge(lat: float, lng: float, days: int) -> list[dict]:
    try:
        params = {
            "latitude": lat,
            "longitude": lng,
            "daily": "river_discharge",
            "forecast_days": min(days, 16),  # API cap
        }
        response = requests.get(OPEN_METEO_FLOOD_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        dates = data.get("daily", {}).get("time", [])
        discharges = data.get("daily", {}).get("river_discharge", [])

        return [
            {"date": d, "river_discharge": float(q) if q is not None else None}
            for d, q in zip(dates, discharges)
        ]
    except Exception as exc:
        print(f"[Open-Meteo Flood] Failed to fetch river discharge: {exc}")
        return []


def _discharge_to_water_level(
    discharge_series: list[dict],
    anchor_level: float | None,
    station_name: str,
) -> list[dict]:
    """
    Convert a discharge series (m³/s) to estimated water levels (m).

    Uses Manning's simplified relationship H ∝ Q^0.5 to scale around the
    anchor observation.  If ``anchor_level`` is None, discharge values are
    returned as-is (scaled to a nominal 1 m reference so the series is still
    meaningful relative to itself).
    """
    valid = [
        d["river_discharge"]
        for d in discharge_series
        if d["river_discharge"] is not None
    ]
    if not valid:
        return [
            {**d, "water_level": anchor_level, "station_name": station_name}
            for d in discharge_series
        ]

    q_ref = valid[0]  # first forecasted day as reference
    h_ref = anchor_level if anchor_level is not None else 1.0

    result = []
    for entry in discharge_series:
        q = entry["river_discharge"]
        if q is None or q_ref is None or q_ref <= 0:
            wl = anchor_level
        else:
            # H2/H1 ≈ (Q2/Q1)^0.5
            wl = round(h_ref * ((q / q_ref) ** 0.5), 3)

        result.append(
            {
                "date": entry["date"],
                "water_level": wl,
                "river_discharge": q,
                "station_name": station_name,
            }
        )
    return result
