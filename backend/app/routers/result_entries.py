"""Result-entry rows on a LIMS run (calculations S6).

GET lists the rows of the run's ``Results`` entry. PATCH lets a user type raw
(and raw units) or overwrite reported. calculated_result is never accepted.
"""
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.rbac import require_result_enter, require_result_read, validate_client_access
from app.database import get_db
from app.schemas.result_entry import ResultEntryListResponse, ResultEntryRead
from app.services.result_entry_service import ResultEntryService
from models.entry import ResultEntry
from models.flexible_experiment import LimsRun
from models.user import User

router = APIRouter(prefix="/lims-runs", tags=["result-entries"])


def result_entry_read(row: ResultEntry) -> ResultEntryRead:
    test = row.test
    return ResultEntryRead(
        id=row.id,
        entry_id=row.entry_id,
        lims_run_id=test.lims_run_id,
        test_id=row.test_id,
        sample_id=test.sample_id,
        sample_name=test.sample.name if test.sample else None,
        analyte_id=row.analyte_id,
        analyte_name=row.analyte.name if row.analyte else None,
        replicate=row.replicate,
        raw_result=row.raw_result,
        raw_units=row.raw_units,
        raw_origin=row.raw_origin,
        final_units_id=row.final_units_id,
        calculated_result=row.calculated_result,
        reported_result=row.reported_result,
        qualifiers=row.qualifiers,
        knocked_out=bool(row.knocked_out),
        knocked_out_by=row.knocked_out_by,
        knocked_out_at=row.knocked_out_at,
        display_order=row.display_order,
        modified_at=row.modified_at,
        modified_by=row.modified_by,
    )


def _get_run(db: Session, run_id: UUID) -> LimsRun:
    run = db.query(LimsRun).filter(LimsRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LIMS run not found")
    return run


@router.get("/{run_id}/result-entries", response_model=ResultEntryListResponse)
def list_result_entries(
    run_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    current_user: User = Depends(require_result_read),
    db: Session = Depends(get_db),
) -> ResultEntryListResponse:
    """Rows of the run's Results entry, by sample, display order, analyte, replicate."""
    _get_run(db, run_id)
    rows, total = ResultEntryService(db, current_user.id).list_rows(run_id, page, size)
    return ResultEntryListResponse(
        result_entries=[result_entry_read(row) for row in rows],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.patch("/{run_id}/result-entries/{row_id}", response_model=ResultEntryRead)
def update_result_entry(
    run_id: UUID,
    row_id: UUID,
    body: Dict[str, Any] = Body(...),
    current_user: User = Depends(require_result_enter),
    db: Session = Depends(get_db),
) -> ResultEntryRead:
    """Type raw, set raw units, or overwrite reported.

    Allowed fields: raw_result, raw_units, reported_result. Refused with 400:
    calculated_result (calculated_locked), any other field (invalid_input),
    raw on a row whose raw came from a file (raw_uploaded), reported before a
    calculated result exists (reported_before_calculation), and any edit on a
    published run (run_published).
    """
    _get_run(db, run_id)
    service = ResultEntryService(db, current_user.id)
    row = service.get_row(run_id, row_id)
    validate_client_access(current_user, row.test.sample.project.client_id)
    service.apply_user_edit(row, body)
    db.commit()
    db.refresh(row)
    return result_entry_read(row)
