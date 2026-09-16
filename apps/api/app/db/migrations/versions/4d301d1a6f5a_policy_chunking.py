"""add policy_chunking for retrieval

Revision ID: 4d301d1a6f5a
Revises: fd8a7d66bdfc
Create Date: 2026-09-16 00:00:00.000000+00:00

Source of truth: docs/schemas/database-schema.md

policy_chunking stores chunked policy text with a pgvector embedding from
gemini-embedding-2 (1536 dims, Matryoshka-truncated) for semantic search.
The HNSW index uses cosine distance because Gemini embeddings are
normalized.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '4d301d1a6f5a'
down_revision: Union[str, None] = 'fd8a7d66bdfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "policy_chunking",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embeddings", Vector(1536), nullable=True),
    )
    op.create_index(
        "ix_policy_chunking_policy_id",
        "policy_chunking",
        ["policy_id"],
    )
    op.create_index(
        "ix_policy_chunking_embeddings",
        "policy_chunking",
        ["embeddings"],
        postgresql_using="hnsw",
        postgresql_ops={"embeddings": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_policy_chunking_embeddings", table_name="policy_chunking")
    op.drop_index("ix_policy_chunking_policy_id", table_name="policy_chunking")
    op.drop_table("policy_chunking")