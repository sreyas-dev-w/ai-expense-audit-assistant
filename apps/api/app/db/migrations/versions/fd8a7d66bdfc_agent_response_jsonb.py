"""store agent response payloads as JSONB

Revision ID: fd8a7d66bdfc
Revises: fca7d0249071
Create Date: 2026-09-16 00:00:00.000000+00:00

Source of truth: docs/schemas/database-schema.md

validation_response and policy_response carry structured agent outputs
(like claims.category_data), so they are stored as JSONB instead of TEXT.
The payload schema is defined later via Pydantic contracts.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fd8a7d66bdfc'
down_revision: Union[str, None] = 'fca7d0249071'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for column in ("validation_response", "policy_response"):
        op.alter_column(
            "agent_response",
            column,
            type_=postgresql.JSONB(astext_type=sa.Text()),
            postgresql_using=f"{column}::jsonb",
        )


def downgrade() -> None:
    for column in ("validation_response", "policy_response"):
        op.alter_column(
            "agent_response",
            column,
            type_=sa.Text(),
            postgresql_using=f"{column}::text",
        )