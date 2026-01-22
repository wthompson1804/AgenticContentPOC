"""
Chat LLM Module v2 - Per-State Prompting Architecture.

This module implements the FSM-LLM pattern where each state has:
1. Its own focused prompt asking ONE thing
2. Its own extraction logic for just that state's data
3. Deterministic transitions based on data collected

Per best practices from:
- jsz-05/LLM-State-Machine
- statelyai/agent
- robocorp/llmstatemachine
"""

import os
import json
import re
from typing import Optional, Tuple
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


def get_chat_client(model: str = "claude-sonnet-4-20250514", api_key: Optional[str] = None) -> Optional[ChatAnthropic]:
    """Get Claude client for chat inference."""
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None

    return ChatAnthropic(
        model=model,
        api_key=key,
        max_tokens=1024,  # Smaller for focused responses
        temperature=0.2,  # Lower for more deterministic extraction
    )


# =============================================================================
# STATE-SPECIFIC PROMPTS - Each state asks ONE focused question
# =============================================================================

STATE_PROMPTS = {
    "S1_INTENT": """You are helping scope an AI agent project. The user just described what they want.

Your ONLY job: Restate their goal clearly in 2-3 sentences.

User said: "{user_message}"

Respond with JSON:
{{
    "use_case_summary": "A clear 2-3 sentence summary of what they want to achieve",
    "industry_detected": "The industry/sector if mentioned (hospitality, healthcare, retail, finance, manufacturing, etc.) or null",
    "needs_clarification": true/false,
    "clarification_question": "A follow-up question if the goal is unclear, otherwise null"
}}

IMPORTANT:
- If they mention banquet halls, catering, events, weddings → industry is "hospitality" or "events"
- If they mention hotels, restaurants, food service → industry is "hospitality"
- Actually READ what they wrote. Don't guess "technology" unless they mention software/tech.
""",

    "S2_OPPORTUNITY": """You are helping scope an AI agent project.

The user's goal: "{use_case_summary}"

Your ONLY job: Determine the PRIMARY business opportunity type.

Options:
- "revenue" = Make more money, increase sales, new business
- "cost" = Save money, reduce time, improve efficiency
- "risk" = Reduce risk, improve compliance, prevent problems
- "transform" = Fundamentally change how the business operates

Respond with JSON:
{{
    "opportunity_type": "revenue" or "cost" or "risk" or "transform",
    "confidence": "high" or "med" or "low",
    "reasoning": "One sentence explaining why"
}}
""",

    "S3_CONTEXT": """You are helping scope an AI agent project.

The user's goal: "{use_case_summary}"
Industry: {industry}

Your ONLY job: Extract business context from their latest message.

User said: "{user_message}"

Respond with JSON:
{{
    "jurisdiction": "Where this operates (US, EU, UK, Global, specific state/country) or null",
    "organization_size": "Small (1-50), Medium (51-500), Large (500+), Enterprise (5000+) or null",
    "timeline": "Urgent (0-3mo), Near-term (3-6mo), Standard (6-12mo), Long-term (12mo+), Exploratory or null",
    "existing_systems": ["List of systems/tools mentioned"] or [],
    "anything_unclear": "What context is still missing, or null if we have enough"
}}

IMPORTANT: Only extract what they ACTUALLY said. Don't invent details.
""",

    "S4_RISK": """You are helping scope an AI agent project in a {industry} context.

The user's goal: "{use_case_summary}"

Your ONLY job: Assess risk level and regulatory considerations.

Respond with JSON:
{{
    "risk_level": "low" or "medium" or "high",
    "risk_reasoning": "Why this risk level",
    "regulatory_concerns": ["List any regulations that might apply"] or [],
    "worst_case": "What happens if the agent fails or makes mistakes"
}}
""",

    "S5_SUMMARY": """You are helping scope an AI agent project.

Here's what we know:
- Goal: {use_case_summary}
- Industry: {industry}
- Opportunity type: {opportunity}
- Jurisdiction: {jurisdiction}
- Organization size: {org_size}
- Timeline: {timeline}
- Risk level: {risk_level}

Your job: Create a brief summary for user confirmation.

Respond with JSON:
{{
    "summary_text": "A 3-4 sentence summary of the project scope",
    "assumptions": [
        {{"statement": "What we're assuming", "confidence": "high/med/low"}}
    ],
    "ready_for_analysis": true/false,
    "missing_critical": "What's still needed, or null if ready"
}}
"""
}


