import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from miestu_oras import MIESTAI, nearest_forecast, format_row, parse_utc

class WeatherTests(unittest.TestCase):
    def test_five_cities(self):
        self.assertEqual(len(MIESTAI), 5)
        self.assertEqual(len({code for _, code in MIESTAI}), 5)

    def test_nearest_future(self):
        now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
        data = {"forecastTimestamps": [
            {"forecastTimeUtc": "2026-10-21 11:00:00", "airTemperature": 3},
            {"forecastTimeUtc": "2026-10-21 14:00:00", "airTemperature": 7},
            {"forecastTimeUtc": "2026-10-21 13:00:00", "airTemperature": 5}]}
        self.assertEqual(nearest_forecast(data, now)[1]["airTemperature"], 5)

    def test_unknown_condition_and_timezone(self):
        now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
        data = {"forecastTimestamps": [{"forecastTimeUtc": "2026-10-21 13:00:00", "airTemperature": 4.5, "conditionCode": "unknown"}]}
        row = format_row("Vilnius", data, now)
        self.assertIn("Nenustatyta", row)
        self.assertIn("2026-10-21 16:00", row)

    def test_missing_forecast(self):
        self.assertIn("Duomenų nėra", format_row("Kaunas", {}, datetime.now(timezone.utc)))

if __name__ == "__main__":
    unittest.main()
