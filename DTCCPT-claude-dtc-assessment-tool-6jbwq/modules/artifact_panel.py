"""
Artifact Panel Module - Progressive 2-pager artifact management.

Per PRD Part 9: Progressive 2-Pager Artifact
- 8 sections that update progressively
- Single source of truth for the assessment
"""

from typing import TypedDict, Literal
from datetime import datetime

from .judgment_engine import IntakePacket, Assumption, format_assumptions_for_display


class ArtifactSection(TypedDict, total=False):
    """Structure for an artifact section."""
    title: str
    content: str
    confidence: Literal["high", "med", "low"]
    locked: bool
    last_updated: str
    source: str  # Which state/step populated this


class ArtifactDoc(TypedDict):
    """Full artifact document structure per PRD Part 9.1."""
    section_1: ArtifactSection  # What You're Trying to Do
    section_2: ArtifactSection  # Opportunity Shape
    section_3: ArtifactSection  # Operating Context
    section_4: ArtifactSection  # What the Agent Would Actually Do
    section_5: ArtifactSection  # Initial Feasibility & Direction
    section_6: ArtifactSection  # Key Risks & Success Factors
    section_7: ArtifactSection  # Assumptions & Uncertainties
    section_8: ArtifactSection  # What Happens Next
    created_at: str
    last_updated: str
    version: str


def init_artifact() -> ArtifactDoc:
    """Initialize empty artifact document."""
    now = datetime.utcnow().isoformat()

    def empty_section(title: str) -> ArtifactSection:
        return {
            "title": title,
            "content": "",
            "confidence": "low",
            "locked": False,
            "last_updated": now,
            "source": "init"
        }

    return {
        "section_1": empty_section("What You're Trying to Do"),
        "section_2": empty_section("Opportunity Shape"),
        "section_3": empty_section("Operating Context"),
        "section_4": empty_section("What the Agent Would Actually Do"),
        "section_5": empty_section("Initial Feasibility & Direction"),
        "section_6": empty_section("Key Risks & Success Factors"),
        "section_7": empty_section("Assumptions & Uncertainties"),
        "section_8": empty_section("What Happens Next"),
        "created_at": now,
        "last_updated": now,
        "version": "1.0"
    }


def update_section(
    artifact: ArtifactDoc,
    section_key: str,
    content: str,
    confidence: Literal["high", "med", "low"] = "med",
    source: str = "chat",
    lock: bool = False
) -> ArtifactDoc:
    """Update a specific section of the artifact."""
    updated = artifact.copy()
    now = datetime.utcnow().isoformat()

    if section_key in updated:
        section = updated[section_key].copy()
        section["content"] = content
        section["confidence"] = confidence
        section["last_updated"] = now
        section["source"] = source
        if lock:
            section["locked"] = True
        updated[section_key] = section
        updated["last_updated"] = now

    return updated


