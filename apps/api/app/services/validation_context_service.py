"""Short read-only lookups that feed the Validation Agent.

Loads remaining budget and prior claims for duplicate scoring. The agent never
opens a database session; this service owns a short transaction and returns
structured snapshots.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from app.db.session import async_session_factory
from app.repositories.claim_repository import ClaimRepository
from app.repositories.employee_repository import EmployeeRepository
from app.rules.duplicates import score_duplicate_candidates
from app.rules.helpers import to_decimal
from app.rules.normalize import claim_amount, normalize_request
from app.schemas.validation import (
    BudgetSnapshot,
    DuplicateCandidate,
    ValidationRequest,
)


class ValidationContextError(Exception):
    def __init__(self, message: str, *, code: str = "validation_context_error"):
        super().__init__(message)
        self.code = code


@dataclass
class ValidationContext:
    budget: BudgetSnapshot | None = None
    duplicates: list[DuplicateCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ValidationContextService:
    def __init__(self, *, session_factory=async_session_factory) -> None:
        self._session_factory = session_factory

    async def load(self, request: ValidationRequest) -> ValidationContext:
        expense = normalize_request(request)
        amount = claim_amount(expense) or Decimal("0")
        warnings: list[str] = []
        budget: BudgetSnapshot | None = None
        duplicates: list[DuplicateCandidate] = []

        try:
            async with self._session_factory() as session:
                budget, warnings = await self._load_budget(
                    session, request=request, amount=amount
                )
                claims = ClaimRepository(session)
                prior = await claims.list_employee_claims(
                    request.employee_id,
                    exclude_claim_id=request.claim_id,
                )
                duplicates = score_duplicate_candidates(
                    expense=expense, prior_claims=prior
                )
        except ValidationContextError:
            raise
        except Exception as exc:
            raise ValidationContextError(
                f"Failed to load validation context: {exc}",
                code="context_lookup_failed",
            ) from exc

        return ValidationContext(
            budget=budget, duplicates=duplicates, warnings=warnings
        )

    async def _load_budget(
        self,
        session,
        *,
        request: ValidationRequest,
        amount: Decimal,
    ) -> tuple[BudgetSnapshot | None, list[str]]:
        warnings: list[str] = []
        account_id = request.account_id
        if not account_id:
            warnings.append("budget_check_skipped: claim context has no account_id")
            return None, warnings

        account = await EmployeeRepository(session).get_account(account_id)
        if not account:
            warnings.append(
                f"budget_check_skipped: account {account_id} was not found"
            )
            return None, warnings

        remaining = to_decimal(account.get("remaining_budget")) or Decimal("0")
        currency = account.get("currency")
        return (
            BudgetSnapshot(
                account_id=account_id,
                remaining_budget=remaining,
                claim_amount=amount,
                currency=str(currency) if currency is not None else None,
                within_budget=amount <= remaining,
            ),
            warnings,
        )
