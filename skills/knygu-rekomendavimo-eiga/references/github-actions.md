# Paleidimas GitHub mygtuku

1. Repozitorijoje atverk **Actions → Knygų rekomendacijos**.
2. Spausk **Run workflow**, palik šaką **main**.
3. Lauke query įrašyk Open Library paiešką, pvz., `subject:fantasy`, `healthy living` arba knygos pavadinimą. Tai katalogo užklausa, ne laisvas nurodymas agentui lietuviškai.
4. limit — kiek kandidatų ieškoti, nuo 1 iki 20. Tai nėra garantuotas galutinių atitikmenų skaičius. min_year — pirmos publikacijos metų apatinė riba. max_year galima palikti tuščią.
5. preferences palik `{}`, jei papildomų kriterijų nereikia. Pavyzdys: `{"authors":["Brandon Sanderson"],"subjects_any":["Fantasy"]}`. Nenurodyk preferences kitokių metų nei atskiruose metų laukuose.
6. Dar kartą spausk **Run workflow**, atverk atsiradusį vykdymą. Santraukoje bus rekomendacijos arba sustojimo priežastis. Skiltyje **Artifacts** atsisiųsk `knygu-rezultatai-…` ZIP su etapų JSON ir galutiniu Markdown failu. Failai saugomi 14 dienų.

API rakto ar papildomo Python bibliotekų diegimo nereikia. GitHub Actions naudojimui taikomos paskyros įprastos sąlygos ir limitai.

## Ką ši versija daro

Vykdytojas yra Python programa [scripts/vykdyti.py](../scripts/vykdyti.py), realizuojanti penkių įgūdžių duomenų ir atrankos taisykles. Ji perskaito įgūdžių failų versijas ir išsaugo jų SHA-256, bet natūralios kalbos instrukcijų neinterpretuoja modeliu. Vien pakeitus SKILL.md programos elgsena nepasikeis — taisyklių pakeitimus reikia perkelti į kodą ir testus.

Veiksmai: Open Library paieška → kūrinių duomenų papildymas → filtravimas → faktinis palyginimas → iki trijų variantų su atrankos priežastimis lietuviškai. Pirminiai duomenys ir visi kandidatai yra JSON failuose. Temos išlieka šaltinio kalba; laisvos siužeto santraukos negeneruojamos. Nepagrįstas kokybės ar populiarumo reitingas nesudaromas.

Papildomi kriterijai: authors, min_year, max_year, subjects_any, excluded_subjects, description_keywords_any. Temoms ir autoriams taikomas tikslus sutapimas nepaisant raidžių dydžio bei kraštinių tarpų; aprašymo raktažodžiui — poeilutės sutapimas. Nežinomų laukų duomenys laikomi unknown ir knygos lieka pending. Kriterijai nesusilpninami automatiškai.

Jei nelieka atrinktų knygų, eiga sustoja ir paaiškina priežastį. Toks tvarkingas sustojimas gali turėti žalią GitHub būseną: tikrą rezultatą rodo vykdymo-busena.json. Įvesties ar tinklo klaida pažymima raudonai; diagnostikos failai vis tiek įkeliami, jei įmanoma. HTTP 429 nutraukia likusias duomenų užklausas be pakartotinių bandymų. Išlikus tinkamų kandidatų, dalinis vykdymas tęsiamas su perspėjimais.

## Ribos

Katalogo datos gali būti netikslios. Konkretaus leidimo kalba, puslapių skaičius, knygynų pardavimai, pasaulinis populiarumas ir leidėjų duomenų patikra čia neįgyvendinti. Ankstesniuose pokalbio bandymuose agento papildomai atlikta internetinė patikra automatiškai į šį vykdytoją nepersikelia.

Workflow vykdomas tik rankiniu workflow_dispatch paleidimu; nėra periodinio tvarkaraščio ir automatinio commit ar push. Įvestys perduodamos per aplinkos kintamuosius, ne įterpiamos į vykdomas komandas.

## Patikra ir vietinis paleidimas

Iš repozitorijos aplanko:

```text
python -m unittest discover -s skills/knygu-rekomendavimo-eiga/evals -p "test_*.py" -v
python skills/knygu-rekomendavimo-eiga/scripts/vykdyti.py --query "subject:fantasy" --limit 6 --min-year 2000 --output results-naujas
```

Kiekvienam paleidimui nurodyk naują output aplanką. Ankstesni rezultatai neperrašomi.

Šaltiniai: [GitHub rankinis paleidimas](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow), [Open Library Search API](https://openlibrary.org/dev/docs/api/search).
