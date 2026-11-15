"""Database engine, session factory, and connection health management."""

import logging
from typing import Generator, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 base class for all relational models."""
    pass


def create_db_engine(database_url: str):
    """Create SQLAlchemy engine with appropriate dialect arguments."""
    is_sqlite = database_url.startswith("sqlite")

    if is_sqlite:
        return create_engine(
            database_url,
            echo=settings.DATABASE_ECHO,
            connect_args={"check_same_thread": False},
        )
    else:
        return create_engine(
            database_url,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
        )


# Global database engine and session factory
engine = create_db_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Tuple[bool, Optional[str]]:
    """Test database connectivity with a lightweight probe."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        logger.warning(f"Database connection probe failed: {exc}")
        return False, str(exc)

