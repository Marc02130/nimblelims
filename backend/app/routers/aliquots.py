"""
Aliquots and derivatives router for LIMS MVP
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.database import get_db
from models.sample import Sample
from models.container import Container, Contents
from models.unit import Unit
from models.user import User
from app.schemas.aliquot import (
    AliquotCreateRequest, DerivativeCreateRequest, AliquotResponse, DerivativeResponse,
    PoolingRequest, PoolingResponse
)
from app.core.rbac import (
    require_sample_create, require_sample_read, require_sample_update,
    require_project_access
)
from app.core.security import get_current_user
from datetime import datetime
from uuid import UUID
from decimal import Decimal

router = APIRouter()


@router.post("/aliquot", response_model=AliquotResponse)
async def create_aliquot(
    aliquot_data: AliquotCreateRequest,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Create an aliquot from a parent sample.
    Implements US-3: Create Aliquots/Derivatives.
    """
    # Verify parent sample exists and user has access
    parent_sample = db.query(Sample).filter(
        Sample.id == aliquot_data.parent_sample_id,
        Sample.active == True
    ).first()
    
    if not parent_sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent sample not found"
        )
    
    # Check project access
    if current_user.role.name != "Administrator":
        if current_user.client_id and parent_sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Verify container exists
    container = db.query(Container).filter(
        Container.id == aliquot_data.container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container not found"
        )
    
    # Get "Available for Testing" status
    from models.list import ListEntry
    available_status = db.query(ListEntry).filter(
        ListEntry.list_id == "sample_status",  # Assuming this list exists
        ListEntry.name == "Available for Testing"
    ).first()
    
    if not available_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample status 'Available for Testing' not found in configuration"
        )
    
    # Create aliquot (same sample_id, new container_id)
    # For aliquots, we create a new sample record but link it to the parent
    aliquot = Sample(
        name=aliquot_data.name,
        description=aliquot_data.description,
        due_date=parent_sample.due_date,
        received_date=parent_sample.received_date,
        sample_type=parent_sample.sample_type,  # Same type as parent
        status=available_status.id,
        matrix=parent_sample.matrix,  # Same matrix as parent
        temperature=aliquot_data.temperature or parent_sample.temperature,
        parent_sample_id=parent_sample.id,
        project_id=parent_sample.project_id,  # Inherit project
        qc_type=aliquot_data.qc_type or parent_sample.qc_type,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(aliquot)
    db.flush()  # Get the ID without committing
    
    # Create contents entry linking aliquot to container
    contents = Contents(
        container_id=aliquot_data.container_id,
        sample_id=aliquot.id,
        concentration=aliquot_data.concentration,
        concentration_units=aliquot_data.concentration_units,
        amount=aliquot_data.amount,
        amount_units=aliquot_data.amount_units,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(contents)
    db.commit()
    db.refresh(aliquot)
    
    return AliquotResponse.from_orm(aliquot)


@router.post("/derivative", response_model=DerivativeResponse)
async def create_derivative(
    derivative_data: DerivativeCreateRequest,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Create a derivative from a parent sample.
    Implements US-3: Create Aliquots/Derivatives.
    """
    # Verify parent sample exists and user has access
    parent_sample = db.query(Sample).filter(
        Sample.id == derivative_data.parent_sample_id,
        Sample.active == True
    ).first()
    
    if not parent_sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent sample not found"
        )
    
    # Check project access
    if current_user.role.name != "Administrator":
        if current_user.client_id and parent_sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Verify container exists
    container = db.query(Container).filter(
        Container.id == derivative_data.container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container not found"
        )
    
    # Get "Available for Testing" status
    from models.list import ListEntry
    available_status = db.query(ListEntry).filter(
        ListEntry.list_id == "sample_status",  # Assuming this list exists
        ListEntry.name == "Available for Testing"
    ).first()
    
    if not available_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample status 'Available for Testing' not found in configuration"
        )
    
    # Create derivative (new sample_id/type, new container_id)
    derivative = Sample(
        name=derivative_data.name,
        description=derivative_data.description,
        due_date=parent_sample.due_date,
        received_date=parent_sample.received_date,
        sample_type=derivative_data.sample_type,  # Different type from parent
        status=available_status.id,
        matrix=parent_sample.matrix,  # Same matrix as parent
        temperature=derivative_data.temperature or parent_sample.temperature,
        parent_sample_id=parent_sample.id,
        project_id=parent_sample.project_id,  # Inherit project
        qc_type=derivative_data.qc_type or parent_sample.qc_type,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(derivative)
    db.flush()  # Get the ID without committing
    
    # Create contents entry linking derivative to container
    contents = Contents(
        container_id=derivative_data.container_id,
        sample_id=derivative.id,
        concentration=derivative_data.concentration,
        concentration_units=derivative_data.concentration_units,
        amount=derivative_data.amount,
        amount_units=derivative_data.amount_units,
        created_by=current_user.id,
        modified_by=current_user.id
    )
    
    db.add(contents)
    db.commit()
    db.refresh(derivative)
    
    return DerivativeResponse.from_orm(derivative)


@router.post("/pool", response_model=PoolingResponse)
async def pool_samples(
    pooling_data: PoolingRequest,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Pool multiple samples in a container.
    Implements US-6: Pooled Samples Creation.
    """
    # Verify container exists
    container = db.query(Container).filter(
        Container.id == pooling_data.container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container not found"
        )
    
    # Verify all samples exist and user has access
    samples = db.query(Sample).filter(
        Sample.id.in_(pooling_data.samples),
        Sample.active == True
    ).all()
    
    if len(samples) != len(pooling_data.samples):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more samples not found"
        )
    
    # Check project access for all samples
    if current_user.role.name != "Administrator":
        for sample in samples:
            if current_user.client_id and sample.project.client_id != current_user.client_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: insufficient project permissions"
                )
    
    # Calculate pooled values using units multipliers
    total_volume = 0.0
    total_concentration = 0.0
    concentration_units_id = None
    
    # Get base units for calculations
    base_volume_unit = db.query(Unit).filter(
        Unit.type == "volume",  # Assuming this list entry exists
        Unit.multiplier == 1.0  # Base unit
    ).first()
    
    base_concentration_unit = db.query(Unit).filter(
        Unit.type == "concentration",  # Assuming this list entry exists
        Unit.multiplier == 1.0  # Base unit
    ).first()
    
    if not base_volume_unit or not base_concentration_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Base units not configured"
        )
    
    # Process each sample
    for i, sample_id in enumerate(pooling_data.samples):
        sample = next(s for s in samples if s.id == sample_id)
        
        # Get units
        amount_unit = db.query(Unit).filter(Unit.id == pooling_data.amount_units[i]).first()
        concentration_unit = db.query(Unit).filter(Unit.id == pooling_data.concentration_units[i]).first()
        
        if not amount_unit or not concentration_unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid units for sample {sample_id}"
            )
        
        # Convert to base units
        amount_base = float(pooling_data.amounts[i]) * float(amount_unit.multiplier)
        concentration_base = float(pooling_data.concentrations[i]) * float(concentration_unit.multiplier)
        
        # Calculate volume from concentration and amount
        volume = amount_base / concentration_base if concentration_base > 0 else 0
        
        total_volume += volume
        total_concentration += concentration_base * volume
        
        # Create contents entry
        contents = Contents(
            container_id=pooling_data.container_id,
            sample_id=sample_id,
            concentration=pooling_data.concentrations[i],
            concentration_units=pooling_data.concentration_units[i],
            amount=pooling_data.amounts[i],
            amount_units=pooling_data.amount_units[i],
            created_by=current_user.id,
            modified_by=current_user.id
        )
        db.add(contents)
    
    # Calculate average concentration
    average_concentration = total_concentration / total_volume if total_volume > 0 else 0
    
    db.commit()
    
    return PoolingResponse(
        container_id=pooling_data.container_id,
        pooled_samples=pooling_data.samples,
        total_volume=total_volume,
        total_volume_units=base_volume_unit.id,
        average_concentration=average_concentration,
        concentration_units=base_concentration_unit.id,
        notes=pooling_data.notes
    )


