"""Domain exceptions shared across services.

These carry a stable ``code`` so routers can map them onto HTTP status codes
without string-matching messages (``docs/backend/reliability.md``).
"""


class ClaimNotFoundError(Exception):
    def __init__(self, claim_id: int):
        super().__init__(f"Claim {claim_id} was not found")
        self.claim_id = claim_id
        self.code = "claim_not_found"
