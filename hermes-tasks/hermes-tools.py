#!/usr/bin/env python3
"""
Grant System Hermes Tool
Provides Hermes with tools to query grant data
"""

import json
import os

from grants_context import active_month, grants_path
from grant_archive import archive_grant as _archive_grant

GRANTS_ROOT = grants_path()


def get_tools():
    """Return tools available to Hermes"""
    return {
        "grant_status": {
            "description": "Get current status of grant intelligence system",
            "parameters": {},
            "returns": "JSON with grant counts, urgency levels",
        },
        "grant_search": {
            "description": "Search grants by keyword",
            "parameters": {"query": "string"},
            "returns": "List of matching grants with fit scores",
        },
        "grant_urgent": {
            "description": "Get grants due within 14 days",
            "parameters": {},
            "returns": "List of urgent grants sorted by deadline",
        },
        "grant_proposals": {
            "description": "List generated proposal drafts",
            "parameters": {},
            "returns": "List of proposal files",
        },
        "grant_archive": {
            "description": "Archive a grant outcome and persist an audit trail",
            "parameters": {
                "grant_id": "string",
                "status": "string",
                "note": "string (optional)",
                "month": "string (optional)",
            },
            "returns": "Archived grant metadata and audit file paths",
        },
    }


def grant_status():
    grants_file = GRANTS_ROOT / "data" / "enriched" / active_month() / "grants-enriched.json"
    if not grants_file.exists():
        return {"error": "No grant data. Run research first."}

    with grants_file.open("r", encoding="utf-8") as f:
        grants = json.load(f)

    return {
        "total_grants": len(grants),
        "high_priority": len(
            [g for g in grants if g.get("intelligence", {}).get("fit_score", 0) >= 7]
        ),
        "proposal_ready": len(
            [g for g in grants if g.get("intelligence", {}).get("fit_score", 0) >= 6]
        ),
        "urgent": len(
            [
                g
                for g in grants
                if g.get("enrichment", {}).get("urgency_level") == "HIGH"
            ]
        ),
        "total_funding": sum(g.get("amount", 0) for g in grants),
    }


def grant_search(query):
    grants_file = GRANTS_ROOT / "data" / "enriched" / active_month() / "grants-enriched.json"
    if not grants_file.exists():
        return {"error": "No grant data"}

    with grants_file.open("r", encoding="utf-8") as f:
        grants = json.load(f)

    results = []
    for g in grants:
        if query.lower() in f"{g.get('name', '')} {g.get('funder', '')}".lower():
            results.append(
                {
                    "name": g.get("name"),
                    "funder": g.get("funder"),
                    "amount": g.get("amount"),
                    "fit": g.get("intelligence", {}).get("fit_score"),
                    "rec": g.get("intelligence", {}).get("recommendation"),
                }
            )

    return {"query": query, "results": results}


def grant_urgent():
    grants_file = GRANTS_ROOT / "data" / "enriched" / active_month() / "grants-enriched.json"
    if not grants_file.exists():
        return {"error": "No grant data"}

    with grants_file.open("r", encoding="utf-8") as f:
        grants = json.load(f)

    urgent = []
    for g in grants:
        if g.get("enrichment", {}).get("urgency_level") == "HIGH":
            urgent.append(
                {
                    "name": g.get("name"),
                    "days": g.get("enrichment", {}).get("days_remaining"),
                    "deadline": g.get("deadline"),
                    "fit": g.get("intelligence", {}).get("fit_score"),
                }
            )

    return sorted(urgent, key=lambda x: x["days"])


def grant_proposals():
    proposals_dir = GRANTS_ROOT / "outputs" / "proposals" / active_month()
    if not proposals_dir.exists():
        return {"error": "No proposals generated"}

    return {"proposals": os.listdir(proposals_dir)}


def grant_archive(grant_id, status, note=None, month=None):
    return _archive_grant(grant_id=grant_id, status=status, month_str=month, note=note)


if __name__ == "__main__":
    import sys

    tool = sys.argv[1] if len(sys.argv) > 1 else "grant_status"

    funcs = {
        "grant_status": grant_status,
        "grant_search": lambda: grant_search(
            sys.argv[2] if len(sys.argv) > 2 else "youth"
        ),
        "grant_urgent": grant_urgent,
        "grant_proposals": grant_proposals,
        "grant_archive": lambda: grant_archive(
            sys.argv[2],
            sys.argv[3] if len(sys.argv) > 3 else "won",
            " ".join(sys.argv[4:]) if len(sys.argv) > 4 else None,
        ),
    }

    if tool in funcs:
        print(json.dumps(funcs[tool](), indent=2))
