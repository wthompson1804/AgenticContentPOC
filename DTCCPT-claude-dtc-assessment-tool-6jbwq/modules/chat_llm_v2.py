"""
Chat LLM Module v2 - Per-State Prompting Architecture.

Designed to work with all Claude model tiers (Opus, Sonnet, Haiku).
Uses simple, focused prompts that even smaller models can handle reliably.
"""

import os
import json
import re
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


@dataclass
class ProcessResult:
    """Result from processing a state."""
    extracted: dict
    next_state: str
    system_response: str
    intake_packet_updates: dict
    assumptions: list
    debug_info: dict  # For troubleshooting


def get_chat_client(model: str = "claude-sonnet-4-20250514", api_key: Optional[str] = None):
    """Get Claude client for chat inference."""
    if not LANGCHAIN_AVAILABLE:
        return None

    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None

    return ChatAnthropic(
        model=model,
        api_key=key,
        max_tokens=1024,
        temperature=0.1,  # Very low for deterministic extraction
    )


# =============================================================================
# SIMPLE PROMPTS - Designed to work with all model tiers
# =============================================================================

# These prompts are deliberately simple and explicit
# CRITICAL: Each prompt now asks for REASONING to preserve context handoff
SIMPLE_PROMPTS = {
    "extract_intent": """Extract information from this user message about their AI agent project.

USER MESSAGE: {user_message}

{prior_context}

Return ONLY a JSON object with these fields:
- "summary": A 1-2 sentence summary of what they want (string)
- "industry": The industry/sector mentioned (string or null). Examples: hospitality, healthcare, retail, finance, manufacturing, technology, education, logistics
- "needs_more_info": true if the message is too vague to understand, false otherwise
- "reasoning": 2-3 sentences explaining WHY you interpreted it this way, what signals you picked up on, and what might be important for downstream processing

IMPORTANT INDUSTRY HINTS:
- banquet, catering, hotel, restaurant, event, wedding, venue, food → "hospitality"
- medical, hospital, clinic, patient, health → "healthcare"
- store, shop, retail, merchandise → "retail"
- bank, financial, investment, trading, insurance → "finance"
- factory, production, manufacturing → "manufacturing"
- software, app, platform, tech, developer → "technology"

JSON response:""",

    "extract_opportunity": """The user wants to: {use_case_summary}

{prior_context}

What is their PRIMARY goal? Pick ONE:
- "revenue" = make money, increase sales, grow business
- "cost" = save money, reduce time, improve efficiency
- "risk" = reduce risk, compliance, prevent problems
- "transform" = fundamentally change operations

Return ONLY a JSON object:
{{"goal": "<one of the four options>", "reason": "<brief explanation>", "reasoning": "<2-3 sentences on WHY this goal fits and what it means for the agent design>"}}

JSON response:""",

    "extract_context": """The user's project: {use_case_summary}
Industry: {industry}

{prior_context}

From their latest message, extract any business context mentioned.

USER MESSAGE: {user_message}

Return ONLY a JSON object with these fields (use null if not mentioned):
- "location": Where does this operate? (country, region, or "global")
- "org_size": Organization size (small/medium/large/enterprise)
- "timeline": How urgent? (urgent/near-term/standard/exploratory)
- "stakeholders": Who would use this and who needs to approve? (object with "users" and "approvers" fields, or null)
- "systems": List of existing systems/tools mentioned, or empty list
- "reasoning": 2-3 sentences capturing the nuance of their operating context that might affect agent design

JSON response:""",

    "extract_location": """From the user's message, extract where their project operates.

USER MESSAGE: {user_message}

Return ONLY a JSON object:
{{"location": "<country, region, or global>", "reasoning": "<brief note on regulatory implications>"}}

If they mention multiple locations, pick the primary one or say "multi-region".

JSON response:""",

    "extract_org_size": """From the user's message, extract their organization size.

USER MESSAGE: {user_message}

Return ONLY a JSON object:
{{"org_size": "<small/medium/large/enterprise>", "employee_count": "<number if mentioned, else null>", "reasoning": "<brief note>"}}

Guidelines:
- small = under 50 employees or startup
- medium = 50-500 employees or SMB
- large = 500-5000 employees
- enterprise = 5000+ employees or Fortune 500

JSON response:""",

    "extract_timeline": """From the user's message, extract their timeline/urgency.

USER MESSAGE: {user_message}

Return ONLY a JSON object:
{{"timeline": "<exploratory/near-term/urgent>", "raw_timeframe": "<what they actually said>", "reasoning": "<brief note>"}}

Guidelines for categorization:
- "urgent" = need this within 1 month (weeks, ASAP, this month, critical)
- "near-term" = want to pilot in the next 1-6 months (1-2 quarters, next quarter, few months, soon)
- "exploratory" = 6+ months out or no concrete timeline (this year, next year, eventually, researching)

Time expression hints:
- "2 quarters" = 6 months = near-term
- "1 quarter" = 3 months = near-term
- "next year" = 12+ months = exploratory
- "this quarter" = 1-3 months = near-term
- "this month" or "next month" = urgent

JSON response:""",

    "extract_stakeholders": """From the user's message, extract who would use this system and who needs to approve it.

USER MESSAGE: {user_message}

Return ONLY a JSON object:
{{"users": "<who would use this day-to-day>", "approvers": "<who needs to sign off>", "reasoning": "<brief note on org dynamics>"}}

Use null for fields not mentioned.

JSON response:""",

    "extract_risk": """Project: {use_case_summary}
Industry: {industry}

{prior_context}

Assess the risk level based on industry norms.

What happens if this AI agent makes mistakes? Consider:
- Patient safety (healthcare) = high risk
- Financial loss (finance) = high risk
- Reputation damage = medium risk
- Minor inconvenience = low risk

For HOSPITALITY (hotels, restaurants, events, banquets):
- Booking errors = medium risk (inconvenience, possible lost revenue)
- Not high risk unless handling payments or sensitive data

Return ONLY a JSON object:
{{"risk_level": "low" or "medium" or "high", "reason": "<brief explanation>", "reasoning": "<2-3 sentences capturing the specific failure modes and their impact for THIS use case>"}}

JSON response:"""
}


