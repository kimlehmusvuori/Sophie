"""Fetches and persists weather snapshots for a date range, using the
profile's configured coarse location. No-ops gracefully (no exception) when
location isn't configured or the provider returns nothing."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from sophie.providers.weather.open_meteo import WeatherProvider
from sophie.repositories import profile_repo, weather_repo


def refresh_weather_for_range(
    session: Session, profile_id: str, provider: WeatherProvider, start: date, end: date
) -> int:
    """Returns the number of days written. 0 if location isn't configured or
    the provider couldn't be reached — never raises."""

    config = profile_repo.get_config(session, profile_id)
    if config.weather_lat is None or config.weather_lon is None:
        return 0

    days = provider.get_forecast(config.weather_lat, config.weather_lon, start, end)
    now = datetime.now(UTC)
    for day in days:
        weather_repo.upsert_weather_snapshot(
            session,
            profile_id,
            day.for_date,
            location_name=config.weather_location_name,
            lat_rounded=round(config.weather_lat, 2),
            lon_rounded=round(config.weather_lon, 2),
            temp_c=day.temp_c,
            humidity_pct=day.humidity_pct,
            precip_mm=day.precip_mm,
            wind_kph=day.wind_kph,
            condition_summary=day.condition_summary,
            fetched_at=now,
            provider="open-meteo",
        )
    return len(days)
