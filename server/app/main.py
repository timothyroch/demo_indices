import asyncio
import os
from dataclasses import asdict
from functools import partial
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.alerts import run_risk_alerts_in_background, send_email, send_sms
from app.auth import ensure_admin_user, get_current_user, require_admin
from app.auth import router as auth_router
from app.constants.alerts import (
    ALERT_EMAIL_TEST_BODY,
    ALERT_EMAIL_TEST_SUBJECT,
    ALERT_SMS_TEST_MESSAGE,
)
from app.constants.errors import (
    ALERT_ERROR_EMAIL_UNAVAILABLE,
    ALERT_ERROR_NO_EMAIL,
    ALERT_ERROR_NO_PHONE,
    ALERT_ERROR_SMS_UNAVAILABLE,
    REPORT_ERROR_BACKEND,
)
from app.constants.feature_flags import auth_disabled
from app.database import (
    SessionLocal,
    User,
    get_db,
    get_db_optional,
    init_db,
    sync_legacy_alert_fields,
)
from app.schemas import (
    AlertSettingsResponse,
    AlertSettingsUpdate,
    JournalReportGenerateRequest,
    JournalStructuredReport,
    UserActionJournalCreate,
)
from app.services.hasard_maps_service import compute_all_hazard_zones, snap_to_grid
from app.services.journal_model_context_service import build_model_run_journal_payload
from app.services.journal_reports_service import generate_journal_structured_report
from app.services.user_action_journal_service import (
    append_user_action_journal,
    append_user_model_fetch_journal,
    extract_journal_request_meta,
)
from app.stub_alert_settings import update_stub_alert_settings

from .models.fluvial_floods_model import (
    predict_detailed_fluvial_flood,
    simulate_fluvial_flood_predictions,
)
from .models.pluvial_floods_model import (
    predict_detailed_pluvial_flood,
    simulate_pluvial_flood_predictions,
)
from .providers.open_meteo import open_meteo_provider
from .risk_assessors.heatwave import HeatwaveAssessor
from .risk_assessors.snow import assess_snow_risk, simulate_snow_predictions
from .services.partner_city_access_service import (
    ensure_lat_lng_allowed,
    partner_city_scope,
)
from .services.place_label_service import get_place_label
from .services.weather_service import get_cached_weather_data

load_dotenv()

app = FastAPI()
app.include_router(auth_router)

_cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:4200").strip().split()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

heatwave_assessor = HeatwaveAssessor()


@app.on_event("startup")
def startup() -> None:
    if os.environ.get("JWT_SECRET") in (None, "", "change-me-in-production-use-env"):
        print("WARNING: Set JWT_SECRET in production (e.g. in .env).")
    if os.environ.get("MAPBOX_API_KEY") in (None, ""):
        print("WARNING: MAPBOX_API_KEY is not set; the frontend map may not display.")
    if auth_disabled():
        print("INFO: AUTH_DISABLED=on, skipping DB init and admin bootstrap.")
    else:
        init_db()
        ensure_admin_user()


@app.on_event("startup")
async def startup_scheduled_model_journal() -> None:
    from app.services.scheduled_model_journal_service import (
        scheduled_model_journal_loop,
        scheduled_model_log_enabled,
    )

    if scheduled_model_log_enabled():
        asyncio.create_task(scheduled_model_journal_loop())


@app.get("/api/alerts/settings", response_model=AlertSettingsResponse)
async def get_alert_settings(current_user: Annotated[User, Depends(get_current_user)]):
    return AlertSettingsResponse(
        alert_pluvial_enabled=current_user.alert_pluvial_enabled,
        alert_fluvial_enabled=current_user.alert_fluvial_enabled,
        alert_heatwave_enabled=current_user.alert_heatwave_enabled,
        alert_snow_enabled=current_user.alert_snow_enabled,
        alert_threshold_pluvial_pct=current_user.alert_threshold_pluvial_pct,
        alert_threshold_fluvial_pct=current_user.alert_threshold_fluvial_pct,
        alert_threshold_heatwave_humidex=current_user.alert_threshold_heatwave_humidex,
        alert_threshold_snow_pct=current_user.alert_threshold_snow_pct,
        alert_via_sms=current_user.alert_via_sms,
        alert_via_email=current_user.alert_via_email,
        alert_frequency_hours=current_user.alert_frequency_hours,
    )


