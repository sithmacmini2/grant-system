#!/usr/bin/env python3
"""
Historical grant outcome aggregation.

This module builds a funder-level outcome index from archived markdown notes and
structured grant JSON files.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from grants_context import grants_path, wiki_path


OUTCOME_DIR_NAMES = {"won": "won", "lost": "lost", "pending": "pending"}


def _iter_archived_markdown_files(root: Path):
    if not root.exists():
        return
    for path in root.rglob("*.md"):
        yield path


def _extract_frontmatter_field(text: str, field_name: str) -> str | None:
    pattern = rf"(?im)^{re.escape(field_name)}:\s*(.+?)\s*$"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip().strip('"').strip("'")
    return None


def _normalize_status(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    if value in {"won", "lost", "pending"}:
        return value
    return None


def _grant_key(grant: dict) -> str:
    grant_id = str(grant.get("grant_id", "")).strip()
    if grant_id:
        return f"id:{grant_id}"
    name = str(grant.get("name", "")).strip().lower()
    funder = str(grant.get("funder", "")).strip().lower()
    deadline = str(grant.get("deadline", "")).strip()
    return f"sig:{name}|{funder}|{deadline}"


def _merge_status(existing: str | None, new: str | None) -> str | None:
    priority = {"won": 3, "lost": 2, "pending": 1, None: 0}
    if priority.get(new, 0) >= priority.get(existing, 0):
        return new
    return existing


def build_funder_outcome_index() -> dict[str, dict[str, int | bool]]:
    """Build a funder-level index of wins/losses/pending outcomes."""
    index: dict[str, dict[str, int | bool]] = defaultdict(
        lambda: {"won": 0, "lost": 0, "pending": 0, "past_success": False, "known_rejections": False}
    )
    seen: dict[str, str] = {}

    # Structured output data: current and historical enriched grant files.
    data_root = grants_path("data", "enriched")
    if data_root.exists():
        for json_file in data_root.glob("*/grants-enriched.json"):
            try:
                grants = json.loads(json_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            for grant in grants if isinstance(grants, list) else []:
                funder = str(grant.get("funder", "")).strip()
                status = _normalize_status(grant.get("status"))
                if not funder or not status:
                    continue
                key = _grant_key(grant)
                seen_status = seen.get(key)
                merged_status = _merge_status(seen_status, status)
                if merged_status == seen_status:
                    continue
                if seen_status:
                    index[funder][seen_status] -= 1
                seen[key] = merged_status or status
                index[funder][seen[key]] += 1

    # Archived markdown notes: use the directory name if available, otherwise try frontmatter.
    wiki_grants_root = wiki_path("Grants")
    if wiki_grants_root.exists():
        for md_file in _iter_archived_markdown_files(wiki_grants_root):
            status = None
            for parent in md_file.parents:
                parent_name = parent.name.lower()
                if parent_name in OUTCOME_DIR_NAMES:
                    status = OUTCOME_DIR_NAMES[parent_name]
                    break

            try:
                content = md_file.read_text(encoding="utf-8")
            except OSError:
                continue

            funder = _extract_frontmatter_field(content, "funder")
            if not funder:
                continue

            if status is None:
                status = _normalize_status(_extract_frontmatter_field(content, "status"))
            if status is None:
                continue

            grant_id = _extract_frontmatter_field(content, "grant_id")
            key = f"id:{grant_id}" if grant_id else f"md:{md_file.as_posix()}"
            seen_status = seen.get(key)
            merged_status = _merge_status(seen_status, status)
            if merged_status == seen_status:
                continue
            if seen_status:
                index[funder][seen_status] -= 1
            seen[key] = merged_status or status
            index[funder][seen[key]] += 1

    archive_ledger = wiki_grants_root.rglob("ledger.json") if wiki_grants_root.exists() else []
    for ledger_path in archive_ledger:
        try:
            ledger_entries = json.loads(ledger_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        for entry in ledger_entries if isinstance(ledger_entries, list) else []:
            funder = str(entry.get("funder", "")).strip()
            status = _normalize_status(entry.get("status"))
            if not funder or not status:
                continue
            grant_id = str(entry.get("grant_id", "")).strip()
            key = f"id:{grant_id}" if grant_id else f"ledger:{funder}|{entry.get('deadline', '')}"
            seen_status = seen.get(key)
            merged_status = _merge_status(seen_status, status)
            if merged_status == seen_status:
                continue
            if seen_status:
                index[funder][seen_status] -= 1
            seen[key] = merged_status or status
            index[funder][seen[key]] += 1

    for funder, stats in index.items():
        stats["past_success"] = stats["won"] > 0
        stats["known_rejections"] = stats["lost"] > 0

    return dict(index)


def annotate_grants_with_outcomes(grants: list[dict]) -> list[dict]:
    """Attach past_success/known_rejections flags from outcome history."""
    if not isinstance(grants, list):
        return grants

    outcome_index = build_funder_outcome_index()
    annotated = []

    for grant in grants:
        if not isinstance(grant, dict):
            annotated.append(grant)
            continue

        funder = str(grant.get("funder", "")).strip()
        stats = outcome_index.get(funder)
        if stats:
            enrichment = grant.setdefault("enrichment", {})
            enrichment["past_success"] = bool(stats.get("past_success"))
            enrichment["known_rejections"] = bool(stats.get("known_rejections"))
        annotated.append(grant)

    return annotated
