#!/usr/bin/env python3
"""
Compatibility wrapper for the Telegram bot.

The canonical command implementation lives in telegram-bot.py. This module keeps
older imports and entrypoints working without duplicating command logic.
"""

import importlib.util
from pathlib import Path
import sys


def _load_bot_module():
    module_path = Path(__file__).with_name("telegram-bot.py")
    spec = importlib.util.spec_from_file_location("telegram_bot", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_bot_module = _load_bot_module()
Bot = _bot_module.Bot


def _bot():
    return Bot()


def send_message(chat_id, text, parse_mode=None):
    _bot().send(chat_id, text)


def parse_command(update):
    _bot().process_update(update)


def run_polling():
    _bot().poll()


def handle_grants_this_month(chat_id):
    _bot().cmd_grants(chat_id)


def handle_status(chat_id):
    _bot().handle("status", None, chat_id)


def handle_deadline_alerts(chat_id):
    _bot().cmd_alerts(chat_id)


def handle_rank_by_deadline(chat_id):
    _bot().cmd_rank(chat_id)


def handle_pattern_scan(chat_id):
    _bot().cmd_patterns(chat_id)


def handle_research(chat_id, keywords):
    _bot().cmd_research(chat_id, keywords)


def handle_grant_brief(chat_id, name):
    _bot().cmd_brief(chat_id, name)


def handle_funder_intel(chat_id, funder):
    _bot().cmd_funder(chat_id, funder)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        run_polling()
    else:
        print("Telegram command handlers are provided by telegram-bot.py.")
        print("Run with: python3 telegram-handlers.py poll")
