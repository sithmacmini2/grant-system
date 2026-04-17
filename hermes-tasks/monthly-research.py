#!/usr/bin/env python3
"""
Layer 5 - Monthly Research Orchestration
Runs complete monthly grant research cycle: Layer 1-4
"""

import json
import os
import sys
import logging
import subprocess
from datetime import datetime

GRANTS_ROOT = "/home/sithmm2_admin/grants-system"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("monthly_research")


def run_command(cmd, description):
    """Run a command and log the result"""
    logger.info(f"Running: {description}")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            logger.info(f"Success: {description}")
            return True
        else:
            logger.error(f"Failed: {description} - {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error running {description}: {e}")
        return False


def run_monthly_research(month_str=None):
    """Execute full monthly research cycle"""
    if month_str is None:
        month_str = datetime.now().strftime("%Y-%m")

    logger.info(f"=== Starting Monthly Research Cycle: {month_str} ===")

    raw_file = f"{GRANTS_ROOT}/data/raw/{month_str}/grants-raw.json"
    if not os.path.exists(raw_file):
        logger.error(f"Raw data not found: {raw_file}")
        logger.info("Generating test data first...")
        run_command(
            f"python3 {GRANTS_ROOT}/hermes-tasks/generate_test_data.py",
            "Generate test data",
        )

    success = True

    logger.info("--- Step 1: Enrich Grants ---")
    if not run_command(
        f"python3 {GRANTS_ROOT}/hermes-tasks/enrich-grants.py {month_str}",
        "Enrich grants",
    ):
        success = False

    logger.info("--- Step 2: Run Cerebro Intelligence ---")
    if not run_command(
        f"python3 {GRANTS_ROOT}/hermes-tasks/cerebro-integration.py {month_str}",
        "Cerebro scan",
    ):
        success = False

    logger.info("--- Step 3: Generate Outputs ---")
    if not run_command(
        f"python3 {GRANTS_ROOT}/hermes-tasks/brief-generator.py {month_str}",
        "Generate briefs",
    ):
        success = False

    if not run_command(
        f"python3 {GRANTS_ROOT}/hermes-tasks/proposal-generator.py {month_str}",
        "Generate proposals",
    ):
        success = False

    if not run_command(
        f"python3 {GRANTS_ROOT}/hermes-tasks/matrix-generator.py {month_str}",
        "Generate matrix",
    ):
        success = False

    if not run_command(
        f"python3 {GRANTS_ROOT}/hermes-tasks/dashboard-generator.py {month_str}",
        "Generate dashboard",
    ):
        success = False

    logger.info("--- Step 4: Sync to Obsidian ---")

    source_briefs = f"{GRANTS_ROOT}/outputs/briefs/{month_str}"
    dest_briefs = f"{GRANTS_ROOT}/../wiki/Grants/2026/02-Grant-Briefs"
    if os.path.exists(source_briefs):
        os.makedirs(dest_briefs, exist_ok=True)
        for f in os.listdir(source_briefs):
            if f.endswith(".md"):
                src = os.path.join(source_briefs, f)
                dst = os.path.join(dest_briefs, f)
                with open(src, "r") as sf:
                    with open(dst, "w") as df:
                        df.write(sf.read())
                logger.info(f"Synced: {f}")

    source_matrix = f"{GRANTS_ROOT}/outputs/matrix/{month_str}-grant-matrix.md"
    dest_matrix = f"{GRANTS_ROOT}/../wiki/Grants/2026/01-Monthly-Landscape.md"
    if os.path.exists(source_matrix):
        with open(source_matrix, "r") as sf:
            with open(dest_matrix, "w") as df:
                df.write(sf.read())
        logger.info("Synced: Monthly-Landscape.md")

    source_tracking = f"{GRANTS_ROOT}/outputs/tracking/{month_str}/active-tracking.md"
    dest_tracking = f"{GRANTS_ROOT}/../wiki/Grants/2026/04-Active-Tracking.md"
    if os.path.exists(source_tracking):
        with open(source_tracking, "r") as sf:
            with open(dest_tracking, "w") as df:
                df.write(sf.read())
        logger.info("Synced: Active-Tracking.md")

    logger.info("=== Monthly Research Complete ===")

    with open(f"{GRANTS_ROOT}/logs/monthly-research.log", "a") as f:
        f.write(
            f"{datetime.now().isoformat()} - Monthly research completed - Success: {success}\n"
        )

    return success


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_monthly_research(month)
    sys.exit(0 if success else 1)
