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

Tools expose narrow, well-defined operations. The exact tool set should evolve with the domain. Examples:

```text
update_extraction_result(...)
store_validation_result(...)
store_policy_result(...)
update_audit_status(...)
```

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