"""
Input form component for collecting use case information.
"""

import streamlit as st
from typing import Dict, Any, Optional, Tuple


# Common industries for suggestions
INDUSTRIES = [
    "Energy & Utilities",
    "Manufacturing",
    "Healthcare",
    "Transportation & Logistics",
    "Agriculture",
    "Construction",
    "Mining & Resources",
    "Oil & Gas",
    "Water Management",
    "Smart Cities",
    "Aerospace & Defense",
    "Financial Services",
    "Telecommunications",
    "Retail & Supply Chain",
    "Other"
]

# Common jurisdictions
JURISDICTIONS = [
    "United States",
    "European Union",
    "United Kingdom",
    "Canada",
    "Australia",
    "Germany",
    "Japan",
    "Singapore",
    "China",
    "India",
    "Brazil",
    "Multi-jurisdictional",
    "Other"
]

# Implementation timelines with descriptions
TIMELINES = [
    ("Proof of Concept", "Testing feasibility, 1-3 months"),
    ("Pilot Project", "Limited deployment, 3-6 months"),
    ("Production Deployment", "Full rollout, 6-12 months"),
    ("Scaling Existing", "Expanding current system"),
]


def render_input_form() -> Tuple[bool, Dict[str, Any]]:
    """Render the input form for collecting use case information.

    Returns:
        Tuple of (form_submitted, form_data)
    """
    st.markdown("### Define Your Use Case")
    st.markdown(
        "Provide information about your AI agent implementation to enable "
        "targeted research and accurate capability assessment."
    )

    with st.form("use_case_form"):
        # Industry selection
        col1, col2 = st.columns(2)

        with col1:
            industry_select = st.selectbox(
                "Industry Sector *",
                options=INDUSTRIES,
                help="Select the primary industry for your AI agent deployment"
            )

        with col2:
            if industry_select == "Other":
                industry = st.text_input(
                    "Specify Industry *",
                    placeholder="Enter your industry"
                )
            else:
                industry = industry_select

        # Use case description
        use_case = st.text_area(
            "Use Case Description *",
            placeholder=(
                "Describe what you want your AI agent to do. Include:\n"
                "- Primary function or task\n"
                "- Key interactions (with humans, systems, physical equipment)\n"
                "- Expected outcomes or decisions\n"
                "- Any specific constraints or requirements"
            ),
            height=150,
            help="Be specific about the AI agent's role and responsibilities"
        )

        # Jurisdiction and Timeline (both visible, not hidden)
        col3, col4 = st.columns(2)

        with col3:
            jurisdiction_select = st.selectbox(
                "Primary Jurisdiction *",
                options=JURISDICTIONS,
                help="Select the primary regulatory jurisdiction for compliance requirements"
            )

            if jurisdiction_select == "Other":
                jurisdiction = st.text_input(
                    "Specify Jurisdiction *",
                    placeholder="Enter jurisdiction"
                )
            else:
                jurisdiction = jurisdiction_select

        with col4:
            timeline_options = [t[0] for t in TIMELINES]
            timeline = st.selectbox(
                "Implementation Timeline *",
                options=timeline_options,
                index=1,
                help="Select your expected implementation timeline"
            )
            # Show description for selected timeline
            timeline_desc = next((t[1] for t in TIMELINES if t[0] == timeline), "")
            st.caption(f"_{timeline_desc}_")

        # Organization size
        organization_size = st.selectbox(
            "Organization Size",
            options=["Startup (<50)", "SMB (50-500)", "Enterprise (500-5000)", "Large Enterprise (5000+)"],
            index=2,
            help="Select your organization size to help tailor recommendations"
        )

        # Additional context (optional)
        with st.expander("Additional Context (Optional)", expanded=False):
            existing_systems = st.text_area(
                "Existing Systems",
                placeholder="List any existing systems the AI agent needs to integrate with (e.g., SCADA, ERP, CRM)",
                height=80
            )

            safety_requirements = st.text_area(
                "Safety Requirements",
                placeholder="Describe any specific safety, compliance, or regulatory requirements",
                height=80
            )

        # Submit button
        submitted = st.form_submit_button("Start Assessment", type="primary", use_container_width=True)

        if submitted:
            # Validate required fields
            if not industry or industry == "Other":
                st.error("Please specify an industry.")
                return False, {}

            if not use_case or len(use_case.strip()) < 20:
                st.error("Please provide a more detailed use case description (at least 20 characters).")
                return False, {}

            if not jurisdiction or jurisdiction == "Other":
                st.error("Please specify a jurisdiction.")
                return False, {}

            # Return form data
            form_data = {
                "industry": industry,
                "use_case": use_case.strip(),
                "jurisdiction": jurisdiction,
                "organization_size": organization_size,
                "timeline": timeline,
                "existing_systems": existing_systems.strip() if existing_systems else None,
                "safety_requirements": safety_requirements.strip() if safety_requirements else None,
            }

            return True, form_data

    return False, {}