# =============================================================================
# CORE PROCESSING FUNCTION - Handles one state at a time
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
    Process a single state with its focused prompt.

    This is the key architectural change: instead of one giant prompt,
    each state has its own focused extraction task.

    Args:
        current_state: Current state (S1_INTENT, S2_OPPORTUNITY, etc.)
        user_message: The latest user message
        intake_packet: Current intake packet with existing data
        chat_history: Full chat history for context
        model: Claude model to use
        api_key: API key

    Returns:
        dict with:
        - extracted: Data extracted for this state
        - next_state: Suggested next state
        - system_response: What to say to the user
        - intake_packet_updates: Updates to merge into intake_packet
    """
    client = get_chat_client(model, api_key)

    if not client:
        return _no_api_fallback(current_state, user_message, intake_packet)

    # Get the prompt template for this state
    prompt_template = STATE_PROMPTS.get(current_state)

    if not prompt_template:
        # Unknown state, use a generic extraction
        return _generic_extraction(current_state, user_message, intake_packet, client)

    # Build the prompt with context
    prompt = _build_state_prompt(prompt_template, user_message, intake_packet)

    try:
        response = client.invoke([
            SystemMessage(content="You are a helpful assistant. Always respond with valid JSON only, no markdown."),
            HumanMessage(content=prompt)
        ])

        # Parse the JSON response
        extracted = _parse_json_response(response.content)

        if not extracted:
            # Parsing failed, try to salvage
            return _handle_parse_failure(current_state, user_message, response.content, intake_packet)

        # Process based on state
        return _process_state_response(current_state, extracted, user_message, intake_packet)

    except Exception as e:
        # Log error and provide graceful fallback
        print(f"LLM call failed for state {current_state}: {e}")
        return _graceful_fallback(current_state, user_message, intake_packet, str(e))


def _build_state_prompt(template: str, user_message: str, intake_packet: dict) -> str:
    """Build the prompt by filling in template variables."""

    # Get values from intake packet with defaults
    use_case = intake_packet.get("use_case_intent", {}).get("value", "Not yet captured")
    industry = intake_packet.get("industry", {}).get("value", "Not specified")
    opportunity = intake_packet.get("opportunity_shape", {}).get("value", "Not specified")
    jurisdiction = intake_packet.get("jurisdiction", {}).get("value", "Not specified")
    org_size = intake_packet.get("organization_size", {}).get("bucket", "Not specified")
    timeline = intake_packet.get("timeline", {}).get("bucket", "Not specified")
    risk_level = intake_packet.get("risk_posture", {}).get("level", "Not assessed")

    return template.format(
        user_message=user_message,
        use_case_summary=use_case,
        industry=industry,
        opportunity=opportunity,
        jurisdiction=jurisdiction,
        org_size=org_size,
        timeline=timeline,
        risk_level=risk_level
    )


def _parse_json_response(content: str) -> Optional[dict]:
    """Parse JSON from LLM response, handling common issues."""

    # Clean up the response
    content = content.strip()

    # Remove markdown code blocks if present
    if content.startswith("```"):
        # Extract content between code blocks
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if match:
            content = match.group(1)

    # Try direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the content
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except json.JSONDecodeError:
        pass

    return None


def _process_state_response(
    current_state: str,
    extracted: dict,
    user_message: str,
    intake_packet: dict
) -> dict:
    """Process the extracted data based on current state."""

    result = {
        "extracted": extracted,
        "next_state": current_state,  # Default: stay in state
        "system_response": None,
        "intake_packet_updates": {},
        "assumptions": []
    }

    if current_state == "S1_INTENT":
        # Extract use case and industry
        if extracted.get("use_case_summary"):
            result["intake_packet_updates"]["use_case_intent"] = {
                "value": extracted["use_case_summary"],
                "confidence": "high",
                "source": "llm_extracted"
            }
            result["intake_packet_updates"]["use_case_synthesized"] = extracted["use_case_summary"]

        if extracted.get("industry_detected"):
            result["intake_packet_updates"]["industry"] = {
                "value": extracted["industry_detected"],
                "confidence": "med",
                "source": "llm_inferred"
            }

        # Determine next action
        if extracted.get("needs_clarification") and extracted.get("clarification_question"):
            result["system_response"] = extracted["clarification_question"]
        else:
            result["next_state"] = "S2_OPPORTUNITY"
            result["system_response"] = "Got it. Is your main goal to make more money, save time/cost, reduce risk, or fundamentally change how you operate?"

    elif current_state == "S2_OPPORTUNITY":
        if extracted.get("opportunity_type"):
            result["intake_packet_updates"]["opportunity_shape"] = {
                "value": extracted["opportunity_type"],
                "confidence": extracted.get("confidence", "med"),
                "source": "llm_extracted"
            }

        result["next_state"] = "S3_CONTEXT"
        result["system_response"] = "Quick context: where does this operate (country/region), and roughly how big is the organization?"

    elif current_state == "S3_CONTEXT":
        if extracted.get("jurisdiction"):
            result["intake_packet_updates"]["jurisdiction"] = {
                "value": extracted["jurisdiction"],
                "confidence": "high",
                "source": "llm_extracted"
            }

        if extracted.get("organization_size"):
            result["intake_packet_updates"]["organization_size"] = {
                "bucket": extracted["organization_size"],
                "confidence": "med",
                "source": "llm_extracted"
            }

        if extracted.get("timeline"):
            result["intake_packet_updates"]["timeline"] = {
                "bucket": extracted["timeline"],
                "confidence": "med",
                "source": "llm_extracted"
            }

        if extracted.get("existing_systems"):
            result["intake_packet_updates"]["integration_surface"] = {
                "systems": extracted["existing_systems"],
                "confidence": "high",
                "source": "llm_extracted"
            }

        # Check if we need more context
        if extracted.get("anything_unclear"):
            result["system_response"] = extracted["anything_unclear"]
        else:
            result["next_state"] = "S4_INTEGRATION_RISK"
            result["system_response"] = "Does this need to connect to any existing systems? And if something went wrong, what's the worst-case impact?"

    elif current_state == "S4_INTEGRATION_RISK":
        if extracted.get("risk_level"):
            result["intake_packet_updates"]["risk_posture"] = {
                "level": extracted["risk_level"],
                "worst_case": extracted.get("worst_case", ""),
                "confidence": "med",
                "source": "llm_extracted"
            }

        result["next_state"] = "S5_ASSUMPTIONS_CHECK"
        # Build summary for confirmation
        result["system_response"] = _build_confirmation_summary(intake_packet, result["intake_packet_updates"])

    elif current_state == "S5_ASSUMPTIONS_CHECK":
        if extracted.get("assumptions"):
            result["assumptions"] = extracted["assumptions"]

        if extracted.get("ready_for_analysis"):
            result["next_state"] = "S6_RUN_STEP0"
            result["system_response"] = "Great, I have what I need. Starting the analysis now..."
        elif extracted.get("missing_critical"):
            result["system_response"] = f"Before we proceed: {extracted['missing_critical']}"

    return result


def _build_confirmation_summary(intake_packet: dict, updates: dict) -> str:
    """Build a confirmation summary for the user."""

    # Merge updates into packet for summary
    merged = {**intake_packet}
    for key, value in updates.items():
        merged[key] = value

    parts = ["Here's what I understand so far:\n"]

    if merged.get("use_case_intent", {}).get("value"):
        parts.append(f"**Goal:** {merged['use_case_intent']['value']}")

    if merged.get("industry", {}).get("value"):
        parts.append(f"**Industry:** {merged['industry']['value']}")

    if merged.get("opportunity_shape", {}).get("value"):
        opp_map = {
            "revenue": "Generate revenue / grow sales",
            "cost": "Reduce costs / save time",
            "risk": "Mitigate risk / improve compliance",
            "transform": "Transform operations"
        }
        parts.append(f"**Primary Goal:** {opp_map.get(merged['opportunity_shape']['value'], merged['opportunity_shape']['value'])}")

    if merged.get("jurisdiction", {}).get("value"):
        parts.append(f"**Location:** {merged['jurisdiction']['value']}")

    if merged.get("organization_size", {}).get("bucket"):
        parts.append(f"**Organization Size:** {merged['organization_size']['bucket']}")

    if merged.get("risk_posture", {}).get("level"):
        parts.append(f"**Risk Level:** {merged['risk_posture']['level']}")

    parts.append("\nDoes this look right? Let me know if anything's off.")

    return "\n".join(parts)


# =============================================================================
# FALLBACK HANDLERS - Graceful degradation when things go wrong
# =============================================================================

def _no_api_fallback(current_state: str, user_message: str, intake_packet: dict) -> dict:
    """Fallback when no API key is available."""

    # Use simple heuristics instead of LLM
    result = {
        "extracted": {},
        "next_state": current_state,
        "system_response": None,
        "intake_packet_updates": {},
        "assumptions": [],
        "fallback_reason": "no_api_key"
    }

    # Very basic extraction using the user's message directly
    if current_state == "S1_INTENT":
        result["intake_packet_updates"]["use_case_intent"] = {
            "value": user_message,
            "confidence": "low",
            "source": "user_direct"
        }

        # Simple industry detection
        industry = _detect_industry_simple(user_message)
        if industry:
            result["intake_packet_updates"]["industry"] = {
                "value": industry,
                "confidence": "low",
                "source": "keyword_match"
            }

        result["next_state"] = "S2_OPPORTUNITY"
        result["system_response"] = "Is your main goal to make more money, save time/cost, reduce risk, or change how you operate?"

    elif current_state == "S2_OPPORTUNITY":
        # Try to detect from keywords
        opp = _detect_opportunity_simple(user_message)
        if opp:
            result["intake_packet_updates"]["opportunity_shape"] = {
                "value": opp,
                "confidence": "low",
                "source": "keyword_match"
            }
        result["next_state"] = "S3_CONTEXT"
        result["system_response"] = "Where does this operate, and roughly how big is your organization?"

    # Continue with other states...

    return result


def _detect_industry_simple(text: str) -> Optional[str]:
    """Simple keyword-based industry detection."""
    text_lower = text.lower()

    industry_keywords = {
        "hospitality": ["banquet", "catering", "hotel", "restaurant", "event", "wedding", "venue", "food service", "hospitality"],
        "healthcare": ["medical", "hospital", "clinic", "patient", "health", "doctor", "nurse", "healthcare"],
        "retail": ["store", "shop", "retail", "merchandise", "customer", "sales floor", "inventory"],
        "finance": ["bank", "financial", "investment", "trading", "loan", "insurance", "fintech"],
        "manufacturing": ["factory", "production", "assembly", "manufacturing", "supply chain"],
        "technology": ["software", "app", "platform", "saas", "tech", "developer", "code"],
        "education": ["school", "university", "student", "teacher", "learning", "education"],
        "real_estate": ["property", "real estate", "rental", "landlord", "tenant", "building"],
        "logistics": ["shipping", "delivery", "warehouse", "logistics", "freight", "transport"],
    }

    for industry, keywords in industry_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                return industry

    return None


def _detect_opportunity_simple(text: str) -> Optional[str]:
    """Simple keyword-based opportunity detection."""
    text_lower = text.lower()

    if any(w in text_lower for w in ["revenue", "sales", "money", "profit", "income", "grow"]):
        return "revenue"
    if any(w in text_lower for w in ["cost", "save", "efficient", "time", "reduce", "automate"]):
        return "cost"
    if any(w in text_lower for w in ["risk", "compliance", "safety", "security", "audit"]):
        return "risk"
    if any(w in text_lower for w in ["transform", "change", "innovate", "disrupt", "new way"]):
        return "transform"

    return None


def _handle_parse_failure(current_state: str, user_message: str, raw_response: str, intake_packet: dict) -> dict:
    """Handle cases where JSON parsing failed."""

    result = {
        "extracted": {"_raw": raw_response},
        "next_state": current_state,
        "system_response": None,
        "intake_packet_updates": {},
        "assumptions": [],
        "parse_error": True
    }

    # Try to salvage what we can from the raw response
    if current_state == "S1_INTENT":
        # The response might still contain useful text
        result["intake_packet_updates"]["use_case_intent"] = {
            "value": user_message,  # Use user's message as fallback
            "confidence": "low",
            "source": "parse_failure_fallback"
        }
        result["next_state"] = "S2_OPPORTUNITY"
        result["system_response"] = "I captured that. Is your main goal to make more money, save time, reduce risk, or transform operations?"

    return result


def _graceful_fallback(current_state: str, user_message: str, intake_packet: dict, error: str) -> dict:
    """Graceful fallback when LLM call completely fails."""

    return {
        "extracted": {},
        "next_state": _get_next_state_default(current_state),
        "system_response": _get_fallback_response(current_state),
        "intake_packet_updates": _extract_basics_from_message(current_state, user_message),
        "assumptions": [],
        "error": error,
        "fallback_reason": "llm_error"
    }


def _get_next_state_default(current_state: str) -> str:
    """Get default next state for fallback progression."""
    state_order = ["S0_ENTRY", "S1_INTENT", "S2_OPPORTUNITY", "S3_CONTEXT", "S4_INTEGRATION_RISK", "S5_ASSUMPTIONS_CHECK"]
    try:
        idx = state_order.index(current_state)
        if idx < len(state_order) - 1:
            return state_order[idx + 1]
    except ValueError:
        pass
    return current_state


def _get_fallback_response(current_state: str) -> str:
    """Get fallback response for each state."""
    responses = {
        "S0_ENTRY": "What problem are you hoping an AI agent could help with?",
        "S1_INTENT": "Is your main goal to make more money, save time, reduce risk, or transform how you operate?",
        "S2_OPPORTUNITY": "Where does this operate, and roughly how big is your organization?",
        "S3_CONTEXT": "Does this need to connect to any existing systems?",
        "S4_INTEGRATION_RISK": "Let me summarize what I understand so far...",
        "S5_ASSUMPTIONS_CHECK": "Does this look correct? Let me know if anything needs adjustment."
    }
    return responses.get(current_state, "Tell me more about what you're looking for.")


def _extract_basics_from_message(current_state: str, user_message: str) -> dict:
    """Extract basic info from user message as fallback."""
    updates = {}

    if current_state in ["S0_ENTRY", "S1_INTENT"]:
        updates["use_case_intent"] = {
            "value": user_message,
            "confidence": "low",
            "source": "fallback_direct"
        }
        industry = _detect_industry_simple(user_message)
        if industry:
            updates["industry"] = {
                "value": industry,
                "confidence": "low",
                "source": "fallback_keyword"
            }

    return updates


def _generic_extraction(current_state: str, user_message: str, intake_packet: dict, client: ChatAnthropic) -> dict:
    """Generic extraction for unknown states."""

    prompt = f"""The user said: "{user_message}"

