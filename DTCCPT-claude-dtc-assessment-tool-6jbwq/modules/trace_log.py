"""
Trace Logging Module - Agent Observability

Provides structured logging for debugging agent state machines.
Captures state transitions, LLM calls, extractions, and decisions.
"""

import json
import os
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, asdict, field


@dataclass
class TraceEntry:
    """Single trace log entry."""
    timestamp: str
    event_type: str  # state_transition, llm_call, extraction, decision, error
    state: str
    data: dict
    duration_ms: Optional[int] = None


@dataclass
class TraceSession:
    """Complete session trace."""
    session_id: str
    started_at: str
    entries: list = field(default_factory=list)

    def add_entry(self, event_type: str, state: str, data: dict, duration_ms: int = None):
        """Add a trace entry."""
        entry = TraceEntry(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            state=state,
            data=data,
            duration_ms=duration_ms
        )
        self.entries.append(entry)
        return entry

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "entries": [asdict(e) for e in self.entries]
        }

    def get_summary(self) -> dict:
        """Get a summary of the session for UI display."""
        state_transitions = [e for e in self.entries if e.event_type == "state_transition"]
        llm_calls = [e for e in self.entries if e.event_type == "llm_call"]
        errors = [e for e in self.entries if e.event_type == "error"]

        return {
            "total_events": len(self.entries),
            "state_transitions": len(state_transitions),
            "llm_calls": len(llm_calls),
            "errors": len(errors),
            "current_state": state_transitions[-1].data.get("to_state") if state_transitions else "unknown",
            "duration_total_ms": sum(e.duration_ms or 0 for e in self.entries),
        }


class TraceLogger:
    """Manages trace logging for a session."""

    def __init__(self, session_id: str, persist_dir: str = "data/traces"):
        self.session = TraceSession(
            session_id=session_id,
            started_at=datetime.now().isoformat()
        )
        self.persist_dir = persist_dir

        # Create directory if needed
        if persist_dir:
            os.makedirs(persist_dir, exist_ok=True)

    def log_state_transition(self, from_state: str, to_state: str, trigger: str = None):
        """Log a state machine transition."""
        self.session.add_entry(
            event_type="state_transition",
            state=from_state,
            data={
                "from_state": from_state,
                "to_state": to_state,
                "trigger": trigger
            }
        )

    def log_llm_call(self, state: str, prompt_type: str, model: str,
                     response_preview: str = None, duration_ms: int = None,
                     parse_success: bool = False, fallback_used: bool = False):
        """Log an LLM API call."""
        self.session.add_entry(
            event_type="llm_call",
            state=state,
            data={
                "prompt_type": prompt_type,
                "model": model,
                "response_preview": (response_preview or "")[:200],
                "parse_success": parse_success,
                "fallback_used": fallback_used
            },
            duration_ms=duration_ms
        )

    def log_extraction(self, state: str, field: str, value: Any,
                       confidence: str, source: str):
        """Log a data extraction."""
        self.session.add_entry(
            event_type="extraction",
            state=state,
            data={
                "field": field,
                "value": str(value)[:100],
                "confidence": confidence,
                "source": source
            }
        )

    def log_decision(self, state: str, decision: str, reason: str = None):
        """Log a decision point."""
        self.session.add_entry(
            event_type="decision",
            state=state,
            data={
                "decision": decision,
                "reason": reason
            }
        )

    def log_error(self, state: str, error: str, recoverable: bool = True):
        """Log an error."""
        self.session.add_entry(
            event_type="error",
            state=state,
            data={
                "error": error,
                "recoverable": recoverable
            }
        )

    def get_recent_entries(self, n: int = 10) -> list:
        """Get the N most recent entries."""
        return self.session.entries[-n:]

    def get_summary(self) -> dict:
        """Get session summary."""
        return self.session.get_summary()

    def persist(self):
        """Save trace to file."""
        if not self.persist_dir:
            return

        filepath = os.path.join(
            self.persist_dir,
            f"trace_{self.session.session_id}.json"
        )

        with open(filepath, 'w') as f:
            json.dump(self.session.to_dict(), f, indent=2)

    def format_for_ui(self) -> str:
        """Format trace for UI display."""
        lines = []
        lines.append(f"**Session:** {self.session.session_id}")
        lines.append(f"**Started:** {self.session.started_at}")
        lines.append("")

        summary = self.get_summary()
        lines.append(f"**Events:** {summary['total_events']} total")
        lines.append(f"**LLM Calls:** {summary['llm_calls']}")
        lines.append(f"**Current State:** {summary['current_state']}")

        if summary['errors'] > 0:
            lines.append(f"**Errors:** {summary['errors']}")

        lines.append("")
        lines.append("---")
        lines.append("**Recent Activity:**")

        for entry in self.get_recent_entries(5):
            icon = {
                "state_transition": "🔄",
                "llm_call": "🤖",
                "extraction": "📤",
                "decision": "🎯",
                "error": "❌"
            }.get(entry.event_type, "•")

            if entry.event_type == "state_transition":
                lines.append(f"{icon} {entry.data['from_state']} → {entry.data['to_state']}")
            elif entry.event_type == "llm_call":
                status = "✓" if entry.data.get('parse_success') else "⚠"
                lines.append(f"{icon} LLM: {entry.data['prompt_type']} {status}")
            elif entry.event_type == "extraction":
                lines.append(f"{icon} {entry.data['field']}: {entry.data['value'][:30]}...")
            elif entry.event_type == "error":
                lines.append(f"{icon} Error: {entry.data['error'][:50]}")
            else:
                lines.append(f"{icon} {entry.event_type}")

        return "\n".join(lines)


# Global instance management
_current_logger: Optional[TraceLogger] = None


def get_trace_logger(session_id: str = None) -> TraceLogger:
    """Get or create trace logger for session."""
    global _current_logger

    if session_id and (_current_logger is None or _current_logger.session.session_id != session_id):
        _current_logger = TraceLogger(session_id)

    return _current_logger


def init_trace_logger(session_id: str) -> TraceLogger:
    """Initialize a new trace logger."""
    global _current_logger
    _current_logger = TraceLogger(session_id)
    return _current_logger
