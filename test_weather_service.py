import sys
import types
import unittest

import weather_service
from weather_service import OFFLINE_SAMPLE_DATA, get_weather, weather_label


class FakeResponse:
    def __init__(self, payload, status_ok=True):
        self._payload = payload
        self._status_ok = status_ok

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self._status_ok:
            raise RuntimeError("simulated HTTP error")


class TestWeatherLabel(unittest.TestCase):
    def test_known_code_maps_to_a_label(self):
        self.assertEqual(weather_label(0), "Clear sky")

    def test_unknown_code_falls_back_gracefully(self):
        self.assertEqual(weather_label(9999), "Unknown conditions")


class TestOfflineFallback(unittest.TestCase):
    """Dual-patches sys.modules and the module's own bound `requests`
    name — required because weather_service.py does `import requests` at
    load time, so a sys.modules swap alone doesn't reach the
    already-bound reference (same technique as the Anime News
    Aggregator's offline-fallback tests)."""

    def setUp(self):
        self.original_requests = weather_service.requests
        fake_requests = types.ModuleType("requests")
        fake_requests.get = self._raise_connection_error
        sys.modules["requests"] = fake_requests
        weather_service.requests = fake_requests

    def tearDown(self):
        sys.modules["requests"] = self.original_requests
        weather_service.requests = self.original_requests

    @staticmethod
    def _raise_connection_error(*args, **kwargs):
        raise ConnectionError("simulated network failure")

    def test_known_city_falls_back_to_offline_sample(self):
        data, source, found = get_weather("Cairo")
        self.assertEqual(source, "offline sample data")
        self.assertTrue(found)
        self.assertEqual(data["city"], "Cairo")
        self.assertEqual(len(data["forecast"]), 3)

    def test_lookup_is_case_and_whitespace_insensitive(self):
        data, _source, found = get_weather("  CAIRO  ")
        self.assertTrue(found)
        self.assertEqual(data["city"], "Cairo")

    def test_unknown_city_reports_not_found_rather_than_crashing(self):
        data, source, found = get_weather("Atlantis")
        self.assertFalse(found)
        self.assertIsNone(data)
        self.assertEqual(source, "offline sample data")

    def test_every_offline_city_has_a_three_day_forecast(self):
        for city, data in OFFLINE_SAMPLE_DATA.items():
            with self.subTest(city=city):
                self.assertEqual(len(data["forecast"]), 3)
                self.assertIn("temp_c", data["current"])


class TestLivePath(unittest.TestCase):
    def setUp(self):
        self.original_requests = weather_service.requests
        fake_requests = types.ModuleType("requests")
        fake_requests.get = self._fake_get
        sys.modules["requests"] = fake_requests
        weather_service.requests = fake_requests

    def tearDown(self):
        sys.modules["requests"] = self.original_requests
        weather_service.requests = self.original_requests

    @staticmethod
    def _fake_get(url, params=None, timeout=5):
        if "geocoding-api" in url:
            return FakeResponse({
                "results": [
                    {"name": "Testville", "country": "Testland", "latitude": 1.0, "longitude": 2.0}
                ]
            })
        if "api.open-meteo.com" in url:
            return FakeResponse({
                "current": {"temperature_2m": 20.0, "weathercode": 1},
                "daily": {
                    "temperature_2m_max": [21.0, 22.0, 23.0, 19.0],
                    "temperature_2m_min": [10.0, 11.0, 12.0, 9.0],
                    "weathercode": [1, 2, 3, 61],
                },
            })
        raise AssertionError(f"unexpected URL: {url}")

    def test_live_path_parses_current_and_three_day_forecast(self):
        data, source, found = get_weather("Testville")
        self.assertEqual(source, "live")
        self.assertTrue(found)
        self.assertEqual(data["city"], "Testville")
        self.assertEqual(data["current"]["temp_c"], 20.0)
        # Forecast should be days 1-3 of the daily arrays, not day 0
        # (today), which `current` already covers.
        self.assertEqual(len(data["forecast"]), 3)
        self.assertEqual(data["forecast"][0]["temp_max_c"], 22.0)
        self.assertEqual(data["forecast"][2]["temp_max_c"], 19.0)

    def test_geocoding_with_no_results_triggers_fallback(self):
        def fake_get_no_results(url, params=None, timeout=5):
            if "geocoding-api" in url:
                return FakeResponse({"results": []})
            raise AssertionError("forecast should never be called")

        weather_service.requests.get = fake_get_no_results
        data, source, found = get_weather("Cairo")
        self.assertEqual(source, "offline sample data")
        self.assertTrue(found)
        self.assertEqual(data["city"], "Cairo")


if __name__ == "__main__":
    unittest.main()
