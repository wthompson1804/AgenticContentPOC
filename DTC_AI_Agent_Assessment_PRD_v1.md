# DTC AI Agent Capabilities Assessment Tool — Product Requirements Document

**Version:** 1.1 (QC Revised)
**Date:** January 21, 2026
**Status:** Ready for Implementation

**Revision History:**
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-21 | Initial consolidated PRD |
| 1.1 | 2026-01-21 | QC pass: Added Parts 18-22 (Error Handling, API Config, Demo Mode, CPT Schema, Agent Type UI), chat message schema, enhanced acceptance criteria, fixed internal consistency issues |

---

## Executive Summary

Build a chat-first agent scoping wizard that:
- Feels like "talking it through"
- Behaves like a bounded methodology
- Produces a progressive 2-page artifact alongside chat (single source of truth)
- Runs the existing Step 0–3 pipeline (research → requirements → design → capability mapping)
- Outputs Private Reality Check + Public Narrative artifacts derived from the 2-pager
- Enforces a 10–15 minute active attention timebox
- Supports voice or text, plus document upload/linking

**Constraints:**
- No persistence, no collaboration in V1
- Minimal changes to existing step modules
- Repo remains Streamlit-based

---

## Part 1: System Architecture

### 1.1 Top-level Application

**`app.py` (Streamlit UI + orchestration spine)**
- Owns the 4-step wizard flow via `st.session_state`
- Renders each step screen, calls the step modules, stores outputs, and gates navigation
- Handles "demo mode" for Step 0 if no API key is present

### 1.2 Core Step Modules (Business Logic)

**Step 0 (Research):** `modules/research.py`
- Builds a research prompt from `prompts/step_0_research_brief.md`
- Calls Claude (Anthropic via LangChain wrapper)
- Parses the response into a `ResearchResult` object (best-effort regex extraction)

**Step 1 (Business Requirements):** `modules/requirements.py`
- Builds requirements prompt by injecting: form inputs, Step 0 research findings, DTC prompt template
- Calls Claude
- Parses sections via simple string/heading heuristics

**Step 2 (Agent Design):** `modules/agent_design.py`
- Builds agent design prompt from: form inputs, research summaries, requirements, agent type reference table (T0–T4)
- Calls Claude
- Extracts recommended type and sub-sections via regex
- **Requires a user confirmation step** (UI sets `confirmed_type`)

**Step 3 (Capability Mapping):** `modules/capability_mapping.py`
- Loads CPT YAML ontology: `data/ai_agent_cpt.yaml`
- Builds prompt with capability reference listing
- Calls Claude
- Parses capability IDs (`AA.BB` pattern), categorizes into essential/advanced/optional
- Generates an HTML visualization

### 1.3 Shared Utilities

**`modules/data_loader.py`**
- Loads config (`config.yaml`)
- Loads prompts for steps 0–3
- Loads CPT YAML and provides lookup helpers

**`modules/export.py`**
- Generates: Markdown report, Executive summary, HTML package, DOCX export (if python-docx installed)

### 1.4 Artifacts Produced

| Step | Output |
|------|--------|
| Step 0 | `research_results` dict (structured + raw "full_content") |
| Step 1 | `requirements_output` dict containing `full_text` + parsed "sections" |
| Step 2 | `agent_design_output` dict containing `recommended_type`, `confirmed_type`, summaries |
| Step 3 | `capability_mapping` dict containing mappings + HTML visualization |
| Exports | Markdown report, HTML package, optional DOCX |

---

## Part 2: Data Flow

| Step | Inputs | Transformations | Outputs | Downstream |
|------|--------|-----------------|---------|------------|
| **0 — Research** | `form_data` (industry, use_case, jurisdiction, org size, timeline) | Build prompt → Claude call → regex extract | `research_results` | Steps 1, 2 |
| **1 — Requirements** | `form_data` + `research_results` | Context blob + prompt → Claude call → section parsing | `requirements_output` | Steps 2, 3 |
| **2 — Agent Design** | `form_data` + `research_results` + `requirements_output` | Context + type criteria → Claude call → extract type/justification | `agent_design_output` + `confirmed_type` | Step 3 |
| **3 — Capability Mapping** | `form_data` + `requirements_output` + `agent_design_output` + CPT YAML | Prompt with CPT reference → Claude call → parse IDs → classify | `capability_mapping` | Exports |

---

## Part 3: Prompt Inventory

### 3.1 Prompt Files in `prompts/`

1. **`step_0_research_brief.md`**
   - Used by: `modules/research.py`
   - Variables: `{industry}`, `{use_case}`, `{jurisdiction}`, `{organization_size}`, `{timeline}`
   - **CRITICAL:** Verify this template can handle a multi-paragraph description in `{use_case}`. If it expects a single sentence, the context blob injection may confuse the LLM.

