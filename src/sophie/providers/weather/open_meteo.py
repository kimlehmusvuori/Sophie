"""Open-Meteo weather provider — free, no API key required. Coarse,
user-configured lat/lon only (see docs/PRIVACY.md). Any network failure
degrades to an empty forecast rather than raising, per docs/PRODUCT_SPEC.md
§40 ("If weather is unavailable, planning must continue normally")."""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

import httpx

from sophie.domain.weather_types import WeatherDay

_BASE_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT_S = 8.0

_WMO_CONDITION = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherProvider(Protocol):
    def get_forecast(self, lat: float, lon: float, start: date, end: date) -> list[WeatherDay]: ...


class OpenMeteoProvider:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def get_forecast(self, lat: float, lon: float, start: date, end: date) -> list[WeatherDay]:
        params: dict[str, str | float] = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
            "windspeed_10m_max,relative_humidity_2m_mean,weathercode",
            "timezone": "auto",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        try:
            if self._client is not None:
                response = self._client.get(_BASE_URL, params=params, timeout=_TIMEOUT_S)
            else:
                response = httpx.get(_BASE_URL, params=params, timeout=_TIMEOUT_S)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return []

        return _parse_daily(payload)


def _parse_daily(payload: dict) -> list[WeatherDay]:
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        return []
    dates = daily.get("time") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    precip = daily.get("precipitation_sum") or []
    wind = daily.get("windspeed_10m_max") or []
    humidity = daily.get("relative_humidity_2m_mean") or []
    codes = daily.get("weathercode") or []

    days: list[WeatherDay] = []
    for i, day_str in enumerate(dates):
        try:
            for_date = datetime.strptime(day_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        temp_c = None
        if i < len(tmax) and i < len(tmin) and tmax[i] is not None and tmin[i] is not None:
            temp_c = round((tmax[i] + tmin[i]) / 2, 1)
        code = codes[i] if i < len(codes) else None
        days.append(
            WeatherDay(
                for_date=for_date,
                temp_c=temp_c,
                humidity_pct=humidity[i] if i < len(humidity) else None,
                precip_mm=precip[i] if i < len(precip) else None,
                wind_kph=wind[i] if i < len(wind) else None,
                condition_summary=_WMO_CONDITION.get(code) if code is not None else None,
            )
        )
    return days
