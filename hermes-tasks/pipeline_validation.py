#!/usr/bin/env python3
"""
Schema-aware validation helpers for grant pipeline records.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from grants_context import grants_path


SCHEMA_PATH = grants_path("configs", "grant_normalized.schema.json")


def _load_schema() -> dict:
    try:
        with SCHEMA_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


SCHEMA = _load_schema()
RAW_REQUIRED = set(SCHEMA.get("required", []))
INTELLIGENCE_RECOMMENDATIONS = {
    "Start draft",
    "Full application",
    "Track only",
    "Skip",
}
URGENCY_LEVELS = {"HIGH", "MEDIUM", "LOW"}


def validate_grant_record(grant: object, stage: str = "raw") -> list[str]:
    """Return validation errors for a single grant record."""
    errors: list[str] = []
    if not isinstance(grant, dict):
        return ["Grant record must be a dictionary"]

    required = set(RAW_REQUIRED)
    if stage in {"enriched", "intelligence"}:
        required.add("enrichment")
    if stage == "intelligence":
        required.add("intelligence")

    for key in sorted(required):
        if key not in grant:
            errors.append(f"Missing required field: {key}")

    deadline = grant.get("deadline")
    if deadline:
        try:
            datetime.strptime(str(deadline), "%Y-%m-%d")
        except ValueError:
            errors.append(f"Invalid deadline format: {deadline}")

    amount = grant.get("amount")
    if amount is not None and not isinstance(amount, (int, float)):
        errors.append(f"Amount must be numeric, got {type(amount).__name__}")
    elif isinstance(amount, (int, float)) and amount < 0:
        errors.append("Amount cannot be negative")

    url = grant.get("url")
    if url is not None and not isinstance(url, str):
        errors.append("URL must be a string")

    if stage in {"enriched", "intelligence"}:
        enrichment = grant.get("enrichment")
        if not isinstance(enrichment, dict):
            errors.append("enrichment must be an object")
        else:
            days_remaining = enrichment.get("days_remaining")
            if not isinstance(days_remaining, int) or days_remaining < 0:
                errors.append("enrichment.days_remaining must be a non-negative integer")

            urgency_level = enrichment.get("urgency_level")
            if urgency_level not in URGENCY_LEVELS:
                errors.append(f"Invalid urgency level: {urgency_level}")

            eligibility = enrichment.get("eligibility")
            if not isinstance(eligibility, dict):
                errors.append("enrichment.eligibility must be an object")

    if stage == "intelligence":
        intelligence = grant.get("intelligence")
        if not isinstance(intelligence, dict):
            errors.append("intelligence must be an object")
        else:
            fit_score = intelligence.get("fit_score")
            if not isinstance(fit_score, int) or not 1 <= fit_score <= 10:
                errors.append("intelligence.fit_score must be an integer from 1 to 10")

            recommendation = intelligence.get("recommendation")
            if recommendation not in INTELLIGENCE_RECOMMENDATIONS:
                errors.append(f"Invalid recommendation: {recommendation}")

    return errors


def validate_grant_collection(grants: list[dict], stage: str = "raw") -> list[str]:
    """Return a flat list of validation errors for a collection of grants."""
    errors: list[str] = []
    for index, grant in enumerate(grants, start=1):
        record_errors = validate_grant_record(grant, stage=stage)
        errors.extend(f"Grant #{index}: {err}" for err in record_errors)
    return errors
