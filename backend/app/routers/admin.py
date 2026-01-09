"""
Admin router for name templates management
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database import get_db
from models.name_template import NameTemplate
from models.user import User, Role
from app.schemas.name_template import (
    NameTemplateResponse,
    NameTemplateCreate,
    NameTemplateUpdate,
    NameTemplateListResponse,
)
from pydantic import BaseModel
from app.core.security import get_current_user
from app.core.rbac import require_config_edit
from app.core.name_generation import generate_name
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/admin/name-templates", tags=["name-templates"])


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


@router.get("", response_model=NameTemplateListResponse)
async def get_name_templates(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get name templates with filtering and pagination.
    Requires config:edit permission for full access, others can view active templates.
    """
    query = db.query(NameTemplate)
    
    # Apply filters
    if entity_type:
        query = query.filter(NameTemplate.entity_type == entity_type.lower())
    
    if active is not None:
        query = query.filter(NameTemplate.active == active)
    else:
        # By default, show active templates to non-admins
        if not is_administrator(current_user, db):
            query = query.filter(NameTemplate.active == True)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    templates = query.order_by(
        NameTemplate.entity_type,
        NameTemplate.created_at.desc()
    ).offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size
    
    return NameTemplateListResponse(
        templates=[NameTemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.post("", response_model=NameTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_name_template(
    template_data: NameTemplateCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Create a new name template.
    Requires config:edit permission.
    """
    # Check if there's already an active template for this entity_type
    if template_data.active:
        existing_active = db.query(NameTemplate).filter(
            and_(
                NameTemplate.entity_type == template_data.entity_type,
                NameTemplate.active == True
            )
        ).first()
        
        if existing_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An active template already exists for entity type '{template_data.entity_type}'. Deactivate it first or update the existing template."
            )
    
    new_template = NameTemplate(
        entity_type=template_data.entity_type,
        template=template_data.template,
        description=template_data.description,
        active=template_data.active,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    return NameTemplateResponse.model_validate(new_template)


class NamePreviewResponse(BaseModel):
    """Response schema for name preview"""
    preview: str


@router.get("/preview", response_model=NamePreviewResponse)
async def preview_generated_name(
    entity_type: str = Query(..., description="Entity type (sample, project, batch, analysis, container)"),
    client_id: Optional[str] = Query(None, description="Client ID for {CLIENT} placeholder (UUID string)"),
    reference_date: Optional[str] = Query(None, description="Reference date in YYYY-MM-DD format for date placeholders"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview a generated name without consuming a sequence number.
    This endpoint generates a preview of what the name would look like,
    but does not actually increment the sequence.
    """
    try:
        # Validate entity_type
        allowed_types = ['sample', 'project', 'batch', 'analysis', 'container']
        entity_type_lower = entity_type.lower() if entity_type else ''
        if not entity_type or entity_type_lower not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"entity_type must be one of: {', '.join(allowed_types)}"
            )
        
        # Parse client_id if provided (handle empty strings)
        parsed_client_id = None
        if client_id and client_id.strip():
            try:
                parsed_client_id = UUID(client_id.strip())
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="client_id must be a valid UUID"
                )
        
        # Parse reference_date if provided (handle empty strings)
        ref_date = None
        if reference_date and reference_date.strip():
            try:
                ref_date = datetime.strptime(reference_date.strip(), '%Y-%m-%d')
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="reference_date must be in YYYY-MM-DD format"
                )
        
        # Get client name if client_id provided
        client_name = None
        if parsed_client_id:
            from models.client import Client
            client = db.query(Client).filter(Client.id == parsed_client_id).first()
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Client not found"
                )
            client_name = client.name
        
        # Generate preview (this will use the current sequence value but not increment it)
        # We'll use a special preview mode that doesn't consume sequences
        from app.core.name_generation import get_active_template
        template_obj = get_active_template(db, entity_type_lower)
        
        if not template_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active template found for entity type '{entity_type}'"
            )
        
        template = template_obj.template
        now = ref_date if ref_date else datetime.now()
        
        # Build replacement dictionary (without consuming sequence)
        replacements = {}
        
        # Date placeholders
        if '{YYYY}' in template:
            replacements['{YYYY}'] = str(now.year)
        if '{MM}' in template:
            replacements['{MM}'] = f"{now.month:02d}"
        if '{DD}' in template:
            replacements['{DD}'] = f"{now.day:02d}"
        if '{YYYYMMDD}' in template:
            replacements['{YYYYMMDD}'] = now.strftime('%Y%m%d')
        
        # Sequence placeholder - use next value for preview (will show what the next generated name would be)
        if '{SEQ}' in template:
            from sqlalchemy import text
            sequence_name = f'name_template_seq_{entity_type_lower}'
            # Get the current value for preview (without actually incrementing)
            try:
                # Try to get the last value from the sequence using pg_sequences
                result = db.execute(text("""
                    SELECT last_value 
                    FROM pg_sequences 
                    WHERE schemaname = 'public' AND sequencename = :seq_name
                """), {'seq_name': sequence_name})
                row = result.first()
                if row:
                    # Next value will be last_value + 1
                    seq = row[0] + 1
                else:
                    # Sequence might not exist or be initialized, use 1
                    seq = 1
            except Exception as e:
                # If query fails, try a simpler approach - just use 1 for preview
                # In production, the actual generation will use the real sequence
                seq = 1
            replacements['{SEQ}'] = f"{seq:03d}"
        
        # Client placeholder
        if '{CLIENT}' in template:
            if client_name:
                client_code = client_name.upper().replace(' ', '').replace('-', '')[:10]
                replacements['{CLIENT}'] = client_code
            else:
                replacements['{CLIENT}'] = 'UNKNOWN'
        
        # Apply replacements
        preview = template
        for placeholder, value in replacements.items():
            preview = preview.replace(placeholder, value)
        
        # Ensure preview is always a string (never None)
        if not preview:
            preview = "PREVIEW_ERROR"
        
        return NamePreviewResponse(preview=preview)
    except HTTPException:
        raise
    except Exception as e:
        # Log unexpected errors and return a generic error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating name preview: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating preview: {str(e)}"
        )


