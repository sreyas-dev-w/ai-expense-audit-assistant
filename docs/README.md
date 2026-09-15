# Docs Index

The repository's knowledge base. It serves two audiences:

- **Humans** — reference for how the system is architected, what the standards are, and why decisions were made.
- **AI agents** — structured, focused context that the root `AGENTS.md` points to. Files are small and domain-scoped so an agent loads only what it needs.

## How to use

1. Start at `AGENTS.md` (repo root) for the ground rules.
2. Load the decision file that matches the area you are working on (see index below).
3. Return to a file if a cross-cutting change affects it. Do not duplicate rules between files — the most specific file is authoritative.

## Index

| Area | File | Read this when |
|---|---|---|
| System overview | `architecture/high-level-backend-architecture.md` | You need the full system picture, runtime flows, or component inventory |
| Agent orchestration | `agents/orchestration.md` | Working on the LangGraph workflow, graph state, or agent-to-agent contracts |
| Audit Agent | `agents/audit-agent.md` | Working on the orchestrating agent |
| OCR & Extraction Agent | `agents/extraction-agent.md` | Working on receipt/document extraction |
| Validation Agent | `agents/validation-agent.md` | Working on claim validation rules |
| Policy RAG Agent | `agents/policy-rag-agent.md` | Working on policy reasoning / grounding |
| Agent tools | `agents/agent-tools.md` | Adding or changing agent tools or database access from agents |
| Technology stack | `backend/technology-stack.md` | Writing FastAPI, Pydantic, SQLAlchemy, psycopg, Alembic, or PostgreSQL code |
| API design | `backend/api-design.md` | Declaring or modifying HTTP endpoints |
| LLM integration | `backend/llm-integration.md` | Using Gemini, structured LLM output, or configuration |
| RAG pipeline | `backend/rag-pipeline.md` | Changing ingestion, embeddings, retrieval, or vector schema |
| Reliability | `backend/reliability.md` | Error handling, retries, timeouts, transaction boundaries |
| Auditability | `backend/auditability.md` | Shaping the final audit result / grounding references |
| Security | `backend/security.md` | Handling sensitive data, secrets, tool privileges |
| Data contracts | `schemas/data-contracts.md` | Defining or evolving Pydantic contracts / agent messages |
| Decisions | `decisions/0001-separation-of-responsibilities.md` | Reasoning about layer boundaries or applying the guiding principles |
| Code standards | `development/code-standards.md` | Writing/completing Python or backend code |
| Change process | `development/change-process.md` | Changing the agent workflow, database schema, or RAG pipeline |

## Status of sections

- **Backend** — documented. Backend context is the current source of truth.
- **Frontend** — not documented yet (Next.js). Frontend conventions will be added in a later phase. Until then, keep frontend changes localized to `apps/web` and follow the existing Next.js project conventions.