import joblib
import numpy as np
import pandas as pd

from ..constants.features import FLUVIAL_FLOODS_FEATURES
from ..constants.labels import (
    FLUVIAL_FEATURE_LABELS,
    FLUVIAL_FEATURE_UNITS,
    MEDIUM_INFLUENCE,
    STRONG_INFLUENCE,
    WEAK_INFLUENCE,
)
from ..providers import DailyFluvialForecast
from ..providers.open_meteo import open_meteo_provider
from ..services.water_levels_service import (
    get_daily_wl_history,
    get_latest_water_level,
    get_water_level_forecast,
)
from ..services.weather_service import get_historical_weather
from ..utils.preprocessing import build_weather_dataframe
from ..utils.scoring import combined_probability, get_zone_properties, get_zone_score

WEIGHTS = {
    "Water_Level": 0.609,
    "WL_change_3d": 0.154,
    "Rain_7d": 0.214,
    "Temp_5d_mean": 0.023,
}

GAMMA = 2
INTERCEPT = -3.3160865607447074

scaler = joblib.load("app/models/fluvial_scaler_V2.pkl")


def _is_valid_hazard_zone(adidu: str | None, hazard_type: str) -> bool:
    """
    Check if a zone has a valid hazard score (1-5) for the given hazard type.

    Args:
        adidu: Zone identifier
        hazard_type: Type of hazard (e.g., 'crues', 'pluvial')

    Returns:
        True if the zone has a valid score, False otherwise
    """
    if adidu is None:
        return True

    zone_props = get_zone_properties(adidu, hazard_type)
    val_key = f"val_{hazard_type}"
    val = zone_props.get(val_key)

    try:
        val_float = float(val)
        return 1 <= val_float <= 5
    except (TypeError, ValueError):
        return False


def predict_fluvial_flood(
    lat: float,
    lng: float,
    temp: float,
    precip: float,
    wl_history: pd.Series,
    weather_history: list[dict],
) -> float:
    df = _build_features(lat, lng, temp, precip, wl_history, weather_history)
    latest = df.iloc[-1:]
    X = latest[FLUVIAL_FLOODS_FEATURES]
    X_scaled = scaler.transform(X)

    return _score_to_probability(X_scaled[0])


def predict_detailed_fluvial_flood(
    lat: float, lng: float, temp: float, precip: float, adidu: str | None = None
) -> dict:
    """
    Predict current fluvial flood probability.
    Requires Water_Level, WL_change_3d, Rain_7d, Temp_5d_mean.
    """

    wl_history = get_daily_wl_history(lat, lng, days=7)
    df = _build_features(lat, lng, temp, precip, wl_history)

    latest = df.iloc[-1:]
    X = latest[FLUVIAL_FLOODS_FEATURES]

    X_scaled = scaler.transform(X)
    raw_probability = _score_to_probability(X_scaled[0])

    risk_score = get_zone_score(adidu, "crues") if adidu is not None else None

    is_valid_val_crues = _is_valid_hazard_zone(adidu, "crues")

    return {
        "probability": combined_probability(risk_score, raw_probability)
        if risk_score is not None and is_valid_val_crues
        else (0.0 if not is_valid_val_crues else raw_probability),
        "raw_probability": 0.0 if not is_valid_val_crues else raw_probability,
        "explainability": _get_explainability(X_scaled[0], latest),
        "risk_score": risk_score,
        "forecast": _get_forecast(lat, lng, risk_score) if is_valid_val_crues else [],
    }


def simulate_fluvial_flood_predictions(
    lat: float,
    lng: float,
    adidu: str | None,
    simulation_overrides: list[DailyFluvialForecast],
) -> list[dict]:
    # Fetch the real water-level forecast once as a fallback baseline
    water_forecasts = get_water_level_forecast(lat, lng, days=len(simulation_overrides))
    wl_by_date: dict[str, float | None] = {
        wf["date"]: wf.get("water_level") for wf in water_forecasts
    }

    # Normalize overrides to dicts
    overrides_dicts = [
        o
        if isinstance(o, dict)
        else {
            "date": o.date,
            "temperature_mean": o.temperature_mean,
            "precipitation": o.precipitation,
            "water_level": o.water_level,
        }
        for o in simulation_overrides
    ]

    wl_history = get_daily_wl_history(lat, lng, days=7)
    risk_score = get_zone_score(adidu, "crues") if adidu is not None else None

    is_valid_val_crues = _is_valid_hazard_zone(adidu, "crues")
    if not is_valid_val_crues:
        risk_score = None

    return _build_forecast(
        lat, lng, risk_score, overrides_dicts, wl_by_date, wl_history
    )


def _get_forecast(
    lat: float,
    lng: float,
    risk_score: float | None,
) -> list[dict]:
    weather_forecasts = open_meteo_provider.get_weather_forecast(lat, lng, days=7)
    water_forecasts = get_water_level_forecast(lat, lng, days=7)

    # Build a lookup keyed by date string
    wl_by_date: dict[str, float | None] = {
        wf["date"]: wf.get("water_level") for wf in water_forecasts
    }

    wl_history = get_daily_wl_history(lat, lng, days=7)
    return _build_forecast(
        lat, lng, risk_score, weather_forecasts, wl_by_date, wl_history
    )


