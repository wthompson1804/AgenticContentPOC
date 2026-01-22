"""
Chat LLM Module - LLM-powered inference for chat intake.

This module provides the missing intelligence layer that:
1. Interprets user intent using Claude
2. Generates context-aware follow-up questions
3. Synthesizes user input for the artifact
4. Extracts structured judgments semantically

Per PRD Part 4: Uses Claude to power adaptive branches B1-B4
"""

import os
import json
from typing import Optional
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


def get_chat_client(model: str = "claude-sonnet-4-20250514", api_key: Optional[str] = None) -> ChatAnthropic:
    """Get Claude client for chat inference."""
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None

    return ChatAnthropic(
        model=model,
        api_key=key,
        max_tokens=2048,
        temperature=0.3,
    )


CHAT_INFERENCE_SYSTEM_PROMPT = """You are an expert business analyst helping scope an AI agent project.

Your task is to analyze the user's message and extract structured information while generating helpful responses.

## Your Goals:
1. INTERPRET the user's intent - understand what they really mean, not just what they said
2. EXTRACT structured data from their natural language
3. SYNTHESIZE their input into clear, professional statements
4. IDENTIFY what information is still missing
5. GENERATE intelligent follow-up questions when needed

## Core Judgments to Extract (CJ01-CJ09):
- CJ01 Industry: What sector/industry is this for?
- CJ02 Use Case Intent: What problem are they trying to solve?
- CJ03 Opportunity Shape: revenue (make money), cost (save money), risk (reduce risk), transform (change operations)
- CJ04 Jurisdiction: Where does this operate? (US, EU, UK, Global, etc.)
- CJ05 Stakeholder Reality: Who benefits? Who decides?
- CJ06 Timeline: How urgent? (0-3mo, 3-6mo, 6-12mo, 12mo+, exploratory)
- CJ07 Org Scale: How big is the organization? (startup, mid-size, enterprise)
- CJ08 Integration Surface: What existing systems does this touch?
- CJ09 Risk Posture: How critical if this fails? (low, medium, high)

## Adaptive Branches (ask follow-ups when needed):
- B1: If use case is vague → "What changes if this works perfectly?"
- B2: If jurisdiction unclear → "Where are your users, and where is data stored/processed?"
- B3: If integration implied → "What's the system-of-record today? Is there an API?"
- B4: If regulated domain → "If this went wrong, what's the worst-case outcome?"

## Output Format:
Return a JSON object with this structure:
{
    "extracted": {
        "industry": {"value": "string or null", "confidence": "high/med/low"},
        "use_case_intent": {"value": "string or null", "confidence": "high/med/low"},
        "use_case_synthesized": "A clear, professional 1-2 sentence restatement of their goal",
        "opportunity_shape": {"value": "revenue/cost/risk/transform or null", "confidence": "high/med/low"},
        "jurisdiction": {"value": "string or null", "confidence": "high/med/low"},
        "timeline": {"bucket": "0-3mo/3-6mo/6-12mo/12mo+/exploratory or null", "confidence": "high/med/low"},
        "organization_size": {"bucket": "1-50/51-200/201-1000/1001-5000/5000+ or null", "confidence": "high/med/low"},
        "integration_surface": {"systems": ["list of systems"], "confidence": "high/med/low"},
        "risk_posture": {"level": "low/medium/high or null", "confidence": "high/med/low"}
    },
    "assumptions": [
        {"statement": "What you're assuming", "confidence": "high/med/low", "impact": "high/med/low"}
    ],
    "missing_critical": ["list of CJ IDs still needed, e.g. CJ01, CJ04"],
    "suggested_followup": "A natural follow-up question if needed, or null if you have enough",
    "branch_triggered": "B1/B2/B3/B4 or null",
    "ready_to_proceed": true/false
}

IMPORTANT:
- Be conversational, not robotic
- Make reasonable inferences but flag them as assumptions
- Don't ask about everything at once - prioritize what's most important
- If the user gives a rich description, extract as much as you can
- A single message might give you multiple judgments
"""


