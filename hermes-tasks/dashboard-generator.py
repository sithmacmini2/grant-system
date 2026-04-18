#!/usr/bin/env python3
"""
Layer 4 - Output Generator 4: Tracking Dashboard
Generates persistent tracking dashboard with active grants, deadlines, and metrics.
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
logger = logging.getLogger("dashboard_generator")


def generate_dashboard(month_str=None):
    """Generate tracking dashboard"""
    month_str = active_month(month_str)

    enriched_file = GRANTS_ROOT / "data" / "enriched" / month_str / "grants-enriched.json"

    if not enriched_file.exists():
        logger.error(f"Enriched data not found: {enriched_file}")
        return False

    with enriched_file.open("r", encoding="utf-8") as f:
        grants = json.load(f)

    active_grants = sorted(
        [
            g
            for g in grants
            if g.get("status") in ["new", "updated", "active", "pending"]
        ],
        key=lambda g: g.get("enrichment", {}).get("days_remaining", 999),
    )

    urgent_grants = [
        g
        for g in active_grants
        if g.get("enrichment", {}).get("urgency_level") == "HIGH"
    ]

    won_count = len([g for g in grants if g.get("status") == "won"])
    lost_count = len([g for g in grants if g.get("status") == "lost"])
    pending_count = len([g for g in grants if g.get("status") == "pending"])
    total_count = len(grants)

    success_rate = 0
    if won_count + lost_count > 0:
        success_rate = int((won_count / (won_count + lost_count)) * 100)

    patterns = set()
    for g in grants:
        for p in g.get("intelligence", {}).get("pattern_matches", []):
            patterns.add(p)

    dashboard = f"""---
title: Active Tracking Dashboard - {month_str}
generated: {datetime.now().isoformat()}
---

# Grant Tracking Dashboard - {month_str}

*Generated: {datetime.now().strftime("%Y-%m-%d")}*

---

## Active Grants This Month

| Grant | Funder | Amount | Deadline | Days | Fit | Status |
|-------|--------|--------|----------|------|-----|--------|
"""

    for g in active_grants:
        name = g.get("name", "")[:35]
        funder = g.get("funder", "")[:20]
        amount = f"${g.get('amount', 0):,}"
        deadline = g.get("deadline", "TBD")
        days = g.get("enrichment", {}).get("days_remaining", "N/A")
        fit = g.get("intelligence", {}).get("fit_score", "N/A")
        status = g.get("status", "new")

        dashboard += f"| {name} | {funder} | {amount} | {deadline} | {days} | {fit} | {status} |\n"

    dashboard += f"\n**Total Active:** {len(active_grants)}\n\n"

    if urgent_grants:
        dashboard += "## Deadline Alerts ⚠️\n\n"
        dashboard += "*Grants due in less than 14 days requiring action:*\n\n"

        for g in urgent_grants:
            name = g.get("name", "")
            days = g.get("enrichment", {}).get("days_remaining", 0)
            deadline = g.get("deadline", "TBD")
            fit = g.get("intelligence", {}).get("fit_score", 0)
            rec = g.get("intelligence", {}).get("recommendation", "Review")

            dashboard += (
                f"- **{name}** - {days} days ({deadline}) | Fit: {fit}/10 | *{rec}*\n"
            )

        dashboard += "\n"

    dashboard += f"""## Historical Summary

| Metric | Count |
|--------|-------|
| Total Analyzed | {total_count} |
| Won | {won_count} |
| Lost | {lost_count} |
| Pending | {pending_count} |
| **Success Rate** | **{success_rate}%** |

"""

    if patterns:
        dashboard += "## Success Patterns\n\n"
        for p in sorted(patterns):
            dashboard += f"- {p}\n"
        dashboard += "\n"

    next_month = datetime.now().month % 12 + 1
    dashboard += f"""## Next Month Preview

*Preparation needed for upcoming deadlines:*

- Review proposals for fit score >= 7
- Prepare materials for HIGH urgency grants
- Update funder profiles with new intelligence

---

*Dashboard updates monthly with each research cycle*
*Access briefs at: /outputs/briefs/{month_str}/*
*Access matrix at: /outputs/matrix/{month_str}/*
"""

    tracking_dir = GRANTS_ROOT / "outputs" / "tracking" / month_str
    tracking_dir.mkdir(parents=True, exist_ok=True)

    output_file = tracking_dir / "active-tracking.md"
    with output_file.open("w", encoding="utf-8") as f:
        f.write(dashboard)

    logger.info(f"Tracking dashboard saved to {output_file}")
    return True


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else None
    success = generate_dashboard(month)
    sys.exit(0 if success else 1)
