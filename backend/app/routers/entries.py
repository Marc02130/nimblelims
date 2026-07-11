"""
Experiment Entries API — Phase 2

  /v1/experiments/{experiment_id}/entries
  /v1/entries/{entry_id}
  /v1/entries/{entry_id}/values
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.rbac import require_experiment_manage
from app.services.entry_service import EntryService
from app.schemas.entry import (
    EntryCreate,
    EntryUpdate,
    EntryRead,
    EntryListResponse,
    EntryFieldValueUpsert,
    EntryFieldValueBulkUpsert,
    EntryFieldValueRead,
    InstantiateEntriesRequest,
)
from models.user import User

router = APIRouter(tags=["entries"])


def get_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> EntryService:
    return EntryService(db, current_user=current_user)


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
    # Ensure path and body agree
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
    """Upsert field values; applies allowlisted sample write-back when configured."""
    values = service.upsert_values(entry_id, data.values)
    return [EntryFieldValueRead.model_validate(v) for v in values]


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
