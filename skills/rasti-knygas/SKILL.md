---
name: rasti-knygas
description: Ieško knygų Open Library pagal temą, pavadinimą arba autorių ir paruošia JSON kitam gauti-knygu-duomenis etapui. Naudok prašant surasti knygų arba pradėti knygų rekomendavimo grandinę.
---

# Knygų paieška

Pirmas grandinės etapas: rasti-knygas → gauti-knygu-duomenis → atrinkti-knygas → palyginti-knygas → rekomenduoti-knygas.
Šis įgūdis atlieka tik paiešką. Jam reikia interneto užklausas ir JSON atsakymus palaikančio įrankio.

## Įvestis

Priimk `query` (netuščią paieškos tekstą), neprivalomą `limit` (sveikąjį skaičių 1–20, numatyta 10) ir `preferences` (skaitytojo kriterijų objektą, numatyta `{}`). Jei query nepateikta, paklausk temos, autoriaus arba pavadinimo. Kriterijus išsaugok kitam etapui; šiame etape pagal juos knygų neatmesk.

## Veiksmai

1. Užkoduok query kaip URL parametro reikšmę ir kreipkis į `https://openlibrary.org/search.json` su parametrais `q`, `limit` ir `fields=key,title,author_name,first_publish_year`. Naudok tikrą API atsakymą.
2. Iš `docs` paimk knygas API pateikta tvarka. `key` normalizuok į `/works/OL…W` (jei pateiktas tik `OL…W`, pridėk `/works/`). Įrašus be tinkamo kūrinio identifikatoriaus arba pavadinimo praleisk; pasikartojančius work_key pašalink.
3. Paversk `author_name` į `authors` masyvą (trūkstant — `[]`), `first_publish_year` į skaičių arba `null`. Nekurk nežinomų autorių ar metų.
4. Grąžink toliau aprašytą JSON. `source_url` turi būti faktiškai naudotos užklausos URL. Rezultatų neišgalvok ir jų nepildyk iš atminties.

## Duomenų perdavimas

Grąžink vieną JSON objektą be komentarų. Toliau pateikta tuščio sėkmingo atsakymo forma, ne tikros paieškos rezultatas:

```json
{
  "schema_version": "1.0",
  "stage": "rasti-knygas",
  "status": "ok",
  "query": "fantasy",
  "preferences": {},
  "source_url": "https://openlibrary.org/search.json?q=fantasy&limit=10&fields=key%2Ctitle%2Cauthor_name%2Cfirst_publish_year",
  "books": [],
  "error": null
}
```

Kiekvienas `books` elementas turi laukus: `work_key` (eilutė), `title` (eilutė), `authors` (eilučių masyvas), `first_publish_year` (sveikasis skaičius arba null), `url` (`https://openlibrary.org` + work_key).

Nerasta knygų: `status: "ok"`, `books: []`, `error: null`. Tinklo, HTTP ar netinkamo JSON / atsakymo struktūros klaida: `status: "error"`, `books: []`, `error` su trumpu priežasties tekstu. Klaida nėra tuščia sėkminga paieška.

Visą objektą perduok `gauti-knygu-duomenis` kaip įvestį; išsaugok `query`, `preferences` ir kūrinių identifikatorius. Kai status yra error arba books tuščias, grandinę sustabdyk ir paaiškink priežastį. Vien įgūdžių failai automatinio vykdymo nesukuria: kitą etapą turi iškviesti agentas arba atskirai sukurtas vykdytojas. Kitų etapų šis failas dar neįgyvendina.

Oficiali dokumentacija: https://openlibrary.org/dev/docs/api/search
