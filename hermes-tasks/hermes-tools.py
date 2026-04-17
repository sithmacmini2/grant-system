#!/usr/bin/env python3
"""
Grant System Hermes Tool
Provides Hermes with tools to query grant data
"""

import json
import os

GRANTS_ROOT = "/home/sithmm2_admin/grants-system"


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
    }


def grant_status():
    grants_file = f"{GRANTS_ROOT}/data/enriched/2026-04/grants-enriched.json"
    if not os.path.exists(grants_file):
        return {"error": "No grant data. Run research first."}

    with open(grants_file) as f:
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
    grants_file = f"{GRANTS_ROOT}/data/enriched/2026-04/grants-enriched.json"
    if not os.path.exists(grants_file):
        return {"error": "No grant data"}

    with open(grants_file) as f:
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
    grants_file = f"{GRANTS_ROOT}/data/enriched/2026-04/grants-enriched.json"
    if not os.path.exists(grants_file):
        return {"error": "No grant data"}

    with open(grants_file) as f:
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
    proposals_dir = f"{GRANTS_ROOT}/outputs/proposals/2026-04"
    if not os.path.exists(proposals_dir):
        return {"error": "No proposals generated"}

    return {"proposals": os.listdir(proposals_dir)}


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
    }

    if tool in funcs:
        print(json.dumps(funcs[tool](), indent=2))
