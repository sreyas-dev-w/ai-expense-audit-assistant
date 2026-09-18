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

Tools expose narrow, well-defined operations. The Audit Agent is built with the concrete tool set from
`app/tools/__init__.py` (`build_audit_tools`):

| Tool | Operation |
|---|---|
| `get_claim` | Load a claim + employee into a `ClaimAuditContext` for the workflow |
| `update_audit_run_status` | Set `claims.ai_run_status` (pending / running / failed) |
| `fetch_receipt` | Read the claim's receipt bytes (http(s) or local path) into the OCR stage |
| `store_extraction` | Persist the OCR extraction onto `claims.category_data` |
| `store_agent_response` | Write the policy / validation envelope into `agent_response` (JSONB + confidence) |
| `update_claim_result` | Persist the final aggregated decision support onto the claim at the end of the run |

Each tool opens a short-lived database transaction that commits/rollbacks/closes around a single operation (no
long-lived transactions across LLM calls) and raises `AuditToolError` (code + retryability) on failure.

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