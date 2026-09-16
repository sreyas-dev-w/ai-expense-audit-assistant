# Data Contracts

Structured data exchange is the backbone of this system. It defines contracts between the API, agents, tools, and
services.

## Philosophy

Pydantic models define contracts between:

- API requests and responses
- agents
- agent tools
- services
- persistence boundaries where appropriate

Agent communication uses explicit structured models — never loosely defined dictionaries or free-form strings.

```text
Agent A
   ↓
Pydantic Output Model
   ↓
Agent B
```

## Rules

- **Do not duplicate the same conceptual schema in multiple locations.** A contract is defined once and reused.
- Each major agent must have a clearly defined input schema, output schema, and failure/error behavior.
- Whenever an LLM is expected to produce application data, validate the output against a Pydantic model before
  passing it to the next stage (see `docs/backend/llm-integration.md`).
- Do not expose internal database models directly as public API contracts unless there is a deliberate reason
  (see `docs/backend/api-design.md`).
- The exact models belong to the relevant domain and should evolve with the application; do not over-engineer them.

## Where Contracts Live

- **API contracts** — `apps/api/app/schemas/`
- **Agent output models** — defined alongside the agent or in shared schemas, following the same "define once"
  rule.
- **Persistence models** — `apps/api/app/models/` (SQLAlchemy). The authoritative database schema is defined in
  `docs/schemas/database-schema.md`; models and Alembic migrations must match it exactly. These are distinct from
  public API schemas.

## Policy Contracts

Policy domain schemas are defined once in `apps/api/app/schemas/policy.py` and reused across the API, the policy
RAG agent, and services:

- API: `PolicyDocumentSummary`, `PolicyIngestResult`, `PolicySearchRequest`, `RetrievedPolicyChunk`,
  `PolicySearchResponse` (ingestion/search endpoints in `app/api/policies.py`).
- Agent input: `PolicyClaimContext` + `PolicyEvaluationRequest` — a discriminated union over
  `FoodMealsPolicyEvaluation | TravelPolicyEvaluation | AccommodationPolicyEvaluation | OtherPolicyEvaluation`
  that reuses the canonical category data models from `app/schemas/expense.py` (so agent and claim-extraction
  contracts cannot drift).
- Agent output: `PolicyAgentOutput` (decision, severity, violations/checks, references, confidence),
  `PolicyAgentResult`, `PolicyAgentError`, `PolicyAgentStatus`.

## Validation Contracts

Validation domain schemas are defined once in `apps/api/app/schemas/validation.py`:

- Agent input: `ValidationRequest` — the OCR envelope (`submission` + `employee_context` +
  `extraction`) plus optional `claim_id` / `persist`. Category-specific extraction is coerced from
  `submission.expense_category` so the four OCR unions cannot silently drop fields.
- Agent output: `ValidationAgentOutput` (verdict, findings, checks, duplicate candidates, budget
  snapshot, authenticity, confidence) wrapped in `ValidationAgentResult` with explicit
  `error` / `status`. HTTP adds `stored_agent_response_id` on `ValidationEvaluateResponse`.
- Persistence: `ValidationService.store_validation_result(claim_id, result)` inserts a new
  `agent_response` row with `validation_response` JSONB. ERROR envelopes are not written.
- Policy handoff: `to_policy_evaluation_request(ocr)` in
  `apps/api/app/services/policy_request_mapper.py` builds `PolicyEvaluationRequest` from the same
  OCR envelope. Policy RAG does **not** consume validation findings.

## Audit Contracts

Audit domain schemas are defined once in `apps/api/app/schemas/audit.py`:

- Agent input: `AuditRequest` (`claim_id`, optional `persist`) plus receipt bytes. Relational
  context is `AuditContext` (claim, employee, manager, project, account snapshots) loaded from
  the core tables — not ORM models.
- Agent output: `AuditResult` (recommendation, reasons, extraction, validation, policy,
  references, warnings, confidence, `validation_violation`, `policy_violation`, `notes`) wrapped
  in `AuditAgentResult`. HTTP `AuditRunResponse` adds `agent_response_id`, `claim_status`, and
  the denormalized approver fields.
- Persistence: one `agent_response` row per run. The Audit Agent tools write
  `validation_response`, `policy_response`, `audit_response`, `validation_violation`,
  `policy_violation`, `notes`, and `confidence_score`. `claims.auditer_notes` is never written.
- Recommendation is decision support (`RECOMMEND_APPROVE` / `RECOMMEND_REJECT` /
  `FLAG_FOR_REVIEW`). Claim status is set to `IN_AUDIT` only; the workflow does not approve or
  reject the claim.

## Outcome

The system preserves structured stage outputs for auditability:

```text
Extraction Result
Validation Result
Policy Result
Grounding References
Final Audit Result
```

See `docs/backend/auditability.md` for the decision-support shape of the final result.