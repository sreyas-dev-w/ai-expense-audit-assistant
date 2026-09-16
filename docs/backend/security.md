# Security

Treat the expense claim and receipt data as potentially sensitive business information.

## Rules

Never:

- commit secrets
- log API keys
- log database passwords
- expose credentials through agent state
- allow arbitrary SQL execution by LLMs
- trust LLM output without schema validation
- allow unrestricted tool capabilities

## Agent Tools

Agent tools must follow the **principle of least privilege** (see `docs/agents/agent-tools.md`).

## Sensitive Data

- Receipts and claim data are sensitive business information.
- Secrets and credentials live only in environment variables or the project's configuration mechanism.
- LLM responses are untrusted until validated against a Pydantic schema (see `docs/backend/llm-integration.md`).