2. **`step_0_use_case_suitability.md`**
   - Status: **DEPRECATED** — Keep for reference but do not use. Consider removing in V2 cleanup.

3. **`step_1_business_requirements.md`**
   - Used by: `modules/requirements.py`
   - No placeholders; context injected around template

4. **`step_2_agent_design.md`**
   - Used by: `modules/agent_design.py`
   - No placeholders; context and references injected around it

5. **`step_3_capability_mapping.md`**
   - Used by: `modules/capability_mapping.py`
   - No placeholders; module injects context + full CPT reference list

### 3.2 Extraction/Parsing Reality

**Reliable parsing (high confidence):**
- Capability IDs in Step 3: regex `\b([A-Z]{2}\.[A-Z]{2})\b`
- Agent type extraction: T0–T4 tokens + fallback keyword inference
- Go/No-Go in Step 0: keyword match ("no-go", "caution", "go/recommended")

**Brittle parsing (best-effort):**
- Step 0 section extraction: complex regex, fails if model formats creatively
- Step 0 bullet extraction: multiple regex patterns, max 5 items
- Step 1 structured requirements: naive heading detection
- Step 2 justification/architecture extraction: can return empty

**Human-in-the-loop:**
- Agent type confirmation: UI expects user to confirm `recommended_type` → `confirmed_type`

---

## Part 4: Judgment Inventory

### 4.1 Core Judgments (CJ01–CJ10)

| ID | Name | Type | Source | Criticality | Policy |
|----|------|------|--------|-------------|--------|
| CJ01 | Industry | enum/string | user-provided | **blocker** | **ask** |
| CJ02 | Use case intent | string | user-provided | **blocker** | **ask** (refine) |
| CJ03 | Opportunity shape | enum | user/inferred | important | infer, surface |
| CJ04 | Jurisdiction | enum/string | user-provided | **blocker** | **ask**, confirm if unclear |
| CJ05 | Stakeholder reality | string | user/inferred | nice-to-have | infer if mentioned |
| CJ06 | Timeline | enum/string | user-provided | important | infer → confirm if ambiguous |
| CJ07 | Org scale | enum/string | user-provided | important | infer from description |
| CJ08 | Integration surface | string | user-provided | important (some domains) | infer, ask if central |
| CJ09 | Risk posture | enum | inferred | important (regulated) | infer → confirm if high-risk |
| CJ10 | Confirmed agent type | enum T0–T4 | user confirmation | **blocker** for Step 3 | **confirm** (explicit gate) |

### 4.2 Adaptive Branches

**Branch B1 — Use case refinement (CJ02)**  
Triggered if vague. Max 2 follow-ups:
- "What changes if this works perfectly?"
- "Who benefits most?"

**Branch B2 — Jurisdiction ambiguity (CJ04)**  
Triggered if unclear. Max 1 follow-up:
- "Where are users + where is data stored/processed?"

**Branch B3 — Integration unknown (CJ08)**  
Triggered if use case implies systems. Max 2 follow-ups:
- "What's the system-of-record today?"
- "Is there an API, or mostly manual?"

**Branch B4 — Risk posture (CJ09)**  
Triggered if regulated domain. Max 2 follow-ups:
- "Worst-case failure: what happens?"
- "Recommend only vs can execute?"

---

## Part 5: V1 Minimal Schema

### 5.1 Chat Message Schema

```json
{
  "chat_history": [
    {
      "id": "msg_001",
      "role": "system" | "user" | "assistant",
      "content": "string",
      "timestamp": "ISO8601",
      "state": "S0_ENTRY" | "S1_INTENT" | "...",  // State when message was sent
      "metadata": {
        "is_hard_question": false,
        "extracted_judgments": ["CJ01", "CJ02"],  // Which CJs this message informed
        "voice_transcribed": false,
        "attachments": []  // File references if any
      }
    }
  ]
}
```

### 5.2 Intake Packet Schema

```json
{
  "intake_packet": {
    "industry": {"value": "string", "confidence": "high|med|low", "source": "asked|inferred|user_edit"},
    "use_case_intent": {"value": "string", "confidence": "high|med|low", "source": "..."},
    "opportunity_shape": {"value": "revenue|cost|risk|transform", "confidence": "...", "source": "..."},
    "jurisdiction": {"value": "string", "confidence": "...", "source": "..."},
    "timeline": {"bucket": "0-3mo|3-6mo|6-12mo|12mo+|exploratory", "raw": "string|null", "..."},
    "organization_size": {"bucket": "1-50|51-200|201-1000|1001-5000|5000+|unknown", "raw": "...", "..."},
    "stakeholder_reality": {"value": "string|null", "..."},
    "integration_surface": {"systems": ["string"], "summary": "string|null", "..."},
    "risk_posture": {"level": "low|medium|high", "worst_case": "string|null", "..."},
    "boundaries": {"value": "string", "..."}
  },
  "assumptions": [
    {"id": "A1", "statement": "string", "confidence": "high|med|low", "impact": "high|med|low", "needs_confirmation": true, "status": "assumed|confirmed|corrected"}
  ],
  "step2_agent_type": {
    "recommended_type": "T0|T1|T2|T3|T4",
    "confirmed_type": "T0|T1|T2|T3|T4"
  }
}
```

