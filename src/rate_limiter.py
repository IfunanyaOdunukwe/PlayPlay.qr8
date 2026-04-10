"""Rate limiting and input validation for the Sculptor.

Pure functions — no Streamlit imports. Global counter persists to a JSON file.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date

MAX_PROMPT_LENGTH = 500
SESSION_MESSAGE_CAP = 20
GLOBAL_DAILY_CAP = 500
GLOBAL_COUNTER_FILE = "cache/sculptor_global_counter.json"


@dataclass
class RateLimitResult:
    allowed: bool
    reason: str | None = None


def validate_prompt(prompt: str, last_prompt: str | None) -> RateLimitResult:
    """Check prompt length and reject identical-to-previous prompts."""
    if len(prompt) > MAX_PROMPT_LENGTH:
        return RateLimitResult(
            allowed=False,
            reason=f"Your message is too long (max {MAX_PROMPT_LENGTH} characters). Please shorten it.",
        )
    if last_prompt is not None and prompt.strip() == last_prompt.strip():
        return RateLimitResult(
            allowed=False,
            reason="You just sent that same message. Try rephrasing or asking something new.",
        )
    return RateLimitResult(allowed=True)


def check_session_cap(session_count: int) -> RateLimitResult:
    """Check whether the session has reached its per-session message cap."""
    if session_count >= SESSION_MESSAGE_CAP:
        return RateLimitResult(
            allowed=False,
            reason=(
                f"You've reached the per-session limit of {SESSION_MESSAGE_CAP} messages. "
                "Refresh the page to start a new session."
            ),
        )
    return RateLimitResult(allowed=True)


def _load_global_counter() -> dict:
    """Load the global counter file, returning a fresh dict if missing or corrupt."""
    today = date.today().isoformat()
    if not os.path.exists(GLOBAL_COUNTER_FILE):
        return {"date": today, "count": 0}
    try:
        with open(GLOBAL_COUNTER_FILE, "r") as f:
            data = json.load(f)
        if data.get("date") != today:
            return {"date": today, "count": 0}
        if not isinstance(data.get("count"), int):
            return {"date": today, "count": 0}
        return data
    except (json.JSONDecodeError, OSError):
        return {"date": today, "count": 0}


def _save_global_counter(data: dict) -> None:
    os.makedirs(os.path.dirname(GLOBAL_COUNTER_FILE), exist_ok=True)
    try:
        with open(GLOBAL_COUNTER_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass  # Best-effort; don't crash the app on counter write failure


def check_global_cap() -> RateLimitResult:
    """Check whether the global daily cap has been reached."""
    data = _load_global_counter()
    if data["count"] >= GLOBAL_DAILY_CAP:
        return RateLimitResult(
            allowed=False,
            reason="The daily usage limit for this app has been reached. Please try again tomorrow.",
        )
    return RateLimitResult(allowed=True)


def record_request() -> None:
    """Increment the global counter. Call only after a successful LLM call."""
    data = _load_global_counter()
    data["count"] += 1
    _save_global_counter(data)
