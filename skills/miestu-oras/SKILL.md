---
name: miestu-oras
description: Pateikia penkių didžiausių Lietuvos miestų (Vilniaus, Kauno, Klaipėdos, Šiaulių ir Panevėžio) naujausią meteo.lt oro temperatūros ir sąlygų prognozę lietuviškai. Naudok, kai prašoma Lietuvos didmiesčių orų, temperatūrų palyginimo arba „miestu-oras“ įgūdžio.
---

# Miestų oras

## Veiksmų seka

1. Naudok oficialią Lietuvos hidrometeorologijos tarnybos API `https://api.meteo.lt/v1/`. Reikalingas interneto ryšys ir Python 3; papildomų bibliotekų ar API rakto nereikia.
2. Paleisk `python scripts/miestu_oras.py` iš šio įgūdžio aplanko (arba nurodyk pilną skripto kelią).
3. Skriptas kiekvienam miestui atskirai gauna `places/{code}/forecasts/long-term` duomenis ir pasirenka artimiausią dar nepraėjusį prognozės laiką UTC. Tai **prognozė**, ne faktinis matavimas. Neteik jos kaip stebėjimų duomenų.
4. Grąžink skripto lietuvišką lentelę, išsaugodamas prognozės laiką Lietuvos laiku ir šaltinį. Jei miestas nepasiekiamas, parodyk „Duomenų nėra“, nekurk temperatūros ar sąlygų.
5. Jei visi API kreipiniai nepavyko, aiškiai pasakyk, kad orų duomenų gauti nepavyko; nenaudok spėjimų.

## Rezultatas

Lentelė: **Miestas | Temperatūra (°C) | Oro sąlygos | Prognozės laikas**. Po lentele: **Šaltinis: Lietuvos hidrometeorologijos tarnyba, meteo.lt (prognozė)**. Nenurodyk vieno bendro laiko, jei miestų laikai skiriasi.

## Patikra

Paleisk `python -m unittest discover -s evals -v`. Patikrink, kad yra tiksliai penki miestai, teisingai konvertuojamas UTC laikas, nežinomas sąlygų kodas neišgalvojamas, o HTTP klaida nesugriauna kitų miestų rezultatų.
