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

## Implemented Agent

The agent is a LangGraph subgraph in `app/agents/policy_rag_agent.py` (built with the `@tool`-free, tool-based
design — it uses narrow service dependencies, never SQL):

```text
build_query → retrieve_policy → (route) → reason | insufficient_context | error_terminal
```

- **Input contract:** `schemas.policy.PolicyEvaluationRequest` (category-specific discriminated union:
  `FoodMeals | Travel | Accommodation | Other`), evaluated against `PolicyClaimContext`.
- **Output contract:** `PolicyAgentOutput` (decision, severity, checks list, references, confidence) wrapped in
  `PolicyAgentResult` with explicit `error`/`status` fields. LLM output is validated with Pydantic before being
  accepted; invalid output is an explicit error state, never a silent pass.
- **Retrieval:** `rag_service.search` under a configured `top_k`; empty or sub-threshold context routes to
  `insufficient_context` (flagged, not failed) so no unsupported claims are drawn.
- **Entry points:** `run_policy_agent(request, ...)` for one-off calls; `build_policy_agent(rag_service,
  llm_client)` returns the compiled graph for embedding into the audit orchestration graph.
- **LLM:** Gemini Flash via `services/gemini_client.py` (`generate_structured` with `response_schema`), with
  explicit timeouts and retries. System prompt: `app/prompts/policy_evaluation_prompt.txt`.