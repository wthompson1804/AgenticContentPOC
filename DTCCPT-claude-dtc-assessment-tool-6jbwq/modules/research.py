"""
Research module for Open Deep Research integration.

This module provides the research functionality for Step 0 of the DTC workflow,
using LangChain's Open Deep Research framework to conduct comprehensive
industry and regulatory research.
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


@dataclass
class ResearchArea:
    """Represents a research area with its findings."""
    name: str
    findings: str = ""
    summary: str = ""  # AI-generated 2-3 sentence summary
    sources: List[Dict[str, str]] = field(default_factory=list)
    confidence: str = "medium"  # high, medium, low


@dataclass
class ResearchResult:
    """Complete research results for a use case."""
    industry: str
    use_case: str
    jurisdiction: str

    # Research areas
    industry_adoption: ResearchArea = field(default_factory=lambda: ResearchArea("Industry AI Adoption"))
    regulatory_environment: ResearchArea = field(default_factory=lambda: ResearchArea("Regulatory Environment"))
    technical_integration: ResearchArea = field(default_factory=lambda: ResearchArea("Technical Integration"))
    risk_failure_modes: ResearchArea = field(default_factory=lambda: ResearchArea("Risk & Failure Modes"))
    economic_viability: ResearchArea = field(default_factory=lambda: ResearchArea("Economic Viability"))

    # Preliminary assessment
    go_no_go: str = "pending"  # go, caution, no-go, pending
    recommended_type: str = "T2"  # T0-T4
    confidence_level: str = "medium"  # high, medium, low
    key_risks: List[str] = field(default_factory=list)
    critical_success_factors: List[str] = field(default_factory=list)
    recommendation_rationale: str = ""  # Explanation of why go/caution/no-go

    # Metadata
    status: str = "pending"  # pending, in_progress, complete, error
    error_message: Optional[str] = None
    all_sources: List[Dict[str, str]] = field(default_factory=list)
    full_content: str = ""  # Store full research response


def load_research_template() -> str:
    """Load the enhanced Step 0 research brief template."""
    template_path = Path(__file__).parent.parent / "prompts" / "step_0_research_brief.md"

    with open(template_path, 'r') as f:
        return f.read()


def build_research_prompt(
    industry: str,
    use_case: str,
    jurisdiction: str,
    organization_size: str = "Enterprise",
    timeline: str = "Pilot Project"
) -> str:
    """Build the complete research prompt from the template.

    Args:
        industry: Industry sector
        use_case: Use case description
        jurisdiction: Primary regulatory jurisdiction
        organization_size: Organization size category
        timeline: Implementation timeline

    Returns:
        Formatted research prompt
    """
    template = load_research_template()

    # Replace placeholders - handle None values with defaults
    prompt = template.replace("{industry}", industry or "unspecified")
    prompt = prompt.replace("{use_case}", use_case or "unspecified")
    prompt = prompt.replace("{jurisdiction}", jurisdiction or "unspecified")
    prompt = prompt.replace("{organization_size}", organization_size or "unspecified")
    prompt = prompt.replace("{timeline}", timeline or "standard")

    return prompt


def get_anthropic_client(model: str = "claude-sonnet-4-20250514", api_key: Optional[str] = None) -> ChatAnthropic:
    """Get an Anthropic Claude client.

    Args:
        model: Model name to use
        api_key: Optional API key (falls back to environment variable)

    Returns:
        ChatAnthropic client instance
    """
    # Use provided key or fall back to environment
    key = api_key or os.getenv("ANTHROPIC_API_KEY")

    if not key:
        raise ValueError("ANTHROPIC_API_KEY not provided")

    return ChatAnthropic(
        model=model,
        api_key=key,
        max_tokens=8192,
    )


async def conduct_research_async(
    industry: str,
    use_case: str,
    jurisdiction: str,
    organization_size: str = "Enterprise",
    timeline: str = "Pilot Project",
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None
) -> ResearchResult:
    """Conduct comprehensive research asynchronously.

    This is the main research function that integrates with Claude
    to conduct the DTC-specific research across all 5 areas.

    Args:
        industry: Industry sector
        use_case: Use case description
        jurisdiction: Primary regulatory jurisdiction
        organization_size: Organization size
        timeline: Implementation timeline
        model: Claude model to use
        api_key: Optional API key

    Returns:
        ResearchResult with findings
    """
    result = ResearchResult(
        industry=industry,
        use_case=use_case,
        jurisdiction=jurisdiction,
        status="in_progress"
    )

    try:
        client = get_anthropic_client(model, api_key)

        # Build the research prompt
        research_prompt = build_research_prompt(
            industry=industry,
            use_case=use_case,
            jurisdiction=jurisdiction,
            organization_size=organization_size,
            timeline=timeline
        )

        # System message for research context
        system_message = SystemMessage(content="""You are a senior research analyst specializing in industrial AI implementations and digital twin technologies.

