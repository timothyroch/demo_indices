"""Accès par ville partenaire (Montréal / Laval) pour les comptes non admin."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.constants.errors import (
    AUTH_ERROR_OUTSIDE_PARTNER_ZONE,
    AUTH_ERROR_PARTNER_CITY_NOT_ASSIGNED,
)
from app.constants.feature_flags import auth_disabled
from app.constants.partner_city import (
    GEOJSON_PROPERTY_PARTNER_CITY,
    PARTNER_CITY_LAVAL,
    PARTNER_CITY_MONTREAL,
)
from app.database import User

# Boîtes approximatives WGS84 (ville partenaire) pour filtrage et validation lat/lng.
PARTNER_CITY_BBOX: dict[str, dict[str, float]] = {
    PARTNER_CITY_MONTREAL: {
        "min_lng": -73.98,
        "max_lng": -73.42,
        "min_lat": 45.38,
        "max_lat": 45.65,
    },
    PARTNER_CITY_LAVAL: {
        "min_lng": -73.88,
        "max_lng": -73.58,
        "min_lat": 45.52,
        "max_lat": 45.72,
    },
}


def centroid_wgs84(geom: dict[str, Any] | None) -> tuple[float, float] | None:
    if not geom:
        return None
    gtype = geom.get("type")
    coords = None
    if gtype == "Polygon":
        coords = geom["coordinates"][0]
    elif gtype == "MultiPolygon":
        coords = geom["coordinates"][0][0]
    if not coords:
        return None
    avg_lng = sum(c[0] for c in coords) / len(coords)
    avg_lat = sum(c[1] for c in coords) / len(coords)
    return (avg_lat, avg_lng)


def partner_city_scope(user: User) -> str | None:
    """None = accès complet (admin ou mode sans auth). Sinon identifiant de ville."""
    if auth_disabled():
        return None
    if user.is_admin:
        return None
    if not user.partner_city:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=AUTH_ERROR_PARTNER_CITY_NOT_ASSIGNED,
        )
    if user.partner_city not in (PARTNER_CITY_MONTREAL, PARTNER_CITY_LAVAL):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=AUTH_ERROR_PARTNER_CITY_NOT_ASSIGNED,
        )
    return user.partner_city


def _lat_lng_in_bbox(lat: float, lng: float, partner_city: str) -> bool:
    box = PARTNER_CITY_BBOX[partner_city]
    return (
        box["min_lat"] <= lat <= box["max_lat"]
        and box["min_lng"] <= lng <= box["max_lng"]
    )


def ensure_lat_lng_allowed(user: User, lat: float, lng: float) -> None:
    scope = partner_city_scope(user)
    if scope is None:
        return
    if not _lat_lng_in_bbox(lat, lng, scope):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=AUTH_ERROR_OUTSIDE_PARTNER_ZONE,
        )


def filter_feature_collection_by_partner_city(
    fc: dict[str, Any], partner_city: str
) -> dict[str, Any]:
    out_features: list[dict[str, Any]] = []
    for feat in fc.get("features", []):
        c = centroid_wgs84(feat.get("geometry"))
        if not c:
            continue
        lat, lng = c
        if _lat_lng_in_bbox(lat, lng, partner_city):
            out_features.append(feat)
    return {"type": "FeatureCollection", "features": out_features}


def filter_features_by_partner_city(
    fc: dict[str, Any], partner_city: str
) -> dict[str, Any]:
    out_features: list[dict[str, Any]] = []
    for feat in fc.get("features", []):
        props = feat.get("properties") or {}
        feature_city = props.get(GEOJSON_PROPERTY_PARTNER_CITY)
        if feature_city != partner_city:
            continue
        out_features.append(feat)
    return {"type": "FeatureCollection", "features": out_features}
