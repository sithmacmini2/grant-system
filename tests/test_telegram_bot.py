import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
BOT_PATH = REPO_ROOT / "hermes-tasks" / "telegram-bot.py"


def load_bot_module(root, month="2026-04"):
    os.environ["GRANTS_ROOT"] = str(root)
    os.environ["GRANTS_MONTH"] = month
    os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"

    spec = importlib.util.spec_from_file_location("telegram_bot_under_test", BOT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CapturingBotMixin:
    def send(self, chat_id, text):
        self.sent.append((chat_id, text))


class TelegramBotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "configs").mkdir()
        (self.root / "configs" / "system-config.json").write_text(
            json.dumps({"telegram": {"bot_token": ""}}),
            encoding="utf-8",
        )
        self.module = load_bot_module(self.root)

        class TestBot(CapturingBotMixin, self.module.Bot):
            def __init__(self):
                super().__init__()
                self.sent = []

        self.Bot = TestBot

    def tearDown(self):
        self.tmp.cleanup()

    def write_json(self, relative_path, data):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def write_text(self, relative_path, text):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def last_message(self, bot):
        return bot.sent[-1][1]

    def test_process_update_accepts_bot_suffix_and_advances_offset(self):
        self.write_text(
            "outputs/briefs/2026-04/youth-summer-employment-program-brief.md",
            "Youth summer brief body",
        )
        bot = self.Bot()

        bot.process_update(
            {
                "update_id": 41,
                "message": {"chat": {"id": 123}, "text": "/brief@TestBot youth summer"},
            }
        )

        self.assertEqual(bot.offset, 42)
        self.assertIn("youth-summer-employment-program-brief.md", self.last_message(bot))

    def test_command_aliases_share_handlers(self):
        self.write_text("outputs/matrix/2026-04/2026-04-grant-matrix.csv", "name,deadline")
        bot = self.Bot()

        bot.handle("rank-by-deadline", None, 123)
        bot.handle("rank_by_deadline", None, 123)

        self.assertEqual(len(bot.sent), 2)
        self.assertTrue(all("Grant matrix:" in message for _, message in bot.sent))

    def test_missing_research_argument_returns_usage(self):
        bot = self.Bot()

        bot.handle("research", None, 123)

        self.assertEqual(self.last_message(bot), "Usage: /research [keywords]")

    def test_missing_data_files_do_not_crash(self):
        bot = self.Bot()

        bot.handle("status", None, 123)
        bot.handle("patterns", None, 123)
        bot.handle("alerts", None, 123)

        self.assertIn("Active grants: 0", bot.sent[0][1])
        self.assertIn("No pattern analysis found", bot.sent[1][1])
        self.assertEqual(bot.sent[2][1], "No urgent deadlines.")

    def test_invalid_json_falls_back_to_default(self):
        path = self.root / "data/enriched/2026-04/grants-enriched.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{bad json", encoding="utf-8")
        bot = self.Bot()

        with self.assertLogs("bot", level="ERROR"):
            bot.handle("status", None, 123)

        self.assertIn("Active grants: 0", self.last_message(bot))

    def test_research_returns_matching_grants(self):
        self.write_json(
            "data/enriched/2026-04/grants-enriched.json",
            [
                {
                    "name": "Youth Leadership Development Grant",
                    "funder": "Rhode Island Foundation",
                    "amount": 50000,
                    "enrichment": {"urgency_level": "MEDIUM"},
                }
            ],
        )
        bot = self.Bot()

        bot.handle("research", "foundation", 123)

        self.assertIn("Found 1 match(es):", self.last_message(bot))
        self.assertIn("$50,000", self.last_message(bot))

    def test_json_cache_reloads_when_file_changes(self):
        path = self.write_json(
            "data/enriched/2026-04/grants-enriched.json",
            [{"name": "First"}],
        )
        bot = self.Bot()

        self.assertEqual(bot.load_grants()[0]["name"], "First")
        next_mtime = path.stat().st_mtime + 2
        path.write_text(json.dumps([{"name": "Second"}]), encoding="utf-8")
        os.utime(path, (next_mtime, next_mtime))

        self.assertEqual(bot.load_grants()[0]["name"], "Second")

    def test_long_messages_are_truncated(self):
        text = "x" * 5000

        truncated = self.module.Bot.truncate_message(text)

        self.assertLessEqual(len(truncated), self.module.MAX_TELEGRAM_MESSAGE_LENGTH)
        self.assertTrue(truncated.endswith("[message truncated]"))


if __name__ == "__main__":
    unittest.main()
