"""
Chat Intake Module - Conversational state machine for intake flow.

Per PRD Part 7: Conversation State Machine (S0-S9)
Per PRD Part 8: UX Copy (System Prompts)
"""

from typing import TypedDict, Literal
from datetime import datetime
import uuid

from .judgment_engine import (
    IntakePacket,
    Assumption,
    update_judgments,
    can_proceed_to_research,
    is_regulated_domain,
    CORE_JUDGMENTS,
)
from .timebox import (
    TimeboxState,
    register_turn,
    should_offer_fast_path,
    mark_fast_path_offered,
    reached_hard_stop,
    should_force_proceed,
)


# State definitions
State = Literal[
    "S0_ENTRY",
    "S1_INTENT",
    "S2_OPPORTUNITY",
    "S3_CONTEXT",
    "S4_INTEGRATION",      # Asks about existing systems (split from S4_INTEGRATION_RISK)
    "S4_RISK",             # Asks about failure impact (split from S4_INTEGRATION_RISK)
    "S4_INTEGRATION_RISK", # Legacy - kept for backwards compatibility
    "S5_ASSUMPTIONS_CHECK",
    "S6_RUN_STEP0",
    "S7_CONFIRM_TYPE",
    "S8_RUN_STEP1_3",
    "S9_EXPORTS",
]

# User actions
UserAction = Literal[
    "message",          # User sent a message
    "fast_path",        # User clicked "Just run it"
    "confirm_proceed",  # User confirmed at checkpoint
    "fix_assumption",   # User wants to fix an assumption
    "ask_question",     # User wants most important question
    "confirm_type",     # User confirmed agent type
    "start_over",       # User wants to restart
]


class ChatMessage(TypedDict):
    """Chat message structure per PRD Part 5.1."""
    id: str
    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: str
    state: State
    metadata: dict


class ChatIntakeResult(TypedDict):
    """Result from chat intake step."""
    new_state: State
    system_messages: list[str]
    intake_packet: IntakePacket
    assumptions: list[Assumption]
    artifact_updates: dict
    open_questions: list[str]
    should_run_step0: bool
    buttons: list[dict] | None  # Optional action buttons


# UX Copy per PRD Part 8 - Conversational with examples
# Using predictive maintenance as the running example for consistency
UX_COPY = {
    "S0_ENTRY": (
        "Hi! I'm here to help you scope an AI agent project. I'll ask a few questions "
        "to understand what you're trying to do, then generate a detailed assessment.\n\n"
        "You don't need to be precise — I'll make reasonable assumptions and show them "
        "to you before anything runs."
    ),
    "S1_INTENT": (
        "What problem are you trying to solve with an AI agent?\n\n"
        "_Example: \"I want to predict when our factory machines will need maintenance "
        "before they break down.\"_"
    ),
    "S1_INTENT_FOLLOWUP": (
        "That's helpful. If this worked perfectly, what would be different?\n\n"
        "_Example: \"We'd catch problems days in advance instead of discovering them "
        "when the machine stops working.\"_"
    ),
    "S2_OPPORTUNITY": (
        "What would success look like? Are you mainly trying to:\n"
        "- **Grow revenue** (sell more, reach more customers)\n"
        "- **Save money or time** (efficiency, automation)\n"
        "- **Reduce risk** (errors, compliance, safety)\n"
        "- **Transform operations** (fundamentally change how you work)\n\n"
        "_Example: \"Mainly saving money — avoiding unplanned downtime and emergency repairs.\"_"
    ),
    "S3_CONTEXT": (
        "Quick context: Where does this operate, and roughly how big is your organization?\n\n"
        "_Example: \"Three manufacturing plants in the Midwest US, about 200 employees.\"_"
    ),
    "S4_INTEGRATION": (
        "Will this agent need to connect to any existing systems?\n\n"
        "Things like: CRM, calendar, payment processor, inventory system, databases, "
        "sensors, ERP, etc.\n\n"
        "_Example: \"Our machines have sensors feeding into a SCADA system, and we use "
        "SAP for maintenance scheduling.\"_"
    ),
    "S4_RISK": (
        "If the agent made a mistake, what's the worst that could happen?\n\n"
        "_Example: \"If it misses a prediction, a machine could fail unexpectedly — "
        "that's costly but not dangerous since we have safety shutoffs.\"_"
    ),
    "S5_ASSUMPTIONS_CHECK": (
        "Let me summarize what I've understood. Please correct anything that's off — "
        "this is what I'll base the research on:"
    ),
    "HARD_STOP": (
        "We've covered a lot of ground. I have enough to work with — ready to proceed?"
    ),
}

