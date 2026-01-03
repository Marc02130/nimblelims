"""
Custom Attributes Configuration router for NimbleLims
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from app.database import get_db
from models.custom_attributes_config import CustomAttributeConfig
from models.user import User, Role
from app.schemas.custom_attributes_config import (
    CustomAttributeConfigResponse,
    CustomAttributeConfigCreate,
    CustomAttributeConfigUpdate,
    CustomAttributeConfigListResponse,
)
from app.core.security import get_current_user
from app.core.rbac import require_config_edit
from uuid import UUID

router = APIRouter(prefix="/admin/custom-attributes", tags=["custom-attributes"])


def is_administrator(user: User, db: Session) -> bool:
    """Helper function to check if user is an administrator"""
    try:
        if hasattr(user, 'role') and user.role is not None:
            return user.role.name == "Administrator"
    except (AttributeError, Exception):
        pass
    
    # If role is not loaded, query it
    role = db.query(Role).filter(Role.id == user.role_id).first()
    return role.name == "Administrator" if role else False


@router.get("", response_model=CustomAttributeConfigListResponse)
async def get_custom_attribute_configs(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get custom attribute configurations with filtering and pagination.
    """
    query = db.query(CustomAttributeConfig)
    
    # Apply filters
    if entity_type:
        query = query.filter(CustomAttributeConfig.entity_type == entity_type)
    
    if active is not None:
        query = query.filter(CustomAttributeConfig.active == active)
    else:
        # By default, show active configs to non-admins
        if not is_administrator(current_user, db):
            query = query.filter(CustomAttributeConfig.active == True)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    configs = query.order_by(
        CustomAttributeConfig.entity_type,
        CustomAttributeConfig.attr_name
    ).offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size
    
    return CustomAttributeConfigListResponse(
        configs=[CustomAttributeConfigResponse.model_validate(config) for config in configs],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.post("", response_model=CustomAttributeConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_attribute_config(
    config_data: CustomAttributeConfigCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Create a new custom attribute configuration.
    Requires config:edit permission.
    """
    # Check for unique constraint (entity_type + attr_name)
    existing_config = db.query(CustomAttributeConfig).filter(
        and_(
            CustomAttributeConfig.entity_type == config_data.entity_type,
            CustomAttributeConfig.attr_name == config_data.attr_name
        )
    ).first()
    
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Custom attribute '{config_data.attr_name}' already exists for entity type '{config_data.entity_type}'"
        )
    
    new_config = CustomAttributeConfig(
        entity_type=config_data.entity_type,
        attr_name=config_data.attr_name,
        data_type=config_data.data_type.value,
        validation_rules=config_data.validation_rules,
        description=config_data.description,
        active=config_data.active,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    return CustomAttributeConfigResponse.model_validate(new_config)


@router.get("/{config_id}", response_model=CustomAttributeConfigResponse)
async def get_custom_attribute_config(
    config_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific custom attribute configuration by ID.
    """
    config = db.query(CustomAttributeConfig).filter(CustomAttributeConfig.id == config_id).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom attribute configuration not found"
        )
    
    # Non-admins can only see active configs
    if not is_administrator(current_user, db) and not config.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom attribute configuration not found"
        )
    
    return CustomAttributeConfigResponse.model_validate(config)


@router.patch("/{config_id}", response_model=CustomAttributeConfigResponse)
async def update_custom_attribute_config(
    config_id: UUID,
    config_data: CustomAttributeConfigUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Update a custom attribute configuration.
    Requires config:edit permission.
    """
    config = db.query(CustomAttributeConfig).filter(CustomAttributeConfig.id == config_id).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom attribute configuration not found"
        )
    
    # Check for unique constraint if updating entity_type or attr_name
    if config_data.entity_type or config_data.attr_name:
        new_entity_type = config_data.entity_type or config.entity_type
        new_attr_name = config_data.attr_name or config.attr_name
        
        if new_entity_type != config.entity_type or new_attr_name != config.attr_name:
            existing_config = db.query(CustomAttributeConfig).filter(
                and_(
                    CustomAttributeConfig.entity_type == new_entity_type,
                    CustomAttributeConfig.attr_name == new_attr_name,
                    CustomAttributeConfig.id != config_id
                )
            ).first()
            
            if existing_config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Custom attribute '{new_attr_name}' already exists for entity type '{new_entity_type}'"
                )
    
    # Update fields
    if config_data.entity_type is not None:
        config.entity_type = config_data.entity_type
    if config_data.attr_name is not None:
        config.attr_name = config_data.attr_name
    if config_data.data_type is not None:
        config.data_type = config_data.data_type.value
    if config_data.validation_rules is not None:
        config.validation_rules = config_data.validation_rules
    if config_data.description is not None:
        config.description = config_data.description
    if config_data.active is not None:
        config.active = config_data.active
    
    config.modified_by = current_user.id
    
    db.commit()
    db.refresh(config)
    
    return CustomAttributeConfigResponse.model_validate(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_attribute_config(
    config_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Soft-delete a custom attribute configuration (set active=False).
    Requires config:edit permission.
    """
    config = db.query(CustomAttributeConfig).filter(CustomAttributeConfig.id == config_id).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom attribute configuration not found"
        )
    
    # Soft delete by setting active=False
    config.active = False
    config.modified_by = current_user.id
    
    db.commit()
    
    return None

