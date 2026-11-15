"""Research worker job REST endpoints."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, verify_session_access
from app.core.exceptions import NotFoundException
from app.models.research_job import ResearchJob
from app.models.user import User
from app.schemas.job import ResearchJobResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "/{job_id}",
    response_model=ResearchJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get execution status and progress for a research job",
)
def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchJobResponse:
    """Retrieve durable background worker job status, attempt count, and error information."""
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    if not job:
        raise NotFoundException(message="Research job not found.", code="JOB_NOT_FOUND")

    # Enforce authorization via the job's research session
    if job.session:
        verify_session_access(job.session, current_user, db)

    return ResearchJobResponse.model_validate(job)

