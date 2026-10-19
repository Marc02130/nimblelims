"""
Batches router for NimbleLims
"""
import os
from typing import List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, text, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from app.database import get_db
from models.batch import Batch, BatchContainer
from models.container import Container, Contents, ContainerType
from models.sample import Sample
from models.test import Test
from models.project import Project, ProjectUser
from models.user import User
from models.list import ListEntry
from app.schemas.batch import (
    BatchCreate, BatchUpdate, BatchResponse, BatchListResponse,
    BatchContainerRequest, BatchContainerResponse, BatchContainerBody,
    BatchCreateWithContainersRequest, BatchContainerRead, BatchContainerContentRead,
    BatchContentSample,
)
from app.schemas.test import TestResponse
from app.core.rbac import (
    require_batch_manage, require_batch_read, require_batch_update,
    require_batch_delete, require_project_access, validate_client_access
)
from app.core.security import get_current_user
from app.core.patch_fields import explicit_updates
from datetime import datetime, timezone

from app.core.lab_time import current_lab_day, days_from_today, resolve_lab_timezone
from app.schemas._dates import store_calendar_day
from uuid import UUID

router = APIRouter()


def batch_container_response(bc: BatchContainer) -> BatchContainerResponse:
    """Include the container id and its 1-based grid position."""
    container = bc.container
    body = None
    if container is not None:
        body = BatchContainerBody(
            id=container.id,
            name=container.name,
            row=container.row,
            column=container.column,
            type_id=container.type_id,
            concentration=float(container.concentration) if container.concentration is not None else None,
            concentration_units=container.concentration_units,
            amount=float(container.amount) if container.amount is not None else None,
            amount_units=container.amount_units,
        )
    return BatchContainerResponse(
        batch_id=bc.batch_id,
        container_id=bc.container_id,
        position=bc.position,
        notes=bc.notes,
        id=body.id if body is not None else bc.container_id,
        name=body.name if body is not None else None,
        row=body.row if body is not None else None,
        column=body.column if body is not None else None,
        type_id=body.type_id if body is not None else None,
        container=body,
    )


def build_batch_response(batch: Batch, batch_containers: list) -> BatchResponse:
    """
    Build a BatchResponse from a Batch model and its BatchContainer records.
    
    This helper is needed because the Batch model has a 'containers' relationship
    that points to Container objects (via secondary table), but BatchResponse.containers
    expects BatchContainerResponse objects. Using from_orm() directly would fail.
    """
    return BatchResponse(
        id=batch.id,
        name=batch.name,
        description=batch.description,
        type=batch.type,
        status=batch.status,
        start_date=batch.start_date,
        end_date=batch.end_date,
        custom_attributes=batch.custom_attributes or {},
        active=batch.active,
        created_at=batch.created_at,
        created_by=batch.created_by,
        modified_at=batch.modified_at,
        modified_by=batch.modified_by,
        containers=[batch_container_response(bc) for bc in batch_containers] if batch_containers else []
    )


@router.get("", response_model=BatchListResponse)
def get_batches(
    type: Optional[UUID] = Query(None, description="Filter by batch type ID"),
    status: Optional[UUID] = Query(None, description="Filter by status ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_batch_read),
    db: Session = Depends(get_db)
):
    """
    Get batches with filtering and pagination.
    Access control is enforced entirely by Row-Level Security (RLS) policies at the database level.
    No Python-level filtering is applied - RLS automatically filters batches based on project access.
    """
    # Build query with filters - RLS will automatically filter based on batches_access policy
    # No need for manual Python-level filtering - RLS handles:
    # - Admin users: see all batches
    # - System client users (lab employees): see all batches
    # - Client users: see batches containing samples from their client's projects
    query = db.query(Batch).filter(Batch.active == True)
    
    # Apply filters
    if type:
        query = query.filter(Batch.type == type)
    if status:
        query = query.filter(Batch.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    batches = query.offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size
    
    # Load containers for each batch
    batch_responses = []
    for batch in batches:
        batch_containers = db.query(BatchContainer).filter(
            BatchContainer.batch_id == batch.id
        ).all()
        batch_responses.append(build_batch_response(batch, batch_containers))
    
    return BatchListResponse(
        batches=batch_responses,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


_BATCH_FORBIDDEN = {
    "code": "batch_forbidden",
    "message": "Access denied",
}


def _visible_batch_or_http(db: Session, batch_id: UUID) -> Batch:
    """404 when the batch is missing. 403 when it exists and this session cannot see it.

    ``batch_access_status`` reads ``app.current_user_id`` and returns one word.
    The body of a 403 is that word's public message. It does not name a client
    or the batch.
    """
    seen = db.execute(
        text("SELECT public.batch_access_status(CAST(:batch_id AS uuid))"),
        {"batch_id": str(batch_id)},
    ).scalar()
    if seen == "forbidden":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_BATCH_FORBIDDEN,
        )
    if seen != "visible":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )
    batch = db.query(Batch).filter(
        Batch.id == batch_id,
        Batch.active == True,
    ).first()
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )
    return batch


