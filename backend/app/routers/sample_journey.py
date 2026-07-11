"""
Sample journey API — sample-scoped process progress (Decision #7).

GET /v1/samples/{sample_id}/journey
Readable by anyone who can access the sample (not only experiment:manage).
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.services.eln_process_service import ELNProcessService
from app.schemas.eln_process import SampleJourneyResponse
from models.user import User
from models.sample import Sample

router = APIRouter(prefix="/samples", tags=["sample-journey"])


@router.get("/{sample_id}/journey", response_model=SampleJourneyResponse)
def get_sample_journey(
    sample_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Process progress for a sample.

    Visibility: if the sample is visible under RLS/session for this user,
    return process journey. Manage actions are not exposed here.
    """
    # Existence + RLS: query sample in current session
    sample = db.query(Sample).filter(Sample.id == sample_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found or not accessible",
        )
    service = ELNProcessService(db, current_user=current_user)
    return service.sample_journey(sample_id)
