"""Shared FastAPI endpoint dependencies: database sessions, auth, and permissions."""

import uuid
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException
from app.core.security import decode_access_token
from app.models.enums import OwnershipScope
from app.models.research_session import ResearchSession
from app.models.user import User
from app.models.workspace import WorkspaceMembership

# Bearer token extractor (auto_error=False allows returning custom AppException)
security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate JWT bearer token and return the authenticated User."""
    if not credentials or not credentials.credentials:
        raise UnauthorizedException(
            message="Authentication credentials were not provided.",
            code="NOT_AUTHENTICATED",
        )

    payload = decode_access_token(credentials.credentials)
    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(
            message="Token payload is missing subject claim.",
            code="INVALID_TOKEN",
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(
            message="Token subject is not a valid UUID.",
            code="INVALID_TOKEN",
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise UnauthorizedException(
            message="User account associated with this token was not found.",
            code="USER_NOT_FOUND",
        )

    if not user.is_active:
        raise ForbiddenException(
            message="User account is deactivated.",
            code="USER_INACTIVE",
        )

    return user


def verify_session_access(session: ResearchSession, user: User, db: Session) -> None:
    """Verify that user is authorized to view or mutate the given research session."""
    if session.scope == OwnershipScope.PERSONAL:
        if session.owner_user_id != user.id:
            raise NotFoundException(
                message="Research session not found.",
                code="SESSION_NOT_FOUND",
            )
    elif session.scope == OwnershipScope.WORKSPACE:
        # Check that user is an active member of this workspace
        membership = (
            db.query(WorkspaceMembership)
            .filter(
                WorkspaceMembership.workspace_id == session.workspace_id,
                WorkspaceMembership.user_id == user.id,
            )
            .first()
        )
        if not membership:
            raise NotFoundException(
                message="Research session not found.",
                code="SESSION_NOT_FOUND",
            )


__all__ = [
    "get_db",
    "get_current_user",
    "verify_session_access",
    "Session",
    "User",
]
