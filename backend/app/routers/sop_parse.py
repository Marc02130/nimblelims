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

from app.database import release_transaction

router = APIRouter(prefix="/sop-parse", tags=["sop-parse"])


def _sop_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> SOPParseService:
    return SOPParseService(db, current_user=current_user)


@router.post("", response_model=SopParseJobRead, status_code=202)
def create_parse_job(
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
    from app.core.uploads import read_upload_capped

    sop_bytes = read_upload_capped(sop_file, field_name=sop_file.filename or "sop_file")
    instrument_bytes = read_upload_capped(
        instrument_file, field_name=instrument_file.filename or "instrument_file"
    )

    # Same extraction as the configuring agent: PDF/DOCX text, refuse binary
    # and text-less files here instead of completing with an empty template.
    from app.services.configuring_agent_extract import NoTextInFile, UnsupportedFileType, file_text

    def _text(data: bytes, upload: UploadFile, label: str) -> str:
        try:
            return file_text(data, upload.filename or "")
        except UnsupportedFileType as exc:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"{label}: {exc}") from exc
        except NoTextInFile as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{label}: {exc}") from exc

    sop_text = _text(sop_bytes, sop_file, "SOP file")
    instrument_text = _text(instrument_bytes, instrument_file, "Instrument file")

    job = service.create_job(
        sop_filename=sop_file.filename,
        instrument_filename=instrument_file.filename,
    )

    background_tasks.add_task(
        SOPParseService.run_extraction_background,
        job_id=job.id,
        sop_text=sop_text,
        instrument_text=instrument_text,
        # RLS context of this request, for the task's own sessions.
        user_id=service.current_user.id if service.current_user else None,
        client_id=service.current_user.client_id if service.current_user else None,
    )

    out = SopParseJobRead.model_validate(job)
    # Request session cleanup waits for the background extraction (up to 120 s);
    # don't leave this read idle in a transaction meanwhile.
    release_transaction(service.db)
    return out


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
