import os
import threading
from datetime import datetime, timezone

import requests
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.constants.feature_flags import auth_disabled
from app.database import User
from app.services.hasard_maps_service import compute_all_hazard_zones
from app.services.partner_city_access_service import (
    filter_feature_collection_by_partner_city,
)
from app.stub_alert_settings import (
    get_stub_alert_settings,
    update_stub_last_alert_sent,
)

DEFAULT_ALERT_FREQUENCY_HOURS = 4

_twilio_client = None


def _get_twilio_client():
    global _twilio_client
    if _twilio_client is not None:
        return _twilio_client
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        return None
    try:
        from twilio.rest import Client

        _twilio_client = Client(sid, token)
        return _twilio_client
    except Exception as e:
        print(f"[alerts] Twilio client init failed: {e}")
        return None


def send_sms(phone: str, body: str) -> bool:
    client = _get_twilio_client()
    from_number = os.environ.get("TWILIO_PHONE_NUMBER")
    if not client or not from_number:
        print(
            "[alerts] Twilio non configuré "
            "(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER)"
        )
        return False
    phone_clean = "".join(c for c in phone if c.isdigit() or c == "+")
    if not phone_clean.startswith("+"):
        if len(phone_clean) == 10:
            phone_clean = "+1" + phone_clean
        else:
            phone_clean = "+" + phone_clean
    try:
        client.messages.create(to=phone_clean, from_=from_number, body=body)
        return True
    except Exception as e:
        print(f"[alerts] Twilio send_sms error: {e}")
        return False


def send_email(to_email: str, subject: str, body: str) -> bool:
    api_key = os.environ.get("SENDGRID_API_KEY")
    from_email = os.environ.get("ALERT_EMAIL_FROM")
    if not api_key or not from_email:
        print(
            "[alerts] SendGrid non configuré "
            "(SENDGRID_API_KEY, ALERT_EMAIL_FROM manquants)"
        )
        return False

    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject,
            }
        ],
        "from": {"email": from_email},
        "content": [
            {
                "type": "text/plain",
                "value": body,
            }
        ],
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if 200 <= resp.status_code < 300:
            return True
        print(
            f"[alerts] SendGrid email error: status={resp.status_code}, "
            f"body={resp.text}"
        )
        return False
    except Exception as e:
        print(f"[alerts] SendGrid exception: {e}")
        return False


def _pluvial_combined_pct_from_feature_props(props: dict) -> float:
    hazards = props.get("hazards") or {}
    pluv = hazards.get("pluvial") or {}
    v = pluv.get("combined_probability")
    if v is not None:
        try:
            return float(v)
        except (TypeError, ValueError):
            pass
    legacy = props.get("display_score")
    if legacy is not None:
        try:
            return float(legacy)
        except (TypeError, ValueError):
            pass
    return 0.0


def _max_pluvial_combined_from_geojson(geojson: dict) -> float:
    features = geojson.get("features") or []
    if not features:
        return 0.0
    scores = [
        _pluvial_combined_pct_from_feature_props(f.get("properties") or {})
        for f in features
    ]
    return max(scores) if scores else 0.0


def _crues_combined_pct_from_feature_props(props: dict) -> float:
    """Même source que la carte : hazards.crues.combined_probability (0–100)."""
    hazards = props.get("hazards") or {}
    cr = hazards.get("crues") or {}
    v = cr.get("combined_probability")
    if v is not None:
        try:
            return float(v)
        except (TypeError, ValueError):
            pass
    return 0.0


def _max_crues_combined_from_geojson(geojson: dict) -> float:
    features = geojson.get("features") or []
    if not features:
        return 0.0
    scores = [
        _crues_combined_pct_from_feature_props(f.get("properties") or {})
        for f in features
    ]
    return max(scores) if scores else 0.0


def _canicules_combined_from_feature_props(props: dict) -> float:
    hazards = props.get("hazards") or {}
    c = hazards.get("canicules") or {}
    v = c.get("combined_probability")
    if v is not None:
        try:
            return float(v)
        except (TypeError, ValueError):
            pass
    return 0.0


def _max_canicules_combined_from_geojson(geojson: dict) -> float:
    features = geojson.get("features") or []
    if not features:
        return 0.0
    scores = [
        _canicules_combined_from_feature_props(f.get("properties") or {})
        for f in features
    ]
    return max(scores) if scores else 0.0


