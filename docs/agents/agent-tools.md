# Agent Tools

The Audit Agent uses **tool calls** for database operations, particularly operations that update/persist audit
workflow data. Tools provide controlled capabilities to the agent.

## Tool Flow

```text
Audit Agent
    │
    │ tool call
    ▼
Database Tool
    │
    ▼
Application / Repository Layer
    │
    ▼
PostgreSQL
```

The LLM must **not** directly construct or execute arbitrary SQL.

## Tool Design

Tools expose narrow, well-defined operations. The Audit Agent tool set in
`apps/api/app/tools/audit_tools.py` is:

```text
load_audit_context(claim_id)
update_claim_status(claim_id, status)
create_run_row(claim_id)
store_validation_result(row_id, result)
store_policy_result(row_id, result)
store_audit_result(row_id, result)
load_receipt_bytes(receipt_url)
```

`store_audit_result` writes `audit_response` JSONB plus the approver-facing
`validation_violation`, `policy_violation`, `notes`, and `confidence_score`
columns. Violation text is joined from structured findings in code; `notes` is
the Gemini summary.

Tools must:

- validate their inputs
- perform authorized operations only
- return structured results
- handle failures explicitly
- avoid exposing unnecessary database functionality to the agent

**Do not create a generic tool such as `execute_sql(sql: str)` for normal agent operation.**

## Database Access From Agents

Agents must not directly instantiate SQLAlchemy sessions or database engines.

Prefers:

```text
Audit Agent
    ↓
Agent Tool
    ↓
Application Service / Repository
    ↓
SQLAlchemy
    ↓
PostgreSQL
```

instead of:

```text
Audit Agent
    ↓
SQLAlchemy Session
    ↓
PostgreSQL
```

This keeps the agent layer independent from persistence implementation details and makes the system easier to test
and evolve.

## Security

Agent tools follow the **principle of least privilege**: expose only the capabilities a tool's job requires, and
never allow unrestricted tool capabilities or arbitrary SQL (see `docs/backend/security.md`).