Your task is to conduct comprehensive research for an AI agent capability assessment following the Digital Twin Consortium methodology.

Guidelines:
1. Provide specific, actionable intelligence grounded in current industry knowledge
2. Cite specific sources, standards, and regulations where applicable
3. Be honest about areas of uncertainty or where information is limited
4. Focus on practical implications for implementation
5. Consider both technical and organizational factors

When recommending an agent type (T0-T4), consider:
- T0: Simple rule-based automation (deterministic, no learning)
- T1: Conversational interfaces (NLP, basic context)
- T2: Procedural workflows (multi-step, tool integration)
- T3: Cognitive autonomy (planning, learning, adaptation)
- T4: Multi-agent systems (distributed, collaborative)

IMPORTANT OUTPUT FORMAT REQUIREMENTS:

1. For each research section, start with a "**Summary:**" line containing a 2-3 sentence overview, then provide detailed findings below.

2. For your Preliminary Assessment, you MUST include:
   - **Go/No-Go Recommendation:** [Go/Caution/No-Go]
   - **Recommended Agent Type:** [T0-T4]
   - **Confidence Level:** [High/Medium/Low]
   - **Key Risk Factors:**
     - [Bullet list of 3-5 specific risks]
   - **Critical Success Factors:**
     - [Bullet list of 3-5 specific success factors]
   - **Recommendation Rationale:**
     [A paragraph explaining WHY you made this recommendation. Be specific about the key factors that led to your conclusion. If recommending caution or no-go, explain what would need to change for it to become viable.]

