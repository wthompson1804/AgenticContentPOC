"""
Timebox Module - Turn counting and fast-path management for chat intake.

Per PRD Part 6: Question Budget & Timebox
- Default session: 8-12 turns
- Hard cap: 18 turns
- Hard questions: max 4
"""

from typing import TypedDict
from datetime import datetime


class TimeboxState(TypedDict):
    """Timebox state structure."""
    turns: int
    hard_questions: int
    started_at: str
    last_turn_at: str
    fast_path_offered: bool
    hard_stop_reached: bool
    extension_turns: int  # Additional turns after hard stop (max 2)


def init_timebox() -> TimeboxState:
    """Initialize timebox state for a new session."""
    now = datetime.utcnow().isoformat()
    return {
        "turns": 0,
        "hard_questions": 0,
        "started_at": now,
        "last_turn_at": now,
        "fast_path_offered": False,
        "hard_stop_reached": False,
        "extension_turns": 0
    }


def register_turn(
    timebox: TimeboxState,
    is_hard_question: bool = False,
    config: dict | None = None
) -> TimeboxState:
    """
    Register a conversation turn and update timebox state.

    Args:
        timebox: Current timebox state
        is_hard_question: Whether this turn contains a hard question
        config: Optional config with timebox settings

    Returns:
        Updated timebox state
    """
    # Get limits from config or use defaults
    hard_cap = 18
    hard_questions_max = 4
    if config and "timebox" in config:
        hard_cap = config["timebox"].get("hard_cap_turns", 18)
        hard_questions_max = config["timebox"].get("hard_questions_max", 4)

    # Create updated state
    updated = timebox.copy()
    updated["turns"] = timebox["turns"] + 1
    updated["last_turn_at"] = datetime.utcnow().isoformat()

    if is_hard_question:
        updated["hard_questions"] = timebox["hard_questions"] + 1

    # Check if hard stop reached
    if updated["turns"] >= hard_cap and not timebox["hard_stop_reached"]:
        updated["hard_stop_reached"] = True

    # Track extension turns after hard stop
    if timebox["hard_stop_reached"]:
        updated["extension_turns"] = timebox["extension_turns"] + 1

    return updated


def should_offer_fast_path(
    timebox: TimeboxState,
    config: dict | None = None
) -> bool:
    """
    Determine if fast-path should be offered to user.

    Conditions:
    - Turns >= default_turns (10) and not yet offered
    - OR hard_questions >= max (4)
    """
    default_turns = 10
    hard_questions_max = 4
    if config and "timebox" in config:
        default_turns = config["timebox"].get("default_turns", 10)
        hard_questions_max = config["timebox"].get("hard_questions_max", 4)

    if timebox["fast_path_offered"]:
        return False

    if timebox["turns"] >= default_turns:
        return True

    if timebox["hard_questions"] >= hard_questions_max:
        return True

    return False


def mark_fast_path_offered(timebox: TimeboxState) -> TimeboxState:
    """Mark that fast-path has been offered to user."""
    updated = timebox.copy()
    updated["fast_path_offered"] = True
    return updated


def reached_hard_stop(
    timebox: TimeboxState,
    config: dict | None = None
) -> bool:
    """Check if hard stop has been reached (18 turns)."""
    hard_cap = 18
    if config and "timebox" in config:
        hard_cap = config["timebox"].get("hard_cap_turns", 18)

    return timebox["turns"] >= hard_cap


def should_force_proceed(timebox: TimeboxState) -> bool:
    """
    Check if system should force proceed after hard stop.

    Per PRD Part 6.4: After hard stop, allow max 2 additional turns,
    then force proceed.
    """
    if not timebox["hard_stop_reached"]:
        return False

    return timebox["extension_turns"] >= 2


def get_timebox_status(
    timebox: TimeboxState,
    config: dict | None = None
) -> dict:
    """
    Get human-readable timebox status for UI display.

    Returns dict with:
    - turns_used: Current turn count
    - turns_remaining: Turns until hard stop
    - hard_questions_used: Hard questions asked
    - hard_questions_remaining: Hard questions until limit
    - status: "normal" | "approaching_limit" | "at_limit" | "exceeded"
    """
    hard_cap = 18
    default_turns = 10
    hard_questions_max = 4
    if config and "timebox" in config:
        hard_cap = config["timebox"].get("hard_cap_turns", 18)
        default_turns = config["timebox"].get("default_turns", 10)
        hard_questions_max = config["timebox"].get("hard_questions_max", 4)

    turns_remaining = max(0, hard_cap - timebox["turns"])
    hq_remaining = max(0, hard_questions_max - timebox["hard_questions"])

    # Determine status
    if timebox["turns"] >= hard_cap:
        status = "exceeded"
    elif timebox["turns"] >= default_turns:
        status = "at_limit"
    elif timebox["turns"] >= default_turns - 2:
        status = "approaching_limit"
    else:
        status = "normal"

    return {
        "turns_used": timebox["turns"],
        "turns_remaining": turns_remaining,
        "hard_questions_used": timebox["hard_questions"],
        "hard_questions_remaining": hq_remaining,
        "status": status,
        "fast_path_offered": timebox["fast_path_offered"],
        "hard_stop_reached": timebox["hard_stop_reached"]
    }


def get_session_duration_minutes(timebox: TimeboxState) -> float:
    """Calculate session duration in minutes."""
    started = datetime.fromisoformat(timebox["started_at"])
    now = datetime.utcnow()
    delta = now - started
    return delta.total_seconds() / 60
