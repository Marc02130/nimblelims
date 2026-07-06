"""
FieldDefinitions router for NimbleLIMS (new modeled fields system)
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from models.field_definition import FieldDefinition
from models.list import List as ListModel
from app.schemas.field_definition import (
    FieldDefinitionCreate,
    FieldDefinitionUpdate,
    FieldDefinitionResponse,
    FieldDefinitionListResponse,
)
from app.core.security import get_current_user
from app.core.rbac import require_config_edit
from models.user import User

router = APIRouter(prefix="/admin/fields", tags=["field-definitions"])


@router.get("", response_model=FieldDefinitionListResponse)
async def get_field_definitions(
    entity_type: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List FieldDefinitions. Supports filtering by entity_type."""
    query = db.query(FieldDefinition)

    if entity_type:
        query = query.filter(FieldDefinition.entity_type == entity_type.lower())
    if active is not None:
        query = query.filter(FieldDefinition.active == active)

    total = query.count()
    offset = (page - 1) * size
    items = query.order_by(FieldDefinition.entity_type, FieldDefinition.name).offset(offset).limit(size).all()

    pages = (total + size - 1) // size

    return FieldDefinitionListResponse(
        items=[FieldDefinitionResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.post("", response_model=FieldDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_field_definition(
    field_data: FieldDefinitionCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """Create a new FieldDefinition. Requires config:edit."""
    # Check for duplicate name per entity_type
    existing = db.query(FieldDefinition).filter(
        FieldDefinition.entity_type == field_data.entity_type.lower(),
        FieldDefinition.name == field_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"FieldDefinition with name '{field_data.name}' already exists for entity_type '{field_data.entity_type}'"
        )

    # If source_list_name provided? For now, assume source_list_id is passed.
    # UI can pass source_list_id after selecting from lists.

    field_def = FieldDefinition(
        entity_type=field_data.entity_type.lower(),
        name=field_data.name,
        display_name=field_data.display_name,
        data_type=field_data.data_type.value,
        source_list_id=field_data.source_list_id,
        is_required=field_data.is_required,
        is_unique=field_data.is_unique,
        default_value=field_data.default_value,
        validation_rules=field_data.validation_rules,
        ui_hints=field_data.ui_hints,
        description=field_data.description,
        active=field_data.active,
        is_materialized_column=field_data.is_materialized_column,
        column_name=field_data.column_name,
    )

    db.add(field_def)
    db.commit()
    db.refresh(field_def)
    return FieldDefinitionResponse.model_validate(field_def)


@router.get("/{field_id}", response_model=FieldDefinitionResponse)
async def get_field_definition(
    field_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single FieldDefinition by ID."""
    field_def = db.query(FieldDefinition).filter(FieldDefinition.id == field_id).first()
    if not field_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FieldDefinition not found")
    return FieldDefinitionResponse.model_validate(field_def)


@router.patch("/{field_id}", response_model=FieldDefinitionResponse)
async def update_field_definition(
    field_id: UUID,
    field_data: FieldDefinitionUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """Update a FieldDefinition."""
    field_def = db.query(FieldDefinition).filter(FieldDefinition.id == field_id).first()
    if not field_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FieldDefinition not found")

    update_data = field_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "entity_type" and value:
            value = value.lower()
        setattr(field_def, key, value)

    db.commit()
    db.refresh(field_def)
    return FieldDefinitionResponse.model_validate(field_def)


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field_definition(
    field_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """Soft-delete by setting active=False (or hard delete if preferred)."""
    field_def = db.query(FieldDefinition).filter(FieldDefinition.id == field_id).first()
    if not field_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FieldDefinition not found")

    # For now, deactivate (matches old custom attr behavior)
    field_def.active = False
    db.commit()
    return None