---

## Part 6: Question Budget & Timebox

### 6.1 Budget Targets
- Default session: 8–12 turns total (a "turn" = one user message + one system response)
- Hard cap: 18 turns
- Hard questions: max 4 (anything requiring thoughtful recall)

**Note:** States (S0–S9) do not map 1:1 to turns. Some states (S3_CONTEXT) capture multiple judgments in one turn. States S6–S9 are mechanistic pipeline execution, not conversation turns.

### 6.2 Skip Rules
- If user is flowing, do not interrupt with granular follow-ups
- Prefer: summarize → ask "right?" instead of interrogating
- "Good enough" when: Industry, use case, jurisdiction set; timeline + scale roughly set

### 6.3 Fast Path
At any point, user can say "Just run it." System proceeds using assumptions and flags them.

**CRITICAL UI NOTE:** The "Just run it" / fast-path trigger button must be pinned to the sidebar or bottom input area, NOT in the scrolling chat stream where users will miss it.

### 6.4 Hard Stop Behavior
When `timebox.turns >= 18`:
1. System displays: "We've been chatting a while. I have enough to work with — ready to proceed?"
2. Options presented:
   - **"Yes, run the analysis"** → Proceed to S5 (Assumptions Check) then S6+
   - **"Let me add one more thing"** → Allow 2 additional turns max, then force proceed
   - **"Start over"** → Reset session (with confirmation)
3. If user continues chatting without selecting an option, system auto-proceeds after 1 additional turn with assumption flags maximized

---

## Part 7: Conversation State Machine

### 7.1 States

| State | Description |
|-------|-------------|
| S0_ENTRY | Confidence framing |
| S1_INTENT | Intent capture (microstep 2 first) |
| S2_OPPORTUNITY | Opportunity shape |
| S3_CONTEXT | Context anchors (bundled) |
| S4_INTEGRATION_RISK | Conditional: integration + risk |
| S5_ASSUMPTIONS_CHECK | Assumptions checkpoint (critical) |
| S6_RUN_STEP0 | Execute Step 0 Research |
| S7_CONFIRM_TYPE | Agent type confirmation gate |
| S8_RUN_STEP1_3 | Execute Steps 1–3 (mechanistic) |
| S9_EXPORTS | Output & Export |

### 7.2 Transitions
- Linear by default
- Branching only at S4 if decision-critical
- Hard stop at S5 unless user explicitly says "just run it"

### 7.3 Stop Conditions
- All Core Judgments CJ01–CJ09 satisfied
- Agent type confirmed (CJ10)
- Timebox reached → system offers fast-path

---

## Part 8: UX Copy (System Prompts)

### S0_ENTRY
"Let's talk this through. You don't need to be precise — I'll make reasonable assumptions and show them to you before anything runs."

### S1_INTENT
"Start with the thing you want. In one or two sentences: what problem are you hoping an AI agent could help with?"

Follow-up (only if vague):
"If this worked perfectly, what would change?"

### S2_OPPORTUNITY
"Which is closest to your goal right now: make more money, save time/cost, reduce risk, or change how the business works?"

### S3_CONTEXT (bundled)
"Quick context so I don't give you something generic: what industry are you in, roughly how big is the organization, and where does this operate (US/EU/global/etc.)?"

### S4_INTEGRATION (conditional)
"Does this touch any existing systems, or would it mostly work on its own?"

### S4_RISK (conditional)
"If this went wrong, what's the worst-case outcome?"

### S5_ASSUMPTIONS_CHECK
"Here's what I think you're saying. Correct anything that's off — this is what I'll base the research on."

Buttons:
- "Looks right — proceed"
- "Fix one thing"
- "Ask me the most important question"
- "Just run it"

---

## Part 9: Progressive 2-Pager Artifact

### 9.1 Template Structure

**Section 1 — What You're Trying to Do**
Populated from: S1–S2. Locked after S5 unless user edits.

**Section 2 — Opportunity Shape**
Populated from: CJ03. Explicit if selected, otherwise inferred + flagged.