def _links_caller_can_see(db: Session, batch_id: UUID) -> List[BatchContainer]:
    """Junction rows have no policy. Keep only containers this session can read."""
    links = db.query(BatchContainer).filter(BatchContainer.batch_id == batch_id).all()
    visible: List[BatchContainer] = []
    for link in links:
        container = db.query(Container).filter(
            Container.id == link.container_id,
            Container.active == True,
        ).first()
        if container is not None:
            visible.append(link)
    return visible


@router.get("/{batch_id}", response_model=BatchResponse)
def get_batch(
    batch_id: UUID,
    current_user: User = Depends(require_batch_read),
    db: Session = Depends(get_db)
):
    """
    Get a specific batch by ID.
    """
    del current_user
    batch = _visible_batch_or_http(db, batch_id)
    return build_batch_response(batch, _links_caller_can_see(db, batch.id))


def _active_batch_or_404(db: Session, batch_id: UUID) -> Batch:
    return _visible_batch_or_http(db, batch_id)


@router.get("/{batch_id}/containers", response_model=List[BatchContainerRead])
def get_batch_containers(
    batch_id: UUID,
    current_user: User = Depends(require_batch_read),
    db: Session = Depends(get_db),
):
    """
    Containers in a batch, with the samples Enter Results lists.

    GET was missing, so the page received 405 from POST /batches/{id}/containers.
    """
    del current_user
    batch = _active_batch_or_404(db, batch_id)

    links = _links_caller_can_see(db, batch.id)
    container_ids = [link.container_id for link in links]
    if not container_ids:
        return []

    containers = db.query(Container).filter(
        Container.id.in_(container_ids),
        Container.active == True,
    ).all()
    by_id = {container.id: container for container in containers}
    contents = db.query(Contents).options(joinedload(Contents.sample)).filter(
        Contents.container_id.in_(container_ids)
    ).all()
    contents_by_container: dict = {}
    for content in contents:
        contents_by_container.setdefault(content.container_id, []).append(content)

    result: List[BatchContainerRead] = []
    for link in links:
        container = by_id.get(link.container_id)
        if container is None:
            continue
        content_rows: List[BatchContainerContentRead] = []
        for content in contents_by_container.get(container.id, []):
            sample = content.sample
            sample_name = sample.name if sample is not None else None
            qc_type = sample.qc_type if sample is not None else None
            content_rows.append(BatchContainerContentRead(
                sample_id=content.sample_id,
                sample_name=sample_name,
                qc_type=qc_type,
                sample=BatchContentSample(qc_type=qc_type) if sample is not None else None,
            ))
        result.append(BatchContainerRead(
            id=container.id,
            name=container.name,
            row=container.row,
            column=container.column,
            contents=content_rows,
        ))
    return result


@router.get("/{batch_id}/tests", response_model=List[TestResponse])
def get_batch_tests(
    batch_id: UUID,
    current_user: User = Depends(require_batch_read),
    db: Session = Depends(get_db),
):
    """
    Active tests for samples in this batch.

    Enter Results calls this path. It did not exist (404). RLS on tests
    still hides rows the caller cannot see.
    """
    del current_user
    batch = _active_batch_or_404(db, batch_id)

    links = _links_caller_can_see(db, batch.id)
    container_ids = [link.container_id for link in links]
    if not container_ids:
        return []
    sample_ids = [
        row[0]
        for row in db.query(Contents.sample_id).filter(
            Contents.container_id.in_(container_ids),
            Contents.sample_id.isnot(None),
        ).distinct().all()
    ]
    if not sample_ids:
        return []
    tests = db.query(Test).filter(
        Test.sample_id.in_(sample_ids),
        Test.active == True,
    ).all()
    return [TestResponse.model_validate(test) for test in tests]


