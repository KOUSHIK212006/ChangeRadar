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


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Validate JWT bearer token if provided; return None if unauthenticated."""
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_uuid = uuid.UUID(user_id_str)
        user = db.query(User).filter(User.id == user_uuid).first()
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None


DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


def verify_session_access(session: ResearchSession, user: Optional[User], db: Session) -> None:
    """Verify that user is authorized to view or mutate the given research session."""
    if session.scope == OwnershipScope.PERSONAL:
        if session.owner_user_id is not None and session.owner_user_id != DEMO_USER_ID:
            if not user or session.owner_user_id != user.id:
                raise NotFoundException(
                    message="Research session not found.",
                    code="SESSION_NOT_FOUND",
                )
    elif session.scope == OwnershipScope.WORKSPACE:
        if session.workspace_id is not None and session.workspace_id != DEMO_WORKSPACE_ID:
            if not user:
                raise NotFoundException(
                    message="Research session not found.",
                    code="SESSION_NOT_FOUND",
                )
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
    "get_current_user_optional",
    "verify_session_access",
    "Session",
    "User",
]
