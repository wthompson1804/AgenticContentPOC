"""
Judgment Engine Module - Core Judgment extraction, inference, and assumption management.

Per PRD Part 4: Judgment Inventory (CJ01-CJ10)
Per PRD Part 14: Assumption Fix Loop (Dependency Ripple)
"""

import re
from typing import TypedDict, Literal
from datetime import datetime


# Type definitions
ConfidenceLevel = Literal["high", "med", "low"]
SourceType = Literal["asked", "inferred", "user_edit"]
OpportunityShape = Literal["revenue", "cost", "risk", "transform"]
TimelineBucket = Literal["0-3mo", "3-6mo", "6-12mo", "12mo+", "exploratory"]
OrgSizeBucket = Literal["1-50", "51-200", "201-1000", "1001-5000", "5000+", "unknown"]
RiskLevel = Literal["low", "medium", "high"]
AssumptionStatus = Literal["assumed", "confirmed", "corrected", "needs_revalidation"]


class JudgmentValue(TypedDict):
    """Structure for a single judgment value with metadata."""
    value: str | None
    confidence: ConfidenceLevel
    source: SourceType


class Assumption(TypedDict):
    """Structure for an assumption."""
    id: str
    statement: str
    confidence: ConfidenceLevel
    impact: ConfidenceLevel
    needs_confirmation: bool
    status: AssumptionStatus


class IntakePacket(TypedDict, total=False):
    """Full intake packet structure per PRD Part 5.2."""
    industry: JudgmentValue
    use_case_intent: JudgmentValue
    opportunity_shape: JudgmentValue
    jurisdiction: JudgmentValue
    timeline: dict  # bucket + raw
    organization_size: dict  # bucket + raw
    stakeholder_reality: JudgmentValue
    integration_surface: dict  # systems + summary
    risk_posture: dict  # level + worst_case
    boundaries: JudgmentValue


# Core Judgment definitions
CORE_JUDGMENTS = {
    "CJ01": {"name": "Industry", "field": "industry", "criticality": "blocker", "policy": "ask"},
    "CJ02": {"name": "Use case intent", "field": "use_case_intent", "criticality": "blocker", "policy": "ask"},
    "CJ03": {"name": "Opportunity shape", "field": "opportunity_shape", "criticality": "important", "policy": "infer"},
    "CJ04": {"name": "Jurisdiction", "field": "jurisdiction", "criticality": "blocker", "policy": "ask"},
    "CJ05": {"name": "Stakeholder reality", "field": "stakeholder_reality", "criticality": "nice-to-have", "policy": "infer"},
    "CJ06": {"name": "Timeline", "field": "timeline", "criticality": "important", "policy": "infer"},
    "CJ07": {"name": "Org scale", "field": "organization_size", "criticality": "important", "policy": "infer"},
    "CJ08": {"name": "Integration surface", "field": "integration_surface", "criticality": "important", "policy": "infer"},
    "CJ09": {"name": "Risk posture", "field": "risk_posture", "criticality": "important", "policy": "infer"},
    "CJ10": {"name": "Confirmed agent type", "field": "confirmed_type", "criticality": "blocker", "policy": "confirm"},
}

# Industry keywords for extraction
INDUSTRY_KEYWORDS = {
    "healthcare": ["health", "medical", "hospital", "patient", "clinical", "pharma", "drug"],
    "finance": ["bank", "financial", "trading", "investment", "insurance", "fintech", "payment"],
    "manufacturing": ["manufactur", "factory", "production", "assembly", "industrial"],
    "retail": ["retail", "ecommerce", "e-commerce", "shop", "store", "consumer"],
    "technology": ["tech", "software", "saas", "platform", "app", "digital"],
    "energy": ["energy", "utility", "power", "electric", "oil", "gas", "renewable"],
    "logistics": ["logistics", "supply chain", "shipping", "transport", "warehouse"],
    "education": ["education", "learning", "school", "university", "training"],
    "government": ["government", "public sector", "federal", "municipal", "civic"],
    "agriculture": ["agriculture", "farming", "crop", "livestock", "agri"],
}

