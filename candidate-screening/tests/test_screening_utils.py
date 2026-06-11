import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parents[1] / "scripts" / "screening_utils.py"
)
SPEC = importlib.util.spec_from_file_location("screening_utils", MODULE_PATH)
screening_utils = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(screening_utils)


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "potential-leads").mkdir()
        (self.root / ".candidate-screening").mkdir()
        (self.root / "job-description.md").write_text("role", encoding="utf-8")
        (self.root / "candidate-portrait.md").write_text("portrait", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_manifest(self, leads):
        manifest = {
            "job_description_hash": screening_utils.sha256_file(
                self.root / "job-description.md"
            ),
            "candidate_portrait_hash": screening_utils.sha256_file(
                self.root / "candidate-portrait.md"
            ),
            "leads": leads,
        }
        (self.root / ".candidate-screening" / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

    def test_unchanged_checked_lead_is_not_eligible_for_screening(self):
        lead = self.root / "potential-leads" / "jane.md"
        lead.write_text("Jane profile", encoding="utf-8")
        self.write_manifest(
            {
                "potential-leads/jane.md": {
                    "lead_hash": screening_utils.sha256_file(lead),
                    "screening_status": "checked_not_proceeded",
                    "checked_at": "2026-06-08T00:00:00Z",
                }
            }
        )

        result = screening_utils.status(self.root)["leads"][0]

        self.assertFalse(result["eligible_for_screening"])
        self.assertEqual(result["screening_status"], "checked_not_proceeded")

    def test_changed_checked_lead_is_eligible_for_screening(self):
        lead = self.root / "potential-leads" / "jane.md"
        lead.write_text("Old profile", encoding="utf-8")
        old_hash = screening_utils.sha256_file(lead)
        lead.write_text("Updated profile", encoding="utf-8")
        self.write_manifest(
            {
                "potential-leads/jane.md": {
                    "lead_hash": old_hash,
                    "screening_status": "checked_not_proceeded",
                    "checked_at": "2026-06-08T00:00:00Z",
                }
            }
        )

        result = screening_utils.status(self.root)["leads"][0]

        self.assertTrue(result["eligible_for_screening"])

    def test_untracked_lead_is_eligible_for_screening(self):
        (self.root / "potential-leads" / "jane.md").write_text(
            "Jane profile",
            encoding="utf-8",
        )
        self.write_manifest({})

        result = screening_utils.status(self.root)["leads"][0]

        self.assertTrue(result["eligible_for_screening"])
        self.assertEqual(result["screening_status"], "not_checked")

    def test_mark_checked_records_not_proceeded_status(self):
        lead = self.root / "potential-leads" / "jane.md"
        lead.write_text("Jane profile", encoding="utf-8")
        report = self.root / "candidates" / "jane" / "report.md"
        report.parent.mkdir(parents=True)
        report.write_text("## Summary\nJane", encoding="utf-8")
        self.write_manifest({})

        screening_utils.mark_checked(
            self.root,
            "potential-leads/jane.md",
            "candidates/jane/report.md",
            42,
        )

        manifest = screening_utils.read_manifest(self.root)
        entry = manifest["leads"]["potential-leads/jane.md"]
        self.assertEqual(entry["screening_status"], "checked_not_proceeded")
        self.assertEqual(entry["score"], 42)
        self.assertEqual(entry["lead_hash"], screening_utils.sha256_file(lead))
        self.assertEqual(entry["report_hash"], screening_utils.sha256_file(report))
        self.assertIn("checked_at", entry)


if __name__ == "__main__":
    unittest.main()
