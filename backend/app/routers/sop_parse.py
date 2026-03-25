"""
SOP Parse Jobs API — /api/v1/sop-parse

Routes:
    POST   /sop-parse              — upload SOP + instrument file, create job
    GET    /sop-parse/{id}         — poll job status / retrieve result
    POST   /sop-parse/{id}/apply   — apply completed job → create template/parser/worklist records
"""
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.rbac import require_experiment_manage
from app.services.sop_parse_service import SOPParseService
from app.schemas.flexible_experiment import SopParseJobRead, SopApplyResponse
from models.user import User

router = APIRouter(prefix="/sop-parse", tags=["sop-parse"])


def _sop_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> SOPParseService:
    return SOPParseService(db, current_user=current_user)


@router.post("", response_model=SopParseJobRead, status_code=202)
async def create_parse_job(
    background_tasks: BackgroundTasks,
    sop_file: UploadFile = File(..., description="SOP document (text or PDF)"),
    instrument_file: UploadFile = File(..., description="Example instrument output CSV"),
    service: SOPParseService = Depends(_sop_service),
):
    """
    Upload SOP + example instrument file; kick off Claude extraction as background task.

    Returns 202 Accepted with job_id immediately.
    Poll GET /sop-parse/{id} to check status.
    """
    sop_bytes = await sop_file.read()
    instrument_bytes = await instrument_file.read()

    # Decode file bytes to text (UTF-8 with BOM stripping)
    sop_text = sop_bytes.decode("utf-8-sig", errors="replace")
    instrument_text = instrument_bytes.decode("utf-8-sig", errors="replace")

    job = service.create_job(
        sop_filename=sop_file.filename,
        instrument_filename=instrument_file.filename,
    )

    background_tasks.add_task(
        SOPParseService.run_extraction_background,
        job_id=job.id,
        sop_text=sop_text,
        instrument_text=instrument_text,
    )

    return SopParseJobRead.model_validate(job)


@router.get("/{job_id}", response_model=SopParseJobRead)
def get_parse_job(
    job_id: UUID,
    service: SOPParseService = Depends(_sop_service),
):
    """Poll parse job status. When status='complete', result contains the extracted config."""
    job = service.get_job(job_id)
    return SopParseJobRead.model_validate(job)


@router.post("/{job_id}/apply", response_model=SopApplyResponse, status_code=201)
def apply_parse_job(
    job_id: UUID,
    service: SOPParseService = Depends(_sop_service),
):
    """
    Apply a completed SOP parse job: creates ExperimentTemplate, InstrumentParser,
    and (if worklist steps present) RobotWorklistConfig from the AI-extracted result.

    Idempotency: returns 409 if the job has already been applied.
    Precondition: job status must be 'complete'; returns 422 otherwise.
    """
    result = service.apply_job(job_id)
    return SopApplyResponse(**result)