def _neige_combined_from_feature_props(props: dict) -> float:
    hazards = props.get("hazards") or {}
    n = hazards.get("neige") or {}
    v = n.get("combined_probability")
    if v is not None:
        try:
            return float(v)
        except (TypeError, ValueError):
            pass
    return 0.0


def _max_neige_combined_from_geojson(geojson: dict) -> float:
    features = geojson.get("features") or []
    if not features:
        return 0.0
    scores = [
        _neige_combined_from_feature_props(f.get("properties") or {})
        for f in features
    ]
    return max(scores) if scores else 0.0


def _cooldown_seconds_from_user(user: User) -> float:
    hours = user.alert_frequency_hours
    if hours is None or hours < 4 or hours > 24:
        hours = DEFAULT_ALERT_FREQUENCY_HOURS
    return hours * 3600


def _last_sent_ok(last_iso: str | None, cooldown_seconds: float) -> bool:
    if not last_iso:
        return True
    try:
        last_dt = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        seconds_since_last = (datetime.now(timezone.utc) - last_dt).total_seconds()
        return seconds_since_last >= cooldown_seconds
    except Exception:
        return True


def _user_has_contact_for_alerts(user: User) -> bool:
    sms_ok = bool(user.alert_via_sms and user.phone)
    email_ok = bool(user.alert_via_email and user.email)
    return sms_ok or email_ok


def _last_field_for_kind(kind: str) -> str:
    return {
        "pluvial": "last_pluvial_alert_sent_at",
        "fluvial": "last_fluvial_alert_sent_at",
        "heatwave": "last_heatwave_alert_sent_at",
        "snow": "last_snow_alert_sent_at",
    }[kind]


def _user_can_fire_kind(user: User, kind: str) -> bool:
    if not _user_has_contact_for_alerts(user):
        return False
    last = getattr(user, _last_field_for_kind(kind), None)
    return _last_sent_ok(last, _cooldown_seconds_from_user(user))


def _pluvial_max_for_zone(full_fc: dict, partner_city: str | None) -> float:
    if partner_city:
        fc = filter_feature_collection_by_partner_city(full_fc, partner_city)
    else:
        fc = full_fc
    return _max_pluvial_combined_from_geojson(fc)


def _crues_max_for_zone(full_fc: dict, partner_city: str | None) -> float:
    if partner_city:
        fc = filter_feature_collection_by_partner_city(full_fc, partner_city)
    else:
        fc = full_fc
    return _max_crues_combined_from_geojson(fc)


def _canicules_max_for_zone(full_fc: dict, partner_city: str | None) -> float:
    if partner_city:
        fc = filter_feature_collection_by_partner_city(full_fc, partner_city)
    else:
        fc = full_fc
    return _max_canicules_combined_from_geojson(fc)


def _neige_max_for_zone(full_fc: dict, partner_city: str | None) -> float:
    if partner_city:
        fc = filter_feature_collection_by_partner_city(full_fc, partner_city)
    else:
        fc = full_fc
    return _max_neige_combined_from_geojson(fc)


def _metrics_for_user(user: User, full_hazard_fc: dict) -> dict[str, float]:
    partner_scope: str | None = None if user.is_admin else user.partner_city
    return {
        "pluvial_pct": _pluvial_max_for_zone(full_hazard_fc, partner_scope),
        "fluvial_pct": _crues_max_for_zone(full_hazard_fc, partner_scope),
        "heatwave_humidex": _canicules_max_for_zone(full_hazard_fc, partner_scope),
        "snow_pct": _neige_max_for_zone(full_hazard_fc, partner_scope),
    }


