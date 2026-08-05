import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb

from ..constants.features import PLUVIAL_FLOODS_FEATURES
from ..constants.labels import (
    MEDIUM_INFLUENCE,
    PLUVIAL_FEATURE_LABELS,
    PLUVIAL_FEATURE_UNITS,
    STRONG_INFLUENCE,
    WEAK_INFLUENCE,
)
from ..providers import DailyWeatherForecast
from ..providers.open_meteo import open_meteo_provider
from ..services.weather_service import get_historical_weather
from ..utils.preprocessing import build_weather_dataframe
from ..utils.scoring import combined_probability, get_zone_score

FLOOD_MODEL_PATH = "app/models/xgb_pluvial_flood_model.pkl"

pluvial_flood_model = joblib.load(FLOOD_MODEL_PATH)
explainer = shap.TreeExplainer(pluvial_flood_model)


def predict_pluvial_flood(
    lat: float,
    lng: float,
    temp: float,
    precip: float,
    history: list[dict],
) -> float:
    X, _ = _build_features(lat, lng, temp, precip, history)
    return float(pluvial_flood_model.predict_proba(X)[0, 1])


def predict_detailed_pluvial_flood(
    lat: float, lng: float, temp: float, precip: float, adidu: str | None = None
) -> dict:
    X, latest_row = _build_features(lat, lng, temp, precip)
    raw_probability = float(pluvial_flood_model.predict_proba(X)[0, 1])

    risk_score = get_zone_score(adidu, "pluvial") if adidu is not None else None

    pluvial_probability = (
        combined_probability(risk_score, raw_probability)
        if risk_score is not None
        else raw_probability
    )

    shap_values = explainer.shap_values(X)[0]

    return {
        "probability": pluvial_probability,
        "raw_probability": raw_probability,
        "confidence_std": _get_tree_std(X),
        "explainability": _get_shap_explainability(shap_values, X, latest_row),
        "risk_score": risk_score,
        "forecast": _get_forecast(lat, lng, risk_score),
        "rain_intensity_info": _get_rain_intensity_info(lat, lng),
    }


def simulate_pluvial_flood_predictions(
    lat: float,
    lng: float,
    adidu: str | None,
    simulation_overrides: list[DailyWeatherForecast],
) -> list[dict]:
    risk_score = get_zone_score(adidu, "pluvial") if adidu is not None else None
    return _get_forecast(lat, lng, risk_score, simulation_overrides)


def _get_forecast(
    lat: float,
    lng: float,
    risk_score: float,
    simulation_overrides: list[DailyWeatherForecast] | None = None,
) -> list[dict]:
    if simulation_overrides:
        forecasts = simulation_overrides
    else:
        forecasts = open_meteo_provider.get_weather_forecast(lat, lng, days=7)

    history = get_historical_weather(lat, lng, days=6)

    if forecasts and not isinstance(forecasts[0], dict):
        forecasts = [vars(f) for f in forecasts]

    result = []
    for f in forecasts:
        temp = f["temperature_mean"]
        precip = f["precipitation"]
        date = f["date"]

        X, _ = _build_features(lat, lng, temp, precip, history)
        raw_probabilty = float(pluvial_flood_model.predict_proba(X)[0, 1])
        result.append(
            {
                "date": date,
                "temperature_mean": temp,
                "precipitation": precip,
                "prediction_value": combined_probability(risk_score, raw_probabilty),
                "raw_prediction_value": raw_probabilty,
            }
        )
    return result


def _build_features(
    lat: float, lng: float, temp: float, precip: float, history=None
) -> pd.DataFrame:
    if history is None:
        history = get_historical_weather(lat, lng, days=6)
    df = build_weather_dataframe(history, temp, precip)
    df = _engineer_features(df)
    latest = df.iloc[-1:]
    X = latest[PLUVIAL_FLOODS_FEATURES]
    X = pd.get_dummies(X, columns=["Season"], drop_first=True)
    expected_cols = pluvial_flood_model.get_booster().feature_names
    for col in expected_cols:
        if col not in X.columns:
            X[col] = 0
    return X[expected_cols], df.iloc[-1:]


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df["rain_1d"] = df["Précip. tot. (mm)"]
    df["rain_3d"] = df["Précip. tot. (mm)"].rolling(3, min_periods=1).sum()
    df["rain_5d"] = df["Précip. tot. (mm)"].rolling(5, min_periods=1).sum()
    df["rain_7d"] = df["Précip. tot. (mm)"].rolling(7, min_periods=1).sum()
    df["rain_intensity"] = df["rain_1d"] / (df["rain_7d"] + 1)
    df["Temp_diff_2d"] = df["Temp moy.(°C)"].diff(2)
    df["is_freezing"] = (df["Temp moy.(°C)"] <= 0).astype(int)
    return df


