#!/usr/bin/env python3
"""
Telegram Bot Handler for Grant Intelligence System
Handles all Telegram commands for the grant system.
"""

import json
import os
import sys
import logging
from datetime import datetime
import requests

GRANTS_ROOT = "/home/sithmm2_admin/grants-system"
BOT_TOKEN = "8114463389:AAEQPHmADS7olea-VM-0dIqYEOs2fEeVpzo"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_handlers")


def send_message(chat_id, text, parse_mode="Markdown"):
    """Send message via Telegram bot"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    try:
        r = requests.post(url, json=data, timeout=10)
        return r.json()
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return None


def handle_grants_this_month(chat_id):
    """Handle /grants-this-month command"""
    tracking_file = f"{GRANTS_ROOT}/outputs/tracking/2026-04/active-tracking.md"

    if not os.path.exists(tracking_file):
        send_message(
            chat_id, "❌ No tracking data available. Run monthly research first."
        )
        return

    with open(tracking_file, "r") as f:
        content = f.read()

    send_message(
        chat_id,
        f"📊 *Grant Tracking Dashboard - April 2026*\n\n`/home/sithmm2_admin/grants-system/outputs/tracking/2026-04/active-tracking.md`",
    )


def handle_status(chat_id):
    """Handle /status command"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    raw_file = f"{GRANTS_ROOT}/data/raw/2026-04/grants-raw.json"
    grant_count = 0
    if os.path.exists(raw_file):
        with open(raw_file, "r") as f:
            grant_count = len(json.load(f))

    msg = f"""✅ *Grant Intelligence System Status*

• Last Research: {now}
• Active Grants: {grant_count}
• Next Monthly: May 2, 2026
• Next Weekly: Next Monday 9am

Location: `/home/sithmm2_admin/grants-system/`"""

    send_message(chat_id, msg)


def handle_deadline_alerts(chat_id):
    """Handle /deadline-alerts command"""
    tracking_file = f"{GRANTS_ROOT}/outputs/tracking/2026-04/active-tracking.md"

    if not os.path.exists(tracking_file):
        send_message(chat_id, "❌ No data available.")
        return

    with open(tracking_file, "r") as f:
        content = f.read()

    if "Deadline Alerts" in content:
        send_message(
            chat_id,
            "📅 *Deadline Alerts*\n\nCheck active-tracking.md for urgent grants",
        )
    else:
        send_message(chat_id, "✅ No urgent deadlines this week!")


def handle_rank_by_deadline(chat_id):
    """Handle /rank-by-deadline command"""
    matrix_file = f"{GRANTS_ROOT}/outputs/matrix/2026-04/2026-04-grant-matrix.csv"

    if not os.path.exists(matrix_file):
        send_message(chat_id, "❌ No matrix available.")
        return

    send_message(
        chat_id,
        "📋 *Grants Ranked by Deadline*\n\n`/home/sithmm2_admin/grants-system/outputs/matrix/2026-04/2026-04-grant-matrix.csv`",
    )


def handle_pattern_scan(chat_id):
    """Handle /pattern-scan command"""
    intel_file = f"{GRANTS_ROOT}/data/intelligence/2026-04/cerebro-analysis.json"

    if not os.path.exists(intel_file):
        send_message(chat_id, "❌ Run monthly research first.")
        return

    with open(intel_file, "r") as f:
        data = json.load(f)

    patterns = data.get("patterns_identified", [])
    msg = "🧠 *Pattern Analysis*\n\n"
    msg += "\n".join([f"• {p}" for p in patterns[:5]])

    send_message(chat_id, msg)


def handle_research(chat_id, keywords):
    """Handle /research command"""
    cmd = f"python3 {GRANTS_ROOT}/hermes-tasks/adhoc-research.py '{keywords}'"
    os.system(cmd)

    send_message(
        chat_id,
        f"🔍 Research triggered for: {keywords}\n\nCheck outputs folder for results.",
    )


def handle_grant_brief(chat_id, name):
    """Handle /grant-brief command"""
    slug = name.lower().replace(" ", "-")
    brief_file = f"{GRANTS_ROOT}/outputs/briefs/2026-04/{slug}-brief.md"

    if os.path.exists(brief_file):
        with open(brief_file, "r") as f:
            content = f.read()[:500]
        send_message(chat_id, f"📄 *Brief for: {name}*\n\n{content}...")
    else:
        send_message(chat_id, f"❌ Brief not found for: {name}")


def handle_funder_intel(chat_id, funder):
    """Handle /funder-intel command"""
    send_message(
        chat_id,
        f"🔍 Funder profile for: {funder}\n\nCheck `/home/sithmm2_admin/wiki/Funder-Profiles/` for details.",
    )


def parse_command(update):
    """Parse incoming Telegram command"""
    if "message" not in update:
        return

    msg = update["message"]
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "")

    if not text.startswith("/"):
        return

    parts = text.split(" ", 1)
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else None

    handlers = {
        "/grants-this_month": handle_grants_this_month,
        "/status": handle_status,
        "/deadline-alerts": handle_deadline_alerts,
        "/rank-by-deadline": handle_rank_by_deadline,
        "/pattern-scan": handle_pattern_scan,
        "/research": lambda cid: (
            handle_research(cid, arg)
            if arg
            else send_message(cid, "Usage: /research [keywords]")
        ),
        "/grant-brief": lambda cid: (
            handle_grant_brief(cid, arg)
            if arg
            else send_message(cid, "Usage: /grant-brief [name]")
        ),
        "/funder-intel": lambda cid: (
            handle_funder_intel(cid, arg)
            if arg
            else send_message(cid, "Usage: /funder-intel [funder-name]")
        ),
    }

    if cmd in handlers:
        handlers[cmd](chat_id)


def run_polling():
    """Run Telegram bot in polling mode (for testing)"""
    offset = 0
    logger.info("Starting Telegram bot polling...")

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}"
            r = requests.get(url, timeout=60)
            updates = r.json().get("result", [])

            for u in updates:
                offset = u["update_id"] + 1
                parse_command(u)

        except Exception as e:
            logger.error(f"Polling error: {e}")
            continue


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        run_polling()
    else:
        print("Telegram handlers loaded. Run with 'poll' flag for polling mode.")
        print(
            "Commands: /grants-this_month, /status, /deadline-alerts, /rank-by-deadline, /pattern-scan, /research [keywords], /grant-brief [name], /funder-intel [name]"
        )
