"""Actor identity

One `actors` table with `role` as a column (ADR-005 5.1).

No `coordinators` table and no Domain Registry persistence is created: ADR-003
3.10 forbids both until the Coordinator lifecycle is resolved (Blueprint 14,
item 7). This table stores identity only.

Revision ID: 0002_actor_identity
Revises: 0001_baseline
Create Date: 2026-09-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_actor_identity"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "actors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "row_created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "row_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('BUILDER', 'ORCHESTRATOR', 'COORDINATOR', 'WORKER', 'REVIEWER', 'QA')",
            name="ck_actors_role",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("actors")
