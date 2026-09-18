# Auditability and Grounding

The final audit result must be **explainable** to the human auditor/manager.

## Stage Outputs

The system should preserve the relevant outputs of the individual stages:

```text
Extraction Result
Validation Result
Policy Result
Grounding References
LLM Assessment (summary, decision, priority, confidence)
Final Audit Result
```

Policy-related conclusions should include references to the retrieved policy content wherever applicable.

The LLM assessment summary is a human-readable note written to `agent_response.notes`; the produced
decision/priority/confidence feed the final result. When the assessment LLM is unavailable, the deterministic
aggregation produces the note instead — the run still completes with decision support.

## Decision Support

The goal is not simply to produce:

```text
APPROVE
```

but to provide decision support such as:

```text
Recommendation
Reasons
Validation Findings
Policy Findings
Grounding References
Warnings
Confidence / Uncertainty where applicable
```

The exact final schema is defined as the domain evolves (see `docs/schemas/data-contracts.md`).

## Principle

The human-facing outcome is **decision support for the auditor/manager**, not autonomous approval or rejection
unless that behavior is explicitly introduced later.