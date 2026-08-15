from __future__ import annotations

from datetime import date

from sophie.repositories import profile_repo, weather_repo
from sophie.services.weather_service import refresh_weather_for_range


class _FakeProvider:
    def __init__(self, days):
        self._days = days

    def get_forecast(self, lat, lon, start, end):
        return self._days


def test_no_op_when_location_not_configured(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    written = refresh_weather_for_range(
        db_session, profile.id, _FakeProvider([]), date(2026, 8, 17), date(2026, 8, 18)
    )
    assert written == 0


def test_persists_forecast_when_location_configured(db_session):
    from sophie.domain.weather_types import WeatherDay

    profile = profile_repo.get_or_create_profile(db_session)
    profile_repo.update_config(db_session, profile.id, weather_lat=60.17, weather_lon=24.94)

    fake_days = [
        WeatherDay(date(2026, 8, 17), 20.0, 50.0, 0.0, 10.0, "Clear sky"),
    ]
    written = refresh_weather_for_range(
        db_session, profile.id, _FakeProvider(fake_days), date(2026, 8, 17), date(2026, 8, 17)
    )
    assert written == 1
    snapshots = weather_repo.list_weather_for_range(
        db_session, profile.id, date(2026, 8, 17), date(2026, 8, 17)
    )
    assert len(snapshots) == 1
    assert snapshots[0].temp_c == 20.0