@app.patch("/api/alerts/settings", response_model=AlertSettingsResponse)
async def update_alert_settings(
    body: AlertSettingsUpdate,
    db: Annotated[Session | None, Depends(get_db_optional)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if body.alert_pluvial_enabled is not None:
        current_user.alert_pluvial_enabled = body.alert_pluvial_enabled
    if body.alert_fluvial_enabled is not None:
        current_user.alert_fluvial_enabled = body.alert_fluvial_enabled
    if body.alert_heatwave_enabled is not None:
        current_user.alert_heatwave_enabled = body.alert_heatwave_enabled
    if body.alert_snow_enabled is not None:
        current_user.alert_snow_enabled = body.alert_snow_enabled
    if body.alert_threshold_pluvial_pct is not None:
        current_user.alert_threshold_pluvial_pct = body.alert_threshold_pluvial_pct
    if body.alert_threshold_fluvial_pct is not None:
        current_user.alert_threshold_fluvial_pct = body.alert_threshold_fluvial_pct
    if body.alert_threshold_heatwave_humidex is not None:
        current_user.alert_threshold_heatwave_humidex = (
            body.alert_threshold_heatwave_humidex
        )
    if body.alert_threshold_snow_pct is not None:
        current_user.alert_threshold_snow_pct = body.alert_threshold_snow_pct
    if body.alert_via_sms is not None:
        current_user.alert_via_sms = body.alert_via_sms
    if body.alert_via_email is not None:
        current_user.alert_via_email = body.alert_via_email
    if body.alert_frequency_hours is not None:
        current_user.alert_frequency_hours = body.alert_frequency_hours
    sync_legacy_alert_fields(current_user)
    if db is not None:
        db.commit()
        db.refresh(current_user)
    else:
        update_stub_alert_settings(
            {
                "alert_pluvial_enabled": current_user.alert_pluvial_enabled,
                "alert_fluvial_enabled": current_user.alert_fluvial_enabled,
                "alert_heatwave_enabled": current_user.alert_heatwave_enabled,
                "alert_snow_enabled": current_user.alert_snow_enabled,
                "alert_threshold_pluvial_pct": current_user.alert_threshold_pluvial_pct,
                "alert_threshold_fluvial_pct": current_user.alert_threshold_fluvial_pct,
                "alert_threshold_heatwave_humidex": (
                    current_user.alert_threshold_heatwave_humidex
                ),
                "alert_threshold_snow_pct": current_user.alert_threshold_snow_pct,
                "alert_via_sms": current_user.alert_via_sms,
                "alert_via_email": current_user.alert_via_email,
                "alert_frequency_hours": current_user.alert_frequency_hours,
            }
        )
    return AlertSettingsResponse(
        alert_pluvial_enabled=current_user.alert_pluvial_enabled,
        alert_fluvial_enabled=current_user.alert_fluvial_enabled,
        alert_heatwave_enabled=current_user.alert_heatwave_enabled,
        alert_snow_enabled=current_user.alert_snow_enabled,
        alert_threshold_pluvial_pct=current_user.alert_threshold_pluvial_pct,
        alert_threshold_fluvial_pct=current_user.alert_threshold_fluvial_pct,
        alert_threshold_heatwave_humidex=current_user.alert_threshold_heatwave_humidex,
        alert_threshold_snow_pct=current_user.alert_threshold_snow_pct,
        alert_via_sms=current_user.alert_via_sms,
        alert_via_email=current_user.alert_via_email,
        alert_frequency_hours=current_user.alert_frequency_hours,
    )


@app.post("/api/alerts/test")
async def test_alert(current_user: Annotated[User, Depends(get_current_user)]):
    if not current_user.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ALERT_ERROR_NO_PHONE,
        )
    ok = send_sms(current_user.phone, ALERT_SMS_TEST_MESSAGE)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ALERT_ERROR_SMS_UNAVAILABLE,
        )
    return {"sent": True}


@app.post("/api/alerts/test-email")
async def test_alert_email(current_user: Annotated[User, Depends(get_current_user)]):
    if not current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ALERT_ERROR_NO_EMAIL,
        )
    ok = send_email(
        to_email=current_user.email,
        subject=ALERT_EMAIL_TEST_SUBJECT,
        body=ALERT_EMAIL_TEST_BODY,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ALERT_ERROR_EMAIL_UNAVAILABLE,
        )
    return {"sent": True}


