# Audit Agent

The **Audit Agent** is the primary orchestration agent for the LangGraph workflow.

## Responsibilities

- Controlling the audit workflow
- Passing structured data between agents
- Deciding which sub-agent should execute next
- Receiving structured results from sub-agents
- Invoking appropriate tools
- Persisting relevant workflow results
- Aggregating the outputs from the specialized agents
- Producing the final structured audit result

## Boundaries

The Audit Agent must **not duplicate the specialized reasoning of its sub-agents**:

- OCR/extraction logic belongs to the **OCR & Extraction Agent**.
- Validation logic belongs to the **Validation Agent**.
- Policy retrieval and policy reasoning belong to the **Policy RAG Agent**.

The Audit Agent coordinates these capabilities; it does not reimplement them.

## Interaction Pattern

```text
Audit Agent
    │
    ├── call → OCR & Extraction Agent   → structured extraction result
    ├── call → Validation Agent         → structured validation result
    ├── call → Policy RAG Agent         → structured policy result
    │
    ├── tool calls → persist / update workflow state
    │
    └── aggregate → final structured audit result
```

## Persistence

The Audit Agent uses **agent tools** for database operations — particularly operations that update or persist audit
workflow data (see `docs/agents/agent-tools.md`). It does not construct SQL or hold database sessions directly.

## Output

The final output is **decision support for the auditor/manager**, not autonomous approval or rejection:

```text
Recommendation
Reasons
Validation Findings
Policy Findings
Grounding References
Warnings
Confidence / Uncertainty where applicable
```

See `docs/backend/auditability.md` for the final-schema requirements.