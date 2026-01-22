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
SIMPLE_PROMPTS = {
    "extract_intent": """Extract information from this user message about their AI agent project.

USER MESSAGE: {user_message}

Return ONLY a JSON object with these fields:
- "summary": A 1-2 sentence summary of what they want (string)
- "industry": The industry/sector mentioned (string or null). Examples: hospitality, healthcare, retail, finance, manufacturing, technology, education, logistics
- "needs_more_info": true if the message is too vague to understand, false otherwise

IMPORTANT INDUSTRY HINTS:
- banquet, catering, hotel, restaurant, event, wedding, venue, food → "hospitality"
- medical, hospital, clinic, patient, health → "healthcare"
- store, shop, retail, merchandise → "retail"
- bank, financial, investment, trading, insurance → "finance"
- factory, production, manufacturing → "manufacturing"
- software, app, platform, tech, developer → "technology"

JSON response:""",

    "extract_opportunity": """The user wants to: {use_case_summary}

What is their PRIMARY goal? Pick ONE:
- "revenue" = make money, increase sales, grow business
- "cost" = save money, reduce time, improve efficiency
- "risk" = reduce risk, compliance, prevent problems
- "transform" = fundamentally change operations

Return ONLY a JSON object:
{{"goal": "<one of the four options>", "reason": "<brief explanation>"}}

JSON response:""",

    "extract_context": """The user's project: {use_case_summary}
Industry: {industry}

From their latest message, extract any business context mentioned.

USER MESSAGE: {user_message}

Return ONLY a JSON object with these fields (use null if not mentioned):
- "location": Where does this operate? (country, region, or "global")
- "org_size": Organization size (small/medium/large/enterprise)
- "timeline": How urgent? (urgent/near-term/standard/exploratory)
- "systems": List of existing systems/tools mentioned, or empty list

JSON response:""",

    "extract_risk": """Project: {use_case_summary}
Industry: {industry}

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
{{"risk_level": "low" or "medium" or "high", "reason": "<brief explanation>"}}

JSON response:"""
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
    api_key: Optional[str] = None
) -> dict:
    """
    Process a single state with a simple, focused LLM call.

    Designed to work reliably with Opus, Sonnet, AND Haiku.
    """
    debug_info = {
        "state": current_state,
        "model": model,
        "llm_called": False,
        "llm_response": None,
        "parse_success": False,
        "fallback_used": False,
        "error": None
    }

    client = get_chat_client(model, api_key)

    if not client:
        debug_info["error"] = "No API client (missing key or langchain)"
        debug_info["fallback_used"] = True
        return _keyword_fallback(current_state, user_message, intake_packet, debug_info)

    # Route to appropriate handler based on state
    try:
        if current_state in ["S0_ENTRY", "S1_INTENT"]:
            return _handle_intent_state(client, user_message, intake_packet, debug_info)
        elif current_state == "S2_OPPORTUNITY":
            return _handle_opportunity_state(client, user_message, intake_packet, debug_info)
        elif current_state == "S3_CONTEXT":
            return _handle_context_state(client, user_message, intake_packet, debug_info)
        elif current_state == "S4_INTEGRATION_RISK":
            return _handle_risk_state(client, user_message, intake_packet, debug_info)
        elif current_state == "S5_ASSUMPTIONS_CHECK":
            return _handle_assumptions_state(user_message, intake_packet, debug_info)
        else:
            # Unknown state - try generic extraction
            return _handle_intent_state(client, user_message, intake_packet, debug_info)
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

def _handle_intent_state(client, user_message: str, intake_packet: dict, debug_info: dict) -> dict:
    """Handle S0_ENTRY and S1_INTENT states."""

    prompt = SIMPLE_PROMPTS["extract_intent"].format(user_message=user_message)
    response = _call_llm(client, prompt, debug_info)
    extracted = _parse_json(response, debug_info) if response else None

    updates = {}
    next_state = "S1_INTENT"  # Default: stay
    system_response = None

    if extracted:
        # Got LLM extraction
        if extracted.get("summary"):
            updates["use_case_intent"] = {
                "value": extracted["summary"],
                "confidence": "high",
                "source": "llm_extracted"
            }
            updates["use_case_synthesized"] = extracted["summary"]

        if extracted.get("industry"):
            # Validate and normalize industry
            industry = _normalize_industry(extracted["industry"])
            if industry:
                updates["industry"] = {
                    "value": industry,
                    "confidence": "high",
                    "source": "llm_extracted"
                }

        # Determine next action
        if extracted.get("needs_more_info"):
            system_response = "Could you tell me a bit more about what specific problem you're trying to solve?"
        else:
            next_state = "S2_OPPORTUNITY"
            system_response = "Got it. Is your main goal to make more money, save time/cost, reduce risk, or fundamentally change how you operate?"
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
        system_response = "Thanks. Is your main goal to make more money, save time/cost, reduce risk, or change how you operate?"

    return {
        "extracted": extracted or {},
        "next_state": next_state,
        "system_response": system_response,
        "intake_packet_updates": updates,
        "assumptions": [],
        "debug_info": debug_info
    }