def _build_forecast(
    lat: float,
    lng: float,
    risk_score: float | None,
    weather_days: list,
    wl_by_date: dict[str, float | None],
    wl_history: pd.Series,
) -> list[dict]:
    history = get_historical_weather(lat, lng, days=6)
    if weather_days and not isinstance(weather_days[0], dict):
        weather_days = [vars(f) for f in weather_days]

    rolling_wl = wl_history.copy()

    result = []
    for entry in weather_days:
        date = entry["date"]
        temp = entry["temperature_mean"]
        precip = entry["precipitation"]
        water_level = entry.get("water_level") or wl_by_date.get(date)

        if water_level is not None:
            rolling_wl[date] = water_level

        df = build_weather_dataframe(history, temp, precip)
        df = _engineer_features(df, rolling_wl)
        latest = df.iloc[-1:]

        X = latest[FLUVIAL_FLOODS_FEATURES]

        if X.isna().any().any():
            result.append(
                {
                    "date": date,
                    "temperature_mean": temp,
                    "precipitation": precip,
                    "water_level": water_level,
                    "prediction_value": None,
                    "raw_prediction_value": None,
                }
            )
            continue

        X_scaled = scaler.transform(X)
        raw_probability = _score_to_probability(X_scaled[0])
        fluvial_probability = (
            combined_probability(risk_score, raw_probability)
            if risk_score is not None
            else raw_probability
        )

        result.append(
            {
                "date": date,
                "temperature_mean": temp,
                "precipitation": precip,
                "water_level": water_level,
                "prediction_value": fluvial_probability,
                "raw_prediction_value": raw_probability,
            }
        )

    return result


def _build_features(
    lat: float,
    lng: float,
    temp: float,
    precip: float,
    wl_history: pd.Series,
    weather_history: list[dict] | None = None,
) -> pd.DataFrame:
    history = (
        weather_history
        if weather_history is not None
        else get_historical_weather(lat, lng, days=6)
    )
    df = build_weather_dataframe(history, temp, precip)

    if weather_history is None:
        obs = get_latest_water_level(lat=lat, lng=lng)
        if obs and obs.get("value") is not None:
            today = pd.Timestamp.now(tz="UTC").date().isoformat()
            wl_history = wl_history.copy()
            wl_history[today] = obs["value"]

    return _engineer_features(df, wl_history)


def _engineer_features(df: pd.DataFrame, wl_history: pd.Series) -> pd.DataFrame:
    df["Rain_7d"] = df["Précip. tot. (mm)"].rolling(7, min_periods=1).sum()
    df["Temp_5d_mean"] = df["Temp moy.(°C)"].rolling(5, min_periods=1).mean()

    if wl_history.empty:
        df["Water_Level"] = None
        df["WL_change_3d"] = None
    else:
        df["Water_Level"] = wl_history.iloc[-1]
        wl_change = (
            wl_history.iloc[-1] - wl_history.iloc[-4] if len(wl_history) >= 4 else None
        )
        df["WL_change_3d"] = wl_change

    return df


def _get_explainability(X_scaled: np.ndarray, latest: pd.DataFrame) -> list:
    contributions = []
    for i, col in enumerate(FLUVIAL_FLOODS_FEATURES):
        impact = GAMMA * WEIGHTS[col] * X_scaled[i]  # linear contribution to log-odds
        raw_value = float(latest[col].values[0])
        contributions.append((col, impact, raw_value))

    contributions.sort(key=lambda x: abs(x[1]), reverse=True)

    result = []
    for rank, (col, impact, raw_value) in enumerate(contributions, start=1):
        abs_impact = abs(impact)
        max_impact = max(abs(impact) for _, impact, _ in contributions) or 1.0

        if abs_impact >= 0.4:
            strength_label = STRONG_INFLUENCE
        elif abs_impact >= 0.2:
            strength_label = MEDIUM_INFLUENCE
        else:
            strength_label = WEAK_INFLUENCE

        direction = "up" if impact > 0 else "down"
        unit = FLUVIAL_FEATURE_UNITS.get(col, "")
        result.append(
            {
                "rank": rank,
                "label": FLUVIAL_FEATURE_LABELS.get(col, col),
                "value": round(raw_value, 2),
                "unit": unit,
                "weight_pct": round(abs(impact) / max_impact * 100, 1),
                "direction": direction,
                "direction_label": "↑" if direction == "up" else "↓",
                "strength_label": strength_label,
            }
        )

    return result


def _score_to_probability(X_scaled: np.ndarray) -> float:
    score = 0
    for i, col in enumerate(FLUVIAL_FLOODS_FEATURES):
        score += WEIGHTS[col] * X_scaled[i]

    score = GAMMA * score + INTERCEPT
    return 1 / (1 + np.exp(-score))
