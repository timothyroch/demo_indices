from __future__ import annotations

from typing import Any

from fastapi import Request

from app.database import User

HAZARD_LABEL_FR: dict[str, str] = {
    "heatwave": "Canicule",
    "snow": "Chutes de neige",
    "fluvial_flood": "Crues fluviales",
    "pluvial_flood": "Inondations pluviales",
}

_MODEL_TO_RISK_MAP_KIND: dict[str, str] = {
    "heatwave": "canicules",
    "snow": "neige",
    "fluvial_flood": "crues",
    "pluvial_flood": "pluvial",
}

_SOCIAL_DEMO_KEYS = (
    "pct_65_plus",
    "revenu_median_menage",
    "gini",
    "logement_reparations_majeures",
)

_CENSUS_SOURCE = "Recensement Statistique Canada 2021"


def client_ip_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip() or None
    client = request.client
    return client.host if client else None


def client_audit_from_request(request: Request | None) -> dict[str, Any]:
    if request is None:
        return {"ip": None, "user_agent": None}
    ua = request.headers.get("user-agent")
    if ua and len(ua) > 500:
        ua = ua[:500]
    return {"ip": client_ip_from_request(request), "user_agent": ua}


def _user_snapshot(user: User) -> dict[str, Any]:
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
    }


# @functools.lru_cache(maxsize=8)
# def _risk_map_features(kind: str) -> tuple[dict[str, Any], ...]:
#     geo = load_risk_zone_map(kind)
#     feats = geo.get("features") or []
#     return tuple(feats)


# def zone_social_snapshot(
#     model_name: str, zone_feature_id: str | None
# ) -> dict[str, Any] | None:
#     if not zone_feature_id or not str(zone_feature_id).strip():
#         return None
#     map_kind = _MODEL_TO_RISK_MAP_KIND.get(model_name)
#     if not map_kind:
#         return None
#     fid = str(zone_feature_id).strip()
#     for feat in _risk_map_features(map_kind):
#         props = feat.get("properties") or {}
#         pf = props.get("FID")
#         if pf is not None and str(pf) == fid:
#             return _pick_social_props(props)
#         zid = props.get("zone_id")
#         if zid is not None and str(zid) == fid:
#             return _pick_social_props(props)
#     return None


def _pick_social_props(props: dict[str, Any]) -> dict[str, Any]:
    indicateurs: dict[str, Any] = {k: props.get(k) for k in _SOCIAL_DEMO_KEYS}
    indicateurs["source"] = _CENSUS_SOURCE
    return {
        "zone_selected_adidu": props.get("ADIDU"),
        "score_vuln_sociale": props.get("score_vuln_sociale"),
        "score_risque": props.get("score_risque"),
        "risque_de_base": props.get("niveau_risque"),
        "indicateurs_clefs": indicateurs,
        "source": _CENSUS_SOURCE,
    }


def _heatwave_extras(response: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
    days = list(response.get("daily_details") or [])
    first = days[0] if days else {}
    summary = {
        "first_forecast_date": first.get("date"),
        "temp_max_c": first.get("temperature_max"),
        "temp_min_c": first.get("temperature_min"),
        "humidex": first.get("humidex"),
        "humidity_max_pct": first.get("relative_humidity_max"),
        "risk_level": response.get("risk_level"),
        "risk_message": response.get("message"),
        "risk_detected": response.get("risk_detected"),
    }
    return days, summary


def _snow_extras(response: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
    days = list(response.get("daily_details") or [])
    first = days[0] if days else {}
    summary = {
        "first_forecast_date": first.get("date"),
        "snow_cm": first.get("total_snow_cm"),
        "mean_temp_c": first.get("mean_temperature"),
        "snow_risk_rules": first.get("snow_risk_rules"),
        "risk_level": response.get("risk_level"),
        "risk_message": response.get("message"),
        "risk_detected": response.get("risk_detected"),
    }
    return days, summary


def build_model_run_journal_payload(
    *,
    user: User,
    request: Request | None,
    model_name: str,
    route: str,
    zone_id: str | None,
    request_summary: dict[str, Any],
    response_body: Any,
    source: str | None = None,
    recommendations_made: list[str] | None = None,
    simulation: dict[str, Any] | None = None,
    weather_summary_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resp_dict = response_body if isinstance(response_body, dict) else {}
    forecast_days: list[Any] | None = None
    weather_summary: dict[str, Any] | None = None

    if model_name == "heatwave":
        forecast_days, weather_summary = _heatwave_extras(resp_dict)
    elif model_name == "snow":
        forecast_days, weather_summary = _snow_extras(resp_dict)

    if weather_summary_extra:
        weather_summary = {**(weather_summary or {}), **weather_summary_extra}

    zone_norm: str | int | None = None
    if zone_id is not None:
        zs = str(zone_id).strip()
        if zs:
            zone_norm = int(zs) if zs.isdigit() else zs

    payload: dict[str, Any] = {
        "operation_status": "success",
        "journal_event": "run_predictive_model",
        "user": _user_snapshot(user),
        "client": client_audit_from_request(request),
        "hazard": HAZARD_LABEL_FR.get(model_name, model_name),
        "model": model_name,
        "route": route,
        "selected_zone_id": zone_norm,
        "weather_source": "Open-Meteo",
        "weather_summary": weather_summary,
        "forecast_days": forecast_days,
        # "social_indicators": zone_social_snapshot(model_name, zone_id),
        "recommendations_made": list(recommendations_made or []),
        "simulation": simulation
        if simulation is not None
        else {"has_simulated": False},
        "request": request_summary,
        "response": response_body,
    }
    if source:
        payload["source"] = source
    return payload
