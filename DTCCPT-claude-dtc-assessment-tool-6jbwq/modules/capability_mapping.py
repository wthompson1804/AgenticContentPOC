"""
Capability Mapping module for DTC Step 3: CPT Capability Mapping.

This module maps requirements to the 45-capability CPT framework
and generates the HTML visualization.
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from .data_loader import load_prompt, load_capabilities, get_all_capabilities_flat


@dataclass
class CapabilityMapping:
    """Individual capability mapping."""
    capability_id: str
    capability_name: str
    category_id: str
    category_name: str
    priority: str = "medium"  # essential, high, medium, low, optional
    justification: str = ""
    maturity_required: str = ""
    implementation_notes: str = ""


@dataclass
class CapabilityMappingResult:
    """Complete capability mapping result."""
    status: str = "pending"  # pending, in_progress, complete, error
    agent_type: str = "T2"
    mappings: List[CapabilityMapping] = field(default_factory=list)
    essential_capabilities: List[str] = field(default_factory=list)
    advanced_capabilities: List[str] = field(default_factory=list)
    optional_capabilities: List[str] = field(default_factory=list)
    mapping_document: str = ""
    html_visualization: str = ""
    error_message: Optional[str] = None


def build_capability_mapping_prompt(
    form_data: Dict[str, Any],
    research_results: Dict[str, Any],
    requirements_output: Dict[str, Any],
    agent_design_output: Dict[str, Any],
    capabilities: Dict[str, Any],
    boundaries: Optional[str] = None,
    assumptions: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Build the complete capability mapping prompt.

    Args:
        form_data: User input form data
        research_results: Research findings from Step 0
        requirements_output: Requirements from Step 1
        agent_design_output: Agent design from Step 2
        capabilities: CPT capability definitions
        boundaries: Optional explicit boundaries from Phase 5 chat intake
        assumptions: Optional assumptions list from Phase 5 chat intake

    Returns:
        Complete prompt for capability mapping
    """
    # Load the DTC Step 3 prompt template
    dtc_prompt = load_prompt(3)

    # Format capabilities reference
    cap_reference = format_capabilities_reference(capabilities)

    # Phase 5: Format boundaries section if provided
    boundaries_section = ""
    if boundaries:
        boundaries_section = f"""
### Explicit Boundaries (Non-Goals)
**IMPORTANT:** The capability mapping must respect these boundaries. Do NOT map capabilities that violate them.
{boundaries}
"""

    # Phase 5: Format assumptions section if provided
    assumptions_section = ""
    if assumptions:
        high_impact = [a for a in assumptions if a.get('impact') == 'high'][:3]
        if high_impact:
            assumptions_section = """
### Key Assumptions
The capability mapping should account for these assumptions:
"""
            for a in high_impact:
                conf = a.get('confidence', 'med')
                assumptions_section += f"- {a.get('statement', '')} (confidence: {conf})\n"

    # Build context from all prior steps
    context = f"""
## Assessment Summary

**Industry:** {form_data.get('industry', 'Not specified')}
**Use Case:** {form_data.get('use_case', 'Not provided')[:500]}
{boundaries_section}
{assumptions_section}

## Agent Design Summary

**Confirmed Agent Type:** {agent_design_output.get('confirmed_type', agent_design_output.get('recommended_type', 'T2'))}

### Architecture Summary
{agent_design_output.get('architecture_summary', 'See full design document')[:1000]}

## Business Requirements Summary

{requirements_output.get('full_text', 'Requirements not available')[:2000]}

---

## Available Capabilities (CPT Framework)

{cap_reference}

---

Now, following the DTC methodology below, map requirements to capabilities:

{dtc_prompt}
"""

    return context


