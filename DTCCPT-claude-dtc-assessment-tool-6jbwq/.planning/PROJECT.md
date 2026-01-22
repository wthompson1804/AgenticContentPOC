# DTC AI Agent Capability Assessment Tool

## What This Is

A production-ready Streamlit web application that provides a friendly GUI for the Digital Twin Consortium's AI Agent Capabilities Periodic Table (CPT) assessment workflow. The tool uses LangChain's Open Deep Research framework (powered by Anthropic Claude) for grounded research, then executes the DTC's existing 4-step sequential prompt workflow unchanged.

## Core Value

Ground AI agent planning decisions in current, cited research for serious industrial planners and operators of AI systems that interact with the physical world. Physical systems have higher stakes than chatbots: equipment damage, safety incidents, regulatory violations.

## Target Users

- Industrial AI planners
- Digital twin operators
- Systems integrators
- Enterprise architects
- Compliance officers

## Problem Being Solved

1. Current AI planning relies on LLM training knowledge (stale, uncited)
2. The DTC methodology exists but lacks a user-friendly interface
3. Industrial operators need transparency and traceability for stakeholder review
4. No tool currently grounds DTC assessments in real-time research

## Key Constraints

- **Methodology Fidelity**: DTC prompts must execute exactly as designed - NO modifications
- **Research Grounding**: Use Open Deep Research for cited, current intelligence
- **Human-in-the-Loop**: Honor explicit pause points in DTC methodology
- **Transparency**: Show search queries, source URLs, confidence levels
- **Export Quality**: Documents must be suitable for executive presentations

## Technical Stack

- **Frontend**: Streamlit (web-hosted application)
- **Research Engine**: LangChain Open Deep Research
- **LLM Provider**: Anthropic Claude (claude-sonnet-4-20250514, claude-haiku-3.5)
- **Search**: Anthropic native web search (no Tavily dependency)
- **Data Format**: YAML (DTC capability definitions)
- **Export**: PDF, DOCX, HTML visualization

## Source Materials

### DTC Repository
- Main: https://github.com/digitaltwinconsortium/capabilities-toolkit
- AI Agent CPT YAML: https://raw.githubusercontent.com/digitaltwinconsortium/capabilities-toolkit/main/ai-agent-cpt/ai_agent_cpt.yaml
- Sequence Prompts: https://github.com/digitaltwinconsortium/capabilities-toolkit/tree/main/ai-agent-cpt/prompts/aia_sequence_prompts

### DTC 4-Step Workflow
1. **Step 0**: Pre-research industry analysis (enhanced with Open Deep Research)
2. **Step 1**: Business requirements extraction
3. **Step 2**: Agent type assessment (T0-T4) and architecture design
4. **Step 3**: 45-capability CPT mapping with HTML visualization

### AI Agent Types (DTC Framework)
- T0: Static Automation - Pre-programmed, rule-based
- T1: Conversational Agents - NLP interaction, basic context
- T2: Procedural Workflow Agents - Multi-step execution, tool integration
- T3: Cognitive Autonomous Agents - Self-directed planning, learning
- T4: Multi-Agent Generative Systems (MAGS) - Collaborative intelligence

### Capability Categories (45 total)
- PK - Perception & Knowledge (blue)
- CG - Cognition & Reasoning (orange)
- LA - Learning & Adaptation (purple)
- AE - Action & Execution (gray)
- IC - Interaction & Collaboration (teal)
- GS - Governance & Safety (red)

## Open Deep Research Integration

### Why Open Deep Research
- Benchmarked: Ranked #6 on Deep Research Bench (RACE score 0.4344)
- Production-grade: 10.1k GitHub stars, MIT license, active development
- Anthropic native: Supports Claude's native web search
- LangGraph-based: Proper state management, parallel execution

### Configuration
```python
config = {
    "search_api": "anthropic",
    "research_model": "anthropic:claude-sonnet-4-20250514",
    "summarization_model": "anthropic:claude-haiku-3.5",
    "compression_model": "anthropic:claude-sonnet-4-20250514",
    "final_report_model": "anthropic:claude-sonnet-4-20250514",
    "max_concurrent_research_units": 5,
    "max_researcher_iterations": 3
}
```

## Requirements

### Validated

(None yet - building from scratch)

### Active

- [ ] REQ-01: Deep research produces cited, current, industry-specific intelligence
- [ ] REQ-02: DTC prompts execute exactly as designed with no modifications
- [ ] REQ-03: Non-technical planners can navigate workflow without training
- [ ] REQ-04: Generated documents suitable for executive presentations
- [ ] REQ-05: Users can trace recommendations to specific sources
- [ ] REQ-06: 4-step wizard with progressive disclosure
- [ ] REQ-07: Human-in-the-loop checkpoints after each step
- [ ] REQ-08: Export at every stage (PDF, DOCX, HTML)
- [ ] REQ-09: Interactive CPT periodic table visualization
- [ ] REQ-10: Session state persistence across steps

### Out of Scope

- Mobile-native app (web responsive is sufficient)
- Multi-user collaboration (single-user workflow)
- Custom prompt modification UI (methodology fidelity)
- Database persistence (session-based only for v1)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Streamlit over React | Faster development, Python ecosystem, data science friendly | Pending |
| Open Deep Research over custom | Benchmarked, maintained, Anthropic-native | Pending |
| Embedded library over LangGraph server | Simpler deployment for v1 | Pending |

---
*Last updated: 2026-01-19 after initialization from detailed project brief*