@router.get("/parent/{parent_sample_id}", response_model=List[AliquotResponse])
async def get_aliquots_for_parent(
    parent_sample_id: UUID,
    current_user: User = Depends(require_sample_read),
    db: Session = Depends(get_db)
):
    """
    Get all aliquots for a parent sample.
    """
    # Verify parent sample exists and user has access
    parent_sample = db.query(Sample).filter(
        Sample.id == parent_sample_id,
        Sample.active == True
    ).first()
    
    if not parent_sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent sample not found"
        )
    
    # Check project access
    if current_user.role.name != "Administrator":
        if current_user.client_id and parent_sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Get aliquots (child samples with same sample_type as parent)
    aliquots = db.query(Sample).filter(
        Sample.parent_sample_id == parent_sample_id,
        Sample.sample_type == parent_sample.sample_type,  # Same type = aliquot
        Sample.active == True
    ).all()
    
    return [AliquotResponse.from_orm(aliquot) for aliquot in aliquots]


@router.get("/derivatives/{parent_sample_id}", response_model=List[DerivativeResponse])
async def get_derivatives_for_parent(
    parent_sample_id: UUID,
    current_user: User = Depends(require_sample_read),
    db: Session = Depends(get_db)
):
    """
    Get all derivatives for a parent sample.
    """
    # Verify parent sample exists and user has access
    parent_sample = db.query(Sample).filter(
        Sample.id == parent_sample_id,
        Sample.active == True
    ).first()
    
    if not parent_sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent sample not found"
        )
    
    # Check project access
    if current_user.role.name != "Administrator":
        if current_user.client_id and parent_sample.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions"
            )
    
    # Get derivatives (child samples with different sample_type from parent)
    derivatives = db.query(Sample).filter(
        Sample.parent_sample_id == parent_sample_id,
        Sample.sample_type != parent_sample.sample_type,  # Different type = derivative
        Sample.active == True
    ).all()
    
    return [DerivativeResponse.from_orm(derivative) for derivative in derivatives]
