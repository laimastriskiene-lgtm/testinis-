---
name: miestu-oras
description: Pateikia Vilniaus, Kauno, Klaipėdos, Šiaulių ir Panevėžio temperatūros bei oro sąlygų prognozę lietuviškai iš Meteo.lt, su automatiniu Open-Meteo atsarginiu šaltiniu. Naudok prašant Lietuvos didmiesčių orų, temperatūrų palyginimo arba miestu-oras įgūdžio.
---

# Miestų oras

Paleisk `python scripts/miestu_oras.py` iš šio įgūdžio aplanko arba nurodyk visą skripto kelią. Reikia interneto ir Python 3.9+. Naudojamos tik standartinės bibliotekos; jei Windows neturi IANA laiko juostų duomenų, reikia `python -m pip install tzdata`. API rakto nereikia.

Kiekvienam miestui pirmiausia naudojama `https://api.meteo.lt/v1/places/{code}/forecasts/long-term`. Jei užklausa nepavyksta, JSON netinkamas arba nėra tinkamos prognozės, automatiškai naudojama `https://api.open-meteo.com/v1/forecast` su fiksuotomis miesto koordinatėmis ir valandiniais `temperature_2m,weather_code` duomenimis UTC bei Celsijaus vienetais.

Skriptas pasirenka artimiausią dar nepraėjusį tinkamą prognozės laiką, ne daugiau kaip 3 valandos nuo vykdymo pradžios. Tinkamas įrašas turi baigtinę skaitinę temperatūrą ir žinomą sąlygų kodą. Sugadinti, pasenę, per tolimi ir nežinomų kodų įrašai praleidžiami; jei tinkamų nelieka, bandomas atsarginis šaltinis. Meteo.lt kodai ir Open-Meteo WMO kodai verčiami į lietuvių kalbą skripte.

Pateik visų penkių miestų temperatūrą, oro sąlygas, prognozės laiką ir šaltinį iš skripto išvesties. Laikas konvertuojamas į `Europe/Vilnius`, atsižvelgiant į vasaros ir žiemos laiką; UTC poslinkis padeda atskirti pasikartojančią valandą. Kiekviena eilutė turi savo šaltinį: LHMT (`api.meteo.lt`) arba Open-Meteo (`api.open-meteo.com`). Tai prognozė, ne faktinis matavimas.

Jei abu šaltiniai konkrečiam miestui nepateikia tinkamų duomenų, išsaugok eilutę „Duomenų nėra“ ir aiškų abiejų šaltinių nesėkmės pranešimą. Nespėliok temperatūros, sąlygų ar laiko. Kitų miestų gavimą tęsk. Kai nė vienam miestui duomenų nėra, skriptas papildomai pateikia bendrą klaidą ir baigiasi kodu `1`; bent vieno miesto sėkmė grąžina `0`. Trūkstant laiko juostų duomenų, baigiama kodu `1` su `tzdata` diegimo instrukcija.

## Patikra

`python -m unittest discover -s evals -v` tikrina pagrindinio šaltinio pirmenybę, automatinį perėjimą po HTTP / tinklo / JSON klaidų ir netinkamų duomenų, abiejų šaltinių nesėkmę, WMO kodus, laiko konvertavimą bei dalinę sėkmę. Testams interneto nereikia. Tada paleisk skriptą su tikrais API; vien testai nepatvirtina tinklo prieinamumo.

API schemos ir kodai: [Meteo.lt dokumentacija](https://api.meteo.lt/), [Open-Meteo dokumentacija](https://open-meteo.com/en/docs).
