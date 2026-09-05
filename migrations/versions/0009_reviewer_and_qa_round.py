"""Reviewer routing and QA rounds

The three columns ADR-007 authorises, grouped as one coherent schema change
(ADR-005 5.10). Two of the four rulings needed no schema at all; these are the
two that did.

`tasks.reviewer_id` (ADR-007 7.3) records the Reviewer routed a submitted Task.
It is nullable because a Task carries no Reviewer before routing, and it carries
a `CHECK` refusing to store the assigned Worker as the Reviewer. The domain model
already makes that state unconstructible; the constraint makes it unstorable, so
ADR-001 survives any path that bypasses the model.

`features.qa_round` and `qa_reports.qa_round` (ADR-007 7.4) select a Feature's
current defect position. Both default to 1 for existing rows and are then left
`NOT NULL` with no server default: the round is always supplied by the Kernel,
never by the database.

Neither timestamp columns nor the event `sequence_number` are pressed into this
service, so ADR-005 5.9 and ADR-006 6.1 stand.

Revision ID: 0009_reviewer_and_qa_round
Revises: 0008_events_and_transition_audit
Create Date: 2026-09-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_reviewer_and_qa_round"
down_revision: str | None = "0008_events_and_transition_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("reviewer_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_tasks_reviewer_id_actors",
        "tasks",
        "actors",
        ["reviewer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_tasks_reviewer_is_not_worker",
        "tasks",
        "reviewer_id IS NULL OR assigned_worker_id IS NULL OR reviewer_id <> assigned_worker_id",
    )

    _add_qa_round("features", "ck_features_qa_round")
    _add_qa_round("qa_reports", "ck_qa_reports_qa_round")


def _add_qa_round(table: str, constraint: str) -> None:
    """Adds a `NOT NULL` `qa_round` to ``table``, backfilling existing rows to 1.

    The server default is dropped immediately after the backfill so the column
    has no default at rest. A default would let a caller omit the round and get
    a plausible-looking 1, which is exactly the silent wrong answer ADR-007 7.4
    exists to prevent.
    """
    op.add_column(
        table,
        sa.Column("qa_round", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.alter_column(table, "qa_round", server_default=None)
    op.create_check_constraint(constraint, table, "qa_round >= 1")


def downgrade() -> None:
    op.drop_constraint("ck_qa_reports_qa_round", "qa_reports", type_="check")
    op.drop_column("qa_reports", "qa_round")
    op.drop_constraint("ck_features_qa_round", "features", type_="check")
    op.drop_column("features", "qa_round")
    op.drop_constraint("ck_tasks_reviewer_is_not_worker", "tasks", type_="check")
    op.drop_constraint("fk_tasks_reviewer_id_actors", "tasks", type_="foreignkey")
    op.drop_column("tasks", "reviewer_id")
