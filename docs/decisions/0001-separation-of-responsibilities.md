# ADR 0001 — Separation of Responsibilities

**Status:** Accepted · **Applies to:** backend

## Context

The system is an agentic application spanning HTTP APIs, agent orchestration, business rules, persistence, vector
retrieval, and external LLM integration. Without explicit boundaries, business logic leaks into route handlers,
agents reach into the database, and contracts become unstructured.

## Decision

Maintain clear, deliberate boundaries between layers:

### API Layer

Responsible for HTTP, authentication/authorization (when implemented), request parsing, response serialization,
and API-level validation.

### Agent Layer

Responsible for reasoning, orchestration, agent-specific behavior, interaction with tools, and structured agent
outputs.

### Tool Layer

Responsible for exposing controlled capabilities to agents, validating tool inputs, and invoking application
services.

### Service / Application Layer

Responsible for business operations, workflow-independent application logic, and coordinating
repositories/infrastructure where appropriate.

### Repository / Data Access Layer

Responsible for database persistence, querying, updates, and transactions.

### Infrastructure Layer

Responsible for PostgreSQL, pgvector, Gemini integration, external services, and other infrastructure dependencies.

**Do not allow responsibilities to leak between layers without a clear reason.**

## Consequences

- Business logic is testable without HTTP or agents.
- Agents never hold database sessions or construct SQL; they use tools.
- Any cross-layer shortcut is a design smell requiring explicit justification.

## Guiding Principles

When making implementation decisions, prioritize these principles **in order**:

1. **Correctness**
2. **Traceability and grounding**
3. **Clear agent boundaries**
4. **Structured data contracts**
5. **Reliable persistence**
6. **Failure handling and recoverability**
7. **Maintainability**
8. **Simplicity**
9. **Performance**
10. **Premature abstraction should be avoided**

The system is an **agentic application**, but not every piece of functionality should become an agent.

- Use agents for tasks requiring reasoning, interpretation, orchestration, or interaction with contextual
  information.
- Use normal application code for deterministic operations whenever possible (see
  `docs/agents/validation-agent.md`).