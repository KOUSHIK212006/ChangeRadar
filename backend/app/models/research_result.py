"""ResearchResult entity representing synthesized intelligence, briefing, and delta history."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    JSON,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ResearchResultStatus

if TYPE_CHECKING:
    from app.models.research_job import ResearchJob
    from app.models.research_session import ResearchSession
    from app.models.user import User


class ResearchResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persisted synthesized intelligence briefing resulting from a research run."""

    __tablename__ = "research_results"
    __table_args__ = (
        Index("ix_research_result_session_created", "session_id", "created_at"),
        Index("ix_research_result_baseline", "baseline_result_id"),
        Index("ix_research_result_is_reviewed", "session_id", "is_reviewed"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("research_jobs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Future Delta Briefing: Baseline reference against which this result was compared
    baseline_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("research_results.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Research Execution Status (stored separately from individual claim verification statuses)
    research_status: Mapped[ResearchResultStatus] = mapped_column(
        SQLEnum(ResearchResultStatus, native_enum=False, length=50),
        default=ResearchResultStatus.COMPLETED,
        index=True,
        nullable=False,
    )

    # Synthesized Briefing Content
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_developments: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    sources: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    claims_and_evidence: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    coverage_report: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    talking_points_analysis: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    # Delta Briefing Fields
    is_delta: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    delta_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Raw Engine Output for Full Auditability & Reproducibility
    raw_intelligence: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Review State
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Relationships
    session: Mapped["ResearchSession"] = relationship(
        "ResearchSession",
        back_populates="results",
        foreign_keys=[session_id],
    )
    job: Mapped[Optional["ResearchJob"]] = relationship("ResearchJob", back_populates="result")
    baseline_result: Mapped[Optional["ResearchResult"]] = relationship(
        "ResearchResult",
        remote_side="ResearchResult.id",
        foreign_keys=[baseline_result_id],
    )
    reviewed_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by_user_id],
    )

    def __repr__(self) -> str:
        return f"<ResearchResult id={self.id} session={self.session_id} status={self.research_status} is_delta={self.is_delta}>"

