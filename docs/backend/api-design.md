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