def _get_shap_explainability(shap_values, X, latest_row: pd.DataFrame) -> list:
    features = []
    for feature_name, impact in zip(X.columns, shap_values):
        if abs(impact) < 0.3:
            continue
        features.append((feature_name, float(impact)))

    features.sort(key=lambda x: abs(x[1]), reverse=True)
    max_impact = max(abs(impact) for _, impact in features) or 1.0

    result = []
    for rank, (feature_name, impact) in enumerate(features, start=1):
        abs_impact = abs(impact)
        if abs_impact >= 1:
            strength_label = STRONG_INFLUENCE
        elif abs_impact >= 0.6:
            strength_label = MEDIUM_INFLUENCE
        else:
            strength_label = WEAK_INFLUENCE

        direction = "up" if impact > 0 else "down"
        result.append(
            {
                "rank": rank,
                "label": PLUVIAL_FEATURE_LABELS.get(feature_name, feature_name),
                "value": round(float(latest_row[feature_name].values[0]), 2)
                if feature_name in latest_row.columns
                else None,
                "unit": PLUVIAL_FEATURE_UNITS.get(feature_name, ""),
                "weight_pct": round(abs_impact / max_impact * 100, 1),
                "direction": direction,
                "direction_label": "↑" if direction == "up" else "↓",
                "strength_label": strength_label,
            }
        )

    return result


def _get_tree_std(X: pd.DataFrame) -> float:
    "Probability std as trees are added one by one during boosting"
    booster = pluvial_flood_model.get_booster()
    dmatrix = xgb.DMatrix(X)
    n_trees = booster.num_boosted_rounds()
    tree_probs = []
    for i in range(1, n_trees + 1):
        margin = booster.predict(dmatrix, output_margin=True, iteration_range=(0, i))
        prob = float(1 / (1 + np.exp(-margin[0])))
        tree_probs.append(prob)
    return float(np.std(tree_probs))


def _get_rain_intensity_info(lat: float, lng: float) -> dict:
    hourly_prec = open_meteo_provider.get_today_hourly_precipitation(lat, lng)

    if not hourly_prec:
        return {"level": "unknown", "label": "données indisponibles", "info": None}

    hourly_rain = [h for h in hourly_prec if h.get("temperature", 1.0) > 0.0]
    hourly_values = [float(h["precipitation"]) for h in hourly_rain]
    total_precip = sum(hourly_values)

    if total_precip == 0:
        return {"level": "none", "label": "Aucune pluie", "info": None}

    max_hourly = round(max(hourly_values), 1)
    max_3h = round(
        max(
            sum(hourly_values[max(0, i - 2) : i + 1]) for i in range(len(hourly_values))
        ),
        1,
    )

    info_short = f"Intensité maximale de {max_hourly} mm/h"
    info_long = f"{info_short} ({max_3h} mm sur 3 h)"

    # Partially determined from ECCC:
    # Defines thresholds: light ≤2.5, moderate 2.6-7.5, heavy ≥7.6 mm/h
    if max_hourly >= 40 or max_3h >= 60:
        level, label, info = "extreme", "Pluie diluvienne extrême", info_long
    elif max_hourly >= 25 or max_3h >= 40:
        level, label, info = "torrential", "Pluie diluvienne", info_long
    elif max_hourly >= 7.6:
        level, label, info = "heavy", "Fortes pluies", info_long
    elif max_hourly >= 2.6:
        level, label, info = "moderate", "Pluie modérée", info_short
    else:
        level, label, info = "light", "Pluie faible", info_short

    return {"level": level, "label": label, "info": info}
