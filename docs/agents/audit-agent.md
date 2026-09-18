# Audit Agent

The **Audit Agent** is the primary orchestration agent for the LangGraph workflow.

## Responsibilities

- Controlling the audit workflow
- Passing structured data between agents
- Deciding which sub-agent should execute next
- Receiving structured results from sub-agents
- Invoking appropriate tools
- Persisting relevant workflow results
- Summarising the OCR / policy / validation outputs via an **LLM assessment node**
  into the final recommendation (summary, decision, priority, confidence)
- Aggregating the outputs from the specialized agents
- Producing the final structured audit result

## Boundaries

The Audit Agent must **not duplicate the specialized reasoning of its sub-agents**:

- OCR/extraction logic belongs to the **OCR & Extraction Agent**.
- Validation logic belongs to the **Validation Agent**.
- Policy retrieval and policy reasoning belong to the **Policy RAG Agent**.

The Audit Agent coordinates these capabilities; it does not reimplement them.

## LLM Assessment Node

After the policy and validation envelopes are persisted, the `assess_result` node invokes the LLM once more
(`app/agents/audit_assessment.py`, prompt `app/prompts/audit_assessment_prompt.txt`) to summarise the three stage
outputs into an `AuditAssessment` (`app/schemas/assessment.py`): a note, an AI decision (approve / reject / review),
a priority (low / medium / high / urgent) and a confidence. Its inputs come from graph state, falling back to the
stored `agent_response` row via the read `get_agent_response` tool when a stage did not run.

On success its values drive the persisted decision fields; the deterministic aggregation remains as a fallback and
envelope builder. The node persists **only** `agent_response.notes` (the summary) and `agent_response.confidence_score`
— it must never write to the `policy_response` or `validation_response` columns.

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