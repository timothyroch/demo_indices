from dataclasses import asdict, dataclass, field, replace

from ..providers import SnowDailyForecast
from ..utils.scoring import combined_probability, get_zone_score

SUMMER_MONTHS = {6, 7, 8, 9}
MIN_SNOW_CM_FOR_NEXT_DAY_INCREMENT = 8.0


@dataclass
class SnowDayDetail:
    date: str
    total_snow_cm: float
    mean_temperature: float
    prediction_value: float
    raw_prediction_value: float
    risk_base: float = 0.0
    inc_temp: float = 0.0
    inc_humidity: float = 0.0
    inc_forecast: float = 0.0
    inc_quartile: float = 0.0
    small_snow: float = 0.0
    quartile_label: str = ""


@dataclass
class SnowAssessment:
    risk_detected: bool
    risk_level: str
    risk_score: float | None
    message: str
    daily_details: list[SnowDayDetail] = field(default_factory=list)


def no_snow_forecast_assessment() -> SnowAssessment:
    return SnowAssessment(
        risk_detected=False,
        risk_level="none",
        risk_score=None,
        message="Aucune prévision disponible.",
        daily_details=[],
    )


def _month_from_date(date_str: str) -> int:
    try:
        return int(date_str.split("-")[1])
    except (IndexError, ValueError):
        return 0


def _is_summer_month(month: int) -> bool:
    return month in SUMMER_MONTHS


def _compute_snow_risk(
    forecasts: list[SnowDailyForecast], risk_score: float | None
) -> list[SnowDayDetail]:
    details: list[SnowDayDetail] = []
    for i, f in enumerate(forecasts):
        month = _month_from_date(f.date)
        snow = max(0.0, f.snowfall_sum)
        temp = f.temperature_mean
        hum = max(0, min(100, f.relative_humidity_max))
        n1 = forecasts[i + 1].snowfall_sum if i + 1 < len(forecasts) else 0.0
        snow_next = max(0.0, n1)
        snow_prev = max(0.0, forecasts[i - 1].snowfall_sum if i > 0 else 0.0)
        snow_prev2 = max(0.0, forecasts[i - 2].snowfall_sum if i > 1 else 0.0)

        accum_2d_back = snow_prev + snow
        accum_3d_back = snow_prev2 + snow_prev + snow

        if month in (6, 7, 8, 9):
            risk = 0.0
            base = inc_temp = inc_hum = inc_forecast = inc_quartile = small_snow = 0.0
            quartile_label = ""
        else:
            base = 0.0
            if snow > 10 or accum_2d_back >= 15.0 or accum_3d_back >= 20.0:
                base = max(base, 0.20)

            apply_inc = snow >= 10.0 or accum_2d_back >= 15.0 or accum_3d_back >= 20.0
            inc_temp = (0.10 if -10 <= temp <= 0 else 0.0) if apply_inc else 0.0
            inc_hum = min(0.08, hum * 0.0008) if apply_inc else 0.0
            inc_forecast = (
                min(0.10, snow_next * 0.005)
                if apply_inc and snow >= MIN_SNOW_CM_FOR_NEXT_DAY_INCREMENT
                else 0.0
            )

            if not apply_inc:
                inc_quartile = 0.0
                quartile_label = ""
            elif snow <= 8.2:
                inc_quartile = 0.0
                quartile_label = "1er quartile (0–8,2 cm)"
            elif snow <= 12.8:
                inc_quartile = 0.05
                quartile_label = "2e quartile (8,3–12,8 cm)"
            elif snow <= 20.5:
                inc_quartile = 0.10
                quartile_label = "3e quartile (12,9–20,5 cm)"
            else:
                inc_quartile = 0.15
                quartile_label = "4e quartile (>20,5 cm)"

            if not apply_inc and snow > 0:
                small_snow = min(0.10, snow * 0.02)
            else:
                small_snow = 0.0

            risk = min(
                1.0,
                base + inc_temp + inc_hum + inc_forecast + inc_quartile + small_snow,
            )
            if snow == 0:
                risk = 0.0

        details.append(
            SnowDayDetail(
                date=f.date,
                total_snow_cm=round(snow, 1),
                mean_temperature=round(temp, 1),
                prediction_value=combined_probability(
                    risk_score if risk_score is not None else 0.0, round(risk, 4)
                ),
                raw_prediction_value=round(risk, 4),
                risk_base=round(base, 4) if _is_summer_month(month) else 0.0,
                inc_temp=round(inc_temp, 4) if _is_summer_month(month) else 0.0,
                inc_humidity=round(inc_hum, 4) if _is_summer_month(month) else 0.0,
                inc_forecast=(
                    round(inc_forecast, 4) if _is_summer_month(month) else 0.0
                ),
                inc_quartile=(
                    round(inc_quartile, 4) if _is_summer_month(month) else 0.0
                ),
                small_snow=round(small_snow, 4) if _is_summer_month(month) else 0.0,
                quartile_label=quartile_label if _is_summer_month(month) else "",
            )
        )
    return details


def assess_snow_risk(
    forecasts: list[SnowDailyForecast], adidu: str | None = None
) -> SnowAssessment:
    if not forecasts:
        return no_snow_forecast_assessment()
    risk_score = get_zone_score(adidu, "neige") if adidu is not None else None
    daily_details = _compute_snow_risk(forecasts, risk_score)
    max_risk = max(d.prediction_value for d in daily_details)
    days_above_20 = sum(1 for d in daily_details if d.prediction_value >= 0.20)

    if max_risk < 0.20:
        risk_level = "none"
        message = "Risque faible de neige dans les prochains jours."
    elif max_risk >= 0.50:
        risk_level = "high"
        message = f"Risque élevé de neige (probabilité jusqu'à {max_risk * 100:.0f} %)."
    else:
        risk_level = "moderate"
        message = f"Risque modéré de neige ({days_above_20} jour(s) à ≥20 %)."

    return SnowAssessment(
        risk_detected=max_risk >= 0.20,
        risk_level=risk_level,
        risk_score=risk_score,
        message=message,
        daily_details=daily_details,
    )


def simulate_snow_predictions(
    forecasts: list[SnowDailyForecast],
    adidu: str,
    simulation_overrides: list[dict],
):
    if not forecasts:
        return no_snow_forecast_assessment()

    overrides_by_date = {
        override["date"]: override for override in simulation_overrides
    }

    simulated_forecasts = []
    for forecast in forecasts:
        override = overrides_by_date.get(forecast.date)

        if override:
            # Humidity kept from original forecast (override doesn't include it)
            simulated_forecasts.append(
                replace(
                    forecast,
                    snowfall_sum=float(override["total_snow_cm"]),
                    temperature_mean=float(override["mean_temperature"]),
                )
            )
        else:
            simulated_forecasts.append(forecast)

    assessment = assess_snow_risk(simulated_forecasts, adidu)
    return [asdict(d) for d in assessment.daily_details]
