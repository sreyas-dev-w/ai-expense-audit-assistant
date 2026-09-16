"""convert enum columns from varchar to native PostgreSQL enums

Revision ID: 9fa11ade2ebf
Revises: df1932b4c898
Create Date: 2026-09-16 00:00:00.000000+00:00

Source of truth: docs/schemas/database-schema.md

The enum columns were previously stored as VARCHAR with CHECK constraints
(native_enum=False, create_constraint=True). This migration creates the
actual PostgreSQL enum types and converts the columns to use them.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.models.enums import (
    ClaimCategory,
    ClaimPriority,
    ClaimStatus,
    Currency,
    JobLevel,
)

# revision identifiers, used by Alembic.
revision: str = '9fa11ade2ebf'
down_revision: Union[str, None] = 'df1932b4c898'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum_type(python_enum, name: str) -> postgresql.ENUM:
    # Labels are derived from the Python members, which is also the value
    # SQLAlchemy persists for these (str, Enum) types.
    return postgresql.ENUM(
        *(member.name for member in python_enum),
        name=name,
    )


def _drop_check_constraints(constraints: list[tuple[str, str]]) -> None:
    for table, constraint_name in constraints:
        op.execute(
            f"ALTER TABLE {table} DROP CONSTRAINT "
            f"ck_{table}_{constraint_name}"
        )


def upgrade() -> None:
    bind = op.get_bind()

    enum_recipes = [
        (Currency, "currency", [
            ("accounts", "currency"),
            ("claims", "currency"),
        ]),
        (JobLevel, "job_level", [("employees", "job_level")]),
        (ClaimCategory, "claim_category", [("claims", "category")]),
        (ClaimStatus, "claim_status", [("claims", "status")]),
        (ClaimPriority, "claim_priority", [("claims", "priority")]),
    ]

    # Create the PostgreSQL enum types once (shared types must not be
    # created twice for both accounts.currency and claims.currency).
    for python_enum, type_name, _columns in enum_recipes:
        # _columns documents which tables/columns share each type; the type
        # is created once per unique name even when shared.
        enum_type = _enum_type(python_enum, type_name)
        enum_type.create(bind, checkfirst=True)

    # The CHECK constraints on the varchar columns prevent the type change.
    # Names follow the repo naming convention: ck_%(table)s_%(enum name)s.
    _drop_check_constraints(
        [
            ("accounts", "currency"),
            ("claims", "currency"),
            ("employees", "job_level"),
            ("claims", "claim_category"),
            ("claims", "claim_status"),
            ("claims", "claim_priority"),
        ]
    )

    # Convert each column to its native enum type. Server defaults must be
    # dropped first because PostgreSQL cannot cast an existing default to the
    # new type automatically.
    conversions = [
        ("accounts", "currency", "currency", "INR"),
        ("claims", "currency", "currency", "INR"),
        ("employees", "job_level", "job_level", None),
        ("claims", "category", "claim_category", None),
        ("claims", "status", "claim_status", None),
        ("claims", "priority", "claim_priority", None),
    ]
    for table, column, type_name, server_default in conversions:
        if server_default is not None:
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT"
            )
        op.alter_column(
            table,
            column,
            type_=postgresql.ENUM(name=type_name, create_type=False),
            postgresql_using=f"{column}::{type_name}",
        )
        if server_default is not None:
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {column} "
                f"SET DEFAULT '{server_default}'"
            )


def downgrade() -> None:
    # Convert enum columns back to VARCHAR with CHECK constraints.
    conversions = [
        ("accounts", "currency", "currency", Currency),
        ("claims", "currency", "currency", Currency),
        ("employees", "job_level", "job_level", JobLevel),
        ("claims", "category", "claim_category", ClaimCategory),
        ("claims", "status", "claim_status", ClaimStatus),
        ("claims", "priority", "claim_priority", ClaimPriority),
    ]
    for table, column, type_name, python_enum in conversions:
        if type_name == "currency":
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT"
            )
        op.alter_column(
            table,
            column,
            type_=sa.String(32),
            postgresql_using=f"{column}::text",
        )
        labels = ", ".join(f"'{member.name}'" for member in python_enum)
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT ck_{table}_{type_name} "
            f"CHECK ({column} IN ({labels}))"
        )
        if type_name == "currency":
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {column} "
                f"SET DEFAULT 'INR'"
            )

    # Drop the PostgreSQL enum types (currency last, it is shared).
    for python_enum, type_name in [
        (JobLevel, "job_level"),
        (ClaimCategory, "claim_category"),
        (ClaimStatus, "claim_status"),
        (ClaimPriority, "claim_priority"),
        (Currency, "currency"),
    ]:
        enum_type = _enum_type(python_enum, type_name)
        enum_type.drop(op.get_bind(), checkfirst=True)