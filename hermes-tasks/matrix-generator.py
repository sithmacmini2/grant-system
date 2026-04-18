#!/usr/bin/env python3
"""
Layer 4 - Output Generator 3: Comparative Matrix
Generates ranked CSV and markdown matrix of all grants.
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
logger = logging.getLogger("matrix_generator")


def generate_matrix(month_str=None):
    """Generate comparative matrix for grants"""
    month_str = active_month(month_str)

    enriched_file = GRANTS_ROOT / "data" / "enriched" / month_str / "grants-enriched.json"

    if not enriched_file.exists():
        logger.error(f"Enriched data not found: {enriched_file}")
        return False

    with enriched_file.open("r", encoding="utf-8") as f:
        grants = json.load(f)

    grants_sorted = sorted(
        grants,
        key=lambda g: g.get("intelligence", {}).get("fit_score", 0),
        reverse=True,
    )

    for rank, g in enumerate(grants_sorted, 1):
        g["rank"] = rank

    matrix_dir = GRANTS_ROOT / "outputs" / "matrix" / month_str
    matrix_dir.mkdir(parents=True, exist_ok=True)

    csv_content = "rank,grant_name,funder,amount_k,deadline_days,fit_score,effort_level,status,link\n"

    for grant in grants_sorted:
        name = grant.get("name", "")[:40]
        funder = grant.get("funder", "")[:30]
        amount_k = int(grant.get("amount", 0) / 1000)
        days = grant.get("enrichment", {}).get("days_remaining", 0)
        fit = grant.get("intelligence", {}).get("fit_score", 0)

        if fit >= 8:
            effort = "HIGH"
        elif fit >= 6:
            effort = "MEDIUM"
        else:
            effort = "LOW"

        status = grant.get("status", "new")
        link = grant.get("url", "")

        csv_content += (
            f"{rank},{name},{funder},{amount_k},{days},{fit},{effort},{status},{link}\n"
        )

    csv_file = matrix_dir / f"{month_str}-grant-matrix.csv"
    with csv_file.open("w", encoding="utf-8") as f:
        f.write(csv_content)

    logger.info(f"CSV matrix saved to {csv_file}")

    md_content = f"# Grant Comparative Matrix - {month_str}\n\n"
    md_content += f"*Generated: {datetime.now().strftime('%Y-%m-%d')}*\n\n"
    md_content += "| Rank | Grant | Funder | Amount | Days | Fit | Effort | Status |\n"
    md_content += "|------|-------|--------|--------|------|-----|--------|--------|\n"

    for grant in grants_sorted:
        rank = grant.get("rank", "")
        name = grant.get("name", "")[:30]
        funder = grant.get("funder", "")[:20]
        amount_k = int(grant.get("amount", 0) / 1000)
        days = grant.get("enrichment", {}).get("days_remaining", 0)
        fit = grant.get("intelligence", {}).get("fit_score", 0)

        if fit >= 8:
            effort = "HIGH"
        elif fit >= 6:
            effort = "MEDIUM"
        else:
            effort = "LOW"

        status = grant.get("status", "new")

        md_content += f"| {rank} | {name} | {funder} | ${amount_k}k | {days} | {fit} | {effort} | {status} |\n"

    md_file = matrix_dir / f"{month_str}-grant-matrix.md"
    with md_file.open("w", encoding="utf-8") as f:
        f.write(md_content)

    logger.info(f"Markdown matrix saved to {md_file}")

    logger.info(f"Comparative matrix generated for {len(grants)} grants")
    return True


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else None
    success = generate_matrix(month)
    sys.exit(0 if success else 1)
