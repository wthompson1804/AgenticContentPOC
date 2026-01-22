"""
Agent Design module for DTC Step 2: Agent Type Assessment and Design.

This module assesses the appropriate agent type (T0-T4) and generates
the agent architecture design using the DTC methodology.
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from .data_loader import load_prompt, load_config


@dataclass
class AgentDesignResult:
    """Agent design assessment result."""
    status: str = "pending"  # pending, in_progress, complete, error
    recommended_type: str = "T2"  # T0-T4
    confirmed_type: Optional[str] = None
    type_justification: str = ""
    design_document: str = ""
    architecture_summary: str = ""
    team_structure: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None


# Agent type criteria from DTC framework
AGENT_TYPE_CRITERIA = {
    "T0": {
        "name": "Static Automation",
        "description": "Pre-programmed, rule-based systems with no learning capability",
        "indicators": [
            "Simple, deterministic tasks",
            "No need for adaptation",
            "Rule-based logic sufficient",
            "No human interaction required",
            "Static environment"
        ],
        "not_suitable": [
            "Complex decision-making",
            "Learning requirements",
            "Natural language interaction",
            "Dynamic environments"
        ]
    },
    "T1": {
        "name": "Conversational Agents",
        "description": "NLP interaction with basic context awareness",
        "indicators": [
            "Natural language interface needed",
            "Information retrieval tasks",
            "FAQ/helpdesk scenarios",
            "Basic context tracking",
            "Single-turn or simple multi-turn"
        ],
        "not_suitable": [
            "Complex workflows",
            "Tool integration",
            "Autonomous operation",
            "Physical system interaction"
        ]
    },
    "T2": {
        "name": "Procedural Workflow Agents",
        "description": "Multi-step execution with tool integration",
        "indicators": [
            "Multi-step processes",
            "Tool/API integration needed",
            "Structured workflows",
            "Human-in-the-loop checkpoints",
            "Moderate complexity"
        ],
        "not_suitable": [
            "Self-directed planning",
            "Complex reasoning",
            "Autonomous learning",
            "Emergent behavior"
        ]
    },
    "T3": {
        "name": "Cognitive Autonomous Agents",
        "description": "Self-directed planning with learning capability",
        "indicators": [
            "Complex decision-making",
            "Self-directed planning",
            "Learning and adaptation",
            "Dynamic environments",
            "Limited supervision"
        ],
        "not_suitable": [
            "Simple, repetitive tasks",
            "Fully deterministic needs",
            "No learning requirement"
        ]
    },
    "T4": {
        "name": "Multi-Agent Generative Systems (MAGS)",
        "description": "Collaborative intelligence with distributed coordination",
        "indicators": [
            "Multiple specialized agents needed",
            "Distributed coordination",
            "Emergent behavior acceptable",
            "Enterprise-scale complexity",
            "Collaborative problem-solving"
        ],
        "not_suitable": [
            "Simple, single-purpose tasks",
            "Tight control requirements",
            "Limited infrastructure"
        ]
    }
}


def build_agent_design_prompt(
    form_data: Dict[str, Any],
    research_results: Dict[str, Any],
    requirements_output: Dict[str, Any],
    boundaries: Optional[str] = None,
    assumptions: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Build the complete agent design prompt.

    Args:
        form_data: User input form data
        research_results: Research findings from Step 0
        requirements_output: Requirements from Step 1
        boundaries: Optional explicit boundaries from Phase 5 chat intake
        assumptions: Optional assumptions list from Phase 5 chat intake

    Returns:
        Complete prompt for agent design
    """
    # Load the DTC Step 2 prompt template
    dtc_prompt = load_prompt(2)

    # Phase 5: Format boundaries section if provided
    boundaries_section = ""
    if boundaries:
        boundaries_section = f"""
### Explicit Boundaries (Non-Goals)
**IMPORTANT:** The agent design must respect these boundaries. Do NOT design capabilities that violate them.
{boundaries}
"""

    # Phase 5: Format assumptions section if provided
    assumptions_section = ""
    if assumptions:
        high_impact = [a for a in assumptions if a.get('impact') == 'high'][:3]
        if high_impact:
            assumptions_section = """
### Key Assumptions
The design should account for these assumptions:
"""
            for a in high_impact:
                conf = a.get('confidence', 'med')
                assumptions_section += f"- {a.get('statement', '')} (confidence: {conf})\n"

    # Build context from all prior steps
    context = f"""
## Use Case Summary

**Industry:** {form_data.get('industry', 'Not specified')}
**Jurisdiction:** {form_data.get('jurisdiction', 'Not specified')}

### Use Case
{form_data.get('use_case', 'Not provided')}
{boundaries_section}
{assumptions_section}

## Research Summary

**Preliminary Recommendation:** {research_results.get('preliminary_assessment', {}).get('recommended_type', 'TBD')}
**Go/No-Go:** {research_results.get('preliminary_assessment', {}).get('go_no_go', 'pending')}

### Key Findings
- Industry: {research_results.get('research_areas', {}).get('industry_adoption', {}).get('findings', '')[:500]}
- Regulatory: {research_results.get('research_areas', {}).get('regulatory_environment', {}).get('findings', '')[:500]}
- Technical: {research_results.get('research_areas', {}).get('technical_integration', {}).get('findings', '')[:500]}

## Business Requirements Summary

{requirements_output.get('full_text', 'Requirements not yet generated')[:3000]}

---

## Agent Type Reference

{format_agent_types_reference()}

---

Now, following the DTC methodology below, assess the appropriate agent type and generate the design:

{dtc_prompt}
"""

    return context


