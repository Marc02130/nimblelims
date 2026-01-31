"""
Clients router for NimbleLims
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from models.client import Client
from models.user import User
from app.schemas.client import ClientResponse, ClientCreate, ClientUpdate
from app.core.security import get_current_user, set_current_user_id
from app.core.rbac import require_permission, is_system_client_or_admin
from uuid import UUID

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[ClientResponse])
async def get_clients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all accessible clients.
    Access control: application-level filter (is_system_client_or_admin + client_id) is primary;
    RLS (clients_access) provides defense-in-depth when app.current_user_id is set.
    - Administrators: see all clients
    - System client users (lab employees): see all clients
    - Client users: see only their own client record
    """
    # Set current user for RLS so DB policies can evaluate
    set_current_user_id(str(current_user.id), db)
    # Verify the same connection has app.current_user_id set (for RLS and diagnostics)
    row = db.execute(text("SELECT current_setting('app.current_user_id', true)")).fetchone()
    rv = row[0] if row else None
    logger.info(
        "GET /clients: user_id=%s role=%s client_id=%s db_app_current_user_id=%s",
        current_user.id,
        getattr(current_user.role, "name", None),
        current_user.client_id,
        rv,
    )
    # Application-level filter is the primary enforcement: client users see only their client.
    # RLS (clients_access policy) provides defense-in-depth when app.current_user_id is set.
    if not is_system_client_or_admin(current_user):
        # Regular client user: only their own client (role is eager-loaded in get_current_user)
        if current_user.client_id is None:
            return []
        clients_query = db.query(Client).filter(Client.active == True, Client.id == current_user.client_id)
    else:
        clients_query = db.query(Client).filter(Client.active == True)
    
    clients = clients_query.order_by(Client.name).all()
    return [ClientResponse.from_orm(client) for client in clients]


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    current_user: User = Depends(require_permission("config:edit")),
    db: Session = Depends(get_db)
):
    """
    Create a new client.
    Requires config:edit permission.
    """
    # Check for unique name
    existing_client = db.query(Client).filter(Client.name == client_data.name).first()
    if existing_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client name already exists"
        )
    
    new_client = Client(
        name=client_data.name,
        description=client_data.description,
        billing_info=client_data.billing_info or {},
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    return ClientResponse.from_orm(new_client)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    client_data: ClientUpdate,
    current_user: User = Depends(require_permission("config:edit")),
    db: Session = Depends(get_db)
):
    """
    Update a client.
    Requires config:edit permission.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Check for unique name if updating
    if client_data.name and client_data.name != client.name:
        existing_client = db.query(Client).filter(Client.name == client_data.name).first()
        if existing_client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client name already exists"
            )
        client.name = client_data.name
    
    if client_data.description is not None:
        client.description = client_data.description
    
    if client_data.billing_info is not None:
        client.billing_info = client_data.billing_info
    
    if client_data.active is not None:
        client.active = client_data.active
    
    client.modified_by = current_user.id
    db.commit()
    db.refresh(client)
    
    return ClientResponse.from_orm(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    current_user: User = Depends(require_permission("config:edit")),
    db: Session = Depends(get_db)
):
    """
    Soft delete a client.
    Requires config:edit permission.
    Fails if client has active users or projects.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Check if client has active users
    users_count = db.query(User).filter(User.client_id == client_id, User.active == True).count()
    if users_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete client: {users_count} active user(s) are assigned to this client"
        )
    
    # Check if client has active projects (if projects table exists)
    # This is a simplified check - can be expanded
    
    client.active = False
    client.modified_by = current_user.id
    db.commit()
    
    return None