def _handle_opportunity_state(client, user_message: str, intake_packet: dict, debug_info: dict) -> dict:
    """Handle S2_OPPORTUNITY state."""

    use_case = intake_packet.get("use_case_intent", {}).get("value", user_message)
    prompt = SIMPLE_PROMPTS["extract_opportunity"].format(use_case_summary=use_case)
    response = _call_llm(client, prompt, debug_info)
    extracted = _parse_json(response, debug_info) if response else None

    updates = {}

    if extracted and extracted.get("goal"):
        goal = extracted["goal"].lower()
        if goal in ["revenue", "cost", "risk", "transform"]:
            updates["opportunity_shape"] = {
                "value": goal,
                "confidence": "high",
                "source": "llm_extracted"
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
        "next_state": "S3_CONTEXT",
        "system_response": "Quick context: where does this operate (country/region), and roughly how big is your organization?",
        "intake_packet_updates": updates,
        "assumptions": [],
        "debug_info": debug_info
    }


def _handle_context_state(client, user_message: str, intake_packet: dict, debug_info: dict) -> dict:
    """Handle S3_CONTEXT state."""

    use_case = intake_packet.get("use_case_intent", {}).get("value", "their project")
    industry = intake_packet.get("industry", {}).get("value", "unspecified")

    prompt = SIMPLE_PROMPTS["extract_context"].format(
        use_case_summary=use_case,
        industry=industry,
        user_message=user_message
    )
    response = _call_llm(client, prompt, debug_info)
    extracted = _parse_json(response, debug_info) if response else None

    updates = {}

    if extracted:
        if extracted.get("location"):
            updates["jurisdiction"] = {
                "value": extracted["location"],
                "confidence": "high",
                "source": "llm_extracted"
            }
        if extracted.get("org_size"):
            updates["organization_size"] = {
                "bucket": extracted["org_size"],
                "confidence": "med",
                "source": "llm_extracted"
            }
        if extracted.get("timeline"):
            updates["timeline"] = {
                "bucket": extracted["timeline"],
                "confidence": "med",
                "source": "llm_extracted"
            }
        if extracted.get("systems"):
            updates["integration_surface"] = {
                "systems": extracted["systems"],
                "confidence": "high",
                "source": "llm_extracted"
            }

    return {
        "extracted": extracted or {},
        "next_state": "S4_INTEGRATION_RISK",
        "system_response": "Does this need to connect to any existing systems? And if something went wrong, what would the impact be?",
        "intake_packet_updates": updates,
        "assumptions": [],
        "debug_info": debug_info
    }


def _handle_risk_state(client, user_message: str, intake_packet: dict, debug_info: dict) -> dict:
    """Handle S4_INTEGRATION_RISK state."""

    use_case = intake_packet.get("use_case_intent", {}).get("value", "their project")
    industry = intake_packet.get("industry", {}).get("value", "unspecified")

    prompt = SIMPLE_PROMPTS["extract_risk"].format(
        use_case_summary=use_case,
        industry=industry
    )
    response = _call_llm(client, prompt, debug_info)
    extracted = _parse_json(response, debug_info) if response else None

    updates = {}

    if extracted and extracted.get("risk_level"):
        risk = extracted["risk_level"].lower()
        if risk in ["low", "medium", "high"]:
            updates["risk_posture"] = {
                "level": risk,
                "confidence": "med",
                "source": "llm_extracted",
                "reason": extracted.get("reason", "")
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
            "system_response": "Is your main goal to make more money, save time/cost, reduce risk, or change how you operate?",
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
            "next_state": "S3_CONTEXT",
            "system_response": "Where does this operate, and roughly how big is your organization?",
            "intake_packet_updates": updates,
            "assumptions": [],
            "debug_info": debug_info
        }

    # Default progression
    state_order = ["S1_INTENT", "S2_OPPORTUNITY", "S3_CONTEXT", "S4_INTEGRATION_RISK", "S5_ASSUMPTIONS_CHECK"]
    try:
        idx = state_order.index(current_state)
        next_state = state_order[idx + 1] if idx < len(state_order) - 1 else current_state
    except ValueError:
        next_state = "S2_OPPORTUNITY"

    responses = {
        "S2_OPPORTUNITY": "Is your main goal revenue, cost savings, risk reduction, or transformation?",
        "S3_CONTEXT": "Where does this operate, and how big is your organization?",
        "S4_INTEGRATION_RISK": "Does this connect to existing systems? What if it fails?",
        "S5_ASSUMPTIONS_CHECK": "Let me summarize what I understand..."
    }

    return {
        "extracted": {},
        "next_state": next_state,
        "system_response": responses.get(next_state, "Tell me more."),
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
    """Build confirmation summary for user."""
    merged = {**intake_packet}
    for key, value in updates.items():
        merged[key] = value

    parts = ["Here's what I understand so far:\n"]

    if merged.get("use_case_intent", {}).get("value"):
        parts.append(f"**Goal:** {merged['use_case_intent']['value']}")

    if merged.get("industry", {}).get("value"):
        parts.append(f"**Industry:** {merged['industry']['value'].title()}")

    if merged.get("opportunity_shape", {}).get("value"):
        opp_map = {
            "revenue": "Generate revenue / grow sales",
            "cost": "Reduce costs / save time",
            "risk": "Mitigate risk / improve compliance",
            "transform": "Transform operations"
        }
        opp = merged['opportunity_shape']['value']
        parts.append(f"**Primary Goal:** {opp_map.get(opp, opp)}")

    if merged.get("jurisdiction", {}).get("value"):
        parts.append(f"**Location:** {merged['jurisdiction']['value']}")

    if merged.get("organization_size", {}).get("bucket"):
        parts.append(f"**Organization Size:** {merged['organization_size']['bucket']}")

    if merged.get("risk_posture", {}).get("level"):
        parts.append(f"**Risk Level:** {merged['risk_posture']['level']}")

    parts.append("\nDoes this look right? Let me know if anything's off.")

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
