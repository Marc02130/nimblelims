"""Sample type transition catalog.

GET: authenticated (RLS + client_id). Inactive rows only for config:edit.
POST/PATCH/DELETE: config:edit (S3).
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.rbac import require_config_edit
from app.core.security import get_current_user, get_user_permissions
from app.database import get_db
from app.schemas.sample_type_transition import (
    SampleTypeTransitionCreate,
    SampleTypeTransitionRead,
    SampleTypeTransitionUpdate,
)
from app.services.sample_type_transition_service import SampleTypeTransitionService
from models.user import User

router = APIRouter(
    prefix="/sample-type-transitions",
    tags=["sample-type-transitions"],
)


def _svc(db: Session, user: User) -> SampleTypeTransitionService:
    return SampleTypeTransitionService(db, user)


@router.get("", response_model=List[SampleTypeTransitionRead])
def list_transitions(
    operation: Optional[str] = Query(None, pattern="^(aliquot|pool)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    include_inactive = "config:edit" in get_user_permissions(current_user, db)
    return _svc(db, current_user).list(
        operation=operation, include_inactive=include_inactive
    )


@router.post(
    "",
    response_model=SampleTypeTransitionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_transition(
    data: SampleTypeTransitionCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    return _svc(db, current_user).create(data)


@router.patch("/{row_id}", response_model=SampleTypeTransitionRead)
def update_transition(
    row_id: UUID,
    data: SampleTypeTransitionUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    return _svc(db, current_user).update(row_id, data)


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transition(
    row_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    _svc(db, current_user).delete(row_id)
    return None
