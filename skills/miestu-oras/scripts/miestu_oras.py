"""Penkių Lietuvos miestų artimiausia orų prognozė su atsarginiu šaltiniu."""
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MIESTAI = [("Vilnius", "vilnius"), ("Kaunas", "kaunas"), ("Klaipėda", "klaipeda"),
           ("Šiauliai", "siauliai"), ("Panevėžys", "panevezys")]
KOORDINATES = dict(zip((code for _, code in MIESTAI),
    [(54.6872, 25.2797), (54.8985, 23.9036), (55.7033, 21.1443),
     (55.9349, 23.3137), (55.7348, 24.3575)]))
SALYGOS = {
    "clear": "Giedra", "partly-cloudy": "Mažai debesuota",
    "cloudy-with-sunny-intervals": "Debesuota su pragiedruliais", "cloudy": "Debesuota",
    "light-rain": "Nedidelis lietus", "rain": "Lietus", "heavy-rain": "Smarkus lietus",
    "thunder": "Perkūnija", "isolated-thunderstorms": "Trumpas lietus su perkūnija",
    "thunderstorms": "Lietus su perkūnija", "heavy-rain-with-thunderstorms": "Smarkus lietus su perkūnija",
    "light-sleet": "Nedidelė šlapdriba", "sleet": "Šlapdriba", "freezing-rain": "Lijundra",
    "hail": "Kruša", "light-snow": "Nedidelis sniegas", "snow": "Sniegas",
    "heavy-snow": "Smarkus sniegas", "fog": "Rūkas",
}
WMO_SALYGOS = {
    0: "Giedra", 1: "Daugiausia giedra", 2: "Mažai debesuota", 3: "Debesuota",
    45: "Rūkas", 48: "Rūkas su šerkšnu", 51: "Silpna dulksna", 53: "Vidutinė dulksna",
    55: "Smarki dulksna", 56: "Silpna lijundrą sukelianti dulksna",
    57: "Smarki lijundrą sukelianti dulksna", 61: "Nedidelis lietus", 63: "Lietus",
    65: "Smarkus lietus", 66: "Silpnas lijundrą sukeliantis lietus",
    67: "Smarkus lijundrą sukeliantis lietus", 71: "Nedidelis sniegas", 73: "Sniegas",
    75: "Smarkus sniegas", 77: "Sniego grūdai", 80: "Silpnos liūtys",
    81: "Vidutinės liūtys", 82: "Labai smarkios liūtys", 85: "Silpnos sniego liūtys",
    86: "Smarkios sniego liūtys", 95: "Perkūnija", 96: "Perkūnija su nedidele kruša",
    97: "Smarki perkūnija", 99: "Perkūnija su smarkia kruša",
}


def parse_utc(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def fetch_json(url):
    request = Request(url, headers={"User-Agent": "miestu-oras/2.0", "Accept": "application/json"})
    with urlopen(request, timeout=12) as response:
        return json.load(response)


def fetch_city(code):
    return fetch_json(f"https://api.meteo.lt/v1/places/{code}/forecasts/long-term")


def fetch_open_meteo(code):
    latitude, longitude = KOORDINATES[code]
    query = urlencode(dict(latitude=latitude, longitude=longitude,
        hourly="temperature_2m,weather_code", timezone="UTC", temperature_unit="celsius", forecast_days=2))
    return fetch_json("https://api.open-meteo.com/v1/forecast?" + query)


def nearest_forecast(data, now, open_meteo=False):
    if not isinstance(data, dict) or data.get("error"):
        return None
    if open_meteo:
        hourly = data.get("hourly")
        if not isinstance(hourly, dict):
            return None
        arrays = [hourly.get(key) for key in ("time", "temperature_2m", "weather_code")]
        if not all(isinstance(a, list) for a in arrays) or len({len(a) for a in arrays}) != 1:
            return None
        rows = [dict(forecastTimeUtc=t, airTemperature=temp, conditionCode=code)
                for t, temp, code in zip(*arrays)]
    else:
        rows = data.get("forecastTimestamps")
    if not isinstance(rows, list):
        return None
    valid = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            stamp = parse_utc(row["forecastTimeUtc"])
            temp, code = row.get("airTemperature"), row.get("conditionCode")
            mapping = WMO_SALYGOS if open_meteo else SALYGOS
            code_type = type(code) is int if open_meteo else isinstance(code, str)
            if (now <= stamp <= now + timedelta(hours=3)
                    and isinstance(temp, (int, float)) and not isinstance(temp, bool)
                    and math.isfinite(temp) and code_type and code in mapping):
                valid.append((stamp, temp, mapping[code]))
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
    return min(valid, key=lambda item: item[0]) if valid else None


def get_forecast(code, now):
    for source, fetch, backup in (
        ("LHMT, api.meteo.lt", fetch_city, False),
        ("Open-Meteo, api.open-meteo.com", fetch_open_meteo, True),
    ):
        try:
            forecast = nearest_forecast(fetch(code), now, backup)
            if forecast:
                return forecast, source
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            print(f"Įspėjimas: {code}, {source}: {exc}", file=sys.stderr)
    return None, "Abu šaltiniai nepateikė tinkamų duomenų"


def format_row(name, forecast, source, local_zone):
    if forecast is None:
        return f"| {name} | Duomenų nėra | Duomenų nėra | – | {source} |"
    stamp, temp, condition = forecast
    local_time = stamp.astimezone(local_zone).strftime("%Y-%m-%d %H:%M %z")
    return f"| {name} | {temp:g} °C | {condition} | {local_time} | {source} |"


def main():
    try:
        local_zone = ZoneInfo("Europe/Vilnius")
    except ZoneInfoNotFoundError:
        print("Nerasta Europe/Vilnius laiko juosta. Įdiekite: python -m pip install tzdata", file=sys.stderr)
        return 1
    now = datetime.now(timezone.utc)
    print("Artimiausia orų prognozė (Lietuvos laiku, Europe/Vilnius)\n")
    print("| Miestas | Temperatūra | Oro sąlygos | Prognozės laikas | Šaltinis |")
    print("|---|---:|---|---|---|")
    successful = 0
    for name, code in MIESTAI:
        forecast, source = get_forecast(code, now)
        successful += forecast is not None
        print(format_row(name, forecast, source, local_zone))
    print("\nTai prognozė, ne faktinis matavimas. LHMT – Lietuvos hidrometeorologijos tarnyba.")
    if not successful:
        print("Nepavyko gauti aktualių prognozės duomenų iš abiejų šaltinių.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
