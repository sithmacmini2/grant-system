#!/usr/bin/env python3
"""
Telegram Bot for Grant Intelligence System
"""

import json
import os
import logging
import requests
from datetime import datetime
from pathlib import Path
import signal
import time
import sys

GRANTS_ROOT = Path(os.environ.get("GRANTS_ROOT", "/home/sithmm2_admin/grants-system"))
CONFIG_PATH = GRANTS_ROOT / "configs" / "system-config.json"
LOG_DIR = GRANTS_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as e:
        logger_name = "bot.bootstrap"
        logging.getLogger(logger_name).warning("Could not load config: %s", e)
        return {}


CONFIG = load_config()
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or CONFIG.get("telegram", {}).get(
    "bot_token", ""
)
MONTH_OVERRIDE = os.environ.get("GRANTS_MONTH", "").strip()
OFFSET_PATH = LOG_DIR / "telegram-offset.json"
MAX_TELEGRAM_MESSAGE_LENGTH = 3900

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "telegram-bot.log"),
        logging.StreamHandler(),
    ],
    force=True,
)
logger = logging.getLogger("bot")


class JsonFileCache:
    def __init__(self):
        self._cache = {}

    def read(self, path, default):
        try:
            stat = path.stat()
            cached = self._cache.get(path)
            if cached and cached["mtime"] == stat.st_mtime:
                return cached["data"]

            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self._cache[path] = {"mtime": stat.st_mtime, "data": data}
            return data
        except FileNotFoundError:
            self._cache.pop(path, None)
            return default
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to read %s: %s", path, e)
            return default


