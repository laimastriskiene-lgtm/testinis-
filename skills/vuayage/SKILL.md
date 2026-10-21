---
name: vuayage
description: Rask ir palygink penkis galiojančius Novaturas paskutinės minutės kelionių pasiūlymus, jų kainas ir sąlygas. Naudok, kai vartotojas prašo Vuayage, Novaturo paskutinės minutės kelionių, pigių atostogų ar penkių kelionių pasiūlymų.
---

# Vuayage – paskutinės minutės kelionės

## Šaltinis
Oficialus puslapis: https://www.novaturas.lt/paskutine-minute

## Veiksmų eiga
1. Atidaryk oficialų puslapį naudodamas turimą naršyklės / interneto paieškos įrankį. Jei svetainė reikalauja JavaScript, naudok palaikomą naršyklę; nesugalvok neegzistuojančio API ir neapeik apsaugų.
2. Užfiksuok tikrinimo datą ir laiką (Lietuvos laiku). Atsirink **penkis galiojančius** paskutinės minutės kelionių pasiūlymus. Pagal nutylėjimą rodyk pirmus penkis svetainėje pateiktus tinkamus pasiūlymus, o ne teik, kad jie paskelbti vėliausiai: svetainė nebūtinai skelbia įkėlimo laiką.
3. Atmesk keliones, kurių išvykimo data jau praėjusi. Jei datos, kaina ar prieinamumas nepatvirtinti, pažymėk „nepatvirtinta“ arba pasiūlymo nerodyk.
4. Kiekvienam pasiūlymui patikrink šalį / kurortą, viešbutį, išvykimo miestą ir datą, nakvynių skaičių, maitinimą, kainą vienam asmeniui ir bendrą kainą (jei nurodyta), pasiūlymo URL, įskaičiuotas paslaugas, papildomus mokesčius ir atšaukimo / keitimo sąlygas. Nespręsk apie konkretaus pasiūlymo sąlygas vien iš bendrų taisyklių.
5. Parodyk lentelę lietuviškai: Kelionė | Išvykimas | Naktys | Maitinimas | Kaina nuo | Nuoroda. Po lentele pateik svarbiausias patikrintas sąlygas ir duomenų patikrinimo laiką. Paaiškink, kad kaina ir vietų skaičius gali keistis.
6. Jei pavyksta patikrinti mažiau nei penkis pasiūlymus, pateik tik patikrintus ir aiškiai nurodyk trūkumą. Jei puslapis nepasiekiamas, pranešk apie nesėkmę ir pateik oficialią nuorodą; **niekada neišgalvok kainų ar pasiūlymų**.
7. Jei vartotojas nurodo išvykimo miestą, biudžetą, keliautojų skaičių ar datas, taikyk tuos filtrus. Be nurodymų nedaryk prielaidų apie vaikų amžių ar konkrečias kelionės sąlygas.

## Maitinimo kodai
RO – be maitinimo; BB – pusryčiai; HB – pusryčiai ir vakarienė; AI – viskas įskaičiuota; UAI – išplėstinis viskas įskaičiuota. Jei svetainėje vartojami kitokie apibrėžimai, vadovaukis svetaine.

## Testavimas
Naudok `evals/scenarios.md` scenarijus. Patikrink datų filtravimą, nepatvirtintų kainų žymėjimą, trūkstamus duomenis ir neveikiantį puslapį. Testai nėra gyvų pasiūlymų patvirtinimas.
