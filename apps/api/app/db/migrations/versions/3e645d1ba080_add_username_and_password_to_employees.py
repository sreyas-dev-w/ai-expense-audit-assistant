"""add username and password columns to employees

Revision ID: 3e645d1ba080
Revises: 3fc459b1feb6
Create Date: 2026-09-16 00:00:00.000000+00:00

Source of truth: docs/schemas/database-schema.md

Adds nullable ``username`` (unique) and ``password`` columns to the
employees table, and backfills dummy login credentials for the seeded
employees (username = lower(employee_id), password = 'password@123').

Both columns are nullable so they are safe to add on top of existing rows;
they are seeded with dummy values only, with no hashing or auth logic.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3e645d1ba080'
down_revision: Union[str, None] = '3fc459b1feb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('employees', sa.Column('username', sa.String(length=64), nullable=True, unique=True, index=True))
    op.add_column('employees', sa.Column('password', sa.String(length=255), nullable=True))
    op.execute(
        "UPDATE employees SET username = lower(employee_id), "
        "password = 'password@123' WHERE username IS NULL"
    )


def downgrade() -> None:
    op.drop_column('employees', 'password')
    op.drop_column('employees', 'username')