class Bot:
    def __init__(self):
        if not BOT_TOKEN:
            raise RuntimeError(
                "Telegram bot token missing. Set TELEGRAM_BOT_TOKEN."
            )
        self.api = f"https://api.telegram.org/bot{BOT_TOKEN}"
        self.session = requests.Session()
        self.cache = JsonFileCache()
        self.offset = self.load_offset()
        self.month = self.latest_month()
        self.running = True

    def send(self, chat_id, text):
        logger.info("Sending message to chat %s (%s chars)", chat_id, len(text))
        result = self.request_json(
            "post",
            f"{self.api}/sendMessage",
            json={"chat_id": chat_id, "text": self.truncate_message(text)},
            timeout=10,
        )
        if result and not result.get("ok"):
            logger.error("Telegram send failed: %s", result)

    def request_json(self, method, url, attempts=3, **kwargs):
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as e:
                last_error = e
                if attempt < attempts:
                    time.sleep(min(2 ** (attempt - 1), 5))
        logger.error("Telegram request failed after %s attempt(s): %s", attempts, last_error)
        return None

    def load_offset(self):
        try:
            with OFFSET_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return int(data.get("offset", 0))
        except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
            return 0

    def save_offset(self):
        try:
            temp_path = OFFSET_PATH.with_suffix(".tmp")
            temp_path.write_text(json.dumps({"offset": self.offset}), encoding="utf-8")
            temp_path.replace(OFFSET_PATH)
        except OSError as e:
            logger.error("Failed to save Telegram offset: %s", e)

    def stop(self, signum=None, frame=None):
        logger.info("Stopping polling...")
        self.running = False

    def handle(self, cmd, args, chat_id):
        cmd = cmd.replace("-", "_")
        logger.info("Handling command /%s for chat %s", cmd, chat_id)
        if cmd == "start":
            self.send(chat_id, "Grant System Active! /help for commands")
        elif cmd == "help":
            self.send(
                chat_id,
                (
                    "Commands:\n"
                    "/status\n"
                    "/grants or /grants_this_month\n"
                    "/alerts or /deadline_alerts\n"
                    "/rank or /rank_by_deadline\n"
                    "/patterns or /pattern_scan\n"
                    "/research [keywords]\n"
                    "/brief or /grant_brief [name]\n"
                    "/funder_intel [name]"
                ),
            )
        elif cmd == "status":
            grants = self.load_grants()
            month = self.month or "No data"
            self.send(
                chat_id,
                (
                    "Grant Intelligence System Status\n"
                    f"Data month: {month}\n"
                    f"Active grants: {len(grants)}\n"
                    f"Last check: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    f"Location: {GRANTS_ROOT}"
                ),
            )
        elif cmd in {"grants", "grants_this_month"}:
            self.cmd_grants(chat_id)
        elif cmd in {"alerts", "deadline_alerts"}:
            self.cmd_alerts(chat_id)
        elif cmd in {"rank", "rank_by_deadline"}:
            self.cmd_rank(chat_id)
        elif cmd in {"patterns", "pattern_scan"}:
            self.cmd_patterns(chat_id)
        elif cmd == "research":
            self.cmd_research(chat_id, args)
        elif cmd in {"brief", "grant_brief"}:
            self.cmd_brief(chat_id, args)
        elif cmd == "funder_intel":
            self.cmd_funder(chat_id, args)
        else:
            self.send(chat_id, f"Unknown: {cmd}")

    def latest_month(self):
        if MONTH_OVERRIDE:
            return MONTH_OVERRIDE

        candidates = []
        for base in (
            GRANTS_ROOT / "data" / "enriched",
            GRANTS_ROOT / "outputs" / "tracking",
            GRANTS_ROOT / "outputs" / "matrix",
        ):
            if base.exists():
                candidates.extend(p.name for p in base.iterdir() if p.is_dir())
        return max(candidates) if candidates else datetime.now().strftime("%Y-%m")

    def read_json(self, path, default):
        return self.cache.read(path, default)

    def load_grants(self):
        path = GRANTS_ROOT / "data" / "enriched" / self.month / "grants-enriched.json"
        data = self.read_json(path, [])
        return data if isinstance(data, list) else []

    def cmd_grants(self, chat_id):
        path = GRANTS_ROOT / "outputs" / "tracking" / self.month / "active-tracking.md"
        if path.exists():
            self.send(chat_id, f"Tracking dashboard: {path}")
        else:
            self.send(chat_id, "No tracking dashboard found. Run monthly research first.")

    def cmd_alerts(self, chat_id):
        urgent = [
            grant
            for grant in self.load_grants()
            if grant.get("enrichment", {}).get("urgency_level") == "HIGH"
        ]
        if not urgent:
            self.send(chat_id, "No urgent deadlines.")
            return

        lines = ["Urgent deadlines:"]
        for grant in urgent[:5]:
            name = grant.get("name", "Unnamed grant")
            deadline = grant.get("deadline", "No deadline")
            amount = self.format_amount(grant.get("amount"))
            lines.append(f"- {name} | {deadline} | {amount}")
        if len(urgent) > 5:
            lines.append(f"+{len(urgent) - 5} more")
        self.send(chat_id, "\n".join(lines))

    def cmd_rank(self, chat_id):
        path = (
            GRANTS_ROOT
            / "outputs"
            / "matrix"
            / self.month
            / f"{self.month}-grant-matrix.csv"
        )
        if path.exists():
            self.send(chat_id, f"Grant matrix: {path}")
        else:
            self.send(chat_id, "No grant matrix found.")

    def cmd_patterns(self, chat_id):
        path = (
            GRANTS_ROOT
            / "data"
            / "intelligence"
            / self.month
            / "cerebro-analysis.json"
        )
        patterns = self.read_json(path, {}).get("patterns_identified", [])
        if patterns:
            self.send(chat_id, "Patterns:\n" + "\n".join(f"- {p}" for p in patterns[:5]))
        else:
            self.send(chat_id, "No pattern analysis found. Run research first.")

    def cmd_research(self, chat_id, args):
        if not args:
            self.send(chat_id, "Usage: /research [keywords]")
            return

        needle = args.lower()
        matches = [
            grant
            for grant in self.load_grants()
            if needle in f"{grant.get('name', '')} {grant.get('funder', '')}".lower()
        ]
        if not matches:
            self.send(chat_id, "No matches.")
            return

        lines = [f"Found {len(matches)} match(es):"]
        for grant in matches[:5]:
            name = grant.get("name", "Unnamed grant")
            funder = grant.get("funder", "Unknown funder")
            amount = self.format_amount(grant.get("amount"))
            lines.append(f"- {name} | {funder} | {amount}")
        self.send(chat_id, "\n".join(lines))

    def cmd_brief(self, chat_id, args):
        if not args:
            self.send(chat_id, "Usage: /brief [name]")
            return

        brief_dir = GRANTS_ROOT / "outputs" / "briefs" / self.month
        slug = self.slugify(args)
        matches = (
            sorted(brief_dir.glob(f"*{slug}*-brief.md"))
            if brief_dir.exists()
            else []
        )
        if not matches:
            self.send(chat_id, f"Brief not found for: {args}")
            return

        try:
            preview = matches[0].read_text(encoding="utf-8")[:900].strip()
        except OSError as e:
            logger.error("Failed to read brief %s: %s", matches[0], e)
            self.send(chat_id, "Brief found, but it could not be read.")
            return
        self.send(chat_id, f"Brief: {matches[0].name}\n\n{preview}")

    def cmd_funder(self, chat_id, args):
        if not args:
            self.send(chat_id, "Usage: /funder_intel [name]")
            return

        funders = self.read_json(
            GRANTS_ROOT / "data" / "intelligence" / self.month / "cerebro-analysis.json",
            {},
        ).get("funders_clustered", {})
        match = next((name for name in funders if args.lower() in name.lower()), None)
        if not match:
            self.send(chat_id, f"No funder profile found for: {args}")
            return

        profile = funders[match]
        self.send(
            chat_id,
            (
                f"Funder: {match}\n"
                f"Grants tracked: {profile.get('count', 0)}\n"
                f"Average fit: {profile.get('avg_fit', 0):.1f}"
            ),
        )

    @staticmethod
    def format_amount(amount):
        if isinstance(amount, (int, float)):
            return f"${amount:,.0f}"
        return "Amount unavailable"

    @staticmethod
    def slugify(value):
        return "-".join(value.lower().strip().replace("_", " ").split())

    @staticmethod
    def truncate_message(text):
        if len(text) <= MAX_TELEGRAM_MESSAGE_LENGTH:
            return text
        suffix = "\n\n[message truncated]"
        return text[: MAX_TELEGRAM_MESSAGE_LENGTH - len(suffix)] + suffix

    def process_update(self, update):
        self.offset = max(self.offset, update.get("update_id", self.offset - 1) + 1)
        self.save_offset()
        logger.info("Processing update %s", update.get("update_id"))

        message = update.get("message") or {}
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        if not chat_id or not text.startswith("/"):
            logger.info("Skipping non-command update %s", update.get("update_id"))
            return

        parts = text.split(" ", 1)
        cmd = parts[0][1:].split("@", 1)[0].lower()
        args = parts[1] if len(parts) > 1 else None
        self.handle(cmd, args, chat_id)

    def poll(self):
        logger.info("Polling...")
        while self.running:
            result = self.request_json(
                "get",
                f"{self.api}/getUpdates?timeout=60&offset={self.offset}",
                attempts=1,
                timeout=65,
            )
            if not result:
                time.sleep(5)
                continue
            if not result.get("ok", True):
                logger.error("Telegram polling failed: %s", result)
                time.sleep(5)
                continue

            for u in result.get("result", []):
                self.process_update(u)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        bot = Bot()
        signal.signal(signal.SIGINT, bot.stop)
        signal.signal(signal.SIGTERM, bot.stop)
        bot.poll()
    else:
        print("Run with: python3 telegram-bot.py poll")