# =============================================================================
# CONVERSATIONAL RESPONSES - Natural Claude-style messages with examples
# Using predictive maintenance as the running example for consistency
# =============================================================================

RESPONSES = {
    "S1_NEED_MORE": (
        "I'd love to help, but I need a bit more detail. What specific problem are you "
        "trying to solve?\n\n"
        "_Example: \"I want to predict when our factory machines will need maintenance "
        "before they break down.\"_"
    ),
    "S2_OPPORTUNITY": (
        "Got it! What would success look like for you? Are you mainly trying to:\n\n"
        "- **Grow revenue** (sell more, reach more customers)\n"
        "- **Save money or time** (efficiency, automation)\n"
        "- **Reduce risk** (errors, compliance, safety)\n"
        "- **Transform operations** (fundamentally change how you work)\n\n"
        "_Example: \"Mainly saving money — avoiding unplanned downtime and emergency repairs.\"_"
    ),
    # Split S3 into focused questions to reduce cognitive load
    "S3_LOCATION": (
        "Where does this operate? (country, region, or global)\n\n"
        "_Example: \"Three manufacturing plants in the Midwest US.\"_"
    ),
    "S3_ORG_SIZE": (
        "Roughly how big is your organization?\n\n"
        "_Example: \"About 200 employees across three locations.\"_"
    ),
    "S3_TIMELINE": (
        "What's your timeline? Are you:\n"
        "- **Exploring** (early research)\n"
        "- **Near-term** (want to pilot in the next few months)\n"
        "- **Urgent** (need this soon)\n\n"
        "_Example: \"We want to pilot this in the next quarter.\"_"
    ),
    "S3_STAKEHOLDERS": (
        "Who would use this day-to-day, and who needs to approve it?\n\n"
        "_Example: \"The maintenance team would use it, and our VP of Operations "
        "would need to sign off.\"_"
    ),
    # Legacy - kept for backwards compatibility
    "S3_CONTEXT": (
        "Where does this operate? (country, region, or global)\n\n"
        "_Example: \"Three manufacturing plants in the Midwest US.\"_"
    ),
    "S4_INTEGRATION": (
        "Will this agent need to connect to any existing systems?\n\n"
        "Things like: CRM, calendar, payment processor, inventory system, databases, "
        "sensors, ERP, etc.\n\n"
        "_Example: \"Our machines have sensors feeding into a SCADA system, and we use "
        "SAP for maintenance scheduling.\"_"
    ),
    "S4_RISK": (
        "Last question: If the agent made a mistake, what's the worst that could happen?\n\n"
        "_Example: \"If it misses a prediction, a machine could fail unexpectedly — "
        "that's costly but not dangerous since we have safety shutoffs.\"_"
    ),
}


# =============================================================================
# MAIN PROCESSING FUNCTION
# =============================================================================

def process_state(
    current_state: str,
    user_message: str,
    intake_packet: dict,
    chat_history: list,
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None,
    context_handoff: Optional[dict] = None
) -> dict:
    """
    Process a single state with a simple, focused LLM call.

    Designed to work reliably with Opus, Sonnet, AND Haiku.

    Args:
        current_state: Current state machine state
        user_message: User's message
        intake_packet: Accumulated structured data
        chat_history: Chat history for reference
        model: Claude model to use
        api_key: API key
        context_handoff: Optional context handoff document for preserving reasoning across stages

    Returns:
        dict with extracted data, next_state, system_response, and context updates
    """
    debug_info = {
        "state": current_state,
        "model": model,
        "llm_called": False,
        "llm_response": None,
        "parse_success": False,
        "fallback_used": False,
        "error": None,
        "reasoning": None  # Capture reasoning for context handoff
    }

    # Build prior context from handoff if available
    prior_context = ""
    if context_handoff:
        from modules.context_handoff import ContextHandoff
        if isinstance(context_handoff, dict):
            handoff = ContextHandoff.from_dict(context_handoff)
        else:
            handoff = context_handoff
        prior_context = f"\n## Prior Context\n{handoff.get_briefing(current_state)}\n"

    client = get_chat_client(model, api_key)

    if not client:
        debug_info["error"] = "No API client (missing key or langchain)"
        debug_info["fallback_used"] = True
        return _keyword_fallback(current_state, user_message, intake_packet, debug_info)

    # Route to appropriate handler based on state
    try:
        if current_state in ["S0_ENTRY", "S1_INTENT"]:
            return _handle_intent_state(client, user_message, intake_packet, debug_info, prior_context)
        elif current_state == "S2_OPPORTUNITY":
            return _handle_opportunity_state(client, user_message, intake_packet, debug_info, prior_context)
        # Split S3 states for reduced cognitive load
        elif current_state in ["S3_CONTEXT", "S3_LOCATION"]:
            return _handle_location_state(client, user_message, intake_packet, debug_info, prior_context)
        elif current_state == "S3_ORG_SIZE":
            return _handle_org_size_state(client, user_message, intake_packet, debug_info, prior_context)
        elif current_state == "S3_TIMELINE":
            return _handle_timeline_state(client, user_message, intake_packet, debug_info, prior_context)
        elif current_state == "S3_STAKEHOLDERS":
            return _handle_stakeholders_state(client, user_message, intake_packet, debug_info, prior_context)
        elif current_state == "S4_INTEGRATION":
            return _handle_integration_state(client, user_message, intake_packet, debug_info, prior_context)
        elif current_state in ["S4_INTEGRATION_RISK", "S4_RISK"]:
            return _handle_risk_state(client, user_message, intake_packet, debug_info, prior_context)
        elif current_state == "S5_ASSUMPTIONS_CHECK":
            return _handle_assumptions_state(user_message, intake_packet, debug_info)
        else:
            # Unknown state - try generic extraction
            return _handle_intent_state(client, user_message, intake_packet, debug_info, prior_context)
    except Exception as e:
        debug_info["error"] = str(e)
        debug_info["fallback_used"] = True
        return _keyword_fallback(current_state, user_message, intake_packet, debug_info)