@router.post("/validate-compatibility")
def validate_batch_compatibility(
    data: dict,
    current_user: User = Depends(require_batch_manage),
    db: Session = Depends(get_db)
):
    """
    Validate compatibility of containers for cross-project batching.
    Returns compatibility status and details.
    
    Includes checks for:
    - Container existence and access
    - Shared analyses across samples
    - Expired samples (warns if any have days_until_expiration < 0)
    """
    from datetime import timedelta
    from models.analysis import Analysis
    
    container_ids = data.get("container_ids", [])
    
    if not container_ids or len(container_ids) < 2:
        return {
            "compatible": False,
            "error": "At least 2 containers are required for compatibility validation"
        }
    
    # Verify all containers exist
    containers = db.query(Container).filter(
        Container.id.in_(container_ids),
        Container.active == True
    ).all()
    
    if len(containers) != len(container_ids):
        found_ids = {c.id for c in containers}
        missing_ids = set(container_ids) - found_ids
        return {
            "compatible": False,
            "error": f"Containers not found: {missing_ids}"
        }
    
    # Get all samples in these containers via Contents junction
    sample_ids = db.query(Contents.sample_id).filter(
        Contents.container_id.in_(container_ids)
    ).distinct().all()
    sample_ids = [s[0] for s in sample_ids]
    
    if not sample_ids:
        return {
            "compatible": False,
            "error": "No samples found in the specified containers"
        }
    
    # Get all projects for these samples
    projects = db.query(Sample.project_id).filter(
        Sample.id.in_(sample_ids),
        Sample.active == True
    ).distinct().all()
    project_ids = [p[0] for p in projects]
    
    # Check RLS access for all projects
    inaccessible_projects = []
    for project_id in project_ids:
        result = db.execute(
            text("SELECT has_project_access(:project_id)"),
            {"project_id": str(project_id)}
        ).scalar()
        if not result:
            inaccessible_projects.append(project_id)
    
    if inaccessible_projects:
        return {
            "compatible": False,
            "error": "Access denied"
        }
    
    # Validate compatibility: check if samples share a common analysis
    tests = db.query(Test.analysis_id).filter(
        Test.sample_id.in_(sample_ids),
        Test.active == True
    ).distinct().all()
    analysis_ids = {t[0] for t in tests}
    
    if not analysis_ids:
        return {
            "compatible": False,
            "error": "No tests found for samples in the specified containers"
        }
    
    # Get analysis objects (need shelf_life for expiration check)
    analyses = db.query(Analysis).filter(
        Analysis.id.in_(analysis_ids),
        Analysis.active == True
    ).all()
    analysis_map = {a.id: a for a in analyses}
    
    # Group tests by sample to find common analyses
    sample_analyses = {}
    for sample_id in sample_ids:
        sample_tests = db.query(Test.analysis_id).filter(
            Test.sample_id == sample_id,
            Test.active == True
        ).all()
        sample_analyses[sample_id] = {t[0] for t in sample_tests}
    
    # Find common analyses across all samples
    if sample_analyses:
        common_analyses = set.intersection(*sample_analyses.values())
        
        if not common_analyses:
            analysis_names = {a.name for a in analyses if a.id in analysis_ids}
            return {
                "compatible": False,
                "error": "Incompatible samples: no shared analyses found",
                "details": {
                    "projects": [str(p) for p in project_ids],
                    "analyses": list(analysis_names),
                    "suggestion": "Samples must share at least one common analysis (e.g., prep method) for cross-project batching"
                }
            }
    else:
        return {
            "compatible": False,
            "error": "Unable to determine compatibility"
        }
    
    # Check for expired samples based on date_sampled + shelf_life
    zone_name = resolve_lab_timezone(db)
    expired_samples = []
    expiring_soon_samples = []
    
    # Get samples with their date_sampled
    samples = db.query(Sample).filter(
        Sample.id.in_(sample_ids),
        Sample.active == True
    ).all()
    
    for sample in samples:
        if not sample.date_sampled:
            continue
        
        # Get the minimum shelf_life from analyses assigned to this sample
        sample_analysis_ids = sample_analyses.get(sample.id, set())
        min_shelf_life = None
        for aid in sample_analysis_ids:
            analysis = analysis_map.get(aid)
            if analysis and analysis.shelf_life:
                if min_shelf_life is None or analysis.shelf_life < min_shelf_life:
                    min_shelf_life = analysis.shelf_life
        
        if min_shelf_life is None:
            continue
        
        # Compute expiration date and days until expiration
        expiration_date = sample.date_sampled + timedelta(days=min_shelf_life)
        days_until_expiration = days_from_today(expiration_date, zone_name)
        
        if days_until_expiration < 0:
            expired_samples.append({
                "sample_id": str(sample.id),
                "sample_name": sample.name,
                "days_expired": abs(days_until_expiration),
                "expiration_date": expiration_date.isoformat()
            })
        elif days_until_expiration <= 3:
            expiring_soon_samples.append({
                "sample_id": str(sample.id),
                "sample_name": sample.name,
                "days_until_expiration": days_until_expiration,
                "expiration_date": expiration_date.isoformat()
            })
    
    # Build response
    common_analysis_names = {a.name for a in analyses if a.id in common_analyses}
    warnings = []
    
    if expired_samples:
        warnings.append({
            "type": "expired_samples",
            "message": "Expired samples cannot be tested validly",
            "samples": expired_samples
        })
    
    if expiring_soon_samples:
        warnings.append({
            "type": "expiring_soon",
            "message": "Some samples are expiring soon",
            "samples": expiring_soon_samples
        })
    
    return {
        "compatible": True,
        "details": {
            "projects": [str(p) for p in project_ids],
            "common_analyses": list(common_analysis_names)
        },
        "warnings": warnings if warnings else None
    }


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    batch_data: BatchCreate,
    current_user: User = Depends(require_batch_manage),
    db: Session = Depends(get_db)
):
    """
    Create a new batch.
    Implements US-26: Cross-Project Batching.
    Supports cross-project batching with compatibility validation.
    Requires batch:manage permission.
    """
    # Generate name if not provided
    batch_name = batch_data.name
    if not batch_name:
        from app.core.name_generation import generate_name_for_batch
        try:
            batch_name = generate_name_for_batch(
                db=db,
                start_date=batch_data.start_date
            )
        except Exception as e:
            # Fallback to UUID if generation fails
            import uuid
            batch_name = str(uuid.uuid4())
    
    # Auto-detect cross-project if container_ids provided
    is_cross_project = batch_data.cross_project
    if batch_data.container_ids:
        if is_cross_project is None:
            is_cross_project = True  # Auto-detect as cross-project
    
    # If container_ids provided, validate cross-project compatibility
    if batch_data.container_ids:
        # Verify all containers exist
        containers = db.query(Container).filter(
            Container.id.in_(batch_data.container_ids),
            Container.active == True
        ).all()
        
        if len(containers) != len(batch_data.container_ids):
            found_ids = {c.id for c in containers}
            missing_ids = set(batch_data.container_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Containers not found: {missing_ids}"
            )
        
        # Get all samples in these containers via Contents junction
        sample_ids = db.query(Contents.sample_id).filter(
            Contents.container_id.in_(batch_data.container_ids)
        ).distinct().all()
        sample_ids = [s[0] for s in sample_ids]
        
        if not sample_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No samples found in the specified containers"
            )
        
        # Get all projects for these samples
        projects = db.query(Project).join(Sample, Project.id == Sample.project_id).filter(
            Sample.id.in_(sample_ids),
            Sample.active == True
        ).distinct().all()
        project_ids = [p.id for p in projects]
        
        # Check RLS access for all projects using SQL function
        # This handles admin, project_users, client_id, and client_projects
        inaccessible_projects = []
        for project_id in project_ids:
            # Use SQL function to check access (handles all RLS cases)
            result = db.execute(
                text("SELECT has_project_access(:project_id)"),
                {"project_id": str(project_id)}
            ).scalar()
            if not result:
                inaccessible_projects.append(project_id)
        
        if inaccessible_projects:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_BATCH_FORBIDDEN,
            )
        
        # Additional client isolation check: validate user has access to all projects' client_ids
        # For non-System/Admin users, ensure all projects belong to their client
        for project in projects:
            try:
                validate_client_access(current_user, project.client_id)
            except HTTPException:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=_BATCH_FORBIDDEN,
                )
        
        # Validate compatibility: check if samples share a common analysis
        # Get all tests for these samples
        tests = db.query(Test.analysis_id).filter(
            Test.sample_id.in_(sample_ids),
            Test.active == True
        ).distinct().all()
        analysis_ids = {t[0] for t in tests}
        
        if not analysis_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tests found for samples in the specified containers"
            )
        
        # Check compatibility: all samples should have at least one shared analysis
        # For cross-project batching, we require a shared prep analysis (e.g., 'EPA Method 8080 Prep')
        # Get analysis names to check for prep analyses
        from models.analysis import Analysis
        analyses = db.query(Analysis).filter(
            Analysis.id.in_(analysis_ids),
            Analysis.active == True
        ).all()
        
        # Check if there's a shared analysis across all samples
        # Group tests by sample to find common analyses
        sample_analyses = {}
        for sample_id in sample_ids:
            sample_tests = db.query(Test.analysis_id).filter(
                Test.sample_id == sample_id,
                Test.active == True
            ).all()
            sample_analyses[sample_id] = {t[0] for t in sample_tests}
        
        # Find common analyses across all samples
        if sample_analyses:
            common_analyses = set.intersection(*sample_analyses.values())
            
            # If divergent_analyses specified, check if they're in common_analyses
            if batch_data.divergent_analyses:
                divergent_set = set(batch_data.divergent_analyses)
                if divergent_set.intersection(common_analyses):
                    # These analyses require separate sub-batches
                    # For now, we'll create a note but still create the main batch
                    # Future: child_batch_id FK will be added for sub-batches
                    pass
            
            if not common_analyses:
                # Get analysis names for error message
                analysis_names = {a.name for a in analyses if a.id in analysis_ids}
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Incompatible samples: no shared analyses found",
                        # str(): UUIDs in an HTTPException detail are not
                        # JSON-serializable (this 400 used to surface as a 500)
                        "projects": [str(p) for p in project_ids],
                        "analyses": list(analysis_names),
                        "suggestion": "Samples must share at least one common analysis (e.g., prep method) for cross-project batching"
                    }
                )
    
    # Check QC requirement based on batch type and env var
    require_qc_types = os.getenv("REQUIRE_QC_FOR_BATCH_TYPES", "")
    require_qc_type_ids = []
    if require_qc_types:
        # Parse comma-separated UUIDs
        try:
            require_qc_type_ids = [UUID(t.strip()) for t in require_qc_types.split(",") if t.strip()]
        except ValueError:
            # Invalid UUID format, ignore
            pass
    
    # Check if QC is required for this batch type
    qc_required = False
    if batch_data.type and require_qc_type_ids and batch_data.type in require_qc_type_ids:
        qc_required = True
    
    # Validate QC additions if required
    if qc_required and (not batch_data.qc_additions or len(batch_data.qc_additions) == 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"QC samples are required for batch type {batch_data.type}. Please provide qc_additions."
        )
    
    # Get Laboratory QC project for QC samples - all batch QC samples go to this system project
    # This ensures QC samples are batch-level controls shared across all client projects
    LAB_QC_PROJECT_ID = UUID('00000000-0000-0000-0000-000000000002')
    qc_project_id = None
    first_sample = None
    
    if batch_data.qc_additions:
        # Verify the Laboratory QC project exists
        # (Project is imported at module level; a local import here made
        # `Project` function-local and raised UnboundLocalError earlier in
        # create_batch for container-based requests.)
        lab_qc_project = db.query(Project).filter(
            Project.id == LAB_QC_PROJECT_ID,
            Project.active == True
        ).first()
        
        if not lab_qc_project:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Laboratory QC project not found. Please run database migrations."
            )
        
        qc_project_id = LAB_QC_PROJECT_ID
        
        # Optionally get first sample from containers for inheriting sample_type/matrix
        if batch_data.container_ids:
            first_container_id = batch_data.container_ids[0]
            first_contents = db.query(Contents).filter(
                Contents.container_id == first_container_id
            ).first()
            if first_contents:
                first_sample = db.query(Sample).filter(
                    Sample.id == first_contents.sample_id,
                    Sample.active == True
                ).first()
        
        # Try to get first sample from sample_ids if not from containers
        if not first_sample and batch_data.sample_ids:
            first_sample = db.query(Sample).filter(
                Sample.id == batch_data.sample_ids[0],
                Sample.active == True
            ).first()
    
    # Validate status exists and is active
    if batch_data.status:
        status_entry = db.query(ListEntry).filter(
            ListEntry.id == batch_data.status,
            ListEntry.active == True
        ).first()
        if not status_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid batch status ID: {batch_data.status}"
            )
    
    # Validate custom_attributes (previously accepted by the schema but dropped)
    validated_custom_attributes = {}
    if batch_data.custom_attributes:
        from app.core.custom_attributes import validate_custom_attributes
        try:
            validated_custom_attributes = validate_custom_attributes(
                db, "batches", batch_data.custom_attributes
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    # Create batch
    batch = Batch(
        name=batch_name,
        description=batch_data.description,
        type=batch_data.type,
        status=batch_data.status,
        start_date=batch_data.start_date,
        end_date=batch_data.end_date,
        custom_attributes=validated_custom_attributes,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(batch)
    db.flush()  # Get the ID without committing
    
    # Add containers to batch if provided
    if batch_data.container_ids:
        for idx, container_id in enumerate(batch_data.container_ids):
            batch_container = BatchContainer(
                batch_id=batch.id,
                container_id=container_id,
                position=None,  # Can be set later if needed
                notes=None
            )
            db.add(batch_container)
    
    # Create QC samples if provided (US-27)
    # All QC creation happens atomically within the batch creation transaction
    if batch_data.qc_additions and qc_project_id:
        # Get "Received" status for QC samples
        from models.list import List
        sample_status_list = db.query(List).filter(
            List.name == "sample_status"
        ).first()
        
        if not sample_status_list:
            # Create sample_status list if it doesn't exist
            sample_status_list = List(
                name="sample_status",
                description="Sample status list",
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(sample_status_list)
            db.flush()
        
        received_status = db.query(ListEntry).filter(
            ListEntry.list_id == sample_status_list.id,
            ListEntry.name == "Received",
            ListEntry.active == True
        ).first()
        
        if not received_status:
            # Create "Received" status if it doesn't exist
            received_status = ListEntry(
                name="Received",
                description="Sample received",
                list_id=sample_status_list.id,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(received_status)
            db.flush()
            db.refresh(received_status)  # Ensure ID is available
        
        # Create QC samples - each QC addition specifies its own container
        for qc_idx, qc_addition in enumerate(batch_data.qc_additions):
            # Validate QC type exists
            qc_type_entry = db.query(ListEntry).filter(
                ListEntry.id == qc_addition.qc_type,
                ListEntry.active == True
            ).first()
            
            if not qc_type_entry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid QC type ID: {qc_addition.qc_type}"
                )
            
            # Generate QC sample name
            qc_sample_name = f"QC-{batch.name}-{qc_idx + 1}"
            
            # Validate received status exists
            if not received_status or not received_status.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot create QC sample: received status not found or invalid"
                )
            
            # Get sample_type for QC - inherit from first_sample or get default "QC" type
            qc_sample_type = None
            qc_due_date = first_sample.due_date if first_sample else None
            
            # Use the matrix provided by the user
            qc_matrix = qc_addition.matrix_id
            
            # Validate the matrix exists
            matrix_entry = db.query(ListEntry).filter(
                ListEntry.id == qc_matrix,
                ListEntry.active == True
            ).first()
            if not matrix_entry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid matrix ID for QC sample: {qc_matrix}"
                )
            
            if first_sample:
                # Inherit sample_type from existing sample
                qc_sample_type = first_sample.sample_type
            else:
                # Get or create default QC sample type - list name is "Sample Types"
                sample_type_list = db.query(List).filter(
                    List.name.in_(["Sample Types", "sample_type", "sample_types"])
                ).first()
                if sample_type_list:
                    qc_sample_type_entry = db.query(ListEntry).filter(
                        ListEntry.list_id == sample_type_list.id,
                        ListEntry.name.in_(["QC", "Quality Control"]),
                        ListEntry.active == True
                    ).first()
                    if qc_sample_type_entry:
                        qc_sample_type = qc_sample_type_entry.id
                    else:
                        # Get first sample type as fallback
                        first_type = db.query(ListEntry).filter(
                            ListEntry.list_id == sample_type_list.id,
                            ListEntry.active == True
                        ).first()
                        if first_type:
                            qc_sample_type = first_type.id
                
                # If sample_type is still None, raise an error since it's a required field
                if not qc_sample_type:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot create QC sample: No sample type found. Please configure a 'QC' or 'Quality Control' sample type in the Sample Types list."
                    )
            
            # Validate that the provided container type exists
            container_type = db.query(ContainerType).filter(
                ContainerType.id == qc_addition.container_type_id,
                ContainerType.active == True
            ).first()
            if not container_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Container type not found for QC sample: {qc_addition.container_type_id}"
                )
            
            # Create QC sample
            qc_sample = Sample(
                name=qc_sample_name,
                description=f"QC sample ({qc_type_entry.name})" + (f": {qc_addition.notes}" if qc_addition.notes else ""),
                due_date=qc_due_date,
                received_date=current_lab_day(),
                sample_type=qc_sample_type,  # Use inherited or default sample type
                status=received_status.id,
                matrix=qc_matrix,  # Use inherited or default matrix
                temperature=first_sample.temperature if first_sample else None,  # Inherit temperature if available
                project_id=qc_project_id,  # Use determined project ID
                qc_type=qc_addition.qc_type,  # Set QC type
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(qc_sample)
            db.flush()  # Get the ID without committing
            
            # Create a new container for the QC sample
            qc_container = Container(
                name=f"QC-{batch.name}-{qc_idx + 1}",
                description=f"Container for QC sample {qc_sample_name}",
                type_id=qc_addition.container_type_id,
                row=1,
                column=1,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(qc_container)
            db.flush()  # Get the container ID
            
            # Link QC sample to the new container via Contents
            qc_contents = Contents(
                container_id=qc_container.id,
                sample_id=qc_sample.id
            )
            db.add(qc_contents)
            
            # Link QC container to batch
            qc_batch_container = BatchContainer(
                batch_id=batch.id,
                container_id=qc_container.id,
                position=None,
                notes=qc_addition.notes
            )
            db.add(qc_batch_container)
    
    # Commit all changes atomically (batch, containers, QC samples, contents, batch_containers)
    # If any error occurs, the entire transaction is rolled back
    try:
        db.commit()
        db.refresh(batch)
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating batch: {str(e)}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Batch data: name={batch_name}, type={batch_data.type}, status={batch_data.status}")
        logger.error(f"Container IDs: {batch_data.container_ids}")
        logger.error(f"QC additions: {batch_data.qc_additions}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create batch: {str(e)}"
        )
    
    # Load containers for response
    batch_containers = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch.id
    ).all()
    
    return build_batch_response(batch, batch_containers)


@router.post("/with-containers", response_model=BatchResponse)
def create_batch_with_containers(
    batch_data: BatchCreateWithContainersRequest,
    current_user: User = Depends(require_batch_manage),
    db: Session = Depends(get_db)
):
    """
    Create a new batch with containers.
    Implements US-11: Create and Manage Batches.
    """
    # Generate name if not provided
    batch_name = batch_data.name
    if not batch_name:
        from app.core.name_generation import generate_name_for_batch
        try:
            batch_name = generate_name_for_batch(
                db=db,
                start_date=batch_data.start_date
            )
        except Exception as e:
            # Fallback to UUID if generation fails
            import uuid
            batch_name = str(uuid.uuid4())
    
    # Create batch
    batch = Batch(
        name=batch_name,
        description=batch_data.description,
        type=batch_data.type,
        status=batch_data.status,
        start_date=batch_data.start_date,
        end_date=batch_data.end_date,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(batch)
    db.flush()  # Get the ID without committing
    
    # Add containers to batch
    for container_req in batch_data.containers:
        # Verify container exists
        container = db.query(Container).filter(
            Container.id == container_req.container_id,
            Container.active == True
        ).first()
        
        if not container:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Container {container_req.container_id} not found"
            )
        
        batch_container = BatchContainer(
            batch_id=batch.id,
            container_id=container_req.container_id,
            position=container_req.position,
            notes=container_req.notes
        )
        db.add(batch_container)
    
    db.commit()
    db.refresh(batch)
    
    # Load batch containers for response
    batch_containers = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch.id
    ).all()
    
    return build_batch_response(batch, batch_containers)


