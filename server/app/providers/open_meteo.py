from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from . import (
    DailyWeatherForecast,
    HeatwaveDailyForecast,
    HourlyPrecipitationPoint,
    SnowDailyForecast,
)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


class OpenMeteoProvider:
    def get_weather_forecast(
        self, lat: float, lng: float, days: int = 8
    ) -> list[DailyWeatherForecast]:
        params = {
            "latitude": lat,
            "longitude": lng,
            "daily": "temperature_2m_mean,precipitation_sum",
            "timezone": "America/Montreal",
            "forecast_days": days,
        }

        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("daily", {})

        results = []
        for date, temp, precip in zip(
            data.get("time", []),
            data.get("temperature_2m_mean", []),
            data.get("precipitation_sum", []),
        ):
            results.append(
                DailyWeatherForecast(
                    date=date,
                    temperature_mean=float(temp) if temp is not None else 0.0,
                    precipitation=float(precip) if precip is not None else 0.0,
                )
            )
        return results

    def get_daily_weather(self, lat: float, lng: float) -> tuple[float, float]:
        forecasts = self.get_weather_forecast(lat, lng, days=2)
        if not forecasts:
            raise ValueError("Open-Meteo forecast returned no data")
        today_local = datetime.now(ZoneInfo("America/Montreal")).date().isoformat()
        selected = next(
            (f for f in forecasts if str(f.date).startswith(today_local)), None
        )
        if selected is None:
            selected = forecasts[0]
        return float(selected.temperature_mean), float(selected.precipitation)

    def get_historical_weather_archive(
        self,
        lat: float,
        lng: float,
        start_date: str,
        end_date: str,
    ) -> list[DailyWeatherForecast]:
        params = {
            "latitude": lat,
            "longitude": lng,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_mean,precipitation_sum",
            "timezone": "America/Montreal",
        }

        resp = requests.get(
            OPEN_METEO_ARCHIVE_URL,
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("daily", {})

        results = []
        for date, temp, precip in zip(
            data.get("time", []),
            data.get("temperature_2m_mean", []),
            data.get("precipitation_sum", []),
        ):
            results.append(
                DailyWeatherForecast(
                    date=str(date),
                    temperature_mean=float(temp) if temp is not None else 0.0,
                    precipitation=float(precip) if precip is not None else 0.0,
                )
            )

        return results

    def get_heatwave_forecast(
        self, lat: float, lng: float, days: int = 7
    ) -> list[HeatwaveDailyForecast]:
        params = {
            "latitude": lat,
            "longitude": lng,
            "hourly": "dew_point_2m",
            "daily": "temperature_2m_max,temperature_2m_min,relative_humidity_2m_max",
            "timezone": "America/Montreal",
            "forecast_days": days,
        }

        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        dates = data["daily"]["time"]
        tmax_list = data["daily"]["temperature_2m_max"]
        tmin_list = data["daily"]["temperature_2m_min"]
        rh_max_list = data["daily"].get("relative_humidity_2m_max", [])

        hourly_times = data["hourly"]["time"]
        hourly_dew = data["hourly"]["dew_point_2m"]

        results: list[HeatwaveDailyForecast] = []

        for i, date in enumerate(dates):
            # Find the maximum dew point for this day from hourly data
            day_dews = [
                hourly_dew[j]
                for j, ht in enumerate(hourly_times)
                if ht.startswith(date)
            ]
            max_dew = max(day_dews) if day_dews else 0.0
            rh_max = (
                float(rh_max_list[i])
                if i < len(rh_max_list) and rh_max_list[i] is not None
                else 50.0
            )

            results.append(
                HeatwaveDailyForecast(
                    date=date,
                    temperature_max=tmax_list[i],
                    temperature_min=tmin_list[i],
                    max_dew_point=max_dew,
                    relative_humidity_max=rh_max,
                )
            )

        return results

    def get_snow_forecast(
        self, lat: float, lng: float, days: int = 8
    ) -> list[SnowDailyForecast]:
        params = {
            "latitude": lat,
            "longitude": lng,
            "daily": (
                "temperature_2m_mean,temperature_2m_min,precipitation_sum,"
                "snowfall_sum,relative_humidity_2m_max"
            ),
            "timezone": "America/Montreal",
            "forecast_days": days,
        }
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("daily", {})
        times = data.get("time", [])
        temp_mean = data.get("temperature_2m_mean", [])
        temp_min = data.get("temperature_2m_min", [])
        precip = data.get("precipitation_sum", [])
        snowfall_mm = data.get("snowfall_sum", [])
        rh_max = data.get("relative_humidity_2m_max", [])

        def _val(arr: list, i: int, default: float = 0.0) -> float:
            if not arr or i >= len(arr) or arr[i] is None:
                return default
            return float(arr[i])

        results: list[SnowDailyForecast] = []
        for i, date in enumerate(times):
            snow_cm = _val(snowfall_mm, i)
            results.append(
                SnowDailyForecast(
                    date=date,
                    temperature_mean=_val(temp_mean, i),
                    temperature_min=_val(temp_min, i),
                    precipitation_sum=_val(precip, i),
                    snowfall_sum=snow_cm,
                    relative_humidity_max=_val(rh_max, i, 50.0),
                )
            )
        return results

    def get_today_hourly_precipitation(
        self, lat: float, lng: float
    ) -> list[HourlyPrecipitationPoint]:
        today_local = datetime.now(ZoneInfo("America/Montreal")).date().isoformat()

        params = {
            "latitude": lat,
            "longitude": lng,
            "hourly": "precipitation,temperature_2m",
            "timezone": "America/Montreal",
            "forecast_days": 2,
        }

        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("hourly", {})

        times = data.get("time", [])
        precipitations = data.get("precipitation", [])
        temperatures = data.get("temperature_2m", [])

        results = []
        for dt, precip, temp in zip(times, precipitations, temperatures):
            if not str(dt).startswith(today_local):
                continue
            results.append(
                {
                    "datetime": str(dt),
                    "precipitation": float(precip) if precip is not None else 0.0,
                    "temperature": float(temp) if temp is not None else 0.0,
                }
            )

        return results


open_meteo_provider: OpenMeteoProvider = OpenMeteoProvider()
