import unittest
from unittest.mock import patch

from app import create_app


class TestWeatherDashboard(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def test_get_index_defaults_to_cairo(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cairo", response.data)

    def test_posting_a_known_city_shows_current_and_forecast(self):
        response = self.client.post("/", data={"city": "London"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"London", response.data)
        # 3 forecast day cards should be present.
        self.assertEqual(response.data.count(b"forecast-card"), 3)

    def test_posting_an_unknown_city_shows_a_not_found_message_not_a_crash(self):
        with patch("app.get_weather", return_value=(None, "offline sample data", False)):
            response = self.client.post("/", data={"city": "Nowhereland"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Couldn't find weather", response.data)

    def test_blank_city_falls_back_to_default(self):
        response = self.client.post("/", data={"city": "   "})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cairo", response.data)

    def test_source_label_is_shown_to_the_user(self):
        response = self.client.get("/")
        self.assertIn(b"Source:", response.data)


if __name__ == "__main__":
    unittest.main()