**Section 3 — Operating Context**
Populated from: S3–S4. Inferred fields get assumption flags.

**Section 4 — What the Agent Would Actually Do**
Populated from: S1–S4, refined by Step 2. **Boundary statement required.**

**Section 5 — Initial Feasibility & Direction**
Populated from: Step 0 output. System-generated, user cannot edit.

**Section 6 — Key Risks & Success Factors**
Populated from: Step 0. If empty → "None identified yet" + low confidence.

**Section 7 — Assumptions & Uncertainties**
Populated from: Inference layer + Step 0. Editable inline. Max 8 displayed, sorted by impact × uncertainty.

**Section 8 — What Happens Next**
Populated from: System logic at end of flow.

### 9.2 Update Triggers

| Event | Sections Updated |
|-------|------------------|
| S1 Intent | 1, 4 (draft) |
| S2 Opportunity | 2 |
| S3 Context | 3 |
| S4 Integration/Risk | 3, 7 |
| S5 Assumptions Check | 7 (full) |
| Step 0 complete | 5, 6 |
| Step 2 complete | 4, 5 |
| End of flow | 8 |

---

## Part 10: Output Suite

### 10.1 Private Reality Check (Internal Champion)

**Audience:** Director+ IT, product, ops, strategy — the person who gets blamed if wrong

**Content:** Full 2-pager unfiltered including all assumptions, confidence levels, explicit non-goals, risks + CSFs, directional judgment

**Tone:** Calm, direct, non-salesy

**Format:** Markdown (primary), DOCX (export), HTML (light)

### 10.2 Public Narrative (Stakeholders)

**Audience:** Execs, Finance, Legal, Adjacent teams

**Critical rule:** May omit uncertainty, but never contradict internal assessment.

**Outputs:**
1. **One-Page Exec Brief** — Sections 1, 2, 4, 8 + sanitized Section 5. Excludes assumptions.
2. **Internal Email Draft** — Neutral framing, coordination-focused
3. **Slide Outline** — Title + takeaway + 3 bullets per slide (NOT a full PPTX)

### 10.3 Directional Consistency Check

Before generating public outputs, system runs: "Does this public framing contradict the internal assessment?"

If yes, insert warning: "This framing may overstate confidence relative to the internal assessment."

---

## Part 11: Voice + Upload Requirements

### 11.1 Voice Input

**CRITICAL FIX:** Streamlit does NOT support browser-based speech-to-text natively. The server-side Python architecture prevents client-side Web Speech API access.

**V1 Implementation:**
- Use `streamlit-audiorecorder` component to capture WAV bytes from browser microphone
- Send captured audio to OpenAI Whisper API for transcription
- Insert transcript into chat input as text

**Fallback:** User can paste manual transcript or upload audio file.

**Hard requirement:** Chat pipeline treats voice transcript exactly like text message.

### 11.2 Document Upload + Link Paste

- `st.file_uploader` supports: pdf, docx, txt, md
- V1: Do NOT parse files deeply
- Store: file name + short user note ("What is this document?")
- Include metadata in `use_case_context_blob`

---

## Part 12: Implementation Plan

### 12.1 Files to ADD (new modules)

| File | Responsibility |
|------|----------------|
| `modules/chat_intake.py` | State machine S0–S5, message templates, extraction, timebox |
| `modules/artifact_panel.py` | Progressive 2-pager schema, update rules, rendering |
| `modules/judgment_engine.py` | CJ01–CJ09 extraction, normalization, assumption generation |
| `modules/timebox.py` | Turn counting, hard question tracking, fast-path |

### 12.2 Files to MODIFY

**`app.py`**
- Add session state keys: `chat_history`, `intake_packet`, `artifact_doc`, `assumptions`, `timebox`, `uploaded_files`, `links`, `current_state`
- Add 2-column layout: left (chat), right (artifact panel)
- Add Step -1 "Chat Intake" before Step 0
- Wire chat intake → Step 0 binding
- **CRITICAL:** Disable "Proceed to Step 3" button until `st.session_state.confirmed_type` is not None

**`modules/research.py`**
- Accept `use_case_override` parameter for context blob injection
- Verify `step_0_research_brief.md` template handles multi-paragraph input

**`modules/requirements.py`, `modules/agent_design.py`, `modules/capability_mapping.py`**
- **MANDATORY (not optional):** Modify prompt assembly to include:
  - `artifact_doc.section_4_agent_behavior` (Boundaries)
  - `artifact_doc.section_7_assumptions` (top 3 high-impact)
- This prevents Steps 1-3 from hallucinating features explicitly ruled out in Boundaries

**`modules/export.py`**
- Add: `render_internal_brief_md()`, `render_exec_brief_md()`, `render_email_md()`, `render_slide_outline_md()`

