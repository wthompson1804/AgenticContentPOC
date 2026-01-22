"""
Sidebar component for navigation and settings.
"""

import streamlit as st
from typing import Dict, Any


def render_sidebar(config: Dict[str, Any]) -> None:
    """Render the application sidebar with navigation and settings.

    Args:
        config: Application configuration dictionary
    """
    with st.sidebar:
        st.title("DTC Assessment")
        st.caption("AI Agent Capability Planning Tool")

        st.divider()

        # API Key input
        st.subheader("API Configuration")
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            value=st.session_state.get('api_key', ''),
            help="Enter your Anthropic API key to enable AI-powered features"
        )
        if api_key:
            st.session_state['api_key'] = api_key
            if api_key.startswith('sk-ant-'):
                st.success("API key configured", icon=":material/check_circle:")
            else:
                st.warning("Invalid key format", icon=":material/warning:")
        else:
            st.info("Demo mode active", icon=":material/info:")

        st.divider()

        # Current step indicator
        current_step = st.session_state.get('current_step', 0)
        steps = [
            "Research",
            "Requirements",
            "Agent Design",
            "Capability Mapping"
        ]

        st.subheader("Workflow Progress")
        for i, step_name in enumerate(steps):
            if i < current_step:
                st.markdown(f"~~{i}. {step_name}~~")
            elif i == current_step:
                st.markdown(f"**{i}. {step_name}** (current)")
            else:
                st.markdown(f"{i}. {step_name}")

        st.divider()

        # Settings section
        with st.expander("Settings", expanded=False):
            # Model is hardcoded to Opus - display only
            st.markdown("**Model:** Claude Opus 4")
            st.caption("claude-opus-4-20250514")

            st.checkbox(
                "Show Debug Info",
                key="show_debug",
                value=config.get('ui', {}).get('show_debug', False)
            )

        st.divider()

        # Quick actions
        st.subheader("Actions")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Reset", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key not in ['config']:
                        del st.session_state[key]
                st.rerun()

        with col2:
            if st.button("Export", use_container_width=True, disabled=current_step < 3):
                st.session_state['show_export'] = True

        st.divider()

        # Info section
        st.caption("Powered by:")
        st.caption("- Digital Twin Consortium CPT")
        st.caption("- Open Deep Research")
        st.caption("- Anthropic Claude")

        st.divider()
        st.caption("v1.0.0")
