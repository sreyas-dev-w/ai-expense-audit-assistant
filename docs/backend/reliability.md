# Reliability

Errors must be treated as **first-class workflow states**.

## Error Handling

The system should explicitly handle failures such as:

- OCR/extraction failure
- malformed extraction result
- validation failure
- policy retrieval failure
- vector database failure
- LLM failure
- LLM timeout
- invalid structured output
- database failure
- tool execution failure
- unavailable external service
- unexpected agent state

Do not silently swallow exceptions. Avoid generic:

```python
except Exception:
    pass
```

Errors should contain enough context to identify:

- which workflow was executing
- which agent was executing
- which operation failed
- whether retrying is safe
- what the next recovery action should be

## Retries

Retries should only be applied to operations where retrying is **safe**.

Potential retry candidates include transient:

- LLM failures
- network failures
- vector database connectivity failures
- external service failures

Do not blindly retry database mutations or non-idempotent operations. Agent/tool operations that can be retried
should be designed with idempotency in mind where practical.

## Timeouts

External operations must have explicit timeout behavior:

- LLM calls
- OCR services
- vector retrieval
- database operations where appropriate
- external APIs

A single failed external dependency must not cause the application to hang indefinitely.

## Transaction Boundaries

Database transactions should be **deliberate**. Do not keep a database transaction open while waiting for a
potentially slow LLM or external agent operation unless there is a specific requirement.

Prefer:

```text
Agent operation
    ↓
Result
    ↓
Short database transaction
    ↓
Commit
```

rather than:

```text
BEGIN TRANSACTION
    ↓
LLM call
    ↓
OCR
    ↓
RAG retrieval
    ↓
More LLM calls
    ↓
COMMIT
```

Long-running agent workflows must not unnecessarily hold database connections or transactions.