### 12.3 Session State Keys

```python
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_state" not in st.session_state:
    st.session_state.current_state = "S0_ENTRY"
if "intake_packet" not in st.session_state:
    st.session_state.intake_packet = {}
if "assumptions" not in st.session_state:
    st.session_state.assumptions = []
if "artifact_doc" not in st.session_state:
    st.session_state.artifact_doc = init_artifact()
if "timebox" not in st.session_state:
    st.session_state.timebox = init_timebox()
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []
if "links" not in st.session_state:
    st.session_state.links = []
if "confirmed_type" not in st.session_state:
    st.session_state.confirmed_type = None  # CRITICAL: Gate for Step 3
```

---

## Part 13: Step 0 Prompt Binding

### 13.1 Variable Mapping

| Placeholder | Source |
|-------------|--------|
| `{industry}` | `intake_packet.industry.value` |
| `{use_case}` | `use_case_context_blob` (see below) |
| `{jurisdiction}` | `intake_packet.jurisdiction.value` |
| `{organization_size}` | `intake_packet.organization_size.bucket` |
| `{timeline}` | `intake_packet.timeline.bucket` |

### 13.2 Context Blob Structure

Since the prompt only has `{use_case}`, pack richer context inside it:

```
**Objective:** [Section 1]

**Opportunity Type:** [Section 2]

**Agent Behavior (draft):** [Section 4]
- Primary action
- Secondary action
- Boundary: [explicit non-goal]

**Integration Surface:** [if any]

**Key Assumptions:**
- [A1]: [statement] (confidence: X, impact: Y)
- [A2]: ...
- [A3]: ...
```

**CRITICAL:** Verify `step_0_research_brief.md` doesn't have instruction text like "You are analyzing a use case described in the following sentence: {use_case}" — if so, adjust prompt or use a delimiter.

---

## Part 14: Assumption Fix Loop (Dependency Ripple)

### 14.1 Problem
When user changes a Core Judgment at the checkpoint, dependent inferences become stale.

Example: User changes Industry from "Retail" to "Healthcare" → Risk Posture (inferred from Industry) is now wrong.

### 14.2 Solution
The `update_judgments` function needs a dependency ripple flag:

```python
def update_judgments(intake_packet, assumptions, changed_field):
    """
    If a Core Judgment (CJ01-CJ04) is modified:
    - Re-evaluate all non-confirmed Inferred Judgments
    - Mark affected assumptions as 'needs_revalidation'
    - Invalidate downstream drafts
    - Re-run Step 0 if already executed
    """
    CORE_JUDGMENTS = ["industry", "use_case_intent", "jurisdiction", "opportunity_shape"]
    
    if changed_field in CORE_JUDGMENTS:
        # Re-infer dependent fields
        if changed_field == "industry":
            intake_packet["risk_posture"] = infer_risk_posture(intake_packet)
            # Mark related assumptions for review
            for a in assumptions:
                if "industry" in a["statement"].lower() or "risk" in a["statement"].lower():
                    a["status"] = "needs_revalidation"
```

---

## Part 15: Acceptance Criteria

### 15.1 UX/Flow
- [ ] User can complete intake in <15 minutes typical case
- [ ] Artifact panel updates after each user turn
- [ ] Assumptions checkpoint always appears before Step 0 unless bypassed
- [ ] User can correct assumptions; corrections update artifact + judgments
- [ ] Fast-path button is pinned (not in scrolling chat)

### 15.2 Pipeline Correctness
- [ ] Step 0 uses new intake values (no old form required)
- [ ] Steps 1-3 receive Boundaries and Assumptions in prompt context
- [ ] Step 2 requires confirmation; Step 3 button disabled until `confirmed_type` set
- [ ] Outputs generate successfully even when parsers fail (graceful degradation)

### 15.3 Output Suite
- [ ] Internal brief includes assumptions + confidence
- [ ] Exec brief omits assumptions but does not contradict internal direction
- [ ] Email + slide outline generated from artifact doc

### 15.4 Voice Input
- [ ] `streamlit-audiorecorder` captures audio
- [ ] Whisper API transcribes to text
- [ ] Transcript flows into chat as normal message
- [ ] Graceful fallback when `OPENAI_API_KEY` missing (voice UI hidden or disabled)

### 15.5 Performance & Reliability
- [ ] Claude API calls complete within 60s (timeout with retry)
- [ ] Whisper transcription completes within 30s
- [ ] Full intake flow (S0–S5) completes in <15 min for typical user
- [ ] Parser failures do not block pipeline progression
- [ ] Session auto-saves to localStorage every 60s

### 15.6 Error Handling
- [ ] API failures show user-friendly error messages (not stack traces)
- [ ] Retry buttons appear after transient failures
- [ ] Network disconnection detected and communicated to user

