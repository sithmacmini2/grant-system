#!/usr/bin/env python3
"""
Layer 2: Enrichment Pipeline
Normalizes raw grant data and enriches with LLM Wiki data, eligibility extraction,
and deadline calculations.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import logging
import yaml

GRANTS_ROOT = "/home/sithmm2_admin/grants-system"
WIKI_ROOT = "/home/sithmm2_admin/wiki"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("enrich_grants")

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


def fuzzy_match(text1, text2, threshold=0.85):
    """Fuzzy string matching for funder names"""
    ratio = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    return ratio >= threshold


def load_llm_wiki_funders():
    """Load funder profiles from LLM Wiki"""
    funder_dir = f"{WIKI_ROOT}/funders"
    funders = {}

    if not os.path.exists(funder_dir):
        logger.warning(f"Funder directory not found: {funder_dir}")
        return funders

    for filename in os.listdir(funder_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(funder_dir, filename)
            try:
                with open(filepath, "r") as f:
                    content = f.read()
                    funder_name = filename[:-3]
                    funders[funder_name] = {"content": content, "path": filepath}
            except Exception as e:
                logger.error(f"Error reading {filename}: {e}")

    return funders


def calculate_days_remaining(deadline_str):
    """Calculate days remaining until deadline"""
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
        today = datetime.now()
        delta = (deadline - today).days
        return max(0, delta)
    except:
        return 0


def get_urgency_level(days_remaining):
    """Determine urgency level based on days remaining"""
    if days_remaining <= 14:
        return "HIGH"
    elif days_remaining <= 30:
        return "MEDIUM"
    return "LOW"


def extract_eligibility(criteria_text):
    """Extract structured eligibility from criteria text"""
    eligibility = {
        "org_type": [],
        "geography": [],
        "budget_size": None,
        "focus_areas": [],
    }

    criteria_lower = criteria_text.lower()

    if "501(c)(3)" in criteria_lower or "nonprofit" in criteria_lower:
        eligibility["org_type"].append("501(c)(3)")
    if "government" in criteria_lower or "municipal" in criteria_lower:
        eligibility["org_type"].append("Government")

    if "rhode island" in criteria_lower or "ri" in criteria_lower:
        eligibility["geography"].append("Rhode Island")
    if "new england" in criteria_lower:
        eligibility["geography"].append("New England")
    if "national" in criteria_lower:
        eligibility["geography"].append("National")

    for focus in FOCUS_AREAS:
        if focus.lower() in criteria_lower:
            eligibility["focus_areas"].append(focus)

    return eligibility


def enrich_grant(grant, wiki_funders):
    """Enrich a single grant with additional data"""
    enriched = grant.copy()

    days_remaining = calculate_days_remaining(grant.get("deadline", ""))
    enriched["enrichment"] = {
        "eligibility": extract_eligibility(grant.get("criteria", "")),
        "days_remaining": days_remaining,
        "urgency_level": get_urgency_level(days_remaining),
        "known_rejections": False,
        "past_success": False,
        "funder_profile": None,
    }

    matched_funder = None
    for funder_name in wiki_funders.keys():
        if fuzzy_match(grant.get("funder", ""), funder_name):
            matched_funder = funder_name
            break

    if matched_funder:
        enriched["enrichment"]["funder_profile"] = {
            "name": matched_funder,
            "matched_from": wiki_funders[matched_funder]["path"],
        }
        logger.info(f"Matched funder: {matched_funder}")

    return enriched


def deduplicate_grants(grants):
    """Remove duplicate grants using fuzzy matching"""
    seen = []
    unique = []

    for grant in grants:
        is_duplicate = False
        for existing in seen:
            name_match = fuzzy_match(
                grant.get("name", ""), existing.get("name", ""), 0.85
            )
            funder_match = fuzzy_match(
                grant.get("funder", ""), existing.get("funder", ""), 0.85
            )
            amount_close = (
                abs(grant.get("amount", 0) - existing.get("amount", 0)) <= 5000
            )

            if name_match and funder_match and amount_close:
                is_duplicate = True
                break

        if not is_duplicate:
            seen.append(grant)
            unique.append(grant)

    logger.info(f"Deduplication: {len(grants)} -> {len(unique)} grants")
    return unique


def process_raw_grants(month_str=None):
    """Process raw grants and create enriched version"""
    if month_str is None:
        month_str = datetime.now().strftime("%Y-%m")

    raw_file = f"{GRANTS_ROOT}/data/raw/{month_str}/grants-raw.json"

    if not os.path.exists(raw_file):
        logger.error(f"Raw data file not found: {raw_file}")
        return False

    with open(raw_file, "r") as f:
        grants = json.load(f)

    logger.info(f"Processing {len(grants)} grants from {raw_file}")

    wiki_funders = load_llm_wiki_funders()

    grants = deduplicate_grants(grants)

    enriched_grants = []
    for grant in grants:
        enriched = enrich_grant(grant, wiki_funders)
        enriched_grants.append(enriched)

    enriched_dir = f"{GRANTS_ROOT}/data/enriched/{month_str}"
    os.makedirs(enriched_dir, exist_ok=True)

    output_file = f"{enriched_dir}/grants-enriched.json"
    with open(output_file, "w") as f:
        json.dump(enriched_grants, f, indent=2)

    logger.info(f"Enriched grants saved to {output_file}")
    return True


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else None
    success = process_raw_grants(month)
    sys.exit(0 if success else 1)
