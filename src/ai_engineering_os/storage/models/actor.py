"""Actor identity table (ADR-005 5.1, Blueprint 4.1 #9).

**One `actors` table with `role` as a column.** No `coordinators` table and no
Domain Registry persistence exists: ADR-003 3.10 forbids both until the
Coordinator lifecycle is resolved (Blueprint 14, item 7). This table stores
identity only and maps no domain to any Coordinator.
"""

from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_engineering_os.domain.enums import ActorRole
from ai_engineering_os.storage.database import Base
from ai_engineering_os.storage.models.base import (
    RowMetadataMixin,
    status_check,
    status_column,
    version_column,
)

__all__ = ["ActorRow"]


class ActorRow(RowMetadataMixin, Base):
    """A Builder, Orchestrator, Coordinator, Worker, Reviewer, or QA identity."""

    __tablename__ = "actors"
    __table_args__ = (status_check("role", ActorRole, name="ck_actors_role"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    role: Mapped[str] = status_column()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSONB, nullable=False)

    version: Mapped[int] = version_column()
    __mapper_args__ = {"version_id_col": version}