def format_capabilities_reference(capabilities: Dict[str, Any]) -> str:
    """Format capabilities as reference text for the prompt."""
    lines = []

    for cat_id, cat_data in capabilities.get('capabilities', {}).items():
        cat_name = cat_data.get('name', cat_id)
        lines.append(f"\n### {cat_id}: {cat_name}")
        lines.append(cat_data.get('description', '')[:200])

        for cap_id, cap_data in cat_data.get('capabilities', {}).items():
            cap_name = cap_data.get('name', cap_id)
            cap_desc = cap_data.get('description', '')[:150]
            archetypes = cap_data.get('archetypes', 'All Types')
            lines.append(f"\n**{cap_id}: {cap_name}**")
            lines.append(f"  {cap_desc}")
            lines.append(f"  *Archetypes: {archetypes}*")

    return "\n".join(lines)


def generate_capability_mapping(
    form_data: Dict[str, Any],
    research_results: Dict[str, Any],
    requirements_output: Dict[str, Any],
    agent_design_output: Dict[str, Any],
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None,
    boundaries: Optional[str] = None,
    assumptions: Optional[List[Dict[str, Any]]] = None
) -> CapabilityMappingResult:
    """Generate capability mapping using DTC Step 3 methodology.

    Args:
        form_data: User input form data
        research_results: Research findings from Step 0
        requirements_output: Requirements from Step 1
        agent_design_output: Agent design from Step 2
        model: Claude model to use
        api_key: Optional API key
        boundaries: Optional explicit boundaries from Phase 5 chat intake
        assumptions: Optional assumptions list from Phase 5 chat intake

    Returns:
        CapabilityMappingResult with capability mappings
    """
    result = CapabilityMappingResult(status="in_progress")
    result.agent_type = agent_design_output.get(
        'confirmed_type',
        agent_design_output.get('recommended_type', 'T2')
    )

    try:
        # Load capabilities
        capabilities = load_capabilities()

        # Build the prompt with Phase 5 context injection
        prompt = build_capability_mapping_prompt(
            form_data,
            research_results,
            requirements_output,
            agent_design_output,
            capabilities,
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
        system = SystemMessage(content="""You are a senior AI systems architect specializing in capability assessment using the Digital Twin Consortium's Capabilities Periodic Table (CPT) framework.

Your task is to map the business requirements to specific CPT capabilities, providing:
1. Essential capabilities (must have)
2. Advanced capabilities (should have)
3. Optional capabilities (nice to have)

For each capability:
- Provide clear justification linked to specific requirements
- Note the minimum maturity level required
- Include implementation considerations

Format your output as structured markdown with:
1. Executive Summary
2. Essential Capabilities (with justifications)
3. Advanced Capabilities (with justifications)
4. Optional Capabilities (with justifications)
5. Implementation Priority Matrix
6. Key Recommendations

Use the exact capability IDs from the CPT framework (e.g., PK.OB, CG.PL, etc.).""")

        # Execute
        response = client.invoke([
            system,
            HumanMessage(content=prompt)
        ])

        result.mapping_document = response.content
        result.status = "complete"

        # Parse mappings
        all_caps = get_all_capabilities_flat(capabilities)
        result.mappings = parse_capability_mappings(response.content, all_caps)

        # Categorize by priority
        for mapping in result.mappings:
            if mapping.priority == "essential":
                result.essential_capabilities.append(mapping.capability_id)
            elif mapping.priority in ["high", "advanced"]:
                result.advanced_capabilities.append(mapping.capability_id)
            else:
                result.optional_capabilities.append(mapping.capability_id)

        # Generate HTML visualization
        result.html_visualization = generate_html_visualization(
            result.mappings,
            capabilities,
            form_data,
            result.agent_type
        )

    except Exception as e:
        result.status = "error"
        result.error_message = str(e)

    return result


def parse_capability_mappings(
    content: str,
    all_capabilities: Dict[str, Dict[str, Any]]
) -> List[CapabilityMapping]:
    """Parse capability mappings from the LLM response.

    Args:
        content: LLM response content
        all_capabilities: Flat dict of all capabilities

    Returns:
        List of CapabilityMapping objects
    """
    import re

    mappings = []
    seen_caps = set()

    # First, identify sections for priority classification
    essential_section = extract_priority_section(content, "essential")
    advanced_section = extract_priority_section(content, "advanced")
    optional_section = extract_priority_section(content, "optional")

    # Find all capability IDs mentioned
    cap_pattern = r'\b([A-Z]{2}\.[A-Z]{2})\b'
    matches = re.findall(cap_pattern, content)

    for cap_id in matches:
        if cap_id in seen_caps:
            continue
        seen_caps.add(cap_id)

        cap_data = all_capabilities.get(cap_id)
        if not cap_data:
            continue

        # Determine priority based on which section the capability appears in
        priority = determine_priority(content, cap_id, essential_section, advanced_section, optional_section)

        # Extract justification if available
        justification = extract_capability_justification(content, cap_id)

        mapping = CapabilityMapping(
            capability_id=cap_id,
            capability_name=cap_data.get('name', ''),
            category_id=cap_data.get('category_id', ''),
            category_name=cap_data.get('category_name', ''),
            priority=priority,
            justification=justification,
        )
        mappings.append(mapping)

    return mappings


def extract_priority_section(content: str, priority_type: str) -> str:
    """Extract the section content for a given priority level.

    Args:
        content: Full LLM response
        priority_type: "essential", "advanced", or "optional"

    Returns:
        Section content or empty string
    """
    import re

    # Define patterns for each priority type
    patterns = {
        "essential": [
            r"#{1,4}\s*(?:\d+\.?\s*)?Essential\s+Capabilities[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
            r"\*\*Essential\s+Capabilities[:\*]*\*\*[^\n]*\n(.*?)(?=\n\*\*|\n#{1,4}\s|\Z)",
            r"#{1,4}\s*Must[- ]Have[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
            r"#{1,4}\s*Critical\s+Capabilities[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
        ],
        "advanced": [
            r"#{1,4}\s*(?:\d+\.?\s*)?Advanced\s+Capabilities[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
            r"\*\*Advanced\s+Capabilities[:\*]*\*\*[^\n]*\n(.*?)(?=\n\*\*|\n#{1,4}\s|\Z)",
            r"#{1,4}\s*Should[- ]Have[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
            r"#{1,4}\s*High\s+Priority[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
        ],
        "optional": [
            r"#{1,4}\s*(?:\d+\.?\s*)?Optional\s+Capabilities[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
            r"\*\*Optional\s+Capabilities[:\*]*\*\*[^\n]*\n(.*?)(?=\n\*\*|\n#{1,4}\s|\Z)",
            r"#{1,4}\s*Nice[- ]to[- ]Have[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
            r"#{1,4}\s*Future\s+Capabilities[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
        ],
    }

    for pattern in patterns.get(priority_type, []):
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)

    return ""


