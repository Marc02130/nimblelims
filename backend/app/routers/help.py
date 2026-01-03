"""
Help router for role-filtered help content
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from models.help_entry import HelpEntry
from models.user import User, Role
from app.schemas.help import (
    HelpEntryResponse,
    HelpEntryCreate,
    HelpEntryUpdate,
    HelpEntryListResponse,
)
from app.core.security import get_current_user, get_user_permissions
from app.core.rbac import require_config_edit
from uuid import UUID

router = APIRouter()


def role_name_to_slug(role_name: str) -> str:
    """
    Convert role name to slug format.
    
    Examples:
        "Lab Technician" -> "lab-technician"
        "Client" -> "client"
        "Lab Manager" -> "lab-manager"
    
    Args:
        role_name: Role name (e.g., "Lab Technician")
    
    Returns:
        Slug format (e.g., "lab-technician")
    """
    return role_name.lower().replace(' ', '-')


def normalize_role_filter(role_filter: str) -> str:
    """
    Normalize role filter to slug format (case-insensitive).
    
    Handles both role names and slugs:
        "Lab Technician" -> "lab-technician"
        "lab-technician" -> "lab-technician"
        "LAB-TECHNICIAN" -> "lab-technician"
        "Lab Manager" -> "lab-manager"
        "lab-manager" -> "lab-manager"
        "LAB-MANAGER" -> "lab-manager"
        "Administrator" -> "administrator"
        "administrator" -> "administrator"
        "Client" -> "client"
    
    Args:
        role_filter: Role name or slug (case-insensitive)
    
    Returns:
        Normalized slug format
    """
    return role_filter.lower().replace(' ', '-')


def validate_role_filter(role_filter: Optional[str], db: Session) -> Optional[str]:
    """
    Validate that role_filter corresponds to an existing role.
    
    If role_filter is None, returns None (public help entry).
    If role_filter is provided, validates it exists in the roles table
    (by matching slug format against role names).
    
    Args:
        role_filter: Role filter in slug format (e.g., "lab-technician")
        db: Database session
    
    Returns:
        Normalized role_filter if valid, None if role_filter is None
    
    Raises:
        HTTPException 400: If role_filter doesn't match any existing role
    """
    if role_filter is None:
        return None
    
    # Normalize to slug format
    normalized = normalize_role_filter(role_filter)
    
    # Get all active roles
    roles = db.query(Role).filter(Role.active == True).all()
    
    # Check if normalized slug matches any role name (converted to slug)
    for role in roles:
        role_slug = role_name_to_slug(role.name)
        if role_slug == normalized:
            return normalized
    
    # If no match found, raise error
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid role_filter '{role_filter}': No matching role found. "
               f"Available roles: {', '.join([role_name_to_slug(r.name) for r in roles])}"
    )


@router.get("", response_model=HelpEntryListResponse)
async def get_help_entries(
    role: Optional[str] = Query(None, description="Filter by role (overrides current user role). Accepts role name or slug (case-insensitive). Examples: 'Lab Technician', 'lab-technician', 'Lab Manager', 'lab-manager', 'Administrator', 'administrator', 'Client'"),
    section: Optional[str] = Query(None, description="Filter by section"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get help entries filtered by role.
    
    - Uses current user's role if role parameter not provided
    - Shows entries where role_filter matches user's role (converted to slug) OR role_filter is NULL (public)
    - Supports pagination and section filtering
    - Role parameter accepts both role names and slugs (case-insensitive)
    
    Examples:
        - Lab Technician accessing help: GET /help (automatically filters by 'lab-technician')
        - Lab Manager accessing help: GET /help (automatically filters by 'lab-manager')
        - Administrator accessing help: GET /help (automatically filters by 'administrator')
        - Admin filtering for Lab Manager: GET /help?role=lab-manager
        - Admin filtering by role name: GET /help?role=Lab Manager
        - Admin filtering for Lab Technician: GET /help?role=lab-technician
        - Admin filtering by role name: GET /help?role=Lab Technician
        - Admin filtering for Administrator: GET /help?role=administrator
        - Admin filtering by role name: GET /help?role=Administrator
        - Client accessing help: GET /help (automatically filters by 'client')
        - Filtering by section: GET /help?section=Results Review
        - Filtering by section: GET /help?section=User Management
        - Filtering by section: GET /help?section=Accessioning Workflow
    
    Returns:
        Paginated list of help entries matching the role filter and section (if provided)
    """
    # Check if user has config:edit permission (for Help Management page)
    user_permissions = get_user_permissions(current_user, db)
    has_config_edit = "config:edit" in user_permissions
    
    # Determine role filter
    if role:
        # Only users with config:edit permission can filter by role
        if not has_config_edit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users with config:edit permission can filter by role"
            )
        # Normalize role parameter to slug format (case-insensitive)
        role_filter = normalize_role_filter(role)
    else:
        # Use current user's role, convert to slug format
        role_filter = role_name_to_slug(current_user.role.name)
    
    # Build query - RLS will filter, but we add explicit filter for clarity
    query = db.query(HelpEntry).filter(
        HelpEntry.active == True
    )
    
    # If user has config:edit permission and no role filter specified, show all entries
    # Otherwise, filter by role: role_filter matches user's role (as slug) OR role_filter is NULL
    if has_config_edit and not role:
        # Show all help entries for management (no role filtering)
        pass
    else:
        # Filter by role: role_filter matches user's role (as slug) OR role_filter is NULL
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
    section: str = Query(..., description="Section name for contextual help. Examples: 'Accessioning Workflow', 'Batch Creation', 'Results Entry', 'Results Review', 'Batch Management', 'Project Management', 'User Management', 'EAV Configuration', 'Row Level Security (RLS)'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get contextual help for a specific section.
    
    Returns help entry filtered by current user's role (converted to slug format).
    Returns 404 if no help entry found for the section and user's role.
    
    Examples:
        - Lab Technician accessing accessioning help: GET /help/contextual?section=Accessioning Workflow
        - Lab Technician accessing batch help: GET /help/contextual?section=Batch Creation
        - Lab Manager accessing results review help: GET /help/contextual?section=Results Review
        - Lab Manager accessing batch management help: GET /help/contextual?section=Batch Management
        - Lab Manager accessing project management help: GET /help/contextual?section=Project Management
        - Administrator accessing user management help: GET /help/contextual?section=User Management
        - Administrator accessing EAV configuration help: GET /help/contextual?section=EAV Configuration
        - Client accessing project help: GET /help/contextual?section=Viewing Projects
    
    Args:
        section: Section name (e.g., "Accessioning Workflow", "Batch Creation", "Results Review")
    
    Returns:
        Help entry matching the section and user's role
    
    Raises:
        HTTPException 404: If no help entry found for the section and user's role
    """
    # Convert user's role name to slug format for filtering
    role_filter = role_name_to_slug(current_user.role.name)
    
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
    
    Examples:
        - Create Lab Technician help: {"section": "Accessioning Workflow", "content": "...", "role_filter": "lab-technician"}
        - Create Lab Manager help: {"section": "Results Review", "content": "...", "role_filter": "lab-manager"}
        - Create Administrator help: {"section": "User Management", "content": "...", "role_filter": "administrator"}
        - Create Client help: {"section": "Viewing Projects", "content": "...", "role_filter": "client"}
        - Create public help: {"section": "Getting Started", "content": "...", "role_filter": null}
    
    Note: role_filter accepts both role names and slugs (case-insensitive). It will be validated
    against existing roles and normalized to slug format.
    """
    # Validate and normalize role_filter
    normalized_role_filter = validate_role_filter(help_data.role_filter, db)
    
    # Create help entry with name and description from section/content for BaseModel
    new_help_entry = HelpEntry(
        name=help_data.section,  # Use section as name
        description=help_data.content[:255] if len(help_data.content) > 255 else help_data.content,
        section=help_data.section,
        content=help_data.content,
        role_filter=normalized_role_filter,
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
    
    Examples:
        - Update content: PATCH /admin/help/{id} {"content": "Updated content"}
        - Update role_filter: PATCH /admin/help/{id} {"role_filter": "lab-manager"}
        - Update section: PATCH /admin/help/{id} {"section": "New Section Name"}
        - Deactivate entry: PATCH /admin/help/{id} {"active": false}
    
    Note: role_filter will be validated against existing roles and normalized to slug format.
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
        # Validate and normalize role_filter
        help_entry.role_filter = validate_role_filter(help_data.role_filter, db)
    
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

