"""
Experiment Entries API (P0 foundation)

  /v1/experiments/{experiment_id}/entries
  /v1/entries/{entry_id}
  /v1/entries/{entry_id}/values   — save (no Sample write-back)
  /v1/entries/{entry_id}/submit   — complete + write-back
  /v1/entries/{entry_id}/grid     — wide UI
  /v1/entries/{entry_id}/export   — long report
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
import csv
import io

from app.database import get_db
from app.core.rbac import require_experiment_manage
from app.services.entry_service import EntryService
from app.services.aliquot_plan_service import AliquotPlanService
from app.schemas.entry import (
    EntryCreate,
    EntryUpdate,
    EntryRead,
    EntryListResponse,
    EntryFieldValueBulkUpsert,
    EntryFieldValueRead,
    InstantiateEntriesRequest,
    EntryGridResponse,
    EntryExportResponse,
    EntrySubmitResponse,
)
from app.schemas.aliquot_plan import (
    AliquotPlanSaveRequest,
    AliquotPlanSaveResponse,
    AliquotExecuteRequest,
    AliquotExecuteResponse,
    AliquotMethodListResponse,
)
from models.user import User
from sqlalchemy.orm import Session

router = APIRouter(tags=["entries"])


def get_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> EntryService:
    return EntryService(db, current_user=current_user)


def get_aliquot_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> AliquotPlanService:
    return AliquotPlanService(db, current_user=current_user)


@router.get(
    "/experiments/{experiment_id}/entries",
    response_model=EntryListResponse,
)
def list_entries(
    experiment_id: UUID,
    active: Optional[bool] = Query(True),
    include_values: bool = Query(False),
    service: EntryService = Depends(get_service),
):
    items = service.list_entries(
        experiment_id,
        active=active,
        include_values=include_values,
    )
    return EntryListResponse(
        entries=[EntryRead.model_validate(e) for e in items],
        total=len(items),
    )


@router.post(
    "/experiments/{experiment_id}/entries",
    response_model=EntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_entry(
    experiment_id: UUID,
    data: EntryCreate,
    service: EntryService = Depends(get_service),
):
    payload = data.model_copy(update={'experiment_id': experiment_id})
    entry = service.create_entry(payload)
    return EntryRead.model_validate(entry)


@router.post(
    "/experiments/{experiment_id}/entries/instantiate",
    response_model=EntryListResponse,
    status_code=status.HTTP_201_CREATED,
)
def instantiate_entries(
    experiment_id: UUID,
    data: Optional[InstantiateEntriesRequest] = None,
    service: EntryService = Depends(get_service),
):
    """Create entries from the experiment template's template_definition['entries']."""
    items = service.instantiate_from_template(
        experiment_id,
        data or InstantiateEntriesRequest(),
    )
    return EntryListResponse(
        entries=[EntryRead.model_validate(e) for e in items],
        total=len(items),
    )


@router.get(
    "/entries/aliquot-methods",
    response_model=AliquotMethodListResponse,
)
def list_aliquot_methods(
    service: AliquotPlanService = Depends(get_aliquot_service),
):
    """Return full v1 aliquot/pool method matrix (Lab Ops L9)."""
    return AliquotMethodListResponse(methods=service.list_methods())


@router.get("/entries/{entry_id}", response_model=EntryRead)
def get_entry(
    entry_id: UUID,
    service: EntryService = Depends(get_service),
):
    return EntryRead.model_validate(service.get_entry(entry_id))


@router.patch("/entries/{entry_id}", response_model=EntryRead)
def update_entry(
    entry_id: UUID,
    data: EntryUpdate,
    service: EntryService = Depends(get_service),
):
    return EntryRead.model_validate(service.update_entry(entry_id, data))


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: UUID,
    service: EntryService = Depends(get_service),
):
    service.delete_entry(entry_id)
    return None


