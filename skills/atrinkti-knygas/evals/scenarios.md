# Atrankos scenarijai

Naudok sintetinį, pagal SKILL.md galiojantį antrojo etapo objektą su dviem skirtingais work_key. Tai patikros duomenys, ne faktinės Open Library knygos. Keisk tik nurodytus laukus. Kiekvienu atveju tikrink visų pradinių laukų išsaugojimą, masyvų tvarką ir tai, kad kiekviena knyga grąžinta tik kartą.

1. Metų ribos: preferences min_year 1950, max_year 2020; knygų metai 1950 ir 2021. Pirma selected, antra rejected; ribinis atvejis priimamas.
2. Nežinomi metai: min_year 1950; metai null. pending, o ne rejected.
3. Nepavykęs papildymas: įvesties status partial, error su priežastimi; vienai knygai details_status error ir details_error; subjects_any ["Fantasy"]. Ši knyga pending; jos klaida bei ankstesnio etapo klaida išlieka, bendras status partial.
4. Draudžiamos temos: excluded_subjects ["Horror"]; subjects [" horror "] → rejected, subjects [] → pending. Didžiosios raidės ir kraštiniai tarpai sprendimo nekeičia.
5. Sprendimų pirmenybė: min_year 2000 ir subjects_any ["Fantasy"]; metai 1990, subjects []. rejected, nes vienas kriterijus aiškiai netenkintas, nors kitas unknown.
6. Nepalaikomas kriterijus: preferences language "lit". pending kiekvienai knygai, warnings paaiškina trūkstamus leidimo duomenis. Kriterijus neprapuola.
7. Tušti kriterijai: preferences {}. Visos knygos selected, checks []; details_error ir įvesties partial vis tiek išsaugomi. Jokia knyga nepaskelbiama rekomenduota.
8. Raktažodžiai: description_keywords_any ["magic"]; description "A MAGIC journey" → selected, description "A journey" → rejected, description null → pending. Priežastys remiasi tik tekstu.
9. Netinkama įvestis: min_year didesnis už max_year, netinkamas lauko tipas, pakartotas work_key arba ankstesnio etapo status error. Kiekvienas atskiras atvejis grąžina status error ir sustabdo grandinę.
10. Tuščias rezultatas: visos knygos rejected. status ok, books [], rejected_books išlaiko knygas; palyginimas nekviečiamas, kriterijai automatiškai nešvelninami.
