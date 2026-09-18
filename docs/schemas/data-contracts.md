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

- Agent input: `ValidationRequest` — a **flat** envelope combining the OCR `extraction` with the minimal
  claim/employee/account context the deterministic rules need: `claim_id`, `persist`, `category`, `employee_id`,
  `submitted_at`, `account_id`, `claim_amount`, `currency`, `merchant_name`, `receipt_provided`, `category_data`,
  and `extraction`. `category` drives the discriminated `extraction` payload (a before-validator coerces it), so the
  four OCR unions cannot silently drop fields (`apps/api/app/schemas/validation.py`).
- Agent output: `ValidationAgentOutput` (verdict, confidence, findings, checks, warnings, duplicate candidates,
  budget snapshot, authenticity, summary) wrapped in `ValidationAgentResult` with explicit `error` / `status`.
  HTTP adds `stored_agent_response_id` on `ValidationEvaluateResponse`.
- Persistence: `ValidationService.store_validation_result(claim_id, result)` updates the claim's `agent_response`
  row (created at claim submission) with `validation_response` JSONB. ERROR envelopes are not written.
- Policy handoff: `map_to_policy_request(...)` in
  `apps/api/app/agents/mappers/policy_request_mapper.py` builds `PolicyEvaluationRequest` from the claim context
  and canonical category data. Policy RAG does **not** consume validation findings.

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