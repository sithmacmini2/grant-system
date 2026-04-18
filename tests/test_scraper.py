import importlib
import json
import os
from datetime import datetime
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = REPO_ROOT / "hermes-tasks"

if str(TASKS_DIR) not in sys.path:
    sys.path.insert(0, str(TASKS_DIR))


class ScraperTests(unittest.TestCase):
    def setUp(self):
        for name in ["grants_context", "pipeline_validation", "scraper"]:
            sys.modules.pop(name, None)
        os.environ["GRANTS_ROOT"] = str(REPO_ROOT)
        self.scraper_module = importlib.import_module("scraper")
        self.scraper = self.scraper_module.GrantScraper()
        self.year = datetime.now().year

    def tearDown(self):
        os.environ.pop("GRANTS_ROOT", None)

    def test_helper_parsers_extract_deadline_and_amount(self):
        self.assertEqual(
            self.scraper._parse_deadline(f"Apply by 05/17/{self.year}"),
            f"{self.year}-05-17",
        )
        self.assertEqual(
            self.scraper._parse_deadline(f"Deadline: May 17, {self.year}"),
            f"{self.year}-05-17",
        )
        self.assertEqual(self.scraper._parse_amount("Up to $50,000 available"), 50000.0)

    def test_source_specific_query_terms_are_used(self):
        base_url, params = self.scraper._build_search_url(
            {
                "id": "ri-grants",
                "name": "Rhode Island Grants",
                "base_url": "https://example.com",
                "search_params": {"query": "search"},
                "query_terms": ["youth", "community", "equity"],
                "parse_mode": "table",
            }
        )

        self.assertEqual(base_url, "https://example.com")
        self.assertEqual(params["query"], "youth community equity")

    def test_scrape_database_parses_table_rows(self):
        html = f"""
        <html>
          <body>
            <table>
              <tr>
                <th>Opportunity</th>
                <th>Deadline</th>
                <th>Award</th>
              </tr>
              <tr>
                <td><a href="/grant/123">Youth Leadership Development Grant</a></td>
                <td>{self.year}-05-17</td>
                <td>$50,000</td>
              </tr>
            </table>
          </body>
        </html>
        """

        class FakeResponse:
            def __init__(self, text, url):
                self.text = text
                self.url = url

        self.scraper._request = lambda *args, **kwargs: FakeResponse(
            html, "https://example.com/listings"
        )

        grants = self.scraper.scrape_database(
            {
                "id": "ri-grants",
                "name": "Rhode Island Grants",
                "base_url": "https://example.com",
                "enabled": True,
            }
        )

        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0]["name"], "Youth Leadership Development Grant")
        self.assertEqual(grants[0]["deadline"], f"{self.year}-05-17")
        self.assertEqual(grants[0]["amount"], 50000.0)
        self.assertEqual(grants[0]["url"], "https://example.com/grant/123")
        self.assertEqual(grants[0]["source_parse_mode"], "auto")
        self.assertIn("community", grants[0]["source_query_terms"])

    def test_scrape_database_skips_non_parseable_page(self):
        html = "<html><body><p>No grant data here.</p></body></html>"

        class FakeResponse:
            def __init__(self, text, url):
                self.text = text
                self.url = url

        self.scraper._request = lambda *args, **kwargs: FakeResponse(
            html, "https://example.com/listings"
        )

        grants = self.scraper.scrape_database(
            {
                "id": "ri-grants",
                "name": "Rhode Island Grants",
                "base_url": "https://example.com",
                "enabled": True,
            }
        )

        self.assertEqual(grants, [])

    def test_scrape_database_uses_selector_hints_for_cards(self):
        html = f"""
        <html>
          <body>
            <div class="grant-card">
              <h2 class="title">Community Opportunity Grant</h2>
              <a class="details" href="/grants/456">View</a>
              <span class="deadline">Deadline: {self.year}-05-18</span>
              <span class="amount">Up to $25,000</span>
            </div>
          </body>
        </html>
        """

        class FakeResponse:
            def __init__(self, text, url):
                self.text = text
                self.url = url

        self.scraper._request = lambda *args, **kwargs: FakeResponse(
            html, "https://example.com/listings"
        )

        grants = self.scraper.scrape_database(
            {
                "id": "ri-grants",
                "name": "Rhode Island Grants",
                "base_url": "https://example.com",
                "enabled": True,
                "parse_mode": "cards",
                "selectors": {
                    "card_selector": ".grant-card",
                    "title_selector": ".title",
                    "deadline_selector": ".deadline",
                    "amount_selector": ".amount",
                    "link_selector": ".details",
                },
            }
        )

        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0]["name"], "Community Opportunity Grant")
        self.assertEqual(grants[0]["deadline"], f"{self.year}-05-18")
        self.assertEqual(grants[0]["amount"], 25000.0)
        self.assertEqual(grants[0]["url"], "https://example.com/grants/456")

    def test_grant_ids_are_stable_for_same_inputs(self):
        grant_id_one = self.scraper._stable_grant_id(
            "ri-grants", "Youth Leadership Development Grant", f"{self.year}-05-17", "https://example.com/grant/123"
        )
        grant_id_two = self.scraper._stable_grant_id(
            "ri-grants", "Youth Leadership Development Grant", f"{self.year}-05-17", "https://example.com/grant/123"
        )

        self.assertEqual(grant_id_one, grant_id_two)
        self.assertTrue(grant_id_one.startswith("RI-GRANTS-"))

    def test_scrape_database_parses_json_records(self):
        payload = {
            "results": [
                {
                    "title": "API Opportunity Grant",
                    "deadline": f"{self.year}-05-20",
                    "grant_amount": 40000,
                    "description": "Support for community programs",
                    "link": "/api/grants/789",
                }
            ]
        }

        response = SimpleNamespace(
            headers={"Content-Type": "application/json"},
            text=json.dumps(payload),
            url="https://api.example.com/search",
            json=lambda: payload,
        )

        self.scraper._request = lambda *args, **kwargs: response

        grants = self.scraper.scrape_database(
            {
                "id": "candid",
                "name": "Candid",
                "base_url": "https://api.example.com",
                "enabled": True,
                "parse_mode": "api",
                "fields": {
                    "name": "title",
                    "deadline": "deadline",
                    "amount": "grant_amount",
                    "criteria": "description",
                    "url": "link",
                },
            }
        )

        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0]["name"], "API Opportunity Grant")
        self.assertEqual(grants[0]["deadline"], f"{self.year}-05-20")
        self.assertEqual(grants[0]["amount"], 40000.0)
        self.assertEqual(grants[0]["url"], "https://api.example.com/api/grants/789")
        self.assertEqual(grants[0]["provenance"]["parse_mode"], "api")


if __name__ == "__main__":
    unittest.main()
