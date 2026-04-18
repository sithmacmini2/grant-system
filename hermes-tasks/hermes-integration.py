#!/usr/bin/env python3
"""
Hermes Grant Integration - Connect Hermes Agent with Grant System
This script allows Hermes to query grant data and run research.
"""

import json
import os
import sys
import subprocess
from datetime import datetime

from grants_context import active_month, grants_path

GRANTS_ROOT = grants_path()


def get_status():
    """Get system status for Hermes"""
    month_str = active_month()
    data = {
        "system": "Grant Intelligence Workflow",
        "location": str(GRANTS_ROOT),
        "status": "active",
        "last_run": datetime.now().isoformat(),
        "grants_count": 0,
        "high_priority": 0,
        "urgent": 0,
    }

    grants_file = GRANTS_ROOT / "data" / "enriched" / month_str / "grants-enriched.json"
    if grants_file.exists():
        with open(grants_file, encoding="utf-8") as f:
            grants = json.load(f)
            data["grants_count"] = len(grants)
            data["high_priority"] = len(
                [
                    g
                    for g in grants
                    if g.get("intelligence", {}).get("fit_score", 0) >= 7
                ]
            )
            data["urgent"] = len(
                [
                    g
                    for g in grants
                    if g.get("enrichment", {}).get("urgency_level") == "HIGH"
                ]
            )

    return data


def search_grants(query):
    """Search grants by keyword"""
    grants_file = GRANTS_ROOT / "data" / "enriched" / active_month() / "grants-enriched.json"
    results = []

    if grants_file.exists():
        with open(grants_file, encoding="utf-8") as f:
            grants = json.load(f)
            query_lower = query.lower()
            for g in grants:
                searchable = f"{g.get('name', '')} {g.get('funder', '')} {g.get('criteria', '')}".lower()
                if query_lower in searchable:
                    results.append(
                        {
                            "name": g.get("name"),
                            "funder": g.get("funder"),
                            "amount": g.get("amount"),
                            "fit_score": g.get("intelligence", {}).get("fit_score"),
                            "recommendation": g.get("intelligence", {}).get(
                                "recommendation"
                            ),
                        }
                    )

    return results


def get_urgent_grants():
    """Get grants due within 14 days"""
    grants_file = GRANTS_ROOT / "data" / "enriched" / active_month() / "grants-enriched.json"
    urgent = []

    if grants_file.exists():
        with open(grants_file, encoding="utf-8") as f:
            grants = json.load(f)
            for g in grants:
                if g.get("enrichment", {}).get("urgency_level") == "HIGH":
                    urgent.append(
                        {
                            "name": g.get("name"),
                            "days_remaining": g.get("enrichment", {}).get(
                                "days_remaining"
                            ),
                            "deadline": g.get("deadline"),
                            "fit_score": g.get("intelligence", {}).get("fit_score"),
                        }
                    )

    return sorted(urgent, key=lambda x: x["days_remaining"])


def run_monthly_research():
    """Trigger full research cycle"""
    log_path = GRANTS_ROOT / "logs" / "hermes-trigger.log"
    with log_path.open("w", encoding="utf-8") as log_file:
        result = subprocess.run(
            [sys.executable, str(GRANTS_ROOT / "run-all.py")],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return result.returncode == 0


def get_proposals():
    """Get generated proposal drafts"""
    proposals = []
    dir_path = GRANTS_ROOT / "outputs" / "proposals" / active_month()

    if dir_path.exists():
        for f in os.listdir(dir_path):
            if f.endswith("-draft.md"):
                proposals.append(f)

    return proposals


GRANT_COMMANDS = {
    "status": get_status,
    "urgent": get_urgent_grants,
    "search": lambda q: search_grants(q or "youth"),
    "proposals": get_proposals,
    "run": run_monthly_research,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    arg = sys.argv[2] if len(sys.argv) > 2 else None

    if cmd in GRANT_COMMANDS:
        result = GRANT_COMMANDS[cmd](arg)
        print(json.dumps(result, indent=2))
    else:
        print(f"Available commands: {list(GRANT_COMMANDS.keys())}")
