"""Domain enumeration types for database models and contracts."""

import enum


class OwnershipScope(str, enum.Enum):
    """Ownership scope for research sessions."""
    PERSONAL = "PERSONAL"
    WORKSPACE = "WORKSPACE"


class SessionStatus(str, enum.Enum):
    """Operational status of a research session."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ResearchJobStatus(str, enum.Enum):
    """Execution status of a research worker job."""
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    RETRY_WAIT = "RETRY_WAIT"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ResearchResultStatus(str, enum.Enum):
    """Overall outcome status of a synthesized research run."""
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NO_NEW_DEVELOPMENTS = "NO_NEW_DEVELOPMENTS"


class EvidenceVerificationStatus(str, enum.Enum):
    """Status of factual claims relative to available evidence."""
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT = "INSUFFICIENT"
    OUTDATED = "OUTDATED"
    UNVERIFIABLE = "UNVERIFIABLE"


class WorkspaceRole(str, enum.Enum):
    """Roles for workspace memberships."""
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
