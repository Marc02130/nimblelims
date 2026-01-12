"""
Containers router for NimbleLims
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from models.container import Container, ContainerType, Contents
from models.user import User
from app.schemas.container import (
    ContainerCreate, ContainerUpdate, ContainerResponse, ContainerWithContentsResponse,
    ContainerTypeCreate, ContainerTypeUpdate, ContainerTypeResponse,
    ContentsCreate, ContentsUpdate, ContentsResponse, ContentsListResponse
)
from app.core.rbac import (
    require_sample_create, require_sample_read, require_sample_update,
    require_config_edit
)
from app.core.security import get_current_user, get_user_permissions
from datetime import datetime
from uuid import UUID

router = APIRouter()


# Container Types endpoints
@router.get("/types", response_model=List[ContainerTypeResponse])
async def get_container_types(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all container types.
    For users with config:edit permission, returns all container types (active and inactive).
    For other users, returns only active container types.
    """
    # Check if user has config:edit permission
    user_permissions = get_user_permissions(current_user, db)
    has_config_edit = "config:edit" in user_permissions
    
    # If user has config:edit permission, show all container types; otherwise, only active
    if has_config_edit:
        container_types = db.query(ContainerType).all()
    else:
        container_types = db.query(ContainerType).filter(ContainerType.active == True).all()
    return [ContainerTypeResponse.from_orm(ct) for ct in container_types]


@router.post("/types", response_model=ContainerTypeResponse)
async def create_container_type(
    container_type_data: ContainerTypeCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Create a new container type.
    Requires config:edit permission.
    """
    container_type = ContainerType(
        name=container_type_data.name,
        description=container_type_data.description,
        capacity=container_type_data.capacity,
        material=container_type_data.material,
        dimensions=container_type_data.dimensions,
        preservative=container_type_data.preservative,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(container_type)
    db.commit()
    db.refresh(container_type)
    
    return ContainerTypeResponse.from_orm(container_type)


@router.patch("/types/{type_id}", response_model=ContainerTypeResponse)
async def update_container_type(
    type_id: UUID,
    container_type_data: ContainerTypeUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Update a container type.
    Requires config:edit permission.
    """
    container_type = db.query(ContainerType).filter(
        ContainerType.id == type_id,
        ContainerType.active == True
    ).first()
    
    if not container_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container type not found"
        )
    
    # Update fields
    update_data = container_type_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(container_type, field, value)
    
    container_type.modified_by = current_user.id
    container_type.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(container_type)
    
    return ContainerTypeResponse.from_orm(container_type)