@app.get("/api/risk-zones/computed")
def all_hazard_zones_computed(
    current_user: Annotated[User, Depends(get_current_user)],
):
    scope = partner_city_scope(current_user)
    response = compute_all_hazard_zones(scope)
    return response


@app.post("/api/alerts/evaluate")
def evaluate_risk_alerts(
    _current_user: Annotated[User, Depends(get_current_user)],
):
    run_risk_alerts_in_background(SessionLocal, None)
    return {"ok": True}


@app.get("/api/weather-data")
def weather_feature_info(
    current_user: Annotated[User, Depends(get_current_user)],
    lat: float = Query(...),
    lng: float = Query(...),
):
    ensure_lat_lng_allowed(current_user, lat, lng)
    return get_cached_weather_data(lat, lng)


@app.get("/api/place-label")
def place_label(
    current_user: Annotated[User, Depends(get_current_user)],
    lat: float = Query(...),
    lng: float = Query(...),
):
    ensure_lat_lng_allowed(current_user, lat, lng)
    label = get_place_label(lat, lng)
    return {"label": label or ""}


@app.post("/api/pluvial-flood/predict")
def pluvial_flood_predict(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    payload: dict = Body(...),
):
    lat = payload["lat"]
    lng = payload["lng"]
    adidu = payload["adidu"]
    ensure_lat_lng_allowed(current_user, lat, lng)

    snapped_lat, snapped_lng = snap_to_grid(lat, lng)

    weather = get_cached_weather_data(snapped_lat, snapped_lng)
    response = predict_detailed_pluvial_flood(
        snapped_lat,
        snapped_lng,
        weather["temperature"],
        weather["precipitation"],
        adidu,
    )
    jpayload = build_model_run_journal_payload(
        user=current_user,
        request=request,
        model_name="pluvial_flood",
        route="/api/pluvial-flood/predict",
        zone_id=adidu,
        request_summary={
            "lat": lat,
            "lng": lng,
            "snapped_lat": snapped_lat,
            "snapped_lng": snapped_lng,
            "zone_id": adidu,
        },
        response_body=response,
        weather_summary_extra={
            "cached_temperature_c": weather.get("temperature"),
            "cached_precipitation": weather.get("precipitation"),
        },
    )
    append_user_model_fetch_journal(
        current_user=current_user,
        model_name="pluvial_flood",
        route="/api/pluvial-flood/predict",
        payload=jpayload,
    )
    return response


@app.post("/api/pluvial-flood/simulate-predictions")
def pluvial_flood_simulate(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: dict = Body(...),
):
    lat = payload["lat"]
    lng = payload["lng"]
    adidu = payload["adidu"]
    simulation_overrides = payload["simulation_overrides"]
    ensure_lat_lng_allowed(current_user, lat, lng)

    lat, lng = snap_to_grid(lat, lng)
    return simulate_pluvial_flood_predictions(lat, lng, adidu, simulation_overrides)


@app.post("/api/fluvial-flood/predict")
def fluvial_flood_predict(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    payload: dict = Body(...),
):
    lat = payload["lat"]
    lng = payload["lng"]
    adidu = payload["adidu"]

    ensure_lat_lng_allowed(current_user, lat, lng)
    snapped_lat, snapped_lng = snap_to_grid(lat, lng)
    weather = get_cached_weather_data(snapped_lat, snapped_lng)
    response = predict_detailed_fluvial_flood(
        snapped_lat,
        snapped_lng,
        weather["temperature"],
        weather["precipitation"],
        adidu,
    )

    jpayload = build_model_run_journal_payload(
        user=current_user,
        request=request,
        model_name="fluvial_flood",
        route="/api/fluvial-flood/predict",
        zone_id=adidu,
        request_summary={
            "lat": lat,
            "lng": lng,
            "snapped_lat": snapped_lat,
            "snapped_lng": snapped_lng,
            "zone_id": adidu,
        },
        response_body=response,
        weather_summary_extra={
            "cached_temperature_c": weather.get("temperature"),
            "cached_precipitation": weather.get("precipitation"),
        },
    )
    append_user_model_fetch_journal(
        current_user=current_user,
        model_name="fluvial_flood",
        route="/api/fluvial-flood/predict",
        payload=jpayload,
    )
    return response


@app.post("/api/fluvial-flood/simulate-predictions")
def fluvial_flood_simulate(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: dict = Body(...),
):
    lat = payload["lat"]
    lng = payload["lng"]
    adidu = payload["adidu"]
    simulation_overrides = payload["simulation_overrides"]
    ensure_lat_lng_allowed(current_user, lat, lng)

    lat, lng = snap_to_grid(lat, lng)
    return simulate_fluvial_flood_predictions(lat, lng, adidu, simulation_overrides)


