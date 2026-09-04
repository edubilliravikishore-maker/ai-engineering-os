"""Event store and transition audit

The append-only event stream and the ledger of evaluated transitions
(ADR-005 5.13 assigned both to this checkpoint; ADR-006 delivers them).

Both tables carry `sequence_number` as `GENERATED ALWAYS AS IDENTITY`
(ADR-006 6.1). It is the sole authority on append order, and `ALWAYS` rather
than `BY DEFAULT` so the application cannot supply it. Neither table carries an
optimistic-lock version column: a row that is never updated cannot lose an
update race (ADR-005 5.6).

`state_transitions_audit` records every evaluated attempt, allowed or rejected
(ADR-006 6.3), which amends the Blueprint 7.2 description of a rejection-only
ledger.

The actor columns are nullable under a `CHECK` written as an equivalence, so an
absent actor is bound to `OS` and to nothing else (ADR-006 6.8): the OS is
infrastructure and has no row in `actors`.

Revision ID: 0008_events_and_transition_audit
Revises: 0007_decisions
Create Date: 2026-09-04 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008_events_and_transition_audit"
down_revision: str | None = "0007_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INITIATORS = "'BUILDER', 'ORCHESTRATOR', 'COORDINATOR', 'WORKER', 'REVIEWER', 'QA', 'OS'"

_EVENT_TYPES = (
    "'FeatureCreated', 'FeaturePlanCreated', 'FeaturePlanActivated', 'TaskAssigned', "
    "'TaskStarted', 'WorkPackageSubmitted', 'EvidenceAttached', 'StateTransitionAllowed', "
    "'StateTransitionRejected', 'ReviewCompleted', 'QAReportSubmitted', 'FeatureAccepted', "
    "'EscalationRaised'"
)


def upgrade() -> None:
    op.create_table(
        "os_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_role", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint(f"event_type IN ({_EVENT_TYPES})", name="ck_os_events_event_type"),
        sa.CheckConstraint(f"actor_role IN ({_INITIATORS})", name="ck_os_events_actor_role"),
        sa.CheckConstraint(
            "(actor_role = 'OS') = (actor_id IS NULL)",
            name="ck_os_events_actorless_only_for_os",
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["actors.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sequence_number"),
    )
    op.create_index(op.f("ix_os_events_actor_id"), "os_events", ["actor_id"], unique=False)
    op.create_index(op.f("ix_os_events_aggregate_id"), "os_events", ["aggregate_id"], unique=False)

    op.create_table(
        "state_transitions_audit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("from_state", sa.String(length=64), nullable=False),
        sa.Column("attempted_state", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=True),
        sa.Column("requested_by_role", sa.String(length=64), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
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
            "outcome IN ('ALLOWED', 'REJECTED')", name="ck_transitions_audit_outcome"
        ),
        sa.CheckConstraint(
            f"requested_by_role IN ({_INITIATORS})",
            name="ck_transitions_audit_requested_by_role",
        ),
        sa.CheckConstraint(
            "(requested_by_role = 'OS') = (requested_by IS NULL)",
            name="ck_transitions_audit_actorless_only_for_os",
        ),
        sa.CheckConstraint(
            "(outcome = 'REJECTED') = (jsonb_array_length(reasons) > 0)",
            name="ck_transitions_audit_refusal_records_why",
        ),
        sa.ForeignKeyConstraint(["requested_by"], ["actors.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sequence_number"),
    )
    op.create_index(
        op.f("ix_state_transitions_audit_entity_id"),
        "state_transitions_audit",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_state_transitions_audit_requested_by"),
        "state_transitions_audit",
        ["requested_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_state_transitions_audit_requested_by"), table_name="state_transitions_audit"
    )
    op.drop_index(
        op.f("ix_state_transitions_audit_entity_id"), table_name="state_transitions_audit"
    )
    op.drop_table("state_transitions_audit")
    op.drop_index(op.f("ix_os_events_aggregate_id"), table_name="os_events")
    op.drop_index(op.f("ix_os_events_actor_id"), table_name="os_events")
    op.drop_table("os_events")
