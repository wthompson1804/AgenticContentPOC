"""
DTC AI Agent Capability Assessment Tool

A Streamlit application for assessing AI agent capabilities using the
Digital Twin Consortium's Capabilities Periodic Table (CPT) framework.

This tool:
1. Conducts deep research on industry/regulatory context (Enhanced Step 0)
2. Generates business requirements (Step 1)
3. Assesses agent type (T0-T4) and designs architecture (Step 2)
4. Maps capabilities to the 45-capability CPT (Step 3)
"""

import streamlit as st
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import modules
from modules.data_loader import load_config, load_capabilities, load_prompt
from modules.research import conduct_research, format_research_for_display
from modules.requirements import generate_requirements, format_requirements_for_display
from modules.agent_design import generate_agent_design, format_agent_design_for_display, AGENT_TYPE_CRITERIA
from modules.capability_mapping import generate_capability_mapping, format_capability_mapping_for_display

# Phase 5: Chat-First Intake modules
from modules.timebox import init_timebox, register_turn, get_timebox_status, should_offer_fast_path
from modules.judgment_engine import init_intake_packet, update_judgments, build_use_case_context_blob, can_proceed_to_research
from modules.chat_intake import chat_intake_step, get_initial_messages, create_message, State
from modules.artifact_panel import init_artifact, apply_artifact_updates, render_artifact_html, get_overall_progress

# Import components
from components.sidebar import render_sidebar
from components.progress import (
    render_progress_indicator,
    render_step_header,
    render_step_navigation
)
from components.input_form import render_input_form, render_input_summary
from components.research_display import render_research_results, render_research_error
from components.chat_ui import (
    render_chat_history,
    render_action_buttons,
    render_timebox_indicator,
    render_fast_path_button,
)