# Opportunity shape keywords
OPPORTUNITY_KEYWORDS = {
    "revenue": ["revenue", "sales", "growth", "monetize", "profit", "income", "sell"],
    "cost": ["cost", "save", "efficiency", "reduce", "automate", "streamline", "cut"],
    "risk": ["risk", "compliance", "security", "protect", "prevent", "safety", "audit"],
    "transform": ["transform", "innovate", "disrupt", "reimagine", "new way", "change"],
}

# Regulated industries (triggers risk branch)
REGULATED_INDUSTRIES = ["healthcare", "finance", "government", "energy"]


def init_intake_packet() -> IntakePacket:
    """Initialize empty intake packet."""
    return {
        "industry": {"value": None, "confidence": "low", "source": "inferred"},
        "use_case_intent": {"value": None, "confidence": "low", "source": "inferred"},
        "opportunity_shape": {"value": None, "confidence": "low", "source": "inferred"},
        "jurisdiction": {"value": None, "confidence": "low", "source": "inferred"},
        "timeline": {"bucket": None, "raw": None, "confidence": "low", "source": "inferred"},
        "organization_size": {"bucket": None, "raw": None, "confidence": "low", "source": "inferred"},
        "stakeholder_reality": {"value": None, "confidence": "low", "source": "inferred"},
        "integration_surface": {"systems": [], "summary": None, "confidence": "low", "source": "inferred"},
        "risk_posture": {"level": None, "worst_case": None, "confidence": "low", "source": "inferred"},
        "boundaries": {"value": None, "confidence": "low", "source": "inferred"},
    }


def extract_industry(text: str) -> tuple[str | None, ConfidenceLevel]:
    """Extract industry from text using keyword matching."""
    text_lower = text.lower()

    matches = []
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                matches.append(industry)
                break

    if len(matches) == 1:
        return matches[0], "high"
    elif len(matches) > 1:
        return matches[0], "med"  # Ambiguous, return first match
    return None, "low"


def extract_opportunity_shape(text: str) -> tuple[OpportunityShape | None, ConfidenceLevel]:
    """Extract opportunity shape from text."""
    text_lower = text.lower()

    scores = {shape: 0 for shape in OPPORTUNITY_KEYWORDS}
    for shape, keywords in OPPORTUNITY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[shape] += 1

    max_score = max(scores.values())
    if max_score == 0:
        return None, "low"

    winner = max(scores, key=scores.get)
    confidence = "high" if max_score >= 2 else "med"
    return winner, confidence


def extract_jurisdiction(text: str) -> tuple[str | None, ConfidenceLevel]:
    """Extract jurisdiction from text."""
    text_lower = text.lower()

    # Common jurisdiction patterns
    jurisdictions = {
        "US": ["united states", "usa", "u.s.", "america", "federal"],
        "EU": ["europe", "european union", "eu", "gdpr"],
        "UK": ["united kingdom", "uk", "britain", "england"],
        "global": ["global", "worldwide", "international", "multi-jurisdictional"],
        "Canada": ["canada", "canadian"],
        "Australia": ["australia", "australian"],
        "Germany": ["germany", "german"],
        "Singapore": ["singapore"],
    }

    for jurisdiction, keywords in jurisdictions.items():
        for kw in keywords:
            if kw in text_lower:
                return jurisdiction, "high"

    return None, "low"


def extract_timeline(text: str) -> tuple[TimelineBucket | None, str | None, ConfidenceLevel]:
    """Extract timeline from text."""
    text_lower = text.lower()

    # Look for explicit time mentions
    if any(x in text_lower for x in ["poc", "proof of concept", "1-3 month", "quick", "pilot"]):
        return "0-3mo", "POC/Pilot", "high"
    elif any(x in text_lower for x in ["3-6 month", "pilot project", "trial"]):
        return "3-6mo", "Pilot", "high"
    elif any(x in text_lower for x in ["6-12 month", "production", "deploy", "rollout"]):
        return "6-12mo", "Production", "high"
    elif any(x in text_lower for x in ["year", "long term", "scale", "enterprise"]):
        return "12mo+", "Long-term", "med"
    elif any(x in text_lower for x in ["exploring", "research", "investigate", "feasibility"]):
        return "exploratory", "Exploratory", "med"

    return None, None, "low"