def process_chat_message(
    chat_history: list,
    current_state: str,
    intake_packet: dict,
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None
) -> dict:
    """
    Process the chat history with LLM to extract structured data and generate responses.

    This is the core intelligence layer that replaces keyword extraction.

    Args:
        chat_history: List of chat messages
        current_state: Current state in state machine (S0-S5)
        intake_packet: Current intake packet with existing data
        model: Claude model to use
        api_key: Optional API key

    Returns:
        dict with extracted data, assumptions, follow-up suggestion, etc.
    """
    client = get_chat_client(model, api_key)

    if not client:
        # Fallback to basic extraction if no API key
        return _fallback_extraction(chat_history, intake_packet)

    # Build context for Claude
    context = _build_inference_context(chat_history, current_state, intake_packet)

    try:
        response = client.invoke([
            SystemMessage(content=CHAT_INFERENCE_SYSTEM_PROMPT),
            HumanMessage(content=context)
        ])

        # Parse JSON response
        result = _parse_llm_response(response.content)
        return result

    except Exception as e:
        # Fallback on error
        return _fallback_extraction(chat_history, intake_packet)


def _build_inference_context(chat_history: list, current_state: str, intake_packet: dict) -> str:
    """Build the context prompt for LLM inference."""

    # Format chat history
    chat_text = ""
    for msg in chat_history[-10:]:  # Last 10 messages for context
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            chat_text += f"USER: {content}\n"
        elif role == "assistant":
            chat_text += f"ASSISTANT: {content}\n"

    # Format what we already know
    known_data = []
    if intake_packet.get("industry", {}).get("value"):
        known_data.append(f"- Industry: {intake_packet['industry']['value']}")
    if intake_packet.get("use_case_intent", {}).get("value"):
        known_data.append(f"- Use case: {intake_packet['use_case_intent']['value'][:100]}...")
    if intake_packet.get("jurisdiction", {}).get("value"):
        known_data.append(f"- Jurisdiction: {intake_packet['jurisdiction']['value']}")
    if intake_packet.get("opportunity_shape", {}).get("value"):
        known_data.append(f"- Opportunity: {intake_packet['opportunity_shape']['value']}")
    if intake_packet.get("timeline", {}).get("bucket"):
        known_data.append(f"- Timeline: {intake_packet['timeline']['bucket']}")
    if intake_packet.get("organization_size", {}).get("bucket"):
        known_data.append(f"- Org size: {intake_packet['organization_size']['bucket']}")

    known_text = "\n".join(known_data) if known_data else "Nothing confirmed yet."

    # State context
    state_guidance = {
        "S0_ENTRY": "Just starting. Get the user's core intent.",
        "S1_INTENT": "Focus on understanding what they want to achieve.",
        "S2_OPPORTUNITY": "Understand their primary goal: revenue, cost, risk, or transformation.",
        "S3_CONTEXT": "Get industry, jurisdiction, and org scale if not already known.",
        "S4_INTEGRATION_RISK": "Understand systems integration and risk tolerance.",
        "S5_ASSUMPTIONS_CHECK": "Summarize what you know and confirm assumptions."
    }

    guidance = state_guidance.get(current_state, "Continue gathering information.")

    return f"""## Current State: {current_state}
{guidance}

## What We Already Know:
{known_text}

## Conversation So Far:
{chat_text}

Analyze the conversation and extract all possible judgments. Return your analysis as JSON."""


def _parse_llm_response(content: str) -> dict:
    """Parse the LLM response into structured data."""
    # Try to extract JSON from response
    try:
        # Handle case where JSON is wrapped in markdown code block
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            # Try to find JSON object directly
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
            else:
                raise ValueError("No JSON found in response")

        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError, IndexError):
        # Return a basic structure if parsing fails
        return {
            "extracted": {},
            "assumptions": [],
            "missing_critical": ["CJ01", "CJ02", "CJ04"],
            "suggested_followup": None,
            "branch_triggered": None,
            "ready_to_proceed": False,
            "parse_error": True
        }


