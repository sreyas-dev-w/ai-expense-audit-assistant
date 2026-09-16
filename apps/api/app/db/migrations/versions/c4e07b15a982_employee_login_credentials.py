"""add email and password columns to employees

Revision ID: c4e07b15a982
Revises: b7c91e2a4d03
Create Date: 2026-09-16 16:40:00.000000+00:00

Source of truth: docs/schemas/database-schema.md

Both columns are added nullable, backfilled for existing rows, then tightened
to NOT NULL so the migration is safe against the populated employees table.

Emails are derived from ``employee_name`` (``first.last@expenseaudit.test``)
with the employee id appended when two people share a name. ``password`` is
seeded with a single shared demo value and is stored unhashed on purpose --
this is a sample application, not a production credential store.
"""
import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c4e07b15a982"
down_revision: Union[str, None] = "b7c91e2a4d03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMAIL_DOMAIN = "expenseaudit.test"
SEED_PASSWORD = "Password@123"


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", ".", ascii_only).strip(".").lower()
    return re.sub(r"\.{2,}", ".", cleaned)


def upgrade() -> None:
    op.add_column("employees", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column(
        "employees", sa.Column("password", sa.String(length=255), nullable=True)
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT employee_id, employee_name FROM employees ORDER BY employee_id"
        )
    ).fetchall()

    taken: set[str] = set()
    for employee_id, employee_name in rows:
        local = _slug(employee_name) or _slug(employee_id) or "employee"
        email = f"{local}@{EMAIL_DOMAIN}"
        if email in taken:
            email = f"{local}.{_slug(employee_id)}@{EMAIL_DOMAIN}"
        taken.add(email)
        connection.execute(
            sa.text(
                "UPDATE employees SET email = :email, password = :password "
                "WHERE employee_id = :employee_id"
            ),
            {
                "email": email,
                "password": SEED_PASSWORD,
                "employee_id": employee_id,
            },
        )

    op.alter_column("employees", "email", nullable=False)
    op.alter_column("employees", "password", nullable=False)
    op.create_unique_constraint("uq_employees_email", "employees", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_employees_email", "employees", type_="unique")
    op.drop_column("employees", "password")
    op.drop_column("employees", "email")
