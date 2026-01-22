# DTC AI Agent Capability Assessment Tool

A Streamlit web application for assessing AI agent capabilities using the Digital Twin Consortium's Capabilities Periodic Table (CPT) framework.

## Overview

This tool provides a guided 4-step workflow for industrial AI planners to:

1. **Research** - Conduct comprehensive industry and regulatory research
2. **Requirements** - Generate business requirements following DTC methodology
3. **Agent Design** - Assess appropriate agent type (T0-T4) and architecture
4. **Capability Mapping** - Map to 45 capabilities in the CPT framework

## Features

- **Deep Research Integration** - Uses Anthropic Claude for grounded, cited research
- **DTC Methodology Fidelity** - Executes DTC prompts unchanged
- **Human-in-the-Loop** - Confirmation checkpoints at each step
- **Interactive Visualization** - HTML periodic table with filtering
- **Export Capabilities** - Markdown, HTML, and complete packages
- **Demo Mode** - Works without API key for testing

## Quick Start

```bash
# Clone and navigate
cd dtc-assessment-tool

# Install dependencies
pip install -r requirements.txt

# Set API key (optional - demo mode available without)
export ANTHROPIC_API_KEY=sk-ant-...

# Run the application
streamlit run app.py
```

## Project Structure

```
dtc-assessment-tool/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── config.yaml            # Application configuration
├── .env.example           # Environment variable template
│
├── modules/               # Core business logic
│   ├── data_loader.py     # DTC data loading utilities
│   ├── research.py        # Research integration (Step 0)
│   ├── requirements.py    # Requirements generation (Step 1)
│   ├── agent_design.py    # Agent type assessment (Step 2)
│   ├── capability_mapping.py  # CPT mapping (Step 3)
│   └── export.py          # Export utilities
│
├── components/            # Streamlit UI components
│   ├── sidebar.py         # Navigation sidebar
│   ├── progress.py        # Step progress indicator
│   ├── input_form.py      # Use case input form
│   └── research_display.py # Research results display
│
├── prompts/               # DTC prompt templates
│   ├── step_0_*.md        # Research prompts
│   ├── step_1_*.md        # Requirements prompt
│   ├── step_2_*.md        # Agent design prompt
│   └── step_3_*.md        # Capability mapping prompt
│
└── data/
    └── ai_agent_cpt.yaml  # 45-capability CPT definitions
```

## Agent Types (T0-T4)

| Type | Name | Description |
|------|------|-------------|
| T0 | Static Automation | Pre-programmed, rule-based systems |
| T1 | Conversational Agents | NLP interaction, basic context |
| T2 | Procedural Workflow Agents | Multi-step execution, tool integration |
| T3 | Cognitive Autonomous Agents | Self-directed planning, learning |
| T4 | Multi-Agent Generative Systems | Collaborative intelligence, distributed coordination |

## Capability Categories

| Code | Category | Color |
|------|----------|-------|
| PK | Perception & Knowledge | Blue |
| CG | Cognition & Reasoning | Orange |
| LA | Learning & Adaptation | Purple |
| AE | Action & Execution | Gray |
| IC | Interaction & Collaboration | Teal |
| GS | Governance & Safety | Red |

## Configuration

### Environment Variables

```bash
# Required for full functionality
ANTHROPIC_API_KEY=sk-ant-...

# Optional for tracing
LANGCHAIN_API_KEY=...
LANGCHAIN_TRACING_V2=true
```

### config.yaml

```yaml
models:
  research: "claude-sonnet-4-20250514"
  summarization: "claude-3-5-haiku-20241022"
  workflow: "claude-sonnet-4-20250514"

research:
  search_api: "anthropic"
  max_concurrent_units: 5
  max_iterations: 3
```

## Usage

### With API Key (Full Functionality)

1. Set `ANTHROPIC_API_KEY` environment variable
2. Run `streamlit run app.py`
3. Enter use case details
4. Click "Start Deep Research" for each step
5. Review and confirm at each checkpoint
6. Export final assessment

### Demo Mode (No API Key)

1. Run `streamlit run app.py`
2. Enter use case details
3. Click "Skip Research (Demo Mode)" at each step
4. Navigate through workflow with placeholder data
5. Useful for UI testing and demonstrations

## Development

Built using the GSD (Get Shit Done) framework for structured development.

### Phase 1: Infrastructure
- Streamlit app skeleton
- DTC data loading
- Session state management

### Phase 2: Research Integration
- Anthropic Claude integration
- Research prompt templates
- Citation display

### Phase 3: DTC Workflow
- Requirements generation
- Agent type assessment
- Capability mapping

### Phase 4: Polish & Export
- Export capabilities
- Error handling
- Documentation

## Source Materials

- [Digital Twin Consortium Capabilities Toolkit](https://github.com/digitaltwinconsortium/capabilities-toolkit)
- [AI Agent CPT YAML](https://github.com/digitaltwinconsortium/capabilities-toolkit/tree/main/ai-agent-cpt)
- [LangChain Open Deep Research](https://github.com/langchain-ai/open_deep_research)

## License

This tool implements the Digital Twin Consortium's CPT framework which is licensed under CC BY-SA 4.0.

---

*Built for serious industrial AI planners who need to ground their decisions in current research.*