def extract_org_size(text: str) -> tuple[OrgSizeBucket | None, str | None, ConfidenceLevel]:
    """Extract organization size from text."""
    text_lower = text.lower()

    # Look for size indicators
    if any(x in text_lower for x in ["startup", "small team", "5 people", "10 people"]):
        return "1-50", "Small/Startup", "med"
    elif any(x in text_lower for x in ["mid-size", "medium", "growing", "100 people", "200 people"]):
        return "51-200", "Mid-size", "med"
    elif any(x in text_lower for x in ["large", "enterprise", "1000", "thousand", "corporation"]):
        return "1001-5000", "Large", "med"
    elif any(x in text_lower for x in ["fortune 500", "multinational", "global company", "10000"]):
        return "5000+", "Enterprise", "med"

    return None, None, "low"


def infer_risk_posture(intake_packet: IntakePacket) -> tuple[RiskLevel | None, ConfidenceLevel]:
    """Infer risk posture from industry and other factors."""
    industry = intake_packet.get("industry", {}).get("value")

    if industry and industry.lower() in REGULATED_INDUSTRIES:
        return "high", "med"

    # Check use case for risk keywords
    use_case = intake_packet.get("use_case_intent", {}).get("value", "")
    if use_case:
        use_case_lower = use_case.lower()
        if any(x in use_case_lower for x in ["autonom", "decision", "approve", "critical"]):
            return "high", "med"
        elif any(x in use_case_lower for x in ["assist", "recommend", "suggest", "support"]):
            return "low", "med"

    return "medium", "low"


def is_regulated_domain(intake_packet: IntakePacket) -> bool:
    """Check if this is a regulated domain (triggers risk branch)."""
    industry = intake_packet.get("industry", {}).get("value")
    return industry and industry.lower() in REGULATED_INDUSTRIES


def extract_systems(text: str) -> list[str]:
    """Extract mentioned systems/integrations from text."""
    systems = []
    text_lower = text.lower()

    # Common system keywords
    system_patterns = [
        (r"salesforce", "Salesforce"),
        (r"sap", "SAP"),
        (r"oracle", "Oracle"),
        (r"workday", "Workday"),
        (r"servicenow", "ServiceNow"),
        (r"slack", "Slack"),
        (r"jira", "Jira"),
        (r"confluence", "Confluence"),
        (r"sharepoint", "SharePoint"),
        (r"dynamics", "Microsoft Dynamics"),
        (r"hubspot", "HubSpot"),
        (r"zendesk", "Zendesk"),
        (r"erp", "ERP System"),
        (r"crm", "CRM System"),
        (r"database", "Database"),
        (r"api", "API Integration"),
    ]

    for pattern, name in system_patterns:
        if re.search(pattern, text_lower):
            if name not in systems:
                systems.append(name)

    return systems


