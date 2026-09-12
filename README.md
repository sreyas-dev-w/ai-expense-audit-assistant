# AI Expense Audit Assistant

Monorepo with two apps:

## web
Next.js (TypeScript + Tailwind) frontend with shadcn UI, TanStack Query, zod, react-hook-form and Hugeicons.

```bash
cd web
npm install
npm run dev
```

## api
FastAPI backend.

```bash
cd api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Health check: http://localhost:8000/api/v1/health
Interactive docs: http://localhost:8000/docs