@router.post("/{batch_id}/containers", response_model=BatchContainerResponse)
def add_container_to_batch(
    batch_id: UUID,
    container_data: BatchContainerRequest,
    current_user: User = Depends(require_batch_manage),
    db: Session = Depends(get_db)
):
    """
    Add a container to a batch.
    """
    batch = _visible_batch_or_http(db, batch_id)
    
    # Validate client access: check access to the container's sample's project
    container = db.query(Container).filter(
        Container.id == container_data.container_id,
        Container.active == True
    ).first()
    
    if container:
        # Get sample from container
        content = db.query(Contents).filter(
            Contents.container_id == container.id
        ).first()
        
        if content:
            sample = db.query(Sample).filter(
                Sample.id == content.sample_id,
                Sample.active == True
            ).first()
            
            if sample:
                project = db.query(Project).filter(Project.id == sample.project_id).first()
                if project:
                    validate_client_access(current_user, project.client_id)
    
    # Verify container exists
    container = db.query(Container).filter(
        Container.id == container_data.container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container not found"
        )
    
    # Check if container is already in batch
    existing = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch_id,
        BatchContainer.container_id == container_data.container_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container is already in this batch"
        )
    
    # Add container to batch
    batch_container = BatchContainer(
        batch_id=batch_id,
        container_id=container_data.container_id,
        position=container_data.position,
        notes=container_data.notes
    )
    
    db.add(batch_container)
    db.commit()
    db.refresh(batch_container)
    
    return batch_container_response(batch_container)


