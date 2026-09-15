# Expense Audit Assistant — Architecture & Data Spec

AI-powered expense audit system: FastAPI + LangGraph agents + Gemini Flash (LLM) + PostgreSQL with pgvector for RAG.

The system helps company auditors/managers review employee expense claims. A multi-agent workflow validates the claim
against receipt data, business rules, and company policies, and produces a structured recommendation backed by relevant
references.

**Frontend:** Next.js (`apps/web`) · **Backend:** FastAPI (`apps/api`) · **Database:** PostgreSQL + pgvector ·
**ORM:** SQLAlchemy 2.x · **Driver:** psycopg 3 · **Migrations:** Alembic · **Agents:** LangGraph · **LLM:** Google Gemini Flash

## Architecture

```mermaid
flowchart TD
    A[Employee / Auditor] --> B[Next.js Frontend]
    B <--> C[FastAPI API Layer]

    subgraph BE["FastAPI Backend"]
        C --> D[Middleware: CORS, Logging, Error Handling]
        D --> E{Routers}
        E --> E2[Upload]
        E --> E3[Claims]
        E --> E4[Audit]
        E --> E5[Policy]
        E --> E6[Dashboard]
        E2 --> F[Background Task]
    end

    F --> G[Load Claim + Document]
    G --> WF

    subgraph WF["LangGraph Audit Workflow - sequential"]
        direction TB
        ORCH[Audit Agent — Orchestrator]
        ORCH -->|call| OCR[OCR & Extraction Agent]
        OCR --> ORCH
        ORCH -->|call| VAL["Validation Agent<br/>(incl. duplicate detection)"]
        VAL --> ORCH
        ORCH -->|call| RAG[Policy RAG Agent]
        RAG --> ORCH
        ORCH -->|tool call| SAVE[Persist Audit Result]
    end

    OCR -. structured extraction .-> GEM[(Gemini Flash)]
    VAL -. LLM reasoning .-> GEM
    RAG -. LLM reasoning .-> GEM
    ORCH -. evidence-based explanation .-> GEM

    RAG -. policy clause search .-> DB[(PostgreSQL + pgvector)]
    VAL -. invoice/amount/hash search .-> DB
    SAVE --> DB
    E3 & E5 & E6 --> DB
    DB --> E4 --> B
```

The workflow is **sequential**: the Audit Agent coordinates the specialized sub-agents one stage at a time.
Parallel agent execution is not used in the initial implementation.

**Runtime flows**
- `data/input/` → `seed_postgres.py` → PostgreSQL (employees, historical claims)
- `data/input/policies/` → `index_policies.py` → pgvector embeddings table in PostgreSQL
- Frontend upload → `storage/uploads/` → Gemini Flash OCR → PostgreSQL (audit results)

## Backend Components

| Component | Purpose |
|---|---|
| Upload Router | Upload invoice/receipt/form; store path + hash |
| Claims Router | Create/submit claims, add expense lines |
| Audit Router | Start audit, get status/findings/decision |
| Policy Router | Upload policy docs, trigger pgvector indexing |
| Dashboard Router | Claims/violations/duplicates/risk counts |
| Middleware | CORS, logging, error handling |
| Claim / File / Audit / Policy Service | Business logic behind each router |
| Duplicate Service | Searches PostgreSQL for likely duplicate claims — invoked by the **Validation Agent** |
| Gemini Client | Calls Gemini Flash with retry, timeout, rate-limit, JSON validation |
| RAG Service | Policy vector retrieval for the **Policy RAG Agent** |

*Auth is intentionally left out of the current architecture — it will be added in a later phase.*

## LangGraph Agents

LangGraph runs only inside the audit background task (not a separate server). There is **one orchestrating agent and
three sub-agents**. The Audit Agent lives between stages: each sub-agent is invoked, returns a structured result,
and control returns to the orchestrator before the next stage.

| Agent | Role | Input | Output |
|---|---|---|---|
| **Audit Agent** (orchestrator) | Orchestrates the workflow: invokes the 3 sub-agents, manages state/handoffs, aggregates results, persists state, and synthesizes the final result | Claim + document | Structured audit result: risk assessment, findings, recommendation, references |
| OCR & Extraction Agent | Sub-agent, called by the orchestrator. Normalizes the input into structured data | Uploaded invoice/form | Structured expense data (merchant, invoice #, date, amount, currency, category) |
| Validation Agent | Sub-agent, called by the orchestrator. Validates against deterministic application rules and detects duplicates (exact + fuzzy match on invoice #, merchant, amount, file/image hashes) | Claim + extracted expense data | Structured validation result + duplicate score/candidates |
| Policy RAG Agent | Sub-agent, called by the orchestrator. Retrieves and reasons over company policy context | Category + claim context | Relevant policy findings + citations, retrieved via pgvector |

**LLM usage:** Gemini Flash is the single model used across the whole workflow — OCR & Extraction (reading
invoices/forms), Validation and Policy RAG reasoning, and the orchestrator's final evidence-based audit explanation.
Simple deterministic checks (totals, date math, required fields) stay as plain Python, not Gemini calls.

## Layered Boundaries

```text
API
  ↓
Application / Workflow
  ↓
Agents
  ↓
Tools / Services
  ↓
Infrastructure
  ↓
PostgreSQL / External Services
```

Business logic must not be placed directly inside FastAPI route handlers. Agents must not construct SQL or hold
database sessions; they use narrow, well-defined tools that delegate to application services.

## Project Structure

```
apps/api/
├── requirements.txt
└── app/
    ├── main.py
    ├── api/                       # Routers (HTTP) - audits, auth, claims, dashboard, health, policies, uploads
    ├── core/                      # config, security, logging, exceptions, dependencies
    ├── db/                        # session, base, migrations/
    ├── models/                    # SQLAlchemy ORM models
    ├── schemas/                   # Pydantic contracts (API, agent, tool, persistence)
    ├── repositories/              # data access layer
    ├── services/                  # application/business logic, gemini client, rag, duplicate detection
    ├── agents/                    # LangGraph - graph.py, state.py, audit_agent.py, ocr_agent.py,
    │                              #   validation_agent.py, policy_rag_agent.py
    ├── tools/                     # agent tool layer (planned)
    ├── rules/                     # deterministic validation rules
    ├── prompts/                   # LLM prompt templates
    └── utils/                     # file_hash, image_hash, date_utils, money_utils
```

The final human-facing outcome is **decision support for the auditor/manager** — recommendation, reasons, validation
findings, policy findings, grounding references, warnings, and confidence — not autonomous approval or rejection
unless that behavior is explicitly introduced later.

## Technology Stack

- **FastAPI** for HTTP APIs: typed request/response models, dependency injection, async endpoints.
- **Pydantic** for structured contracts between API, agents, tools, and services.
- **SQLAlchemy 2.x** (modern `Mapped` / `mapped_column` style) with **psycopg 3** as the driver.
- **PostgreSQL** with JSON/JSONB only for genuinely semi-structured data.
- **Alembic** for all schema migrations.
- **pgvector** for policy document vector storage and similarity retrieval.

Detailed standards: `backend/technology-stack.md`, `backend/rag-pipeline.md`.