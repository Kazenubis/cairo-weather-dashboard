"""
Weather lookup logic for the Cairo-first Weather Dashboard — a "weather
dashboard" backlog item that defaults to Cairo (home base) but works for
any city. Uses Open-Meteo (free, no API key) for geocoding + forecast,
with the same live-API-with-offline-fallback pattern as this portfolio's
other API-integration projects: this sandbox has no outbound network
access, so the offline sample data is what genuinely runs here.
"""

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes (used by Open-Meteo) -> a short human label. Not
# exhaustive, but covers the common cases; anything unmapped falls back
# to "Unknown conditions" rather than raising.
WEATHER_CODE_LABELS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm",
}

# Offline sample data, keyed by lowercase city name — representative
# seasonal conditions rather than scraped/live data, clearly labeled as
# such in the UI. Cairo gets a hot, dry, clear-sky profile; the other two
# are here to prove the tool isn't just hardcoded to one city.
OFFLINE_SAMPLE_DATA = {
    "cairo": {
        "city": "Cairo", "country": "Egypt",
        "current": {"temp_c": 34.0, "weather_code": 0},
        "forecast": [
            {"day_offset": 1, "temp_max_c": 35.0, "temp_min_c": 23.0, "weather_code": 0},
            {"day_offset": 2, "temp_max_c": 36.0, "temp_min_c": 24.0, "weather_code": 1},
            {"day_offset": 3, "temp_max_c": 33.0, "temp_min_c": 22.0, "weather_code": 2},
        ],
    },
    "london": {
        "city": "London", "country": "United Kingdom",
        "current": {"temp_c": 14.0, "weather_code": 61},
        "forecast": [
            {"day_offset": 1, "temp_max_c": 15.0, "temp_min_c": 9.0, "weather_code": 3},
            {"day_offset": 2, "temp_max_c": 13.0, "temp_min_c": 8.0, "weather_code": 61},
            {"day_offset": 3, "temp_max_c": 16.0, "temp_min_c": 10.0, "weather_code": 2},
        ],
    },
    "seoul": {
        "city": "Seoul", "country": "South Korea",
        "current": {"temp_c": 8.0, "weather_code": 71},
        "forecast": [
            {"day_offset": 1, "temp_max_c": 5.0, "temp_min_c": -2.0, "weather_code": 73},
            {"day_offset": 2, "temp_max_c": 3.0, "temp_min_c": -4.0, "weather_code": 71},
            {"day_offset": 3, "temp_max_c": 6.0, "temp_min_c": -1.0, "weather_code": 1},
        ],
    },
}


def weather_label(code):
    return WEATHER_CODE_LABELS.get(code, "Unknown conditions")


def geocode_city(city_name, timeout=5):
    """Returns {name, country, latitude, longitude} for the best match,
    or None if the city isn't found. Raises on network/HTTP failure."""
    response = requests.get(GEOCODING_URL, params={"name": city_name, "count": 1}, timeout=timeout)
    response.raise_for_status()
    results = response.json().get("results")
    if not results:
        return None
    match = results[0]
    return {
        "name": match["name"],
        "country": match.get("country", ""),
        "latitude": match["latitude"],
        "longitude": match["longitude"],
    }


def fetch_forecast(latitude, longitude, timeout=5):
    """Raw current + daily forecast for a coordinate. Raises on
    network/HTTP failure."""
    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weathercode",
            "daily": "temperature_2m_max,temperature_2m_min,weathercode",
            "timezone": "auto",
            "forecast_days": 4,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _parse_live_forecast(city_info, raw):
    current = raw["current"]
    daily = raw["daily"]
    # Index 0 in the daily arrays is "today" (already covered by
    # `current`), so the 3-day forecast is indices 1-3.
    forecast = []
    for i in range(1, 4):
        forecast.append({
            "day_offset": i,
            "temp_max_c": daily["temperature_2m_max"][i],
            "temp_min_c": daily["temperature_2m_min"][i],
            "weather_code": daily["weathercode"][i],
        })
    return {
        "city": city_info["name"],
        "country": city_info["country"],
        "current": {
            "temp_c": current["temperature_2m"],
            "weather_code": current["weathercode"],
        },
        "forecast": forecast,
    }


def get_weather(city_name, timeout=5):
    """Tries the live Open-Meteo API; falls back to offline sample data
    on any failure (or when the live lookup returns no match). Returns
    (data, source_label, found) where `found` is False only when neither
    the live API nor the offline sample data has anything for this city."""
    try:
        city_info = geocode_city(city_name, timeout=timeout)
        if city_info is None:
            raise ValueError(f"No geocoding match for {city_name!r}")
        raw = fetch_forecast(city_info["latitude"], city_info["longitude"], timeout=timeout)
        return _parse_live_forecast(city_info, raw), "live", True
    except Exception:
        sample = OFFLINE_SAMPLE_DATA.get(city_name.strip().lower())
        if sample is None:
            return None, "offline sample data", False
        return sample, "offline sample data", True
