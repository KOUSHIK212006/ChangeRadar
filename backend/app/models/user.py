"""User model for authentication, identity, and personal research ownership."""

from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.research_session import ResearchSession
    from app.models.workspace import Workspace, WorkspaceMembership


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account entity."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    personal_sessions: Mapped[List["ResearchSession"]] = relationship(
        "ResearchSession",
        back_populates="owner",
        cascade="all, delete-orphan",
        foreign_keys="[ResearchSession.owner_user_id]",
    )
    created_workspaces: Mapped[List["Workspace"]] = relationship(
        "Workspace",
        back_populates="creator",
        foreign_keys="[Workspace.created_by_user_id]",
    )
    workspace_memberships: Mapped[List["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"

