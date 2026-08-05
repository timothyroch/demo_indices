from __future__ import annotations

import asyncio
import os
from dataclasses import asdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.alerts import run_risk_alerts_in_background
from app.constants.feature_flags import auth_disabled
from app.database import SessionLocal, User
from app.models.fluvial_floods_model import (
    predict_detailed_fluvial_flood,
)
from app.models.pluvial_floods_model import (
    predict_detailed_pluvial_flood,
)
from app.providers.open_meteo import open_meteo_provider
from app.risk_assessors.heatwave import HeatwaveAssessor
from app.risk_assessors.snow import assess_snow_risk
from app.services.journal_model_context_service import build_model_run_journal_payload
from app.services.user_action_journal_service import append_user_model_fetch_journal
from app.services.weather_service import get_cached_weather_data

_JOURNAL_ACTION_SCHEDULED = "scheduled_model_fetch"


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def scheduled_model_log_enabled() -> bool:
    if auth_disabled():
        return False
    return _env_bool("SCHEDULED_MODEL_LOG_ENABLED", True)


def _snapshot_coords() -> tuple[float, float, str]:
    lat = float(os.environ.get("SCHEDULED_MODEL_SNAPSHOT_LAT", "45.55"))
    lng = float(os.environ.get("SCHEDULED_MODEL_SNAPSHOT_LNG", "-73.55"))
    zone_id = os.environ.get("SCHEDULED_MODEL_ZONE_ID", "default")
    return lat, lng, zone_id


def _schedule_time() -> tuple[int, int, str]:
    hour = int(os.environ.get("SCHEDULED_MODEL_LOG_HOUR", "12"))
    minute = int(os.environ.get("SCHEDULED_MODEL_LOG_MINUTE", "0"))
    tz_name = os.environ.get("SCHEDULED_MODEL_LOG_TZ", "America/Montreal")
    return hour, minute, tz_name


def seconds_until_next_run() -> float:
    hour, minute, tz_name = _schedule_time()
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def _run_predictions_and_log_for_user(user: User) -> None:
    lat, lng, zone_id = _snapshot_coords()
    adidu = str(zone_id).strip() or None
    weather = get_cached_weather_data(lat, lng)

    pluvial = predict_detailed_pluvial_flood(
        lat,
        lng,
        weather["temperature"],
        weather["precipitation"],
        adidu,
    )
    pluvial_payload = build_model_run_journal_payload(
        user=user,
        request=None,
        model_name="pluvial_flood",
        route="scheduled:/api/pluvial-flood/predict",
        zone_id=str(zone_id),
        request_summary={"lat": lat, "lng": lng, "zone_id": zone_id},
        response_body=pluvial,
        source="scheduled_daily",
        weather_summary_extra={
            "cached_temperature_c": weather.get("temperature"),
            "cached_precipitation": weather.get("precipitation"),
        },
    )
    append_user_model_fetch_journal(
        current_user=user,
        model_name="pluvial_flood",
        route="scheduled:/api/pluvial-flood/predict",
        journal_action=_JOURNAL_ACTION_SCHEDULED,
        payload=pluvial_payload,
    )

    fluvial = predict_detailed_fluvial_flood(
        lat, lng, weather["temperature"], weather["precipitation"], adidu
    )
    fluvial_payload = build_model_run_journal_payload(
        user=user,
        request=None,
        model_name="fluvial_flood",
        route="scheduled:/api/fluvial-flood/predict",
        zone_id=str(zone_id),
        request_summary={"lat": lat, "lng": lng, "zone_id": zone_id},
        response_body=fluvial,
        source="scheduled_daily",
        weather_summary_extra={
            "cached_temperature_c": weather.get("temperature"),
            "cached_precipitation": weather.get("precipitation"),
        },
    )
    append_user_model_fetch_journal(
        current_user=user,
        model_name="fluvial_flood",
        route="scheduled:/api/fluvial-flood/predict",
        journal_action=_JOURNAL_ACTION_SCHEDULED,
        payload=fluvial_payload,
    )

    assessor = HeatwaveAssessor()
    hw_forecasts = open_meteo_provider.get_heatwave_forecast(lat, lng, days=7)
    hw_assessment = assessor.assess(hw_forecasts, adidu)
    hw_response = asdict(hw_assessment)
    hw_payload = build_model_run_journal_payload(
        user=user,
        request=None,
        model_name="heatwave",
        route="scheduled:/api/heatwave/predict",
        zone_id=str(zone_id),
        request_summary={"lat": lat, "lng": lng, "days": 7, "zone_id": zone_id},
        response_body=hw_response,
        source="scheduled_daily",
    )
    append_user_model_fetch_journal(
        current_user=user,
        model_name="heatwave",
        route="scheduled:/api/heatwave/predict",
        journal_action=_JOURNAL_ACTION_SCHEDULED,
        payload=hw_payload,
    )

    snow_forecasts = open_meteo_provider.get_snow_forecast(lat, lng, days=8)
    snow_assessment = assess_snow_risk(snow_forecasts, adidu)
    snow_out = asdict(snow_assessment)
    snow_out["daily_details"] = [asdict(d) for d in snow_assessment.daily_details]
    snow_payload = build_model_run_journal_payload(
        user=user,
        request=None,
        model_name="snow",
        route="scheduled:/api/snow/predict",
        zone_id=str(zone_id),
        request_summary={"lat": lat, "lng": lng, "days": 8, "zone_id": zone_id},
        response_body=snow_out,
        source="scheduled_daily",
    )
    append_user_model_fetch_journal(
        current_user=user,
        model_name="snow",
        route="scheduled:/api/snow/predict",
        journal_action=_JOURNAL_ACTION_SCHEDULED,
        payload=snow_payload,
    )


def run_scheduled_model_snapshots_for_all_users() -> None:
    if not scheduled_model_log_enabled():
        return

    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id).all()
    finally:
        db.close()

    if not users:
        print("[scheduled_model_journal] No users in DB; skipping daily snapshot.")
        return

    lat, lng, _ = _snapshot_coords()
    msg = (
        f"[scheduled_model_journal] Daily snapshots for {len(users)} user(s) "
        f"at lat={lat}, lng={lng}…"
    )
    print(msg)

    for user in users:
        try:
            _run_predictions_and_log_for_user(user)
        except Exception as e:
            print(
                f"[scheduled_model_journal] Failed for user id={user.id} "
                f"{user.username!r}: {e}"
            )

    try:
        run_risk_alerts_in_background(SessionLocal, None)
    except Exception as e:
        print(f"[scheduled_model_journal] risk alerts: {e}")


async def scheduled_model_journal_loop() -> None:
    if not scheduled_model_log_enabled():
        print(
            "INFO: Scheduled model journal disabled "
            "(AUTH_DISABLED or SCHEDULED_MODEL_LOG_ENABLED=false)."
        )
        return

    hour, minute, tz_name = _schedule_time()
    print(
        f"INFO: Scheduled model journal enabled: daily at "
        f"{hour:02d}:{minute:02d} ({tz_name})."
    )

    while True:
        wait_s = seconds_until_next_run()
        await asyncio.sleep(wait_s)
        await asyncio.to_thread(run_scheduled_model_snapshots_for_all_users)