### 15.7 Browser Compatibility
- [ ] Chrome 90+ (primary target)
- [ ] Firefox 90+ (secondary)
- [ ] Safari 15+ (best effort)
- [ ] Mobile browsers: Not supported in V1 (display warning)

---

## Part 16: Test Scenarios

1. **Dreamer, vague, non-technical** — System infers, surfaces assumptions, proceeds
2. **Technical champion, detailed** — System captures richness, minimal follow-ups
3. **Regulated domain (finance/healthcare)** — Triggers risk branch, appropriate cautions
4. **Integration-heavy use case** — Triggers integration branch
5. **Missing jurisdiction** — Assumption + confirm before Step 0
6. **User edits assumption at checkpoint** — Dependency ripple, re-run Step 0 if needed
7. **Parser failure** — System still exports; marks low confidence

---

## Part 17: Implementation Order

1. Add artifact panel + `artifact_doc` structure + renderer
2. Add chat UI + transcript storage
3. Implement minimal `chat_intake.step()` with S0–S5 copy
4. Implement `judgment_engine` heuristics + assumptions
5. Bind intake into Step 0 placeholder values
6. Add checkpoint controls + user edits + dependency ripple
7. **Add context injection to Steps 1-3 prompts (MANDATORY)**
8. Add export suite from artifact doc
9. Add type confirmation wiring after Step 2 + disable Step 3 until confirmed
10. Add voice (`streamlit-audiorecorder` + Whisper) + upload plumbing

---

## Appendix A: Failure Modes

### A.1 Core Intake Blockers
- **Missing/garbled Industry:** Everything becomes generic
- **Weak Use Case:** Capability mapping selects plausible but wrong capabilities
- **Wrong Jurisdiction:** Regulatory findings wrong → survivor cover blown

### A.2 Agent Type Failures
- **Recommended type wrong:** Architecture and capability mapping misaligned
- **No confirmed type:** Step 3 uses wrong default; user loses trust

### A.3 Context Propagation Failure (CRITICAL)
- **Steps 1-3 only see short `use_case_intent`:** Model hallucinate features explicitly ruled out in Boundaries
- **Fix:** MANDATORY context injection of Boundaries + Assumptions

### A.4 Parsing Fragility
- **Step 0 headings drift:** `extract_section` fails → missing context
- **Architecture summary empty:** Step 3 gets weak context → broad guessing

---

## Appendix B: Module API Signatures

### chat_intake.py
```python
def chat_intake_step(
    chat_history: list,
    intake_packet: dict,
    artifact_doc: dict,
    assumptions: list,
    timebox: dict,
    uploaded_files: list,
    links: list,
    user_action: dict | None = None
) -> dict:
    """
    Returns:
    {
        "new_state": str,
        "system_messages": list[str],
        "intake_packet": dict,
        "assumptions": list,
        "artifact_doc": dict,
        "open_questions": list
    }
    """
```

### judgment_engine.py
```python
def update_judgments(
    chat_history: list,
    intake_packet: dict,
    uploaded_files: list,
    links: list,
    changed_field: str | None = None  # For dependency ripple
) -> dict:
    """Returns updated intake_packet + assumptions + open_questions"""

def build_use_case_context_blob(
    intake_packet: dict,
    artifact_doc: dict,
    assumptions: list
) -> str:
    """Produces single text blob to inject into {use_case} placeholder"""
```

### artifact_panel.py
```python
def init_artifact() -> dict
def apply_artifact_updates(artifact_doc: dict, intake_packet: dict, assumptions: list, step_outputs: dict) -> dict
def render_artifact_md(artifact_doc: dict) -> str
```

### timebox.py
```python
def init_timebox() -> dict
def register_turn(timebox: dict, system_question: bool, hard: bool) -> dict
def should_offer_fast_path(timebox: dict) -> bool
def reached_hard_stop(timebox: dict) -> bool
```

---

## Appendix C: V1 vs V2 Scope

### V1 (Ship This)
- ✅ Chat intake flow S0–S5
- ✅ One persistent artifact panel
- ✅ Progressive fill + inline corrections
- ✅ Assumptions table (max 8 displayed)
- ✅ Step 2 confirmation gate
- ✅ Step 3 button disabled until confirmed
- ✅ Export suite (4 outputs)
- ✅ Voice via `streamlit-audiorecorder` + Whisper
- ✅ Document upload with metadata

### V2 (Explicitly Defer)
- ❌ Persistence/session restore
- ❌ Collaboration
- ❌ Multiple artifacts
- ❌ Full revision history
- ❌ Rich visual diffing
- ❌ Auto-designed decks (PPTX generation)
- ❌ Role-based rewriting
- ❌ Tone sliders
- ❌ Approval workflows

