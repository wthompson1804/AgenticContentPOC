"""
Context Handoff Module - Preserving semantic richness across agent stages.

The problem: Each LLM call starts fresh. Complex ideas, nuance, and reasoning
chains can be lost when reduced to structured data alone.

Solution: Maintain a "rolling narrative" that captures:
1. What we learned (facts)
2. Why we think it matters (reasoning)
3. What questions remain (uncertainty)
4. The user's voice (original language)

This document gets passed forward through stages, growing richer over time.
"""

import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ContextBlock:
    """A block of context from a single stage."""
    stage: str
    timestamp: str

    # The user's exact words (preserve their voice)
    user_verbatim: str

    # What we extracted (structured)
    facts: Dict[str, Any]

    # The reasoning behind our interpretation (rich prose)
    reasoning: str

    # What we're still uncertain about
    open_questions: List[str]

    # Connections to prior context
    builds_on: Optional[str] = None

    # Confidence in our interpretation
    confidence: str = "medium"  # low/medium/high


@dataclass
class ContextHandoff:
    """
    Accumulating context document passed between stages.

    Think of this as a "briefing document" that gets richer
    as we learn more from the user.
    """
    session_id: str
    created_at: str

    # The rolling narrative - rich prose summary
    narrative: str = ""

    # Structured blocks from each stage
    blocks: List[ContextBlock] = field(default_factory=list)

    # Key themes that have emerged
    themes: List[str] = field(default_factory=list)

    # The "golden thread" - the core user intent in their own words
    golden_thread: str = ""

    # Constraints and boundaries (critical for backend)
    constraints: List[str] = field(default_factory=list)

    # Unresolved tensions or contradictions
    tensions: List[str] = field(default_factory=list)

    def add_block(self, block: ContextBlock):
        """Add a context block and update narrative."""
        self.blocks.append(block)

        # Update golden thread if this is early intent
        if block.stage in ["S0_ENTRY", "S1_INTENT"] and not self.golden_thread:
            self.golden_thread = block.user_verbatim

        # Accumulate constraints
        if "boundary" in block.stage.lower() or block.facts.get("constraints"):
            constraints = block.facts.get("constraints", [])
            if isinstance(constraints, str):
                constraints = [constraints]
            self.constraints.extend(constraints)

        # Note any tensions
        if block.open_questions:
            for q in block.open_questions:
                if "conflict" in q.lower() or "tension" in q.lower():
                    self.tensions.append(q)

    def get_briefing(self, for_stage: str) -> str:
        """
        Generate a briefing document for a downstream stage.

        This is what gets passed to the next LLM call to provide
        full context without losing nuance.
        """
        briefing_parts = []

        # The golden thread
        if self.golden_thread:
            briefing_parts.append(f"## The User's Core Intent\n\n\"{self.golden_thread}\"")

        # Rolling narrative
        if self.narrative:
            briefing_parts.append(f"## Story So Far\n\n{self.narrative}")

        # Key themes
        if self.themes:
            briefing_parts.append(f"## Emerging Themes\n\n" + "\n".join(f"- {t}" for t in self.themes))

        # Constraints
        if self.constraints:
            briefing_parts.append(f"## Constraints & Boundaries\n\n" + "\n".join(f"- {c}" for c in self.constraints))

        # Open questions
        all_questions = []
        for block in self.blocks:
            all_questions.extend(block.open_questions)
        if all_questions:
            briefing_parts.append(f"## Open Questions\n\n" + "\n".join(f"- {q}" for q in all_questions[:5]))

        # Tensions
        if self.tensions:
            briefing_parts.append(f"## Unresolved Tensions\n\n" + "\n".join(f"- {t}" for t in self.tensions))

        # Recent context blocks (last 3)
        recent = self.blocks[-3:] if len(self.blocks) > 3 else self.blocks
        if recent:
            block_summaries = []
            for b in recent:
                block_summaries.append(
                    f"**{b.stage}** ({b.confidence} confidence):\n"
                    f"User said: \"{b.user_verbatim[:150]}...\"\n"
                    f"We understood: {b.reasoning[:200]}..."
                )
            briefing_parts.append(f"## Recent Context\n\n" + "\n\n".join(block_summaries))

        return "\n\n---\n\n".join(briefing_parts)

    def update_narrative(self, new_content: str, stage: str):
        """Update the rolling narrative with new understanding."""
        timestamp = datetime.now().strftime("%H:%M")

        if self.narrative:
            self.narrative += f"\n\n[{stage} @ {timestamp}] {new_content}"
        else:
            self.narrative = f"[{stage} @ {timestamp}] {new_content}"

    def add_theme(self, theme: str):
        """Add an emerging theme if not already present."""
        if theme not in self.themes:
            self.themes.append(theme)

    def to_dict(self) -> dict:
        """Serialize for storage."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "narrative": self.narrative,
            "blocks": [asdict(b) for b in self.blocks],
            "themes": self.themes,
            "golden_thread": self.golden_thread,
            "constraints": self.constraints,
            "tensions": self.tensions
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ContextHandoff':
        """Deserialize from storage."""
        blocks = [
            ContextBlock(**b) for b in data.get("blocks", [])
        ]
        instance = cls(
            session_id=data["session_id"],
            created_at=data["created_at"],
            narrative=data.get("narrative", ""),
            blocks=blocks,
            themes=data.get("themes", []),
            golden_thread=data.get("golden_thread", ""),
            constraints=data.get("constraints", []),
            tensions=data.get("tensions", [])
        )
        return instance


def create_context_handoff(session_id: str) -> ContextHandoff:
    """Create a new context handoff document."""
    return ContextHandoff(
        session_id=session_id,
        created_at=datetime.now().isoformat()
    )


def record_stage_output(
    handoff: ContextHandoff,
    stage: str,
    user_message: str,
    extracted_facts: dict,
    reasoning: str,
    open_questions: List[str] = None,
    confidence: str = "medium"
) -> ContextHandoff:
    """
    Record the output of a stage into the context handoff.

    Args:
        handoff: The context handoff document
        stage: Current stage name (e.g., "S1_INTENT")
        user_message: The user's exact words
        extracted_facts: Structured data extracted
        reasoning: Rich prose explaining our interpretation
        open_questions: What we're still uncertain about
        confidence: How confident we are in our interpretation

    Returns:
        Updated context handoff
    """
    block = ContextBlock(
        stage=stage,
        timestamp=datetime.now().isoformat(),
        user_verbatim=user_message,
        facts=extracted_facts,
        reasoning=reasoning,
        open_questions=open_questions or [],
        confidence=confidence
    )

    handoff.add_block(block)

    # Update narrative with the reasoning
    if reasoning:
        handoff.update_narrative(reasoning, stage)

    return handoff


def extract_for_backend(handoff: ContextHandoff) -> dict:
    """
    Extract structured data for the mechanistic backend.

    This is what actually feeds into Steps 0-3.
    Returns the accumulated facts plus the narrative context.
    """
    # Merge all facts from all blocks
    merged_facts = {}
    for block in handoff.blocks:
        for key, value in block.facts.items():
            # Later blocks override earlier ones
            merged_facts[key] = value

    return {
        # Structured data for backend processing
        "facts": merged_facts,

        # Rich context for LLM stages
        "narrative": handoff.narrative,
        "golden_thread": handoff.golden_thread,
        "constraints": handoff.constraints,
        "themes": handoff.themes,

        # Open items for human review
        "open_questions": list(set(
            q for b in handoff.blocks for q in b.open_questions
        )),
        "tensions": handoff.tensions,

        # Confidence assessment
        "lowest_confidence_stages": [
            b.stage for b in handoff.blocks if b.confidence == "low"
        ]
    }


def format_handoff_for_display(handoff: ContextHandoff) -> str:
    """Format the handoff for UI display."""
    lines = []

    lines.append(f"**Session:** {handoff.session_id}")
    lines.append(f"**Stages completed:** {len(handoff.blocks)}")

    if handoff.golden_thread:
        lines.append(f"\n**Core Intent:** \"{handoff.golden_thread[:100]}...\"")

    if handoff.themes:
        lines.append(f"\n**Themes:** {', '.join(handoff.themes)}")

    if handoff.constraints:
        lines.append(f"\n**Constraints:**")
        for c in handoff.constraints[:3]:
            lines.append(f"  - {c}")

    if handoff.tensions:
        lines.append(f"\n**Tensions:**")
        for t in handoff.tensions[:2]:
            lines.append(f"  - {t}")

    # Recent reasoning
    if handoff.blocks:
        latest = handoff.blocks[-1]
        lines.append(f"\n**Latest ({latest.stage}):**")
        lines.append(f"  {latest.reasoning[:200]}...")

    return "\n".join(lines)