# Checkpoint buttons per PRD Part 8 S5
CHECKPOINT_BUTTONS = [
    {"id": "proceed", "label": "Looks right — proceed", "action": "confirm_proceed"},
    {"id": "fix", "label": "Fix one thing", "action": "fix_assumption"},
    {"id": "ask", "label": "Ask me the most important question", "action": "ask_question"},
    {"id": "fast", "label": "Just run it", "action": "fast_path"},
]

# Hard stop buttons per PRD Part 6.4
HARD_STOP_BUTTONS = [
    {"id": "proceed", "label": "Yes, run the analysis", "action": "confirm_proceed"},
    {"id": "more", "label": "Let me add one more thing", "action": "message"},
    {"id": "restart", "label": "Start over", "action": "start_over"},
]


def create_message(
    role: Literal["system", "user", "assistant"],
    content: str,
    state: State,
    metadata: dict | None = None
) -> ChatMessage:
    """Create a chat message with proper structure."""
    return {
        "id": f"msg_{uuid.uuid4().hex[:8]}",
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
        "state": state,
        "metadata": metadata or {
            "is_hard_question": False,
            "extracted_judgments": [],
            "voice_transcribed": False,
            "attachments": []
        }
    }


def get_initial_messages() -> list[ChatMessage]:
    """Get initial system messages to start the conversation."""
    return [
        create_message("assistant", UX_COPY["S0_ENTRY"], "S0_ENTRY"),
        create_message("assistant", UX_COPY["S1_INTENT"], "S1_INTENT"),
    ]


def determine_next_state(
    current_state: State,
    intake_packet: IntakePacket,
    timebox: TimeboxState,
    user_action: UserAction,
    config: dict | None = None
) -> State:
    """
    Determine the next state based on current state, data, and user action.

    State transitions per PRD Part 7.2:
    - Linear by default
    - Branching only at S4 if decision-critical
    - Hard stop at S5 unless fast-path
    """
    # Fast path always goes to S5 (assumptions check) then S6
    if user_action == "fast_path":
        if current_state in ["S0_ENTRY", "S1_INTENT", "S2_OPPORTUNITY", "S3_CONTEXT", "S4_INTEGRATION_RISK"]:
            return "S5_ASSUMPTIONS_CHECK"
        elif current_state == "S5_ASSUMPTIONS_CHECK":
            return "S6_RUN_STEP0"

    # Confirm proceed from checkpoint
    if user_action == "confirm_proceed":
        if current_state == "S5_ASSUMPTIONS_CHECK":
            return "S6_RUN_STEP0"
        elif current_state == "S7_CONFIRM_TYPE":
            return "S8_RUN_STEP1_3"

    # Start over
    if user_action == "start_over":
        return "S0_ENTRY"

    # Normal progression based on current state
    if current_state == "S0_ENTRY":
        return "S1_INTENT"

    elif current_state == "S1_INTENT":
        # Check if we have enough intent info
        use_case = intake_packet.get("use_case_intent", {}).get("value")
        if use_case and len(use_case) > 20:
            return "S2_OPPORTUNITY"
        return "S1_INTENT"  # Stay for follow-up

    elif current_state == "S2_OPPORTUNITY":
        opp = intake_packet.get("opportunity_shape", {}).get("value")
        if opp:
            return "S3_CONTEXT"
        return "S2_OPPORTUNITY"

    elif current_state == "S3_CONTEXT":
        # Check if we have industry, size, jurisdiction
        industry = intake_packet.get("industry", {}).get("value")
        jurisdiction = intake_packet.get("jurisdiction", {}).get("value")
        if industry and jurisdiction:
            # Check if we need integration/risk branch
            if is_regulated_domain(intake_packet) or intake_packet.get("integration_surface", {}).get("systems"):
                return "S4_INTEGRATION_RISK"
            return "S5_ASSUMPTIONS_CHECK"
        return "S3_CONTEXT"

    elif current_state == "S4_INTEGRATION_RISK":
        # Always proceed to assumptions after this
        return "S5_ASSUMPTIONS_CHECK"

    elif current_state == "S5_ASSUMPTIONS_CHECK":
        # Requires explicit user action to proceed
        return "S5_ASSUMPTIONS_CHECK"

    elif current_state == "S6_RUN_STEP0":
        return "S7_CONFIRM_TYPE"

    elif current_state == "S7_CONFIRM_TYPE":
        # Requires explicit confirmation
        return "S7_CONFIRM_TYPE"

    elif current_state == "S8_RUN_STEP1_3":
        return "S9_EXPORTS"

    return current_state


