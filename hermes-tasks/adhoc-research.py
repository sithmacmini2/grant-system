#!/usr/bin/env python3
"""
Layer 5 - Ad-hoc Research
Triggers subset research based on keywords via Telegram.
"""

import json
import os
import sys
import logging
from datetime import datetime

from grants_context import active_month, grants_path

GRANTS_ROOT = grants_path()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("adhoc_research")


def run_adhoc_research(keywords, month_str=None):
    """Run research filtered by keywords"""
    month_str = active_month(month_str)

    logger.info(f"Running ad-hoc research for: {keywords}")

    raw_file = GRANTS_ROOT / "data" / "raw" / month_str / "grants-raw.json"

    if not raw_file.exists():
        logger.warning("No raw data found. Run monthly research first.")
        print(f"❌ No grant data available. Run /research first to populate data.")
        return False

    with raw_file.open("r", encoding="utf-8") as f:
        all_grants = json.load(f)

    keywords_lower = keywords.lower()
    filtered = []

    for g in all_grants:
        searchable = (
            f"{g.get('name', '')} {g.get('funder', '')} {g.get('criteria', '')}".lower()
        )
        if keywords_lower in searchable:
            filtered.append(g)

    logger.info(f"Found {len(filtered)} grants matching '{keywords}'")

    if filtered:
        output_dir = GRANTS_ROOT / "outputs" / "adhoc" / month_str
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"grants-{keywords.replace(' ', '-')}.json"

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2)

        results_msg = f"✅ *Research Complete*\n\n"
        results_msg += f"Found **{len(filtered)}** grants matching '{keywords}':\n\n"

        for g in filtered[:5]:
            name = g.get("name", "Untitled")[:40]
            funder = g.get("funder", "Unknown")
            amount = f"${g.get('amount', 0):,}"
            deadline = g.get("deadline", "TBD")

            results_msg += (
                f"📋 *{name}*\n   Funder: {funder} | {amount} | Due: {deadline}\n\n"
            )

        if len(filtered) > 5:
            results_msg += f"*+{len(filtered) - 5} more grants*\n"

        print(results_msg)
    else:
        print(f"❌ No grants found matching '{keywords}'")

    return True


if __name__ == "__main__":
    keywords = sys.argv[1] if len(sys.argv) > 1 else "youth"
    month = sys.argv[2] if len(sys.argv) > 2 else None

    success = run_adhoc_research(keywords, month)
    sys.exit(0 if success else 1)
