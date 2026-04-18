import importlib
import json
import os
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = REPO_ROOT / "hermes-tasks"


class PipelineUtilsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "grants-system"
        self.wiki = Path(self.tmp.name) / "wiki"
        self.month = datetime.now().strftime("%Y-%m")
        self.year = self.month.split("-", 1)[0]
        (self.root / "configs").mkdir(parents=True)
        (self.root / "data" / "enriched" / self.month).mkdir(parents=True, exist_ok=True)
        (self.wiki / "Grants" / self.year / "05-Archive" / "Won").mkdir(parents=True)
        (self.wiki / "Grants" / self.year / "05-Archive" / "Lost").mkdir(parents=True)

        schema = {
            "required": [
                "grant_id",
                "name",
                "funder",
                "deadline",
                "amount",
                "url",
                "source_db",
                "scraped_date",
            ]
        }
        (self.root / "configs" / "grant_normalized.schema.json").write_text(
            json.dumps(schema),
            encoding="utf-8",
        )
        (self.wiki / "Grants" / self.year / "05-Archive" / "Won" / "sample.md").write_text(
            "---\ngrant_id: g1\nfunder: Sample Funders\nstatus: won\n---\n# Sample\n",
            encoding="utf-8",
        )
        (self.wiki / "Grants" / self.year / "05-Archive" / "Lost" / "another.md").write_text(
            "---\ngrant_id: g2\nfunder: Sample Funders\nstatus: lost\n---\n# Sample\n",
            encoding="utf-8",
        )
        os.environ["GRANTS_ROOT"] = str(self.root)
        os.environ["WIKI_ROOT"] = str(self.wiki)

        sys.path.insert(0, str(TASKS_DIR))
        for name in ["grants_context", "pipeline_validation", "outcome_tracker", "grant_archive"]:
            sys.modules.pop(name, None)

        self.pipeline_validation = importlib.import_module("pipeline_validation")
        self.outcome_tracker = importlib.import_module("outcome_tracker")
        self.grant_archive = importlib.import_module("grant_archive")

    def tearDown(self):
        self.tmp.cleanup()
        for key in ["GRANTS_ROOT", "WIKI_ROOT"]:
            os.environ.pop(key, None)
        if str(TASKS_DIR) in sys.path:
            sys.path.remove(str(TASKS_DIR))

    def test_validate_grant_collection_flags_bad_records(self):
        errors = self.pipeline_validation.validate_grant_collection(
            [
                {
                    "grant_id": "1",
                    "name": "Bad Grant",
                    "funder": "Funder",
                    "deadline": "not-a-date",
                    "amount": "1000",
                }
            ],
            stage="raw",
        )

        self.assertTrue(errors)
        self.assertTrue(any("Invalid deadline format" in error for error in errors))
        self.assertTrue(any("Amount must be numeric" in error for error in errors))

    def test_outcome_tracker_aggregates_funder_history(self):
        now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        enriched = [
            {
                "grant_id": "g1",
                "name": "Won Grant",
                "funder": "Sample Funders",
                "deadline": f"{self.year}-05-01",
                "amount": 1000,
                "url": "https://example.com",
                "source_db": "ri-grants",
                "scraped_date": now_iso,
                "status": "won",
            },
            {
                "grant_id": "g2",
                "name": "Lost Grant",
                "funder": "Sample Funders",
                "deadline": f"{self.year}-05-02",
                "amount": 1000,
                "url": "https://example.com",
                "source_db": "ri-grants",
                "scraped_date": now_iso,
                "status": "lost",
            },
        ]
        output_file = self.root / "data" / "enriched" / self.month / "grants-enriched.json"
        output_file.write_text(json.dumps(enriched), encoding="utf-8")

        index = self.outcome_tracker.build_funder_outcome_index()
        self.assertIn("Sample Funders", index)
        self.assertEqual(index["Sample Funders"]["won"], 1)
        self.assertEqual(index["Sample Funders"]["lost"], 1)
        self.assertTrue(index["Sample Funders"]["past_success"])
        self.assertTrue(index["Sample Funders"]["known_rejections"])

        annotated = self.outcome_tracker.annotate_grants_with_outcomes(
            [
                {
                    "grant_id": "g3",
                    "name": "Current Grant",
                    "funder": "Sample Funders",
                    "deadline": f"{self.year}-05-03",
                    "amount": 1000,
                    "url": "https://example.com",
                    "source_db": "ri-grants",
                    "scraped_date": now_iso,
                }
            ]
        )
        self.assertTrue(annotated[0]["enrichment"]["past_success"])
        self.assertTrue(annotated[0]["enrichment"]["known_rejections"])

    def test_archive_grant_updates_enriched_json_and_ledger(self):
        now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        enriched = [
            {
                "grant_id": "g1",
                "name": "Archive Grant",
                "funder": "Sample Funders",
                "deadline": f"{self.year}-05-01",
                "amount": 1000,
                "url": "https://example.com",
                "source_db": "ri-grants",
                "scraped_date": now_iso,
                "status": "new",
            }
        ]
        output_file = self.root / "data" / "enriched" / self.month / "grants-enriched.json"
        output_file.write_text(json.dumps(enriched), encoding="utf-8")

        result = self.grant_archive.archive_grant(
            "g1", "won", month_str=self.month, note="Selected for award"
        )

        updated = json.loads(output_file.read_text(encoding="utf-8"))
        self.assertEqual(updated[0]["status"], "won")
        self.assertIn("archive_note", result)
        self.assertIn("ledger_path", result)
        self.assertTrue(Path(result["archive_note"]).exists())
        self.assertTrue(Path(result["ledger_path"]).exists())
        ledger = json.loads(Path(result["ledger_path"]).read_text(encoding="utf-8"))
        self.assertEqual(ledger[0]["grant_id"], "g1")
        self.assertEqual(ledger[0]["status"], "won")
        self.assertEqual(ledger[0]["note"], "Selected for award")


if __name__ == "__main__":
    unittest.main()
