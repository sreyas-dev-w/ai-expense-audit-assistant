"""Agent contract mappers.

These map the OCR/extraction output into the input contracts of the downstream
agents (``docs/schemas/data-contracts.md``). A contract is defined once (the
canonical category data lives in ``app/schemas/expense.py`` and the policy
input in ``app/schemas/policy.py``) and these mappers only transform between
stages — they never re-define a schema.

- ``category_data_mapper`` — extraction ↔ canonical ``category_data`` models.
- ``policy_request_mapper`` — extraction + claim context → ``PolicyEvaluationRequest``.
- ``validation_request_mapper`` — extraction + claim context → ``ValidationRequest``.
"""