Provide your research in a structured format with clear sections for each research area.""")

        # Execute research query
        response = await client.ainvoke([
            system_message,
            HumanMessage(content=research_prompt)
        ])

        # Parse response into research result
        research_content = response.content

        # Store full content for reference
        result.full_content = research_content

        # Update result with findings
        result.status = "complete"

        # Extract each research section with findings and summaries
        result.industry_adoption.findings = extract_section(research_content, "Industry AI Adoption")
        result.industry_adoption.summary = extract_summary(result.industry_adoption.findings)

        result.regulatory_environment.findings = extract_section(research_content, "Regulatory Environment")
        result.regulatory_environment.summary = extract_summary(result.regulatory_environment.findings)

        result.technical_integration.findings = extract_section(research_content, "Technical Integration")
        result.technical_integration.summary = extract_summary(result.technical_integration.findings)

        result.risk_failure_modes.findings = extract_section(research_content, "Risk & Failure Modes")
        result.risk_failure_modes.summary = extract_summary(result.risk_failure_modes.findings)

        result.economic_viability.findings = extract_section(research_content, "Economic Viability")
        result.economic_viability.summary = extract_summary(result.economic_viability.findings)

        # Update confidence for each area based on content quality
        for area in [result.industry_adoption, result.regulatory_environment,
                     result.technical_integration, result.risk_failure_modes,
                     result.economic_viability]:
            if len(area.findings) > 500:
                area.confidence = "high"
            elif len(area.findings) > 100:
                area.confidence = "medium"
            else:
                area.confidence = "low"

        # Extract recommendations
        result.go_no_go = extract_go_no_go(research_content)
        result.recommended_type = extract_agent_type(research_content)
        result.confidence_level = extract_confidence(research_content)

        # Extract key risks and success factors
        result.key_risks = extract_bullet_list(research_content, "Key Risk Factors")
        result.critical_success_factors = extract_bullet_list(research_content, "Critical Success Factors")

        # If no risks extracted, try alternative patterns
        if not result.key_risks:
            result.key_risks = extract_bullet_list(research_content, "Risk Factors")
        if not result.critical_success_factors:
            result.critical_success_factors = extract_bullet_list(research_content, "Success Factors")

        # Extract recommendation rationale
        result.recommendation_rationale = extract_rationale(research_content)

        return result

    except Exception as e:
        result.status = "error"
        result.error_message = str(e)
        return result


def conduct_research(
    industry: str,
    use_case: str,
    jurisdiction: str,
    organization_size: str = "Enterprise",
    timeline: str = "Pilot Project",
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None
) -> ResearchResult:
    """Synchronous wrapper for research function.

    Args:
        industry: Industry sector
        use_case: Use case description
        jurisdiction: Primary regulatory jurisdiction
        organization_size: Organization size
        timeline: Implementation timeline
        model: Claude model to use
        api_key: Optional API key

    Returns:
        ResearchResult with findings
    """
    return asyncio.run(conduct_research_async(
        industry=industry,
        use_case=use_case,
        jurisdiction=jurisdiction,
        organization_size=organization_size,
        timeline=timeline,
        model=model,
        api_key=api_key
    ))


def extract_section(content: str, section_name: str) -> str:
    """Extract a section from the research content.

    Handles various header formats:
    - ## 1. Industry AI Adoption
    - ## Industry AI Adoption
    - # Industry AI Adoption
    - ### INDUSTRY AI ADOPTION
    - **Industry AI Adoption**

    Args:
        content: Full research content
        section_name: Name of section to extract

    Returns:
        Section content or empty string
    """
    import re

    # Build flexible patterns for the section name
    # Allow for numbering, different header levels, and case variations
    section_words = section_name.split()

    # Name variations mapping - be specific to avoid matching executive summary
    name_variations = {
        "Industry AI Adoption": ["Industry AI Adoption", "AI Adoption Patterns", "Industry Adoption Trends", "Sector AI Adoption"],
        "Regulatory Environment": ["Regulatory Environment", "Regulatory Landscape", "Regulatory Framework", "Compliance Requirements", "Legal Framework"],
        "Technical Integration": ["Technical Integration", "Integration Requirements", "Technology Stack", "Technical Architecture", "System Integration"],
        "Risk & Failure Modes": ["Risk & Failure Modes", "Risk and Failure Modes", "Failure Modes", "Risk Analysis", "Risk Assessment"],
        "Economic Viability": ["Economic Viability", "Economic Analysis", "Financial Viability", "ROI Analysis", "Cost-Benefit"],
    }

    # Sections to explicitly skip (these contain summaries, not detailed content)
    skip_sections = ["executive summary", "preliminary assessment", "summary", "overview", "introduction", "conclusion"]

    variations = name_variations.get(section_name, [section_name])

    for variation in variations:
        var_words = variation.split()

        # Pattern variations to try
        patterns = [
            # Numbered markdown header: ## 1. Industry AI Adoption
            rf"#{1,4}\s*\d+\.?\s*{re.escape(variation)}[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
            # Plain markdown header: ## Industry AI Adoption
            rf"#{1,4}\s*{re.escape(variation)}[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
            # Bold header: **1. Industry AI Adoption**
            rf"\*\*\d*\.?\s*{re.escape(variation)}[:\*]*\*\*[^\n]*\n(.*?)(?=\n\*\*\d*\.|\n#{1,4}\s|\Z)",
            # Numbered without hash: 1. Industry AI Adoption
            rf"^\d+\.\s*{re.escape(variation)}[^\n]*\n(.*?)(?=\n\d+\.|\n#{1,4}\s|\Z)",
        ]

        # Also try with partial matches for key words
        if len(var_words) >= 2:
            # Match on key distinctive words
            key_word1 = re.escape(var_words[0])
            key_word2 = re.escape(var_words[-1])
            patterns.extend([
                rf"#{1,4}\s*\d*\.?\s*[^\n]*{key_word1}[^\n]*{key_word2}[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
            ])

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
            if match:
                result = match.group(1).strip()
                # Ensure we got actual content, not just whitespace
                # Also check we're not in a skip section by looking at what came before
                if len(result) > 20:
                    # Check if this is actually from a skip section
                    match_start = match.start()
                    preceding_text = content[max(0, match_start-200):match_start].lower()
                    is_skip_section = any(skip in preceding_text for skip in skip_sections)
                    if not is_skip_section:
                        return result

    # Last resort: try to find any section that contains the key words
    # But be more strict - require multiple key words and exclude skip sections
    key_words = [w for w in section_words if len(w) > 3]
    if len(key_words) >= 2:
        # Look for headers containing multiple key words
        pattern = rf"#{1,4}\s*\d*\.?\s*([^\n]*)\n(.*?)(?=\n#{1,4}\s|\Z)"
        for match in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
            header = match.group(1).lower()
            # Check header contains key words and isn't a skip section
            if sum(1 for kw in key_words if kw.lower() in header) >= 2:
                if not any(skip in header for skip in skip_sections):
                    result = match.group(2).strip()
                    if len(result) > 50:
                        return result

    return ""


def extract_go_no_go(content: str) -> str:
    """Extract go/no-go recommendation from content."""
    content_lower = content.lower()

    if "no-go" in content_lower or "not recommended" in content_lower:
        return "no-go"
    elif "caution" in content_lower or "proceed with caution" in content_lower:
        return "caution"
    elif "go" in content_lower or "recommended" in content_lower:
        return "go"

    return "caution"  # Default to caution


def extract_agent_type(content: str) -> str:
    """Extract recommended agent type from content."""
    import re

    # Look for explicit T0-T4 mentions
    match = re.search(r'\b(T[0-4])\b', content)
    if match:
        return match.group(1)

    # Try to infer from keywords
    content_lower = content.lower()

    if "multi-agent" in content_lower or "mags" in content_lower or "distributed" in content_lower:
        return "T4"
    elif "cognitive" in content_lower or "autonomous" in content_lower or "learning" in content_lower:
        return "T3"
    elif "workflow" in content_lower or "procedural" in content_lower or "tool" in content_lower:
        return "T2"
    elif "conversational" in content_lower or "chatbot" in content_lower:
        return "T1"
    elif "rule-based" in content_lower or "static" in content_lower:
        return "T0"

    return "T2"  # Default to procedural workflow


def extract_confidence(content: str) -> str:
    """Extract confidence level from content."""
    content_lower = content.lower()

    if "high confidence" in content_lower or "strongly recommend" in content_lower:
        return "high"
    elif "low confidence" in content_lower or "limited information" in content_lower:
        return "low"

    return "medium"


def extract_bullet_list(content: str, section_name: str) -> List[str]:
    """Extract a bullet list from content following a section header.

    Args:
        content: Full research content
        section_name: Name of section containing the bullet list

    Returns:
        List of bullet items
    """
    import re

    items = []

    # Normalize variations of the section name
    name_variations = [section_name]
    if "Risk" in section_name:
        name_variations.extend(["Key Risks", "Risk Factors", "Primary Risks", "Main Risks", "Risks"])
    if "Success" in section_name:
        name_variations.extend(["Success Factors", "Critical Factors", "Key Success Factors", "CSF"])

    # Try to find the section and extract bullets with multiple pattern variations
    for name in name_variations:
        patterns = [
            # **Key Risk Factors:** followed by bullet list
            rf"\*\*{re.escape(name)}[:\*]*\*\*[^\n]*\n((?:\s*[-*•]\s*[^\n]+\n?)+)",
            # **Key Risk Factors:** with inline bullets on same line and below
            rf"\*\*{re.escape(name)}[:\*]*\*\*\s*\n?((?:[-*•]\s*[^\n]+\n?)+)",
            # Key Risk Factors: (no bold)
            rf"{re.escape(name)}[:\s]*\n((?:\s*[-*•]\s*[^\n]+\n?)+)",
            # ### Key Risk Factors (markdown header)
            rf"#{1,4}\s*{re.escape(name)}[^\n]*\n((?:\s*[-*•]\s*[^\n]+\n?)+)",
            # Numbered list: 1. First risk
            rf"\*\*{re.escape(name)}[:\*]*\*\*[^\n]*\n((?:\s*\d+\.\s*[^\n]+\n?)+)",
            rf"{re.escape(name)}[:\s]*\n((?:\s*\d+\.\s*[^\n]+\n?)+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                bullet_text = match.group(1)
                # Extract bullet items (dash, asterisk, bullet, or number)
                bullet_matches = re.findall(r'(?:[-*•]|\d+\.)\s*(.+?)(?=\n\s*(?:[-*•]|\d+\.)|\n\n|\n\*\*|\Z)', bullet_text, re.DOTALL)
                for item in bullet_matches:
                    clean_item = item.strip().rstrip('\n').strip()
                    # Remove any trailing markdown like ** that might be captured
                    clean_item = re.sub(r'\*\*$', '', clean_item).strip()
                    if clean_item and len(clean_item) > 3 and clean_item not in items:
                        items.append(clean_item)
                if items:
                    return items[:5]

    # Fallback: Look for any bullet list near keywords
    if not items:
        keywords = section_name.lower().split()
        for keyword in keywords:
            if len(keyword) > 3:
                # Find where this keyword appears and look for bullets nearby
                pattern = rf"{re.escape(keyword)}[^\n]*\n((?:\s*[-*•]\s*[^\n]+\n?)+)"
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    bullet_text = match.group(1)
                    bullet_matches = re.findall(r'[-*•]\s*(.+?)(?=\n[-*•]|\n\n|\Z)', bullet_text, re.DOTALL)
                    for item in bullet_matches:
                        clean_item = item.strip()
                        if clean_item and len(clean_item) > 3 and clean_item not in items:
                            items.append(clean_item)
                    if items:
                        return items[:5]

    return items[:5]  # Return max 5 items


def extract_summary(section_content: str) -> str:
    """Extract or generate a summary from section content.

    Looks for explicit **Summary:** markers, or takes the first paragraph.

    Args:
        section_content: Full section content

    Returns:
        Summary string (2-3 sentences)
    """
    import re

    if not section_content:
        return ""

    # Look for explicit summary marker
    patterns = [
        r"\*\*Summary[:\*]*\*\*\s*(.+?)(?=\n\n|\n\*\*|\n#|\Z)",
        r"Summary[:\s]+(.+?)(?=\n\n|\n\*\*|\n#|\Z)",
    ]

    for pattern in patterns:
        match = re.search(pattern, section_content, re.IGNORECASE | re.DOTALL)
        if match:
            summary = match.group(1).strip()
            if len(summary) > 30:
                return summary

    # Fallback: use first paragraph or first 2-3 sentences
    paragraphs = section_content.split('\n\n')
    for para in paragraphs:
        para = para.strip()
        # Skip if it looks like a header or bullet list
        if para and not para.startswith('#') and not para.startswith('-') and not para.startswith('*'):
            # Get first 2-3 sentences (up to ~300 chars)
            sentences = re.split(r'(?<=[.!?])\s+', para)
            summary_sentences = []
            total_len = 0
            for sent in sentences[:3]:
                if total_len + len(sent) < 350:
                    summary_sentences.append(sent)
                    total_len += len(sent)
                else:
                    break
            if summary_sentences:
                return ' '.join(summary_sentences)

    # Last resort: first 250 characters
    return section_content[:250].strip() + "..." if len(section_content) > 250 else section_content


def extract_rationale(content: str) -> str:
    """Extract the recommendation rationale from content.

    Args:
        content: Full research content

    Returns:
        Rationale explanation string
    """
    import re

    # Look for explicit rationale section with various patterns
    patterns = [
        r"\*\*Recommendation Rationale[:\*]*\*\*\s*\n?(.+?)(?=\n\n\*\*|\n#{1,4}\s|\Z)",
        r"Recommendation Rationale[:\s]+(.+?)(?=\n\n\*\*|\n#{1,4}\s|\Z)",
        r"\*\*Rationale[:\*]*\*\*\s*\n?(.+?)(?=\n\n\*\*|\n#{1,4}\s|\Z)",
        r"#{1,4}\s*Rationale[^\n]*\n(.+?)(?=\n#{1,4}\s|\Z)",
        r"#{1,4}\s*Recommendation Rationale[^\n]*\n(.+?)(?=\n#{1,4}\s|\Z)",
        # Also look for "Why" sections
        r"\*\*Why[:\*]*\*\*\s*\n?(.+?)(?=\n\n\*\*|\n#{1,4}\s|\Z)",
        r"#{1,4}\s*Why[^\n]*\n(.+?)(?=\n#{1,4}\s|\Z)",
        # Analysis or reasoning section
        r"\*\*Analysis[:\*]*\*\*\s*\n?(.+?)(?=\n\n\*\*|\n#{1,4}\s|\Z)",
        r"#{1,4}\s*Analysis[^\n]*\n(.+?)(?=\n#{1,4}\s|\Z)",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            rationale = match.group(1).strip()
            if len(rationale) > 50:
                # Clean up any leading/trailing asterisks
                rationale = re.sub(r'^\*+|\*+$', '', rationale).strip()
                return rationale

    # Fallback: look for reasoning in preliminary assessment section
    prelim_patterns = [
        r"#{1,4}\s*Preliminary Assessment[^\n]*\n(.*?)(?=\n#{1,4}\s[^#]|\Z)",
        r"\*\*Preliminary Assessment[:\*]*\*\*[^\n]*\n(.*?)(?=\n\*\*\d+\.|\n#{1,4}\s|\Z)",
        r"#{1,4}\s*Executive Summary[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
    ]

    for prelim_pattern in prelim_patterns:
        match = re.search(prelim_pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            prelim_section = match.group(1)
            # Look for explanatory text (not just bullet points)
            paragraphs = prelim_section.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                # Find paragraphs that look like explanatory text
                if para and len(para) > 100:
                    # Skip bullet lists and short metadata lines
                    if not para.startswith('-') and not para.startswith('*') and not para.startswith('**Go') and not para.startswith('**Recommended') and not para.startswith('**Confidence'):
                        return para

    # Last resort: Look for any substantial explanatory paragraph after the assessment headers
    assessment_keywords = ["go/no-go", "recommended", "confidence", "assessment"]
    lines = content.split('\n')
    capture_next = False
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in assessment_keywords):
            capture_next = True
            continue
        if capture_next and len(line.strip()) > 100:
            # Found substantial text after assessment metadata
            if not line.strip().startswith('-') and not line.strip().startswith('*'):
                return line.strip()

    return ""


def format_research_for_display(result: ResearchResult) -> Dict[str, Any]:
    """Format research results for Streamlit display.

    Args:
        result: ResearchResult object

    Returns:
        Dictionary formatted for UI display
    """
    # Extract sources from full content if not already populated
    sources = result.all_sources
    if not sources and result.full_content:
        sources = extract_sources(result.full_content)

    return {
        "summary": {
            "industry": result.industry,
            "use_case": result.use_case,
            "jurisdiction": result.jurisdiction,
            "status": result.status,
        },
        "preliminary_assessment": {
            "go_no_go": result.go_no_go,
            "recommended_type": result.recommended_type,
            "confidence_level": result.confidence_level,
            "key_risks": result.key_risks,
            "critical_success_factors": result.critical_success_factors,
            "recommendation_rationale": result.recommendation_rationale,
        },
        "research_areas": {
            "industry_adoption": {
                "name": result.industry_adoption.name,
                "findings": result.industry_adoption.findings,
                "summary": result.industry_adoption.summary,
                "confidence": result.industry_adoption.confidence,
            },
            "regulatory_environment": {
                "name": result.regulatory_environment.name,
                "findings": result.regulatory_environment.findings,
                "summary": result.regulatory_environment.summary,
                "confidence": result.regulatory_environment.confidence,
            },
            "technical_integration": {
                "name": result.technical_integration.name,
                "findings": result.technical_integration.findings,
                "summary": result.technical_integration.summary,
                "confidence": result.technical_integration.confidence,
            },
            "risk_failure_modes": {
                "name": result.risk_failure_modes.name,
                "findings": result.risk_failure_modes.findings,
                "summary": result.risk_failure_modes.summary,
                "confidence": result.risk_failure_modes.confidence,
            },
            "economic_viability": {
                "name": result.economic_viability.name,
                "findings": result.economic_viability.findings,
                "summary": result.economic_viability.summary,
                "confidence": result.economic_viability.confidence,
            },
        },
        "sources": sources,
        "full_content": result.full_content,
        "error": result.error_message,
    }


def extract_sources(content: str) -> List[Dict[str, str]]:
    """Extract source citations from research content.

    Args:
        content: Full research content

    Returns:
        List of source dictionaries with title and url keys
    """
    import re

    sources = []

    # Look for markdown links: [Title](URL)
    link_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
    matches = re.findall(link_pattern, content)

    for title, url in matches:
        if not any(s.get('url') == url for s in sources):  # Avoid duplicates
            sources.append({"title": title.strip(), "url": url.strip()})

    # Look for plain URLs with context
    url_pattern = r'(?:^|\s)(https?://[^\s\)]+)'
    url_matches = re.findall(url_pattern, content)

    for url in url_matches:
        if not any(s.get('url') == url for s in sources):
            sources.append({"title": url.split('/')[2], "url": url})

    return sources[:15]  # Limit to 15 sources
