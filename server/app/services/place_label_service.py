"""
Resolve a short city / neighbourhood label from coordinates.

Uses Mapbox Geocoding (same MAPBOX_API_KEY as the frontend map) when set;
otherwise OpenStreetMap Nominatim reverse geocoding (same HTTP stack as
Open-Meteo: ``requests``).
"""

from __future__ import annotations

import os

import requests

MAPBOX_REVERSE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"

NOMINATIM_USER_AGENT = "VilleIA/1.0 (Polytechnique prototype; reverse geocoding)"


def _shorten_place_name(place_name: str, max_parts: int = 2) -> str:
    parts = [p.strip() for p in place_name.split(",") if p.strip()]
    return ", ".join(parts[:max_parts]) if parts else ""


def _mapbox_reverse(lat: float, lng: float, token: str) -> str | None:
    url = f"{MAPBOX_REVERSE_URL}/{lng},{lat}.json"
    params = {
        "access_token": token,
        "language": "fr",
        "types": "neighborhood,locality,place",
        "limit": 5,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    feats = data.get("features") or []
    if not feats:
        return None
    place_name = feats[0].get("place_name") or feats[0].get("text")
    if not place_name:
        return None
    return _shorten_place_name(place_name)


def _nominatim_reverse(lat: float, lng: float) -> str | None:
    resp = requests.get(
        NOMINATIM_REVERSE,
        params={
            "lat": lat,
            "lon": lng,
            "format": "json",
            "addressdetails": 1,
            "accept-language": "fr",
        },
        headers={"User-Agent": NOMINATIM_USER_AGENT},
        timeout=12,
    )
    resp.raise_for_status()
    data = resp.json()
    addr = data.get("address") or {}
    neighbourhood = (
        addr.get("neighbourhood")
        or addr.get("suburb")
        or addr.get("quarter")
        or addr.get("city_district")
    )
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("municipality")
        or addr.get("village")
        or addr.get("county")
    )
    if neighbourhood and city and neighbourhood != city:
        return f"{neighbourhood}, {city}"
    if neighbourhood:
        return neighbourhood
    if city:
        return city
    display = data.get("display_name")
    if display:
        return _shorten_place_name(display)
    return None


def get_place_label(lat: float, lng: float) -> str | None:
    token = os.environ.get("MAPBOX_API_KEY", "").strip()
    if token:
        try:
            label = _mapbox_reverse(lat, lng, token)
            if label:
                return label
        except (requests.RequestException, KeyError, ValueError, TypeError):
            pass
    try:
        return _nominatim_reverse(lat, lng)
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return None
