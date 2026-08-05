from dataclasses import dataclass


@dataclass
class HeatwaveDailyForecast:
    """One day of weather forecast data."""

    date: str
    temperature_max: float  # °C
    temperature_min: float  # °C
    max_dew_point: float  # °C  (daily max dew point, used for Humidex)
    relative_humidity_max: float  # 0–100


@dataclass
class DailyWeatherForecast:
    date: str
    temperature_mean: float
    precipitation: float


@dataclass
class SnowDailyForecast:
    """One day of forecast for snow risk (rule-based)."""

    date: str
    temperature_mean: float  # °C
    temperature_min: float  # °C
    precipitation_sum: float  # mm
    snowfall_sum: float  # cm (Open-Meteo returns mm; we convert to cm in provider)
    relative_humidity_max: float  # 0–100


@dataclass
class DailyFluvialForecast(DailyWeatherForecast):
    water_level: float


@dataclass
class HourlyPrecipitationPoint:
    datetime: str
    precipitation: float
