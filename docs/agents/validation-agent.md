# Validation Agent

The **Validation Agent** validates the structured expense claim against deterministic application/business rules and
produces a structured, auditable validation result. In the Audit Agent graph it runs **in parallel** with the Policy
RAG Agent (both read only the stored extraction).

## Flow

```text
ValidationRequest
        ↓
load_context → run_rules → reason → assemble
                                │
                                └── errors → error_terminal
        ↓
ValidationAgentResult
        ↓
Audit Agent
```

- `load_context` — loads the account budget and recent prior claims (duplicate candidates). A failed context lookup is
  a **soft** failure: it yields a warning and the rule chain continues without budget/duplicate context.
- `run_rules` — runs the deterministic rule chain (below). **No LLM is involved in this node.**
- `reason` — a single Gemini Flash call that reviews the deterministic findings, is seeded from the deterministic
  authenticity heuristics, and may add authenticity findings/warnings (never deterministic contradiction).
- `assemble` — computes the verdict and confidence. The LLM can flag suspicions and add warnings but can **never**
  override a BLOCKING finding to `PASS`.

## Deterministic Rules

Validation is **deterministic where possible**; the LLM is used only for authenticity reasoning. Implementations live
in `app/rules/` and are invoked in this order:

```text
check_amounts → check_dates → check_cross_fields → check_budget → check_duplicates → check_authenticity_heuristics
```

Runners return findings, checks, warnings, and a `NormalizedExpense`.

| Rule module | Coverage | Key constants |
|---|---|---|
| `amounts` | claimed amount missing / not positive; extracted total vs claim amount | `AMOUNT_TOLERANCE = 1.00` |
| `dates` | invalid / missing dates (missing-blocking except ACCOMMODATION), date-after-submission, claim older than 90 days | `MAX_CLAIM_AGE_DAYS = 90` |
| `cross_fields` | receipt presence mismatch; employee_id mismatch between submission and context | — |
| `budget` | budget check skipped-with-warning when no account context; BLOCKING when budget exceeded | — |
| `duplicates` | exact + fuzzy duplicate score against prior claims (document number, merchant, amount, date) | `DUPLICATE_AMOUNT_TOLERANCE = 1.00`, `DUPLICATE_DATE_WINDOW_DAYS = 7`, `DUPLICATE_SCORE_THRESHOLD = 0.6`, `EXACT_DUPLICATE_SCORE = 1.0`, `EMPLOYEE_CLAIM_SCAN_LIMIT = 100` |
| `authenticity_heuristics` | not-a-receipt / missing-identifier warnings that seed the LLM reasoning node | — |

Each finding carries a `rule_id`, severity (`blocking` / `warning` / `info`), category, description, and evidence —
see `app/schemas/validation.py`. Duplicate detection does **not** use file/image hashes.

## Input / Output Contract

- **Input:** `ValidationRequest` (`app/schemas/validation.py`) — a flat envelope combining the OCR extraction with the
  minimal claim/employee/account context the rules need. Built by `map_to_validation_request` in
  `app/agents/mappers/validation_request_mapper.py`; a category mismatch raises `MapperError`.
- **Output:** `ValidationAgentResult` (`status` + `output` or `error`). `ValidationAgentOutput` = `ValidationVerdict`
  (`PASS` / `FAIL` / `FLAG_FOR_REVIEW`), confidence, findings, checks, warnings, duplicate candidates, budget snapshot,
  authenticity assessment, summary.
- **Persistence:** `ValidationService.store_validation_result(claim_id, result)` writes `validation_response` into the
  claim's `agent_response` row (via the `store_agent_response` tool, or directly in
  `POST /api/v1/validation/evaluate`). `ERROR` envelopes are never persisted.
- **Prompt:** `app/prompts/validation_prompt.txt`. **Entry points:** `run_validation_agent(...)` (standalone) and
  `build_validation_agent(...)` (graph node wired into the Audit Agent's `run_validation` node), see
  `app/agents/validation_agent.py`.

## Output

The Audit Agent aggregates this result (with the policy result) into the final audit result, so the human auditor sees
exactly which rule fired and why — see `docs/backend/auditability.md`.