def _collect_triggered_lines_for_user(
    user: User, metrics: dict[str, float]
) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    kinds: list[str] = []
    if user.alert_pluvial_enabled and user.alert_threshold_pluvial_pct is not None:
        t = float(user.alert_threshold_pluvial_pct)
        v = metrics["pluvial_pct"]
        if v >= t and _user_can_fire_kind(user, "pluvial"):
            lines.append(f"Inondations pluviales: risque {v:.0f} % (seuil {t:.0f} %).")
            kinds.append("pluvial")
    if user.alert_fluvial_enabled and user.alert_threshold_fluvial_pct is not None:
        t = float(user.alert_threshold_fluvial_pct)
        v = metrics["fluvial_pct"]
        if v >= t and _user_can_fire_kind(user, "fluvial"):
            lines.append(f"Crues: probabilité {v:.0f} % (seuil {t:.0f} %).")
            kinds.append("fluvial")
    if (
        user.alert_heatwave_enabled
        and user.alert_threshold_heatwave_humidex is not None
    ):
        t = float(user.alert_threshold_heatwave_humidex)
        v = metrics["heatwave_humidex"]
        if v >= t and _user_can_fire_kind(user, "heatwave"):
            lines.append(f"Canicule: humidex max. {v:.0f} (seuil {t:.0f}).")
            kinds.append("heatwave")
    if user.alert_snow_enabled and user.alert_threshold_snow_pct is not None:
        t = float(user.alert_threshold_snow_pct)
        v = metrics["snow_pct"]
        if v >= t and _user_can_fire_kind(user, "snow"):
            lines.append(f"Chute de neige: risque {v:.0f} % (seuil {t:.0f} %).")
            kinds.append("snow")
    return lines, kinds


def _update_last_alerts(db: Session, user_id: int, kinds: list[str]) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S-00:00")
    updates: dict = {}
    for kind in kinds:
        key = _last_field_for_kind(kind)
        updates[key] = now
        if kind == "pluvial":
            updates["last_flood_alert_sent_at"] = now
    if updates:
        db.query(User).filter(User.id == user_id).update(
            updates, synchronize_session=False
        )
        db.commit()


def _stub_cooldown_seconds(settings: dict) -> float:
    hours = settings.get("alert_frequency_hours")
    if hours is None or hours < 4 or hours > 24:
        hours = DEFAULT_ALERT_FREQUENCY_HOURS
    return hours * 3600


def _stub_last_key(kind: str) -> str:
    return {
        "pluvial": "last_pluvial_alert_sent_at",
        "fluvial": "last_fluvial_alert_sent_at",
        "heatwave": "last_heatwave_alert_sent_at",
        "snow": "last_snow_alert_sent_at",
    }[kind]


def _stub_can_fire_kind(settings: dict, kind: str) -> bool:
    email = os.environ.get("AUTH_STUB_EMAIL")
    phone = os.environ.get("AUTH_STUB_PHONE")
    sms_ok = bool(settings.get("alert_via_sms") and phone)
    email_ok = bool(settings.get("alert_via_email") and email)
    if not (sms_ok or email_ok):
        return False
    last = settings.get(_stub_last_key(kind))
    return _last_sent_ok(last, _stub_cooldown_seconds(settings))


def _check_and_send_stub_risk_alerts(metrics: dict[str, float]) -> None:
    settings = get_stub_alert_settings()
    lines: list[str] = []
    kinds: list[str] = []

    def maybe(kind: str, enabled_key: str, thresh_key: str, check, fmt) -> None:
        if not settings.get(enabled_key):
            return
        th = settings.get(thresh_key)
        if th is None:
            return
        if not _stub_can_fire_kind(settings, kind):
            return
        if check(float(th)):
            lines.append(fmt(float(th)))
            kinds.append(kind)

    maybe(
        "pluvial",
        "alert_pluvial_enabled",
        "alert_threshold_pluvial_pct",
        lambda t: metrics["pluvial_pct"] >= t,
        lambda t: (
            f"Inondations pluviales: risque {metrics['pluvial_pct']:.0f} % "
            f"(seuil {t:.0f} %)."
        ),
    )
    maybe(
        "fluvial",
        "alert_fluvial_enabled",
        "alert_threshold_fluvial_pct",
        lambda t: metrics["fluvial_pct"] >= t,
        lambda t: (
            f"Crues: probabilité {metrics['fluvial_pct']:.0f} % (seuil {t:.0f} %)."
        ),
    )
    maybe(
        "heatwave",
        "alert_heatwave_enabled",
        "alert_threshold_heatwave_humidex",
        lambda t: metrics["heatwave_humidex"] >= t,
        lambda t: (
            f"Canicule: humidex max. {metrics['heatwave_humidex']:.0f} (seuil {t:.0f})."
        ),
    )
    maybe(
        "snow",
        "alert_snow_enabled",
        "alert_threshold_snow_pct",
        lambda t: metrics["snow_pct"] >= t,
        lambda t: (
            f"Chute de neige: risque {metrics['snow_pct']:.0f} % (seuil {t:.0f} %)."
        ),
    )

    if not lines:
        return

    headline = "Alerte IRIU —\n" + "\n".join(lines) + "\nConsultez le tableau de bord."
    email = os.environ.get("AUTH_STUB_EMAIL")
    phone = os.environ.get("AUTH_STUB_PHONE")
    sms_sent = False
    email_sent = False
    if settings.get("alert_via_sms") and phone:
        sms_sent = send_sms(phone, headline)
    if settings.get("alert_via_email") and email:
        email_sent = send_email(
            to_email=email,
            subject="Alerte IRIU — risques météo",
            body=headline + "\n\n(Mode auth désactivé — alertes de test.)",
        )
    if sms_sent or email_sent:
        for k in kinds:
            update_stub_last_alert_sent(k)