def determine_priority(content: str, cap_id: str,
                      essential_section: str = "",
                      advanced_section: str = "",
                      optional_section: str = "") -> str:
    """Determine the priority of a capability based on context.

    Args:
        content: Full LLM response
        cap_id: Capability ID (e.g., "PK.OB")
        essential_section: Pre-extracted essential section
        advanced_section: Pre-extracted advanced section
        optional_section: Pre-extracted optional section

    Returns:
        Priority level: "essential", "high", "medium", or "optional"
    """
    import re

    # Check if capability appears in a specific priority section
    if essential_section and re.search(rf'\b{re.escape(cap_id)}\b', essential_section):
        return "essential"
    if advanced_section and re.search(rf'\b{re.escape(cap_id)}\b', advanced_section):
        return "high"
    if optional_section and re.search(rf'\b{re.escape(cap_id)}\b', optional_section):
        return "optional"

    # Fallback: check context around the capability mention
    pattern = rf'.{{0,300}}{re.escape(cap_id)}.{{0,300}}'
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)

    if match:
        context = match.group(0).lower()

        # Check for priority indicators in context
        if any(word in context for word in ['essential', 'critical', 'must have', 'must-have', 'required', 'mandatory']):
            return "essential"
        elif any(word in context for word in ['advanced', 'should have', 'should-have', 'important', 'high priority', 'recommended']):
            return "high"
        elif any(word in context for word in ['optional', 'nice to have', 'nice-to-have', 'low priority', 'future', 'could have']):
            return "optional"

    return "medium"


