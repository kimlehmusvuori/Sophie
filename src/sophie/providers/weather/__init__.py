"""Weather provider abstraction. Uses an explicitly user-configured coarse
location (city/approximate area/manual lat-lon) — never inferred from
historical GPS routes. If weather is unavailable, planning proceeds without
it. See docs/PRODUCT_SPEC.md §39-40 and docs/PRIVACY.md."""

from sophie.providers.weather.open_meteo import OpenMeteoProvider, WeatherProvider

__all__ = ["OpenMeteoProvider", "WeatherProvider"]