def apply_artifact_updates(
    artifact_doc: ArtifactDoc,
    intake_packet: IntakePacket,
    assumptions: list[Assumption],
    step_outputs: dict | None = None
) -> ArtifactDoc:
    """
    Apply updates to artifact based on intake packet and step outputs.

    Per PRD Part 9.2: Update Triggers
    """
    updated = artifact_doc.copy()
    now = datetime.utcnow().isoformat()

    # Section 1: What You're Trying to Do (from S1 Intent)
    use_case = intake_packet.get("use_case_intent", {}).get("value")
    if use_case:
        updated = update_section(
            updated, "section_1", use_case,
            confidence=intake_packet["use_case_intent"].get("confidence", "med"),
            source="S1_INTENT"
        )

    # Section 2: Opportunity Shape (from S2 Opportunity)
    opp = intake_packet.get("opportunity_shape", {}).get("value")
    if opp:
        opp_descriptions = {
            "revenue": "Generate new revenue or increase sales",
            "cost": "Reduce costs or improve efficiency",
            "risk": "Mitigate risks or improve compliance",
            "transform": "Transform how the business operates"
        }
        content = opp_descriptions.get(opp, opp.title())
        updated = update_section(
            updated, "section_2", content,
            confidence=intake_packet["opportunity_shape"].get("confidence", "med"),
            source="S2_OPPORTUNITY"
        )

    # Section 3: Operating Context (from S3 Context + S4)
    context_parts = []
    if intake_packet.get("industry", {}).get("value"):
        context_parts.append(f"**Industry:** {intake_packet['industry']['value'].title()}")
    if intake_packet.get("organization_size", {}).get("bucket"):
        context_parts.append(f"**Organization Size:** {intake_packet['organization_size']['bucket']} employees")
    if intake_packet.get("jurisdiction", {}).get("value"):
        context_parts.append(f"**Jurisdiction:** {intake_packet['jurisdiction']['value']}")
    if intake_packet.get("timeline", {}).get("bucket"):
        context_parts.append(f"**Timeline:** {intake_packet['timeline']['bucket']}")
    if intake_packet.get("integration_surface", {}).get("systems"):
        systems = intake_packet["integration_surface"]["systems"]
        context_parts.append(f"**Systems:** {', '.join(systems)}")

    if context_parts:
        # Determine overall confidence (lowest of components)
        confidences = [
            intake_packet.get("industry", {}).get("confidence", "low"),
            intake_packet.get("jurisdiction", {}).get("confidence", "low"),
        ]
        overall_conf = "low" if "low" in confidences else ("med" if "med" in confidences else "high")

        updated = update_section(
            updated, "section_3", "\n".join(context_parts),
            confidence=overall_conf,
            source="S3_CONTEXT"
        )

    # Section 4: What the Agent Would Actually Do (refined progressively)
    if use_case:
        # Start with use case, will be refined by Step 2
        boundaries = intake_packet.get("boundaries", {}).get("value")
        content = use_case
        if boundaries:
            content += f"\n\n**Boundaries:** {boundaries}"
        updated = update_section(
            updated, "section_4", content,
            confidence="med",
            source="S1_INTENT"
        )

    # Section 5: Initial Feasibility & Direction (from Step 0)
    if step_outputs and step_outputs.get("step_0"):
        step0 = step_outputs["step_0"]
        feasibility_parts = []

        if step0.get("go_no_go"):
            feasibility_parts.append(f"**Recommendation:** {step0['go_no_go']}")
        if step0.get("recommended_type"):
            feasibility_parts.append(f"**Suggested Agent Type:** {step0['recommended_type']}")
        if step0.get("rationale"):
            feasibility_parts.append(f"\n{step0['rationale']}")

        if feasibility_parts:
            updated = update_section(
                updated, "section_5", "\n".join(feasibility_parts),
                confidence="high",
                source="S6_RUN_STEP0",
                lock=True  # System-generated, user cannot edit
            )

    # Section 6: Key Risks & Success Factors (from Step 0)
    if step_outputs and step_outputs.get("step_0"):
        step0 = step_outputs["step_0"]
        risk_parts = []

        if step0.get("risk_factors"):
            risk_parts.append("**Risk Factors:**")
            for rf in step0["risk_factors"][:5]:
                risk_parts.append(f"- {rf}")

        if step0.get("success_factors"):
            risk_parts.append("\n**Success Factors:**")
            for sf in step0["success_factors"][:5]:
                risk_parts.append(f"- {sf}")

        if risk_parts:
            updated = update_section(
                updated, "section_6", "\n".join(risk_parts),
                confidence="high",
                source="S6_RUN_STEP0"
            )
        else:
            updated = update_section(
                updated, "section_6", "None identified yet",
                confidence="low",
                source="S6_RUN_STEP0"
            )

    # Section 7: Assumptions & Uncertainties
    if assumptions:
        display_assumptions = format_assumptions_for_display(assumptions, max_display=8)
        assumption_lines = []
        for a in display_assumptions:
            status_icon = "" if a["status"] == "confirmed" else "?"
            assumption_lines.append(
                f"- [{a['id']}] {a['statement']} "
                f"(confidence: {a['confidence']}, impact: {a['impact']}){status_icon}"
            )
        updated = update_section(
            updated, "section_7", "\n".join(assumption_lines),
            confidence="med",
            source="S5_ASSUMPTIONS_CHECK"
        )

    # Section 8: What Happens Next (set at end of flow)
    if step_outputs and step_outputs.get("complete"):
        next_steps = [
            "1. Review the capability mapping and adjust priorities as needed",
            "2. Share the executive brief with stakeholders",
            "3. Use the internal assessment for detailed planning",
            "4. Consider pilot scope based on essential capabilities"
        ]
        updated = update_section(
            updated, "section_8", "\n".join(next_steps),
            confidence="high",
            source="S9_EXPORTS"
        )

    return updated