---

## Part 18: Error Handling & Resilience

### 18.1 API Failure Handling

| Scenario | Detection | User Experience | Recovery |
|----------|-----------|-----------------|----------|
| **Claude API timeout** | No response within 60s | Show spinner with "Taking longer than usual..." at 30s | Offer "Retry" button; after 2 failures, suggest trying later |
| **Claude API rate limit** | 429 response | "High demand - waiting for availability" | Exponential backoff: 5s → 15s → 45s; max 3 retries |
| **Claude API error (5xx)** | 500-599 response | "Service temporarily unavailable" | Auto-retry once after 5s; then show manual retry |
| **Whisper API timeout** | No response within 30s | "Voice transcription delayed" | Offer "Type instead" fallback; keep audio for retry |
| **Whisper API error** | Non-200 response | "Couldn't process audio" | Show "Type your message" input; discard audio |
| **Network disconnection** | Fetch failure | "Connection lost - checking..." | Auto-retry 3x at 2s intervals; then show reconnect button |

### 18.2 Graceful Degradation

**Parser Failures:**
- If regex extraction fails, store raw LLM output in `_raw` field
- Mark affected section with `"parse_status": "raw"`
- Display to user with yellow warning: "This section needs manual review"
- Allow proceeding to next step; do not block pipeline

**Missing Required Fields:**
- Block state transition (e.g., S5 → S6) if blocker fields (CJ01, CJ02, CJ04) are empty
- Highlight missing field in artifact panel with red border
- System message: "I need [field] before we can proceed. [Contextual question]"

**Partial Step Completion:**
- If Step 0 completes but Step 1 fails, preserve Step 0 outputs
- User can retry Step 1 without re-running Step 0
- Store `step_X_status: "complete" | "failed" | "pending"` in session state

### 18.3 Session Recovery (V1 Limitations)

**V1:** No persistence. If browser tab closes:
- All progress lost
- User must restart
- Display warning on page load: "This session won't be saved. Export your results before closing."

**Mitigation:** Auto-export artifact to browser localStorage every 60s (JSON only, not full outputs)

---

## Part 19: API Configuration & Provider Management

### 19.1 Required API Keys

| Provider | Purpose | Environment Variable | Required |
|----------|---------|---------------------|----------|
| Anthropic | Claude LLM (Steps 0-3, chat) | `ANTHROPIC_API_KEY` | Yes |
| OpenAI | Whisper transcription | `OPENAI_API_KEY` | No (voice disabled if missing) |

### 19.2 Configuration Schema (`config.yaml`)

```yaml
llm:
  provider: "anthropic"
  model: "claude-3-5-sonnet-20241022"  # Or claude-3-opus for higher quality
  max_tokens: 4096
  temperature: 0.3  # Lower for more deterministic outputs
  timeout_seconds: 60

voice:
  enabled: true  # Set false to hide voice UI entirely
  provider: "openai"
  model: "whisper-1"
  max_audio_seconds: 120
  timeout_seconds: 30

timebox:
  default_turns: 10
  hard_cap_turns: 18
  hard_questions_max: 4

ui:
  artifact_panel_width: 0.4  # Fraction of screen width
  chat_panel_width: 0.6
  auto_save_interval_seconds: 60
```

### 19.3 API Key Validation on Startup

```python
def validate_api_keys():
    """Run on app startup. Returns dict of availability."""
    status = {
        "anthropic": False,
        "openai": False,
        "demo_mode": False
    }

    if os.getenv("ANTHROPIC_API_KEY"):
        # Validate with minimal API call
        status["anthropic"] = test_anthropic_connection()
    else:
        status["demo_mode"] = True

    if os.getenv("OPENAI_API_KEY"):
        status["openai"] = test_openai_connection()

    return status
```

---

## Part 20: Demo Mode Specification

### 20.1 Trigger Conditions
- `ANTHROPIC_API_KEY` environment variable is missing or invalid
- User explicitly selects "Try Demo" from landing page

### 20.2 Demo Mode Behavior

| Component | Live Mode | Demo Mode |
|-----------|-----------|-----------|
| Chat intake | Real Claude responses | Pre-scripted responses from `data/demo_responses.json` |
| Step 0 Research | Claude API call | Load from `data/demo_step0_output.json` |
| Steps 1-3 | Claude API calls | Load from `data/demo_step[1-3]_output.json` |
| Voice input | Whisper transcription | Disabled; show "Voice requires API key" |
| Artifact panel | Live updates | Simulated updates with 1s delays |
| Exports | Generated from live data | Generated from demo data |

### 20.3 Demo Data Files Required

