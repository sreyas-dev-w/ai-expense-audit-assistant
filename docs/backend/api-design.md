# API Design

FastAPI endpoints should:

- use explicit Pydantic request models
- use explicit response models
- return appropriate HTTP status codes
- validate inputs
- avoid embedding complex business logic
- delegate work to application services/workflows

API contracts should remain **stable and intentional**.

**Do not expose internal database models directly as public API contracts** unless there is a deliberate reason.

## API Layer Scope

The API layer is responsible for:

- HTTP
- authentication/authorization (when implemented)
- request parsing
- response serialization
- API-level validation

## Routing vs Application Logic

Keep routing and application logic separate:

```text
FastAPI Route Handler        → parse, validate, call a service
Application Service/Workflow → business logic, orchestration
Repository / Data Access     → persistence
```

Do not put database queries, complex business logic, or agent orchestration directly inside route handlers.

## Current API Surface (implemented)

All routers except OCR are mounted under the `/api/v1` prefix (OCR router declares its own `/api/v1/ocr` prefix;
`health` is imported but **not yet registered** in `main.py`):

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/claims` | Multipart submit (`claim_json` + `receipt`); validates, stores, schedules background audit. `201 ClaimSubmissionResponse` / `422` |
| `POST /api/v1/audits/{claim_id}/run` | Run the full LangGraph workflow for a claim. `AuditResult` (wraps `AgentRunResult`); `502` on workflow failure |
| `POST /api/v1/policies/documents` | Ingest a policy PDF (form with `force` flag). `201 PolicyIngestResult` / `400` on invalid PDF |
| `POST /api/v1/policies/search` | Semantic search over ingested policies. `PolicySearchResponse` |
| `POST /api/v1/validation/evaluate` | Run the Validation Agent standalone with `persist` control. `ValidationEvaluateResponse` / `404` / `502` |
| `POST /api/v1/ocr/extract` | Multipart `expense_category` + `receipt` → structured `Extraction` |

Endpoints parse/validate then delegate to services/workflows; `ClaimNotFoundError` maps to `404` and persistence
failures to `502`.