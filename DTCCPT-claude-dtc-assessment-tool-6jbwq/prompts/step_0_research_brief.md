# Enhanced Step 0: DTC-Specific Research Brief

This template is used with Open Deep Research to conduct comprehensive research
before the DTC assessment workflow.

---

## Research Request Template

Conduct comprehensive research for an AI agent implementation assessment.

### CONTEXT
- **Industry:** {industry}
- **Use Case:** {use_case}
- **Primary Jurisdiction:** {jurisdiction}
- **Organization Size:** {organization_size}
- **Timeline:** {timeline}

### RESEARCH AREAS

Investigate each area thoroughly with current, cited sources:

#### 1. INDUSTRY AI ADOPTION
- Current AI/automation deployment rates in {industry}
- Success and failure case studies from the past 2-3 years
- Vendor landscape and technology maturity levels
- Cost benchmarks from analyst reports (Gartner, Forrester, McKinsey)
- Digital twin adoption specifically in this sector

#### 2. REGULATORY ENVIRONMENT
- {jurisdiction} regulations for autonomous systems in {industry}
- Relevant ISO/IEC standards (e.g., ISO 23247 for digital twins)
- Recent enforcement actions or regulatory changes
- Certification requirements for AI systems
- Data privacy and protection requirements (GDPR, CCPA, etc.)

#### 3. TECHNICAL INTEGRATION
- Common technology stacks in {industry} (SCADA, OT/IT convergence)
- Integration patterns and architectural challenges
- Cybersecurity considerations for AI-connected systems
- Data quality and governance issues
- Interoperability standards and protocols

#### 4. RISK & FAILURE MODES
- Documented AI system failures in {industry}
- Root cause patterns and lessons learned
- Insurance and liability considerations
- Change management challenges
- Human factors and workforce adaptation

#### 5. ECONOMIC VIABILITY
- ROI data for AI implementations in {industry}
- Implementation cost structures and hidden costs
- Timeline benchmarks for similar projects
- Total cost of ownership considerations
- Value realization patterns

### OUTPUT REQUIREMENTS

1. **Citation Format**: Cite all sources with URLs where available
2. **Quantitative Data**: Include specific numbers, percentages, timelines
3. **Uncertainty Flagging**: Clearly identify areas of conflicting information or low confidence
4. **Preliminary Assessment**:
   - Go/No-Go recommendation with reasoning
   - Estimated appropriate AI agent type (T0-T4) based on findings
   - Key risk factors identified
   - Critical success factors

### AGENT TYPE REFERENCE

Use these definitions when recommending an agent type:

- **T0 (Static Automation)**: Pre-programmed, rule-based systems. No learning. Suitable for simple, deterministic tasks.
- **T1 (Conversational Agents)**: NLP interaction, basic context awareness. Suitable for information retrieval, FAQs.
- **T2 (Procedural Workflow Agents)**: Multi-step execution, tool integration. Suitable for structured processes.
- **T3 (Cognitive Autonomous Agents)**: Self-directed planning, learning capability. Suitable for complex decision-making.
- **T4 (Multi-Agent Generative Systems)**: Collaborative intelligence, distributed coordination. Suitable for enterprise-scale complexity.

### RESEARCH DEPTH GUIDELINES

- Prioritize sources from the past 24 months
- Include at least 3-5 sources per research area
- Cross-reference claims across multiple sources
- Note industry-specific nuances vs. general AI trends
- Identify gaps in available research

---

## Output Format

```markdown
# Research Report: {industry} AI Agent Assessment

## Executive Summary
[2-3 paragraph overview with key findings and recommendations]

## Preliminary Assessment
- **Go/No-Go Recommendation:** [Go/Caution/No-Go]
- **Recommended Agent Type:** [T0-T4]
- **Confidence Level:** [High/Medium/Low]
- **Key Risk Factors:** [Bullet list]

## 1. Industry AI Adoption
[Detailed findings with citations]

## 2. Regulatory Environment
[Detailed findings with citations]

## 3. Technical Integration
[Detailed findings with citations]

## 4. Risk & Failure Modes
[Detailed findings with citations]

## 5. Economic Viability
[Detailed findings with citations]

## Sources
[Complete list of all sources with URLs]

## Research Limitations
[Areas where information was limited or conflicting]
```
