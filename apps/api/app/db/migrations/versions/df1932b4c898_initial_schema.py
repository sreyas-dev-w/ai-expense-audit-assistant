"""initial schema

Revision ID: df1932b4c898
Revises: 
Create Date: 2026-09-15 18:17:35.737690+00:00

Source of truth: docs/schemas/database-schema.md

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
revision: str = 'df1932b4c898'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _currency() -> sa.Enum:
    return sa.Enum(
        Currency,
        name="currency",
        length=8,
        native_enum=False,
        create_constraint=True,
    )


def upgrade() -> None:
    # accounts
    op.create_table(
        'accounts',
        sa.Column('account_id', sa.String(length=64), nullable=False),
        sa.Column('account_name', sa.String(length=255), nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('budget_allocated', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('remaining_budget', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('currency', _currency(), server_default='INR', nullable=False),
        sa.PrimaryKeyConstraint('account_id', name=op.f('pk_accounts')),
    )
    op.create_index(op.f('ix_accounts_fiscal_year'), 'accounts', ['fiscal_year'], unique=False)

    # projects
    op.create_table(
        'projects',
        sa.Column('project_code', sa.String(length=64), nullable=False),
        sa.Column('project_name', sa.String(length=255), nullable=False),
        sa.Column('account_id', sa.String(length=64), nullable=False),
        sa.Column('project_lead_id', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('project_code', name=op.f('pk_projects')),
    )
    op.create_index(op.f('ix_projects_account_id'), 'projects', ['account_id'], unique=False)
    op.create_index(op.f('ix_projects_project_lead_id'), 'projects', ['project_lead_id'], unique=False)

    # employees
    op.create_table(
        'employees',
        sa.Column('employee_id', sa.String(length=64), nullable=False),
        sa.Column('employee_name', sa.String(length=255), nullable=False),
        sa.Column('job_level', sa.Enum(
            JobLevel,
            name="job_level",
            length=16,
            native_enum=False,
            create_constraint=True,
        ), nullable=False),
        sa.Column('is_manager', sa.Boolean(), nullable=False),
        sa.Column('manager_id', sa.String(length=64), nullable=True),
        sa.Column('project_code', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('employee_id', name=op.f('pk_employees')),
    )
    op.create_index(op.f('ix_employees_manager_id'), 'employees', ['manager_id'], unique=False)
    op.create_index(op.f('ix_employees_project_code'), 'employees', ['project_code'], unique=False)

    # claims
    op.create_table(
        'claims',
        sa.Column('claim_id', sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column('business_purpose', sa.Text(), nullable=True),
        sa.Column('merchant_name', sa.String(length=255), nullable=True),
        sa.Column('category', sa.Enum(
            ClaimCategory,
            name="claim_category",
            length=32,
            native_enum=False,
            create_constraint=True,
        ), nullable=False),
        sa.Column('category_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('employee_id', sa.String(length=64), nullable=False),
        sa.Column('auditer_id', sa.String(length=64), nullable=True),
        sa.Column('auditer_notes', sa.Text(), nullable=True),
        sa.Column('project_code', sa.String(length=64), nullable=True),
        sa.Column('claim_amount', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('currency', _currency(), server_default='INR', nullable=False),
        sa.Column('status', sa.Enum(
            ClaimStatus,
            name="claim_status",
            length=32,
            native_enum=False,
            create_constraint=True,
        ), nullable=False),
        sa.Column('priority', sa.Enum(
            ClaimPriority,
            name="claim_priority",
            length=16,
            native_enum=False,
            create_constraint=True,
        ), nullable=False),
        sa.Column('receipt_url', sa.String(length=1024), nullable=True),
        sa.Column('claim_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('claim_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('receipt_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('claim_id', name=op.f('pk_claims')),
    )
    op.create_index(op.f('ix_claims_category'), 'claims', ['category'], unique=False)
    op.create_index(op.f('ix_claims_employee_id'), 'claims', ['employee_id'], unique=False)
    op.create_index(op.f('ix_claims_auditer_id'), 'claims', ['auditer_id'], unique=False)
    op.create_index(op.f('ix_claims_project_code'), 'claims', ['project_code'], unique=False)
    op.create_index(op.f('ix_claims_status'), 'claims', ['status'], unique=False)
    op.create_index(op.f('ix_claims_claim_created_at'), 'claims', ['claim_created_at'], unique=False)

    # agent_response
    op.create_table(
        'agent_response',
        sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column('claim_id', sa.Integer(), nullable=False),
        sa.Column('validation_response', sa.Text(), nullable=True),
        sa.Column('policy_response', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_agent_response')),
    )
    op.create_index(op.f('ix_agent_response_claim_id'), 'agent_response', ['claim_id'], unique=False)

    # Foreign keys are added after table creation because the schema has
    # circular references (projects <-> employees).
    op.create_foreign_key(
        op.f('fk_projects_account_id_accounts'),
        'projects', 'accounts',
        ['account_id'], ['account_id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('fk_projects_project_lead_id_employees'),
        'projects', 'employees',
        ['project_lead_id'], ['employee_id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        op.f('fk_employees_manager_id_employees'),
        'employees', 'employees',
        ['manager_id'], ['employee_id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        op.f('fk_employees_project_code_projects'),
        'employees', 'projects',
        ['project_code'], ['project_code'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        op.f('fk_claims_employee_id_employees'),
        'claims', 'employees',
        ['employee_id'], ['employee_id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('fk_claims_auditer_id_employees'),
        'claims', 'employees',
        ['auditer_id'], ['employee_id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        op.f('fk_agent_response_claim_id_claims'),
        'agent_response', 'claims',
        ['claim_id'], ['claim_id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    # CASCADE handles the circular FKs between employees <-> projects
    op.execute("DROP TABLE IF EXISTS agent_response CASCADE")
    op.execute("DROP TABLE IF EXISTS claims CASCADE")
    op.execute("DROP TABLE IF EXISTS employees CASCADE")
    op.execute("DROP TABLE IF EXISTS projects CASCADE")
    op.execute("DROP TABLE IF EXISTS accounts CASCADE")