def render_artifact_md(artifact_doc: ArtifactDoc) -> str:
    """Render artifact document as markdown."""
    lines = [
        "# AI Agent Assessment - 2-Pager",
        "",
        f"*Last updated: {artifact_doc['last_updated']}*",
        "",
        "---",
        ""
    ]

    sections = [
        ("section_1", "1"),
        ("section_2", "2"),
        ("section_3", "3"),
        ("section_4", "4"),
        ("section_5", "5"),
        ("section_6", "6"),
        ("section_7", "7"),
        ("section_8", "8"),
    ]

    for key, num in sections:
        section = artifact_doc.get(key, {})
        title = section.get("title", f"Section {num}")
        content = section.get("content", "")
        confidence = section.get("confidence", "low")
        locked = section.get("locked", False)

        # Confidence indicator
        conf_indicator = {
            "high": "",
            "med": " ⚠️",
            "low": " ❓"
        }.get(confidence, "")

        lock_indicator = " 🔒" if locked else ""

        lines.append(f"## {num}. {title}{conf_indicator}{lock_indicator}")
        lines.append("")
        if content:
            lines.append(content)
        else:
            lines.append("*Not yet captured*")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def render_artifact_html(artifact_doc: ArtifactDoc) -> str:
    """Render artifact document as HTML for display in Streamlit."""
    sections_html = []

    sections = [
        ("section_1", "1", "#3B82F6"),  # blue
        ("section_2", "2", "#F97316"),  # orange
        ("section_3", "3", "#6B7280"),  # gray
        ("section_4", "4", "#14B8A6"),  # teal
        ("section_5", "5", "#A855F7"),  # purple
        ("section_6", "6", "#EF4444"),  # red
        ("section_7", "7", "#F59E0B"),  # amber
        ("section_8", "8", "#10B981"),  # green
    ]

    for key, num, color in sections:
        section = artifact_doc.get(key, {})
        title = section.get("title", f"Section {num}")
        content = section.get("content", "").replace("\n", "<br>")
        confidence = section.get("confidence", "low")

        # Confidence styling
        conf_style = {
            "high": "border-left: 3px solid #10B981;",
            "med": "border-left: 3px solid #F59E0B;",
            "low": "border-left: 3px solid #EF4444;"
        }.get(confidence, "")

        sections_html.append(f"""
        <div style="margin-bottom: 16px; padding: 12px; background: #f9fafb; border-radius: 8px; {conf_style}">
            <div style="font-weight: 600; color: {color}; margin-bottom: 8px;">
                {num}. {title}
            </div>
            <div style="font-size: 14px; color: #374151;">
                {content if content else '<em style="color: #9CA3AF;">Not yet captured</em>'}
            </div>
        </div>
        """)

    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <h3 style="margin-bottom: 16px; color: #111827;">Assessment Summary</h3>
        {''.join(sections_html)}
    </div>
    """


def get_section_completeness(artifact_doc: ArtifactDoc) -> dict:
    """
    Calculate completeness of each section.

    Returns dict with section_key -> percentage complete.
    """
    completeness = {}

    for i in range(1, 9):
        key = f"section_{i}"
        section = artifact_doc.get(key, {})
        content = section.get("content", "")

        if content and len(content) > 10:
            if section.get("confidence") == "high":
                completeness[key] = 100
            elif section.get("confidence") == "med":
                completeness[key] = 75
            else:
                completeness[key] = 50
        else:
            completeness[key] = 0

    return completeness


def get_overall_progress(artifact_doc: ArtifactDoc) -> int:
    """Get overall progress percentage (0-100)."""
    completeness = get_section_completeness(artifact_doc)
    if not completeness:
        return 0
    return int(sum(completeness.values()) / len(completeness))
