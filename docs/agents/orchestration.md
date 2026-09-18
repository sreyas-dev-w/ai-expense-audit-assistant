# Agent Orchestration

The application uses **LangGraph** as the primary agent orchestration framework and runs a **sequential multi-agent
workflow**.

## Workflow

The main orchestration agent is the **Audit Agent**. It controls the workflow and coordinates the specialized
sub-agents:

```text
Employee Expense Claim
        │
        ▼
┌─────────────────────────┐
│      Audit Agent        │
│     Orchestrator        │
│  load_claim / begin_run │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ OCR & Extraction Agent  │
│                         │
│ Receipt → Structured    │
│ Expense Data            │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     Audit Agent         │
│  store_extraction →     │
│  map_requests           │
└────────────┬────────────┘
             │
             ┌──────────────────────┐
             │ dispatch (parallel)  │
             ├──────────┬───────────┤
             ▼          ▼
┌─────────────────┐  ┌───────────────────────┐
│  Validation     │  │    Policy RAG Agent   │
│  Agent          │  │                       │
└────────┬────────┘  │ Retrieve relevant      │
         │           │ company policies from  │
         │           │ PostgreSQL + pgvector  │
         └─────┬─────┴───────────────────────┘
│
                ▼
┌─────────────────────────┐
│     Audit Agent         │
│ store_responses →       │
│ assess_result (LLM) →   │
│ aggregate_result →      │
│ finish (persist result) │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     Manager / Auditor   │
│                         │
│ Final decision support  │
└─────────────────────────┘
```

See `docs/architecture/high-level-backend-architecture.md` for the system-level view.

### Execution model

The graph is **sequential** end-to-end, with **one deliberate parallel fan-out**: after the OCR extraction is mapped to
the downstream agent contracts, the **Policy RAG Agent** and the **Validation Agent** run in the *same LangGraph
superstep* (`dispatch → [run_policy | run_validation]`). The two analyses are independent of each other — both read only
the stored extraction — so running them concurrently cuts audit latency in half. This is the only concurrency in the
workflow: there is no separate accommodation/document-translation sub-flow, and everything else is a single forward
pass.

The Validation Agent runs in the same superstep as the Policy RAG Agent via an injected `validation_runner`
(`app/agents/audit_agent.py`, wired in `app/services/audit_service.py`); when no runner is injected the `run_validation`
node falls back to recording `validation_skipped=True`.

After the policy/validation envelopes are persisted (`store_responses`), an **LLM assessment node** (`assess_result`,
`app/agents/audit_assessment.py`) summarises the OCR extraction and the policy/validation results into a
recommendation (summary, ai_decision, priority, confidence). It reads those inputs from graph state, falling back to
the stored `agent_response` row when a stage did not run. When the LLM assessment succeeds, its values drive the
final `ai_decision` / `priority` / `confidence` / `notes`; when it fails (timeout, client error, invalid output) the
run degrades gracefully and the deterministic `aggregate_audit_result` produces the result instead — the run never
fails just because the assessment LLM is unavailable. The assessment only writes `agent_response.notes` and
`confidence_score`; the `policy_response` / `validation_response` columns are never touched.

Failure-free path: `load_claim → begin_run → fetch_receipt → run_ocr → store_extraction → map_requests →
dispatch → [run_policy | run_validation] → store_responses → assess_result → aggregate_result → finish`.

Every fallible node routes to `mark_failed` on error instead of raising, so failures land as explicit workflow states.

## Agent Communication

Agents must communicate through **structured Pydantic models**.

```text
Agent A
   ↓
Pydantic Output Model
   ↓
Agent B
```

Avoid:

```text
Agent A
   ↓
unstructured string
   ↓
Agent B
```

Avoid loosely typed dictionaries for agent-to-agent contracts unless there is a specific technical reason.

Each major agent must have clearly defined:

- input schema
- output schema
- failure/error behavior

Schema design should remain domain-driven and should not be unnecessarily over-engineered.

## Agent State

LangGraph state should contain the structured information required to execute and reason about the workflow.

- Keep state explicit and typed where practical (`AuditAgentState` in `app/agents/state.py`).
- Avoid putting arbitrary transient data into global state.
- The graph state should represent the workflow rather than becoming a generic application-wide data store.
- Persist important workflow results through the application's persistence layer rather than relying exclusively on
  in-memory LangGraph state. The Audit Agent persists the OCR extraction onto `claims.category_data`, the policy and
  validation envelopes into `agent_response`, and the aggregated decision support onto `claims`
  (`app/repositories/`, `app/tools/`).

## Failure Behavior

Treat errors as first-class workflow states (see `docs/backend/reliability.md`). Every node must fail explicitly and
carry enough context to identify which workflow, agent, and operation failed, and whether retrying is safe.

In the Audit Agent graph every fallible node catches its own failures and returns a `fatal` marker
(`AuditAgentError`) rather than raising, because a raised exception aborts the graph run and would skip the terminal
`mark_failed` node. `mark_failed` resets the claim to `submitted` with `ai_run_status=failed` (re-runnable) and returns
an `AuditResult` carrying the error(s). Agent **envelope** errors (e.g. the Policy RAG agent returning an `error`
status) are not treated as workflow failures: the run completes and the error is folded into the decision-support
result so the human auditor still gets a recommendation (see `app/services/audit_service.py`). Tools raise
`AuditToolError` (code + retryability) and open short-lived transactions that commit/rollback/close around a single
operation (no long-lived transactions across LLM calls).

## Change Process

Changes to the LangGraph workflow are architectural changes. See `docs/development/change-process.md` before adding
or removing an agent.