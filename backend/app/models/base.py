"""Base model mixin and timestamp helpers."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin providing created_at and updated_at UTC timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Mixin providing standard UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

