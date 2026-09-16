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

## Implemented Agent

The Audit Agent is a LangGraph parent graph in `app/agents/audit_agent.py`:

```text
load_context → set_status → extract → validate → persist_validation →
policy → persist_policy → aggregate → persist_final
```

- **Input:** existing `claim_id` plus optional receipt bytes. Context is loaded from
  `claims`, `employees` (submitter + manager), `projects`, and `accounts`.
- **Sub-agents:** OCR (`OCRAgent.process`), Validation (`run_validation_agent` with
  `persist=False`), Policy RAG (`run_policy_agent`). Mapping is
  `claim_to_ocr_kwargs` then `to_policy_evaluation_request`.
- **Persistence:** narrow tools in `app/tools/audit_tools.py` write one `agent_response`
  row: stage JSONB, grounded `validation_violation` / `policy_violation` text, Gemini
  `notes`, and `confidence_score`. `claims.auditer_notes` is reserved for the human
  approver and is not written.
- **HTTP:** `POST /api/v1/audits` (multipart `claim_id` + optional `receipt`) and
  `GET /api/v1/audits/{claim_id}`.
- **LLM:** Gemini Flash produces only the approver `notes` and explanation `reasons`.
  Recommendation is decided in code (FAIL/REJECT cannot become `RECOMMEND_APPROVE`).