def check_and_send_risk_alerts(
    db: Session, pluvial_geojson: dict | None = None
) -> None:
    if pluvial_geojson is None:
        pluvial_geojson = compute_all_hazard_zones(None)

    if auth_disabled():
        pluvial_pct = _max_pluvial_combined_from_geojson(pluvial_geojson)
        fluvial_pct = _max_crues_combined_from_geojson(pluvial_geojson)
        heatwave_humidex = _max_canicules_combined_from_geojson(pluvial_geojson)
        snow_pct = _max_neige_combined_from_geojson(pluvial_geojson)
        metrics = {
            "pluvial_pct": pluvial_pct,
            "fluvial_pct": fluvial_pct,
            "heatwave_humidex": heatwave_humidex,
            "snow_pct": snow_pct,
        }
        print(
            "[alerts] métriques (stub) "
            f"pluvial={metrics['pluvial_pct']:.1f}% "
            f"fluvial={metrics['fluvial_pct']:.1f}% "
            f"humidex={metrics['heatwave_humidex']:.1f} "
            f"neige={metrics['snow_pct']:.1f}%"
        )
        _check_and_send_stub_risk_alerts(metrics)
        return

    users = (
        db.query(User)
        .filter(
            or_(
                and_(
                    User.alert_pluvial_enabled == True,  # noqa: E712
                    User.alert_threshold_pluvial_pct.isnot(None),
                ),
                and_(
                    User.alert_fluvial_enabled == True,  # noqa: E712
                    User.alert_threshold_fluvial_pct.isnot(None),
                ),
                and_(
                    User.alert_heatwave_enabled == True,  # noqa: E712
                    User.alert_threshold_heatwave_humidex.isnot(None),
                ),
                and_(
                    User.alert_snow_enabled == True,  # noqa: E712
                    User.alert_threshold_snow_pct.isnot(None),
                ),
            )
        )
        .all()
    )
    print(f"[alerts] utilisateurs avec au moins une alerte configurée: {len(users)}")

    for user in users:
        metrics = _metrics_for_user(user, pluvial_geojson)
        print(
            f"[alerts] user_id={user.id} partner_city={user.partner_city!r} "
            f"pluvial={metrics['pluvial_pct']:.1f}% "
            f"fluvial={metrics['fluvial_pct']:.1f}% "
            f"humidex={metrics['heatwave_humidex']:.1f} "
            f"neige={metrics['snow_pct']:.1f}%"
        )
        lines, kinds = _collect_triggered_lines_for_user(user, metrics)
        if not lines:
            continue
        headline = (
            "Alerte IRIU —\n" + "\n".join(lines) + "\nConsultez le tableau de bord."
        )
        sms_sent = False
        email_sent = False
        if user.alert_via_sms and user.phone:
            sms_sent = send_sms(user.phone, headline)
        if user.alert_via_email and user.email:
            email_sent = send_email(
                to_email=user.email,
                subject="Alerte IRIU — risques météo",
                body=headline
                + "\n\n(Vous recevez ce message car les alertes email sont activées.)",
            )
        if sms_sent or email_sent:
            _update_last_alerts(db, user.id, kinds)
            print(f"[alerts] notification envoyée user_id={user.id} kinds={kinds}")


def run_risk_alerts_in_background(
    db_session_factory,
    pluvial_geojson: dict | None = None,
) -> None:
    def _run():
        db = db_session_factory()
        try:
            check_and_send_risk_alerts(db, pluvial_geojson)
        except Exception as e:
            print(f"[alerts] run_risk_alerts_in_background error: {e}")
        finally:
            db.close()

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def run_flood_alerts_in_background(
    db_session_factory, geojson: dict | None = None
) -> None:
    run_risk_alerts_in_background(db_session_factory, geojson)
