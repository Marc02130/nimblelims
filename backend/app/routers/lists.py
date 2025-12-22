"""
Lists router for LIMS MVP
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from models.list import List as ListModel, ListEntry
from models.user import User
from app.schemas.list import ListEntryResponse, ListResponse
from app.core.security import get_current_user

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

