"""
ELN Process Definitions API — /api/v1/eln-process-definitions

Phase 3 Decision #6: first-class reusable process definitions.
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.rbac import require_experiment_manage
from app.services.eln_process_service import ELNProcessService
from app.schemas.eln_process_definition import (
    ELNProcessDefinitionCreate,
    ELNProcessDefinitionUpdate,
    ELNProcessDefinitionRead,
    ELNProcessDefinitionListEntry,
    ELNProcessDefinitionListResponse,
    ELNProcessDefinitionStepCreate,
    InstantiateProcessFromDefinitionRequest,
)
from app.schemas.eln_process import ELNProcessRead
from models.user import User

router = APIRouter(
    prefix="/eln-process-definitions",
    tags=["eln-process-definitions"],
)


def get_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> ELNProcessService:
    return ELNProcessService(db, current_user=current_user)


@router.get("", response_model=ELNProcessDefinitionListResponse)
def list_definitions(
    active: Optional[bool] = Query(True),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=500),
    service: ELNProcessService = Depends(get_service),
):
    items, total = service.list_definitions(active=active, page=page, size=size)
    pages = (total + size - 1) // size if size else 0
    entries = [
        ELNProcessDefinitionListEntry(
            id=d.id,
            name=d.name,
            description=d.description,
            active=d.active,
            created_at=d.created_at,
            step_count=service.repo.count_definition_steps(d.id),
        )
        for d in items
    ]
    return ELNProcessDefinitionListResponse(
        definitions=entries,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post("", response_model=ELNProcessDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_definition(
    data: ELNProcessDefinitionCreate,
    service: ELNProcessService = Depends(get_service),
):
    return ELNProcessDefinitionRead.model_validate(service.create_definition(data))


@router.get("/{definition_id}", response_model=ELNProcessDefinitionRead)
def get_definition(
    definition_id: UUID,
    service: ELNProcessService = Depends(get_service),
):
    return ELNProcessDefinitionRead.model_validate(service.get_definition(definition_id))


@router.patch("/{definition_id}", response_model=ELNProcessDefinitionRead)
def update_definition(
    definition_id: UUID,
    data: ELNProcessDefinitionUpdate,
    service: ELNProcessService = Depends(get_service),
):
    return ELNProcessDefinitionRead.model_validate(
        service.update_definition(definition_id, data)
    )


@router.post(
    "/{definition_id}/steps",
    response_model=ELNProcessDefinitionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_definition_step(
    definition_id: UUID,
    data: ELNProcessDefinitionStepCreate,
    service: ELNProcessService = Depends(get_service),
):
    return ELNProcessDefinitionRead.model_validate(
        service.add_definition_step(definition_id, data)
    )


@router.post(
    "/{definition_id}/instantiate",
    response_model=ELNProcessRead,
    status_code=status.HTTP_201_CREATED,
)
def instantiate_process(
    definition_id: UUID,
    data: Optional[InstantiateProcessFromDefinitionRequest] = None,
    service: ELNProcessService = Depends(get_service),
):
    """Start a process instance from this definition (snapshot steps)."""
    p = service.instantiate_from_definition(
        definition_id,
        data or InstantiateProcessFromDefinitionRequest(),
    )
    return ELNProcessRead.model_validate(p)
