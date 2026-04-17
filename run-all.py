#!/usr/bin/env python3
"""
Grant Intelligence System - All-in-One Runner
Run the complete grant research cycle with one command.
"""

import sys
import os

GRANTS_ROOT = "/home/sithmm2_admin/grants-system"


def run_step(cmd, description):
    print(f"\n{'=' * 50}")
    print(f"STEP: {description}")
    print("=" * 50)
    result = os.system(cmd)
    if result != 0:
        print(f"⚠️ Warning: {description} returned code {result}")
    return result


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║     GRANT INTELLIGENCE SYSTEM - FULL CYCLE RUNNER          ║
╚═══════════════════════════════════════════════════════════╝
    """)

    print("Starting complete grant research cycle...")

    # Step 1: Scrape new grants
    run_step(
        f"python3 {GRANTS_ROOT}/hermes-tasks/scraper.py --save",
        "Scraping grant databases",
    )

    # Step 2: Run monthly research (enrichment, intelligence, outputs)
    run_step(
        f"python3 {GRANTS_ROOT}/hermes-tasks/monthly-research.py",
        "Running full research pipeline",
    )

    print("""
╔═══════════════════════════════════════════════════════════╗
║                    ✓ CYCLE COMPLETE                        ║
╚═══════════════════════════════════════════════════════════╝

Results available in:
  📊 /home/sithmm2_admin/wiki/Grants/2026/01-Monthly-Landscape.md
  📋 /home/sithmm2_admin/wiki/Grants/2026/02-Grant-Briefs/
  📈 /home/sithmm2_admin/wiki/Grants/2026/04-Active-Tracking.md
  📄 /home/sithmm2_admin/grants-system/outputs/matrix/
  📝 /home/sithmm2_admin/grants-system/outputs/proposals/

Run 'python3 telegram-bot.py poll' to enable Telegram commands.
    """)

    return 0


if __name__ == "__main__":
    sys.exit(main())
