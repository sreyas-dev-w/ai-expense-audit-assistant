# Validation Agent

The **Validation Agent** receives the structured expense claim produced by the extraction stage and validates it
against application/business validation rules.

## Flow

```text
Structured Expense Claim
        ↓
Validation Agent
        ↓
Structured Validation Result
        ↓
Audit Agent
```

## Contract

The Validation Agent returns a structured Pydantic model containing the relevant validation results.

## Deterministic Rules

Validation rules should remain **deterministic where possible**. **Do not use an LLM for deterministic logic when
normal application code can reliably perform the validation.**

Examples of deterministic checks that should be implemented as code/rules rather than delegated to an LLM:

- numeric limits
- required fields
- date constraints
- totals / tax math
- duplicate detection (exact + fuzzy matching on invoice number, merchant, amount, file/image hashes)

Deterministic rule implementations live in `app/rules/` and are invoked by the Validation Agent.

## Output

The agent returns a structured validation result (findings, warnings, and where applicable duplicate-score
candidates) that the Audit Agent aggregates into the final audit result.