# Containers endpoints
@router.get("", response_model=List[ContainerWithContentsResponse])
async def get_containers(
    type_id: Optional[UUID] = Query(None, description="Filter by container type"),
    parent_id: Optional[UUID] = Query(None, description="Filter by parent container"),
    project_ids: Optional[str] = Query(None, description="Comma-separated list of project IDs for cross-project filtering"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get containers with filtering and contents.
    Supports cross-project filtering via project_ids parameter.
    Returns containers with their associated samples (contents).
    """
    from models.sample import Sample
    from sqlalchemy.orm import joinedload
    
    query = db.query(Container).filter(Container.active == True)
    
    if type_id:
        query = query.filter(Container.type_id == type_id)
    if parent_id:
        query = query.filter(Container.parent_container_id == parent_id)
    
    # Filter by project_ids if provided (for cross-project batching)
    if project_ids:
        project_id_list = [UUID(p.strip()) for p in project_ids.split(',') if p.strip()]
        if project_id_list:
            # Get samples in these projects
            sample_ids = db.query(Sample.id).filter(
                Sample.project_id.in_(project_id_list),
                Sample.active == True
            ).subquery()
            
            # Get containers that have contents with these samples
            container_ids = db.query(Contents.container_id).filter(
                Contents.sample_id.in_(sample_ids)
            ).distinct().subquery()
            
            query = query.filter(Container.id.in_(container_ids))
    
    containers = query.all()
    
    # Get all container IDs
    container_ids = [c.id for c in containers]
    
    # Load all contents for these containers with sample relationship
    contents_map = {}
    if container_ids:
        contents_list = db.query(Contents).options(
            joinedload(Contents.sample)
        ).filter(Contents.container_id.in_(container_ids)).all()
        
        # Group contents by container_id
        for content in contents_list:
            if content.container_id not in contents_map:
                contents_map[content.container_id] = []
            contents_map[content.container_id].append(content)
    
    # Build response with contents
    result = []
    for container in containers:
        container_response = ContainerResponse.model_validate(container)
        
        # Get contents for this container
        container_contents = contents_map.get(container.id, [])
        
        # Build contents response with sample data
        contents_response = []
        for content in container_contents:
            content_dict = {
                "container_id": content.container_id,
                "sample_id": content.sample_id,
                "concentration": content.concentration,
                "concentration_units": content.concentration_units,
                "amount": content.amount,
                "amount_units": content.amount_units,
            }
            # Include sample data if available
            if content.sample:
                from app.schemas.sample import SampleResponse
                content_dict["sample"] = SampleResponse.model_validate(content.sample)
            contents_response.append(ContentsResponse(**content_dict))
        
        # Create ContainerWithContentsResponse
        result.append(ContainerWithContentsResponse(
            **container_response.dict(),
            contents=contents_response
        ))
    
    return result


@router.post("", response_model=ContainerResponse)
async def create_container(
    container_data: ContainerCreate,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Create a new container.
    Implements US-5: Container Management.
    """
    # Validate container type exists
    container_type = db.query(ContainerType).filter(
        ContainerType.id == container_data.type_id,
        ContainerType.active == True
    ).first()
    
    if not container_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid container type ID"
        )
    
    # Validate parent container if specified
    if container_data.parent_container_id:
        parent = db.query(Container).filter(
            Container.id == container_data.parent_container_id,
            Container.active == True
        ).first()
        
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent container ID"
            )
    
    # Generate name if not provided
    container_name = container_data.name
    if not container_name:
        from app.core.name_generation import generate_name_for_container
        try:
            container_name = generate_name_for_container(db=db)
        except Exception as e:
            # Fallback to UUID if generation fails
            import uuid
            container_name = str(uuid.uuid4())
    
    # Create container
    container = Container(
        name=container_name,
        description=container_data.description,
        row=container_data.row,
        column=container_data.column,
        concentration=container_data.concentration,
        concentration_units=container_data.concentration_units,
        amount=container_data.amount,
        amount_units=container_data.amount_units,
        type_id=container_data.type_id,
        parent_container_id=container_data.parent_container_id,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(container)
    try:
        db.commit()
        db.refresh(container)
    except Exception as e:
        db.rollback()
        # Check if it's a unique constraint violation (duplicate name)
        if "duplicate key value violates unique constraint" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Container with name '{container_name}' already exists. Please use a different name."
            )
        # Re-raise other exceptions
        raise
    
    return ContainerResponse.model_validate(container)


