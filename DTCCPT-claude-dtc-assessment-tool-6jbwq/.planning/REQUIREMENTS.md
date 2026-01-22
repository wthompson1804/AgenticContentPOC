# Requirements

## v1 Requirements

### Research Integration (RES)

- [ ] **RES-01**: System conducts deep research using Open Deep Research framework
- [ ] **RES-02**: Research produces cited sources with URLs for all claims
- [ ] **RES-03**: Research covers 5 areas: industry adoption, regulatory, technical, risk, economic
- [ ] **RES-04**: Research results display with expandable sections and source links
- [ ] **RES-05**: Preliminary agent type (T0-T4) recommendation based on research

### DTC Workflow (DTC)

- [ ] **DTC-01**: Load DTC prompt templates from repository unchanged
- [ ] **DTC-02**: Execute Step 0 (enhanced research brief) with user inputs
- [ ] **DTC-03**: Execute Step 1 (business requirements generator)
- [ ] **DTC-04**: Execute Step 2 (agent type assessment and design)
- [ ] **DTC-05**: Execute Step 3 (capability mapping and HTML visualization)
- [ ] **DTC-06**: Chain outputs between steps (each step receives prior outputs)
- [ ] **DTC-07**: Load ai_agent_cpt.yaml for capability definitions

### User Interface (UI)

- [ ] **UI-01**: 4-step wizard with clear step indicators
- [ ] **UI-02**: Progressive disclosure (hide future steps until current complete)
- [ ] **UI-03**: Industry/use case/jurisdiction input form
- [ ] **UI-04**: Research results display with citations
- [ ] **UI-05**: Human-in-the-loop confirmation at each step transition
- [ ] **UI-06**: Agent type confirmation dialog after Step 2
- [ ] **UI-07**: Interactive periodic table visualization for CPT
- [ ] **UI-08**: Responsive design for various screen sizes

### Export (EXP)

- [ ] **EXP-01**: Export research report (Markdown/PDF)
- [ ] **EXP-02**: Export business requirements document
- [ ] **EXP-03**: Export agent design document
- [ ] **EXP-04**: Export interactive HTML CPT visualization
- [ ] **EXP-05**: Export complete planning package (all artifacts)

### Infrastructure (INF)

- [ ] **INF-01**: Streamlit application with session state management
- [ ] **INF-02**: Environment variable configuration for API keys
- [ ] **INF-03**: Error handling with user-friendly messages
- [ ] **INF-04**: Progress indicators during LLM operations
- [ ] **INF-05**: Configuration file for model selection

## v2 Requirements (Deferred)

- Save/resume sessions to database
- Multi-user collaboration features
- Custom industry templates
- Comparison of multiple assessments
- Integration with project management tools

## Out of Scope

- Mobile native application — web responsive sufficient
- Prompt modification UI — methodology fidelity required
- Real-time collaboration — single-user workflow
- Offline mode — requires API access

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| RES-01 | 2 | Pending |
| RES-02 | 2 | Pending |
| RES-03 | 2 | Pending |
| RES-04 | 3 | Pending |
| RES-05 | 2 | Pending |
| DTC-01 | 1 | Pending |
| DTC-02 | 2 | Pending |
| DTC-03 | 3 | Pending |
| DTC-04 | 3 | Pending |
| DTC-05 | 3 | Pending |
| DTC-06 | 3 | Pending |
| DTC-07 | 1 | Pending |
| UI-01 | 1 | Pending |
| UI-02 | 1 | Pending |
| UI-03 | 1 | Pending |
| UI-04 | 3 | Pending |
| UI-05 | 3 | Pending |
| UI-06 | 3 | Pending |
| UI-07 | 4 | Pending |
| UI-08 | 4 | Pending |
| EXP-01 | 4 | Pending |
| EXP-02 | 4 | Pending |
| EXP-03 | 4 | Pending |
| EXP-04 | 4 | Pending |
| EXP-05 | 4 | Pending |
| INF-01 | 1 | Pending |
| INF-02 | 1 | Pending |
| INF-03 | 4 | Pending |
| INF-04 | 3 | Pending |
| INF-05 | 1 | Pending |
