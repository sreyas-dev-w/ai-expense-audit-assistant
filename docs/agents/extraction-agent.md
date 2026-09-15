# OCR & Extraction Agent

The **OCR & Extraction Agent** processes the employee's receipt/document input.

## Responsibility

1. Process the receipt.
2. Extract relevant expense information.
3. Normalize the extracted information.
4. Return a predefined structured Pydantic model.

## Flow

```text
Receipt
   ↓
OCR / Extraction
   ↓
Structured Expense Claim Data
   ↓
Audit Agent
```

## Contract

The agent must **not** return an arbitrary natural-language response as its primary output. The extracted
information must conform to an explicit schema.

```text
Agent A
   ↓
Pydantic Output Model
   ↓
Agent B
```

Refer to `docs/schemas/data-contracts.md` for the contract rules.

## Failure Behavior

OCR/extraction may fail or produce malformed output. These are first-class error states that must be handled
explicitly — see `docs/backend/reliability.md`.