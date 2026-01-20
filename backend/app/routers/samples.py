"""
Samples router for NimbleLims
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, case, text, literal_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import cast
from app.database import get_db
from models.sample import Sample
from models.project import Project
from models.user import User
from models.test import Test
from models.analysis import Analysis
from app.schemas.sample import (
    SampleCreate, SampleUpdate, SampleResponse, SampleListResponse,
    SampleAccessioningRequest, BulkSampleAccessioningRequest,
    EligibleSampleResponse, EligibleSamplesResponse
)
from app.core.rbac import (
    require_sample_create, require_sample_read, require_sample_update,
    require_sample_delete, require_project_access
)
from app.core.security import get_current_user
from datetime import datetime, timedelta
from uuid import UUID

router = APIRouter()


@router.get("/eligible", response_model=EligibleSamplesResponse)
async def get_eligible_samples(
    request: Request,
    test_ids: Optional[str] = Query(None, description="Comma-separated list of test/analysis IDs to filter by"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    include_expired: bool = Query(False, description="Include expired samples in results"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_sample_read),
    db: Session = Depends(get_db)
):
    """
    Get samples eligible for testing with prioritization based on expiration and due dates.
    
    Returns samples sorted by:
    1. days_until_expiration ASC NULLS LAST (most urgent first)
    2. days_until_due ASC NULLS LAST (earliest due first)
    
    Computes:
    - days_until_expiration = (date_sampled + shelf_life) - now
    - days_until_due = coalesce(sample.due_date, project.due_date) - now
    - is_expired = days_until_expiration < 0
    - is_overdue = days_until_due < 0
    
    Query Parameters:
    - test_ids: Comma-separated analysis IDs to filter samples that have tests for these analyses
    - project_id: Filter by specific project
    - include_expired: If False (default), excludes samples with days_until_expiration < 0
    - page/size: Pagination
    
    RLS enforces access via has_project_access.
    """
    # Parse test_ids (analysis IDs)
    analysis_ids = []
    if test_ids and test_ids.strip():
        try:
            analysis_ids = [UUID(tid.strip()) for tid in test_ids.split(",") if tid.strip()]
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid test_ids format. Expected comma-separated UUIDs."
            )
    
    # Parse project_id
    project_id_uuid = None
    if project_id and project_id.strip():
        try:
            project_id_uuid = UUID(project_id)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project_id format. Expected UUID."
            )
    
    # Build base query with project join for due_date inheritance
    # We need to join with tests and analyses to get shelf_life for expiration calculation
    now = datetime.utcnow()
    
    # Subquery to get the minimum shelf_life analysis for each sample
    # This ensures we use the most restrictive (shortest) shelf_life
    if analysis_ids:
        # Filter by specific analyses
        shelf_life_subq = (
            db.query(
                Test.sample_id,
                func.min(Analysis.shelf_life).label('min_shelf_life'),
                func.min(Analysis.id).label('analysis_id'),
                func.min(Analysis.name).label('analysis_name')
            )
            .join(Analysis, Test.analysis_id == Analysis.id)
            .filter(Test.active == True)
            .filter(Analysis.active == True)
            .filter(Test.analysis_id.in_(analysis_ids))
            .group_by(Test.sample_id)
            .subquery()
        )
    else:
        # All analyses
        shelf_life_subq = (
            db.query(
                Test.sample_id,
                func.min(Analysis.shelf_life).label('min_shelf_life'),
                func.min(Analysis.id).label('analysis_id'),
                func.min(Analysis.name).label('analysis_name')
            )
            .join(Analysis, Test.analysis_id == Analysis.id)
            .filter(Test.active == True)
            .filter(Analysis.active == True)
            .group_by(Test.sample_id)
            .subquery()
        )
    
    # Main query with computed prioritization fields
    query = (
        db.query(
            Sample,
            Project.name.label('project_name'),
            Project.due_date.label('project_due_date'),
            shelf_life_subq.c.min_shelf_life.label('shelf_life'),
            shelf_life_subq.c.analysis_id.label('analysis_id'),
            shelf_life_subq.c.analysis_name.label('analysis_name'),
        )
        .join(Project, Sample.project_id == Project.id)
        .outerjoin(shelf_life_subq, Sample.id == shelf_life_subq.c.sample_id)
        .filter(Sample.active == True)
    )
    
    # Apply project filter
    if project_id_uuid:
        query = query.filter(Sample.project_id == project_id_uuid)
    
    # If analysis_ids provided, filter to samples that have tests for those analyses
    if analysis_ids:
        sample_ids_with_tests = (
            db.query(Test.sample_id)
            .filter(Test.analysis_id.in_(analysis_ids))
            .filter(Test.active == True)
            .distinct()
            .subquery()
        )
        query = query.filter(Sample.id.in_(db.query(sample_ids_with_tests.c.sample_id)))
    
    # Get all results for processing (RLS handles access control)
    all_results = query.all()
    
    # Process results and compute prioritization fields
    eligible_samples = []
    warnings = []
    expired_count = 0
    overdue_count = 0
    
    for row in all_results:
        sample = row[0]  # Sample object
        project_name = row.project_name
        project_due_date = row.project_due_date
        shelf_life = row.shelf_life
        analysis_id = row.analysis_id
        analysis_name = row.analysis_name
        
        # Compute effective due date (sample > project)
        effective_due_date = sample.due_date if sample.due_date else project_due_date
        
        # Compute days_until_due
        days_until_due = None
        is_overdue = False
        if effective_due_date:
            delta = effective_due_date - now
            days_until_due = delta.days
            is_overdue = days_until_due < 0
            if is_overdue:
                overdue_count += 1
        
        # Compute days_until_expiration
        days_until_expiration = None
        is_expired = False
        expiration_warning = None
        
        if sample.date_sampled and shelf_life:
            expiration_date = sample.date_sampled + timedelta(days=shelf_life)
            delta = expiration_date - now
            days_until_expiration = delta.days
            is_expired = days_until_expiration < 0
            
            if is_expired:
                expired_count += 1
                expiration_warning = f"Sample expired {abs(days_until_expiration)} days ago"
            elif days_until_expiration <= 3:
                expiration_warning = f"Sample expires in {days_until_expiration} days"
        
        # Skip expired samples if not including them
        if is_expired and not include_expired:
            continue
        
        eligible_samples.append({
            'id': sample.id,
            'name': sample.name,
            'description': sample.description,
            'due_date': sample.due_date,
            'received_date': sample.received_date,
            'date_sampled': sample.date_sampled,
            'sample_type': sample.sample_type,
            'status': sample.status,
            'matrix': sample.matrix,
            'project_id': sample.project_id,
            'qc_type': sample.qc_type,
            'days_until_expiration': days_until_expiration,
            'days_until_due': days_until_due,
            'is_expired': is_expired,
            'is_overdue': is_overdue,
            'expiration_warning': expiration_warning,
            'analysis_id': analysis_id,
            'analysis_name': analysis_name,
            'shelf_life': shelf_life,
            'project_name': project_name,
            'project_due_date': project_due_date,
            'effective_due_date': effective_due_date,
        })
    
    # Sort by days_until_expiration ASC NULLS LAST, then days_until_due ASC NULLS LAST
    def sort_key(s):
        # None values should sort last (use a large number)
        exp = s['days_until_expiration'] if s['days_until_expiration'] is not None else float('inf')
        due = s['days_until_due'] if s['days_until_due'] is not None else float('inf')
        return (exp, due)
    
    eligible_samples.sort(key=sort_key)
    
    # Add warnings
    if expired_count > 0:
        warnings.append(f"{expired_count} expired sample(s) found")
    if overdue_count > 0:
        warnings.append(f"{overdue_count} overdue sample(s) found")
    
    # Apply pagination
    total = len(eligible_samples)
    offset = (page - 1) * size
    paginated_samples = eligible_samples[offset:offset + size]
    pages = (total + size - 1) // size if total > 0 else 1
    
    return EligibleSamplesResponse(
        samples=[EligibleSampleResponse(**s) for s in paginated_samples],
        total=total,
        page=page,
        size=size,
        pages=pages,
        warnings=warnings
    )


def _create_tests_for_sample(
    db: Session,
    sample: Sample,
    battery_id: Optional[UUID],
    assigned_tests: List[UUID],
    in_process_status_id: UUID,
    current_user_id: UUID
):
    """
    Helper function to create tests for a sample.
    Shared between single and bulk accessioning.
    """
    from models.test import Test
    from models.test_battery import TestBattery, BatteryAnalysis
    
    # Handle battery assignment (creates tests for all analyses in battery)
    if battery_id:
        # Verify battery exists and is active
        battery = db.query(TestBattery).filter(
            TestBattery.id == battery_id,
            TestBattery.active == True
        ).first()
        
        if not battery:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test battery not found or inactive"
            )
        
        # Get all analyses in battery, ordered by sequence
        battery_analyses = db.query(BatteryAnalysis).filter(
            BatteryAnalysis.battery_id == battery_id
        ).order_by(BatteryAnalysis.sequence).all()
        
        if not battery_analyses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test battery has no analyses assigned"
            )
        
        # Create tests for each analysis in the battery (in sequence order)
        for battery_analysis in battery_analyses:
            test = Test(
                name=f"{sample.name}_test_{battery_analysis.analysis_id}",
                sample_id=sample.id,
                analysis_id=battery_analysis.analysis_id,
                status=in_process_status_id,
                technician_id=current_user_id,
                created_by=current_user_id,
                modified_by=current_user_id
            )
            db.add(test)
    
    # Also handle individual test assignments (if provided)
    if assigned_tests:
        for analysis_id in assigned_tests:
            # Check if test already exists (from battery assignment)
            existing_test = db.query(Test).filter(
                Test.sample_id == sample.id,
                Test.analysis_id == analysis_id,
                Test.active == True
            ).first()
            
            if not existing_test:
                test = Test(
                    name=f"{sample.name}_test_{analysis_id}",
                    sample_id=sample.id,
                    analysis_id=analysis_id,
                    status=in_process_status_id,
                    technician_id=current_user_id,
                    created_by=current_user_id,
                    modified_by=current_user_id
                )
                db.add(test)


@router.get("", response_model=SampleListResponse)
async def get_samples(
    request: Request,
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status ID"),
    qc_type: Optional[str] = Query(None, description="Filter by QC type ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_sample_read),
    db: Session = Depends(get_db)
):
    """
    Get samples with filtering and pagination.
    Scoped by user access (clients see only their projects).
    """
    # Convert empty strings to None and parse UUIDs
    project_id_uuid = None
    status_uuid = None
    qc_type_uuid = None
    
    if project_id and project_id.strip():
        try:
            project_id_uuid = UUID(project_id)
        except (ValueError, AttributeError):
            pass
    
    if status and status.strip():
        try:
            status_uuid = UUID(status)
        except (ValueError, AttributeError):
            pass
    
    if qc_type and qc_type.strip():
        try:
            qc_type_uuid = UUID(qc_type)
        except (ValueError, AttributeError):
            pass
    
    # Build query with filters - eagerly load project relationship for SampleResponse
    # RLS policies handle access control at the database level, so we don't need Python-level filtering
    from sqlalchemy.orm import joinedload
    query = db.query(Sample).options(joinedload(Sample.project)).filter(Sample.active == True)
    
    # Note: RLS policy samples_access handles access control via has_project_access(project_id)
    # No need for Python-level filtering - RLS will automatically filter based on:
    # - Admin users: see all samples
    # - Lab users: see samples from projects in project_users table
    # - Client users: see samples from their client's projects
    
    # Apply filters
    if project_id_uuid:
        query = query.filter(Sample.project_id == project_id_uuid)
    if status_uuid:
        query = query.filter(Sample.status == status_uuid)
    if qc_type_uuid:
        query = query.filter(Sample.qc_type == qc_type_uuid)
    
    # Parse and apply custom_attributes filters (e.g., ?custom.ph_level=7.0)
    # Note: Attribute names are case-sensitive and must match exactly as stored in database
    # To find the correct attribute name, check the custom_attributes_config table
    custom_filters = {}
    # Load all custom attribute configs once for efficient lookup
    from models.custom_attributes_config import CustomAttributeConfig
    attr_configs = db.query(CustomAttributeConfig).filter(
        CustomAttributeConfig.entity_type == 'samples',
        CustomAttributeConfig.active == True
    ).all()
    # Create a case-insensitive lookup map
    attr_name_map = {config.attr_name.lower(): config.attr_name for config in attr_configs}
    
    for key, value in request.query_params.items():
        if key.startswith('custom.'):
            attr_name = key[7:]  # Remove 'custom.' prefix
            # Try to find matching attribute name in configs (case-insensitive lookup)
            # Also handle partial matches (e.g., "ph" matching "pH" or "ph_level")
            actual_attr_name = None
            
            # First try exact case-insensitive match
            if attr_name.lower() in attr_name_map:
                actual_attr_name = attr_name_map[attr_name.lower()]
            else:
                # Try partial match - check if any config attr_name contains the filter name (case-insensitive)
                # This handles "ph" matching "pH" or "ph_level"
                for config in attr_configs:
                    config_name_lower = config.attr_name.lower()
                    filter_name_lower = attr_name.lower()
                    # Check if filter name is a prefix or exact match (case-insensitive)
                    if (config_name_lower == filter_name_lower or 
                        config_name_lower.startswith(filter_name_lower) or
                        filter_name_lower.startswith(config_name_lower.replace('_', '').replace('-', ''))):
                        actual_attr_name = config.attr_name
                        break
            
            # If no match found, use the provided name as-is
            if actual_attr_name is None:
                actual_attr_name = attr_name
            
            # Try to parse as number, otherwise keep as string
            try:
                if '.' in value:
                    custom_filters[actual_attr_name] = float(value)
                else:
                    custom_filters[actual_attr_name] = int(value)
            except ValueError:
                custom_filters[actual_attr_name] = value
    
    # Apply custom_attributes JSONB filters
    if custom_filters:
        for attr_name, attr_value in custom_filters.items():
            filter_dict = {attr_name: attr_value}
            query = query.filter(
                Sample.custom_attributes.op("@>")(cast(filter_dict, JSONB))
            )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    samples = query.offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size
    
    return SampleListResponse(
        samples=[SampleResponse.model_validate(sample) for sample in samples],
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/{sample_id}", response_model=SampleResponse)
async def get_sample(
    sample_id: UUID,
    current_user: User = Depends(require_sample_read),
    db: Session = Depends(get_db)
):
    """
    Get a specific sample by ID.
    Scoped by user access.
    """
    from sqlalchemy import text
    
    sample = db.query(Sample).filter(
        Sample.id == sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Check project access using has_project_access function (handles admin, client, and lab tech access)
    if current_user.role.name != "Administrator":
        result = db.execute(
            text("SELECT has_project_access(:project_id)"),
            {"project_id": str(sample.project_id)}
        ).scalar()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    return SampleResponse.model_validate(sample)


@router.post("/", response_model=SampleResponse)
async def create_sample(
    sample_data: SampleCreate,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Create a new sample.
    Requires sample:create permission.
    """
    # Check project access
    if current_user.role.name != "Administrator":
        from models.project import ProjectUser
        project_access = db.query(ProjectUser).filter(
            ProjectUser.project_id == sample_data.project_id,
            ProjectUser.user_id == current_user.id
        ).first()
        
        if not project_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Validate custom_attributes if provided
    validated_custom_attributes = {}
    if sample_data.custom_attributes:
        from app.core.custom_attributes import validate_custom_attributes
        validated_custom_attributes = validate_custom_attributes(
            db=db,
            entity_type='samples',
            custom_attributes=sample_data.custom_attributes
        )
    
    # Generate name if not provided
    sample_name = sample_data.name
    if not sample_name:
        from app.core.name_generation import generate_name_for_sample
        try:
            sample_name = generate_name_for_sample(
                db=db,
                project_id=sample_data.project_id,
                received_date=sample_data.received_date
            )
        except Exception as e:
            # Fallback to UUID if generation fails
            import uuid
            sample_name = str(uuid.uuid4())
    
    # Create sample
    sample = Sample(
        name=sample_name,
        description=sample_data.description,
        due_date=sample_data.due_date,
        received_date=sample_data.received_date,
        report_date=sample_data.report_date,
        sample_type=sample_data.sample_type,
        status=sample_data.status,
        matrix=sample_data.matrix,
        temperature=sample_data.temperature,
        parent_sample_id=sample_data.parent_sample_id,
        project_id=sample_data.project_id,
        qc_type=sample_data.qc_type,
        custom_attributes=validated_custom_attributes,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(sample)
    db.commit()
    db.refresh(sample)
    
    return SampleResponse.model_validate(sample)


@router.post("/accession", response_model=SampleResponse)
async def accession_sample(
    accession_data: SampleAccessioningRequest,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Accession a new sample with test assignment.
    Implements US-1: Sample Accessioning workflow.
    Supports project auto-creation if project_id is not provided.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Accessioning sample for user {current_user.id}, client_id={accession_data.client_id}, client_project_id={accession_data.client_project_id}")
        
        from models.client import Client, ClientProject
        from models.list import List, ListEntry
        from models.project import ProjectUser
        from app.core.name_generation import generate_name_for_sample, generate_name_for_project
        
        # Validate client_id is accessible (via RLS)
        client = db.query(Client).filter(Client.id == accession_data.client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Client not found or inaccessible"
            )
        
        # Verify client_project_id if provided (validate against client)
        if accession_data.client_project_id:
            client_project = db.query(ClientProject).filter(
                ClientProject.id == accession_data.client_project_id,
                ClientProject.active == True
            ).first()
            
            if not client_project:
                logger.warning(f"Client project {accession_data.client_project_id} not found or inactive")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Client project not found or inactive"
                )
            
            # Verify client_project belongs to the specified client
            if client_project.client_id != accession_data.client_id:
                logger.warning(f"Client project {accession_data.client_project_id} belongs to client {client_project.client_id}, but request specified {accession_data.client_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Client project does not belong to the specified client"
                )
        
        # Determine project_id - either use provided or auto-create
        project_id = accession_data.project_id
    
        if not project_id:
            logger.info("Auto-creating project")
            # Auto-create project
            # Get "Active" status for projects
            project_status_list = db.query(List).filter(List.name == "project_status").first()
            if not project_status_list:
                logger.error("Project status list not found")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project status list not found in configuration"
                )
            
            active_status = db.query(ListEntry).filter(
                ListEntry.list_id == project_status_list.id,
                ListEntry.name == "Active"
            ).first()
            
            if not active_status:
                logger.error("Project status 'Active' not found")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project status 'Active' not found in configuration"
                )
            
            # Generate project name
            project_name = generate_name_for_project(
                db=db,
                client_id=str(accession_data.client_id),
                start_date=accession_data.received_date
            )
            logger.info(f"Generated project name: {project_name}")
            
            # Create new project
            new_project = Project(
                name=project_name,
                description=None,
                start_date=accession_data.received_date,
                client_id=accession_data.client_id,
                client_project_id=accession_data.client_project_id,
                status=active_status.id,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(new_project)
            db.flush()  # Get the ID without committing
            project_id = new_project.id
            project = new_project  # Set project variable for use later
            logger.info(f"Created project {project_id}")
            
            # Grant current user access to the new project
            project_user = ProjectUser(
                project_id=project_id,
                user_id=current_user.id
            )
            db.add(project_user)
        else:
            # Verify project exists and user has access
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found"
                )
            
            # Check project access (unless admin)
            if current_user.role.name != "Administrator":
                project_access = db.query(ProjectUser).filter(
                    ProjectUser.project_id == project_id,
                    ProjectUser.user_id == current_user.id
                ).first()
                
                if not project_access:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: insufficient project permissions"
                    )
            
            # Verify project belongs to the specified client
            if project.client_id != accession_data.client_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Project does not belong to the specified client"
                )
    
        # Link project to client_project if provided
        if accession_data.client_project_id and not project.client_project_id:
            project.client_project_id = accession_data.client_project_id
        
        # Get initial status (e.g., "Received")
        sample_status_list = db.query(List).filter(List.name == "sample_status").first()
        if not sample_status_list:
            logger.error("Sample status list not found")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sample status list not found in configuration"
            )
        
        received_status = db.query(ListEntry).filter(
            ListEntry.list_id == sample_status_list.id,
            ListEntry.name == "Received"
        ).first()
        
        if not received_status:
            logger.error("Sample status 'Received' not found")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sample status 'Received' not found in configuration"
            )
        
        # Generate sample name if not provided
        sample_name = accession_data.name
        if not sample_name:
            sample_name = generate_name_for_sample(
                db=db,
                project_id=str(project_id),
                received_date=accession_data.received_date
            )
            logger.info(f"Generated sample name: {sample_name}")
    
        # Create sample
        sample = Sample(
                name=sample_name,
            description=accession_data.description,
            due_date=accession_data.due_date,
            received_date=accession_data.received_date,
            sample_type=accession_data.sample_type,
            status=received_status.id,
            matrix=accession_data.matrix,
            temperature=accession_data.temperature,
                project_id=project_id,
            qc_type=accession_data.qc_type,
                custom_attributes=accession_data.custom_attributes or {},
            created_by=current_user.id,
            modified_by=current_user.id
        )
        
        db.add(sample)
        db.flush()  # Get the ID without committing
        
        # Get "In Process" status for tests
        test_status_list = db.query(List).filter(List.name == "test_status").first()
        if not test_status_list:
            logger.error("Test status list not found")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test status list not found in configuration"
            )
        
        in_process_status = db.query(ListEntry).filter(
                ListEntry.list_id == test_status_list.id,
            ListEntry.name == "In Process"
        ).first()
        
        if not in_process_status:
            logger.error("Test status 'In Process' not found")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test status 'In Process' not found in configuration"
            )
        
        # Create tests using shared helper function
        _create_tests_for_sample(
            db=db,
            sample=sample,
            battery_id=accession_data.battery_id,
            assigned_tests=accession_data.assigned_tests,
            in_process_status_id=in_process_status.id,
            current_user_id=current_user.id
        )
        
        db.commit()
        db.refresh(sample)
        
        # Eagerly load project relationship to populate client_id in response
        from sqlalchemy.orm import joinedload
        sample = db.query(Sample).options(joinedload(Sample.project)).filter(Sample.id == sample.id).first()
        
        logger.info(f"Successfully accessioned sample {sample.id}")
        return SampleResponse.model_validate(sample)
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error during sample accession: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during sample accession: {str(e)}"
        )


