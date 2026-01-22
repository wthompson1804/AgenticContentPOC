# Roadmap

## Overview

| Phase | Name | Goal | Requirements |
|-------|------|------|--------------|
| 1 | Infrastructure | Core Streamlit app with project structure and DTC data | DTC-01, DTC-07, UI-01, UI-02, UI-03, INF-01, INF-02, INF-05 |
| 2 | Research Integration | Open Deep Research integration with DTC-specific prompting | RES-01, RES-02, RES-03, RES-05, DTC-02 |
| 3 | DTC Workflow | Complete 4-step workflow with human-in-the-loop checkpoints | DTC-03, DTC-04, DTC-05, DTC-06, RES-04, UI-04, UI-05, UI-06, INF-04 |
| 4 | Polish & Export | Interactive visualization, exports, error handling | UI-07, UI-08, EXP-01, EXP-02, EXP-03, EXP-04, EXP-05, INF-03 |
| 5 | Chat-First Intake | Conversational intake with progressive 2-pager artifact | PRD v1.1 Parts 1-22 |

---

## Phase 1: Infrastructure

**Goal:** Establish core Streamlit application with project structure, DTC data loading, and basic 4-step wizard UI

**Requirements:** DTC-01, DTC-07, UI-01, UI-02, UI-03, INF-01, INF-02, INF-05

### Success Criteria

1. User can launch Streamlit app and see 4-step wizard interface
2. DTC prompts loaded from repository or local cache
3. ai_agent_cpt.yaml parsed and accessible
4. User can enter industry, use case, jurisdiction inputs
5. Session state persists across page interactions
6. Configuration file supports API key and model settings

### Deliverables

- `app.py` - Main Streamlit application
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variable template
- `config.yaml` - Model and API configuration
- `prompts/` - DTC prompt templates (fetched from repo)
- `data/ai_agent_cpt.yaml` - Capability definitions
- `modules/__init__.py` - Module initialization
- `components/sidebar.py` - Navigation component
- `components/progress.py` - Step progress indicator

---

## Phase 2: Research Integration

**Goal:** Integrate Open Deep Research with DTC-specific research brief for grounded industry analysis

**Requirements:** RES-01, RES-02, RES-03, RES-05, DTC-02

### Success Criteria

1. User inputs trigger comprehensive research across 5 areas
2. Research returns cited sources with URLs
3. Research produces preliminary T0-T4 recommendation
4. Research results stored in session state for downstream steps
5. Research can be re-run with modified inputs

### Deliverables

- `modules/research.py` - Open Deep Research integration
- Enhanced Step 0 research brief template
- Research result data structures
- Integration with Anthropic Claude API

---

## Phase 3: DTC Workflow

**Goal:** Execute complete DTC 4-step workflow with proper output chaining and human-in-the-loop checkpoints

**Requirements:** DTC-03, DTC-04, DTC-05, DTC-06, RES-04, UI-04, UI-05, UI-06, INF-04

### Success Criteria

1. Step 1 generates business requirements from research + user context
2. Step 2 assesses agent type with user confirmation dialog
3. Step 3 maps to 45 capabilities with justifications
4. Each step receives outputs from all prior steps
5. User can pause and review at each step transition
6. Progress indicators show LLM operation status

### Deliverables

- `modules/requirements.py` - Step 1 execution
- `modules/agent_design.py` - Step 2 execution
- `modules/capability_mapping.py` - Step 3 execution
- `components/research_display.py` - Research results UI
- Step transition confirmation dialogs
- Output chaining logic

---

## Phase 4: Polish & Export

**Goal:** Interactive CPT visualization, export capabilities, responsive design, error handling

**Requirements:** UI-07, UI-08, EXP-01, EXP-02, EXP-03, EXP-04, EXP-05, INF-03

### Success Criteria

1. Interactive periodic table shows 45 capabilities with color coding
2. Capability cards show priority, justification, maturity level
3. Export produces professional PDF/DOCX documents
4. HTML visualization is self-contained and shareable
5. Error messages are user-friendly and actionable
6. UI works well on various screen sizes

### Deliverables

- `components/periodic_table.py` - Interactive CPT visualization
- `modules/export.py` - Document generation (PDF, DOCX, HTML)
- Error handling wrappers
- Responsive CSS/styling
- Complete planning package export

---

---

## Phase 5: Chat-First Intake

**Goal:** Transform form-based wizard into conversational chat-first experience with progressive 2-pager artifact

**Requirements:** PRD v1.1 (DTC_AI_Agent_Assessment_PRD_v1.md)

### Success Criteria

1. User can complete intake via natural conversation (S0-S5 states)
2. Progressive 2-pager artifact updates in real-time alongside chat
3. Judgment engine extracts CJ01-CJ10 from conversation
4. Timebox enforces 8-12 turns default, 18 turn hard cap
5. Agent type confirmation gate blocks Step 3 until confirmed
6. Voice input via Whisper (optional, graceful degradation)

### Deliverables

- `modules/chat_intake.py` - State machine S0-S5
- `modules/artifact_panel.py` - 2-pager rendering
- `modules/judgment_engine.py` - CJ extraction + inference
- `modules/timebox.py` - Turn tracking
- Modified `app.py` - Two-column layout, chat UI
- Extended `modules/export.py` - Email + slide outline exports

---

## Progress

| Phase | Status | Completed |
|-------|--------|-----------|
| 1 | Complete | 2026-01-19 |
| 2 | Complete | 2026-01-19 |
| 3 | Complete | 2026-01-19 |
| 4 | Complete | 2026-01-19 |
| 5 | In Progress | - |

Phase 5 implementing chat-first intake enhancement.