@router.get("/{container_id}", response_model=ContainerWithContentsResponse)
async def get_container(
    container_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific container with its contents.
    """
    container = db.query(Container).filter(
        Container.id == container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    # Get contents with sample relationship eagerly loaded
    from sqlalchemy.orm import joinedload
    from models.sample import Sample
    contents = db.query(Contents).options(
        joinedload(Contents.sample)
    ).filter(Contents.container_id == container_id).all()
    
    container_response = ContainerResponse.model_validate(container)
    # Build contents response with sample data
    contents_response = []
    for content in contents:
        content_dict = {
            "container_id": content.container_id,
            "sample_id": content.sample_id,
            "concentration": content.concentration,
            "concentration_units": content.concentration_units,
            "amount": content.amount,
            "amount_units": content.amount_units,
        }
        # Include sample data if available
        if content.sample:
            from app.schemas.sample import SampleResponse
            content_dict["sample"] = SampleResponse.model_validate(content.sample)
        contents_response.append(ContentsResponse(**content_dict))
    
    return ContainerWithContentsResponse(
        **container_response.dict(),
        contents=contents_response
    )


@router.patch("/{container_id}", response_model=ContainerResponse)
async def update_container(
    container_id: UUID,
    container_data: ContainerUpdate,
    current_user: User = Depends(require_sample_update),
    db: Session = Depends(get_db)
):
    """
    Partially update a container.
    
    Requires sample:update permission (containers link to samples via contents).
    Updates only the fields provided in the request. Updates audit fields (modified_at, modified_by).
    
    **Example: Update container name and concentration**
    ```json
    {
        "name": "CONTAINER-001-UPDATED",
        "concentration": 15.5,
        "concentration_units": "uuid-of-units"
    }
    ```
    
    **Example: Update container type**
    ```json
    {
        "type_id": "uuid-of-new-container-type"
    }
    ```
    
    Returns 404 if container not found, 403 if user lacks access (RLS enforced).
    All updates are performed in a single atomic transaction.
    """
    container = db.query(Container).filter(
        Container.id == container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    # Validate container type if being updated
    if container_data.type_id is not None:
        container_type = db.query(ContainerType).filter(
            ContainerType.id == container_data.type_id,
            ContainerType.active == True
        ).first()
        
        if not container_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid container type ID"
            )
    
    # Validate parent container if being updated
    if container_data.parent_container_id is not None:
        parent = db.query(Container).filter(
            Container.id == container_data.parent_container_id,
            Container.active == True
        ).first()
        
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent container ID"
            )
    
    # Update fields
    update_data = container_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(container, field, value)
    
    container.modified_by = current_user.id
    container.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(container)
    
    return ContainerResponse.model_validate(container)


# Contents endpoints
@router.get("/{container_id}/contents", response_model=ContentsListResponse)
async def get_container_contents(
    container_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get contents of a container with pagination.
    """
    # Verify container exists
    container = db.query(Container).filter(
        Container.id == container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    # Get contents with pagination and sample relationship eagerly loaded
    from sqlalchemy.orm import joinedload
    from models.sample import Sample
    query = db.query(Contents).options(
        joinedload(Contents.sample)
    ).filter(Contents.container_id == container_id)
    total = query.count()

    offset = (page - 1) * size
    contents = query.offset(offset).limit(size).all()

    pages = (total + size - 1) // size

    # Build contents response with sample data
    contents_response = []
    for content in contents:
        content_dict = {
            "container_id": content.container_id,
            "sample_id": content.sample_id,
            "concentration": content.concentration,
            "concentration_units": content.concentration_units,
            "amount": content.amount,
            "amount_units": content.amount_units,
        }
        # Include sample data if available
        if content.sample:
            from app.schemas.sample import SampleResponse
            content_dict["sample"] = SampleResponse.model_validate(content.sample)
        contents_response.append(ContentsResponse(**content_dict))

    return ContentsListResponse(
        contents=contents_response,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.post("/{container_id}/contents", response_model=ContentsResponse)
async def add_sample_to_container(
    container_id: UUID,
    contents_data: ContentsCreate,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Add a sample to a container (create contents).
    Implements US-6: Pooled Samples Creation.
    """
    # Verify container exists
    container = db.query(Container).filter(
        Container.id == container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found"
        )
    
    # Verify sample exists
    from models.sample import Sample
    sample = db.query(Sample).filter(
        Sample.id == contents_data.sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Check if contents already exists
    existing_contents = db.query(Contents).filter(
        Contents.container_id == container_id,
        Contents.sample_id == contents_data.sample_id
    ).first()
    
    if existing_contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample already exists in this container"
        )
    
    # Create contents
    try:
        # Use path parameter container_id (ignore body container_id to prevent mismatch)
        final_container_id = container_id
        final_sample_id = contents_data.sample_id
        
        contents = Contents(
            container_id=final_container_id,
            sample_id=final_sample_id,
            concentration=contents_data.concentration,
            concentration_units=contents_data.concentration_units,
            amount=contents_data.amount,
            amount_units=contents_data.amount_units
        )
        
        db.add(contents)
        
        # Flush to get any database errors immediately (foreign key violations, etc.)
        try:
            db.flush()
        except Exception as flush_error:
            db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error during flush: {str(flush_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while creating contents: {str(flush_error)}"
            )
        
        # Commit the transaction
        try:
            db.commit()
        except Exception as commit_error:
            db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error during commit: {str(commit_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while committing contents: {str(commit_error)}"
            )
        
        # Verify contents exists after commit using direct SQL query (bypasses session cache)
        from sqlalchemy import text
        verify_sql = text("""
            SELECT container_id, sample_id 
            FROM contents 
            WHERE container_id = :container_id AND sample_id = :sample_id
        """)
        verify_result = db.execute(verify_sql, {
            "container_id": str(final_container_id),
            "sample_id": str(final_sample_id)
        }).first()
        
        if not verify_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Contents was not found in database after commit. container_id={final_container_id}, sample_id={final_sample_id}"
            )
        
        # Also verify using ORM query
        verify_contents = db.query(Contents).filter(
            Contents.container_id == final_container_id,
            Contents.sample_id == final_sample_id
        ).first()
        
        if not verify_contents:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Contents was not found via ORM query after commit"
            )
        
        db.refresh(verify_contents)
        
        # Eagerly load sample relationship for response
        from sqlalchemy.orm import joinedload
        from models.sample import Sample
        contents = db.query(Contents).options(
            joinedload(Contents.sample)
        ).filter(
            Contents.container_id == final_container_id,
            Contents.sample_id == final_sample_id
        ).first()
        
        if not contents:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Contents not found after creation"
            )
        
        # Build response with sample data
        content_dict = {
            "container_id": contents.container_id,
            "sample_id": contents.sample_id,
            "concentration": contents.concentration,
            "concentration_units": contents.concentration_units,
            "amount": contents.amount,
            "amount_units": contents.amount_units,
        }
        if contents.sample:
            from app.schemas.sample import SampleResponse
            content_dict["sample"] = SampleResponse.model_validate(contents.sample)
        
        return ContentsResponse(**content_dict)
    except HTTPException:
        # Re-raise HTTP exceptions as-is (don't rollback, they're already handled)
        raise
    except Exception as e:
        db.rollback()
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error creating contents: {str(e)}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error args: {e.args}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link sample to container: {str(e)}"
        )


@router.patch("/{container_id}/contents/{sample_id}", response_model=ContentsResponse)
async def update_container_contents(
    container_id: UUID,
    sample_id: UUID,
    contents_data: ContentsUpdate,
    current_user: User = Depends(require_sample_update),
    db: Session = Depends(get_db)
):
    """
    Update contents of a container.
    """
    contents = db.query(Contents).filter(
        Contents.container_id == container_id,
        Contents.sample_id == sample_id
    ).first()
    
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contents not found"
        )
    
    # Update fields
    update_data = contents_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contents, field, value)
    
    db.commit()
    db.refresh(contents)
    
    return ContentsResponse.from_orm(contents)


@router.delete("/{container_id}/contents/{sample_id}")
async def remove_sample_from_container(
    container_id: UUID,
    sample_id: UUID,
    current_user: User = Depends(require_sample_update),
    db: Session = Depends(get_db)
):
    """
    Remove a sample from a container.
    """
    contents = db.query(Contents).filter(
        Contents.container_id == container_id,
        Contents.sample_id == sample_id
    ).first()
    
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contents not found"
        )
    
    db.delete(contents)
    db.commit()
    
    return {"message": "Sample removed from container successfully"}