@router.patch("/{batch_id}", response_model=BatchResponse)
def update_batch(
    batch_id: UUID,
    batch_data: BatchUpdate,
    current_user: User = Depends(require_batch_update),
    db: Session = Depends(get_db)
):
    """
    Update a batch.
    Requires batch:update permission.
    """
    batch = _visible_batch_or_http(db, batch_id)
    
    # Validate client access: check access to all projects in the batch
    # Get all containers in batch
    batch_containers = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch.id
    ).all()
    container_ids = [bc.container_id for bc in batch_containers]
    
    if container_ids:
        # Get all samples from batch containers
        contents = db.query(Contents).filter(
            Contents.container_id.in_(container_ids)
        ).all()
        sample_ids = [c.sample_id for c in contents if c.sample_id]
        
        if sample_ids:
            # Get all unique projects for these samples
            projects = db.query(Sample.project_id).filter(
                Sample.id.in_(sample_ids),
                Sample.active == True
            ).distinct().all()
            project_ids = [p[0] for p in projects]
            
            # Validate client access for all projects
            from models.project import Project
            projects_objs = db.query(Project).filter(Project.id.in_(project_ids)).all()
            for project in projects_objs:
                try:
                    validate_client_access(current_user, project.client_id)
                except HTTPException:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=_BATCH_FORBIDDEN,
                    )
    
    update_data = explicit_updates(batch_data, batch, refuse_null={"active"})
    if 'custom_attributes' in update_data and update_data['custom_attributes'] is not None:
        from app.core.custom_attributes import validate_custom_attributes
        try:
            validated_custom_attributes = validate_custom_attributes(
                db, "batches", update_data['custom_attributes']
            )
            update_data['custom_attributes'] = validated_custom_attributes
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    # Update fields
    for field, value in update_data.items():
        setattr(batch, field, value)
    
    batch.modified_by = current_user.id
    batch.modified_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(batch)
    
    # Load batch containers for response
    batch_containers = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch.id
    ).all()
    
    return build_batch_response(batch, batch_containers)


