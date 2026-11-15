"""Authentication REST endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Create a new user account and return an initial JWT access token."""
    existing_user = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing_user:
        raise ConflictException(
            message="A user with this email address already exists.",
            code="USER_ALREADY_EXISTS",
        )

    user = User(
        email=payload.email.lower(),
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    expires_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(subject=str(user.id))

    return AuthResponse(
        user=UserResponse.model_validate(user),
        token=TokenResponse(
            access_token=access_token,
            expires_in=expires_seconds,
        ),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate existing user and return access token",
)
def login(
    payload: UserLoginRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Authenticate email and password, returning JWT access token."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedException(
            message="Invalid email or password.",
            code="INVALID_CREDENTIALS",
        )

    if not user.is_active:
        raise ForbiddenException(
            message="User account is deactivated.",
            code="USER_INACTIVE",
        )

    expires_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(subject=str(user.id))

    return AuthResponse(
        user=UserResponse.model_validate(user),
        token=TokenResponse(
            access_token=access_token,
            expires_in=expires_seconds,
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return profile metadata for the authenticated user."""
    return UserResponse.model_validate(current_user)

