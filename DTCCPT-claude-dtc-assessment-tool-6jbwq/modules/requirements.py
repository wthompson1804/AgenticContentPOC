"""
Requirements module for DTC Step 1: Business Requirements Generation.

This module generates comprehensive business requirements based on
the research findings and use case context using the DTC methodology.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from .data_loader import load_prompt


@dataclass
class RequirementsResult:
    """Business requirements generation result."""
    status: str = "pending"  # pending, in_progress, complete, error
    requirements_text: str = ""
    structured_requirements: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


def build_requirements_prompt(
    form_data: Dict[str, Any],
    research_results: Dict[str, Any],
    boundaries: Optional[str] = None,
    assumptions: Optional[list] = None
) -> str:
    """Build the complete requirements generation prompt.

    Args:
        form_data: User input form data
        research_results: Research findings from Step 0
        boundaries: Optional explicit boundaries/non-goals from chat intake (Phase 5)
        assumptions: Optional list of assumptions from chat intake (Phase 5)

    Returns:
        Complete prompt for requirements generation
    """
    # Load the DTC Step 1 prompt template
    dtc_prompt = load_prompt(1)

    # Phase 5: Format boundaries section if provided
    boundaries_section = ""
    if boundaries:
        boundaries_section = f"""
### Explicit Boundaries (Non-Goals)
**IMPORTANT:** The following boundaries have been explicitly defined. Do NOT include requirements that violate these boundaries.
{boundaries}
"""

    # Phase 5: Format assumptions section if provided
    assumptions_section = ""
    if assumptions:
        high_impact = [a for a in assumptions if a.get('impact') == 'high'][:3]
        if high_impact:
            assumptions_section = """
### Key Assumptions
The following assumptions are being made. Requirements should be conditional on these being true:
"""
            for a in high_impact:
                conf = a.get('confidence', 'med')
                assumptions_section += f"- {a.get('statement', '')} (confidence: {conf})\n"

    # Build context from form data and research
    context = f"""
## Use Case Context

**Industry:** {form_data.get('industry', 'Not specified')}
**Jurisdiction:** {form_data.get('jurisdiction', 'Not specified')}
**Organization Size:** {form_data.get('organization_size', 'Not specified')}
**Timeline:** {form_data.get('timeline', 'Not specified')}

### Use Case Description
{form_data.get('use_case', 'Not provided')}

### Existing Systems
{form_data.get('existing_systems', 'None specified')}

### Safety Requirements
{form_data.get('safety_requirements', 'None specified')}
{boundaries_section}
{assumptions_section}

## Research Findings Summary

### Preliminary Assessment
- **Recommended Agent Type:** {research_results.get('preliminary_assessment', {}).get('recommended_type', 'TBD')}
- **Go/No-Go:** {research_results.get('preliminary_assessment', {}).get('go_no_go', 'pending')}
- **Confidence:** {research_results.get('preliminary_assessment', {}).get('confidence_level', 'medium')}

### Industry Context
{research_results.get('research_areas', {}).get('industry_adoption', {}).get('findings', 'No findings')}

### Regulatory Context
{research_results.get('research_areas', {}).get('regulatory_environment', {}).get('findings', 'No findings')}

### Technical Context
{research_results.get('research_areas', {}).get('technical_integration', {}).get('findings', 'No findings')}

### Risk Factors
{research_results.get('research_areas', {}).get('risk_failure_modes', {}).get('findings', 'No findings')}

---

Now, following the DTC methodology below, generate comprehensive business requirements:

{dtc_prompt}
"""

    return context


def generate_requirements(
    form_data: Dict[str, Any],
    research_results: Dict[str, Any],
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None,
    boundaries: Optional[str] = None,
    assumptions: Optional[list] = None
) -> RequirementsResult:
    """Generate business requirements using DTC Step 1 methodology.

    Args:
        form_data: User input form data
        research_results: Research findings from Step 0
        model: Claude model to use
        api_key: Optional API key
        boundaries: Optional explicit boundaries from Phase 5 chat intake
        assumptions: Optional assumptions list from Phase 5 chat intake

    Returns:
        RequirementsResult with generated requirements
    """
    result = RequirementsResult(status="in_progress")

    try:
        # Build the prompt (with optional Phase 5 context)
        prompt = build_requirements_prompt(
            form_data, research_results,
            boundaries=boundaries,
            assumptions=assumptions
        )

        # Get Anthropic client
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not provided")

        client = ChatAnthropic(
            model=model,
            api_key=key,
            max_tokens=8192,
        )

        # System message
        system = SystemMessage(content="""You are a senior systems architect specializing in AI agent design for industrial and enterprise applications.

Your task is to generate comprehensive business requirements following the Digital Twin Consortium methodology.

Guidelines:
1. Be specific and actionable - each requirement should be testable
2. Consider all stakeholder perspectives
3. Address both functional and non-functional requirements
4. Include safety and compliance requirements
5. Quantify requirements where possible (response times, accuracy thresholds, etc.)

Format your output as structured markdown with clear sections matching the DTC template.""")

        # Execute
        response = client.invoke([
            system,
            HumanMessage(content=prompt)
        ])

        result.requirements_text = response.content
        result.status = "complete"

        # Parse structured requirements
        result.structured_requirements = parse_requirements(response.content)

    except Exception as e:
        result.status = "error"
        result.error_message = str(e)

    return result


def parse_requirements(requirements_text: str) -> Dict[str, Any]:
    """Parse requirements text into structured format.

    Args:
        requirements_text: Raw requirements markdown

    Returns:
        Structured requirements dictionary
    """
    sections = {
        "business_context": "",
        "problem_analysis": "",
        "objectives": "",
        "operational_requirements": "",
        "data_requirements": "",
        "user_experience": "",
        "technical_considerations": "",
        "implementation_approach": "",
    }

    # Simple section extraction
    current_section = None
    current_content = []

    for line in requirements_text.split('\n'):
        line_lower = line.lower()

        if 'business context' in line_lower:
            current_section = 'business_context'
            current_content = []
        elif 'problem analysis' in line_lower:
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'problem_analysis'
            current_content = []
        elif 'objective' in line_lower:
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'objectives'
            current_content = []
        elif 'operational requirement' in line_lower:
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'operational_requirements'
            current_content = []
        elif 'data requirement' in line_lower:
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'data_requirements'
            current_content = []
        elif 'user experience' in line_lower:
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'user_experience'
            current_content = []
        elif 'technical consideration' in line_lower:
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'technical_considerations'
            current_content = []
        elif 'implementation' in line_lower:
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'implementation_approach'
            current_content = []
        elif current_section:
            current_content.append(line)

    # Capture final section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content)

    return sections


def format_requirements_for_display(result: RequirementsResult) -> Dict[str, Any]:
    """Format requirements for Streamlit display.

    Args:
        result: RequirementsResult object

    Returns:
        Dictionary formatted for UI display
    """
    return {
        "status": result.status,
        "full_text": result.requirements_text,
        "sections": result.structured_requirements,
        "error": result.error_message,
    }
