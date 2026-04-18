#!/usr/bin/env python3
"""
Layer 4 - Output Generator 1: Grant Briefs
Generates markdown grant briefs for each enriched grant.
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
logger = logging.getLogger("brief_generator")


def slugify(text):
    """Convert text to URL-friendly slug"""
    import re

    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text[:50]


def generate_brief(grant, month_str):
    """Generate a single grant brief in markdown"""
    intel = grant.get("intelligence", {})
    enrichment = grant.get("enrichment", {})

    amount = grant.get("amount", 0)
    amount_str = f"${amount:,}" if amount else "See details"

    days_remaining = enrichment.get("days_remaining", "N/A")
    urgency = enrichment.get("urgency_level", "UNKNOWN")

    requirements = []
    eligibility = enrichment.get("eligibility", {})
    if eligibility.get("org_type"):
        requirements.extend(eligibility["org_type"])
    if eligibility.get("geography"):
        requirements.extend(eligibility["geography"])
    if eligibility.get("focus_areas"):
        requirements.extend(eligibility["focus_areas"][:2])

    patterns = intel.get("pattern_matches", [])
    pattern_text = ", ".join(patterns) if patterns else "No historical patterns"

    history_note = "No prior history with this funder"
    if enrichment.get("past_success"):
        history_note = "Previous grants received from this funder"
    elif enrichment.get("known_rejections"):
        history_note = "Past applications were not funded"

    brief = f"""---
grant_id: {grant.get("grant_id")}
funder: {grant.get("funder")}
amount: {amount}
deadline: {grant.get("deadline")}
fit_score: {intel.get("fit_score", "N/A")}
status: {grant.get("status", "new")}
generated: {datetime.now().isoformat()}
---

# {grant.get("name")}

**Funder:** {grant.get("funder")} | **Amount:** {amount_str} | **Deadline:** {days_remaining} days ({grant.get("deadline")})

**Urgency:** {urgency}

## Fit Score: {intel.get("fit_score", "N/A")}/10

{intel.get("strategic_reasoning", "No strategic reasoning available.")}

## Key Requirements

{chr(10).join(f"- {req}" for req in requirements) if requirements else "- See grant details"}

## Recommended Angle

{intel.get("recommendation", "Track only")}

## Pattern Intel

{pattern_text}

**History:** {history_note}

---
*Generated: {datetime.now().strftime("%Y-%m-%d")} | Updated: {datetime.now().strftime("%Y-%m-%d")} | Status: {grant.get("status", "new")}*
"""
    return brief


def generate_all_briefs(month_str=None):
    """Generate briefs for all grants"""
    month_str = active_month(month_str)

    enriched_file = GRANTS_ROOT / "data" / "enriched" / month_str / "grants-enriched.json"

    if not enriched_file.exists():
        logger.error(f"Enriched data not found: {enriched_file}")
        return False

    with enriched_file.open("r", encoding="utf-8") as f:
        grants = json.load(f)

    briefs_dir = GRANTS_ROOT / "outputs" / "briefs" / month_str
    briefs_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Generating {len(grants)} grant briefs")

    for grant in grants:
        brief = generate_brief(grant, month_str)
        slug = slugify(grant.get("name", "grant"))
        filename = briefs_dir / f"{slug}-brief.md"

        with filename.open("w", encoding="utf-8") as f:
            f.write(brief)

        logger.info(f"Generated brief: {filename}")

    logger.info(f"All briefs generated in {briefs_dir}")
    return True


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else None
    success = generate_all_briefs(month)
    sys.exit(0 if success else 1)
