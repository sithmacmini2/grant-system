#!/usr/bin/env python3
"""
Layer 3: Intelligence Scanning (Cerebro Integration)
Analyzes enriched grants against Obsidian vault patterns to generate fit scores,
strategic reasoning, and recommendations.
"""

import json
import os
import sys
import logging
from datetime import datetime
from difflib import SequenceMatcher

from grants_context import active_month, grants_path, wiki_path
from outcome_tracker import annotate_grants_with_outcomes
from pipeline_validation import validate_grant_collection

GRANTS_ROOT = grants_path()
WIKI_ROOT = wiki_path()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cerebro_integration")

FOCUS_AREAS = [
    "Black and Brown community advancement",
    "Youth leadership",
    "Philanthropy education",
    "Advocacy",
    "Community-led initiatives",
    "Cultural programming",
    "Community development",
    "Education",
    "Social equity",
]

PROGRAMS = [
    "Rhode Island Black Philanthropy Month",
    "Black Policy Month RI",
    "YESpvd! youth programming",
    "Juneteenth advocacy",
    "MSVL Bridge Sunset Concert Series",
    "Best In Black Community Awards",
    "BLKGivin' micro-grants",
]


def load_past_outcomes():
    """Load historical grant outcomes from Obsidian"""
    outcomes = {"won": [], "lost": [], "pending": []}
    month_str = active_month()
    archive_dir = WIKI_ROOT / "Grants" / month_str.split("-", 1)[0] / "05-Archive"

    if not archive_dir.exists():
        return outcomes

    for subdir in ["Won", "Lost"]:
        path = archive_dir / subdir
        if path.exists():
            for f in os.listdir(path):
                if f.endswith(".md"):
                    try:
                        with open(path / f, "r") as file:
                            content = file.read()
                            outcomes["won" if subdir == "Won" else "lost"].append(
                                content
                            )
                    except:
                        pass

    return outcomes


def load_org_programs():
    """Load organization programs from Obsidian"""
    programs = {}
    programs_dir = f"{WIKI_ROOT}/Org-Programs"

    if not os.path.exists(programs_dir):
        return programs

    for f in os.listdir(programs_dir):
        if f.endswith(".md"):
            try:
                with open(os.path.join(programs_dir, f), "r") as file:
                    programs[f[:-3]] = file.read()
            except:
                pass

    return programs


def calculate_fit_score(grant):
    """Calculate fit score based on multiple factors"""
    score = 0
    max_score = 10

    eligibility = grant.get("enrichment", {}).get("eligibility", {})
    focus_areas = eligibility.get("focus_areas", [])

    if focus_areas:
        for focus in focus_areas:
            for org_focus in FOCUS_AREAS:
                if (
                    focus.lower() in org_focus.lower()
                    or org_focus.lower() in focus.lower()
                ):
                    score += 2
                    break

    amount = grant.get("amount", 0)
    if 15000 <= amount <= 250000:
        score += 2

    urgency = grant.get("enrichment", {}).get("urgency_level", "LOW")
    if urgency == "HIGH":
        score += 1
    elif urgency == "MEDIUM":
        score += 0.5

    if grant.get("enrichment", {}).get("past_success"):
        score += 2

    if grant.get("enrichment", {}).get("known_rejections"):
        score -= 1

    return min(max(1, int(score)), 10)


def generate_strategic_reasoning(grant):
    """Generate strategic reasoning for why this grant fits"""
    reasons = []

    eligibility = grant.get("enrichment", {}).get("eligibility", {})
    focus_areas = eligibility.get("focus_areas", [])

    if focus_areas:
        matching = [
            f
            for f in focus_areas
            if any(
                f.lower() in area.lower() or area.lower() in f.lower()
                for area in FOCUS_AREAS
            )
        ]
        if matching:
            reasons.append(f"Aligns with MUSE focus: {', '.join(matching[:2])}")

    amount = grant.get("amount", 0)
    if amount >= 50000:
        reasons.append(f"Significant funding opportunity (${amount:,})")

    funder = grant.get("funder", "")
    for program in PROGRAMS:
        if program.lower() in funder.lower() or funder.lower() in program.lower():
            reasons.append(f"Direct connection to: {program}")

    if not reasons:
        reasons.append("General fit for community development mission")

    return " | ".join(reasons)


