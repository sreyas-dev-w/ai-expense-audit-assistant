# Policy RAG Agent

The **Policy RAG Agent** evaluates the expense claim against company policies.

## Responsibilities

1. Receive structured claim data.
2. Determine the relevant policy information required.
3. Query the policy vector store.
4. Retrieve relevant policy chunks.
5. Reason over the claim and retrieved policy context.
6. Produce a structured policy evaluation.
7. Include grounding/reference information for the audit result.

## Flow

```text
Structured Claim
      │
      ▼
Policy RAG Agent
      │
      ├── Query construction
      │
      ├── pgvector retrieval
      │
      ├── Relevant policy context
      │
      └── Policy reasoning
               │
               ▼
      Structured Policy Result
               │
               ▼
          Audit Agent
```

## Grounding

Policy reasoning must remain **grounded in retrieved policy content**.

- Do not allow the agent to present unsupported policy claims as authoritative.
- Policy-related conclusions must include references to the retrieved policy content wherever applicable.

See `docs/backend/rag-pipeline.md` for retrieval-stage guidance and `docs/backend/auditability.md` for reference
requirements.