def extract_capability_justification(content: str, cap_id: str) -> str:
    """Extract justification for a specific capability."""
    import re

    # Look for justification near the capability mention
    pattern = rf'{re.escape(cap_id)}[:\s-]+([^\n]+(?:\n(?![A-Z]{{2}}\.[A-Z]{{2}})[^\n]+)*)'
    match = re.search(pattern, content)

    if match:
        return match.group(1).strip()[:500]

    return ""


def generate_html_visualization(
    mappings: List[CapabilityMapping],
    capabilities: Dict[str, Any],
    form_data: Dict[str, Any],
    agent_type: str
) -> str:
    """Generate the HTML periodic table visualization.

    Args:
        mappings: List of capability mappings
        capabilities: Full capabilities data
        form_data: User input form data
        agent_type: Confirmed agent type

    Returns:
        Self-contained HTML string
    """
    # Category colors
    category_colors = {
        "PK": "#3B82F6",  # blue
        "CG": "#F97316",  # orange
        "LA": "#A855F7",  # purple
        "AE": "#6B7280",  # gray
        "IC": "#14B8A6",  # teal
        "GS": "#EF4444",  # red
    }

    # Build mapping lookup
    mapping_lookup = {m.capability_id: m for m in mappings}

    # Build capability cards HTML
    capability_cards = []

    for cat_id, cat_data in capabilities.get('capabilities', {}).items():
        for cap_id, cap_data in cat_data.get('capabilities', {}).items():
            mapping = mapping_lookup.get(cap_id)
            is_mapped = mapping is not None
            priority = mapping.priority if mapping else "not-mapped"
            color = category_colors.get(cat_id, "#6B7280")

            priority_badge = ""
            if is_mapped:
                badge_colors = {
                    "essential": "#10B981",
                    "high": "#3B82F6",
                    "medium": "#F59E0B",
                    "optional": "#9CA3AF",
                }
                badge_color = badge_colors.get(priority, "#6B7280")
                priority_badge = f'<span class="priority-badge" style="background: {badge_color}">{priority.upper()}</span>'

            opacity = "1" if is_mapped else "0.4"

            # Get full description for hover
            full_desc = cap_data.get('description', '')
            justification = mapping.justification if mapping and mapping.justification else ''

            card = f'''
            <div class="capability-card" style="border-color: {color}; opacity: {opacity};" data-category="{cat_id}" data-priority="{priority}">
                <div class="cap-header" style="background: {color}20; border-bottom: 2px solid {color};">
                    <span class="cap-id">{cap_id}</span>
                    {priority_badge}
                </div>
                <div class="cap-name">{cap_data.get('name', '')}</div>
                <div class="cap-description">{full_desc}</div>
                {f'<div class="cap-justification"><strong>Why needed:</strong> {justification}</div>' if justification else ''}
            </div>
            '''
            capability_cards.append(card)

    # Generate complete HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent CPT Assessment - {form_data.get('industry', 'Assessment')}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .header {{ text-align: center; padding: 30px; background: white; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header h1 {{ color: #1F2937; margin-bottom: 10px; }}
        .header .meta {{ color: #6B7280; }}
        .filters {{ display: flex; gap: 10px; justify-content: center; margin-bottom: 20px; flex-wrap: wrap; }}
        .filter-btn {{ padding: 8px 16px; border: 2px solid #E5E7EB; border-radius: 20px; background: white; cursor: pointer; font-weight: 500; }}
        .filter-btn:hover {{ background: #F3F4F6; }}
        .filter-btn.active {{ background: #3B82F6; color: white; border-color: #3B82F6; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }}
        .capability-card {{
            background: white;
            border-radius: 8px;
            border: 2px solid #E5E7EB;
            overflow: hidden;
            transition: all 0.3s ease;
            position: relative;
            min-height: 100px;
        }}
        .capability-card:hover {{
            transform: translateY(-4px) scale(1.02);
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            z-index: 100;
        }}
        .cap-header {{ padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; }}
        .cap-id {{ font-weight: bold; font-size: 0.9rem; }}
        .priority-badge {{ font-size: 0.65rem; padding: 2px 6px; border-radius: 10px; color: white; }}
        .cap-name {{
            padding: 8px 12px;
            font-size: 0.85rem;
            font-weight: 500;
            line-height: 1.3;
            /* Truncate by default */
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .capability-card:hover .cap-name {{
            /* Show full text on hover */
            -webkit-line-clamp: unset;
            overflow: visible;
        }}
        .cap-description {{
            padding: 0 12px;
            font-size: 0.75rem;
            color: #6B7280;
            line-height: 1.4;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease, padding 0.3s ease;
        }}
        .capability-card:hover .cap-description {{
            max-height: 200px;
            padding: 8px 12px;
        }}
        .cap-justification {{
            padding: 0 12px;
            font-size: 0.75rem;
            color: #4B5563;
            line-height: 1.4;
            background: #F9FAFB;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease, padding 0.3s ease;
        }}
        .capability-card:hover .cap-justification {{
            max-height: 150px;
            padding: 8px 12px;
            margin-top: 4px;
        }}
        .legend {{ display: flex; gap: 20px; justify-content: center; margin-top: 20px; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 0.85rem; }}
        .legend-color {{ width: 16px; height: 16px; border-radius: 4px; }}
        .hidden {{ display: none !important; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI Agent Capability Assessment</h1>
        <div class="meta">
            <strong>Industry:</strong> {form_data.get('industry', 'N/A')} |
            <strong>Agent Type:</strong> {agent_type} |
            <strong>Capabilities Mapped:</strong> {len(mappings)}
        </div>
    </div>

    <div class="filters">
        <button class="filter-btn active" data-filter="all">All</button>
        <button class="filter-btn" data-filter="essential">Essential</button>
        <button class="filter-btn" data-filter="high">High Priority</button>
        <button class="filter-btn" data-filter="medium">Medium</button>
        <button class="filter-btn" data-filter="optional">Optional</button>
        <button class="filter-btn" data-filter="not-mapped">Not Mapped</button>
    </div>

    <div class="grid">
        {''.join(capability_cards)}
    </div>

    <div class="legend">
        <div class="legend-item"><div class="legend-color" style="background: #3B82F6;"></div> PK: Perception & Knowledge</div>
        <div class="legend-item"><div class="legend-color" style="background: #F97316;"></div> CG: Cognition & Reasoning</div>
        <div class="legend-item"><div class="legend-color" style="background: #A855F7;"></div> LA: Learning & Adaptation</div>
        <div class="legend-item"><div class="legend-color" style="background: #6B7280;"></div> AE: Action & Execution</div>
        <div class="legend-item"><div class="legend-color" style="background: #14B8A6;"></div> IC: Interaction & Collaboration</div>
        <div class="legend-item"><div class="legend-color" style="background: #EF4444;"></div> GS: Governance & Safety</div>
    </div>

    <script>
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const filter = btn.dataset.filter;
                document.querySelectorAll('.capability-card').forEach(card => {{
                    if (filter === 'all') {{
                        card.classList.remove('hidden');
                    }} else {{
                        card.classList.toggle('hidden', card.dataset.priority !== filter);
                    }}
                }});
            }});
        }});
    </script>
</body>
</html>'''

    return html


def format_capability_mapping_for_display(result: CapabilityMappingResult) -> Dict[str, Any]:
    """Format capability mapping for Streamlit display.

    Args:
        result: CapabilityMappingResult object

    Returns:
        Dictionary formatted for UI display
    """
    return {
        "status": result.status,
        "agent_type": result.agent_type,
        "total_mapped": len(result.mappings),
        "essential_count": len(result.essential_capabilities),
        "advanced_count": len(result.advanced_capabilities),
        "optional_count": len(result.optional_capabilities),
        "essential_capabilities": result.essential_capabilities,
        "advanced_capabilities": result.advanced_capabilities,
        "optional_capabilities": result.optional_capabilities,
        "mappings": [
            {
                "id": m.capability_id,
                "name": m.capability_name,
                "category": m.category_id,
                "priority": m.priority,
                "justification": m.justification,
            }
            for m in result.mappings
        ],
        "full_document": result.mapping_document,
        "html_visualization": result.html_visualization,
        "error": result.error_message,
    }
