"""Asked-for P1 API: /v1/asked-for."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.rbac import require_sample_read, require_test_assign
from app.database import get_db
from app.schemas.asked_for import AskedForCreate, AskedForListResponse, AskedForRead
from app.services.asked_for_service import AskedForService
from models.user import User

router = APIRouter(prefix="/asked-for", tags=["asked-for"])


def _svc(db: Session, user: User) -> AskedForService:
    return AskedForService(db, current_user=user)


@router.post("", response_model=AskedForListResponse, status_code=status.HTTP_201_CREATED)
def create_asked_for(
    body: AskedForCreate,
    user: User = Depends(require_test_assign),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    rows = svc.create(
        sample_ids=body.sample_ids,
        analysis_id=body.analysis_id,
        tat_days=body.tat_days,
        params=body.params,
    )
    items = [AskedForRead(**svc.to_read(r)) for r in rows]
    return AskedForListResponse(items=items, count=len(items))


@router.get("", response_model=AskedForListResponse)
def list_asked_for(
    sample_id: Optional[UUID] = Query(None),
    project_id: Optional[UUID] = Query(None),
    analysis_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    user: User = Depends(require_sample_read),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    rows = svc.list(
        sample_id=sample_id,
        project_id=project_id,
        analysis_id=analysis_id,
        status_filter=status_filter,
    )
    items = [AskedForRead(**svc.to_read(r)) for r in rows]
    return AskedForListResponse(items=items, count=len(items))


@router.get("/{asked_for_id}", response_model=AskedForRead)
def get_asked_for(
    asked_for_id: UUID,
    user: User = Depends(require_sample_read),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    return AskedForRead(**svc.to_read(svc.get(asked_for_id)))


@router.post("/{asked_for_id}/cancel", response_model=AskedForRead)
def cancel_asked_for(
    asked_for_id: UUID,
    user: User = Depends(require_test_assign),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    return AskedForRead(**svc.to_read(svc.cancel(asked_for_id)))
