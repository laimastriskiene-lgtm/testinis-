#!/usr/bin/env python3
"""Penkių Lietuvos didmiesčių artimiausia meteo.lt prognozė."""
import json
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

MIESTAI = [("Vilnius", "vilnius"), ("Kaunas", "kaunas"),
           ("Klaipėda", "klaipeda"), ("Šiauliai", "siauliai"),
           ("Panevėžys", "panevezys")]
SALYGOS = {
    "clear": "Giedra", "partly-cloudy": "Mažai debesuota",
    "cloudy-with-sunny-intervals": "Debesuota su pragiedruliais",
    "cloudy": "Debesuota", "light-rain": "Nedidelis lietus",
    "rain": "Lietus", "heavy-rain": "Smarkus lietus",
    "thunder": "Perkūnija", "isolated-thunderstorms": "Trumpas lietus su perkūnija",
    "thunderstorms": "Lietus su perkūnija",
    "heavy-rain-with-thunderstorms": "Smarkus lietus su perkūnija",
    "light-sleet": "Nedidelė šlapdriba", "sleet": "Šlapdriba",
    "freezing-rain": "Lijundra", "hail": "Kruša",
    "light-snow": "Nedidelis sniegas", "snow": "Sniegas",
    "heavy-snow": "Smarkus sniegas", "fog": "Rūkas",
}

def parse_utc(value):
    return datetime.fromisoformat(value.replace(" ", "T").replace("Z", "+00:00")).replace(tzinfo=timezone.utc) if "+00:00" not in value else datetime.fromisoformat(value.replace(" ", "T"))

def nearest_forecast(data, now):
    rows = data.get("forecastTimestamps", [])
    valid = []
    for row in rows:
        try:
            stamp = parse_utc(row["forecastTimeUtc"])
            if stamp >= now:
                valid.append((stamp, row))
        except (KeyError, ValueError, TypeError):
            continue
    return min(valid, key=lambda item: item[0]) if valid else None

def fetch_city(code):
    url = f"https://api.meteo.lt/v1/places/{code}/forecasts/long-term"
    req = Request(url, headers={"User-Agent": "miestu-oras/1.0 (educational weather skill)", "Accept": "application/json"})
    with urlopen(req, timeout=12) as response:
        return json.load(response)

def format_row(name, data, now):
    forecast = nearest_forecast(data, now)
    if not forecast:
        return f"| {name} | Duomenų nėra | Duomenų nėra | – |"
    stamp, item = forecast
    temp = item.get("airTemperature")
    temperature = f"{temp:g} °C" if isinstance(temp, (int, float)) and not isinstance(temp, bool) else "Duomenų nėra"
    condition = SALYGOS.get(item.get("conditionCode"), "Nenustatyta")
    local_time = stamp.astimezone(ZoneInfo("Europe/Vilnius")).strftime("%Y-%m-%d %H:%M")
    return f"| {name} | {temperature} | {condition} | {local_time} |"

def main():
    now = datetime.now(timezone.utc)
    print("Artimiausia meteo.lt orų prognozė (Lietuvos laiku)\n")
    print("| Miestas | Temperatūra | Oro sąlygos | Prognozės laikas |")
    print("|---|---:|---|---|")
    successful = 0
    for name, code in MIESTAI:
        try:
            data = fetch_city(code)
            if nearest_forecast(data, now):
                successful += 1
            print(format_row(name, data, now))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            print(f"| {name} | Duomenų nėra | Duomenų nėra | – |")
            print(f"Įspėjimas: {name}: {exc}", file=sys.stderr)
    print("\nŠaltinis: Lietuvos hidrometeorologijos tarnyba, meteo.lt (prognozė).")
    if not successful:
        print("Nepavyko gauti aktualių prognozės duomenų.", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
