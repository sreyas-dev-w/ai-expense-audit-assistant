"""replace claim_category enum with the four expense_categories

Revision ID: fca7d0249071
Revises: 9fa11ade2ebf
Create Date: 2026-09-16 00:00:00.000000+00:00

Source of truth: docs/schemas/database-schema.md

The claim model now uses ExpenseCategory with four categories
(FOOD_MEALS, TRAVEL, ACCOMMODATION, OTHER) instead of the nine legacy
ClaimCategory values. This creates the new PostgreSQL enum type and converts
claims.category to it, mapping legacy values.

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fca7d0249071'
down_revision: Union[str, None] = '9fa11ade2ebf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LEGACY_CATEGORY_LABELS = (
    'MEALS', 'TRAVEL', 'LODGING', 'TRANSPORTATION', 'ENTERTAINMENT',
    'OFFICE_SUPPLIES', 'SOFTWARE', 'SERVICES', 'OTHER',
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE expense_category AS ENUM "
        "('FOOD_MEALS', 'TRAVEL', 'ACCOMMODATION', 'OTHER')"
    )
    op.execute(
        """
        ALTER TABLE claims ALTER COLUMN category TYPE expense_category
        USING CASE category::text
            WHEN 'MEALS' THEN 'FOOD_MEALS'
            WHEN 'LODGING' THEN 'ACCOMMODATION'
            WHEN 'TRANSPORTATION' THEN 'TRAVEL'
            WHEN 'TRAVEL' THEN 'TRAVEL'
            ELSE 'OTHER'
        END::expense_category
        """
    )
    op.execute("DROP TYPE claim_category")


def downgrade() -> None:
    labels = ", ".join(f"'{label}'" for label in _LEGACY_CATEGORY_LABELS)
    op.execute(f"CREATE TYPE claim_category AS ENUM ({labels})")
    op.execute(
        """
        ALTER TABLE claims ALTER COLUMN category TYPE claim_category
        USING CASE category::text
            WHEN 'FOOD_MEALS' THEN 'MEALS'
            WHEN 'ACCOMMODATION' THEN 'LODGING'
            ELSE category::text
        END::claim_category
        """
    )
    op.execute("DROP TYPE expense_category")