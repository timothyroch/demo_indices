"""
Abstract base classes and data structures for risk assessment.

To add a new risk type (e.g., snowfall), create a new module that
implements the RiskAssessor interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..providers import HeatwaveDailyForecast


@dataclass
class DayDetail:
    date: str
    temperature_max: float
    temperature_min: float
    prediction_value: float
    raw_prediction_value: float
    relative_humidity_max: float
    meets_criteria: bool


@dataclass
class RiskAssessment:
    risk_detected: bool
    risk_level: str  # "none", "moderate", "high"
    message: str
    heatwave_windows: list[dict] = field(default_factory=list)
    daily_details: list[DayDetail] = field(default_factory=list)
    territorial_risk_score: float | None = None


class RiskAssessor(ABC):
    """Abstract interface for risk evaluation on forecast data."""

    @abstractmethod
    def assess(
        self, forecasts: list[HeatwaveDailyForecast], adidu: str | None = None
    ) -> RiskAssessment:
        """Evaluate a list of daily forecasts and return a risk assessment.

        Args:
            forecasts: Ordered list of daily forecasts.
            adidu: Identifier for the zone being assessed.

        Returns:
            A RiskAssessment with risk level, affected windows, and daily details.
        """
