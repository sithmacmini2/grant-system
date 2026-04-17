#!/usr/bin/env python3
"""
Layer 5 - Weekly Deadline Check
Checks for grants with deadlines approaching and sends alerts.
"""

import json
import os
import sys
import logging
from datetime import datetime

GRANTS_ROOT = "/home/sithmm2_admin/grants-system"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("weekly_deadline_check")


def check_deadlines(month_str=None):
    """Check for upcoming deadlines and generate alert"""
    if month_str is None:
        month_str = datetime.now().strftime("%Y-%m")

    tracking_file = f"{GRANTS_ROOT}/outputs/tracking/{month_str}/active-tracking.md"

    if not os.path.exists(tracking_file):
        logger.warning(f"No tracking file found for {month_str}")
        return False

    with open(tracking_file, "r") as f:
        content = f.read()

    urgent_grants = []
    lines = content.split("\n")
    in_alerts = False

    for line in lines:
        if "## Deadline Alerts" in line:
            in_alerts = True
            continue
        if in_alerts and line.startswith("- **"):
            urgent_grants.append(line)

    logger.info(f"Found {len(urgent_grants)} urgent grants")

    alert_msg = f"📅 *Weekly Deadline Alert*\n\n"

    if urgent_grants:
        alert_msg += f"*{len(urgent_grants)} grants due in 2 weeks:*\n\n"
        for g in urgent_grants[:5]:
            alert_msg += f"{g}\n"
        if len(urgent_grants) > 5:
            alert_msg += f"\n*+{len(urgent_grants) - 5} more*\n"
    else:
        alert_msg += "No urgent deadlines this week. ✅"

    alert_msg += f"\n\n📊 Review at: /wiki/Grants/2026/04-Active-Tracking.md"

    logger.info(f"Alert message ready: {alert_msg[:100]}...")

    with open(f"{GRANTS_ROOT}/logs/weekly-alerts.log", "a") as f:
        f.write(
            f"{datetime.now().isoformat()} - Checked deadlines - Found {len(urgent_grants)} urgent\n"
        )

    print(alert_msg)
    return True


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else None
    success = check_deadlines(month)
    sys.exit(0 if success else 1)