def update_judgments(
    chat_history: list[dict],
    intake_packet: IntakePacket,
    changed_field: str | None = None
) -> tuple[IntakePacket, list[Assumption], list[str]]:
    """
    Update judgments based on chat history.

    Per PRD Part 14: If a Core Judgment is modified, re-evaluate dependent inferences.

    Args:
        chat_history: List of chat messages
        intake_packet: Current intake packet
        changed_field: Field that was changed (for dependency ripple)

    Returns:
        Tuple of (updated_intake_packet, assumptions, open_questions)
    """
    updated = intake_packet.copy()
    assumptions = []
    open_questions = []

    # Concatenate all user messages for extraction
    user_text = " ".join([
        msg["content"] for msg in chat_history
        if msg.get("role") == "user"
    ])

    # Extract judgments from text if not already set
    # CJ01: Industry
    if not updated.get("industry", {}).get("value"):
        industry, conf = extract_industry(user_text)
        if industry:
            updated["industry"] = {"value": industry, "confidence": conf, "source": "inferred"}

    # CJ02: Use case intent (usually from first user message)
    if not updated.get("use_case_intent", {}).get("value"):
        for msg in chat_history:
            if msg.get("role") == "user" and len(msg.get("content", "")) > 20:
                updated["use_case_intent"] = {
                    "value": msg["content"][:500],  # First substantial message
                    "confidence": "med",
                    "source": "inferred"
                }
                break

    # CJ03: Opportunity shape
    if not updated.get("opportunity_shape", {}).get("value"):
        opp, conf = extract_opportunity_shape(user_text)
        if opp:
            updated["opportunity_shape"] = {"value": opp, "confidence": conf, "source": "inferred"}

    # CJ04: Jurisdiction
    if not updated.get("jurisdiction", {}).get("value"):
        jur, conf = extract_jurisdiction(user_text)
        if jur:
            updated["jurisdiction"] = {"value": jur, "confidence": conf, "source": "inferred"}

    # CJ06: Timeline
    if not updated.get("timeline", {}).get("bucket"):
        bucket, raw, conf = extract_timeline(user_text)
        if bucket:
            updated["timeline"] = {"bucket": bucket, "raw": raw, "confidence": conf, "source": "inferred"}

    # CJ07: Org size
    if not updated.get("organization_size", {}).get("bucket"):
        bucket, raw, conf = extract_org_size(user_text)
        if bucket:
            updated["organization_size"] = {"bucket": bucket, "raw": raw, "confidence": conf, "source": "inferred"}

    # CJ08: Integration surface
    systems = extract_systems(user_text)
    if systems and not updated.get("integration_surface", {}).get("systems"):
        updated["integration_surface"] = {
            "systems": systems,
            "summary": f"Integrates with: {', '.join(systems)}",
            "confidence": "med",
            "source": "inferred"
        }

    # CJ09: Risk posture (inferred from industry)
    if not updated.get("risk_posture", {}).get("level"):
        risk_level, conf = infer_risk_posture(updated)
        if risk_level:
            updated["risk_posture"] = {
                "level": risk_level,
                "worst_case": None,
                "confidence": conf,
                "source": "inferred"
            }

    # Dependency ripple: If core judgment changed, re-evaluate dependents
    CORE_JUDGMENT_FIELDS = ["industry", "use_case_intent", "jurisdiction", "opportunity_shape"]
    if changed_field and changed_field in CORE_JUDGMENT_FIELDS:
        # Re-infer risk posture if industry changed
        if changed_field == "industry":
            risk_level, conf = infer_risk_posture(updated)
            updated["risk_posture"] = {
                "level": risk_level,
                "worst_case": updated.get("risk_posture", {}).get("worst_case"),
                "confidence": conf,
                "source": "inferred"
            }
            # Mark related assumptions for revalidation
            for a in assumptions:
                if "industry" in a["statement"].lower() or "risk" in a["statement"].lower():
                    a["status"] = "needs_revalidation"

    # Generate assumptions for inferred values
    assumption_id = 1
    for field, judgment in updated.items():
        if isinstance(judgment, dict) and judgment.get("source") == "inferred":
            value = judgment.get("value") or judgment.get("bucket") or judgment.get("level")
            if value and judgment.get("confidence") in ["med", "low"]:
                assumptions.append({
                    "id": f"A{assumption_id}",
                    "statement": f"{field.replace('_', ' ').title()} is {value}",
                    "confidence": judgment.get("confidence", "low"),
                    "impact": "high" if field in ["industry", "jurisdiction", "use_case_intent"] else "med",
                    "needs_confirmation": judgment.get("confidence") == "low",
                    "status": "assumed"
                })
                assumption_id += 1

    # Identify open questions (blockers with no value)
    for cj_id, cj_info in CORE_JUDGMENTS.items():
        field = cj_info["field"]
        if cj_info["criticality"] == "blocker":
            field_data = updated.get(field, {})
            value = field_data.get("value") or field_data.get("bucket")
            if not value:
                open_questions.append(cj_id)

    return updated, assumptions, open_questions


