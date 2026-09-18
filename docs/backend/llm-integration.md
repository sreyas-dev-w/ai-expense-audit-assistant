# LLM Integration

The primary LLM is **Google Gemini Flash**.

## Isolation

LLM-specific integration should be isolated behind the agent/AI infrastructure where practical. **Avoid scattering
model initialization throughout the application.**

Model configuration such as:

- model name
- temperature
- token limits
- API credentials
- retry configuration

should be **configuration-driven** rather than hard-coded throughout the codebase (see Configuration below).

## Structured LLM Output

Whenever an LLM is expected to produce application data, prefer structured output mapped to a Pydantic model. The
application must validate the model output before passing it to another stage of the workflow.

```text
Gemini
  ↓
Structured Output
  ↓
Pydantic Validation
  ↓
Agent Workflow
```

**Do not assume an LLM response is valid merely because the model was instructed to produce JSON.**

Strict output schemas (`extra="forbid"`) produce `additionalProperties: false` in the Pydantic JSON schema,
which the Gemini Developer API rejects; `GeminiClient.generate_structured` strips that keyword from the wire
schema only, so strict post-validation of untrusted LLM output is preserved.

Examples in this codebase:

- Policy RAG: `PolicyAgentOutput` via `apps/api/app/prompts/policy_evaluation_prompt.txt` +
  `app/agents/policy_rag_agent.py`.
- Validation: `ValidationReasoningOutput` via `apps/api/app/prompts/validation_prompt.txt` +
  `app/agents/validation_agent.py`.
- Audit assessment: `AuditAssessment` via `apps/api/app/prompts/audit_assessment_prompt.txt` +
  `app/agents/audit_assessment.py` (the Audit Agent's LLM reasoning node).

## Configuration

Application configuration should be centralized and environment-driven. Do not hard-code:

- API keys
- database credentials
- Gemini credentials
- environment-specific URLs
- secrets
- production configuration

Local development configuration uses environment variables or an appropriate `.env` mechanism. **Secrets must never
be committed to Git.**

**Never commit API keys or credentials.** Use environment variables or the project's configuration mechanism for
secrets (see `docs/backend/security.md`).