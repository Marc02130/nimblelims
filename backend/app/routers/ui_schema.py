"""Admin Schema API: Tables / Columns / Layouts / Privileges."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.rbac import require_layout_edit, require_schema_edit, require_schema_or_layout
from app.core.security import get_current_user, get_user_permissions
from app.database import get_db
from app.schemas.ui_schema import (
    ConfirmBody,
    PrivilegeIn,
    RuntimeColumn,
    SchemaColumnCreate,
    SchemaColumnRead,
    SchemaLayoutPut,
    SchemaLayoutRead,
    SchemaPrivilegeRead,
    SchemaTableCreate,
    SchemaTableRead,
)
from app.services.ui_schema_service import UiSchemaService
from models.user import User

router = APIRouter(prefix="/schema", tags=["schema"])


def _svc(db: Session, user: User) -> UiSchemaService:
    return UiSchemaService(db, user)


@router.get("/tables", response_model=List[SchemaTableRead])
def list_tables(
    user: User = Depends(require_schema_or_layout),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    return [SchemaTableRead(**svc.table_read(t)) for t in svc.list_tables()]


@router.post("/tables", response_model=SchemaTableRead, status_code=status.HTTP_201_CREATED)
def create_table(
    body: SchemaTableCreate,
    user: User = Depends(require_schema_edit),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    row = svc.create_table(body.display_name, body.physical_name)
    return SchemaTableRead(**svc.table_read(row))


@router.post("/tables/{table_id}/deprecate", response_model=SchemaTableRead)
def deprecate_table(
    table_id: UUID,
    user: User = Depends(require_schema_edit),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    row = svc.deprecate_table(table_id)
    return SchemaTableRead(**svc.table_read(row))


@router.post("/tables/{table_id}/drop", status_code=status.HTTP_204_NO_CONTENT)
def drop_table(
    table_id: UUID,
    body: ConfirmBody,
    user: User = Depends(require_schema_edit),
    db: Session = Depends(get_db),
):
    _svc(db, user).drop_table(table_id, body.confirm)
    return None


@router.get("/columns", response_model=List[SchemaColumnRead])
def list_columns(
    table_id: UUID = Query(...),
    user: User = Depends(require_schema_or_layout),
    db: Session = Depends(get_db),
):
    return _svc(db, user).list_columns(table_id)


@router.post("/columns", response_model=SchemaColumnRead, status_code=status.HTTP_201_CREATED)
def add_column(
    body: SchemaColumnCreate,
    user: User = Depends(require_schema_edit),
    db: Session = Depends(get_db),
):
    return _svc(db, user).add_column(
        table_id=body.table_id,
        display_name=body.display_name,
        data_type=body.data_type,
        nullable=body.nullable,
        list_id=body.list_id,
        sop_hint=body.sop_hint,
        sort_order=body.sort_order,
        physical_name=body.physical_name,
    )


@router.post("/columns/{column_id}/deprecate", response_model=SchemaColumnRead)
def deprecate_column(
    column_id: UUID,
    user: User = Depends(require_schema_edit),
    db: Session = Depends(get_db),
):
    return _svc(db, user).deprecate_column(column_id)


@router.post("/columns/{column_id}/drop", status_code=status.HTTP_204_NO_CONTENT)
def drop_column(
    column_id: UUID,
    body: ConfirmBody,
    user: User = Depends(require_schema_edit),
    db: Session = Depends(get_db),
):
    _svc(db, user).drop_column(column_id, body.confirm)
    return None


@router.get("/layouts", response_model=Optional[SchemaLayoutRead])
def get_layout(
    role_id: UUID = Query(...),
    screen_key: str = Query(...),
    user: User = Depends(require_schema_or_layout),
    db: Session = Depends(get_db),
):
    svc = _svc(db, user)
    layout = svc.get_layout(role_id, screen_key)
    if not layout:
        return None
    return SchemaLayoutRead(**svc.layout_read(layout))


@router.put("/layouts", response_model=SchemaLayoutRead)
def put_layout(
    body: SchemaLayoutPut,
    user: User = Depends(require_schema_or_layout),
    db: Session = Depends(get_db),
):
    perms = get_user_permissions(user, db)
    if "layout:edit" not in perms and "schema:edit" not in perms:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Permission 'layout:edit' required")
    svc = _svc(db, user)
    layout = svc.put_layout(body.role_id, body.screen_key, [f.model_dump() for f in body.fields])
    return SchemaLayoutRead(**svc.layout_read(layout))


@router.get("/privileges", response_model=List[SchemaPrivilegeRead])
def list_privileges(
    role_id: Optional[UUID] = Query(None),
    table_id: Optional[UUID] = Query(None),
    user: User = Depends(require_schema_edit),
    db: Session = Depends(get_db),
):
    return _svc(db, user).list_privileges(role_id, table_id)


@router.put("/privileges", response_model=List[SchemaPrivilegeRead])
def put_privileges(
    body: List[PrivilegeIn],
    user: User = Depends(require_schema_edit),
    db: Session = Depends(get_db),
):
    return _svc(db, user).put_privileges([p.model_dump() for p in body])


@router.get("/runtime", response_model=List[RuntimeColumn])
def runtime(
    screen_key: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _svc(db, user).runtime_columns(screen_key)
