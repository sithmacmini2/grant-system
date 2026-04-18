#!/usr/bin/env python3
"""
Layer 4 - Output Generator 2: Proposal Drafts
Generates proposal draft templates for high-fit grants.
"""

import json
import os
import sys
import logging
from datetime import datetime

from grants_context import active_month, grants_path, wiki_path

GRANTS_ROOT = grants_path()
WIKI_ROOT = wiki_path()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("proposal_generator")


def slugify(text):
    import re

    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text[:50]


def generate_proposal(grant, month_str):
    """Generate a proposal draft for a grant"""
    intel = grant.get("intelligence", {})
    enrichment = grant.get("enrichment", {})
    archive_year = month_str.split("-", 1)[0]

    amount = grant.get("amount", 0)
    amount_str = f"${amount:,}" if amount else "TBD"

    fit_score = intel.get("fit_score", 0)

    if fit_score < 6:
        status = "needs review"
    else:
        status = "template ready"

    org_mission = "The MUSE Foundation of Rhode Island is a Providence, Rhode Island-based 501(c)(3) nonprofit focused on creating opportunities that cultivate creativity and innovation in communities of color through philanthropic investment and community initiatives."

    proposal = f"""---
grant_id: {grant.get("grant_id")}
funder: {grant.get("funder")}
amount: {amount}
status: {status}
generated: {datetime.now().isoformat()}
---

# {grant.get("name")} - Proposal Draft

**Funder:** {grant.get("funder")}  
**Amount:** {amount_str}  
**Deadline:** {grant.get("deadline")}  
**Fit Score:** {fit_score}/10

---

## Executive Summary

*INLINE NOTE: Custom data required. Reference: /wiki/Org-Programs/[relevant-program].md*

[Organization mission alignment with funder priority - draft template]

{org_mission}

This project aligns with {grant.get("funder")}'s focus on [FUNDER FOCUS AREA] by [HOW MUSE'S WORK CONNECTSS].

---

## Problem Statement

*INLINE NOTE: This section requires custom data. Reference: /wiki/entities/[relevant-entity].md for data-backed insights*

### Current Challenge

[Describe the specific problem this grant addresses]

### Data & Evidence

[Include statistics, community needs assessments, or program data]

### Why This Matters

[Connect to MUSE's mission of "Enrich. Empower. Equip."]

---

## Proposed Solution/Approach

*INLINE NOTE: Structure from past successful proposals in /wiki/Grants/{archive_year}/05-Archive/Won/*

### Program Design

[Detailed approach to address the problem]

### Innovation & Best Practices

[What makes this approach unique]

### Key Activities

1. [Activity 1]
2. [Activity 2]
3. [Activity 3]

---

## Evaluation & Metrics

*INLINE NOTE: Reference /wiki/concepts/grant-strategy.md for metrics framework*

### Outcomes

- **Primary Outcome:** [Measurable outcome]
- **Secondary Outcome:** [Additional impact]

### Indicators

| Indicator | Baseline | Target | Timeline |
|-----------|----------|--------|----------|
| [Metric 1] | [Value] | [Value] | [When] |
| [Metric 2] | [Value] | [Value] | [When] |

---

## Timeline

*INLINE NOTE: Adjust based on grant period*

| Phase | Activities | Months |
|-------|------------|--------|
| Planning | [ ] | Months 1-2 |
| Implementation | [ ] | Months 3-8 |
| Evaluation | [ ] | Months 9-12 |
| Reporting | [ ] | Months 10-12 |

---

## Budget Summary

*INLINE NOTE: Reference /wiki/templates/budget-template.md*

| Category | Amount | Notes |
|----------|--------|-------|
| Personnel | $[Amount] | [Details] |
| Programs | $[Amount] | [Details] |
| Operations | $[Amount] | [Details] |
| Evaluation | $[Amount] | [Details] |
| **Total** | **${amount}** | |

---

## Organizational Capacity

*INLINE NOTE: Pull from /wiki/entities/[org-profile].md*

### Staff & Leadership

[Key staff qualifications]

### Past Successes

[Relevant past grant outcomes]

### Partnerships

[Key collaborative relationships]

---

## Supporting Documents

- [ ] Letters of support
- [ ] Budget detail
- [ ] Organizational documents
- [ ] Timeline detail
- [ ] Evaluation plan

---

*Generated: {datetime.now().strftime("%Y-%m-%d")} | Status: {status}*

**INLINE NOTES:**
- Sections marked with "INLINE NOTE" require custom data before submission
- Reference Obsidian vault at /wiki/ for organizational data
- Past successful proposals in /wiki/Grants/{archive_year}/05-Archive/Won/ for templates
"""
    return proposal


def generate_proposals(month_str=None):
    """Generate proposals for high-fit grants"""
    month_str = active_month(month_str)

    enriched_file = GRANTS_ROOT / "data" / "enriched" / month_str / "grants-enriched.json"

    if not enriched_file.exists():
        logger.error(f"Enriched data not found: {enriched_file}")
        return False

    with enriched_file.open("r", encoding="utf-8") as f:
        grants = json.load(f)

    proposals_dir = GRANTS_ROOT / "outputs" / "proposals" / month_str
    proposals_dir.mkdir(parents=True, exist_ok=True)

    generated = 0
    for grant in grants:
        intel = grant.get("intelligence", {})
        fit_score = intel.get("fit_score", 0)

        if fit_score >= 6:
            proposal = generate_proposal(grant, month_str)
            slug = slugify(grant.get("name", "grant"))
            filename = proposals_dir / f"{slug}-draft.md"

            with filename.open("w", encoding="utf-8") as f:
                f.write(proposal)

            logger.info(f"Generated proposal: {filename}")
            generated += 1

    logger.info(f"Generated {generated} proposal drafts in {proposals_dir}")
    return True


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else None
    success = generate_proposals(month)
    sys.exit(0 if success else 1)
