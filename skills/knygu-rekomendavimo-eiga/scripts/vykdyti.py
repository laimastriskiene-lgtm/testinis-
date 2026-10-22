"""Deterministinis penkių etapų vykdymas. Tik Python standartinė biblioteka."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request


STAGES = ("rasti-knygas", "gauti-knygu-duomenis", "atrinkti-knygas",
          "palyginti-knygas", "rekomenduoti-knygas")
LIST_FILTERS = {"authors", "subjects_any", "excluded_subjects", "description_keywords_any"}
YEAR_FILTERS = {"min_year", "max_year"}
WORK = re.compile(r"/works/OL[0-9]+W")


class WorkflowError(Exception):
    pass


class RateLimit(WorkflowError):
    pass


def fold(value):
    return value.strip().casefold()


def active(value):
    return value is not None and value != "" and value != [] and value != {}


def validate_preferences(prefs):
    if not isinstance(prefs, dict):
        raise WorkflowError("Papildomi kriterijai turi būti JSON objektas.")
    for key, value in prefs.items():
        if key in YEAR_FILTERS:
            if type(value) is not int or not 0 <= value <= 9999:
                raise WorkflowError(f"{key}: reikia sveikųjų metų nuo 0 iki 9999.")
        elif key in LIST_FILTERS:
            if not isinstance(value, list) or any(
                not isinstance(x, str) or not x.strip() for x in value
            ):
                raise WorkflowError(f"{key}: reikia netuščių tekstų masyvo.")
    if prefs.get("min_year", 0) > prefs.get("max_year", 9999):
        raise WorkflowError("Pradiniai metai negali viršyti galutinių metų.")


class Client:
    def __init__(self):
        self.last_start = None

    def get(self, url):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "openlibrary.org":
            raise WorkflowError("Netinkamas Open Library adresas.")
        if self.last_start is not None:
            time.sleep(max(0, 1.1 - (time.monotonic() - self.last_start)))
        self.last_start = time.monotonic()
        request = urllib.request.Request(url, headers={
            "User-Agent": "BookSkillsWorkflow/1.0 (+https://github.com/laimastriskiene-lgtm/testinis-)",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429:
                raise RateLimit("HTTP 429: pasiektas Open Library užklausų limitas.") from error
            raise WorkflowError(f"Open Library HTTP {error.code}.") from error
        except (OSError, ValueError) as error:
            raise WorkflowError(f"Nepavyko gauti Open Library JSON: {error}") from error
        if not isinstance(data, dict):
            raise WorkflowError("API atsakymas nėra JSON objektas.")
        return data


def find_books(query, limit, prefs, client):
    url = "https://openlibrary.org/search.json?" + urllib.parse.urlencode({
        "q": query, "limit": limit,
        "fields": "key,title,author_name,first_publish_year",
    })
    state = dict(schema_version="1.0", stage=STAGES[0], status="ok", query=query,
                 preferences=copy.deepcopy(prefs), source_url=url, books=[], error=None)
    try:
        data = client.get(url)
        docs = data.get("docs")
        if not isinstance(docs, list):
            raise WorkflowError("Paieškos atsakyme nėra docs masyvo.")
        if len(docs) > limit:
            raise WorkflowError("API grąžino daugiau įrašų nei prašytas limitas.")
        seen = set()
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            key, title = doc.get("key"), doc.get("title")
            if isinstance(key, str) and not key.startswith("/works/"):
                key = "/works/" + key
            if not isinstance(key, str) or not WORK.fullmatch(key) or key in seen:
                continue
            if not isinstance(title, str) or not title.strip():
                continue
            seen.add(key)
            authors, year = doc.get("author_name"), doc.get("first_publish_year")
            state["books"].append(dict(
                work_key=key, title=title,
                authors=[x for x in authors if isinstance(x, str)] if isinstance(authors, list) else [],
                first_publish_year=year if type(year) is int else None,
                url="https://openlibrary.org" + key,
            ))
    except WorkflowError as error:
        state.update(status="error", books=[], error=str(error))
    return state


def get_details(previous, client):
    state = copy.deepcopy(previous)
    state["stage"] = STAGES[1]
    limited = False
    for book in state["books"]:
        url = "https://openlibrary.org" + book["work_key"] + ".json"
        book.update(description=None, subjects=[], details_source_url=url,
                    details_status="error", details_error=None)
        try:
            if limited:
                raise WorkflowError("Užklausa nevykdyta po HTTP 429.")
            data = client.get(url)
            if data.get("key") != book["work_key"] or data.get("type") != {"key": "/type/work"}:
                raise WorkflowError("API grąžino kitą kūrinį arba netinkamą jo tipą.")
            description = data.get("description")
            if isinstance(description, dict):
                description = description.get("value")
            subjects = data.get("subjects", [])
            book.update(
                description=description if isinstance(description, str) else None,
                subjects=list(dict.fromkeys(x for x in subjects if isinstance(x, str)))
                if isinstance(subjects, list) else [],
                details_status="ok",
            )
        except WorkflowError as error:
            limited = limited or isinstance(error, RateLimit)
            book["details_error"] = str(error)
    failures = sum(b["details_status"] == "error" for b in state["books"])
    state["status"] = "ok" if not failures else "error" if failures == len(state["books"]) else "partial"
    state["error"] = f"Nepavyko knygų užklausų: {failures}." if failures else None
    return state


def check(book, criterion, wanted):
    field = {"min_year": "first_publish_year", "max_year": "first_publish_year",
             "subjects_any": "subjects", "excluded_subjects": "subjects",
             "description_keywords_any": "description", "authors": "authors"}.get(criterion)
    value = book.get(field) if field else None
    if field in {"subjects", "description"} and book["details_status"] != "ok":
        value = None
    if field is None or value is None or value == [] or (isinstance(value, str) and not value.strip()):
        result, reason = "unknown", "Duomenų nėra arba kriterijus nepalaikomas."
    else:
        if criterion == "min_year":
            matched = value >= wanted
        elif criterion == "max_year":
            matched = value <= wanted
        elif criterion == "description_keywords_any":
            matched = any(fold(x) in fold(value) for x in wanted)
        else:
            overlap = set(map(fold, value)) & set(map(fold, wanted))
            matched = not overlap if criterion == "excluded_subjects" else bool(overlap)
        result = "match" if matched else "no_match"
        reason = "Katalogo duomenys tenkina kriterijų." if matched else "Katalogo duomenys netenkina kriterijaus."
    return dict(criterion=criterion, result=result, reason=reason, evidence=value)


def select_books(previous):
    state = copy.deepcopy(previous)
    state.update(stage=STAGES[2], books=[], pending_books=[], rejected_books=[], warnings=[], error=None)
    prefs = state["preferences"]
    validate_preferences(prefs)
    if previous.get("error"):
        state["warnings"].append(previous["error"])
    unsupported = [k for k, v in prefs.items() if active(v) and k not in LIST_FILTERS | YEAR_FILTERS]
    for key in unsupported:
        state["warnings"].append(f"Nepalaikomas kriterijus: {key}.")
    for original in previous["books"]:
        book = copy.deepcopy(original)
        checks = [check(book, k, v) for k, v in prefs.items() if active(v)]
        results = {item["result"] for item in checks}
        decision = "rejected" if "no_match" in results else "pending" if "unknown" in results else "selected"
        book["selection"] = dict(decision=decision, checks=checks, reason={
            "rejected": "Bent vienas kriterijus netenkinamas.",
            "pending": "Bent vienam kriterijui trūksta duomenų.",
            "selected": "Visi aktyvūs kriterijai tenkinami." if checks else "Atrankos kriterijų nėra.",
        }[decision])
        state[{"selected": "books", "pending": "pending_books", "rejected": "rejected_books"}[decision]].append(book)
        if book.get("details_error"):
            state["warnings"].append(book["title"] + ": " + book["details_error"])
    state["status"] = "partial" if previous["status"] == "partial" or state["pending_books"] or unsupported else "ok"
    return state


def compare_books(previous):
    state = copy.deepcopy(previous)
    state["stage"] = STAGES[3]
    for book in state["books"]:
        limits, evidence = [], []
        for field in ("authors", "first_publish_year", "subjects", "description"):
            value = book[field]
            if field in {"subjects", "description"} and book["details_status"] != "ok":
                value = None
            if value is None or value == [] or (isinstance(value, str) and not value.strip()):
                limits.append(f"Nežinomas laukas: {field}.")
            else:
                evidence.append(dict(field=field,
                    value=" ".join(value.split()[:12]) if field == "description" else value,
                    source_url=book["details_source_url"] if field in {"subjects", "description"} else state["source_url"]))
        # Be kalbos modelio siužeto santraukų negeneruojame. Temas pateikiame iš šaltinio.
        book["comparison_notes"] = dict(overview=None,
            fit_reasons=[item["criterion"] + ": " + item["reason"] for item in book["selection"]["checks"]],
            limitations=limits, evidence=evidence)
        if limits:
            state["status"] = "partial"
            state["warnings"].append(book["title"] + ": " + " ".join(limits))
    books = state["books"]
    shared, differences, limits = [], [], []
    if len(books) > 1:
        if all(b["details_status"] == "ok" and b["subjects"] for b in books):
            common = set.intersection(*(set(map(fold, b["subjects"])) for b in books))
            seen = set()
            for subject in books[0]["subjects"]:
                if fold(subject) in common and fold(subject) not in seen:
                    shared.append(subject)
                    seen.add(fold(subject))
        years = [b for b in books if b["first_publish_year"] is not None]
        if len(years) > 1:
            earliest = min(years, key=lambda b: b["first_publish_year"])
            latest = max(years, key=lambda b: b["first_publish_year"])
            if earliest["first_publish_year"] != latest["first_publish_year"]:
                differences.append(dict(dimension="first_publish_year",
                    observation=f"Katalogo metai skiriasi: nuo {earliest['first_publish_year']} iki {latest['first_publish_year']}. Tai nerodo kokybės.",
                    evidence=[dict(work_key=b["work_key"], field="first_publish_year",
                                   value=b["first_publish_year"], source_url=state["source_url"])
                              for b in (earliest, latest)]))
    else:
        limits.append("Alternatyvų palyginimui nėra." if books else "Atrinktų kandidatų nėra.")
    if not any(active(v) for v in state["preferences"].values()):
        state["warnings"].append("Asmeninio tinkamumo kriterijai nenurodyti.")
    limits.extend(book["title"] + ": " + item for book in books for item in book["comparison_notes"]["limitations"])
    limits.append("Metai yra katalogo duomenys, nepriklausomai nepatikrinti; kalba, puslapiai ir pardavimo populiarumas nevertinti.")
    state["comparison"] = dict(mode="multiple" if len(books) > 1 else "single" if books else "empty",
        candidate_count=len(books), criteria_summary=json.dumps(state["preferences"], ensure_ascii=False),
        shared_subjects=shared, differences=differences, limitations=limits)
    state["warnings"] = list(dict.fromkeys(state["warnings"]))
    return state


def md(value):
    text = " ".join(str(value).split())
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([\\`*\[\]{}_!|])", r"\\\1", text)


def recommend_books(state):
    shown = state["books"][:3]
    lines = ["# Knygų rekomendacijos", "", f"Paieška: **{md(state['query'])}**.",
             f"Atrinkta {len(state['books'])}; rodoma {len(shown)}. Tai paieškos tvarka, ne kokybės ar pardavimų reitingas.", "",
             "Kriterijai: " + md(state["comparison"]["criteria_summary"]) + ".", ""]
    for index, book in enumerate(shown, 1):
        lines += [f"{index}. **[{md(book['title'])}](https://openlibrary.org{book['work_key']})** — "
                  + md(", ".join(book["authors"]) or "Autorius nenurodytas")
                  + ", katalogo pirmos publikacijos metai: " + md(book["first_publish_year"] if book["first_publish_year"] is not None else "nežinomi") + "."]
        for item in book["selection"]["checks"]:
            wanted = state["preferences"][item["criterion"]]
            lines.append(f"   - Atitinka {md(item['criterion'])} = {md(json.dumps(wanted, ensure_ascii=False))}; katalogo reikšmė: {md(json.dumps(item['evidence'], ensure_ascii=False))}.")
        if not book["selection"]["checks"]:
            lines.append("   - Filtrai netaikyti; asmeninis tinkamumas nevertintas.")
        if book["details_status"] == "ok" and book["subjects"]:
            lines.append("   - Katalogo temos: " + md(", ".join(book["subjects"][:5])) + ".")
        for limitation in book["comparison_notes"]["limitations"]:
            lines.append("   - " + md(limitation))
        lines += [f"   - [Paieškos šaltinis]({state['source_url']}) · [Kūrinio duomenys](https://openlibrary.org{book['work_key']}.json)", ""]
    for item in state["comparison"]["differences"]:
        lines.append(md(item["observation"]))
    lines += ["", f"Nepatvirtintos knygos: {len(state['pending_books'])}; atmestos: {len(state['rejected_books'])}.", ""]
    warnings = list(dict.fromkeys(state["warnings"] + state["comparison"]["limitations"]))
    lines.extend("- " + md(warning) for warning in warnings)
    lines += ["", "Tai penkių etapų programinė realizacija be kalbos modelio: siužeto santraukos nekuriamos, temos paliekamos šaltinio kalba. Katalogo įrašų datos gali būti klaidingos. Bestselerių sąrašai ir leidėjų metų patikra automatiškai nejungiami."]
    return "\n".join(lines) + "\n"


def verify_transition(previous, current):
    if current["schema_version"] != "1.0" or current["status"] not in {"ok", "partial", "error"}:
        raise WorkflowError("Netinkama etapo versija arba būsena.")
    if previous is None:
        return
    for key in ("schema_version", "query", "preferences", "source_url"):
        if previous[key] != current[key]:
            raise WorkflowError(f"Tarp etapų pasikeitė {key}.")
    def groups(state):
        return {b["work_key"]: b for key in ("books", "pending_books", "rejected_books") for b in state.get(key, [])}
    old, new = groups(previous), groups(current)
    count = sum(len(current.get(key, [])) for key in ("books", "pending_books", "rejected_books"))
    if len(new) != count or old.keys() != new.keys():
        raise WorkflowError("Prarastos arba pasikartojančios knygos.")
    for key, book in old.items():
        if any(new[key].get(field) != value for field, value in book.items()):
            raise WorkflowError("Pasikeitė ankstesni knygos laukai.")
    for group in ("books", "pending_books", "rejected_books"):
        expected = [book["work_key"] for book in previous.get(group, [])]
        actual = [book["work_key"] for book in current.get(group, [])]
        if current["stage"] != STAGES[2] and expected != actual:
            raise WorkflowError("Pasikeitė knygų grupių tvarka.")
    if current["stage"] == STAGES[3] and current["comparison"]["candidate_count"] != len(current["books"]):
        raise WorkflowError("Palyginimo skaičius nesutampa.")


def run(query, limit, prefs, output, client=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    client = client or Client()
    completed, files, current_stage = [], [], "ivestis"
    input_data = dict(query=query, limit=limit, preferences=prefs)
    def save(name, value):
        with (output / name).open("x", encoding="utf-8") as stream:
            stream.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))
        files.append(name)
    def finish(status, reason=None):
        save("vykdymo-busena.json", dict(status=status, stopped_at=current_stage if reason else None,
            reason=reason, completed_stages=completed, input=input_data, files=list(files)))
    try:
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            raise WorkflowError("Įveskite netuščią paiešką iki 1000 simbolių.")
        if type(limit) is not int or not 1 <= limit <= 20:
            raise WorkflowError("Kandidatų kiekis turi būti sveikasis skaičius nuo 1 iki 20.")
        validate_preferences(prefs)
        skills_root = Path(__file__).resolve().parents[2]
        instructions = {}
        for stage in STAGES:
            source = skills_root / stage / "SKILL.md"
            if not source.is_file():
                raise WorkflowError(f"Trūksta įgūdžio failo: {stage}/SKILL.md.")
            instructions[stage] = hashlib.sha256(source.read_bytes()).hexdigest()
        save("igudziu-versijos.json", instructions)
        state = None
        steps = [lambda: find_books(query, limit, prefs, client),
                 lambda: get_details(state, client), lambda: select_books(state),
                 lambda: compare_books(state)]
        for number, step in enumerate(steps, 1):
            current_stage = STAGES[number - 1]
            previous = state
            state = step()
            verify_transition(previous, state)
            save(f"{number:02}-{current_stage}.json", state)
            completed.append(current_stage)
            print(f"{number}/5 {current_stage}: {len(state['books'])} kandidatų; būsena {state['status']}.", flush=True)
            if state["status"] == "error":
                raise WorkflowError(state["error"] or "Etapo klaida.")
            if not state["books"]:
                reason = (f"Etape {current_stage} neliko atrinktų knygų. "
                          f"Nepatvirtintos: {len(state.get('pending_books', []))}; atmestos: {len(state.get('rejected_books', []))}. "
                          "Patikrinkite paiešką ir kriterijus; jie automatiškai nekeičiami.")
                save("sustojimo-priezastis.md", "# Eiga sustabdyta\n\n" + md(reason) + "\n")
                finish("stopped", reason)
                return 0
        current_stage = STAGES[4]
        save("05-rekomendacijos.md", recommend_books(state))
        completed.append(current_stage)
        print("5/5 rekomenduoti-knygas: rekomendacijos paruoštos.", flush=True)
        finish("completed")
        return 0
    except (WorkflowError, OSError, ValueError) as error:
        reason = str(error)
        save("sustojimo-priezastis.md", "# Eiga sustabdyta\n\nEtapas: " + md(current_stage) + ".\n\n" + md(reason) + "\n")
        finish("stopped", reason)
        print("Klaida: " + reason, flush=True)
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--query", default=os.environ.get("BOOK_QUERY", ""))
    parser.add_argument("--limit", default=os.environ.get("BOOK_LIMIT", "6"))
    parser.add_argument("--min-year", default=os.environ.get("BOOK_MIN_YEAR", ""))
    parser.add_argument("--max-year", default=os.environ.get("BOOK_MAX_YEAR", ""))
    parser.add_argument("--preferences", default=os.environ.get("BOOK_PREFERENCES", "{}"))
    args = parser.parse_args()
    try:
        prefs = json.loads(args.preferences)
        validate_preferences(prefs)
        for key, raw in (("min_year", args.min_year), ("max_year", args.max_year)):
            if raw.strip():
                year = int(raw)
                if key in prefs and prefs[key] != year:
                    raise WorkflowError(f"Prieštaraujantys metų laukai: {key}.")
                prefs[key] = year
        limit = int(args.limit)
    except (WorkflowError, ValueError) as error:
        path = Path(args.output)
        path.mkdir(parents=True, exist_ok=False)
        reason = "Netinkama įvestis: " + str(error)
        (path / "sustojimo-priezastis.md").write_text("# Eiga sustabdyta\n\n" + md(reason), encoding="utf-8")
        (path / "vykdymo-busena.json").write_text(json.dumps(dict(status="stopped", stopped_at="ivestis",
            reason=reason, completed_stages=[], input=dict(query=args.query, limit=args.limit,
            preferences=args.preferences), files=["sustojimo-priezastis.md"]), ensure_ascii=False, indent=2), encoding="utf-8")
        print(reason)
        return 1
    return run(args.query, limit, prefs, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
