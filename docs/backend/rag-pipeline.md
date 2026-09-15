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