Extract any useful information about their project. Respond with JSON:
{{
    "summary": "Brief summary of what they said",
    "industry": "Industry if mentioned, or null",
    "location": "Location/jurisdiction if mentioned, or null",
    "size": "Organization size if mentioned, or null",
    "systems": ["Any systems/tools mentioned"],
    "unclear": "What's still unclear, or null"
}}"""

    try:
        response = client.invoke([
            SystemMessage(content="You are a helpful assistant. Respond with valid JSON only."),
            HumanMessage(content=prompt)
        ])

        extracted = _parse_json_response(response.content)

        return {
            "extracted": extracted or {},
            "next_state": current_state,
            "system_response": "Thanks for that. What else can you tell me?",
            "intake_packet_updates": {},
            "assumptions": []
        }
    except Exception:
        return _graceful_fallback(current_state, user_message, intake_packet, "generic_extraction_failed")


# =============================================================================
# CONVENIENCE FUNCTIONS - For integration with app.py
# =============================================================================

def get_initial_system_message() -> str:
    """Get the initial system message for S0_ENTRY."""
    return "Let's talk this through. You don't need to be precise — I'll make reasonable assumptions and show them to you before anything runs.\n\nWhat problem are you hoping an AI agent could help with?"


def should_proceed_to_research(intake_packet: dict) -> bool:
    """Check if we have enough data to proceed to Step 0 research."""

    required = ["use_case_intent", "industry"]

    for field in required:
        if not intake_packet.get(field, {}).get("value"):
            return False

    return True