```
data/
├── demo_responses.json      # Chat responses keyed by state (S0-S5)
├── demo_step0_output.json   # Pre-computed Step 0 research results
├── demo_step1_output.json   # Pre-computed requirements
├── demo_step2_output.json   # Pre-computed agent design
├── demo_step3_output.json   # Pre-computed capability mapping
└── demo_intake_packet.json  # Sample intake for demo flow
```

### 20.4 Demo UI Indicators
- Yellow banner at top: "🎭 Demo Mode - Using sample data. Add API key for live analysis."
- "Exit Demo" button in sidebar
- All exports watermarked: "[DEMO] This is sample output"

---

## Part 21: CPT YAML Ontology Schema

### 21.1 File Location
`data/ai_agent_cpt.yaml`

### 21.2 Schema Definition

```yaml
# AI Agent Capability Performance Taxonomy (CPT)
version: "1.0"
last_updated: "2026-01-15"

categories:
  - id: "CO"  # Example: Cognitive Operations
    name: "Cognitive Operations"
    description: "Core reasoning and decision-making capabilities"
    capabilities:
      - id: "CO.RA"
        name: "Reasoning & Analysis"
        description: "Ability to analyze information and draw conclusions"
        complexity: "T1+"  # Minimum agent type required
        indicators:
          - "Can identify patterns in unstructured data"
          - "Can explain reasoning chain"
        dependencies: []  # Other capability IDs this depends on

      - id: "CO.PL"
        name: "Planning"
        description: "Multi-step task decomposition and sequencing"
        complexity: "T2+"
        indicators:
          - "Can create actionable plans"
          - "Can adjust plans based on feedback"
        dependencies: ["CO.RA"]

  - id: "DA"  # Data & Analytics
    name: "Data & Analytics"
    # ... more capabilities

  - id: "IN"  # Integration
    name: "Integration & Connectivity"
    # ... more capabilities

  - id: "AU"  # Autonomy
    name: "Autonomous Operations"
    # ... more capabilities

# Agent type definitions for reference
agent_types:
  T0:
    name: "Assistive"
    description: "Human-in-the-loop for all decisions"
    max_autonomy: "Suggest only"
  T1:
    name: "Supervised"
    description: "Can execute with approval"
    max_autonomy: "Execute with confirmation"
  T2:
    name: "Semi-autonomous"
    description: "Can execute routine tasks independently"
    max_autonomy: "Execute routine, escalate exceptions"
  T3:
    name: "Autonomous"
    description: "Can handle exceptions within policy"
    max_autonomy: "Execute within guardrails"
  T4:
    name: "Fully autonomous"
    description: "Self-directed within domain"
    max_autonomy: "Self-directed operations"
```

### 21.3 Capability ID Format
- Pattern: `[A-Z]{2}\.[A-Z]{2}` (e.g., `CO.RA`, `DA.VZ`, `IN.AP`)
- First two letters: Category code
- Last two letters: Capability code within category

---

## Part 22: Agent Type Confirmation UI Specification

### 22.1 Trigger
- Displayed immediately after Step 2 (Agent Design) completes
- Blocks progression to Step 3 until user confirms

### 22.2 UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 Recommended Agent Type: T2 (Semi-autonomous)           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Based on your requirements, I recommend a T2 agent that:   │
│  • Can execute routine tasks independently                  │
│  • Escalates exceptions to humans                           │
│  • Requires defined guardrails and policies                 │
│                                                             │
│  [Justification summary from Step 2 output]                 │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Is this the right level of autonomy?                       │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ ✓ Yes, proceed  │  │ ↓ Show me other │                  │
│  │   with T2       │  │   options       │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 22.3 "Show Other Options" Expanded View

```
┌─────────────────────────────────────────────────────────────┐
│  Select Agent Type:                                         │
│                                                             │
│  ○ T0 - Assistive (human decides everything)               │
│  ○ T1 - Supervised (executes with approval)                │
│  ● T2 - Semi-autonomous (recommended)                       │
│  ○ T3 - Autonomous (handles exceptions)                     │
│  ○ T4 - Fully autonomous (self-directed)                   │
│                                                             │
│  ⚠️ Selecting a higher autonomy level than recommended     │
│     may require additional safeguards not covered here.     │
│                                                             │
│  ┌─────────────────┐                                        │
│  │ Confirm: T2     │                                        │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

### 22.4 Session State Updates

```python
# On "Yes, proceed with T2" click:
st.session_state.confirmed_type = st.session_state.agent_design_output["recommended_type"]

# On alternative selection:
st.session_state.confirmed_type = selected_type  # User's choice

# Step 3 button enable condition:
st.button("Proceed to Capability Mapping", disabled=(st.session_state.confirmed_type is None))
```

*End of Document*