@router.get("/{template_id}", response_model=NameTemplateResponse)
async def get_name_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific name template by ID.
    """
    template = db.query(NameTemplate).filter(NameTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Name template not found"
        )
    
    # Non-admins can only see active templates
    if not is_administrator(current_user, db) and not template.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Name template not found"
        )
    
    return NameTemplateResponse.model_validate(template)


@router.patch("/{template_id}", response_model=NameTemplateResponse)
async def update_name_template(
    template_id: UUID,
    template_data: NameTemplateUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Update a name template.
    Requires config:edit permission.
    """
    template = db.query(NameTemplate).filter(NameTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Name template not found"
        )
    
    # Check for unique constraint if activating or changing entity_type
    new_entity_type = template_data.entity_type or template.entity_type
    new_active = template_data.active if template_data.active is not None else template.active
    
    if new_active and (new_entity_type != template.entity_type or (template_data.active is not None and not template.active)):
        # Check if there's another active template for this entity_type
        existing_active = db.query(NameTemplate).filter(
            and_(
                NameTemplate.entity_type == new_entity_type,
                NameTemplate.active == True,
                NameTemplate.id != template_id
            )
        ).first()
        
        if existing_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An active template already exists for entity type '{new_entity_type}'. Deactivate it first."
            )
    
    # Update fields
    if template_data.entity_type is not None:
        template.entity_type = template_data.entity_type
    if template_data.template is not None:
        template.template = template_data.template
    if template_data.description is not None:
        template.description = template_data.description
    if template_data.active is not None:
        template.active = template_data.active
    
    template.modified_by = current_user.id
    db.commit()
    db.refresh(template)
    
    return NameTemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_name_template(
    template_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Soft delete a name template (sets active=false).
    Requires config:edit permission.
    """
    template = db.query(NameTemplate).filter(NameTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Name template not found"
        )
    
    template.active = False
    template.modified_by = current_user.id
    db.commit()
    
    return None

