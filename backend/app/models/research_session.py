"""ResearchSession entity representing target, context, and ownership boundary."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import OwnershipScope, SessionStatus

if TYPE_CHECKING:
    from app.models.research_job import ResearchJob
    from app.models.research_result import ResearchResult
    from app.models.user import User
    from app.models.workspace import Workspace


class ResearchSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A research session targeting an entity, bounded by Personal or Workspace ownership."""

    __tablename__ = "research_sessions"
    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND workspace_id IS NULL) OR "
            "(owner_user_id IS NULL AND workspace_id IS NOT NULL)",
            name="chk_research_session_ownership_scope",
        ),
        Index("ix_research_session_owner_status", "owner_user_id", "status"),
        Index("ix_research_session_workspace_status", "workspace_id", "status"),
        Index("ix_research_session_target_name", "target_name"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    meeting_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time_window: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    research_questions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    talking_points: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Ownership Scope
    scope: Mapped[OwnershipScope] = mapped_column(
        SQLEnum(OwnershipScope, native_enum=False, length=50),
        default=OwnershipScope.PERSONAL,
        index=True,
        nullable=False,
    )
    owner_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )

    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus, native_enum=False, length=50),
        default=SessionStatus.ACTIVE,
        index=True,
        nullable=False,
    )

    # Review Baseline tracking for future Delta Briefing
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_reviewed_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "research_results.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_session_last_reviewed_result",
        ),
        nullable=True,
    )

    # Relationships
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="personal_sessions",
        foreign_keys=[owner_user_id],
    )
    workspace: Mapped[Optional["Workspace"]] = relationship(
        "Workspace",
        back_populates="sessions",
        foreign_keys=[workspace_id],
    )
    jobs: Mapped[List["ResearchJob"]] = relationship(
        "ResearchJob",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="desc(ResearchJob.created_at)",
    )
    results: Mapped[List["ResearchResult"]] = relationship(
        "ResearchResult",
        back_populates="session",
        cascade="all, delete-orphan",
        foreign_keys="[ResearchResult.session_id]",
        order_by="desc(ResearchResult.created_at)",
    )
    last_reviewed_result: Mapped[Optional["ResearchResult"]] = relationship(
        "ResearchResult",
        foreign_keys=[last_reviewed_result_id],
        post_update=True,
    )

    def __repr__(self) -> str:
        return f"<ResearchSession id={self.id} target={self.target_name} scope={self.scope}>"

