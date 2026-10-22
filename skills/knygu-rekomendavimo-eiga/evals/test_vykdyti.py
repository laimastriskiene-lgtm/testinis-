import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "vykdyti.py"
spec = importlib.util.spec_from_file_location("vykdyti", SCRIPT)
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)


def doc(number, year=2000):
    return dict(key=f"/works/OL{number}W", title=f"Knyga {number}",
                author_name=["Autorė"], first_publish_year=year)


class FakeClient:
    def __init__(self, docs, outcomes=None):
        self.docs = docs
        self.outcomes = outcomes or {}
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if "/search.json?" in url:
            return {"docs": copy.deepcopy(self.docs)}
        key = url.removeprefix("https://openlibrary.org").removesuffix(".json")
        outcome = self.outcomes.get(key, dict(key=key, type={"key": "/type/work"},
            description={"value": "A magic journey"}, subjects=["Fantasy", "Fantasy"]))
        if isinstance(outcome, Exception):
            raise outcome
        return copy.deepcopy(outcome)


class WorkflowTests(unittest.TestCase):
    def execute(self, docs, prefs=None, outcomes=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / "rezultatai"
        client = FakeClient(docs, outcomes)
        code = flow.run("fantasy", 6, prefs if prefs is not None else {"min_year": 2000}, output, client)
        state = json.loads((output / "vykdymo-busena.json").read_text(encoding="utf-8"))
        return code, state, output, client

    def test_all_five_stages_preserve_sources_and_records(self):
        code, state, output, _ = self.execute([doc(1), doc(2, 2020)])
        self.assertEqual((code, state["status"], state["completed_stages"]), (0, "completed", list(flow.STAGES)))
        first = json.loads((output / "01-rasti-knygas.json").read_text(encoding="utf-8"))
        fourth = json.loads((output / "04-palyginti-knygas.json").read_text(encoding="utf-8"))
        self.assertEqual(first["source_url"], fourth["source_url"])
        self.assertEqual(first["preferences"], fourth["preferences"])
        for old, new in zip(first["books"], fourth["books"]):
            self.assertTrue(all(new[k] == v for k, v in old.items()))
        self.assertEqual(fourth["books"][0]["description"], "A magic journey")
        self.assertEqual(fourth["books"][0]["subjects"], ["Fantasy"])

    def test_empty_search_stops_before_details(self):
        code, state, output, client = self.execute([])
        self.assertEqual((code, state["stopped_at"]), (0, flow.STAGES[0]))
        self.assertEqual(len(client.calls), 1)
        self.assertFalse((output / "02-gauti-knygu-duomenis.json").exists())

    def test_year_boundary_and_rejection(self):
        _, _, output, _ = self.execute([doc(1, 1999), doc(2, 2000), doc(3, 2001)],
                                      {"min_year": 2000, "max_year": 2000})
        result = json.loads((output / "03-atrinkti-knygas.json").read_text(encoding="utf-8"))
        self.assertEqual([b["work_key"] for b in result["books"]], ["/works/OL2W"])
        self.assertEqual(len(result["rejected_books"]), 2)

    def test_unsupported_filter_stops_at_selection(self):
        code, state, output, _ = self.execute([doc(1)], {"language": "lit"})
        self.assertEqual((code, state["stopped_at"]), (0, flow.STAGES[2]))
        selected = json.loads((output / "03-atrinkti-knygas.json").read_text(encoding="utf-8"))
        self.assertEqual(len(selected["pending_books"]), 1)
        self.assertIn("language", " ".join(selected["warnings"]))
        self.assertFalse((output / "04-palyginti-knygas.json").exists())

    def test_unknown_year_is_pending_not_rejected(self):
        _, state, output, _ = self.execute([doc(1, None)])
        result = json.loads((output / "03-atrinkti-knygas.json").read_text(encoding="utf-8"))
        self.assertEqual(len(result["pending_books"]), 1)
        self.assertEqual(result["rejected_books"], [])
        self.assertEqual(state["status"], "stopped")

    def test_rate_limit_prevents_remaining_requests(self):
        _, _, output, client = self.execute([doc(1), doc(2), doc(3)], outcomes={
            "/works/OL2W": flow.RateLimit("HTTP 429")})
        self.assertEqual(len(client.calls), 3)  # paieška, pirma, antra
        result = json.loads((output / "02-gauti-knygu-duomenis.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["books"][2]["details_status"], "error")
        report = (output / "05-rekomendacijos.md").read_text(encoding="utf-8")
        self.assertIn("429", report)

    def test_all_details_fail_stop_with_error(self):
        code, state, output, _ = self.execute([doc(1)], outcomes={
            "/works/OL1W": flow.WorkflowError("HTTP 404")})
        self.assertEqual((code, state["stopped_at"]), (1, flow.STAGES[1]))
        self.assertFalse((output / "03-atrinkti-knygas.json").exists())

    def test_author_casefold_and_keyword(self):
        _, state, output, _ = self.execute([doc(1)], {
            "authors": [" autorė "], "description_keywords_any": ["MAGIC"]})
        self.assertEqual(state["status"], "completed")
        self.assertTrue((output / "05-rekomendacijos.md").exists())

    def test_missing_subjects_do_not_prove_exclusion(self):
        record = dict(key="/works/OL1W", type={"key": "/type/work"}, subjects=[])
        _, state, output, _ = self.execute([doc(1)], {"excluded_subjects": ["Horror"]}, {"/works/OL1W": record})
        result = json.loads((output / "03-atrinkti-knygas.json").read_text(encoding="utf-8"))
        self.assertEqual(len(result["pending_books"]), 1)
        self.assertEqual(state["stopped_at"], flow.STAGES[2])

    def test_duplicate_and_invalid_ids_are_removed_in_search(self):
        docs = [doc(1), doc(1), dict(key="https://example.com", title="Netinkama")]
        _, _, output, client = self.execute(docs)
        first = json.loads((output / "01-rasti-knygas.json").read_text(encoding="utf-8"))
        self.assertEqual(len(first["books"]), 1)
        self.assertEqual(len(client.calls), 2)

    def test_one_candidate_and_missing_description(self):
        record = dict(key="/works/OL1W", type={"key": "/type/work"}, subjects=["Fantasy"])
        _, state, output, _ = self.execute([doc(1)], outcomes={"/works/OL1W": record})
        fourth = json.loads((output / "04-palyginti-knygas.json").read_text(encoding="utf-8"))
        self.assertEqual(fourth["status"], "partial")
        self.assertEqual(fourth["comparison"]["mode"], "single")
        self.assertIn("Alternatyvų", (output / "05-rekomendacijos.md").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "completed")

    def test_do_not_replace_existing_output(self):
        _, _, output, _ = self.execute([doc(1)])
        original = (output / "vykdymo-busena.json").read_bytes()
        with self.assertRaises(FileExistsError):
            flow.run("x", 1, {}, output, FakeClient([]))
        self.assertEqual((output / "vykdymo-busena.json").read_bytes(), original)

    def test_invalid_cli_json_produces_failure_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "out"
            with patch.object(sys, "argv", [str(SCRIPT), "--query", "fantasy", "--output", str(output), "--preferences", "[]"]):
                self.assertEqual(flow.main(), 1)
            result = json.loads((output / "vykdymo-busena.json").read_text(encoding="utf-8"))
            self.assertEqual(result["completed_stages"], [])
            self.assertEqual(result["stopped_at"], "ivestis")

    def test_corrupted_transition_fails(self):
        original = flow.find_books("x", 1, {}, FakeClient([doc(1)]))
        corrupted = copy.deepcopy(original)
        corrupted["preferences"] = {"min_year": 2020}
        with self.assertRaises(flow.WorkflowError):
            flow.verify_transition(original, corrupted)

    def test_html_and_markdown_in_titles_are_data(self):
        bad = doc(1)
        bad["title"] = '<script>bad</script> [click](https://example.com)'
        _, _, output, _ = self.execute([bad])
        report = (output / "05-rekomendacijos.md").read_text(encoding="utf-8")
        self.assertNotIn("<script>", report)
        self.assertIn("\\[click\\]", report)

    def test_only_first_three_candidates_are_recommended(self):
        _, _, output, _ = self.execute([doc(i) for i in range(1, 7)])
        report = (output / "05-rekomendacijos.md").read_text(encoding="utf-8")
        self.assertIn("Atrinkta 6; rodoma 3", report)
        self.assertNotIn("**[Knyga 4]", report)


if __name__ == "__main__":
    unittest.main()
