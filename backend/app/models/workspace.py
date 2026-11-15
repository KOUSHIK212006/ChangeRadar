"""Workspace models for team collaboration and shared research isolation."""

import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Enum as SQLEnum, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import WorkspaceRole

if TYPE_CHECKING:
    from app.models.research_session import ResearchSession
    from app.models.user import User


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Shared organization/team space for group research."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="created_workspaces",
        foreign_keys=[created_by_user_id],
    )
    sessions: Mapped[List["ResearchSession"]] = relationship(
        "ResearchSession",
        back_populates="workspace",
        cascade="all, delete-orphan",
        foreign_keys="[ResearchSession.workspace_id]",
    )
    members: Mapped[List["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} slug={self.slug}>"


class WorkspaceMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Associates a User with a Workspace and assigns an authorization role."""

    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[WorkspaceRole] = mapped_column(
        SQLEnum(WorkspaceRole, native_enum=False, length=50),
        default=WorkspaceRole.MEMBER,
        nullable=False,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="workspace_memberships")

    def __repr__(self) -> str:
        return f"<WorkspaceMembership workspace={self.workspace_id} user={self.user_id} role={self.role}>"