def build_use_case_context_blob(
    intake_packet: IntakePacket,
    artifact_doc: dict,
    assumptions: list[Assumption]
) -> str:
    """
    Build context blob to inject into {use_case} placeholder.

    Per PRD Part 13.2: Pack rich context into single placeholder.
    """
    lines = []

    # Section 1: Objective
    use_case = intake_packet.get("use_case_intent", {}).get("value", "Not specified")
    lines.append(f"**Objective:** {use_case}")
    lines.append("")

    # Section 2: Opportunity Type
    opp = intake_packet.get("opportunity_shape", {}).get("value", "Not specified")
    lines.append(f"**Opportunity Type:** {opp}")
    lines.append("")

    # Section 4: Agent Behavior (from artifact if available)
    if artifact_doc and artifact_doc.get("section_4"):
        lines.append("**Agent Behavior (draft):**")
        lines.append(artifact_doc["section_4"].get("content", "To be determined"))
        if artifact_doc["section_4"].get("boundaries"):
            lines.append(f"- Boundary: {artifact_doc['section_4']['boundaries']}")
    lines.append("")

    # Integration Surface
    integration = intake_packet.get("integration_surface", {})
    if integration.get("systems"):
        lines.append(f"**Integration Surface:** {', '.join(integration['systems'])}")
        lines.append("")

    # Key Assumptions (top 3 by impact)
    if assumptions:
        high_impact = [a for a in assumptions if a["impact"] == "high"][:3]
        if high_impact:
            lines.append("**Key Assumptions:**")
            for a in high_impact:
                lines.append(f"- [{a['id']}]: {a['statement']} (confidence: {a['confidence']}, impact: {a['impact']})")

    return "\n".join(lines)


def get_blocker_status(intake_packet: IntakePacket) -> dict:
    """
    Check which blocker judgments are satisfied.

    Returns dict with CJ ID -> bool (True if satisfied).
    """
    status = {}
    for cj_id, cj_info in CORE_JUDGMENTS.items():
        if cj_info["criticality"] == "blocker":
            field = cj_info["field"]
            field_data = intake_packet.get(field, {})
            value = field_data.get("value") or field_data.get("bucket")
            status[cj_id] = bool(value)
    return status


def can_proceed_to_research(intake_packet: IntakePacket) -> tuple[bool, list[str]]:
    """
    Check if we have enough information to proceed to Step 0 (Research).

    Per PRD: CJ01 (Industry), CJ02 (Use case), CJ04 (Jurisdiction) are blockers.

    Returns:
        Tuple of (can_proceed, missing_fields)
    """
    required = ["CJ01", "CJ02", "CJ04"]
    blocker_status = get_blocker_status(intake_packet)

    missing = [cj for cj in required if not blocker_status.get(cj, False)]
    return len(missing) == 0, missing


def format_assumptions_for_display(assumptions: list[Assumption], max_display: int = 8) -> list[dict]:
    """
    Format assumptions for UI display.

    Per PRD Part 9.1 Section 7: Max 8 displayed, sorted by impact × uncertainty.
    """
    # Score assumptions: high impact + low confidence = highest priority
    def score(a: Assumption) -> int:
        impact_score = {"high": 3, "med": 2, "low": 1}.get(a["impact"], 1)
        # Invert confidence: low confidence = high score
        conf_score = {"low": 3, "med": 2, "high": 1}.get(a["confidence"], 1)
        return impact_score * conf_score

    sorted_assumptions = sorted(assumptions, key=score, reverse=True)
    return sorted_assumptions[:max_display]
