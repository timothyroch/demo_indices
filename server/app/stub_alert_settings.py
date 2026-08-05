from datetime import datetime, timezone

_STUB_ALERT_SETTINGS: dict = {
    "alert_pluvial_enabled": False,
    "alert_fluvial_enabled": False,
    "alert_heatwave_enabled": False,
    "alert_snow_enabled": False,
    "alert_threshold_pluvial_pct": 50.0,
    "alert_threshold_fluvial_pct": 50.0,
    "alert_threshold_heatwave_humidex": 41.0,
    "alert_threshold_snow_pct": 20.0,
    "alert_via_sms": True,
    "alert_via_email": False,
    "alert_frequency_hours": 4,
    "last_pluvial_alert_sent_at": None,
    "last_fluvial_alert_sent_at": None,
    "last_heatwave_alert_sent_at": None,
    "last_snow_alert_sent_at": None,
}


def get_stub_alert_settings() -> dict:
    return _STUB_ALERT_SETTINGS.copy()


def update_stub_alert_settings(updates: dict) -> None:
    for k, v in updates.items():
        if k in _STUB_ALERT_SETTINGS:
            _STUB_ALERT_SETTINGS[k] = v


def update_stub_last_alert_sent(alert_kind: str) -> None:
    key = {
        "pluvial": "last_pluvial_alert_sent_at",
        "fluvial": "last_fluvial_alert_sent_at",
        "heatwave": "last_heatwave_alert_sent_at",
        "snow": "last_snow_alert_sent_at",
    }.get(alert_kind)
    if not key:
        return
    _STUB_ALERT_SETTINGS[key] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S+00:00"
    )
