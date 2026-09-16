"""add audit_response and approver-facing violation columns

Revision ID: b7c91e2a4d03
Revises: 26228978c7ca
Create Date: 2026-09-16 13:20:00.000000+00:00

Source of truth: docs/schemas/database-schema.md

``audit_response`` stores the orchestrator's structured AuditResult.
``validation_violation`` / ``policy_violation`` are grounded text summaries
for the approver UI so the frontend does not have to parse nested JSONB.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b7c91e2a4d03"
down_revision: Union[str, None] = "26228978c7ca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_response",
        sa.Column(
            "audit_response",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "agent_response",
        sa.Column("validation_violation", sa.Text(), nullable=True),
    )
    op.add_column(
        "agent_response",
        sa.Column("policy_violation", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_response", "policy_violation")
    op.drop_column("agent_response", "validation_violation")
    op.drop_column("agent_response", "audit_response")