@app.post("/api/heatwave/predict")
def heatwave_predict(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    payload: dict = Body(...),
):
    lat = payload["lat"]
    lng = payload["lng"]
    adidu = payload.get("adidu")

    ensure_lat_lng_allowed(current_user, lat, lng)

    forecasts = open_meteo_provider.get_heatwave_forecast(lat, lng, days=7)
    assessment = heatwave_assessor.assess(forecasts, adidu)
    response = asdict(assessment)

    zone_key = str(adidu) if adidu is not None else None
    jpayload = build_model_run_journal_payload(
        user=current_user,
        request=request,
        model_name="heatwave",
        route="/api/heatwave/predict",
        zone_id=zone_key,
        request_summary={"lat": lat, "lng": lng, "days": 7, "zone_id": adidu},
        response_body=response,
    )
    append_user_model_fetch_journal(
        current_user=current_user,
        model_name="heatwave",
        route="/api/heatwave/predict",
        payload=jpayload,
    )
    return response


@app.post("/api/snow/predict")
def snow_predict(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    payload: dict = Body(...),
):
    lat = payload["lat"]
    lng = payload["lng"]
    adidu = payload.get("adidu")

    ensure_lat_lng_allowed(current_user, lat, lng)

    forecasts = open_meteo_provider.get_snow_forecast(lat, lng, days=8)
    assessment = assess_snow_risk(forecasts, adidu)
    response = asdict(assessment)
    response["daily_details"] = [asdict(d) for d in assessment.daily_details]

    zone_key = str(adidu) if adidu is not None else None
    jpayload = build_model_run_journal_payload(
        user=current_user,
        request=request,
        model_name="snow",
        route="/api/snow/predict",
        zone_id=zone_key,
        request_summary={"lat": lat, "lng": lng, "days": 8, "zone_id": adidu},
        response_body=response,
    )
    append_user_model_fetch_journal(
        current_user=current_user,
        model_name="snow",
        route="/api/snow/predict",
        payload=jpayload,
    )
    return response


@app.post("/api/snow/simulate-predictions")
def snow_simulate(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: dict = Body(...),
):
    lat = payload["lat"]
    lng = payload["lng"]
    adidu = payload.get("adidu")

    simulation_overrides = payload["simulation_overrides"]
    ensure_lat_lng_allowed(current_user, lat, lng)

    forecasts = open_meteo_provider.get_snow_forecast(lat, lng, days=8)

    return simulate_snow_predictions(forecasts, adidu, simulation_overrides)


@app.post("/api/journal/actions", status_code=204)
async def journal_user_action(
    request: Request,
    body: UserActionJournalCreate,
    current_user: Annotated[User, Depends(get_current_user)],
):
    if auth_disabled():
        return None
    meta = extract_journal_request_meta(request)
    await asyncio.to_thread(
        append_user_action_journal,
        current_user=current_user,
        body=body,
        request_meta=meta,
    )
    return None


async def _generate_journal_report_http(
    db: Session,
    body: JournalReportGenerateRequest,
    *,
    user_id: int | None,
    generator_label: str,
    subject_user: User | None,
    log_context: str,
) -> JournalStructuredReport:
    try:
        return await asyncio.to_thread(
            partial(
                generate_journal_structured_report,
                db,
                body,
                user_id=user_id,
                generator_label=generator_label,
                subject_user=subject_user,
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        print(f"[journal report {log_context}] {e!r}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=REPORT_ERROR_BACKEND,
        ) from e


@app.post(
    "/api/journal/reports/generate",
    response_model=JournalStructuredReport,
)
async def user_generate_journal_report(
    body: JournalReportGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return await _generate_journal_report_http(
        db,
        body,
        user_id=current_user.id,
        generator_label=f"Utilisateur : {current_user.username}",
        subject_user=current_user,
        log_context="user",
    )


@app.post(
    "/api/admin/journal/reports/generate",
    response_model=JournalStructuredReport,
)
async def admin_generate_journal_report(
    body: JournalReportGenerateRequest,
    _admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return await _generate_journal_report_http(
        db,
        body,
        user_id=None,
        generator_label=f"Administrateur : {_admin.username}",
        subject_user=None,
        log_context="admin",
    )
