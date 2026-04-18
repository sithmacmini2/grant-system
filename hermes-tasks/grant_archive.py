#!/usr/bin/env python3
"""
Archive a grant outcome and persist a small audit trail.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from grants_context import active_month, grants_path, wiki_path


VALID_STATUSES = {"won", "lost", "pending"}


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    return re.sub(r"[\s-]+", "-", value)[:80] or "grant"


def _archive_year(month_str: str) -> str:
    return month_str.split("-", 1)[0]


def _archive_root(month_str: str) -> Path:
    return wiki_path("Grants", _archive_year(month_str), "05-Archive")


def _ledger_path(month_str: str) -> Path:
    return _archive_root(month_str) / "ledger.json"


def _load_ledger(month_str: str) -> list[dict]:
    path = _ledger_path(month_str)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _save_ledger(entries: list[dict], month_str: str) -> Path:
    path = _ledger_path(month_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return path


def archive_grant(grant_id: str, status: str, month_str: str | None = None, note: str | None = None) -> dict:
    status = status.strip().lower()
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid archive status: {status}")

    month_str = active_month(month_str)
    enriched_path = grants_path("data", "enriched", month_str, "grants-enriched.json")
    if not enriched_path.exists():
        raise FileNotFoundError(f"Enriched data not found: {enriched_path}")

    grants = json.loads(enriched_path.read_text(encoding="utf-8"))
    updated_grant = None
    for grant in grants:
        if str(grant.get("grant_id")) == str(grant_id):
            grant["status"] = status
            grant.setdefault("enrichment", {})
            grant["enrichment"]["archived_at"] = datetime.now().isoformat()
            updated_grant = grant
            break

    if updated_grant is None:
        raise LookupError(f"Grant not found: {grant_id}")

    enriched_path.write_text(json.dumps(grants, indent=2), encoding="utf-8")

    archive_dir = _archive_root(month_str) / status.capitalize()
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_note = archive_dir / f"{_slugify(updated_grant.get('name', grant_id))}-{grant_id}.md"

    markdown = f"""---
grant_id: {updated_grant.get("grant_id")}
name: {updated_grant.get("name")}
funder: {updated_grant.get("funder")}
deadline: {updated_grant.get("deadline")}
status: {status}
archived_at: {datetime.now().isoformat()}
---

# {updated_grant.get("name")}

- Status: {status}
- Funder: {updated_grant.get("funder")}
- Deadline: {updated_grant.get("deadline")}
- Amount: {updated_grant.get("amount")}
"""
    if note:
        markdown += f"\n## Note\n\n{note.strip()}\n"
    archive_note.write_text(markdown, encoding="utf-8")

    ledger = _load_ledger(month_str)
    ledger = [entry for entry in ledger if str(entry.get("grant_id")) != str(grant_id)]
    ledger.append(
        {
            "grant_id": updated_grant.get("grant_id"),
            "name": updated_grant.get("name"),
            "funder": updated_grant.get("funder"),
            "deadline": updated_grant.get("deadline"),
            "status": status,
            "archived_at": datetime.now().isoformat(),
            "month": month_str,
            "note": note or "",
        }
    )
    ledger_path = _save_ledger(ledger, month_str)

    return {
        "grant": updated_grant,
        "archive_note": str(archive_note),
        "ledger_path": str(ledger_path),
    }
