"""
Progress indicator component for the 4-step workflow.
"""

import streamlit as st
from typing import List, Optional


def render_progress_indicator(current_step: int, total_steps: int = 4) -> None:
    """Render a visual progress indicator for the workflow.

    Args:
        current_step: Current step index (0-3)
        total_steps: Total number of steps
    """
    steps = [
        {"name": "Research", "icon": "search", "description": "Industry & regulatory research"},
        {"name": "Requirements", "icon": "file-text", "description": "Business requirements extraction"},
        {"name": "Agent Design", "icon": "cpu", "description": "Agent type assessment (T0-T4)"},
        {"name": "Capability Mapping", "icon": "grid-3x3", "description": "CPT capability mapping"},
    ]

    # Create columns for each step
    cols = st.columns(total_steps)

    for i, (col, step) in enumerate(zip(cols, steps)):
        with col:
            # Determine step status
            if i < current_step:
                status = "completed"
                color = "#10B981"  # green
                icon = ":white_check_mark:"
            elif i == current_step:
                status = "current"
                color = "#3B82F6"  # blue
                icon = ":arrow_forward:"
            else:
                status = "pending"
                color = "#9CA3AF"  # gray
                icon = ":white_circle:"

            # Render step indicator
            st.markdown(
                f"""
                <div style="text-align: center; padding: 10px;">
                    <div style="
                        width: 40px;
                        height: 40px;
                        border-radius: 50%;
                        background-color: {color};
                        color: white;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 0 auto 8px auto;
                        font-weight: bold;
                    ">{i}</div>
                    <div style="font-weight: {'bold' if status == 'current' else 'normal'}; color: {color};">
                        {step['name']}
                    </div>
                    <div style="font-size: 0.8em; color: #6B7280;">
                        {step['description']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Progress bar
    progress = current_step / (total_steps - 1) if total_steps > 1 else 0
    st.progress(progress)


def render_step_header(step_number: int, title: str, description: str) -> None:
    """Render a header for the current step.

    Args:
        step_number: Step number (0-3)
        title: Step title
        description: Step description
    """
    st.markdown(f"## Step {step_number}: {title}")
    st.markdown(f"*{description}*")
    st.divider()


def render_step_navigation(
    current_step: int,
    can_proceed: bool = False,
    on_back: Optional[callable] = None,
    on_next: Optional[callable] = None,
    next_label: str = "Continue",
    show_confirmation: bool = True
) -> None:
    """Render navigation buttons for step transitions.

    Args:
        current_step: Current step index
        can_proceed: Whether the user can proceed to next step
        on_back: Callback for back button
        on_next: Callback for next button
        next_label: Label for the next button
        show_confirmation: Whether to show confirmation checkbox
    """
    st.divider()

    # Back button (outside the highlighted section)
    if current_step > 0:
        col_back, _ = st.columns([1, 4])
        with col_back:
            if st.button("Back", use_container_width=True):
                if on_back:
                    on_back()
                else:
                    st.session_state['current_step'] = current_step - 1
                    st.rerun()

    # Highlighted action section with checkbox and continue button INSIDE
    if can_proceed:
        # Use custom CSS to style the container
        st.markdown("""
        <style>
        div[data-testid="stVerticalBlock"]:has(> div.action-bar-marker) {
            background: linear-gradient(135deg, #EBF4FF 0%, #DBEAFE 100%);
            border: 2px solid #3B82F6;
            border-radius: 12px;
            padding: 20px;
            margin: 16px 0;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
        }
        </style>
        """, unsafe_allow_html=True)

        # Create a container for the action bar
        with st.container():
            # Marker div for CSS targeting
            st.markdown('<div class="action-bar-marker"></div>', unsafe_allow_html=True)

            # Header inside the bar
            st.markdown("""
            <div style="
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 12px;
            ">
                <span style="font-size: 1.2rem; color: #3B82F6;">&#8594;</span>
                <span style="font-weight: 600; color: #1E40AF; font-size: 1.1rem;">Ready to Continue?</span>
            </div>
            """, unsafe_allow_html=True)

            # Checkbox and button inside the styled container
            col1, col2 = st.columns([3, 1])

            confirmed = True
            with col1:
                if show_confirmation:
                    confirmed = st.checkbox(
                        "I have reviewed the results and want to proceed",
                        key=f"confirm_step_{current_step}"
                    )

            with col2:
                if current_step < 3:
                    if st.button(
                        next_label,
                        use_container_width=True,
                        disabled=not confirmed,
                        type="primary"
                    ):
                        if on_next:
                            on_next()
                        else:
                            st.session_state['current_step'] = current_step + 1
                            st.rerun()
                else:
                    if st.button(
                        "Complete Assessment",
                        use_container_width=True,
                        disabled=not confirmed,
                        type="primary"
                    ):
                        st.session_state['assessment_complete'] = True
                        st.rerun()
