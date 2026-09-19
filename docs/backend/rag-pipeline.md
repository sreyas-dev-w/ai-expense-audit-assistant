# RAG Pipeline

The application uses **PostgreSQL + pgvector** for vector storage and similarity search. Policy documents and their
vector representations are stored in PostgreSQL.

## Pipeline Stages

The vector/RAG implementation keeps the following responsibilities **separate**:

```text
Document ingestion
        ↓
Chunking
        ↓
Embedding generation
        ↓
Vector storage
        ↓
Similarity retrieval
        ↓
Policy RAG Agent
```

Do not couple document ingestion unnecessarily to the runtime agent workflow.

## RAG Changes

When modifying the policy RAG pipeline, consider the complete path:

```text
Policy Document
      ↓
Chunking
      ↓
Embedding
      ↓
PostgreSQL + pgvector
      ↓
Retrieval
      ↓
Retrieved Context
      ↓
Policy RAG Agent
      ↓
Structured Policy Result
```

Changes to one stage can affect the others.

**Do not optimize retrieval solely for similarity score.** Relevance to the policy question and sufficient context
for grounded reasoning are more important than raw similarity.

## pgvector Schema

Vector-related schema changes require an Alembic migration (see `docs/backend/technology-stack.md` for migration
requirements).

## Implemented Pipeline

The ingestion + retrieval pipeline lives in `apps/api/app`:

```text
POST /api/v1/policies/documents        (app/api/policies.py)
        ↓
file_service.store_pdf                  → storage dump (POLICY_STORAGE_DIR)
        ↓
pdf_extraction_service.extract_pdf_text + chunking_service.chunk_policy_text
        ↓
embedding_service.GeminiEmbeddingProvider   (gemini-embedding-2, 1536-dim, external call)
        ↓
repositories/policy_repository.add_chunks    (single short transaction)
        ↓
POST /api/v1/policies/search           → rag_service.search (pgvector cosine, (1 - distance))
        ↓
policy_repository.search_chunks        → joins policy_documents for the source filename (surfaces policy_filename)
```

Persistence tables: `policy_documents` (one row per ingested PDF, `sha256` dedupe, forced re-ingest allowed) and
`policy_chunking` (chunks with 1536-dim embeddings, HNSW cosine index). Both are documented in
`docs/schemas/database-schema.md` and defined via Alembic migrations.

Key rules enforced in code:

- Embedding happens **before** the write transaction opens, so no long-lived transaction spans LLM calls.
- Stored PDFs are cleaned up on re-ingest/delete/failed persistence; the dump directory is git-ignored.
- Similarity thresholds filter low-confidence matches; retrieval relevance beats raw score (see policy agent).