"""
Lists router for NimbleLims
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from models.list import List as ListModel, ListEntry
from models.user import User
from app.schemas.list import ListEntryResponse, ListResponse, ListEntryCreate, ListEntryUpdate, ListCreate, ListUpdate
from app.core.security import get_current_user, get_user_permissions
from app.core.rbac import require_config_edit
from datetime import datetime
from uuid import UUID

router = APIRouter()


@router.post("", response_model=ListResponse, status_code=status.HTTP_201_CREATED)
async def create_list(
    list_data: ListCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Create a new list.
    Requires config:edit permission.
    """
    # Check if list with same name already exists
    existing_list = db.query(ListModel).filter(
        ListModel.name == list_data.name
    ).first()
    
    if existing_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"List with name '{list_data.name}' already exists"
        )
    
    # Create new list
    new_list = ListModel(
        name=list_data.name,
        description=list_data.description,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(new_list)
    db.commit()
    db.refresh(new_list)
    
    return ListResponse(
        id=new_list.id,
        name=new_list.name,
        description=new_list.description,
        active=new_list.active,
        created_at=new_list.created_at,
        modified_at=new_list.modified_at,
        entries=[]
    )


@router.get("", response_model=List[ListResponse])
async def get_lists(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all active lists with their entries.
    For users with config:edit permission, returns all entries (active and inactive).
    For other users, returns only active entries.
    """
    # Check if user has config:edit permission
    user_permissions = get_user_permissions(current_user, db)
    has_config_edit = "config:edit" in user_permissions
    
    lists = db.query(ListModel).filter(ListModel.active == True).all()
    result = []
    for list_obj in lists:
        # If user has config:edit permission, show all entries; otherwise, only active
        if has_config_edit:
            entries = db.query(ListEntry).filter(
                ListEntry.list_id == list_obj.id
            ).all()
        else:
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


@router.patch("/{list_id}", response_model=ListResponse)
async def update_list(
    list_id: UUID,
    list_data: ListUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Update a list.
    Requires config:edit permission.
    """
    # Find the list
    list_obj = db.query(ListModel).filter(ListModel.id == list_id).first()
    
    if not list_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="List not found"
        )
    
    # Check for name conflict if name is being updated
    if list_data.name and list_data.name != list_obj.name:
        existing_list = db.query(ListModel).filter(
            ListModel.name == list_data.name,
            ListModel.id != list_id
        ).first()
        
        if existing_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"List with name '{list_data.name}' already exists"
            )
    
    # Update fields
    update_data = list_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(list_obj, field, value)
    
    list_obj.modified_by = current_user.id
    list_obj.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(list_obj)
    
    # Get entries for response
    entries = db.query(ListEntry).filter(ListEntry.list_id == list_obj.id).all()
    
    return ListResponse(
        id=list_obj.id,
        name=list_obj.name,
        description=list_obj.description,
        active=list_obj.active,
        created_at=list_obj.created_at,
        modified_at=list_obj.modified_at,
        entries=[ListEntryResponse.from_orm(entry) for entry in entries]
    )


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(
    list_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Soft delete a list (set active=False).
    Requires config:edit permission.
    """
    # Find the list
    list_obj = db.query(ListModel).filter(ListModel.id == list_id).first()
    
    if not list_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="List not found"
        )
    
    # Soft delete
    list_obj.active = False
    list_obj.modified_by = current_user.id
    list_obj.modified_at = datetime.utcnow()
    
    db.commit()
    
    return None


@router.get("/{list_name}/entries", response_model=List[ListEntryResponse])
async def get_list_entries(
    list_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all entries for a specific list by list name.
    For users with config:edit permission, returns all entries (active and inactive).
    For other users, returns only active entries.
    """
    # Check if user has config:edit permission
    user_permissions = get_user_permissions(current_user, db)
    has_config_edit = "config:edit" in user_permissions
    
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
    
    # If user has config:edit permission, show all entries; otherwise, only active
    if has_config_edit:
        entries = db.query(ListEntry).filter(
            ListEntry.list_id == list_obj.id
        ).order_by(ListEntry.name).all()
    else:
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