def _call_llm(client, prompt: str, debug_info: dict) -> Optional[str]:
    """Make LLM call and return response content."""
    debug_info["llm_called"] = True

    try:
        response = client.invoke([
            SystemMessage(content="You are a helpful assistant. Respond with valid JSON only."),
            HumanMessage(content=prompt)
        ])
        debug_info["llm_response"] = response.content[:500]  # Truncate for debug
        return response.content
    except Exception as e:
        debug_info["error"] = f"LLM call failed: {e}"
        return None


def _parse_json(content: str, debug_info: dict) -> Optional[dict]:
    """Parse JSON from LLM response with multiple fallback strategies."""
    if not content:
        return None

    content = content.strip()

    # Strategy 1: Direct parse
    try:
        result = json.loads(content)
        debug_info["parse_success"] = True
        return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: Remove markdown code blocks
    if "```" in content:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if match:
            try:
                result = json.loads(match.group(1))
                debug_info["parse_success"] = True
                return result
            except json.JSONDecodeError:
                pass

    # Strategy 3: Find JSON object in content
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(content[start:end])
            debug_info["parse_success"] = True
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 4: Try to extract key-value pairs manually
    extracted = {}

    # Look for "summary": "..." pattern
    summary_match = re.search(r'"summary"\s*:\s*"([^"]+)"', content)
    if summary_match:
        extracted["summary"] = summary_match.group(1)

    # Look for "industry": "..." pattern
    industry_match = re.search(r'"industry"\s*:\s*"([^"]+)"', content)
    if industry_match:
        extracted["industry"] = industry_match.group(1)

    # Look for "goal": "..." pattern
    goal_match = re.search(r'"goal"\s*:\s*"([^"]+)"', content)
    if goal_match:
        extracted["goal"] = goal_match.group(1)

    if extracted:
        debug_info["parse_success"] = True
        debug_info["parse_method"] = "regex_extraction"
        return extracted

    return None


# =============================================================================
# STATE HANDLERS
# =============================================================================

def _handle_intent_state(client, user_message: str, intake_packet: dict, debug_info: dict, prior_context: str = "") -> dict:
    """Handle S0_ENTRY and S1_INTENT states."""

    prompt = SIMPLE_PROMPTS["extract_intent"].format(
        user_message=user_message,
        prior_context=prior_context
    )
    response = _call_llm(client, prompt, debug_info)
    extracted = _parse_json(response, debug_info) if response else None

    updates = {}
    next_state = "S1_INTENT"  # Default: stay
    system_response = None

    if extracted:
        # Capture reasoning for context handoff
        if extracted.get("reasoning"):
            debug_info["reasoning"] = extracted["reasoning"]

        # Got LLM extraction
        if extracted.get("summary"):
            updates["use_case_intent"] = {
                "value": extracted["summary"],
                "confidence": "high",
                "source": "llm_extracted",
                "reasoning": extracted.get("reasoning", "")
            }
            updates["use_case_synthesized"] = extracted["summary"]

        if extracted.get("industry"):
            # Validate LLM industry against keyword detection
            # Keyword detection is more reliable for explicit mentions like "banquet halls"
            llm_industry = _normalize_industry(extracted["industry"])
            keyword_industry = _detect_industry(user_message)

            # CRITICAL: If keyword detection finds a different industry, prefer it
            # This prevents LLM hallucinations (e.g., "energy" for "banquet halls")
            if keyword_industry and keyword_industry != llm_industry:
                industry = keyword_industry
                confidence = "high"
                source = "keyword_override"
                debug_info["industry_override"] = f"LLM said '{llm_industry}', keywords found '{keyword_industry}'"
            elif llm_industry:
                industry = llm_industry
                confidence = "high"
                source = "llm_extracted"
            else:
                industry = keyword_industry
                confidence = "med" if keyword_industry else "low"
                source = "keyword_match" if keyword_industry else "unknown"

            if industry:
                updates["industry"] = {
                    "value": industry,
                    "confidence": confidence,
                    "source": source
                }

        # Determine next action
        if extracted.get("needs_more_info"):
            system_response = RESPONSES["S1_NEED_MORE"]
        else:
            next_state = "S2_OPPORTUNITY"
            system_response = RESPONSES["S2_OPPORTUNITY"]
    else:
        # LLM failed - use keyword extraction
        debug_info["fallback_used"] = True

        updates["use_case_intent"] = {
            "value": user_message,
            "confidence": "low",
            "source": "user_direct"
        }

        industry = _detect_industry(user_message)
        if industry:
            updates["industry"] = {
                "value": industry,
                "confidence": "med",
                "source": "keyword_match"
            }

        next_state = "S2_OPPORTUNITY"
        system_response = RESPONSES["S2_OPPORTUNITY"]

    return {
        "extracted": extracted or {},
        "next_state": next_state,
        "system_response": system_response,
        "intake_packet_updates": updates,
        "assumptions": [],
        "debug_info": debug_info
    }


