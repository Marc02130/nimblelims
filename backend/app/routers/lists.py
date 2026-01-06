"""
Lists router for NimbleLims
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from models.list import List as ListModel, ListEntry
from models.user import User
from app.schemas.list import ListEntryResponse, ListResponse, ListEntryCreate, ListEntryUpdate
from app.core.security import get_current_user
from app.core.rbac import require_config_edit
from datetime import datetime
from uuid import UUID

router = APIRouter()


@router.get("", response_model=List[ListResponse])
async def get_lists(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all active lists with their entries.
    """
    lists = db.query(ListModel).filter(ListModel.active == True).all()
    result = []
    for list_obj in lists:
        entries = db.query(ListEntry).filter(
            ListEntry.list_id == list_obj.id,
            ListEntry.active == True
        ).all()
        list_response = ListResponse(
            id=list_obj.id,
            name=list_obj.name,
            description=list_obj.description,
            active=list_obj.active,
            created_at=list_obj.created_at,
            modified_at=list_obj.modified_at,
            entries=[ListEntryResponse.from_orm(entry) for entry in entries]
        )
        result.append(list_response)
    return result


@router.get("/{list_name}/entries", response_model=List[ListEntryResponse])
async def get_list_entries(
    list_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all entries for a specific list by list name.
    Returns only active entries.
    """
    # Find the list by name
    list_obj = db.query(ListModel).filter(
        ListModel.name == list_name,
        ListModel.active == True
    ).first()
    
    if not list_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"List '{list_name}' not found"
        )
    
    # Get all active entries for this list
    entries = db.query(ListEntry).filter(
        ListEntry.list_id == list_obj.id,
        ListEntry.active == True
    ).order_by(ListEntry.name).all()
    
    return [ListEntryResponse.from_orm(entry) for entry in entries]


@router.post("/{list_name}/entries", response_model=ListEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_list_entry(
    list_name: str,
    entry_data: ListEntryCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Create a new entry in a list.
    Requires config:edit permission.
    """
    # Find the list by name
    list_obj = db.query(ListModel).filter(
        ListModel.name == list_name,
        ListModel.active == True
    ).first()
    
    if not list_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"List '{list_name}' not found"
        )
    
    # Check if entry with same name already exists in this list
    existing_entry = db.query(ListEntry).filter(
        ListEntry.list_id == list_obj.id,
        ListEntry.name == entry_data.name,
        ListEntry.active == True
    ).first()
    
    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Entry with name '{entry_data.name}' already exists in list '{list_name}'"
        )
    
    # Create new entry
    new_entry = ListEntry(
        list_id=list_obj.id,
        name=entry_data.name,
        description=entry_data.description,
        active=entry_data.active,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    return ListEntryResponse.from_orm(new_entry)


@router.patch("/{list_name}/entries/{entry_id}", response_model=ListEntryResponse)
async def update_list_entry(
    list_name: str,
    entry_id: UUID,
    entry_data: ListEntryUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Update a list entry.
    Requires config:edit permission.
    """
    # Find the list by name
    list_obj = db.query(ListModel).filter(
        ListModel.name == list_name,
        ListModel.active == True
    ).first()
    
    if not list_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"List '{list_name}' not found"
        )
    
    # Find the entry
    entry = db.query(ListEntry).filter(
        ListEntry.id == entry_id,
        ListEntry.list_id == list_obj.id
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry not found in list '{list_name}'"
        )
    
    # Check for name conflict if name is being updated
    if entry_data.name and entry_data.name != entry.name:
        existing_entry = db.query(ListEntry).filter(
            ListEntry.list_id == list_obj.id,
            ListEntry.name == entry_data.name,
            ListEntry.id != entry_id,
            ListEntry.active == True
        ).first()
        
        if existing_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Entry with name '{entry_data.name}' already exists in list '{list_name}'"
            )
    
    # Update fields
    update_data = entry_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)
    
    entry.modified_by = current_user.id
    entry.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(entry)
    
    return ListEntryResponse.from_orm(entry)


@router.delete("/{list_name}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list_entry(
    list_name: str,
    entry_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Soft delete a list entry (set active=False).
    Requires config:edit permission.
    """
    # Find the list by name
    list_obj = db.query(ListModel).filter(
        ListModel.name == list_name,
        ListModel.active == True
    ).first()
    
    if not list_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"List '{list_name}' not found"
        )
    
    # Find the entry
    entry = db.query(ListEntry).filter(
        ListEntry.id == entry_id,
        ListEntry.list_id == list_obj.id
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry not found in list '{list_name}'"
        )
    
    # Soft delete
    entry.active = False
    entry.modified_by = current_user.id
    entry.modified_at = datetime.utcnow()
    
    db.commit()
    
    return None