def render_input_summary(form_data: Dict[str, Any]) -> None:
    """Render a comprehensive summary of the assessment context.

    This serves as a final checkpoint before starting research.

    Args:
        form_data: Dictionary containing the form data
    """
    st.markdown("### Review Your Assessment Context")
    st.caption("Please review the details below before starting research. This is what I'll use to conduct the analysis.")

    # Use case - prominently displayed
    st.markdown("#### What You're Trying to Do")
    use_case = form_data.get("use_case", "N/A")
    if use_case and use_case != "N/A":
        st.info(use_case)
    else:
        st.warning("No use case description provided")

    # Context metrics in columns
    st.markdown("#### Context")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        industry = form_data.get("industry", "N/A")
        if isinstance(industry, dict):
            industry = industry.get("value", "N/A")
        st.metric("Industry", industry.title() if industry != "N/A" else "N/A")

    with col2:
        jurisdiction = form_data.get("jurisdiction", "N/A")
        if isinstance(jurisdiction, dict):
            jurisdiction = jurisdiction.get("value", "N/A")
        st.metric("Location", jurisdiction)

    with col3:
        timeline_data = form_data.get("timeline", "N/A")
        if isinstance(timeline_data, dict):
            # Prefer raw expression (what user said) over bucket category
            timeline = timeline_data.get("raw") or timeline_data.get("bucket", "N/A")
        else:
            timeline = timeline_data
        st.metric("Timeline", timeline.title() if timeline and timeline != "N/A" else "N/A")

    with col4:
        org_size = form_data.get("organization_size", "N/A")
        if isinstance(org_size, dict):
            org_size = org_size.get("bucket", "N/A")
        if isinstance(org_size, str) and " " in org_size:
            org_size = org_size.split(" ")[0]
        st.metric("Org Size", org_size.title() if org_size and org_size != "N/A" else "N/A")

    # Additional context from chat intake (if available)
    has_additional = False

    # Golden thread / narrative context
    if form_data.get("_golden_thread"):
        has_additional = True
        st.markdown("#### Your Words")
        st.markdown(f"*\"{form_data['_golden_thread']}\"*")

    # Constraints
    if form_data.get("_constraints"):
        has_additional = True
        st.markdown("#### Key Constraints")
        for constraint in form_data["_constraints"][:5]:
            st.markdown(f"- {constraint}")

    # Integration systems
    if form_data.get("existing_systems"):
        has_additional = True
        st.markdown("#### Systems to Integrate With")
        st.markdown(form_data["existing_systems"])

    # Safety/compliance
    if form_data.get("safety_requirements"):
        has_additional = True
        st.markdown("#### Safety & Compliance Notes")
        st.markdown(form_data["safety_requirements"])

    # Open questions from the conversation
    if form_data.get("_open_questions"):
        has_additional = True
        st.markdown("#### Questions to Address")
        for q in form_data["_open_questions"][:3]:
            st.markdown(f"- {q}")

    if not has_additional:
        st.caption("Additional context will be gathered during research.")