def generate_system_response(
    state: State,
    intake_packet: IntakePacket,
    assumptions: list[Assumption],
    open_questions: list[str],
    timebox: TimeboxState
) -> tuple[list[str], list[dict] | None]:
    """
    Generate system response messages and buttons for current state.

    Returns tuple of (messages, buttons).
    """
    messages = []
    buttons = None

    if state == "S1_INTENT":
        if not intake_packet.get("use_case_intent", {}).get("value"):
            messages.append(UX_COPY["S1_INTENT"])

    elif state == "S2_OPPORTUNITY":
        if not intake_packet.get("opportunity_shape", {}).get("value"):
            messages.append(UX_COPY["S2_OPPORTUNITY"])

    elif state == "S3_CONTEXT":
        missing = []
        if not intake_packet.get("industry", {}).get("value"):
            missing.append("industry")
        if not intake_packet.get("jurisdiction", {}).get("value"):
            missing.append("jurisdiction")
        if not intake_packet.get("organization_size", {}).get("bucket"):
            missing.append("organization size")

        if missing:
            messages.append(UX_COPY["S3_CONTEXT"])
        else:
            # We have enough, acknowledge and move on
            messages.append("Got it. Let me put together what I've understood.")

    elif state == "S4_INTEGRATION_RISK":
        # Check what we need to ask
        if is_regulated_domain(intake_packet):
            if not intake_packet.get("risk_posture", {}).get("worst_case"):
                messages.append(UX_COPY["S4_RISK"])
        if intake_packet.get("integration_surface", {}).get("systems"):
            messages.append(UX_COPY["S4_INTEGRATION"])

    elif state == "S5_ASSUMPTIONS_CHECK":
        # Build assumptions summary
        messages.append(UX_COPY["S5_ASSUMPTIONS_CHECK"])

        # Format intake summary
        summary_parts = []
        if intake_packet.get("industry", {}).get("value"):
            summary_parts.append(f"**Industry:** {intake_packet['industry']['value']}")
        if intake_packet.get("use_case_intent", {}).get("value"):
            intent = intake_packet["use_case_intent"]["value"][:200]
            summary_parts.append(f"**Use Case:** {intent}...")
        if intake_packet.get("opportunity_shape", {}).get("value"):
            summary_parts.append(f"**Goal:** {intake_packet['opportunity_shape']['value']}")
        if intake_packet.get("jurisdiction", {}).get("value"):
            summary_parts.append(f"**Jurisdiction:** {intake_packet['jurisdiction']['value']}")
        if intake_packet.get("organization_size", {}).get("bucket"):
            summary_parts.append(f"**Org Size:** {intake_packet['organization_size']['bucket']}")
        if intake_packet.get("timeline", {}).get("bucket"):
            summary_parts.append(f"**Timeline:** {intake_packet['timeline']['bucket']}")

        if summary_parts:
            messages.append("\n".join(summary_parts))

        # Show assumptions if any
        if assumptions:
            assumption_text = "\n**Assumptions I'm making:**\n"
            for a in assumptions[:5]:  # Show top 5
                conf_indicator = "?" if a["confidence"] == "low" else ""
                assumption_text += f"- {a['statement']}{conf_indicator}\n"
            messages.append(assumption_text)

        buttons = CHECKPOINT_BUTTONS

    return messages, buttons


