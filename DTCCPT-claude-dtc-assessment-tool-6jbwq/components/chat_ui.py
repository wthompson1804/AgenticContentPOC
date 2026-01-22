"""
Chat UI Component - Renders the chat interface for conversational intake.

Per PRD Part 12: Two-column layout with chat (left) and artifact (right)
"""

import streamlit as st
from typing import Callable


def render_chat_message(message: dict):
    """Render a single chat message."""
    role = message.get("role", "assistant")
    content = message.get("content", "")

    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    elif role == "assistant":
        with st.chat_message("assistant"):
            st.markdown(content)
    elif role == "typing":
        # Typing indicator - animated dots
        with st.chat_message("assistant"):
            render_typing_indicator()
    elif role == "system":
        # System messages as info boxes
        st.info(content)


def render_typing_indicator():
    """Render an animated typing indicator."""
    st.markdown("""
    <style>
    @keyframes typing-dot {
        0%, 20% { opacity: 0.3; }
        50% { opacity: 1; }
        80%, 100% { opacity: 0.3; }
    }
    .typing-indicator {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 8px 0;
    }
    .typing-dot {
        width: 8px;
        height: 8px;
        background-color: #6B7280;
        border-radius: 50%;
        animation: typing-dot 1.4s infinite ease-in-out;
    }
    .typing-dot:nth-child(1) { animation-delay: 0s; }
    .typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .typing-dot:nth-child(3) { animation-delay: 0.4s; }
    </style>
    <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    </div>
    """, unsafe_allow_html=True)


def render_chat_history(chat_history: list):
    """Render the full chat history."""
    for message in chat_history:
        render_chat_message(message)


def render_chat_input(
    on_submit: Callable[[str], None],
    placeholder: str = "Type your message...",
    disabled: bool = False
):
    """Render the chat input field."""
    if prompt := st.chat_input(placeholder, disabled=disabled):
        on_submit(prompt)


def render_action_buttons(
    buttons: list[dict],
    on_click: Callable[[str], None]
):
    """
    Render action buttons for the current state.

    buttons: List of {"id": str, "label": str, "action": str}
    """
    if not buttons:
        return

    cols = st.columns(len(buttons))
    for i, button in enumerate(buttons):
        with cols[i]:
            if st.button(
                button["label"],
                key=f"action_{button['id']}",
                use_container_width=True,
                type="primary" if button["id"] == "proceed" else "secondary"
            ):
                on_click(button["action"])


def render_fast_path_button(on_click: Callable[[], None], show: bool = True):
    """Render the pinned fast-path button in sidebar."""
    if show:
        st.sidebar.divider()
        st.sidebar.markdown("### Quick Actions")
        if st.sidebar.button(
            "Just run it",
            key="fast_path_sidebar",
            help="Skip remaining questions and proceed with current assumptions",
            use_container_width=True
        ):
            on_click()


def render_timebox_indicator(timebox_status: dict):
    """Render timebox status indicator."""
    status = timebox_status.get("status", "normal")
    turns_used = timebox_status.get("turns_used", 0)
    turns_remaining = timebox_status.get("turns_remaining", 18)

    # Color coding
    colors = {
        "normal": "#10B981",  # green
        "approaching_limit": "#F59E0B",  # amber
        "at_limit": "#EF4444",  # red
        "exceeded": "#7F1D1D",  # dark red
    }
    color = colors.get(status, "#6B7280")

    st.sidebar.markdown(f"""
    <div style="
        padding: 8px 12px;
        background: {color}20;
        border-left: 3px solid {color};
        border-radius: 4px;
        margin: 8px 0;
    ">
        <div style="font-size: 0.75rem; color: #6B7280;">Session Progress</div>
        <div style="font-size: 1rem; font-weight: bold; color: {color};">
            {turns_used} / {turns_used + turns_remaining} turns
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_chat_interface(
    chat_history: list,
    buttons: list[dict] | None,
    timebox_status: dict,
    on_message: Callable[[str], None],
    on_action: Callable[[str], None],
    on_fast_path: Callable[[], None],
    input_disabled: bool = False
):
    """
    Render the complete chat interface.

    This is the main entry point for the chat UI.
    """
    # Render chat history in scrollable container
    chat_container = st.container()
    with chat_container:
        render_chat_history(chat_history)

    # Render action buttons if any
    if buttons:
        st.divider()
        render_action_buttons(buttons, on_action)

    # Render chat input
    st.divider()
    render_chat_input(on_message, disabled=input_disabled)

    # Sidebar elements
    render_timebox_indicator(timebox_status)
    render_fast_path_button(on_fast_path, show=not input_disabled)


def render_artifact_sidebar(
    artifact_html: str,
    progress: int,
    on_export: Callable[[], None] | None = None
):
    """
    Render the artifact panel in the right column.

    Per PRD: Artifact panel shows progressive 2-pager.
    """
    # Progress bar
    st.progress(progress / 100, text=f"Assessment {progress}% complete")

    # Artifact content
    st.components.v1.html(artifact_html, height=600, scrolling=True)

    # Export button (if available)
    if on_export and progress > 50:
        st.divider()
        if st.button("Export Draft", use_container_width=True):
            on_export()


def render_two_column_layout(
    chat_content: Callable[[], None],
    artifact_content: Callable[[], None],
    chat_width: float = 0.6
):
    """
    Render the two-column layout.

    Per PRD Part 19: chat_panel_width: 0.6, artifact_panel_width: 0.4
    """
    artifact_width = 1 - chat_width

    col1, col2 = st.columns([chat_width, artifact_width])

    with col1:
        st.markdown("### Chat")
        chat_content()

    with col2:
        st.markdown("### Assessment Summary")
        artifact_content()
