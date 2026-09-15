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
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Validation Agent      │
│                         │
│ Validate claim data     │
│ against application     │
│ validation rules        │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     Audit Agent         │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│    Policy RAG Agent     │
│                         │
│ Retrieve relevant       │
│ company policies from   │
│ PostgreSQL + pgvector   │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     Audit Agent         │
│                         │
│ Aggregate results       │
│ and persist state       │
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

**Do not introduce parallel agent execution** unless the workflow requirements explicitly change or there is a clear
architectural reason.

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

- Keep state explicit and typed where practical.
- Avoid putting arbitrary transient data into global state.
- The graph state should represent the workflow rather than becoming a generic application-wide data store.
- Persist important workflow results through the application's persistence layer rather than relying exclusively on
  in-memory LangGraph state.

## Failure Behavior

Treat errors as first-class workflow states (see `docs/backend/reliability.md`). Every node must fail explicitly and
carry enough context to identify which workflow, agent, and operation failed, and whether retrying is safe.

## Change Process

Changes to the LangGraph workflow are architectural changes. See `docs/development/change-process.md` before adding
or removing an agent.