_BATCH_STATUS_LIST = "batch_status"
_IN_PROCESS_NAME = "in process"
_COMPLETED_NAME = "completed"


def calendar_stamp_for_batch_status(db: Session, status_entry: ListEntry) -> Optional[str]:
    """Which calendar column a batch_status entry writes.

    ``start`` when the entry name is In Process, ``end`` when it is Completed,
    otherwise None. The parent list must be named ``batch_status``. The entry
    id is not compared to a fixed string. ``list_entries.code`` is not used:
    that column only allows ``positive`` and ``negative``.
    """
    from models.list import List as ListModel

    parent = (
        db.query(ListModel).filter(ListModel.id == status_entry.list_id).one_or_none()
    )
    if parent is None or parent.name != _BATCH_STATUS_LIST:
        return None
    if status_entry.name is None:
        return None
    label = status_entry.name.strip().casefold()
    if label == _IN_PROCESS_NAME:
        return "start"
    if label == _COMPLETED_NAME:
        return "end"
    return None


@router.patch("/{batch_id}/status", response_model=BatchResponse)
def update_batch_status(
    batch_id: UUID,
    status_id: UUID,
    current_user: User = Depends(require_batch_update),
    db: Session = Depends(get_db)
):
    """
    Update batch status.
    Implements US-11: Create and Manage Batches status flow.
    """
    batch = _visible_batch_or_http(db, batch_id)
    
    # Validate status exists
    from models.list import ListEntry
    status_entry = db.query(ListEntry).filter(
        ListEntry.id == status_id,
        ListEntry.active == True
    ).first()
    
    if not status_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status ID"
        )
    
    # Update status and dates. Match the batch_status entry's name.
    # A UUID never equals the strings "in_process" or "completed", so those
    # comparisons never wrote start_date or end_date.
    batch.status = status_id
    stamp = calendar_stamp_for_batch_status(db, status_entry)
    if stamp is not None:
        lab_day = store_calendar_day(datetime.now(timezone.utc))
        if stamp == "start":
            batch.start_date = lab_day
        elif stamp == "end":
            batch.end_date = lab_day

    batch.modified_by = current_user.id
    batch.modified_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(batch)
    
    # Load batch containers for response
    batch_containers = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch.id
    ).all()
    
    return build_batch_response(batch, batch_containers)


@router.delete("/{batch_id}")
def delete_batch(
    batch_id: UUID,
    current_user: User = Depends(require_batch_delete),
    db: Session = Depends(get_db)
):
    """
    Soft delete a batch (set active=False).
    Requires batch:delete permission.
    """
    batch = _visible_batch_or_http(db, batch_id)
    
    # Soft delete
    batch.active = False
    batch.modified_by = current_user.id
    batch.modified_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"message": "Batch deleted successfully"}


@router.delete("/{batch_id}/containers/{container_id}")
def remove_container_from_batch(
    batch_id: UUID,
    container_id: UUID,
    current_user: User = Depends(require_batch_manage),
    db: Session = Depends(get_db)
):
    """
    Remove a container from a batch.
    """
    _visible_batch_or_http(db, batch_id)
    batch_container = db.query(BatchContainer).filter(
        BatchContainer.batch_id == batch_id,
        BatchContainer.container_id == container_id
    ).first()
    
    if not batch_container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found in batch"
        )
    
    db.delete(batch_container)
    db.commit()
    
    return {"message": "Container removed from batch successfully"}
