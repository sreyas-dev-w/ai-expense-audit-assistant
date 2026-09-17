"""Reserved: maps extraction + claim into the future Validation Agent input.

The Validation Agent is not implemented yet, so nothing in the Audit Agent
graph references this module at runtime. When the agent lands:

- define its input contract here (mirroring ``policy_request_mapper``) using
  the same canonical category data models from ``app/schemas/expense.py``;
- wire it into ``map_requests_node`` and the parallel validation branch in
  ``app/agents/audit_agent.py``;
- point ``run_validation_node``'s ``validation_runner`` at the new agent.

Deterministic validation rules already live in ``app/rules/``
(``docs/agents/validation-agent.md``) — the Validation Agent invokes those.
"""
from typing import Any


def map_to_validation_request(extraction: Any, *, context: Any) -> Any:
    """Build the Validation Agent input from the OCR output + claim context."""
    raise NotImplementedError(
        "The Validation Agent is not implemented yet; define its input "
        "contract and implement this mapper when it lands."
    )