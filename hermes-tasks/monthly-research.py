#!/usr/bin/env python3
"""
Layer 5 - Monthly Research Orchestration
Runs complete monthly grant research cycle: Layer 1-4
"""

import sys
import logging
import subprocess
import json
from datetime import datetime
import shutil

from grants_context import active_month, grants_path, wiki_path

GRANTS_ROOT = grants_path()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("monthly_research")


def run_command(cmd, description):
    """Run a command and capture the result."""
    logger.info(f"Running: {description}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {
            "description": description,
            "cmd": cmd,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "ok": result.returncode == 0,
        }
    except Exception as e:
        logger.error(f"Error running {description}: {e}")
        return {
            "description": description,
            "cmd": cmd,
            "returncode": 1,
            "stdout": "",
            "stderr": str(e),
            "ok": False,
        }


def write_run_summary(month_str, success, stages, reason=None):
    """Persist a single summary artifact for the orchestration run."""
    summary = {
        "month": month_str,
        "success": success,
        "completed_at": datetime.now().isoformat(),
        "failed_stage": reason,
        "stages": stages,
    }
    summary_path = GRANTS_ROOT / "logs" / f"monthly-research-summary-{month_str}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary_path


def run_monthly_research(month_str=None):
    """Execute full monthly research cycle"""
    month_str = active_month(month_str)
    wiki_year = month_str.split("-", 1)[0]

    logger.info(f"=== Starting Monthly Research Cycle: {month_str} ===")
    stages = []

    raw_file = GRANTS_ROOT / "data" / "raw" / month_str / "grants-raw.json"
    if not raw_file.exists():
        logger.error(f"Raw data not found: {raw_file}")
        logger.info("Generating test data first...")
        result = run_command(
            [
                sys.executable,
                str(GRANTS_ROOT / "hermes-tasks" / "generate_test_data.py"),
                month_str,
            ],
            "Generate test data",
        )
        stages.append(result)
        if not result["ok"]:
            summary_path = write_run_summary(
                month_str, False, stages, "Generate test data"
            )
            logger.error(f"Monthly research aborted; summary written to {summary_path}")
            return False
        if not raw_file.exists():
            summary_path = write_run_summary(
                month_str, False, stages, "Generate test data did not create raw data"
            )
            logger.error(f"Monthly research aborted; summary written to {summary_path}")
            return False

    logger.info("--- Step 1: Enrich Grants ---")
    result = run_command(
        [sys.executable, str(GRANTS_ROOT / "hermes-tasks" / "enrich-grants.py"), month_str],
        "Enrich grants",
    )
    stages.append(result)
    if not result["ok"]:
        summary_path = write_run_summary(month_str, False, stages, "Enrich grants")
        logger.error(f"Monthly research aborted; summary written to {summary_path}")
        return False

    logger.info("--- Step 2: Run Cerebro Intelligence ---")
    result = run_command(
        [
            sys.executable,
            str(GRANTS_ROOT / "hermes-tasks" / "cerebro-integration.py"),
            month_str,
        ],
        "Cerebro scan",
    )
    stages.append(result)
    if not result["ok"]:
        summary_path = write_run_summary(month_str, False, stages, "Cerebro scan")
        logger.error(f"Monthly research aborted; summary written to {summary_path}")
        return False

    logger.info("--- Step 3: Generate Outputs ---")
    result = run_command(
        [
            sys.executable,
            str(GRANTS_ROOT / "hermes-tasks" / "brief-generator.py"),
            month_str,
        ],
        "Generate briefs",
    )
    stages.append(result)
    if not result["ok"]:
        summary_path = write_run_summary(month_str, False, stages, "Generate briefs")
        logger.error(f"Monthly research aborted; summary written to {summary_path}")
        return False

    result = run_command(
        [
            sys.executable,
            str(GRANTS_ROOT / "hermes-tasks" / "proposal-generator.py"),
            month_str,
        ],
        "Generate proposals",
    )
    stages.append(result)
    if not result["ok"]:
        summary_path = write_run_summary(month_str, False, stages, "Generate proposals")
        logger.error(f"Monthly research aborted; summary written to {summary_path}")
        return False

    result = run_command(
        [
            sys.executable,
            str(GRANTS_ROOT / "hermes-tasks" / "matrix-generator.py"),
            month_str,
        ],
        "Generate matrix",
    )
    stages.append(result)
    if not result["ok"]:
        summary_path = write_run_summary(month_str, False, stages, "Generate matrix")
        logger.error(f"Monthly research aborted; summary written to {summary_path}")
        return False

    result = run_command(
        [
            sys.executable,
            str(GRANTS_ROOT / "hermes-tasks" / "dashboard-generator.py"),
            month_str,
        ],
        "Generate dashboard",
    )
    stages.append(result)
    if not result["ok"]:
        summary_path = write_run_summary(month_str, False, stages, "Generate dashboard")
        logger.error(f"Monthly research aborted; summary written to {summary_path}")
        return False

    logger.info("--- Step 4: Sync to Obsidian ---")
    published_root = GRANTS_ROOT / "outputs" / "published" / month_str
    published_root.mkdir(parents=True, exist_ok=True)

    source_briefs = GRANTS_ROOT / "outputs" / "briefs" / month_str
    dest_briefs = wiki_path("Grants", wiki_year, "02-Grant-Briefs")
    if source_briefs.exists():
        published_briefs = published_root / "briefs"
        published_briefs.mkdir(parents=True, exist_ok=True)
        dest_briefs.mkdir(parents=True, exist_ok=True)
        for path in source_briefs.glob("*.md"):
            shutil.copy2(path, published_briefs / path.name)
            shutil.copy2(path, dest_briefs / path.name)
            logger.info(f"Synced: {path.name}")

    source_matrix = GRANTS_ROOT / "outputs" / "matrix" / month_str / f"{month_str}-grant-matrix.md"
    dest_matrix = wiki_path("Grants", wiki_year, "01-Monthly-Landscape.md")
    if source_matrix.exists():
        published_matrix = published_root / "matrix"
        published_matrix.mkdir(parents=True, exist_ok=True)
        dest_matrix.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_matrix, published_matrix / source_matrix.name)
        shutil.copy2(source_matrix, dest_matrix)
        logger.info("Synced: Monthly-Landscape.md")

    source_tracking = GRANTS_ROOT / "outputs" / "tracking" / month_str / "active-tracking.md"
    dest_tracking = wiki_path("Grants", wiki_year, "04-Active-Tracking.md")
    if source_tracking.exists():
        published_tracking = published_root / "tracking"
        published_tracking.mkdir(parents=True, exist_ok=True)
        dest_tracking.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_tracking, published_tracking / source_tracking.name)
        shutil.copy2(source_tracking, dest_tracking)
        logger.info("Synced: Active-Tracking.md")

    logger.info("=== Monthly Research Complete ===")

    summary_path = write_run_summary(month_str, True, stages)

    with open(GRANTS_ROOT / "logs" / "monthly-research.log", "a") as f:
        f.write(
            f"{datetime.now().isoformat()} - Monthly research completed - Success: True - Summary: {summary_path}\n"
        )

    return True


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_monthly_research(month)
    sys.exit(0 if success else 1)
