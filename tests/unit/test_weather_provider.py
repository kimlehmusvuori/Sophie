from __future__ import annotations

from datetime import date

import httpx

from sophie.providers.weather.open_meteo import OpenMeteoProvider

SAMPLE_RESPONSE = {
    "daily": {
        "time": ["2026-08-17", "2026-08-18"],
        "temperature_2m_max": [22.0, 25.0],
        "temperature_2m_min": [12.0, 14.0],
        "precipitation_sum": [0.0, 3.2],
        "windspeed_10m_max": [10.0, 18.0],
        "relative_humidity_2m_mean": [55.0, 70.0],
        "weathercode": [1, 61],
    }
}


def test_open_meteo_parses_forecast():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_RESPONSE)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenMeteoProvider(client=client)

    days = provider.get_forecast(60.17, 24.94, date(2026, 8, 17), date(2026, 8, 18))

    assert len(days) == 2
    assert days[0].temp_c == 17.0
    assert days[0].condition_summary == "Mainly clear"
    assert days[1].condition_summary == "Slight rain"


def test_open_meteo_network_failure_returns_empty_list():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("boom", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenMeteoProvider(client=client)

    days = provider.get_forecast(60.17, 24.94, date(2026, 8, 17), date(2026, 8, 18))
    assert days == []


def test_open_meteo_malformed_response_returns_empty_list():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenMeteoProvider(client=client)

    days = provider.get_forecast(60.17, 24.94, date(2026, 8, 17), date(2026, 8, 18))
    assert days == []
