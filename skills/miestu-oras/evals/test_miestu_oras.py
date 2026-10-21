import contextlib
import io
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import miestu_oras as weather

NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)


def primary(**changes):
    row = dict(forecastTimeUtc="2026-10-21 13:00:00", airTemperature=5, conditionCode="clear")
    row.update(changes)
    return {"forecastTimestamps": [row]}


def backup():
    return {"hourly": {"time": ["2026-10-21T13:00"], "temperature_2m": [6.5], "weather_code": [63]}}


class WeatherTests(unittest.TestCase):
    def test_cities(self):
        self.assertEqual([n for n, _ in weather.MIESTAI], ["Vilnius", "Kaunas", "Klaipėda", "Šiauliai", "Panevėžys"])
        self.assertEqual(set(weather.KOORDINATES), {c for _, c in weather.MIESTAI})

    def test_primary_preferred(self):
        with patch.object(weather, "fetch_city", return_value=primary()), patch.object(weather, "fetch_open_meteo") as fallback:
            result, source = weather.get_forecast("vilnius", NOW)
        fallback.assert_not_called()
        self.assertEqual(result[1:], (5, "Giedra"))
        self.assertIn("api.meteo.lt", source)

    def test_fallback_errors(self):
        errors = [URLError("offline"), TimeoutError(), ValueError("bad JSON"),
                  HTTPError("url", 503, "Unavailable", None, None)]
        for error in errors:
            with self.subTest(error=error), patch.object(weather, "fetch_city", side_effect=error), patch.object(weather, "fetch_open_meteo", return_value=backup()) as fallback, contextlib.redirect_stderr(io.StringIO()):
                result, source = weather.get_forecast("vilnius", NOW)
                fallback.assert_called_once_with("vilnius")
                self.assertEqual(result[1:], (6.5, "Lietus"))
                self.assertIn("api.open-meteo.com", source)

    def test_fallback_invalid_primary(self):
        invalid = [None, [], {}, {"forecastTimestamps": None}, {"forecastTimestamps": [None]},
                   primary(airTemperature=None), primary(airTemperature=True), primary(airTemperature=float("nan")),
                   primary(airTemperature=float("inf")), primary(conditionCode="unknown"),
                   primary(conditionCode=[]), primary(forecastTimeUtc="invalid"),
                   primary(forecastTimeUtc="2026-10-21 11:00:00"), primary(forecastTimeUtc="2026-10-22 13:00:00")]
        for data in invalid:
            with self.subTest(data=data), patch.object(weather, "fetch_city", return_value=data), patch.object(weather, "fetch_open_meteo", return_value=backup()):
                self.assertIn("open-meteo", weather.get_forecast("kaunas", NOW)[1])

    def test_both_fail(self):
        with patch.object(weather, "fetch_city", side_effect=URLError("offline")), patch.object(weather, "fetch_open_meteo", side_effect=URLError("offline")), contextlib.redirect_stderr(io.StringIO()):
            result, source = weather.get_forecast("kaunas", NOW)
        self.assertIsNone(result)
        self.assertIn("Abu šaltiniai", source)
        self.assertIn("Duomenų nėra", weather.format_row("Kaunas", result, source, ZoneInfo("Europe/Vilnius")))

    def test_invalid_backup(self):
        for data in [None, {}, {"error": True}, {"hourly": []}, {"hourly": {"time": []}},
                     {"hourly": {"time": ["2026-10-21T13:00"], "temperature_2m": [], "weather_code": [0]}}]:
            self.assertIsNone(weather.nearest_forecast(data, NOW, True))
        for code in [999, None, True, "63"]:
            data = backup()
            data["hourly"]["weather_code"] = [code]
            self.assertIsNone(weather.nearest_forecast(data, NOW, True))

    def test_nearest_valid(self):
        rows = [primary(forecastTimeUtc=t)["forecastTimestamps"][0] for t in
                ["2026-10-21 14:00:00", "2026-10-21 11:00:00", "2026-10-21 13:00:00"]]
        self.assertEqual(weather.nearest_forecast({"forecastTimestamps": rows}, NOW)[0].hour, 13)

    def test_timezone(self):
        zone = ZoneInfo("Europe/Vilnius")
        for stamp, expected in [("2026-01-21T13:00Z", "15:00 +0200"), ("2026-07-21T13:00Z", "16:00 +0300"),
                                ("2026-10-25T00:00Z", "03:00 +0300"), ("2026-10-25T01:00Z", "03:00 +0200")]:
            self.assertIn(expected, weather.format_row("Vilnius", (weather.parse_utc(stamp), 5, "Giedra"), "test", zone))
        self.assertEqual(weather.parse_utc("2026-10-21T15:00+02:00").hour, 13)

    def test_wmo_codes(self):
        codes = {0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67,
                 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 97, 99}
        self.assertEqual(set(weather.WMO_SALYGOS), codes)
        for code in codes:
            data = backup()
            data["hourly"]["weather_code"] = [code]
            self.assertEqual(weather.nearest_forecast(data, NOW, True)[2], weather.WMO_SALYGOS[code])

    def test_cli_all_missing_and_partial_success(self):
        for results, status in [([(None, "Abu šaltiniai nepateikė tinkamų duomenų")] * 5, 1),
                                ([( (NOW, 5, "Giedra"), "LHMT, api.meteo.lt")] + [(None, "Abu šaltiniai")] * 4, 0)]:
            output = io.StringIO()
            with patch.object(weather, "get_forecast", side_effect=results), contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(weather.main(), status)
            for city, _ in weather.MIESTAI:
                self.assertEqual(output.getvalue().count("| " + city + " |"), 1)

    def test_missing_timezone(self):
        with patch.object(weather, "ZoneInfo", side_effect=ZoneInfoNotFoundError()), contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(weather.main(), 1)
            self.assertIn("tzdata", error.getvalue())

    def test_request_parameters(self):
        with patch.object(weather, "fetch_json", return_value={}) as fetch:
            weather.fetch_open_meteo("vilnius")
            url = fetch.call_args.args[0]
            self.assertIn("https://api.open-meteo.com/v1/forecast?", url)
            self.assertIn("timezone=UTC", url)
            self.assertIn("temperature_unit=celsius", url)


if __name__ == "__main__":
    unittest.main()