# Page configuration
st.set_page_config(
    page_title="DTC AI Agent Capability Assessment",
    page_icon=":robot_face:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6B7280;
        margin-bottom: 2rem;
    }
    .capability-card {
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
    .step-container {
        background-color: #F9FAFB;
        border-radius: 12px;
        padding: 24px;
        margin: 16px 0;
    }
    .citation {
        font-size: 0.85rem;
        color: #6B7280;
        border-left: 3px solid #3B82F6;
        padding-left: 12px;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    # Legacy form-based mode defaults
    defaults = {
        'current_step': 0,
        'form_data': None,
        'research_results': None,
        'requirements_output': None,
        'agent_design_output': None,
        'capability_mapping': None,
        'assessment_complete': False,
        'show_export': False,
        'selected_model': 'claude-sonnet-4-20250514',  # Default model
    }

    # Phase 5: Chat-first mode defaults (per PRD Part 12.3)
    chat_defaults = {
        'intake_mode': 'chat',  # 'chat' or 'form' - toggleable
        'chat_history': [],
        'current_state': 'S1_INTENT',  # Start at S1 since S0 is just intro text
        'intake_packet': None,  # Will be initialized as dict
        'assumptions': [],
        'artifact_doc': None,  # Will be initialized as dict
        'timebox': None,  # Will be initialized as dict
        'uploaded_files': [],
        'links': [],
        'confirmed_type': None,  # CRITICAL: Gate for Step 3
        'chat_buttons': None,  # Current action buttons
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    for key, default_value in chat_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    # Initialize complex objects if None
    if st.session_state.intake_packet is None:
        st.session_state.intake_packet = init_intake_packet()
    if st.session_state.artifact_doc is None:
        st.session_state.artifact_doc = init_artifact()
    if st.session_state.timebox is None:
        st.session_state.timebox = init_timebox()
    if not st.session_state.chat_history:
        st.session_state.chat_history = get_initial_messages()


def get_api_key() -> str:
    """Get API key from session state or environment."""
    # Check session state first (UI input)
    session_key = st.session_state.get('api_key', '')
    if session_key and session_key.startswith('sk-ant-'):
        return session_key
    # Fall back to environment variable
    return os.getenv('ANTHROPIC_API_KEY', '')


def check_api_key() -> bool:
    """Check if the Anthropic API key is configured."""
    api_key = get_api_key()
    return api_key.startswith('sk-ant-')


def render_step_0_research():
    """Render Step 0: Research phase."""
    render_step_header(
        0,
        "Industry & Regulatory Research",
        "Conduct comprehensive research to ground the assessment in current, cited intelligence"
    )

    if st.session_state.form_data is None:
        # Show input form
        submitted, form_data = render_input_form()

        if submitted:
            st.session_state.form_data = form_data
            st.rerun()
    else:
        # Show input summary and research controls
        render_input_summary(st.session_state.form_data)

        st.divider()

        if st.session_state.research_results is None:
            # Research not yet started
            st.markdown("### Ready to Research")
            st.markdown(
                "Click below to conduct deep research on your use case. "
                "This will analyze 5 key areas:"
            )

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                - **Industry AI Adoption** - Current deployment rates, case studies
                - **Regulatory Environment** - Relevant standards and requirements
                - **Technical Integration** - Common stacks, patterns, challenges
                """)
            with col2:
                st.markdown("""
                - **Risk & Failure Modes** - Documented failures, root causes
                - **Economic Viability** - ROI data, cost structures
                """)

            if not check_api_key():
                st.warning("Anthropic API key required for research. Please configure ANTHROPIC_API_KEY.")
                if st.button("Skip Research (Demo Mode)", use_container_width=True):
                    st.session_state.research_results = {
                        'status': 'demo',
                        'summary': {
                            'industry': st.session_state.form_data.get('industry'),
                            'use_case': st.session_state.form_data.get('use_case'),
                            'jurisdiction': st.session_state.form_data.get('jurisdiction'),
                        },
                        'preliminary_assessment': {
                            'go_no_go': 'caution',
                            'recommended_type': 'T2',
                            'confidence_level': 'medium',
                            'key_risks': ['Demo mode - no actual research conducted'],
                            'critical_success_factors': ['Configure API key for real research'],
                        },
                        'research_areas': {
                            'industry_adoption': {'name': 'Industry AI Adoption', 'findings': 'Demo mode - configure API for actual research', 'confidence': 'low'},
                            'regulatory_environment': {'name': 'Regulatory Environment', 'findings': 'Demo mode - configure API for actual research', 'confidence': 'low'},
                            'technical_integration': {'name': 'Technical Integration', 'findings': 'Demo mode - configure API for actual research', 'confidence': 'low'},
                            'risk_failure_modes': {'name': 'Risk & Failure Modes', 'findings': 'Demo mode - configure API for actual research', 'confidence': 'low'},
                            'economic_viability': {'name': 'Economic Viability', 'findings': 'Demo mode - configure API for actual research', 'confidence': 'low'},
                        },
                        'sources': [],
                    }
                    st.rerun()
            else:
                if st.button("Start Deep Research", type="primary", use_container_width=True):
                    with st.spinner("Conducting deep research... This may take 1-2 minutes."):
                        try:
                            result = conduct_research(
                                industry=st.session_state.form_data.get('industry', ''),
                                use_case=st.session_state.form_data.get('use_case', ''),
                                jurisdiction=st.session_state.form_data.get('jurisdiction', ''),
                                organization_size=st.session_state.form_data.get('organization_size', 'Enterprise'),
                                timeline=st.session_state.form_data.get('timeline', 'Pilot Project'),
                                model=st.session_state.selected_model,
                                api_key=get_api_key(),
                            )
                            st.session_state.research_results = format_research_for_display(result)
                        except Exception as e:
                            st.session_state.research_results = {
                                'status': 'error',
                                'error': str(e),
                            }
                        st.rerun()
        else:
            # Show research results
            st.markdown("### Research Results")

            if st.session_state.research_results.get('error'):
                render_research_error(st.session_state.research_results['error'])
            elif st.session_state.research_results.get('status') == 'demo':
                st.warning("Running in demo mode. Configure ANTHROPIC_API_KEY for actual research.")
                render_research_results(st.session_state.research_results)
            else:
                render_research_results(st.session_state.research_results)

            # Navigation
            render_step_navigation(
                current_step=0,
                can_proceed=True,
                show_confirmation=True
            )


def render_step_1_requirements():
    """Render Step 1: Business Requirements Generation."""
    render_step_header(
        1,
        "Business Requirements",
        "Extract comprehensive business requirements based on research and use case context"
    )

    render_input_summary(st.session_state.form_data)

    st.divider()

    if st.session_state.requirements_output is None:
        st.markdown("### Generate Requirements")
        st.markdown(
            "This step will analyze your use case and research findings to generate "
            "detailed business requirements following the DTC methodology."
        )

        # Show the DTC prompt being used (collapsed)
        with st.expander("View DTC Prompt Template", expanded=False):
            try:
                prompt = load_prompt(1)
                st.code(prompt[:2000] + "..." if len(prompt) > 2000 else prompt, language="markdown")
            except FileNotFoundError:
                st.warning("Prompt template not found")

        if not check_api_key():
            st.warning("Anthropic API key required. Please configure ANTHROPIC_API_KEY.")
            if st.button("Skip Requirements (Demo Mode)", use_container_width=True):
                st.session_state.requirements_output = {
                    'status': 'demo',
                    'full_text': '## Demo Mode\n\nConfigure ANTHROPIC_API_KEY to generate actual requirements.\n\n### Sample Requirements\n- REQ-01: System shall provide AI agent capabilities\n- REQ-02: System shall integrate with existing infrastructure',
                    'sections': {},
                }
                st.rerun()
        else:
            if st.button("Generate Requirements", type="primary", use_container_width=True):
                with st.spinner("Generating business requirements..."):
                    try:
                        # Get boundaries and assumptions from intake (PRD Part 12.2 - MANDATORY)
                        boundaries = st.session_state.intake_packet.get("boundaries", {}).get("value") if st.session_state.intake_packet else None
                        assumptions = st.session_state.assumptions if st.session_state.assumptions else None

                        result = generate_requirements(
                            form_data=st.session_state.form_data,
                            research_results=st.session_state.research_results or {},
                            model=st.session_state.selected_model,
                            api_key=get_api_key(),
                            boundaries=boundaries,
                            assumptions=assumptions,
                        )
                        st.session_state.requirements_output = format_requirements_for_display(result)
                    except Exception as e:
                        st.session_state.requirements_output = {
                            'status': 'error',
                            'error': str(e),
                        }
                    st.rerun()
    else:
        # Show requirements output
        st.markdown("### Generated Requirements")

        if st.session_state.requirements_output.get('error'):
            st.error(f"Error: {st.session_state.requirements_output['error']}")
        elif st.session_state.requirements_output.get('status') == 'demo':
            st.warning("Running in demo mode. Configure ANTHROPIC_API_KEY for actual requirements.")
            st.markdown(st.session_state.requirements_output.get('full_text', ''))
        else:
            # Display requirements
            st.markdown(st.session_state.requirements_output.get('full_text', ''))

        render_step_navigation(
            current_step=1,
            can_proceed=True,
            show_confirmation=True
        )


def render_step_2_agent_design():
    """Render Step 2: Agent Type Assessment and Design."""
    render_step_header(
        2,
        "Agent Type Assessment",
        "Assess the appropriate agent type (T0-T4) and design the agent architecture"
    )

    # Display agent type reference
    with st.expander("Agent Type Reference (T0-T4)", expanded=True):
        for type_id, type_info in AGENT_TYPE_CRITERIA.items():
            st.markdown(f"**{type_id}: {type_info.get('name', '')}** - {type_info.get('description', '')}")

    st.divider()

    if st.session_state.agent_design_output is None:
        st.markdown("### Assess Agent Type")

        # Show the DTC prompt being used (collapsed)
        with st.expander("View DTC Prompt Template", expanded=False):
            try:
                prompt = load_prompt(2)
                st.code(prompt[:2000] + "..." if len(prompt) > 2000 else prompt, language="markdown")
            except FileNotFoundError:
                st.warning("Prompt template not found")

        if not check_api_key():
            st.warning("Anthropic API key required. Please configure ANTHROPIC_API_KEY.")
            if st.button("Skip Assessment (Demo Mode)", use_container_width=True):
                st.session_state.agent_design_output = {
                    'status': 'demo',
                    'recommended_type': 'T2',
                    'confirmed_type': None,
                    'type_info': AGENT_TYPE_CRITERIA.get('T2', {}),
                    'justification': 'Demo mode - configure API for actual assessment',
                    'architecture_summary': 'Demo mode - configure API for actual architecture',
                    'full_document': '## Demo Mode\n\nConfigure ANTHROPIC_API_KEY for actual agent design.',
                }
                st.rerun()
        else:
            if st.button("Assess Agent Type", type="primary", use_container_width=True):
                with st.spinner("Assessing agent type and generating design..."):
                    try:
                        # Get boundaries and assumptions from intake (PRD Part 12.2 - MANDATORY)
                        boundaries = st.session_state.intake_packet.get("boundaries", {}).get("value") if st.session_state.intake_packet else None
                        assumptions = st.session_state.assumptions if st.session_state.assumptions else None

                        result = generate_agent_design(
                            form_data=st.session_state.form_data,
                            research_results=st.session_state.research_results or {},
                            requirements_output=st.session_state.requirements_output or {},
                            model=st.session_state.selected_model,
                            api_key=get_api_key(),
                            boundaries=boundaries,
                            assumptions=assumptions,
                        )
                        st.session_state.agent_design_output = format_agent_design_for_display(result)
                    except Exception as e:
                        st.session_state.agent_design_output = {
                            'status': 'error',
                            'error': str(e),
                        }
                    st.rerun()
    else:
        # Show agent design output
        st.markdown("### Agent Type Assessment")

        if st.session_state.agent_design_output.get('error'):
            st.error(f"Error: {st.session_state.agent_design_output['error']}")
        else:
            recommended = st.session_state.agent_design_output.get('recommended_type', 'T2')
            type_info = st.session_state.agent_design_output.get('type_info', {})

            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown(f"""
                <div style="
                    background-color: #3B82F620;
                    border: 3px solid #3B82F6;
                    border-radius: 12px;
                    padding: 24px;
                    text-align: center;
                ">
                    <div style="font-size: 3rem; font-weight: bold; color: #3B82F6;">{recommended}</div>
                    <div style="font-size: 1.1rem; font-weight: bold;">{type_info.get('name', '')}</div>
                    <div style="font-size: 0.9rem; color: #6B7280; margin-top: 8px;">Recommended Type</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"**Description:** {type_info.get('description', '')}")

                if st.session_state.agent_design_output.get('justification'):
                    st.markdown("**Justification:**")
                    st.markdown(st.session_state.agent_design_output['justification'])

            # Human-in-the-loop confirmation
            st.divider()
            st.markdown("### Confirm Agent Type")
            st.markdown("Review the recommendation and confirm or adjust the agent type before proceeding.")

            confirmed_type = st.selectbox(
                "Select or confirm the agent type for capability mapping:",
                options=['T0', 'T1', 'T2', 'T3', 'T4'],
                index=['T0', 'T1', 'T2', 'T3', 'T4'].index(recommended),
                key="agent_type_selector"
            )
            st.session_state.agent_design_output['confirmed_type'] = confirmed_type

            # Show full design document
            with st.expander("View Full Design Document", expanded=False):
                st.markdown(st.session_state.agent_design_output.get('full_document', ''))

        render_step_navigation(
            current_step=2,
            can_proceed=True,
            show_confirmation=True
        )


def render_step_3_capability_mapping():
    """Render Step 3: Capability Mapping."""
    render_step_header(
        3,
        "Capability Mapping",
        "Map requirements to the 45-capability CPT and generate visualization"
    )

    # Load capabilities
    try:
        capabilities = load_capabilities()
        cap_count = sum(
            len(cat.get('capabilities', {}))
            for cat in capabilities.get('capabilities', {}).values()
        )
        st.info(f"Loaded {cap_count} capabilities from DTC CPT framework")
    except Exception as e:
        st.error(f"Error loading capabilities: {e}")
        capabilities = None

    st.divider()

    if st.session_state.capability_mapping is None:
        st.markdown("### Generate Capability Mapping")

        # Show the DTC prompt being used (collapsed)
        with st.expander("View DTC Prompt Template", expanded=False):
            try:
                prompt = load_prompt(3)
                st.code(prompt[:2000] + "..." if len(prompt) > 2000 else prompt, language="markdown")
            except FileNotFoundError:
                st.warning("Prompt template not found")

        if not check_api_key():
            st.warning("Anthropic API key required. Please configure ANTHROPIC_API_KEY.")
            if st.button("Skip Mapping (Demo Mode)", use_container_width=True):
                st.session_state.capability_mapping = {
                    'status': 'demo',
                    'agent_type': st.session_state.agent_design_output.get('confirmed_type', 'T2') if st.session_state.agent_design_output else 'T2',
                    'total_mapped': 0,
                    'essential_count': 0,
                    'advanced_count': 0,
                    'optional_count': 0,
                    'mappings': [],
                    'full_document': '## Demo Mode\n\nConfigure ANTHROPIC_API_KEY for actual capability mapping.',
                    'html_visualization': '<html><body><h1>Demo Mode</h1><p>Configure API key for visualization.</p></body></html>',
                }
                st.rerun()
        else:
            if st.button("Generate Capability Mapping", type="primary", use_container_width=True):
                with st.spinner("Mapping capabilities... This may take 1-2 minutes."):
                    try:
                        # Get boundaries and assumptions from intake (PRD Part 12.2 - MANDATORY)
                        boundaries = st.session_state.intake_packet.get("boundaries", {}).get("value") if st.session_state.intake_packet else None
                        assumptions = st.session_state.assumptions if st.session_state.assumptions else None

                        result = generate_capability_mapping(
                            form_data=st.session_state.form_data,
                            research_results=st.session_state.research_results or {},
                            requirements_output=st.session_state.requirements_output or {},
                            agent_design_output=st.session_state.agent_design_output or {},
                            model=st.session_state.selected_model,
                            api_key=get_api_key(),
                            boundaries=boundaries,
                            assumptions=assumptions,
                        )
                        st.session_state.capability_mapping = format_capability_mapping_for_display(result)
                    except Exception as e:
                        st.session_state.capability_mapping = {
                            'status': 'error',
                            'error': str(e),
                        }
                    st.rerun()
    else:
        # Show capability mapping
        st.markdown("### Capability Mapping Results")

        if st.session_state.capability_mapping.get('error'):
            st.error(f"Error: {st.session_state.capability_mapping['error']}")
        else:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Total Mapped",
                    st.session_state.capability_mapping.get('total_mapped', 0)
                )
            with col2:
                st.metric(
                    "Essential",
                    st.session_state.capability_mapping.get('essential_count', 0)
                )
            with col3:
                st.metric(
                    "Advanced",
                    st.session_state.capability_mapping.get('advanced_count', 0)
                )
            with col4:
                st.metric(
                    "Optional",
                    st.session_state.capability_mapping.get('optional_count', 0)
                )

            st.divider()

            # Tabbed interface for capability categories
            st.markdown("#### Capability Priority View")

            # Create tabs for priority categories
            tab_all, tab_essential, tab_advanced, tab_optional = st.tabs([
                "All Capabilities",
                f"Essential ({st.session_state.capability_mapping.get('essential_count', 0)})",
                f"Advanced ({st.session_state.capability_mapping.get('advanced_count', 0)})",
                f"Optional ({st.session_state.capability_mapping.get('optional_count', 0)})"
            ])

            # Get mapping lookups
            mappings = st.session_state.capability_mapping.get('mappings', [])
            mapping_lookup = {m.get('id'): m for m in mappings}
            essential_ids = set(st.session_state.capability_mapping.get('essential_capabilities', []))
            advanced_ids = set(st.session_state.capability_mapping.get('advanced_capabilities', []))
            optional_ids = set(st.session_state.capability_mapping.get('optional_capabilities', []))

            # Category colors
            category_colors = {
                "PK": "#3B82F6",  # blue
                "CG": "#F97316",  # orange
                "LA": "#A855F7",  # purple
                "AE": "#6B7280",  # gray
                "IC": "#14B8A6",  # teal
                "GS": "#EF4444",  # red
            }

            def render_cpt_table(highlight_ids: set = None, filter_mode: str = "all"):
                """Render the full CPT table with highlighting."""
                if capabilities is None:
                    st.warning("Capabilities not loaded")
                    return

                # Legend
                st.markdown("""
                <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; padding: 12px; background: #F9FAFB; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 14px; height: 14px; background: #3B82F6; border-radius: 3px;"></div><span style="font-size: 0.8rem;">PK: Perception</span></div>
                    <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 14px; height: 14px; background: #F97316; border-radius: 3px;"></div><span style="font-size: 0.8rem;">CG: Cognition</span></div>
                    <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 14px; height: 14px; background: #A855F7; border-radius: 3px;"></div><span style="font-size: 0.8rem;">LA: Learning</span></div>
                    <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 14px; height: 14px; background: #6B7280; border-radius: 3px;"></div><span style="font-size: 0.8rem;">AE: Action</span></div>
                    <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 14px; height: 14px; background: #14B8A6; border-radius: 3px;"></div><span style="font-size: 0.8rem;">IC: Interaction</span></div>
                    <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 14px; height: 14px; background: #EF4444; border-radius: 3px;"></div><span style="font-size: 0.8rem;">GS: Governance</span></div>
                </div>
                """, unsafe_allow_html=True)

                # Build all capability cards
                all_cards_html = []

                for cat_id, cat_data in capabilities.get('capabilities', {}).items():
                    cat_name = cat_data.get('name', cat_id)
                    color = category_colors.get(cat_id, '#6B7280')

                    for cap_id, cap_data in cat_data.get('capabilities', {}).items():
                        cap_name = cap_data.get('name', '')
                        cap_desc = cap_data.get('description', '')

                        # Determine if this capability should be highlighted
                        is_highlighted = highlight_ids is None or cap_id in highlight_ids
                        mapping = mapping_lookup.get(cap_id)
                        priority = mapping.get('priority', '') if mapping else ''
                        justification = mapping.get('justification', '') if mapping else ''

                        # Priority badge
                        priority_badge = ""
                        if priority:
                            badge_colors = {
                                "essential": "#10B981",
                                "high": "#3B82F6",
                                "medium": "#F59E0B",
                                "optional": "#9CA3AF",
                            }
                            badge_color = badge_colors.get(priority, "#6B7280")
                            priority_badge = f'<span style="background: {badge_color}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 0.6rem; font-weight: bold;">{priority.upper()}</span>'

                        # Styling based on highlight state
                        opacity = "1" if is_highlighted else "0.25"
                        transform = "scale(1)" if is_highlighted else "scale(0.95)"
                        filter_style = "" if is_highlighted else "grayscale(70%)"

                        card_html = f'''
                        <div style="
                            background: white;
                            border: 2px solid {color};
                            border-radius: 8px;
                            overflow: hidden;
                            opacity: {opacity};
                            transform: {transform};
                            filter: {filter_style};
                            transition: all 0.3s ease;
                            min-height: 90px;
                        " class="cap-card" onmouseover="this.style.transform='translateY(-4px) scale(1.02)'; this.style.boxShadow='0 8px 25px rgba(0,0,0,0.15)';" onmouseout="this.style.transform='{transform}'; this.style.boxShadow='none';">
                            <div style="background: {color}20; border-bottom: 2px solid {color}; padding: 8px 10px; display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: bold; font-size: 0.85rem;">{cap_id}</span>
                                {priority_badge}
                            </div>
                            <div style="padding: 8px 10px;">
                                <div style="font-size: 0.8rem; font-weight: 500; line-height: 1.3; margin-bottom: 4px;">{cap_name}</div>
                                <div style="font-size: 0.7rem; color: #6B7280; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">{cap_desc[:100]}...</div>
                                {f'<div style="font-size: 0.65rem; color: #4B5563; margin-top: 6px; padding-top: 6px; border-top: 1px solid #E5E7EB;"><strong>Why:</strong> {justification[:80]}...</div>' if justification and is_highlighted else ''}
                            </div>
                        </div>
                        '''
                        all_cards_html.append(card_html)

                # Render as grid
                grid_html = f'''
                <div style="
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                    gap: 12px;
                    padding: 8px 0;
                ">
                    {''.join(all_cards_html)}
                </div>
                '''
                st.markdown(grid_html, unsafe_allow_html=True)

            # Render content for each tab
            with tab_all:
                st.caption("Showing all 45 CPT capabilities. Mapped capabilities are highlighted with priority badges.")
                all_mapped = essential_ids | advanced_ids | optional_ids
                render_cpt_table(highlight_ids=all_mapped if all_mapped else None, filter_mode="all")

            with tab_essential:
                if essential_ids:
                    st.caption(f"Highlighting {len(essential_ids)} essential (must-have) capabilities. Other capabilities are grayed out.")
                    render_cpt_table(highlight_ids=essential_ids, filter_mode="essential")
                else:
                    st.info("No essential capabilities identified in this assessment.")
                    render_cpt_table(highlight_ids=set(), filter_mode="essential")

            with tab_advanced:
                if advanced_ids:
                    st.caption(f"Highlighting {len(advanced_ids)} advanced (should-have) capabilities. Other capabilities are grayed out.")
                    render_cpt_table(highlight_ids=advanced_ids, filter_mode="advanced")
                else:
                    st.info("No advanced capabilities identified in this assessment.")
                    render_cpt_table(highlight_ids=set(), filter_mode="advanced")

            with tab_optional:
                if optional_ids:
                    st.caption(f"Highlighting {len(optional_ids)} optional (nice-to-have) capabilities. Other capabilities are grayed out.")
                    render_cpt_table(highlight_ids=optional_ids, filter_mode="optional")
                else:
                    st.info("No optional capabilities identified in this assessment.")
                    render_cpt_table(highlight_ids=set(), filter_mode="optional")

            st.divider()

            # Full document and HTML preview in expanders
            with st.expander("View Full Mapping Document", expanded=False):
                st.markdown(st.session_state.capability_mapping.get('full_document', ''))

            # HTML Preview
            if st.session_state.capability_mapping.get('html_visualization'):
                with st.expander("Preview Interactive HTML Visualization", expanded=False):
                    st.components.v1.html(
                        st.session_state.capability_mapping['html_visualization'],
                        height=600,
                        scrolling=True
                    )

        render_step_navigation(
            current_step=3,
            can_proceed=True,
            show_confirmation=True,
            next_label="Complete Assessment"
        )


def render_completion():
    """Render the assessment completion screen."""
    st.balloons()

    st.markdown("## Assessment Complete!")
    st.success("Your AI Agent Capability Assessment has been generated.")

    # Summary
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Industry", st.session_state.form_data.get('industry', 'N/A'))

    with col2:
        agent_type = 'N/A'
        if st.session_state.agent_design_output:
            agent_type = st.session_state.agent_design_output.get(
                'confirmed_type',
                st.session_state.agent_design_output.get('recommended_type', 'N/A')
            )
        st.metric("Agent Type", agent_type)

    with col3:
        cap_count = 0
        if st.session_state.capability_mapping:
            cap_count = st.session_state.capability_mapping.get('total_mapped', 0)
        st.metric("Capabilities Mapped", cap_count)

    st.divider()

    st.markdown("### Export Options")

    # Import extended export functions
    from modules.export import (
        render_internal_brief_md,
        render_exec_brief_md,
        render_email_md,
        render_slide_outline_md
    )

    # Row 1: Primary outputs (PRD Part 10)
    st.markdown("#### Primary Outputs")
    col1, col2, col3, col4 = st.columns(4)

    # Check if we have enough data for exports
    has_artifact = st.session_state.artifact_doc is not None
    has_form_data = st.session_state.form_data is not None

    with col1:
        # Internal Brief (Private Reality Check)
        if has_artifact and has_form_data:
            internal_brief = render_internal_brief_md(
                st.session_state.artifact_doc,
                st.session_state.form_data,
                st.session_state.assumptions
            )
            st.download_button(
                "Internal Brief",
                data=internal_brief,
                file_name="internal_brief.md",
                mime="text/markdown",
                use_container_width=True,
                help="Full assessment with all assumptions and confidence levels"
            )
        else:
            st.button("Internal Brief", disabled=True, use_container_width=True)

    with col2:
        # Executive Brief (Public Narrative)
        if has_artifact and has_form_data:
            exec_brief = render_exec_brief_md(
                st.session_state.artifact_doc,
                st.session_state.form_data
            )
            st.download_button(
                "Executive Brief",
                data=exec_brief,
                file_name="exec_brief.md",
                mime="text/markdown",
                use_container_width=True,
                help="One-page summary for stakeholders (no assumptions)"
            )
        else:
            st.button("Executive Brief", disabled=True, use_container_width=True)

    with col3:
        # Email Draft
        if has_artifact and has_form_data:
            email_draft = render_email_md(
                st.session_state.artifact_doc,
                st.session_state.form_data,
                recipient_type="stakeholder"
            )
            st.download_button(
                "Email Draft",
                data=email_draft,
                file_name="email_draft.md",
                mime="text/markdown",
                use_container_width=True,
                help="Neutral framing for internal coordination"
            )
        else:
            st.button("Email Draft", disabled=True, use_container_width=True)

    with col4:
        # Slide Outline
        if has_artifact and has_form_data:
            slide_outline = render_slide_outline_md(
                st.session_state.artifact_doc,
                st.session_state.form_data
            )
            st.download_button(
                "Slide Outline",
                data=slide_outline,
                file_name="slide_outline.md",
                mime="text/markdown",
                use_container_width=True,
                help="Title + takeaway + 3 bullets per slide"
            )
        else:
            st.button("Slide Outline", disabled=True, use_container_width=True)

    # Row 2: Technical outputs
    st.markdown("#### Technical Outputs")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.session_state.capability_mapping and st.session_state.capability_mapping.get('full_document'):
            st.download_button(
                "Capability Mapping (MD)",
                data=st.session_state.capability_mapping['full_document'],
                file_name="capability_mapping.md",
                mime="text/markdown",
                use_container_width=True
            )
        else:
            st.button("Capability Mapping (MD)", disabled=True, use_container_width=True)

    with col2:
        if st.session_state.capability_mapping and st.session_state.capability_mapping.get('html_visualization'):
            st.download_button(
                "CPT Visualization (HTML)",
                data=st.session_state.capability_mapping['html_visualization'],
                file_name="cpt_visualization.html",
                mime="text/html",
                use_container_width=True
            )
        else:
            st.button("CPT Visualization (HTML)", disabled=True, use_container_width=True)

    with col3:
        # Complete package
        if st.session_state.capability_mapping:
            package = f"""# DTC AI Agent Capability Assessment - Complete Package

## Use Case
**Industry:** {st.session_state.form_data.get('industry', 'N/A')}
**Jurisdiction:** {st.session_state.form_data.get('jurisdiction', 'N/A')}

### Description
{st.session_state.form_data.get('use_case', 'N/A')}

---

## Research Findings
{st.session_state.research_results.get('research_areas', {}).get('industry_adoption', {}).get('findings', 'N/A') if st.session_state.research_results else 'N/A'}

---

## Requirements
{st.session_state.requirements_output.get('full_text', 'N/A') if st.session_state.requirements_output else 'N/A'}

---

## Agent Design
**Recommended Type:** {agent_type}

{st.session_state.agent_design_output.get('full_document', 'N/A') if st.session_state.agent_design_output else 'N/A'}

---

## Capability Mapping
{st.session_state.capability_mapping.get('full_document', 'N/A')}
"""
            st.download_button(
                "Complete Package",
                data=package,
                file_name="dtc_assessment_complete.md",
                mime="text/markdown",
                use_container_width=True,
                type="primary"
            )
        else:
            st.button("Complete Package", disabled=True, use_container_width=True)

    st.divider()

    if st.button("Start New Assessment", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def render_chat_intake():
    """
    Render the chat-first intake interface.

    Phase 5: Two-column layout with chat (left) and artifact (right).
    """
    config = load_config()
    ui_config = config.get('ui', {})
    chat_width = ui_config.get('chat_panel_width', 0.6)

    # Create two-column layout
    col_chat, col_artifact = st.columns([chat_width, 1 - chat_width])

    with col_chat:
        st.markdown("### Let's scope your AI agent")

        # Render chat history
        chat_container = st.container(height=400)
        with chat_container:
            render_chat_history(st.session_state.chat_history)

        # Render action buttons if available
        if st.session_state.chat_buttons:
            st.divider()
            render_action_buttons(
                st.session_state.chat_buttons,
                on_click=handle_chat_action
            )

        # Chat input
        st.divider()
        if prompt := st.chat_input(
            "Type your message...",
            disabled=st.session_state.current_state in ["S6_RUN_STEP0", "S8_RUN_STEP1_3"]
        ):
            handle_chat_message(prompt)

    with col_artifact:
        st.markdown("### Assessment Summary")

        # Progress indicator
        progress = get_overall_progress(st.session_state.artifact_doc)
        st.progress(progress / 100, text=f"{progress}% complete")

        # Render artifact HTML
        artifact_html = render_artifact_html(st.session_state.artifact_doc)
        st.components.v1.html(artifact_html, height=450, scrolling=True)

        # Show assumptions if any
        if st.session_state.assumptions:
            with st.expander(f"Assumptions ({len(st.session_state.assumptions)})", expanded=False):
                for a in st.session_state.assumptions[:5]:
                    status_icon = "" if a["status"] == "confirmed" else "?"
                    st.markdown(f"- {a['statement']}{status_icon}")

    # Sidebar additions for chat mode
    render_timebox_indicator(get_timebox_status(st.session_state.timebox, config))

    # Fast path button in sidebar
    render_fast_path_button(
        on_click=handle_fast_path,
        show=st.session_state.current_state not in ["S5_ASSUMPTIONS_CHECK", "S6_RUN_STEP0", "S7_CONFIRM_TYPE"]
    )


def handle_chat_message(message: str):
    """Handle user chat message with per-state LLM processing (v2 architecture)."""
    config = load_config()

    # CRITICAL: Add user message to chat history BEFORE processing
    user_msg = create_message("user", message, st.session_state.current_state)
    st.session_state.chat_history.append(user_msg)

    # === V2: Per-State LLM Processing ===
    # Each state has its own focused prompt instead of one giant prompt
    from modules.chat_llm_v2 import process_state

    # Get API key
    api_key = get_api_key()

    # Process this state with focused LLM call
    result = process_state(
        current_state=st.session_state.current_state,
        user_message=message,
        intake_packet=st.session_state.intake_packet,
        chat_history=st.session_state.chat_history,
        model=st.session_state.selected_model,
        api_key=api_key
    )

    # Apply intake packet updates
    for key, value in result.get("intake_packet_updates", {}).items():
        st.session_state.intake_packet[key] = value

    # Add assumptions
    for a in result.get("assumptions", []):
        st.session_state.assumptions.append({
            "id": f"A{len(st.session_state.assumptions) + 1}",
            "statement": a.get("statement", ""),
            "confidence": a.get("confidence", "med"),
            "impact": a.get("impact", "med"),
            "needs_confirmation": a.get("confidence") == "low",
            "status": "assumed"
        })

    # Add system response to chat history
    if result.get("system_response"):
        st.session_state.chat_history.append(
            create_message("assistant", result["system_response"], result.get("next_state", st.session_state.current_state))
        )

    # Update state
    new_state = result.get("next_state", st.session_state.current_state)
    st.session_state.current_state = new_state

    # Handle checkpoint buttons at S5
    if new_state == "S5_ASSUMPTIONS_CHECK":
        st.session_state.chat_buttons = [
            {"id": "proceed", "label": "Looks right — proceed", "action": "confirm_proceed"},
            {"id": "fix", "label": "Fix one thing", "action": "fix_assumption"},
            {"id": "ask", "label": "Ask me the most important question", "action": "ask_question"},
            {"id": "fast", "label": "Just run it", "action": "fast_path"},
        ]
    else:
        st.session_state.chat_buttons = None

    # Update artifact with extracted data
    st.session_state.artifact_doc = apply_artifact_updates(
        st.session_state.artifact_doc,
        st.session_state.intake_packet,
        st.session_state.assumptions,
        {}
    )

    # Update timebox
    st.session_state.timebox = register_turn(st.session_state.timebox, config=config)

    # Check if we should run Step 0
    if new_state == "S6_RUN_STEP0":
        transition_to_step_0()

    st.rerun()


def apply_artifact_updates_with_synthesis(
    artifact_doc: dict,
    intake_packet: dict,
    assumptions: list,
    inference_result: dict,
    model: str = "claude-sonnet-4-20250514",
    api_key: str = None
) -> dict:
    """Apply artifact updates using LLM synthesis for better content."""
    from modules.chat_llm import synthesize_for_artifact
    from modules.artifact_panel import update_section

    updated = artifact_doc.copy()

    # Section 1: What You're Trying to Do (SYNTHESIZED)
    if intake_packet.get("use_case_intent", {}).get("value"):
        synthesized = synthesize_for_artifact(
            intake_packet, inference_result, "1", model, api_key
        )
        if synthesized:
            updated = update_section(
                updated, "section_1", synthesized,
                confidence=intake_packet["use_case_intent"].get("confidence", "med"),
                source="S1_INTENT_LLM"
            )

    # Section 2: Opportunity Shape (SYNTHESIZED)
    if intake_packet.get("opportunity_shape", {}).get("value"):
        synthesized = synthesize_for_artifact(
            intake_packet, inference_result, "2", model, api_key
        )
        if synthesized:
            updated = update_section(
                updated, "section_2", synthesized,
                confidence=intake_packet["opportunity_shape"].get("confidence", "med"),
                source="S2_OPPORTUNITY_LLM"
            )

    # Section 3: Operating Context (SYNTHESIZED)
    has_context = (
        intake_packet.get("industry", {}).get("value") or
        intake_packet.get("jurisdiction", {}).get("value")
    )
    if has_context:
        synthesized = synthesize_for_artifact(
            intake_packet, inference_result, "3", model, api_key
        )
        if synthesized:
            updated = update_section(
                updated, "section_3", synthesized,
                confidence="med",
                source="S3_CONTEXT_LLM"
            )

    # Section 4: What the Agent Would Actually Do (SYNTHESIZED)
    if intake_packet.get("use_case_intent", {}).get("value"):
        synthesized = synthesize_for_artifact(
            intake_packet, inference_result, "4", model, api_key
        )
        if synthesized:
            boundaries = intake_packet.get("boundaries", {}).get("value")
            content = synthesized
            if boundaries:
                content += f"\n\n**Boundaries:** {boundaries}"
            updated = update_section(
                updated, "section_4", content,
                confidence="med",
                source="S1_INTENT_LLM"
            )

    # Section 7: Assumptions (from LLM inference)
    if assumptions:
        from modules.artifact_panel import update_section
        assumption_lines = []
        for a in assumptions[:8]:
            status_icon = "" if a.get("status") == "confirmed" else "?"
            assumption_lines.append(
                f"- [{a.get('id', 'A?')}] {a.get('statement', '')} "
                f"(confidence: {a.get('confidence', 'med')}, impact: {a.get('impact', 'med')}){status_icon}"
            )
        if assumption_lines:
            updated = update_section(
                updated, "section_7", "\n".join(assumption_lines),
                confidence="med",
                source="INFERENCE_LLM"
            )

    return updated


def handle_chat_action(action: str):
    """Handle chat action button click."""
    config = load_config()

    if action == "fast_path":
        handle_fast_path()
        return

    if action == "confirm_proceed":
        # User confirmed at checkpoint - proceed to Step 0
        st.session_state.current_state = "S6_RUN_STEP0"
        transition_to_step_0()
        st.rerun()
        return

    if action == "fix_assumption":
        # Show fix UI (simplified - in full impl would show editable assumptions)
        st.session_state.chat_history.append(
            create_message("assistant", "Which assumption would you like to correct?", st.session_state.current_state)
        )
        st.session_state.chat_buttons = None
        st.rerun()
        return

    if action == "ask_question":
        from modules.chat_intake import get_most_important_question
        question = get_most_important_question(
            st.session_state.intake_packet,
            st.session_state.assumptions
        )
        st.session_state.chat_history.append(
            create_message("assistant", question, st.session_state.current_state)
        )
        st.session_state.chat_buttons = None
        st.rerun()
        return

    if action == "start_over":
        # Reset chat state
        st.session_state.chat_history = get_initial_messages()
        st.session_state.current_state = "S0_ENTRY"
        st.session_state.intake_packet = init_intake_packet()
        st.session_state.assumptions = []
        st.session_state.artifact_doc = init_artifact()
        st.session_state.timebox = init_timebox()
        st.session_state.chat_buttons = None
        st.rerun()


def handle_fast_path():
    """Handle fast-path button click."""
    config = load_config()

    # Mark fast path in timebox
    from modules.timebox import mark_fast_path_offered
    st.session_state.timebox = mark_fast_path_offered(st.session_state.timebox)

    # Add message
    st.session_state.chat_history.append(
        create_message("user", "Just run it.", st.session_state.current_state)
    )
    st.session_state.chat_history.append(
        create_message("assistant", "Got it! Proceeding with current assumptions. I'll flag anything I'm uncertain about.", st.session_state.current_state)
    )

    # Transition to Step 0
    st.session_state.current_state = "S6_RUN_STEP0"
    transition_to_step_0()
    st.rerun()


def transition_to_step_0():
    """Transition from chat intake to Step 0 (Research)."""
    # Build form_data from intake_packet for compatibility with existing step modules
    intake = st.session_state.intake_packet

    st.session_state.form_data = {
        'industry': intake.get('industry', {}).get('value', 'Technology'),
        'use_case': intake.get('use_case_intent', {}).get('value', ''),
        'jurisdiction': intake.get('jurisdiction', {}).get('value', 'US'),
        'organization_size': intake.get('organization_size', {}).get('bucket', 'Enterprise'),
        'timeline': intake.get('timeline', {}).get('bucket', 'Pilot Project'),
    }

    # Switch to form-based flow for Steps 0-3 (they're already implemented)
    st.session_state.intake_mode = 'form'
    st.session_state.current_step = 0


def main():
    """Main application entry point."""
    # Initialize
    initialize_session_state()

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        config = {}

    # Render sidebar
    render_sidebar(config)

    # Model selector in sidebar
    st.sidebar.divider()
    st.sidebar.markdown("### Model Selection")
    available_models = config.get('available_models', {})
    model_options = list(available_models.keys()) if available_models else ['claude-sonnet-4-20250514']
    model_names = {
        model_id: available_models.get(model_id, {}).get('name', model_id)
        for model_id in model_options
    }
    selected_model = st.sidebar.selectbox(
        "Select Claude model:",
        options=model_options,
        index=model_options.index(st.session_state.selected_model) if st.session_state.selected_model in model_options else 0,
        format_func=lambda x: model_names.get(x, x),
        key="model_selector",
        help="Opus: most capable. Sonnet: balanced (recommended). Haiku: fastest."
    )
    if selected_model != st.session_state.selected_model:
        st.session_state.selected_model = selected_model

    # Mode toggle in sidebar
    st.sidebar.divider()
    st.sidebar.markdown("### Intake Mode")
    mode = st.sidebar.radio(
        "Select intake mode:",
        options=["chat", "form"],
        index=0 if st.session_state.intake_mode == "chat" else 1,
        format_func=lambda x: "Chat (Conversational)" if x == "chat" else "Form (Classic)",
        key="mode_selector",
        help="Chat mode: conversational intake with progressive artifact. Form mode: traditional wizard."
    )

    # Handle mode switch
    if mode != st.session_state.intake_mode:
        if mode == "chat" and st.session_state.current_step == 0 and st.session_state.form_data is None:
            # Can switch to chat if at beginning
            st.session_state.intake_mode = mode
            st.rerun()
        elif mode == "form":
            # Can always switch to form
            st.session_state.intake_mode = mode
            st.rerun()

    # Main content area
    st.markdown('<div class="main-header">DTC AI Agent Capability Assessment</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Ground your AI agent planning in current research using the Digital Twin Consortium methodology</div>',
        unsafe_allow_html=True
    )

    # Check API key
    if not check_api_key():
        st.warning(
            "Anthropic API key not configured. Please set ANTHROPIC_API_KEY in your environment. "
            "Demo mode available with limited functionality."
        )

    # Route based on intake mode
    if st.session_state.intake_mode == "chat" and st.session_state.current_state not in ["S6_RUN_STEP0", "S7_CONFIRM_TYPE", "S8_RUN_STEP1_3", "S9_EXPORTS"]:
        # Chat-first intake mode (Phase 5)
        render_chat_intake()
    else:
        # Form-based mode (legacy) or post-intake steps
        # Progress indicator
        render_progress_indicator(st.session_state.current_step)

        st.divider()

        # Render current step
        if st.session_state.assessment_complete:
            render_completion()
        elif st.session_state.current_step == 0:
            render_step_0_research()
        elif st.session_state.current_step == 1:
            render_step_1_requirements()
        elif st.session_state.current_step == 2:
            render_step_2_agent_design()
        elif st.session_state.current_step == 3:
            render_step_3_capability_mapping()


if __name__ == "__main__":
    main()
