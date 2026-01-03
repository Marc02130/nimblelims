"""
Help router for role-filtered help content
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from models.help_entry import HelpEntry
from models.user import User
from app.schemas.help import (
    HelpEntryResponse,
    HelpEntryCreate,
    HelpEntryUpdate,
    HelpEntryListResponse,
)
from app.core.security import get_current_user
from app.core.rbac import require_config_edit
from uuid import UUID

router = APIRouter()


@router.get("", response_model=HelpEntryListResponse)
async def get_help_entries(
    role: Optional[str] = Query(None, description="Filter by role (overrides current user role)"),
    section: Optional[str] = Query(None, description="Filter by section"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get help entries filtered by role.
    - Uses current user's role if role parameter not provided
    - Shows entries where role_filter matches user's role OR role_filter is NULL (public)
    - Supports pagination and section filtering
    """
    # Determine role filter
    if role:
        # Admin can filter by any role
        if current_user.role.name != "Administrator":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can filter by role"
            )
        role_filter = role
    else:
        # Use current user's role
        role_filter = current_user.role.name
    
    # Build query - RLS will filter, but we add explicit filter for clarity
    query = db.query(HelpEntry).filter(
        HelpEntry.active == True
    )
    
    # Filter by role: role_filter matches user's role OR role_filter is NULL
    query = query.filter(
        (HelpEntry.role_filter == role_filter) | (HelpEntry.role_filter.is_(None))
    )
    
    # Filter by section if provided
    if section:
        query = query.filter(HelpEntry.section == section)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    help_entries = query.order_by(HelpEntry.section, HelpEntry.created_at).offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size if total > 0 else 0
    
    return HelpEntryListResponse(
        help_entries=[HelpEntryResponse.model_validate(entry) for entry in help_entries],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/contextual", response_model=HelpEntryResponse)
async def get_contextual_help(
    section: str = Query(..., description="Section name for contextual help"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get contextual help for a specific section.
    Returns help entry filtered by current user's role.
    Returns 404 if no help entry found for the section and user's role.
    """
    role_filter = current_user.role.name
    
    # Query for help entry matching section and role
    help_entry = db.query(HelpEntry).filter(
        HelpEntry.active == True,
        HelpEntry.section == section,
        ((HelpEntry.role_filter == role_filter) | (HelpEntry.role_filter.is_(None)))
    ).first()
    
    if not help_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Help entry not found for section '{section}'"
        )
    
    return HelpEntryResponse.model_validate(help_entry)


@router.post("/admin/help", response_model=HelpEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_help_entry(
    help_data: HelpEntryCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Create a new help entry.
    Requires config:edit permission.
    """
    # Create help entry with name and description from section/content for BaseModel
    new_help_entry = HelpEntry(
        name=help_data.section,  # Use section as name
        description=help_data.content[:255] if len(help_data.content) > 255 else help_data.content,
        section=help_data.section,
        content=help_data.content,
        role_filter=help_data.role_filter,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_help_entry)
    db.commit()
    db.refresh(new_help_entry)
    
    return HelpEntryResponse.from_orm(new_help_entry)


@router.patch("/admin/help/{help_entry_id}", response_model=HelpEntryResponse)
async def update_help_entry(
    help_entry_id: UUID,
    help_data: HelpEntryUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Update a help entry (partial update).
    Requires config:edit permission.
    """
    help_entry = db.query(HelpEntry).filter(HelpEntry.id == help_entry_id).first()
    
    if not help_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Help entry not found"
        )
    
    # Update fields
    if help_data.section is not None:
        help_entry.section = help_data.section
        help_entry.name = help_data.section  # Update name to match section
    
    if help_data.content is not None:
        help_entry.content = help_data.content
        help_entry.description = help_data.content[:255] if len(help_data.content) > 255 else help_data.content
    
    if help_data.role_filter is not None:
        help_entry.role_filter = help_data.role_filter
    
    if help_data.active is not None:
        help_entry.active = help_data.active
    
    # Update audit fields
    help_entry.modified_by = current_user.id
    
    db.commit()
    db.refresh(help_entry)
    
    return HelpEntryResponse.model_validate(help_entry)


@router.delete("/admin/help/{help_entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_help_entry(
    help_entry_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Soft delete a help entry (sets active=False).
    Requires config:edit permission.
    """
    help_entry = db.query(HelpEntry).filter(HelpEntry.id == help_entry_id).first()
    
    if not help_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Help entry not found"
        )
    
    # Soft delete
    help_entry.active = False
    help_entry.modified_by = current_user.id
    
    db.commit()
    
    return None