def _handle_opportunity_state(client, user_message: str, intake_packet: dict, debug_info: dict, prior_context: str = "") -> dict:
    """Handle S2_OPPORTUNITY state."""

    use_case = intake_packet.get("use_case_intent", {}).get("value", user_message)
    prompt = SIMPLE_PROMPTS["extract_opportunity"].format(
        use_case_summary=use_case,
        prior_context=prior_context
    )
    response = _call_llm(client, prompt, debug_info)
    extracted = _parse_json(response, debug_info) if response else None

    updates = {}

    if extracted:
        # Capture reasoning for context handoff
        if extracted.get("reasoning"):
            debug_info["reasoning"] = extracted["reasoning"]

        if extracted.get("goal"):
            goal = extracted["goal"].lower()
            if goal in ["revenue", "cost", "risk", "transform"]:
                updates["opportunity_shape"] = {
                    "value": goal,
                    "confidence": "high",
                    "source": "llm_extracted",
                    "reasoning": extracted.get("reasoning", "")
                }
    else:
        # Keyword fallback
        debug_info["fallback_used"] = True
        goal = _detect_opportunity(user_message)
        if goal:
            updates["opportunity_shape"] = {
                "value": goal,
                "confidence": "med",
                "source": "keyword_match"
            }

    return {
        "extracted": extracted or {},
        "next_state": "S3_LOCATION",
        "system_response": RESPONSES["S3_LOCATION"],
        "intake_packet_updates": updates,
        "assumptions": [],
        "debug_info": debug_info
    }


def _handle_location_state(client, user_message: str, intake_packet: dict, debug_info: dict, prior_context: str = "") -> dict:
    """Handle S3_LOCATION state - asks where this operates."""

    prompt = SIMPLE_PROMPTS["extract_location"].format(user_message=user_message)
    response = _call_llm(client, prompt, debug_info)
    extracted = _parse_json(response, debug_info) if response else None

    updates = {}

    if extracted:
        if extracted.get("reasoning"):
            debug_info["reasoning"] = extracted["reasoning"]
        if extracted.get("location"):
            updates["jurisdiction"] = {
                "value": extracted["location"],
                "confidence": "high",
                "source": "llm_extracted"
            }
    else:
        # Keyword fallback for common locations
        debug_info["fallback_used"] = True
        location = _detect_location(user_message)
        if location:
            updates["jurisdiction"] = {
                "value": location,
                "confidence": "med",
                "source": "keyword_match"
            }

    return {
        "extracted": extracted or {},
        "next_state": "S3_ORG_SIZE",
        "system_response": RESPONSES["S3_ORG_SIZE"],
        "intake_packet_updates": updates,
        "assumptions": [],
        "debug_info": debug_info
    }


def _handle_org_size_state(client, user_message: str, intake_packet: dict, debug_info: dict, prior_context: str = "") -> dict:
    """Handle S3_ORG_SIZE state - asks about organization size."""

    prompt = SIMPLE_PROMPTS["extract_org_size"].format(user_message=user_message)
    response = _call_llm(client, prompt, debug_info)
    extracted = _parse_json(response, debug_info) if response else None

    updates = {}

    if extracted:
        if extracted.get("reasoning"):
            debug_info["reasoning"] = extracted["reasoning"]
        if extracted.get("org_size"):
            updates["organization_size"] = {
                "bucket": extracted["org_size"],
                "employee_count": extracted.get("employee_count"),
                "confidence": "high",
                "source": "llm_extracted"
            }
    else:
        # Keyword fallback
        debug_info["fallback_used"] = True
        org_size = _detect_org_size(user_message)
        if org_size:
            updates["organization_size"] = {
                "bucket": org_size,
                "confidence": "med",
                "source": "keyword_match"
            }

    return {
        "extracted": extracted or {},
        "next_state": "S3_TIMELINE",
        "system_response": RESPONSES["S3_TIMELINE"],
        "intake_packet_updates": updates,
        "assumptions": [],
        "debug_info": debug_info
    }


def _handle_timeline_state(client, user_message: str, intake_packet: dict, debug_info: dict, prior_context: str = "") -> dict:
    """Handle S3_TIMELINE state - asks about timeline/urgency."""

    prompt = SIMPLE_PROMPTS["extract_timeline"].format(user_message=user_message)
    response = _call_llm(client, prompt, debug_info)
    extracted = _parse_json(response, debug_info) if response else None

    updates = {}

    if extracted:
        if extracted.get("reasoning"):
            debug_info["reasoning"] = extracted["reasoning"]
        if extracted.get("timeline"):
            updates["timeline"] = {
                "bucket": extracted["timeline"],
                "raw": extracted.get("raw_timeframe", user_message),  # Preserve what they actually said
                "confidence": "high",
                "source": "llm_extracted"
            }
    else:
        # Keyword fallback
        debug_info["fallback_used"] = True
        timeline = _detect_timeline(user_message)
        if timeline:
            updates["timeline"] = {
                "bucket": timeline,
                "raw": user_message,  # Preserve what they actually said
                "confidence": "med",
                "source": "keyword_match"
            }

    return {
        "extracted": extracted or {},
        "next_state": "S3_STAKEHOLDERS",
        "system_response": RESPONSES["S3_STAKEHOLDERS"],
        "intake_packet_updates": updates,
        "assumptions": [],
        "debug_info": debug_info
    }