def chat_intake_step(
    chat_history: list[ChatMessage],
    intake_packet: IntakePacket,
    artifact_doc: dict,
    assumptions: list[Assumption],
    timebox: TimeboxState,
    current_state: State,
    user_message: str | None = None,
    user_action: UserAction = "message",
    config: dict | None = None
) -> ChatIntakeResult:
    """
    Process one step of the chat intake flow.

    This is the main entry point for the chat intake state machine.

    Args:
        chat_history: Current chat history
        intake_packet: Current intake packet
        artifact_doc: Current artifact document
        assumptions: Current assumptions list
        timebox: Current timebox state
        current_state: Current state in state machine
        user_message: Optional user message content
        user_action: Type of user action
        config: Optional config dict

    Returns:
        ChatIntakeResult with updated state and outputs
    """
    new_chat_history = chat_history.copy()
    should_run_step0 = False
    artifact_updates = {}

    # Add user message to history if provided
    if user_message:
        user_msg = create_message("user", user_message, current_state, {
            "is_hard_question": False,
            "extracted_judgments": [],
            "voice_transcribed": False,
            "attachments": []
        })
        new_chat_history.append(user_msg)

        # Update timebox
        timebox = register_turn(timebox, is_hard_question=False, config=config)

    # Update judgments from chat history
    updated_packet, new_assumptions, open_questions = update_judgments(
        new_chat_history, intake_packet
    )

    # Check for hard stop
    if reached_hard_stop(timebox, config) and current_state not in ["S5_ASSUMPTIONS_CHECK", "S6_RUN_STEP0", "S7_CONFIRM_TYPE", "S8_RUN_STEP1_3", "S9_EXPORTS"]:
        if should_force_proceed(timebox):
            # Force proceed to assumptions check
            new_state = "S5_ASSUMPTIONS_CHECK"
        else:
            # Offer hard stop options
            system_msgs = [UX_COPY["HARD_STOP"]]
            buttons = HARD_STOP_BUTTONS

            for msg in system_msgs:
                new_chat_history.append(create_message("assistant", msg, current_state))

            return {
                "new_state": current_state,
                "system_messages": system_msgs,
                "intake_packet": updated_packet,
                "assumptions": new_assumptions,
                "artifact_updates": artifact_updates,
                "open_questions": open_questions,
                "should_run_step0": False,
                "buttons": buttons
            }

    # Determine next state
    new_state = determine_next_state(
        current_state, updated_packet, timebox, user_action, config
    )

    # Check if we should offer fast path
    if should_offer_fast_path(timebox, config) and new_state not in ["S5_ASSUMPTIONS_CHECK", "S6_RUN_STEP0"]:
        timebox = mark_fast_path_offered(timebox)
        # Don't interrupt flow, just note it's available

    # Generate system response
    system_msgs, buttons = generate_system_response(
        new_state, updated_packet, new_assumptions, open_questions, timebox
    )

    # Add system messages to history
    for msg in system_msgs:
        new_chat_history.append(create_message("assistant", msg, new_state))

    # Determine artifact updates based on state
    if new_state in ["S1_INTENT", "S2_OPPORTUNITY"]:
        artifact_updates["section_1"] = True
        artifact_updates["section_2"] = True
    elif new_state in ["S3_CONTEXT", "S4_INTEGRATION_RISK"]:
        artifact_updates["section_3"] = True
    elif new_state == "S5_ASSUMPTIONS_CHECK":
        artifact_updates["section_7"] = True

    # Check if we should run Step 0
    if new_state == "S6_RUN_STEP0":
        can_proceed, missing = can_proceed_to_research(updated_packet)
        should_run_step0 = can_proceed

    return {
        "new_state": new_state,
        "system_messages": system_msgs,
        "intake_packet": updated_packet,
        "assumptions": new_assumptions,
        "artifact_updates": artifact_updates,
        "open_questions": open_questions,
        "should_run_step0": should_run_step0,
        "buttons": buttons
    }


def handle_fix_assumption(
    assumption_id: str,
    new_value: str,
    intake_packet: IntakePacket,
    assumptions: list[Assumption]
) -> tuple[IntakePacket, list[Assumption]]:
    """
    Handle user fixing an assumption.

    Per PRD Part 14: Updates may trigger dependency ripple.
    """
    # Find the assumption
    assumption = None
    for a in assumptions:
        if a["id"] == assumption_id:
            assumption = a
            break

    if not assumption:
        return intake_packet, assumptions

    # Determine which field this affects
    statement_lower = assumption["statement"].lower()
    changed_field = None

    if "industry" in statement_lower:
        changed_field = "industry"
        intake_packet["industry"] = {"value": new_value, "confidence": "high", "source": "user_edit"}
    elif "jurisdiction" in statement_lower:
        changed_field = "jurisdiction"
        intake_packet["jurisdiction"] = {"value": new_value, "confidence": "high", "source": "user_edit"}
    elif "timeline" in statement_lower:
        changed_field = "timeline"
        intake_packet["timeline"]["raw"] = new_value
        intake_packet["timeline"]["source"] = "user_edit"
        intake_packet["timeline"]["confidence"] = "high"
    elif "org" in statement_lower or "size" in statement_lower:
        changed_field = "organization_size"
        intake_packet["organization_size"]["raw"] = new_value
        intake_packet["organization_size"]["source"] = "user_edit"
        intake_packet["organization_size"]["confidence"] = "high"

    # Mark assumption as corrected
    for a in assumptions:
        if a["id"] == assumption_id:
            a["status"] = "corrected"
            break

    # Trigger dependency ripple if needed
    if changed_field:
        intake_packet, assumptions, _ = update_judgments(
            [], intake_packet, changed_field=changed_field
        )

    return intake_packet, assumptions


def get_most_important_question(
    intake_packet: IntakePacket,
    assumptions: list[Assumption]
) -> str:
    """
    Get the most important question to ask the user.

    Per PRD Part 8 S5: "Ask me the most important question" button.
    """
    # Check blockers first
    can_proceed, missing = can_proceed_to_research(intake_packet)
    if missing:
        cj_id = missing[0]
        cj_info = CORE_JUDGMENTS.get(cj_id, {})
        field_name = cj_info.get("name", "information")
        return f"What's the {field_name.lower()} for this use case?"

    # Check low-confidence high-impact assumptions
    for a in assumptions:
        if a["confidence"] == "low" and a["impact"] == "high":
            return f"I assumed {a['statement'].lower()}. Is that right?"

    # Default question
    return "Is there anything else important I should know before we proceed?"