def _fallback_extraction(chat_history: list, intake_packet: dict) -> dict:
    """Fallback to basic keyword extraction when LLM unavailable."""
    from .judgment_engine import (
        extract_industry,
        extract_opportunity_shape,
        extract_jurisdiction,
        extract_timeline,
        extract_org_size,
        extract_systems,
    )

    # Concatenate user messages
    user_text = " ".join([
        msg["content"] for msg in chat_history
        if msg.get("role") == "user"
    ])

    extracted = {}

    # Industry
    industry, conf = extract_industry(user_text)
    if industry:
        extracted["industry"] = {"value": industry, "confidence": conf}

    # Opportunity
    opp, conf = extract_opportunity_shape(user_text)
    if opp:
        extracted["opportunity_shape"] = {"value": opp, "confidence": conf}

    # Jurisdiction
    jur, conf = extract_jurisdiction(user_text)
    if jur:
        extracted["jurisdiction"] = {"value": jur, "confidence": conf}

    # Timeline
    bucket, raw, conf = extract_timeline(user_text)
    if bucket:
        extracted["timeline"] = {"bucket": bucket, "confidence": conf}

    # Org size
    bucket, raw, conf = extract_org_size(user_text)
    if bucket:
        extracted["organization_size"] = {"bucket": bucket, "confidence": conf}

    # Systems
    systems = extract_systems(user_text)
    if systems:
        extracted["integration_surface"] = {"systems": systems, "confidence": "med"}

    # Use case (first substantial user message)
    for msg in chat_history:
        if msg.get("role") == "user" and len(msg.get("content", "")) > 20:
            extracted["use_case_intent"] = {
                "value": msg["content"][:500],
                "confidence": "med"
            }
            extracted["use_case_synthesized"] = msg["content"][:500]
            break

    # Determine what's missing
    missing = []
    if not extracted.get("industry"):
        missing.append("CJ01")
    if not extracted.get("use_case_intent"):
        missing.append("CJ02")
    if not extracted.get("jurisdiction"):
        missing.append("CJ04")

    return {
        "extracted": extracted,
        "assumptions": [],
        "missing_critical": missing,
        "suggested_followup": None,
        "branch_triggered": None,
        "ready_to_proceed": len(missing) == 0,
        "fallback_mode": True
    }


def generate_system_response(
    inference_result: dict,
    current_state: str,
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None
) -> str:
    """
    Generate a natural conversational response based on inference results.

    Args:
        inference_result: Output from process_chat_message
        current_state: Current state
        model: Claude model
        api_key: API key

    Returns:
        Natural language response string
    """
    client = get_chat_client(model, api_key)

    # If we have a suggested follow-up from inference, use it
    if inference_result.get("suggested_followup"):
        return inference_result["suggested_followup"]

    # If no client, use static responses
    if not client:
        return _get_static_response(current_state, inference_result)

    # Generate dynamic response
    prompt = f"""Based on this analysis, generate a brief, natural follow-up message.

Analysis:
{json.dumps(inference_result, indent=2)}

Current State: {current_state}

Rules:
- Be conversational, not robotic
- Keep it to 1-2 sentences
- If ready_to_proceed is true, summarize what you know and ask to confirm
- If missing critical info, ask about the most important missing item
- Don't be overly formal
- Don't repeat what the user just said

Generate ONLY the response text, no JSON or explanation."""

    try:
        response = client.invoke([
            HumanMessage(content=prompt)
        ])
        return response.content.strip()
    except Exception:
        return _get_static_response(current_state, inference_result)


def _get_static_response(current_state: str, inference_result: dict) -> str:
    """Get static response when LLM is unavailable."""
    missing = inference_result.get("missing_critical", [])

    if inference_result.get("ready_to_proceed"):
        return "I think I have a good picture. Let me summarize what I understand, and you can correct anything that's off."

    if "CJ01" in missing and "CJ04" in missing:
        return "Quick context so I don't give you something generic: what industry are you in and where does this operate?"

    if "CJ01" in missing:
        return "What industry or sector is this for?"

    if "CJ04" in missing:
        return "Where will this operate — US, EU, global?"

    if "CJ02" in missing:
        return "Can you tell me more about what problem you're trying to solve?"

    # Default progression
    state_responses = {
        "S0_ENTRY": "What problem are you hoping an AI agent could help with?",
        "S1_INTENT": "If this worked perfectly, what would change?",
        "S2_OPPORTUNITY": "Is your main goal to make money, save money, reduce risk, or transform operations?",
        "S3_CONTEXT": "How big is your organization, roughly?",
        "S4_INTEGRATION_RISK": "Does this need to connect to any existing systems?",
        "S5_ASSUMPTIONS_CHECK": "Here's what I understand. Let me know if anything's off.",
    }

    return state_responses.get(current_state, "Tell me more about what you're looking for.")