def _handle_stakeholders_state(client, user_message: str, intake_packet: dict, debug_info: dict, prior_context: str = "") -> dict:
    """Handle S3_STAKEHOLDERS state - asks who uses and approves."""

    prompt = SIMPLE_PROMPTS["extract_stakeholders"].format(user_message=user_message)
    response = _call_llm(client, prompt, debug_info)
    extracted = _parse_json(response, debug_info) if response else None

    updates = {}

    if extracted:
        if extracted.get("reasoning"):
            debug_info["reasoning"] = extracted["reasoning"]
        if extracted.get("users") or extracted.get("approvers"):
            updates["stakeholder_reality"] = {
                "users": extracted.get("users"),
                "approvers": extracted.get("approvers"),
                "confidence": "high",
                "source": "llm_extracted",
                "reasoning": extracted.get("reasoning", "")
            }

    return {
        "extracted": extracted or {},
        "next_state": "S4_INTEGRATION",
        "system_response": RESPONSES["S4_INTEGRATION"],
        "intake_packet_updates": updates,
        "assumptions": [],
        "debug_info": debug_info
    }


# Legacy handler kept for backwards compatibility
def _handle_context_state(client, user_message: str, intake_packet: dict, debug_info: dict, prior_context: str = "") -> dict:
    """Handle S3_CONTEXT state - legacy, redirects to location state."""
    return _handle_location_state(client, user_message, intake_packet, debug_info, prior_context)


def _handle_integration_state(client, user_message: str, intake_packet: dict, debug_info: dict, prior_context: str = "") -> dict:
    """Handle S4_INTEGRATION state - asks about existing systems."""

    # Extract systems from user message
    updates = {}

    # Simple extraction of system mentions
    systems = []
    system_keywords = ["crm", "erp", "sap", "salesforce", "oracle", "database", "api",
                       "scada", "plc", "sensor", "calendar", "slack", "teams", "email",
                       "payment", "stripe", "square", "inventory", "pos", "warehouse"]

    msg_lower = user_message.lower()
    for keyword in system_keywords:
        if keyword in msg_lower:
            systems.append(keyword.upper() if keyword in ["crm", "erp", "sap", "api", "plc", "pos"] else keyword.title())

    if systems or len(user_message) > 10:
        updates["integration_surface"] = {
            "systems": systems if systems else ["custom systems mentioned"],
            "user_description": user_message,
            "confidence": "high" if systems else "med",
            "source": "keyword_match" if systems else "user_direct"
        }

    return {
        "extracted": {"systems": systems},
        "next_state": "S4_RISK",
        "system_response": RESPONSES["S4_RISK"],
        "intake_packet_updates": updates,
        "assumptions": [],
        "debug_info": debug_info
    }


def _handle_risk_state(client, user_message: str, intake_packet: dict, debug_info: dict, prior_context: str = "") -> dict:
    """Handle S4_RISK state - asks about failure impact."""

    use_case = intake_packet.get("use_case_intent", {}).get("value", "their project")
    industry = intake_packet.get("industry", {}).get("value", "unspecified")

    prompt = SIMPLE_PROMPTS["extract_risk"].format(
        use_case_summary=use_case,
        industry=industry,
        prior_context=prior_context
    )
    response = _call_llm(client, prompt, debug_info)
    extracted = _parse_json(response, debug_info) if response else None

    updates = {}

    if extracted:
        # Capture reasoning for context handoff
        if extracted.get("reasoning"):
            debug_info["reasoning"] = extracted["reasoning"]

        if extracted.get("risk_level"):
            risk = extracted["risk_level"].lower()
            if risk in ["low", "medium", "high"]:
                updates["risk_posture"] = {
                    "level": risk,
                    "confidence": "med",
                    "source": "llm_extracted",
                    "reason": extracted.get("reason", ""),
                    "reasoning": extracted.get("reasoning", "")
                }
    else:
        # Default based on industry
        debug_info["fallback_used"] = True
        risk = _infer_risk_from_industry(industry)
        updates["risk_posture"] = {
            "level": risk,
            "confidence": "low",
            "source": "industry_default"
        }

    # Build confirmation summary
    summary = _build_summary(intake_packet, updates)

    return {
        "extracted": extracted or {},
        "next_state": "S5_ASSUMPTIONS_CHECK",
        "system_response": summary,
        "intake_packet_updates": updates,
        "assumptions": _generate_assumptions(intake_packet, updates),
        "debug_info": debug_info
    }


def _handle_assumptions_state(user_message: str, intake_packet: dict, debug_info: dict) -> dict:
    """Handle S5_ASSUMPTIONS_CHECK state."""

    # User is confirming or correcting - for now just proceed
    return {
        "extracted": {},
        "next_state": "S6_RUN_STEP0",
        "system_response": "Great, I have what I need. Starting the analysis now...",
        "intake_packet_updates": {},
        "assumptions": [],
        "debug_info": debug_info
    }


# =============================================================================
# KEYWORD FALLBACK - Works without LLM
# =============================================================================

