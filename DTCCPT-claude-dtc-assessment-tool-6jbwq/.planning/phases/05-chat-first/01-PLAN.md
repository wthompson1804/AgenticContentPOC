# Phase 5: Chat-First Intake Enhancement

**Goal:** Transform the form-based wizard into a conversational chat-first experience with progressive 2-pager artifact generation

**PRD Reference:** `/Users/williamthompson/Downloads/Agentic Content POC/DTC_AI_Agent_Assessment_PRD_v1.md` (v1.1)

**Mode:** YOLO (build fast, iterate)

---

## Success Criteria

1. User can complete intake via natural conversation (S0-S5 states)
2. Progressive 2-pager artifact updates in real-time alongside chat
3. Judgment engine extracts CJ01-CJ10 from conversation
4. Timebox enforces 8-12 turns default, 18 turn hard cap
5. Assumptions checkpoint (S5) surfaces inferences for user confirmation
6. Agent type confirmation gate blocks Step 3 until confirmed
7. All existing Step 0-3 modules work with new intake system
8. Voice input via Whisper (optional, graceful degradation)

---

## Deliverables

### New Modules (4 files)
| File | Purpose | Lines Est. |
|------|---------|------------|
| `modules/chat_intake.py` | State machine S0-S5, message handling | ~400 |
| `modules/artifact_panel.py` | 2-pager schema, rendering, updates | ~200 |
| `modules/judgment_engine.py` | CJ extraction, inference, assumptions | ~250 |
| `modules/timebox.py` | Turn counting, hard questions, fast-path | ~80 |

### Modified Files (4 files)
| File | Changes |
|------|---------|
| `app.py` | Two-column layout, chat UI, new session keys, state routing |
| `config.yaml` | Add voice, timebox, ui sections per PRD Part 19 |
| `modules/export.py` | Add `render_email_md()`, `render_slide_outline_md()` |
| `modules/requirements.py`, `agent_design.py`, `capability_mapping.py` | Inject boundaries + assumptions into prompts |

### New Data Files (6 files for demo mode)
| File | Purpose |
|------|---------|
| `data/demo_responses.json` | Chat responses by state |
| `data/demo_intake_packet.json` | Sample intake for demo |

---

## Implementation Order

### Step 1: Foundation (timebox + config)
- [ ] Update `config.yaml` with new sections
- [ ] Create `modules/timebox.py`
- [ ] Add new session state keys to `app.py`

### Step 2: Judgment Engine
- [ ] Create `modules/judgment_engine.py`
- [ ] Implement CJ01-CJ10 extraction
- [ ] Implement inference rules
- [ ] Implement assumption generation

### Step 3: Chat Intake State Machine
- [ ] Create `modules/chat_intake.py`
- [ ] Implement S0-S5 states
- [ ] Implement branching logic (B1-B4)
- [ ] Wire to judgment engine

### Step 4: Artifact Panel
- [ ] Create `modules/artifact_panel.py`
- [ ] Implement 8-section schema
- [ ] Implement update triggers
- [ ] Implement rendering

### Step 5: App Integration
- [ ] Modify `app.py` for two-column layout
- [ ] Add chat UI component
- [ ] Wire chat intake to Step 0
- [ ] Add agent type confirmation gate
- [ ] Disable Step 3 until confirmed

### Step 6: Context Injection (CRITICAL)
- [ ] Modify `requirements.py` to include boundaries + assumptions
- [ ] Modify `agent_design.py` to include boundaries + assumptions
- [ ] Modify `capability_mapping.py` to include boundaries + assumptions

### Step 7: Export Extensions
- [ ] Add `render_internal_brief_md()` to export.py
- [ ] Add `render_exec_brief_md()` to export.py
- [ ] Add `render_email_md()` to export.py
- [ ] Add `render_slide_outline_md()` to export.py

### Step 8: Voice Input (Optional)
- [ ] Add `streamlit-audiorecorder` dependency
- [ ] Implement Whisper integration
- [ ] Add fallback for missing OPENAI_API_KEY

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Keep existing step modules unchanged | PRD mandate: "minimal changes to existing step modules" |
| Chat intake as new "Step -1" | Slot before existing Step 0, maintains backward compat |
| Two-column layout | Chat left (60%), artifact right (40%) per PRD Part 19 |
| State machine in Python | Simpler than external orchestrator for V1 |
| Assumptions as first-class objects | Enables dependency ripple per PRD Part 14 |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| State machine complexity | Keep states linear, branch only at S4 |
| Regex parsing fragility | Store raw output, allow graceful degradation |
| 15-min timebox ambitious | Hard stop at 18 turns, fast-path always available |
| Two-column Streamlit layout | Test early, may need custom CSS |

---

## Definition of Done

- [ ] All acceptance criteria from PRD Part 15 pass
- [ ] Test scenarios 1-7 from PRD Part 16 work
- [ ] Demo mode works without API keys
- [ ] Existing form-based flow still accessible (fallback)
