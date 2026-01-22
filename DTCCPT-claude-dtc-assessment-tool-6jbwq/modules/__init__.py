"""
DTC AI Agent Capability Assessment Tool - Core Modules

This package contains the core business logic for:
- Chat Intake: Conversational intake state machine (Phase 5)
- Artifact Panel: Progressive 2-pager generation (Phase 5)
- Judgment Engine: CJ extraction and inference (Phase 5)
- Timebox: Turn counting and fast-path (Phase 5)
- Research: Open Deep Research integration
- Requirements: Step 1 business requirements generation
- Agent Design: Step 2 agent type assessment
- Capability Mapping: Step 3 CPT mapping
- Export: Document generation utilities
"""

from .data_loader import load_capabilities, load_prompt, load_config
from .research import conduct_research, format_research_for_display, ResearchResult
from .requirements import generate_requirements, format_requirements_for_display, RequirementsResult
from .agent_design import generate_agent_design, format_agent_design_for_display, AgentDesignResult
from .capability_mapping import generate_capability_mapping, format_capability_mapping_for_display, CapabilityMappingResult

# Phase 5: Chat-First Intake modules
from .timebox import (
    init_timebox,
    register_turn,
    should_offer_fast_path,
    reached_hard_stop,
    should_force_proceed,
    get_timebox_status,
    TimeboxState,
)
from .judgment_engine import (
    init_intake_packet,
    update_judgments,
    build_use_case_context_blob,
    can_proceed_to_research,
    is_regulated_domain,
    IntakePacket,
    Assumption,
)
from .chat_intake import (
    chat_intake_step,
    get_initial_messages,
    create_message,
    handle_fix_assumption,
    get_most_important_question,
    ChatMessage,
    State,
)
from .artifact_panel import (
    init_artifact,
    apply_artifact_updates,
    render_artifact_md,
    render_artifact_html,
    get_overall_progress,
    ArtifactDoc,
)

# Phase 5: Export extensions
from .export import (
    render_internal_brief_md,
    render_exec_brief_md,
    render_email_md,
    render_slide_outline_md,
    get_available_export_formats,
)

__all__ = [
    # Data loading
    'load_capabilities',
    'load_prompt',
    'load_config',
    # Chat Intake (Phase 5)
    'chat_intake_step',
    'get_initial_messages',
    'create_message',
    'handle_fix_assumption',
    'get_most_important_question',
    'ChatMessage',
    'State',
    # Artifact Panel (Phase 5)
    'init_artifact',
    'apply_artifact_updates',
    'render_artifact_md',
    'render_artifact_html',
    'get_overall_progress',
    'ArtifactDoc',
    # Judgment Engine (Phase 5)
    'init_intake_packet',
    'update_judgments',
    'build_use_case_context_blob',
    'can_proceed_to_research',
    'is_regulated_domain',
    'IntakePacket',
    'Assumption',
    # Timebox (Phase 5)
    'init_timebox',
    'register_turn',
    'should_offer_fast_path',
    'reached_hard_stop',
    'should_force_proceed',
    'get_timebox_status',
    'TimeboxState',
    # Research (Step 0)
    'conduct_research',
    'format_research_for_display',
    'ResearchResult',
    # Requirements (Step 1)
    'generate_requirements',
    'format_requirements_for_display',
    'RequirementsResult',
    # Agent Design (Step 2)
    'generate_agent_design',
    'format_agent_design_for_display',
    'AgentDesignResult',
    # Capability Mapping (Step 3)
    'generate_capability_mapping',
    'format_capability_mapping_for_display',
    'CapabilityMappingResult',
    # Export Extensions (Phase 5)
    'render_internal_brief_md',
    'render_exec_brief_md',
    'render_email_md',
    'render_slide_outline_md',
    'get_available_export_formats',
]