def _keyword_fallback(current_state: str, user_message: str, intake_packet: dict, debug_info: dict) -> dict:
    """Pure keyword-based fallback when LLM is unavailable."""

    updates = {}

    if current_state in ["S0_ENTRY", "S1_INTENT"]:
        updates["use_case_intent"] = {
            "value": user_message,
            "confidence": "low",
            "source": "user_direct"
        }

        industry = _detect_industry(user_message)
        if industry:
            updates["industry"] = {
                "value": industry,
                "confidence": "med",
                "source": "keyword_match"
            }

        return {
            "extracted": {},
            "next_state": "S2_OPPORTUNITY",
            "system_response": RESPONSES["S2_OPPORTUNITY"],
            "intake_packet_updates": updates,
            "assumptions": [],
            "debug_info": debug_info
        }

    elif current_state == "S2_OPPORTUNITY":
        goal = _detect_opportunity(user_message)
        if goal:
            updates["opportunity_shape"] = {"value": goal, "confidence": "low", "source": "keyword_match"}

        return {
            "extracted": {},
            "next_state": "S3_LOCATION",
            "system_response": RESPONSES["S3_LOCATION"],
            "intake_packet_updates": updates,
            "assumptions": [],
            "debug_info": debug_info
        }

    elif current_state in ["S3_CONTEXT", "S3_LOCATION"]:
        location = _detect_location(user_message)
        if location:
            updates["jurisdiction"] = {"value": location, "confidence": "med", "source": "keyword_match"}
        return {
            "extracted": {},
            "next_state": "S3_ORG_SIZE",
            "system_response": RESPONSES["S3_ORG_SIZE"],
            "intake_packet_updates": updates,
            "assumptions": [],
            "debug_info": debug_info
        }

    elif current_state == "S3_ORG_SIZE":
        org_size = _detect_org_size(user_message)
        if org_size:
            updates["organization_size"] = {"bucket": org_size, "confidence": "med", "source": "keyword_match"}
        return {
            "extracted": {},
            "next_state": "S3_TIMELINE",
            "system_response": RESPONSES["S3_TIMELINE"],
            "intake_packet_updates": updates,
            "assumptions": [],
            "debug_info": debug_info
        }

    elif current_state == "S3_TIMELINE":
        timeline = _detect_timeline(user_message)
        if timeline:
            updates["timeline"] = {"bucket": timeline, "confidence": "med", "source": "keyword_match"}
        return {
            "extracted": {},
            "next_state": "S3_STAKEHOLDERS",
            "system_response": RESPONSES["S3_STAKEHOLDERS"],
            "intake_packet_updates": updates,
            "assumptions": [],
            "debug_info": debug_info
        }

    elif current_state == "S3_STAKEHOLDERS":
        # Can't easily extract stakeholders with keywords
        return {
            "extracted": {},
            "next_state": "S4_INTEGRATION",
            "system_response": RESPONSES["S4_INTEGRATION"],
            "intake_packet_updates": updates,
            "assumptions": [],
            "debug_info": debug_info
        }

    # Default progression for other states
    state_order = ["S1_INTENT", "S2_OPPORTUNITY", "S3_LOCATION", "S3_ORG_SIZE", "S3_TIMELINE", "S3_STAKEHOLDERS", "S4_INTEGRATION", "S4_RISK", "S5_ASSUMPTIONS_CHECK"]
    try:
        idx = state_order.index(current_state)
        next_state = state_order[idx + 1] if idx < len(state_order) - 1 else current_state
    except ValueError:
        next_state = "S2_OPPORTUNITY"

    return {
        "extracted": {},
        "next_state": next_state,
        "system_response": RESPONSES.get(next_state, "Tell me more."),
        "intake_packet_updates": updates,
        "assumptions": [],
        "debug_info": debug_info
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _detect_industry(text: str) -> Optional[str]:
    """Keyword-based industry detection."""
    text_lower = text.lower()

    # Order matters - check more specific keywords first
    industry_keywords = {
        "hospitality": ["banquet", "banquets", "catering", "hotel", "hotels", "restaurant",
                       "event", "events", "wedding", "venue", "venues", "food service",
                       "hospitality", "reception", "ballroom", "dining"],
        "healthcare": ["medical", "hospital", "clinic", "patient", "health", "doctor",
                      "nurse", "healthcare", "clinical", "pharma", "pharmaceutical"],
        "retail": ["store", "stores", "shop", "retail", "merchandise", "ecommerce",
                  "shopping", "inventory", "pos", "point of sale"],
        "finance": ["bank", "banking", "financial", "investment", "trading", "loan",
                   "insurance", "fintech", "accounting", "payment"],
        "manufacturing": ["factory", "production", "assembly", "manufacturing",
                         "supply chain", "warehouse", "industrial"],
        "technology": ["software", "app", "platform", "saas", "tech", "developer",
                      "code", "api", "cloud", "data center"],
        "education": ["school", "university", "student", "teacher", "learning",
                     "education", "training", "course", "academic"],
        "real_estate": ["property", "real estate", "rental", "landlord", "tenant",
                       "building", "apartment", "housing"],
        "logistics": ["shipping", "delivery", "warehouse", "logistics", "freight",
                     "transport", "fleet", "courier"],
    }

    for industry, keywords in industry_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                return industry

    return None


def _normalize_industry(industry: str) -> Optional[str]:
    """Normalize industry name to standard value."""
    if not industry:
        return None

    industry_lower = industry.lower().strip()

    # Map common variations
    mappings = {
        "hospitality": "hospitality",
        "hotels": "hospitality",
        "restaurants": "hospitality",
        "events": "hospitality",
        "food": "hospitality",
        "catering": "hospitality",
        "healthcare": "healthcare",
        "medical": "healthcare",
        "health": "healthcare",
        "retail": "retail",
        "ecommerce": "retail",
        "finance": "finance",
        "banking": "finance",
        "financial": "finance",
        "manufacturing": "manufacturing",
        "industrial": "manufacturing",
        "technology": "technology",
        "tech": "technology",
        "software": "technology",
        "education": "education",
        "real estate": "real_estate",
        "property": "real_estate",
        "logistics": "logistics",
        "transportation": "logistics",
        "energy": "energy",  # Keep if actually energy
    }

    # Check exact match first
    if industry_lower in mappings:
        return mappings[industry_lower]

    # Check partial match
    for key, value in mappings.items():
        if key in industry_lower:
            return value

    # Return as-is if not recognized
    return industry_lower


def _detect_opportunity(text: str) -> Optional[str]:
    """Keyword-based opportunity detection."""
    text_lower = text.lower()

    if any(w in text_lower for w in ["revenue", "sales", "money", "profit", "income", "grow", "growth"]):
        return "revenue"
    if any(w in text_lower for w in ["cost", "save", "efficient", "time", "reduce", "automate", "faster"]):
        return "cost"
    if any(w in text_lower for w in ["risk", "compliance", "safety", "security", "audit", "regulation"]):
        return "risk"
    if any(w in text_lower for w in ["transform", "change", "innovate", "disrupt", "new way", "reimagine"]):
        return "transform"

    return None


def _detect_location(text: str) -> Optional[str]:
    """Keyword-based location detection."""
    text_lower = text.lower()

    # Common country/region keywords
    locations = {
        "us": ["us", "usa", "united states", "america", "american"],
        "uk": ["uk", "united kingdom", "britain", "british", "england"],
        "eu": ["eu", "europe", "european", "germany", "france", "spain", "italy"],
        "canada": ["canada", "canadian"],
        "australia": ["australia", "australian"],
        "global": ["global", "worldwide", "international", "multiple countries"],
        "asia": ["asia", "asian", "china", "japan", "singapore", "india"],
    }

    # US regions
    us_regions = ["midwest", "northeast", "southeast", "southwest", "west coast", "east coast",
                  "california", "texas", "new york", "florida"]

    for region in us_regions:
        if region in text_lower:
            return "US - " + region.title()

    for location, keywords in locations.items():
        for keyword in keywords:
            if keyword in text_lower:
                return location.upper() if location in ["us", "uk", "eu"] else location.title()

    return None


def _detect_org_size(text: str) -> Optional[str]:
    """Keyword-based organization size detection."""
    text_lower = text.lower()

    # Check for explicit size keywords
    if any(w in text_lower for w in ["startup", "small team", "just me", "few people", "under 50"]):
        return "small"
    if any(w in text_lower for w in ["smb", "mid-size", "medium", "100 employees", "200 employees", "few hundred"]):
        return "medium"
    if any(w in text_lower for w in ["large", "1000", "thousands", "multiple locations", "enterprise"]):
        return "large"
    if any(w in text_lower for w in ["fortune 500", "10000", "global company", "multinational"]):
        return "enterprise"

    # Try to detect numbers
    import re
    numbers = re.findall(r'\d+', text)
    for num_str in numbers:
        num = int(num_str)
        if num < 50:
            return "small"
        elif num < 500:
            return "medium"
        elif num < 5000:
            return "large"
        else:
            return "enterprise"

    return None


def _detect_timeline(text: str) -> Optional[str]:
    """Keyword-based timeline detection with time expression parsing."""
    text_lower = text.lower()

    # Urgent indicators (< 1 month)
    if any(w in text_lower for w in ["urgent", "asap", "immediately", "this week", "next week", "critical", "emergency"]):
        return "urgent"

    # Try to parse time expressions
    import re

    # Look for "X weeks/months/quarters/years" patterns
    time_match = re.search(r'(\d+)\s*(week|month|quarter|year)s?', text_lower)
    if time_match:
        num = int(time_match.group(1))
        unit = time_match.group(2)

        # Convert to months for comparison
        months = 0
        if unit == "week":
            months = num * 0.25
        elif unit == "month":
            months = num
        elif unit == "quarter":
            months = num * 3
        elif unit == "year":
            months = num * 12

        # Categorize by months
        if months <= 1:
            return "urgent"
        elif months <= 6:
            return "near-term"
        else:
            return "exploratory"

    # Check for "this month" vs "this quarter" vs "this year"
    if "this month" in text_lower:
        return "urgent"
    if "this quarter" in text_lower or "next quarter" in text_lower:
        return "near-term"
    if "this year" in text_lower or "next year" in text_lower:
        return "exploratory"

    # Near-term indicators (1-6 months)
    if any(w in text_lower for w in ["soon", "pilot", "few months", "near-term", "q1", "q2", "q3", "q4"]):
        return "near-term"

    # Exploratory indicators (6+ months or no concrete timeline)
    if any(w in text_lower for w in ["exploring", "research", "looking into", "considering", "early stage", "no rush", "eventually"]):
        return "exploratory"

    return None


def _infer_risk_from_industry(industry: str) -> str:
    """Infer default risk level from industry."""
    high_risk = ["healthcare", "finance", "pharmaceutical", "aviation", "nuclear"]
    medium_risk = ["hospitality", "retail", "manufacturing", "logistics", "education"]

    industry_lower = (industry or "").lower()

    if any(h in industry_lower for h in high_risk):
        return "high"
    if any(m in industry_lower for m in medium_risk):
        return "medium"
    return "low"


def _build_summary(intake_packet: dict, updates: dict) -> str:
    """Build a conversational summary for user confirmation."""
    merged = {**intake_packet}
    for key, value in updates.items():
        merged[key] = value

    # Build narrative summary
    parts = ["**Here's what I understood:**\n"]

    # Core use case
    use_case = merged.get("use_case_intent", {}).get("value", "")
    industry = merged.get("industry", {}).get("value", "")

    if use_case and industry:
        parts.append(f"You're in **{industry.title()}** and want to {use_case.lower() if use_case[0].isupper() else use_case}")
    elif use_case:
        parts.append(f"You want to {use_case.lower() if use_case[0].isupper() else use_case}")

    # Opportunity shape
    opp = merged.get("opportunity_shape", {}).get("value")
    if opp:
        opp_phrases = {
            "revenue": "primarily to **grow revenue**",
            "cost": "primarily to **save time and money**",
            "risk": "primarily to **reduce risk**",
            "transform": "to **transform how you operate**"
        }
        parts.append(f"\nYou're doing this {opp_phrases.get(opp, opp)}.")

    # Context
    context_parts = []
    if merged.get("jurisdiction", {}).get("value"):
        context_parts.append(f"operating in **{merged['jurisdiction']['value']}**")
    if merged.get("organization_size", {}).get("bucket"):
        context_parts.append(f"a **{merged['organization_size']['bucket'].lower()}** organization")

    if context_parts:
        parts.append(f"\nYou're {', '.join(context_parts)}.")

    # Timeline - show raw expression if available
    timeline_data = merged.get("timeline", {})
    timeline_bucket = timeline_data.get("bucket")
    timeline_raw = timeline_data.get("raw")
    if timeline_bucket or timeline_raw:
        if timeline_raw:
            # Show what they said with the category
            timeline_phrases = {
                "urgent": f"Timeline: **{timeline_raw}** (urgent)",
                "near-term": f"Timeline: **{timeline_raw}** (near-term)",
                "standard": f"Timeline: **{timeline_raw}**",
                "exploratory": f"Timeline: **{timeline_raw}** (exploratory)"
            }
            parts.append(f"\n{timeline_phrases.get(timeline_bucket, f'Timeline: {timeline_raw}')}")
        else:
            timeline_phrases = {
                "urgent": "This is **urgent** - you need this soon.",
                "near-term": "Your timeline is **near-term** - looking to pilot soon.",
                "standard": "You have a **standard timeline** - no particular rush.",
                "exploratory": "You're **exploring** - this is early stage research."
            }
            parts.append(f"\n{timeline_phrases.get(timeline_bucket, f'Timeline: {timeline_bucket}')}")

    # Stakeholders
    stakeholders = merged.get("stakeholder_reality", {})
    if stakeholders.get("users") or stakeholders.get("approvers"):
        stakeholder_parts = []
        if stakeholders.get("users"):
            stakeholder_parts.append(f"**{stakeholders['users']}** would use this")
        if stakeholders.get("approvers"):
            stakeholder_parts.append(f"**{stakeholders['approvers']}** needs to approve")
        if stakeholder_parts:
            parts.append(f"\n{' and '.join(stakeholder_parts)}.")

    # Integration
    integration = merged.get("integration_surface", {})
    if integration.get("systems"):
        systems = integration["systems"]
        if isinstance(systems, list) and systems:
            parts.append(f"\nThis will connect to: {', '.join(systems[:5])}.")
    elif integration.get("user_description"):
        parts.append(f"\nIntegration context: {integration['user_description'][:100]}...")

    # Risk
    risk = merged.get("risk_posture", {}).get("level")
    if risk:
        risk_phrases = {
            "low": "If something goes wrong, the impact would be **low** (minor inconvenience).",
            "medium": "If something goes wrong, the impact would be **medium** (some cost or disruption).",
            "high": "If something goes wrong, the impact could be **high** (significant cost, safety, or compliance issues)."
        }
        parts.append(f"\n{risk_phrases.get(risk, f'Risk level: {risk}')}")

    parts.append("\n\n**Does this look right?** Use the buttons below to confirm or make corrections.")

    return "\n".join(parts)


def _generate_assumptions(intake_packet: dict, updates: dict) -> list:
    """Generate assumptions based on what we inferred vs what user said."""
    assumptions = []

    merged = {**intake_packet}
    for key, value in updates.items():
        merged[key] = value

    # Check for low-confidence inferences
    for key in ["industry", "jurisdiction", "organization_size", "timeline", "risk_posture"]:
        data = merged.get(key, {})
        if data.get("confidence") == "low" or data.get("source") in ["keyword_match", "industry_default"]:
            if key == "industry" and data.get("value"):
                assumptions.append({
                    "statement": f"Operating in the {data['value']} industry",
                    "confidence": data.get("confidence", "low"),
                    "impact": "high"
                })
            elif key == "risk_posture" and data.get("level"):
                assumptions.append({
                    "statement": f"Risk level is {data['level']} based on industry norms",
                    "confidence": "low",
                    "impact": "medium"
                })

    return assumptions


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_initial_system_message() -> str:
    """Get the initial system message for starting the conversation."""
    return "Let's talk this through. You don't need to be precise — I'll make reasonable assumptions and show them to you before anything runs.\n\nWhat problem are you hoping an AI agent could help with?"


def should_proceed_to_research(intake_packet: dict) -> bool:
    """Check if we have enough data to proceed to Step 0 research."""
    required = ["use_case_intent"]

    for field in required:
        if not intake_packet.get(field, {}).get("value"):
            return False

    return True
