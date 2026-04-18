#!/usr/bin/env python3
"""
Layer 1: Grant Database Scraper
Fetches grant opportunities from configured sources and stores only
records that can be parsed from source responses.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from grants_context import active_month, grants_path
from pipeline_validation import validate_grant_collection


GRANTS_ROOT = grants_path()
CONFIG_FILE = GRANTS_ROOT / "configs" / "grant-databases.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper")

CURRENCY_RE = re.compile(r"\$[\d,]+(?:\.\d{2})?")
ISO_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
US_DATE_RE = re.compile(
    r"\b(?P<month>0?[1-9]|1[0-2])/(?P<day>0?[1-9]|[12]\d|3[01])/(?P<year>20\d{2})\b"
)
LONG_DATE_RE = re.compile(
    r"\b(?P<month>[A-Za-z]{3,9})\s+(?P<day>0?[1-9]|[12]\d|3[01]),\s*(?P<year>20\d{2})\b"
)
GRANT_KEYWORDS = (
    "grant",
    "funding",
    "fellowship",
    "award",
    "opportunity",
    "proposal",
    "program",
    "initiative",
    "scholarship",
)


@dataclass(frozen=True)
class SourceContext:
    source_id: str
    name: str
    base_url: str
    parse_mode: str = "auto"
    query_terms: tuple[str, ...] = ("community", "youth", "equity")
    search_endpoint: str | None = None
    search_params: dict | None = None
    api_key_required: bool = False
    fields: dict | None = None
    selectors: dict | None = None


class GrantScraper:
    def __init__(self, config_file=CONFIG_FILE):
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.databases = [
            db for db in self.config.get("target_databases", []) if db.get("enabled", True)
        ]
        self.session = requests.Session()

    def _source_context(self, db) -> SourceContext:
        return SourceContext(
            source_id=db["id"],
            name=db["name"],
            base_url=db["base_url"],
            parse_mode=(db.get("parse_mode") or "auto").lower(),
            query_terms=tuple(db.get("query_terms") or ("community", "youth", "equity")),
            search_endpoint=db.get("search_endpoint"),
            search_params=db.get("search_params"),
            api_key_required=bool(db.get("api_key_required")),
            fields=db.get("fields") or {},
            selectors=db.get("selectors") or {},
        )

    def _api_key_available(self, source_id: str) -> bool:
        candidates = [
            f"{source_id.upper().replace('-', '_')}_API_KEY",
            "GRANTS_API_KEY",
        ]
        return any(os.environ.get(name) for name in candidates)

    def _should_skip_source(self, db) -> bool:
        if db.get("api_key_required") and not self._api_key_available(db["id"]):
            logger.warning(
                "Skipping %s because an API key is required but not configured",
                db["name"],
            )
            return True
        return False

    def _request(self, url, params=None, timeout=30, attempts=3):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        }
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                response = self.session.get(url, params=params, headers=headers, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(min(2 ** (attempt - 1), 5))
        raise last_error

    def _build_search_url(self, db) -> tuple[str, dict]:
        source = self._source_context(db)
        base = source.base_url
        params = dict(source.search_params or {})
        query_term = " ".join(source.query_terms).strip() or "community youth black"

        # Prefer source-specific search endpoints when they exist.
        if source.search_endpoint:
            base = urljoin(base.rstrip("/") + "/", source.search_endpoint.lstrip("/"))

        # Populate known search placeholders with source-specific search terms.
        if "query" in params:
            params["query"] = query_term
        elif "q" in params:
            params["q"] = query_term
        elif "keyword" in params:
            params["keyword"] = query_term
        elif "search" in params:
            params["search"] = query_term

        return base, params

    def _parse_deadline(self, text: str) -> str | None:
        text = " ".join(text.split())
        iso_match = ISO_DATE_RE.search(text)
        if iso_match:
            return iso_match.group(1)

        us_match = US_DATE_RE.search(text)
        if us_match:
            month = int(us_match.group("month"))
            day = int(us_match.group("day"))
            year = int(us_match.group("year"))
            return datetime(year, month, day).strftime("%Y-%m-%d")

        long_match = LONG_DATE_RE.search(text)
        if long_match:
            month_name = long_match.group("month")[:3].title()
            try:
                month_num = datetime.strptime(month_name, "%b").month
            except ValueError:
                return None
            day = int(long_match.group("day"))
            year = int(long_match.group("year"))
            return datetime(year, month_num, day).strftime("%Y-%m-%d")

        return None

    def _parse_amount(self, text: str) -> float:
        match = CURRENCY_RE.search(text.replace("USD", "$"))
        if not match:
            return 0.0
        value = match.group(0).replace("$", "").replace(",", "")
        try:
            return float(value)
        except ValueError:
            return 0.0

    def _looks_like_grant(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in GRANT_KEYWORDS)

    def _text_signature(self, name: str, funder: str, deadline: str, amount: float) -> tuple[str, str, str, float]:
        return (name.strip().lower(), funder.strip().lower(), deadline, amount)

    @staticmethod
    def _first_text(node, selector: str | None) -> str:
        if selector:
            match = node.select_one(selector)
            if match:
                return match.get_text(" ", strip=True)
        return ""

    @staticmethod
    def _first_link(node, selector: str | None) -> str | None:
        if selector:
            match = node.select_one(selector)
            if match and match.has_attr("href"):
                return match["href"]
        links = node.find_all("a", href=True)
        if links:
            return links[0]["href"]
        return None

    @staticmethod
    def _extract_value(data, path: str | None):
        if not path:
            return None
        current = data
        for part in str(path).strip().split("."):
            if current is None:
                return None
            if isinstance(current, list):
                try:
                    index = int(part)
                except ValueError:
                    return None
                if index < 0 or index >= len(current):
                    return None
                current = current[index]
                continue
            if isinstance(current, dict):
                current = current.get(part)
                continue
            return None
        return current

    @staticmethod
    def _stable_grant_id(source_id: str, name: str, deadline: str, url: str) -> str:
        payload = "||".join(
            [
                source_id.strip().lower(),
                name.strip().lower(),
                deadline.strip(),
                url.strip(),
            ]
        ).encode("utf-8")
        digest = hashlib.sha1(payload).hexdigest()[:12]
        return f"{source_id.upper()}-{digest}"

    def _coerce_api_records(self, payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("results", "data", "items", "opportunities", "grants"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
            return [payload]
        return []

    @staticmethod
    def _payload_kind(response) -> str:
        headers = getattr(response, "headers", {}) or {}
        content_type = str(headers.get("Content-Type") or "").lower()
        if "json" in content_type:
            return "json"
        body = getattr(response, "text", "").lstrip()
        if body.startswith("{") or body.startswith("["):
            return "json"
        return "html"

    def _make_grant(
        self,
        *,
        source: SourceContext,
        name: str,
        deadline: str | None,
        amount: float,
        criteria: str,
        url: str,
        scraped_date: str,
    ) -> dict | None:
        name = " ".join(name.split()).strip()
        if not name or not deadline:
            return None

        return {
            "grant_id": self._stable_grant_id(source.source_id, name, deadline, url),
            "name": name[:150],
            "funder": source.name,
            "deadline": deadline,
            "amount": amount,
            "criteria": criteria.strip()[:2000] or f"Opportunity from {source.name}",
            "url": url,
            "source_db": source.source_id,
            "scraped_date": scraped_date,
            "status": "new",
            "source_parse_mode": source.parse_mode,
            "source_query_terms": list(source.query_terms),
            "provenance": {
                "source_id": source.source_id,
                "source_name": source.name,
                "source_url": url,
                "parse_mode": source.parse_mode,
                "query_terms": list(source.query_terms),
                "scraped_at": scraped_date,
            },
        }

    def _parse_json_records(
        self, payload, source: SourceContext, page_url: str, scraped_date: str
    ) -> list[dict]:
        grants = []
        seen = set()
        records = self._coerce_api_records(payload)
        fields = source.fields or {}

        for record in records:
            if not isinstance(record, dict):
                continue

            title = self._extract_value(record, fields.get("name")) or self._extract_value(record, "title") or self._extract_value(record, "name")
            deadline_value = self._extract_value(record, fields.get("deadline")) or self._extract_value(record, "deadline")
            amount_value = self._extract_value(record, fields.get("amount")) or self._extract_value(record, "amount")
            criteria = self._extract_value(record, fields.get("criteria")) or self._extract_value(record, "description") or ""
            url_value = self._extract_value(record, fields.get("url")) or self._extract_value(record, "url")

            link_url = urljoin(page_url, url_value) if isinstance(url_value, str) and url_value else page_url
            deadline = self._parse_deadline(str(deadline_value)) if deadline_value else None
            if deadline is None and isinstance(deadline_value, str):
                deadline = deadline_value.strip()

            try:
                amount = float(amount_value) if amount_value is not None else 0.0
            except (TypeError, ValueError):
                amount = self._parse_amount(str(amount_value))

            grant = self._make_grant(
                source=source,
                name=str(title or "").strip(),
                deadline=deadline,
                amount=amount,
                criteria=str(criteria or ""),
                url=link_url,
                scraped_date=scraped_date,
            )
            if grant is None:
                continue

            signature = self._text_signature(
                grant["name"], grant["funder"], grant["deadline"], grant["amount"]
            )
            if signature in seen:
                continue
            seen.add(signature)
            grants.append(grant)

        return grants

    def _parse_table(self, table, source: SourceContext, page_url: str, scraped_date: str) -> list[dict]:
        grants = []
        seen = set()
        selectors = source.selectors or {}

        rows = table.select(selectors.get("row_selector")) if selectors.get("row_selector") else table.find_all("tr")
        for row in rows:
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if not cells:
                continue

            row_text = " ".join(cells)
            if not self._looks_like_grant(row_text) and not self._parse_deadline(row_text):
                continue

            link_href = self._first_link(row, selectors.get("link_selector"))
            link_url = urljoin(page_url, link_href) if link_href else page_url
            title = self._first_text(row, selectors.get("title_selector"))
            if not title and link_href:
                links = row.find_all("a", href=True)
                if links:
                    title = links[0].get_text(" ", strip=True)
            if not title:
                title = max(cells, key=len)

            deadline_text = self._first_text(row, selectors.get("deadline_selector"))
            deadline = self._parse_deadline(deadline_text) if deadline_text else self._parse_deadline(row_text)
            amount_text = self._first_text(row, selectors.get("amount_selector")) or row_text
            amount = self._parse_amount(amount_text)
            criteria = row_text

            grant = self._make_grant(
                source=source,
                name=title,
                deadline=deadline,
                amount=amount,
                criteria=criteria,
                url=link_url,
                scraped_date=scraped_date,
            )
            if grant is None:
                continue

            signature = self._text_signature(
                grant["name"], grant["funder"], grant["deadline"], grant["amount"]
            )
            if signature in seen:
                continue
            seen.add(signature)
            grants.append(grant)

        return grants

    def _parse_cards(self, soup: BeautifulSoup, source: SourceContext, page_url: str, scraped_date: str) -> list[dict]:
        grants = []
        seen = set()
        selectors = source.selectors or {}
        candidates = soup.select(selectors.get("card_selector")) if selectors.get("card_selector") else soup.find_all(["article", "li", "section", "div"])

        for node in candidates:
            text = node.get_text(" ", strip=True)
            if len(text) < 40:
                continue
            if not self._looks_like_grant(text) and not self._parse_deadline(text):
                continue

            link_href = self._first_link(node, selectors.get("link_selector"))
            link_url = urljoin(page_url, link_href) if link_href else page_url
            title = self._first_text(node, selectors.get("title_selector"))
            if not title and link_href:
                links = node.find_all("a", href=True)
                if links:
                    title = links[0].get_text(" ", strip=True)
            if not title:
                headings = node.find_all(["h1", "h2", "h3", "h4", "strong"])
                if headings:
                    title = headings[0].get_text(" ", strip=True)
            if not title:
                title = text[:120]

            deadline_text = self._first_text(node, selectors.get("deadline_selector"))
            deadline = self._parse_deadline(deadline_text) if deadline_text else self._parse_deadline(text)
            amount_text = self._first_text(node, selectors.get("amount_selector")) or text
            amount = self._parse_amount(amount_text)
            grant = self._make_grant(
                source=source,
                name=title,
                deadline=deadline,
                amount=amount,
                criteria=text,
                url=link_url,
                scraped_date=scraped_date,
            )
            if grant is None:
                continue

            signature = self._text_signature(
                grant["name"], grant["funder"], grant["deadline"], grant["amount"]
            )
            if signature in seen:
                continue
            seen.add(signature)
            grants.append(grant)

        return grants

    def scrape_database(self, db) -> list[dict]:
        """Scrape a single configured source."""
        source = self._source_context(db)
        if self._should_skip_source(db):
            self._record_run(source, 0, "skipped")
            return []

        url, params = self._build_search_url(db)
        logger.info("Scraping %s", source.name)

        try:
            response = self._request(url, params=params if params else None)
        except requests.RequestException as exc:
            logger.error("Failed to fetch %s: %s", source.name, exc)
            self._record_run(source, 0, "error", url=url, error=str(exc))
            return []

        scraped_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        payload_kind = self._payload_kind(response)

        grants = []
        if payload_kind == "json" and source.parse_mode in {"auto", "api"}:
            try:
                grants.extend(self._parse_json_records(response.json(), source, response.url, scraped_date))
            except ValueError:
                logger.warning("JSON response could not be parsed for %s", source.name)
        else:
            soup = BeautifulSoup(response.text, "html.parser")
            tables = (
                soup.select(source.selectors.get("table_selector"))
                if source.selectors and source.selectors.get("table_selector")
                else soup.find_all("table")
            )
            if source.parse_mode in {"auto", "table"}:
                for table in tables:
                    grants.extend(self._parse_table(table, source, response.url, scraped_date))

            if not grants and source.parse_mode in {"auto", "cards"}:
                grants.extend(self._parse_cards(soup, source, response.url, scraped_date))

        logger.info("Found %s grants from %s", len(grants), source.name)
        self._record_run(source, len(grants), payload_kind, url=response.url)
        return grants

    def scrape_all(self, sources=None):
        """Scrape all or selected sources from config."""
        selected = set(sources or [])
        all_grants = []
        self.run_history = []

        for db in self.databases:
            if selected and db["id"] not in selected and db["type"] not in selected:
                continue
            all_grants.extend(self.scrape_database(db))

        logger.info("Total grants scraped: %s", len(all_grants))
        return all_grants

    def _record_run(
        self,
        source: SourceContext,
        count: int,
        payload_kind: str,
        url: str | None = None,
        error: str | None = None,
    ):
        if not hasattr(self, "run_history"):
            self.run_history = []
        self.run_history.append(
            {
                "source_id": source.source_id,
                "source_name": source.name,
                "parse_mode": source.parse_mode,
                "query_terms": list(source.query_terms),
                "payload_kind": payload_kind,
                "count": count,
                "url": url,
                "error": error,
            }
        )

    def write_metrics(self, month_str=None):
        month_str = active_month(month_str)
        metrics = {
            "month": month_str,
            "generated_at": datetime.now().isoformat(),
            "total_grants": sum(item.get("count", 0) for item in getattr(self, "run_history", [])),
            "sources": getattr(self, "run_history", []),
        }
        metrics_path = GRANTS_ROOT / "logs" / f"scrape-metrics-{month_str}.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return metrics_path

    def save_grants(self, grants, month_str=None):
        """Validate, deduplicate, and save scraped grants to file."""
        month_str = active_month(month_str)

        errors = validate_grant_collection(grants, stage="raw")
        if errors:
            raise ValueError("Scraped grants failed validation:\n" + "\n".join(errors))

        output_dir = GRANTS_ROOT / "data" / "raw" / month_str
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "grants-raw.json"

        existing = []
        if output_file.exists():
            with output_file.open("r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []

        combined = existing + grants

        deduped = []
        seen = set()
        for grant in combined:
            signature = (
                str(grant.get("name", "")).strip().lower(),
                str(grant.get("funder", "")).strip().lower(),
                str(grant.get("deadline", "")).strip(),
            )
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(grant)

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(deduped, f, indent=2)

        logger.info("Saved %s grants to %s", len(grants), output_file)
        return len(grants)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape grant databases")
    parser.add_argument(
        "--sources", nargs="*", help="Source ids or types to scrape; defaults to all enabled sources"
    )
    parser.add_argument("--save", action="store_true", help="Save to file")
    parser.add_argument("--month", help="Optional month override (YYYY-MM)")
    args = parser.parse_args()

    scraper = GrantScraper()
    grants = scraper.scrape_all(args.sources)
    scraper.write_metrics(args.month)

    if args.save:
        scraper.save_grants(grants, args.month)
    else:
        print(json.dumps(grants, indent=2))

    return len(grants)


if __name__ == "__main__":
    count = main()
    print(f"\nScraped {count} grants")