@router.post("/bulk-accession", response_model=List[SampleResponse])
async def bulk_accession_samples(
    bulk_data: BulkSampleAccessioningRequest,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Bulk accession multiple samples with test assignment.
    Implements US-24: Bulk Sample Accessioning.
    Creates samples, containers, contents, and tests in a single transaction.
    Supports project auto-creation if project_id is not provided.
    """
    from models.client import Client, ClientProject
    from models.list import List, ListEntry
    from models.project import ProjectUser
    from models.container import ContainerType
    from app.core.name_generation import generate_name_for_sample, generate_name_for_project
    
    # Validate client_id is accessible (via RLS)
    client = db.query(Client).filter(Client.id == bulk_data.client_id).first()
    if not client:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
            detail="Client not found or inaccessible"
        )
    
    # Verify client_project_id if provided (validate against client)
    if bulk_data.client_project_id:
        client_project = db.query(ClientProject).filter(
            ClientProject.id == bulk_data.client_project_id,
            ClientProject.active == True
        ).first()
        
        if not client_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client project not found or inactive"
            )
        
        # Verify client_project belongs to the specified client
        if client_project.client_id != bulk_data.client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client project does not belong to the specified client"
            )
    
    # Validate container type exists
    container_type = db.query(ContainerType).filter(
        ContainerType.id == bulk_data.container_type_id,
        ContainerType.active == True
    ).first()
    
    if not container_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid container type ID"
        )
    
    # Determine project_id - either use provided or auto-create
    project_id = bulk_data.project_id
    
    if not project_id:
        # Auto-create project
        # Get "Active" status for projects
        project_status_list = db.query(List).filter(List.name == "project_status").first()
        if not project_status_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project status list not found in configuration"
            )
        
        active_status = db.query(ListEntry).filter(
            ListEntry.list_id == project_status_list.id,
            ListEntry.name == "Active"
        ).first()
        
        if not active_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project status 'Active' not found in configuration"
            )
        
        # Generate project name
        project_name = generate_name_for_project(
            db=db,
            client_id=str(bulk_data.client_id),
            start_date=bulk_data.received_date
            )
        
        # Create new project
        new_project = Project(
            name=project_name,
            description=None,
            start_date=bulk_data.received_date,
            client_id=bulk_data.client_id,
            client_project_id=bulk_data.client_project_id,
            status=active_status.id,
            created_by=current_user.id,
            modified_by=current_user.id
        )
        db.add(new_project)
        db.flush()  # Get the ID without committing
        project_id = new_project.id
        
        # Grant current user access to the new project
        project_user = ProjectUser(
            project_id=project_id,
            user_id=current_user.id
        )
        db.add(project_user)
    else:
        # Verify project exists and user has access
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check project access (unless admin)
        if current_user.role.name != "Administrator":
            project_access = db.query(ProjectUser).filter(
                ProjectUser.project_id == project_id,
                ProjectUser.user_id == current_user.id
            ).first()
            
            if not project_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: insufficient project permissions"
                )
        
        # Verify project belongs to the specified client
        if project.client_id != bulk_data.client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project does not belong to the specified client"
            )
        
        # Link project to client_project if provided
        if bulk_data.client_project_id and not project.client_project_id:
            project.client_project_id = bulk_data.client_project_id
    
    # Get initial status (e.g., "Received")
    from models.list import List, ListEntry
    sample_status_list = db.query(List).filter(List.name == "sample_status").first()
    if not sample_status_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample status list not found in configuration"
        )
    
    received_status = db.query(ListEntry).filter(
        ListEntry.list_id == sample_status_list.id,
        ListEntry.name == "Received"
    ).first()
    
    if not received_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample status 'Received' not found in configuration"
        )
    
    # Get "In Process" status for tests
    test_status_list = db.query(List).filter(List.name == "test_status").first()
    if not test_status_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test status list not found in configuration"
        )
    
    in_process_status = db.query(ListEntry).filter(
        ListEntry.list_id == test_status_list.id,
        ListEntry.name == "In Process"
    ).first()
    
    if not in_process_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test status 'In Process' not found in configuration"
        )
    
    # Validate unique names and container names
    sample_names = []
    container_names = []
    client_sample_ids = []
    
    auto_name_counter = bulk_data.auto_name_start or 1
    
    for unique in bulk_data.uniques:
        # Generate name if not provided
        if unique.name:
            sample_name = unique.name
        elif bulk_data.auto_name_prefix:
            sample_name = f"{bulk_data.auto_name_prefix}{auto_name_counter}"
            auto_name_counter += 1
        else:
            # Use name generation if no prefix provided
            sample_name = generate_name_for_sample(
                db=db,
                project_id=str(project_id),
                received_date=bulk_data.received_date
            )
        
        sample_names.append(sample_name)
        container_names.append(unique.container_name)
        
        if unique.client_sample_id:
            client_sample_ids.append(unique.client_sample_id)
    
    # Check for duplicate sample names
    existing_samples = db.query(Sample).filter(
        Sample.name.in_(sample_names),
        Sample.active == True
    ).all()
    
    if existing_samples:
        duplicate_names = [s.name for s in existing_samples]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate sample names found: {', '.join(duplicate_names)}"
        )
    
    # Check for duplicate container names
    from models.container import Container
    existing_containers = db.query(Container).filter(
        Container.name.in_(container_names),
        Container.active == True
    ).all()
    
    if existing_containers:
        duplicate_containers = [c.name for c in existing_containers]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate container names found: {', '.join(duplicate_containers)}"
        )
    
    # Check for duplicate client_sample_ids
    if client_sample_ids:
        existing_client_ids = db.query(Sample).filter(
            Sample.client_sample_id.in_(client_sample_ids),
            Sample.active == True
        ).all()
        
        if existing_client_ids:
            duplicate_client_ids = [s.client_sample_id for s in existing_client_ids if s.client_sample_id]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate client_sample_ids found: {', '.join(duplicate_client_ids)}"
            )
    
    # Create all samples, containers, contents, and tests in a transaction
    created_samples = []
    auto_name_counter = bulk_data.auto_name_start or 1
    
    try:
        for idx, unique in enumerate(bulk_data.uniques):
            # Generate name if not provided
            if unique.name:
                sample_name = unique.name
            elif bulk_data.auto_name_prefix:
                sample_name = f"{bulk_data.auto_name_prefix}{auto_name_counter}"
                auto_name_counter += 1
            else:
                # Use name generation if no prefix provided
                sample_name = generate_name_for_sample(
                    db=db,
                    project_id=str(project_id),
                    received_date=bulk_data.received_date
                )
            
            # Create sample
            sample = Sample(
                name=sample_name,
                description=unique.description,
                due_date=bulk_data.due_date,
                received_date=bulk_data.received_date,
                sample_type=bulk_data.sample_type,
                status=received_status.id,
                matrix=bulk_data.matrix,
                temperature=unique.temperature if unique.temperature is not None else None,
                project_id=project_id,
                qc_type=bulk_data.qc_type,
                client_sample_id=unique.client_sample_id,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(sample)
            db.flush()  # Get the ID without committing
            
            # Project is already linked to client_project if auto-created or updated above
            
            # Create container
            container = Container(
                name=unique.container_name,
                type_id=bulk_data.container_type_id,
                row=1,
                column=1,
                created_by=current_user.id,
                modified_by=current_user.id
            )
            db.add(container)
            db.flush()  # Get the ID without committing
            
            # Link sample to container via contents
            from models.container import Contents
            contents = Contents(
                container_id=container.id,
                sample_id=sample.id
            )
            db.add(contents)
            
            # Create tests using shared helper function
            _create_tests_for_sample(
                db=db,
                sample=sample,
                battery_id=bulk_data.battery_id,
                assigned_tests=bulk_data.assigned_tests,
                in_process_status_id=in_process_status.id,
                current_user_id=current_user.id
            )
            
            created_samples.append(sample)
        
        # Commit all changes in a single transaction
        db.commit()
        
        # Refresh all samples to get full data
        for sample in created_samples:
            db.refresh(sample)
        
        return [SampleResponse.model_validate(sample) for sample in created_samples]
        
    except Exception as e:
        # Rollback on any error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create samples: {str(e)}"
        )


@router.patch("/{sample_id}", response_model=SampleResponse)
async def update_sample(
    sample_id: UUID,
    sample_data: SampleUpdate,
    current_user: User = Depends(require_sample_update),
    db: Session = Depends(get_db)
):
    """
    Partially update a sample.
    
    Requires sample:update permission. Updates only the fields provided in the request.
    Validates custom attributes against EAV configuration. Updates audit fields (modified_at, modified_by).
    
    **Example: Update sample status to 'Reviewed'**
    ```json
    {
        "status": "uuid-of-reviewed-status"
    }
    ```
    
    **Example: Update sample name and description**
    ```json
    {
        "name": "SAMPLE-001-UPDATED",
        "description": "Updated sample description"
    }
    ```
    
    **Example: Update custom attributes**
    ```json
    {
        "custom_attributes": {
            "ph_level": 7.2,
            "notes": "Sample appears normal"
        }
    }
    ```
    
    Returns 404 if sample not found, 403 if user lacks access (RLS enforced).
    All updates are performed in a single atomic transaction.
    """
    sample = db.query(Sample).filter(
        Sample.id == sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Check project access using has_project_access function (handles admin, client, and lab tech access)
    if current_user.role.name != "Administrator":
        from sqlalchemy import text
        result = db.execute(
            text("SELECT has_project_access(:project_id)"),
            {"project_id": str(sample.project_id)}
        ).scalar()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Validate and update custom_attributes if provided
    if sample_data.custom_attributes is not None:
        from app.core.custom_attributes import validate_custom_attributes
        validated_custom_attributes = validate_custom_attributes(
            db=db,
            entity_type='samples',
            custom_attributes=sample_data.custom_attributes
        )
        sample.custom_attributes = validated_custom_attributes
    
    # Update fields (excluding custom_attributes which is handled above)
    update_data = sample_data.dict(exclude_unset=True, exclude={'custom_attributes'})
    for field, value in update_data.items():
        setattr(sample, field, value)
    
    sample.modified_by = current_user.id
    sample.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(sample)
    
    return SampleResponse.model_validate(sample)


@router.delete("/{sample_id}")
async def delete_sample(
    sample_id: UUID,
    current_user: User = Depends(require_sample_delete),
    db: Session = Depends(get_db)
):
    """
    Soft delete a sample (set active=False).
    Requires sample:delete permission.
    """
    sample = db.query(Sample).filter(
        Sample.id == sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Check project access using has_project_access function (handles admin, client, and lab tech access)
    if current_user.role.name != "Administrator":
        from sqlalchemy import text
        result = db.execute(
            text("SELECT has_project_access(:project_id)"),
            {"project_id": str(sample.project_id)}
        ).scalar()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Soft delete
    sample.active = False
    sample.modified_by = current_user.id
    sample.modified_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Sample deleted successfully"}


@router.patch("/{sample_id}/status", response_model=SampleResponse)
async def update_sample_status(
    sample_id: UUID,
    status_id: UUID,
    current_user: User = Depends(require_sample_update),
    db: Session = Depends(get_db)
):
    """
    Update sample status.
    Implements US-2: Sample Status Management.
    """
    sample = db.query(Sample).filter(
        Sample.id == sample_id,
        Sample.active == True
    ).first()
    
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    # Check project access using has_project_access function (handles admin, client, and lab tech access)
    if current_user.role.name != "Administrator":
        from sqlalchemy import text
        result = db.execute(
            text("SELECT has_project_access(:project_id)"),
            {"project_id": str(sample.project_id)}
        ).scalar()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
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
    
    # Update status
    sample.status = status_id
    sample.modified_by = current_user.id
    sample.modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(sample)
    
    return SampleResponse.model_validate(sample)