def format_agent_types_reference() -> str:
    """Format agent types as reference text."""
    lines = []
    for type_id, type_info in AGENT_TYPE_CRITERIA.items():
        lines.append(f"### {type_id}: {type_info['name']}")
        lines.append(f"{type_info['description']}")
        lines.append("\n**Suitable when:**")
        for indicator in type_info['indicators']:
            lines.append(f"- {indicator}")
        lines.append("\n**Not suitable for:**")
        for contra in type_info['not_suitable']:
            lines.append(f"- {contra}")
        lines.append("")
    return "\n".join(lines)


def generate_agent_design(
    form_data: Dict[str, Any],
    research_results: Dict[str, Any],
    requirements_output: Dict[str, Any],
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None,
    boundaries: Optional[str] = None,
    assumptions: Optional[List[Dict[str, Any]]] = None
) -> AgentDesignResult:
    """Generate agent design using DTC Step 2 methodology.

    Args:
        form_data: User input form data
        research_results: Research findings from Step 0
        requirements_output: Requirements from Step 1
        model: Claude model to use
        api_key: Optional API key
        boundaries: Optional explicit boundaries from Phase 5 chat intake
        assumptions: Optional assumptions list from Phase 5 chat intake

    Returns:
        AgentDesignResult with design recommendations
    """
    result = AgentDesignResult(status="in_progress")

    try:
        # Build the prompt with Phase 5 context injection
        prompt = build_agent_design_prompt(
            form_data, research_results, requirements_output,
            boundaries=boundaries, assumptions=assumptions
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
        system = SystemMessage(content="""You are a senior AI systems architect specializing in agent design for industrial and enterprise applications.

Your task is to assess the appropriate agent type (T0-T4) and generate an architecture design following the Digital Twin Consortium methodology.

Guidelines:
1. Carefully evaluate the use case against all agent type criteria
2. Provide clear justification for your type recommendation
3. Consider safety and compliance implications
4. Design for appropriate human oversight
5. Be specific about architecture components

IMPORTANT: Your type assessment will be confirmed by the user before proceeding. Provide a clear recommendation with supporting rationale.

Format your output as structured markdown with:
1. Agent Type Assessment (with explicit T0-T4 recommendation)
2. Justification
3. Architecture Design
4. Team/Agent Structure (if T4)
5. Key Considerations""")

        # Execute
        response = client.invoke([
            system,
            HumanMessage(content=prompt)
        ])

        result.design_document = response.content
        result.status = "complete"

        # Extract recommended type
        result.recommended_type = extract_recommended_type(response.content)
        result.type_justification = extract_justification(response.content)
        result.architecture_summary = extract_architecture(response.content)

        if result.recommended_type == "T4":
            result.team_structure = extract_team_structure(response.content)

    except Exception as e:
        result.status = "error"
        result.error_message = str(e)

    return result


def extract_recommended_type(content: str) -> str:
    """Extract the recommended agent type from the design document."""
    import re

    # Look for explicit recommendation patterns
    patterns = [
        r"recommend(?:ed|ation)?[:\s]+\*?\*?(T[0-4])\*?\*?",
        r"agent type[:\s]+\*?\*?(T[0-4])\*?\*?",
        r"(T[0-4])[:\s]+(?:is )?recommended",
        r"\*\*(T[0-4])\*\*",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    # Fallback to any T0-T4 mention
    match = re.search(r'\b(T[0-4])\b', content)
    if match:
        return match.group(1).upper()

    return "T2"  # Default


def extract_justification(content: str) -> str:
    """Extract the type justification from the design document."""
    import re

    # Look for justification section
    pattern = r"(?:justification|rationale|reasoning)[:\s]*\n?(.*?)(?=\n##|\n#|\Z)"
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)

    if match:
        return match.group(1).strip()[:1000]

    return ""


def extract_architecture(content: str) -> str:
    """Extract the architecture summary from the design document."""
    import re

    # Look for architecture section
    pattern = r"(?:architecture|design)[:\s]*\n?(.*?)(?=\n##|\n#|\Z)"
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)

    if match:
        return match.group(1).strip()[:2000]

    return ""


def extract_team_structure(content: str) -> List[Dict[str, Any]]:
    """Extract team structure for T4 MAGS designs."""
    # Simplified extraction - in production would use more sophisticated parsing
    agents = []

    import re
    # Look for agent definitions
    pattern = r"(?:agent|role)[:\s]+([^\n]+)"
    matches = re.findall(pattern, content, re.IGNORECASE)

    for i, match in enumerate(matches[:10]):  # Limit to 10 agents
        agents.append({
            "id": f"agent_{i+1}",
            "name": match.strip(),
            "role": "Specialized Agent"
        })

    return agents


def format_agent_design_for_display(result: AgentDesignResult) -> Dict[str, Any]:
    """Format agent design for Streamlit display.

    Args:
        result: AgentDesignResult object

    Returns:
        Dictionary formatted for UI display
    """
    return {
        "status": result.status,
        "recommended_type": result.recommended_type,
        "confirmed_type": result.confirmed_type,
        "type_info": AGENT_TYPE_CRITERIA.get(result.recommended_type, {}),
        "justification": result.type_justification,
        "architecture_summary": result.architecture_summary,
        "full_document": result.design_document,
        "team_structure": result.team_structure,
        "error": result.error_message,
    }
