"""ResearchJob entity representing the durable worker execution lifecycle."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ResearchJobStatus

if TYPE_CHECKING:
    from app.models.research_result import ResearchResult
    from app.models.research_session import ResearchSession


class ResearchJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Durable job execution record tracked and processed by the worker queue."""

    __tablename__ = "research_jobs"
    __table_args__ = (
        Index("ix_research_job_status_next_retry", "status", "next_retry_at"),
        Index("ix_research_job_session_status", "session_id", "status"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    status: Mapped[ResearchJobStatus] = mapped_column(
        SQLEnum(ResearchJobStatus, native_enum=False, length=50),
        default=ResearchJobStatus.PENDING,
        index=True,
        nullable=False,
    )

    stage: Mapped[Optional[str]] = mapped_column(
        String(100),
        default="queued",
        nullable=True,
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Worker Lease and Heartbeat Tracking
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Errors & Diagnostics
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Execution Parameters Snapshot
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    session: Mapped["ResearchSession"] = relationship("ResearchSession", back_populates="jobs")
    result: Mapped[Optional["ResearchResult"]] = relationship(
        "ResearchResult",
        back_populates="job",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<ResearchJob id={self.id} session={self.session_id} status={self.status} attempts={self.attempt_count}>"

