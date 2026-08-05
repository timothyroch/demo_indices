"""
Heatwave risk assessor using the Gold Standard criteria.

Condition (must be met for 2 consecutive days):
    (Tmax >= 32°C AND Tmin >= 20°C) OR (Humidex >= 41)
"""

from ..providers import HeatwaveDailyForecast
from ..utils import compute_humidex
from ..utils.scoring import combined_humidex, get_zone_score
from . import DayDetail, RiskAssessment, RiskAssessor

# Thresholds — easy to adjust or override
TMAX_THRESHOLD = 32.0
TMIN_THRESHOLD = 20.0
HUMIDEX_THRESHOLD = 41.0
CONSECUTIVE_DAYS = 2


class HeatwaveAssessor(RiskAssessor):
    """Assess heatwave risk based on the Strict Combined criteria."""

    def assess(
        self, forecasts: list[HeatwaveDailyForecast], adidu: str | None = None
    ) -> RiskAssessment:
        daily_details: list[DayDetail] = []

        risk_score = get_zone_score(adidu, "canicule") if adidu is not None else 0.0

        for f in forecasts:
            humidex = compute_humidex(f.temperature_max, f.max_dew_point)
            temp_condition = (
                f.temperature_max >= TMAX_THRESHOLD
                and f.temperature_min >= TMIN_THRESHOLD
            )
            humidex_condition = humidex >= HUMIDEX_THRESHOLD
            meets = temp_condition or humidex_condition

            daily_details.append(
                DayDetail(
                    date=f.date,
                    temperature_max=round(f.temperature_max, 1),
                    temperature_min=round(f.temperature_min, 1),
                    prediction_value=combined_humidex(risk_score, humidex),
                    raw_prediction_value=humidex,
                    relative_humidity_max=round(f.relative_humidity_max, 1),
                    meets_criteria=meets,
                )
            )

        # 2-day rolling window detection
        heatwave_windows: list[dict] = []
        for i in range(len(daily_details) - (CONSECUTIVE_DAYS - 1)):
            window = daily_details[i : i + CONSECUTIVE_DAYS]
            if all(d.meets_criteria for d in window):
                heatwave_windows.append(
                    {
                        "start": window[0].date,
                        "end": window[-1].date,
                        "peak_humidex": max(d.prediction_value for d in window),
                    }
                )

        # Determine risk level
        if not heatwave_windows:
            risk_level = "none"
            message = "Aucune canicule prévue dans les 7 prochains jours."
        else:
            peak = max(w["peak_humidex"] for w in heatwave_windows)
            # First window start date
            first_start = heatwave_windows[0]["start"]
            if peak >= 45:
                risk_level = "high"
                message = (
                    f"Canicule sévère prévue à partir du {first_start} "
                    f"(Humidex {peak})."
                )
            else:
                risk_level = "moderate"
                message = f"Canicule prévue à partir du {first_start} (Humidex {peak})."

        return RiskAssessment(
            risk_detected=len(heatwave_windows) > 0,
            risk_level=risk_level,
            message=message,
            heatwave_windows=heatwave_windows,
            daily_details=daily_details,
            territorial_risk_score=risk_score,
        )
