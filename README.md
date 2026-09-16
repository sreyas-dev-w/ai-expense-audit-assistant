# AI Expense Audit Assistant

## Recommended project folder structure

```text
ai-expense-audit-assistant/
│
├── apps/
│   ├── web/                 # Next.js
│   └── api/                 # FastAPI
│
├── design/                  # UI reference
│
├── docs/                    # Project knowledge + development
│   ├── requirements/
│   ├── architecture/
│   ├── agents/
│   ├── policies/
│   ├── schemas/
│   ├── workflows/
│   ├── decisions/
│   └── development/
│
├── .github/
├── README.md
└── CONTRIBUTING.md
```

Monorepo with two apps:

## web

Next.js (TypeScript + Tailwind) frontend with shadcn UI, TanStack Query, zod, react-hook-form and Hugeicons.

```bash
cd web
npm install
npm run dev
```

## api

FastAPI backend. Requires a local PostgreSQL instance with pgvector (see `apps/api/.env.example` for the connection string shape).

```bash
cd apps/api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python scripts/seed_postgres.py
.venv/bin/uvicorn app.main:app --reload --port 8000
```

- `python scripts/seed_postgres.py --dry-run` parses the CSVs and prints counts without writing.
- `python scripts/seed_postgres.py --force` deletes existing accounts/projects/employees (and cascading claims) then reloads. Dev-only.

Liveness: http://localhost:8000/api/v1/health
Readiness (Postgres ping): http://localhost:8000/api/v1/health/ready
Interactive docs: http://localhost:8000/docs