def identify_patterns(grant):
    """Identify matching patterns from past successes"""
    patterns = []

    funder = grant.get("funder", "").lower()
    if "foundation" in funder:
        patterns.append("Foundation grant pattern")
    if "government" in funder or "department" in funder:
        patterns.append("Government funding pattern")
    if "youth" in funder or "youth" in grant.get("name", "").lower():
        patterns.append("Youth programming pattern")
    if "cultural" in funder or "arts" in funder:
        patterns.append("Cultural programming pattern")
    if "community" in funder:
        patterns.append("Community development pattern")

    return patterns[:3]


def get_recommendation(fit_score, days_remaining):
    """Determine recommendation based on fit score and timeline"""
    if fit_score >= 8:
        return "Full application"
    elif fit_score >= 6:
        if days_remaining > 30:
            return "Start draft"
        return "Full application"
    elif fit_score >= 4:
        return "Track only"
    return "Skip"


def analyze_grant(grant, past_outcomes, org_programs):
    """Perform full intelligence analysis on a grant"""
    days_remaining = grant.get("enrichment", {}).get("days_remaining", 0)
    fit_score = calculate_fit_score(grant)

    intelligence = {
        "fit_score": fit_score,
        "strategic_reasoning": generate_strategic_reasoning(grant),
        "pattern_matches": identify_patterns(grant),
        "confidence_level": "HIGH"
        if fit_score >= 7
        else "MEDIUM"
        if fit_score >= 4
        else "LOW",
        "recommendation": get_recommendation(fit_score, days_remaining),
    }

    return intelligence


def run_cerebro_scan(month_str=None):
    """Run full Cerebro intelligence scan"""
    month_str = active_month(month_str)

    enriched_file = GRANTS_ROOT / "data" / "enriched" / month_str / "grants-enriched.json"

    if not enriched_file.exists():
        logger.error(f"Enriched data not found: {enriched_file}")
        return False

    with enriched_file.open("r", encoding="utf-8") as f:
        grants = json.load(f)

    logger.info(f"Running Cerebro scan on {len(grants)} grants")

    past_outcomes = load_past_outcomes()
    org_programs = load_org_programs()
    grants = annotate_grants_with_outcomes(grants)

    intelligence_data = {
        "scan_date": datetime.now().isoformat(),
        "grants_scanned": len(grants),
        "patterns_identified": [],
        "funders_clustered": {},
        "gap_analysis": [],
        "grants": [],
    }

    for grant in grants:
        intel = analyze_grant(grant, past_outcomes, org_programs)
        grant["intelligence"] = intel
        intelligence_data["grants"].append(
            {
                "grant_id": grant.get("grant_id"),
                "name": grant.get("name"),
                "fit_score": intel["fit_score"],
                "recommendation": intel["recommendation"],
                "pattern_matches": intel["pattern_matches"],
            }
        )

    patterns = set()
    for g in intelligence_data["grants"]:
        for p in g.get("pattern_matches", []):
            patterns.add(p)
    intelligence_data["patterns_identified"] = list(patterns)

    funders = {}
    for grant in grants:
        f = grant.get("funder", "Unknown")
        if f not in funders:
            funders[f] = {"count": 0, "total_fit": 0}
        funders[f]["count"] += 1
        funders[f]["total_fit"] += grant.get("intelligence", {}).get("fit_score", 0)

    for f in funders:
        funders[f]["avg_fit"] = funders[f]["total_fit"] / funders[f]["count"]
    intelligence_data["funders_clustered"] = funders

    errors = validate_grant_collection(grants, stage="intelligence")
    if errors:
        raise ValueError("Intelligence-enriched grants failed validation:\n" + "\n".join(errors))

    intelligence_dir = GRANTS_ROOT / "data" / "intelligence" / month_str
    intelligence_dir.mkdir(parents=True, exist_ok=True)

    output_file = intelligence_dir / "cerebro-analysis.json"
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(intelligence_data, f, indent=2)

    with enriched_file.open("w", encoding="utf-8") as f:
        json.dump(grants, f, indent=2)

    logger.info(f"Cerebro analysis saved to {output_file}")
    return True


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_cerebro_scan(month)
    sys.exit(0 if success else 1)
