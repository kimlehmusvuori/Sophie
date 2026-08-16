from __future__ import annotations

from sophie.config.settings import Settings


def test_blank_weather_lat_lon_do_not_crash():
    """Regression test: a freshly-copied .env.example ships WEATHER_LAT/LON
    as blank strings, which pydantic-settings otherwise passes straight
    through and fails float parsing on."""
    settings = Settings(
        weather_lat="", weather_lon="", ms_graph_client_id=None, openai_api_key=None
    )
    assert settings.weather_lat is None
    assert settings.weather_lon is None
    assert settings.weather_configured is False


def test_numeric_weather_lat_lon_still_parse():
    settings = Settings(weather_lat="60.17", weather_lon="24.94")
    assert settings.weather_lat == 60.17
    assert settings.weather_lon == 24.94
    assert settings.weather_configured is True


def test_llm_and_calendar_configured_flags():
    unconfigured = Settings(openai_api_key=None, ms_graph_client_id=None)
    assert unconfigured.llm_configured is False
    assert unconfigured.calendar_configured is False

    configured = Settings(openai_api_key="sk-x", ms_graph_client_id="abc")
    assert configured.llm_configured is True
    assert configured.calendar_configured is True
