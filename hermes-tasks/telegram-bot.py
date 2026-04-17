#!/usr/bin/env python3
"""
Telegram Bot Service for Grant Intelligence System
Run this to enable Telegram command handling.
"""

import json
import os
import sys
import logging
import requests
from datetime import datetime
import threading
import time

GRANTS_ROOT = "/home/sithmm2_admin/grants-system"
BOT_TOKEN = "8114463389:AAEQPHmADS7olea-VM-0dIqYEOs2fEeVpzo"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{GRANTS_ROOT}/logs/telegram.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("telegram_bot")


class GrantTelegramBot:
    def __init__(self):
        self.token = BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0
        self.running = False

    def send_message(self, chat_id, text, parse_mode="Markdown"):
        """Send a message"""
        url = f"{self.api_url}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        try:
            requests.post(url, json=data, timeout=10)
        except Exception as e:
            logger.error(f"Send error: {e}")

    def handle_command(self, command, args, chat_id):
        """Handle incoming commands"""
        logger.info(f"Command: {command} {args}")

        commands = {
            "start": lambda: self.send_message(
                chat_id,
                "✅ *Grant Intelligence System*\n\nWelcome! Use /help for commands.",
            ),
            "help": lambda: self.send_message(
                chat_id,
                """
📋 *Commands:*

/grants_this_month - View dashboard
/grant_brief [name] - Get brief
/rank_by_deadline - Matrix by deadline
/funder_intel [name] - Funder profile
/pattern_scan - Success patterns
/research [keywords] - Search grants
/deadline_alerts - Urgent deadlines
/status - System status
            """,
            ),
            "status": lambda: self.cmd_status(chat_id),
            "grants_this_month": lambda: self.cmd_grants_month(chat_id),
            "deadline_alerts": lambda: self.cmd_deadlines(chat_id),
            "rank_by_deadline": lambda: self.cmd_rank(chat_id),
            "pattern_scan": lambda: self.cmd_patterns(chat_id),
        }

        if command in ["grant_brief", "research", "funder_intel"]:
            commands[command](args, chat_id)
        elif command in commands:
            commands[command]()
        else:
            self.send_message(chat_id, f"Unknown command: {command}")

    def cmd_status(self, chat_id):
        """Handle /status command"""
        import subprocess

        result = subprocess.run(
            f"ls {GRANTS_ROOT}/data/raw/ 2>/dev/null | tail -1",
            shell=True,
            capture_output=True,
            text=True,
        )
        month = result.stdout.strip() or "No data"

        msg = f"""✅ *System Status*

• Location: `/home/sithmm2_admin/grants-system/`
• Data Month: {month}
• Last Run: {datetime.now().strftime("%Y-%m-%d %H:%M")}
• Bot: Active

Use /help for commands."""
        self.send_message(chat_id, msg)

    def cmd_grants_month(self, chat_id):
        """Handle /grants_this_month"""
        dashboard = f"{GRANTS_ROOT}/outputs/tracking/2026-04/active-tracking.md"
        if os.path.exists(dashboard):
            self.send_message(chat_id, "📊 *Tracking Dashboard*\n\n" + dashboard)
        else:
            self.send_message(chat_id, "❌ Run monthly research first.")

    def cmd_deadlines(self, chat_id):
        """Handle /deadline_alerts"""
        self.send_message(
            chat_id,
            "📅 Checking deadlines...\n\nRun `/weekly-deadline-check.py` to generate alerts.",
        )

    def cmd_rank(self, chat_id):
        """Handle /rank_by_deadline"""
        self.send_message(
            chat_id, "📋 Matrix: `/outputs/matrix/2026-04/2026-04-grant-matrix.csv`"
        )

    def cmd_patterns(self, chat_id):
        """Handle /pattern_scan"""
        intel = f"{GRANTS_ROOT}/data/intelligence/2026-04/cerebro-analysis.json"
        if os.path.exists(intel):
            with open(intel) as f:
                data = json.load(f)
            patterns = data.get("patterns_identified", [])[:5]
            msg = "🧠 *Patterns:*\n" + "\n".join([f"• {p}" for p in patterns])
            self.send_message(chat_id, msg)
        else:
            self.send_message(chat_id, "❌ Run monthly research first.")

    def process_update(self, update):
        """Process a single update"""
        if "message" not in update:
            return

        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "")

        if not text.startswith("/"):
            return

        parts = text.split(" ", 1)
        command = parts[0].replace("/", "").lower()
        args = parts[1] if len(parts) > 1 else None

        self.handle_command(command, args, chat_id)

    def poll(self):
        """Poll for updates"""
        logger.info("Starting polling...")
        self.running = True

        while self.running:
            try:
                url = f"{self.api_url}/getUpdates?timeout=60&offset={self.offset}"
                response = requests.get(url, timeout=65)
                updates = response.json().get("result", [])

                for update in updates:
                    self.offset = update["update_id"] + 1
                    self.process_update(update)

            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)

    def start_polling(self):
        """Start polling in background"""
        thread = threading.Thread(target=self.poll, daemon=True)
        thread.start()
        return thread


def main():
    bot = GrantTelegramBot()

    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        logger.info("Starting Telegram bot in polling mode...")
        bot.start_polling()

        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Stopping bot...")
    else:
        print("Telegram bot ready. Run with 'poll' flag to start receiving commands.")
        print(
            "Commands: /start, /help, /status, /grants_this_month, /deadline_alerts, /rank_by_deadline, /pattern_scan"
        )


if __name__ == "__main__":
    main()
