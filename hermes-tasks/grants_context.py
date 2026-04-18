#!/usr/bin/env python3
"""
Shared path and configuration helpers for the grant intelligence scripts.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


DEFAULT_GRANTS_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WIKI_ROOT = Path.home() / "wiki"


def grants_root() -> Path:
    """Return the active grants-system root."""
    return Path(os.environ.get("GRANTS_ROOT", DEFAULT_GRANTS_ROOT))


def wiki_root() -> Path:
    """Return the Obsidian wiki root from config or the default path."""
    config = load_system_config()
    configured = config.get("paths", {}).get("wiki")
    if configured:
        return Path(configured)
    return Path(os.environ.get("WIKI_ROOT", DEFAULT_WIKI_ROOT))


def config_path() -> Path:
    return grants_root() / "configs" / "system-config.json"


def load_system_config() -> dict:
    try:
        with config_path().open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def active_month(month_str: str | None = None) -> str:
    """Resolve the month used for data paths."""
    override = os.environ.get("GRANTS_MONTH", "").strip()
    if override:
        return override
    if month_str:
        return month_str
    return datetime.now().strftime("%Y-%m")


def grants_path(*parts: str) -> Path:
    return grants_root().joinpath(*parts)


def wiki_path(*parts: str) -> Path:
    return wiki_root().joinpath(*parts)