@router.put(
    "/entries/{entry_id}/values",
    response_model=List[EntryFieldValueRead],
)
def upsert_values(
    entry_id: UUID,
    data: EntryFieldValueBulkUpsert,
    service: EntryService = Depends(get_service),
):
    """Save field values only — does not write back to Sample (use submit)."""
    values = service.upsert_values(entry_id, data.values, apply_write_back=False)
    return [EntryFieldValueRead.model_validate(v) for v in values]


@router.post(
    "/entries/{entry_id}/submit",
    response_model=EntrySubmitResponse,
)
def submit_entry(
    entry_id: UUID,
    service: EntryService = Depends(get_service),
):
    """Mark entry submitted and apply Sample write-back for mapped columns."""
    entry, n = service.submit_entry(entry_id)
    return EntrySubmitResponse(
        entry=EntryRead.model_validate(entry),
        write_backs_applied=n,
    )


@router.get(
    "/entries/{entry_id}/grid",
    response_model=EntryGridResponse,
)
def get_entry_grid(
    entry_id: UUID,
    service: EntryService = Depends(get_service),
):
    """Wide grid for UI capture (columns + rows[].cells)."""
    return service.get_grid(entry_id)


@router.get(
    "/entries/{entry_id}/export",
    response_model=EntryExportResponse,
)
def export_entry(
    entry_id: UUID,
    format: str = Query("json", pattern="^(json|csv)$"),
    service: EntryService = Depends(get_service),
):
    """Long-form export for reports (one record per cell)."""
    result = service.export_entry(entry_id)
    if format == "csv":
        buf = io.StringIO()
        fieldnames = [
            "experiment_id", "experiment_name", "entry_id", "entry_name", "entry_type",
            "sample_id", "client_sample_id", "field_definition_id", "field_name",
            "field_display_name", "column_kind", "data_type", "value_text", "value_number",
            "value_list_entry_id", "value_list_entry_name", "value_date", "value_boolean",
            "display_value", "modified_at", "modified_by",
        ]
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in result.rows:
            d = row.model_dump()
            for k, v in list(d.items()):
                if v is not None and not isinstance(v, (str, int, float, bool)):
                    d[k] = str(v)
            writer.writerow({k: d.get(k) for k in fieldnames})
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="entry_{entry_id}_export.csv"'
            },
        )
    return result


@router.get(
    "/entries/{entry_id}/values",
    response_model=List[EntryFieldValueRead],
)
def list_values(
    entry_id: UUID,
    sample_id: Optional[UUID] = Query(None),
    service: EntryService = Depends(get_service),
):
    service.get_entry(entry_id)
    rows = service.repo.list_values(entry_id, sample_id=sample_id)
    return [EntryFieldValueRead.model_validate(v) for v in rows]


# ---------- Aliquot / pool plan + execute (all methods) ----------


@router.get(
    "/entries/{entry_id}/aliquot-plan",
    response_model=AliquotPlanSaveResponse,
)
def get_aliquot_plan(
    entry_id: UUID,
    service: AliquotPlanService = Depends(get_aliquot_service),
):
    return service.get_plan(entry_id)


@router.put(
    "/entries/{entry_id}/aliquot-plan",
    response_model=AliquotPlanSaveResponse,
)
def save_aliquot_plan(
    entry_id: UUID,
    data: AliquotPlanSaveRequest,
    service: AliquotPlanService = Depends(get_aliquot_service),
):
    """Save plan lines on entry.config.plan_lines (method inputs validated)."""
    return service.save_plan(entry_id, data)


@router.post(
    "/entries/{entry_id}/execute",
    response_model=AliquotExecuteResponse,
)
def execute_aliquot_plan(
    entry_id: UUID,
    data: Optional[AliquotExecuteRequest] = None,
    service: AliquotPlanService = Depends(get_aliquot_service),
):
    """
    Execute aliquot/pool plan: reduce source contents amount; create dest samples
    and contents. Supports dry_run. Amount = mass/count only (volume converted).
    """
    return service.execute(entry_id, data or AliquotExecuteRequest())