def synthesize_for_artifact(
    intake_packet: dict,
    inference_result: dict,
    section: str,
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None
) -> str:
    """
    Generate synthesized content for an artifact section.

    This transforms raw user input into polished, professional statements.

    Args:
        intake_packet: Current intake packet
        inference_result: Latest inference result
        section: Which artifact section (1-8)
        model: Claude model
        api_key: API key

    Returns:
        Synthesized content string
    """
    client = get_chat_client(model, api_key)

    if not client:
        # Return raw data if no LLM available
        return _get_raw_artifact_content(intake_packet, inference_result, section)

    section_prompts = {
        "1": """Synthesize "What You're Trying to Do" - a clear 2-3 sentence statement of the user's objective.
Focus on the business problem, not the technical solution.""",

        "2": """Synthesize "Opportunity Shape" - explain how this creates value.
One of: generating revenue, reducing costs, mitigating risk, or transforming operations.""",

        "3": """Synthesize "Operating Context" - summarize the business context.
Include: industry, jurisdiction, organization scale, timeline. Be concise.""",

        "4": """Synthesize "What the Agent Would Actually Do" - describe the agent's behavior.
Focus on actions, decisions, and boundaries. What will it do? What won't it do?""",
    }

    prompt = section_prompts.get(section)
    if not prompt:
        return _get_raw_artifact_content(intake_packet, inference_result, section)

    context = f"""User's raw input:
{intake_packet.get('use_case_intent', {}).get('value', 'Not provided')}

Extracted data:
{json.dumps(inference_result.get('extracted', {}), indent=2)}

{prompt}

Write ONLY the synthesized content (2-4 sentences max). Be professional but not stiff."""

    try:
        response = client.invoke([
            HumanMessage(content=context)
        ])
        return response.content.strip()
    except Exception:
        return _get_raw_artifact_content(intake_packet, inference_result, section)


def _get_raw_artifact_content(intake_packet: dict, inference_result: dict, section: str) -> str:
    """Get raw content when synthesis unavailable."""
    extracted = inference_result.get("extracted", {})

    if section == "1":
        synthesized = extracted.get("use_case_synthesized")
        if synthesized:
            return synthesized
        return intake_packet.get("use_case_intent", {}).get("value", "")

    if section == "2":
        opp = extracted.get("opportunity_shape", {}).get("value")
        if opp:
            descriptions = {
                "revenue": "Generate new revenue or increase sales",
                "cost": "Reduce costs or improve operational efficiency",
                "risk": "Mitigate risks or improve compliance",
                "transform": "Transform how the business operates"
            }
            return descriptions.get(opp, opp.title())
        return intake_packet.get("opportunity_shape", {}).get("value", "")

    if section == "3":
        parts = []
        if extracted.get("industry", {}).get("value"):
            parts.append(f"**Industry:** {extracted['industry']['value'].title()}")
        elif intake_packet.get("industry", {}).get("value"):
            parts.append(f"**Industry:** {intake_packet['industry']['value'].title()}")

        if extracted.get("jurisdiction", {}).get("value"):
            parts.append(f"**Jurisdiction:** {extracted['jurisdiction']['value']}")
        elif intake_packet.get("jurisdiction", {}).get("value"):
            parts.append(f"**Jurisdiction:** {intake_packet['jurisdiction']['value']}")

        if extracted.get("organization_size", {}).get("bucket"):
            parts.append(f"**Organization:** {extracted['organization_size']['bucket']} employees")
        elif intake_packet.get("organization_size", {}).get("bucket"):
            parts.append(f"**Organization:** {intake_packet['organization_size']['bucket']} employees")

        if extracted.get("timeline", {}).get("bucket"):
            parts.append(f"**Timeline:** {extracted['timeline']['bucket']}")
        elif intake_packet.get("timeline", {}).get("bucket"):
            parts.append(f"**Timeline:** {intake_packet['timeline']['bucket']}")

        return "\n".join(parts) if parts else ""

    if section == "4":
        content = extracted.get("use_case_synthesized", "")
        if not content:
            content = intake_packet.get("use_case_intent", {}).get("value", "")
        return content

    return ""
