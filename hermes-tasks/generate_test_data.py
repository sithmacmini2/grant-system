import json
import os
import sys
from datetime import datetime, timedelta
import random

from grants_context import grants_path
from grants_context import active_month
from pipeline_validation import validate_grant_collection

GRANTS_SYSTEM_ROOT = grants_path()
TEST_GRANTS = [
    {
        "name": "Youth Leadership Development Grant",
        "funder": "Rhode Island Foundation",
        "amount": 50000,
        "focus": "youth leadership",
        "deadline_days": 30,
    },
    {
        "name": "Community Arts Programming Initiative",
        "funder": "National Endowment for the Arts",
        "amount": 75000,
        "focus": "cultural programming",
        "deadline_days": 45,
    },
    {
        "name": "Black Community Economic Empowerment",
        "funder": "Robert Wood Johnson Foundation",
        "amount": 100000,
        "focus": "community development",
        "deadline_days": 60,
    },
    {
        "name": "Philanthropy Education Program",
        "funder": "Kellogg Foundation",
        "amount": 250000,
        "focus": "philanthropy education",
        "deadline_days": 90,
    },
    {
        "name": "Youth Summer Employment Program",
        "funder": "Department of Labor",
        "amount": 150000,
        "focus": "youth employment",
        "deadline_days": 14,
    },
    {
        "name": "Cultural Heritage Preservation",
        "funder": "National Humanities Center",
        "amount": 35000,
        "focus": "cultural programming",
        "deadline_days": 21,
    },
    {
        "name": "Community Capacity Building",
        "funder": "Ford Foundation",
        "amount": 80000,
        "focus": "community development",
        "deadline_days": 55,
    },
    {
        "name": "Youth Entrepreneurship Fund",
        "funder": "Ewing Marion Kauffman Foundation",
        "amount": 45000,
        "focus": "youth leadership",
        "deadline_days": 40,
    },
    {
        "name": "Social Equity Research Initiative",
        "funder": "Urban Institute",
        "amount": 60000,
        "focus": "social equity",
        "deadline_days": 35,
    },
    {
        "name": "Juneteenth Celebration Grant",
        "funder": "Rhode Island Council on the Arts",
        "amount": 15000,
        "focus": "cultural programming",
        "deadline_days": 7,
    },
    {
        "name": "Nonprofit Capacity Enhancement",
        "funder": "Pacific Foundation",
        "amount": 40000,
        "focus": "community development",
        "deadline_days": 50,
    },
    {
        "name": "Youth Policy Advocacy Training",
        "funder": "Annie E. Casey Foundation",
        "amount": 65000,
        "focus": "youth leadership",
        "deadline_days": 25,
    },
    {
        "name": "Community Mural Project",
        "funder": "National Trust for Historic Preservation",
        "amount": 20000,
        "focus": "cultural programming",
        "deadline_days": 18,
    },
    {
        "name": "Black Philanthropy Month Endowment",
        "funder": "Vermont Community Foundation",
        "amount": 30000,
        "focus": "philanthropy education",
        "deadline_days": 65,
    },
    {
        "name": "Digital Literacy for Youth",
        "funder": "Google.org",
        "amount": 125000,
        "focus": "youth leadership",
        "deadline_days": 80,
    },
    {
        "name": "Workforce Development Initiative",
        "funder": "JPMorgan Chase Foundation",
        "amount": 200000,
        "focus": "community development",
        "deadline_days": 120,
    },
    {
        "name": "Youth Creative Writing Workshop",
        "funder": "National Book Foundation",
        "amount": 10000,
        "focus": "youth leadership",
        "deadline_days": 10,
    },
    {
        "name": "Community Health Partnership",
        "funder": "Blue Cross Blue Shield of RI",
        "amount": 55000,
        "focus": "community development",
        "deadline_days": 28,
    },
    {
        "name": "Black History Education Program",
        "funder": "National Endowment for the Humanities",
        "amount": 30000,
        "focus": "philanthropy education",
        "deadline_days": 22,
    },
    {
        "name": "Youth Sports Recreation Program",
        "funder": "Nike Foundation",
        "amount": 35000,
        "focus": "youth leadership",
        "deadline_days": 15,
    },
    {
        "name": "Community Investment Fund",
        "funder": "Local Initiatives Support Corporation",
        "amount": 150000,
        "focus": "community development",
        "deadline_days": 70,
    },
    {
        "name": "Micro-Grant Program for Small Nonprofits",
        "funder": "Funder for Change",
        "amount": 10000,
        "focus": "community development",
        "deadline_days": 5,
    },
    {
        "name": "Leadership Development Institute",
        "funder": "Kellogg Foundation",
        "amount": 90000,
        "focus": "youth leadership",
        "deadline_days": 75,
    },
    {
        "name": "Community Economic Research",
        "funder": "Brookings Institution",
        "amount": 45000,
        "focus": "social equity",
        "deadline_days": 42,
    },
    {
        "name": "Youth Radio Production Training",
        "funder": "Corporation for Public Broadcasting",
        "amount": 25000,
        "focus": "youth leadership",
        "deadline_days": 33,
    },
]


def generate_grants_json(month_str=None):
    """Generate synthetic test grants JSON file"""
    month_str = active_month(month_str)
    year = month_str.split("-", 1)[0]
    grants = []
    base_date = datetime.now()

    for i, g in enumerate(TEST_GRANTS):
        deadline = base_date + timedelta(days=g["deadline_days"])

        grant = {
            "grant_id": f"GRANT-{year}-{i + 1:03d}",
            "name": g["name"],
            "funder": g["funder"],
            "deadline": deadline.strftime("%Y-%m-%d"),
            "amount": g["amount"],
            "amount_min": g["amount"] * 0.7,
            "amount_max": g["amount"] * 1.3,
            "criteria": f"501(c)(3) nonprofits focused on {g['focus']}. Youth programming experience required.",
            "url": f"https://example.gov/grants/{year}-{i + 1}",
            "source_db": random.choice(
                ["grants-gov", "foundation-center", "ri-grants"]
            ),
            "scraped_date": base_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "new",
        }
        grants.append(grant)

    errors = validate_grant_collection(grants, stage="raw")
    if errors:
        raise ValueError("Generated test data failed validation:\n" + "\n".join(errors))

    month_str = active_month(month_str)
    output_dir = GRANTS_SYSTEM_ROOT / "data" / "raw" / month_str
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "grants-raw.json"
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(grants, f, indent=2)

    print(f"Generated {len(grants)} test grants to {output_file}")
    return output_file


if __name__ == "__main__":
    month_arg = sys.argv[1] if len(sys.argv) > 1 else None
    generate_grants_json(month_arg)
