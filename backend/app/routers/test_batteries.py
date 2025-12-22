"""
Test Batteries router for LIMS MVP
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from models.test_battery import TestBattery, BatteryAnalysis
from models.analysis import Analysis
from models.test import Test
from models.user import User
from app.schemas.test_battery import (
    TestBatteryResponse,
    TestBatteryCreate,
    TestBatteryUpdate,
    BatteryAnalysisResponse,
    BatteryAnalysisCreate,
    BatteryAnalysisUpdate,
    TestBatteryWithAnalysesResponse,
    TestBatteryListResponse,
)
from app.core.security import get_current_user
from app.core.rbac import require_any_permission
from uuid import UUID

router = APIRouter()


@router.get("", response_model=TestBatteryListResponse)
async def get_test_batteries(
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all active test batteries with optional filtering by name.
    """
    query = db.query(TestBattery).filter(TestBattery.active == True)
    
    # Apply name filter if provided
    if name:
        query = query.filter(TestBattery.name.ilike(f"%{name}%"))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    batteries = query.order_by(TestBattery.name).offset(offset).limit(size).all()
    
    # Calculate pages
    pages = (total + size - 1) // size
    
    # Get analyses count for each battery
    result = []
    for battery in batteries:
        analyses_count = db.query(func.count(BatteryAnalysis.analysis_id)).filter(
            BatteryAnalysis.battery_id == battery.id
        ).scalar() or 0
        
        battery_dict = {
            "id": battery.id,
            "name": battery.name,
            "description": battery.description,
            "active": battery.active,
            "created_at": battery.created_at,
            "created_by": battery.created_by,
            "modified_at": battery.modified_at,
            "modified_by": battery.modified_by,
            "analyses_count": analyses_count
        }
        result.append(TestBatteryResponse(**battery_dict))
    
    return TestBatteryListResponse(
        batteries=result,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/{battery_id}", response_model=TestBatteryWithAnalysesResponse)
async def get_test_battery(
    battery_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a test battery by ID with its analyses.
    """
    battery = db.query(TestBattery).filter(
        TestBattery.id == battery_id,
        TestBattery.active == True
    ).first()
    
    if not battery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test battery not found"
        )
    
    # Get analyses for this battery
    battery_analyses = db.query(BatteryAnalysis, Analysis).join(
        Analysis, BatteryAnalysis.analysis_id == Analysis.id
    ).filter(
        BatteryAnalysis.battery_id == battery_id,
        Analysis.active == True
    ).order_by(BatteryAnalysis.sequence).all()
    
    analyses_list = []
    for ba, analysis in battery_analyses:
        analyses_list.append(BatteryAnalysisResponse(
            battery_id=ba.battery_id,
            analysis_id=ba.analysis_id,
            analysis_name=analysis.name,
            analysis_method=analysis.method,
            sequence=ba.sequence,
            optional=ba.optional
        ))
    
    return TestBatteryWithAnalysesResponse(
        id=battery.id,
        name=battery.name,
        description=battery.description,
        active=battery.active,
        created_at=battery.created_at,
        created_by=battery.created_by,
        modified_at=battery.modified_at,
        modified_by=battery.modified_by,
        analyses=analyses_list
    )


@router.post("", response_model=TestBatteryResponse, status_code=status.HTTP_201_CREATED)
async def create_test_battery(
    battery_data: TestBatteryCreate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Create a new test battery.
    Requires config:edit or test:configure permission.
    """
    # Check for unique name
    existing_battery = db.query(TestBattery).filter(TestBattery.name == battery_data.name).first()
    if existing_battery:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test battery name already exists"
        )
    
    new_battery = TestBattery(
        name=battery_data.name,
        description=battery_data.description,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    
    db.add(new_battery)
    db.commit()
    db.refresh(new_battery)
    
    return TestBatteryResponse(
        id=new_battery.id,
        name=new_battery.name,
        description=new_battery.description,
        active=new_battery.active,
        created_at=new_battery.created_at,
        created_by=new_battery.created_by,
        modified_at=new_battery.modified_at,
        modified_by=new_battery.modified_by,
        analyses_count=0
    )


@router.patch("/{battery_id}", response_model=TestBatteryResponse)
async def update_test_battery(
    battery_id: UUID,
    battery_data: TestBatteryUpdate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Update a test battery.
    Requires config:edit or test:configure permission.
    """
    battery = db.query(TestBattery).filter(TestBattery.id == battery_id).first()
    if not battery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test battery not found"
        )
    
    # Check for unique name if updating
    if battery_data.name and battery_data.name != battery.name:
        existing_battery = db.query(TestBattery).filter(TestBattery.name == battery_data.name).first()
        if existing_battery:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test battery name already exists"
            )
        battery.name = battery_data.name
    
    if battery_data.description is not None:
        battery.description = battery_data.description
    
    if battery_data.active is not None:
        battery.active = battery_data.active
    
    battery.modified_by = current_user.id
    db.commit()
    db.refresh(battery)
    
    # Get analyses count
    analyses_count = db.query(func.count(BatteryAnalysis.analysis_id)).filter(
        BatteryAnalysis.battery_id == battery.id
    ).scalar() or 0
    
    return TestBatteryResponse(
        id=battery.id,
        name=battery.name,
        description=battery.description,
        active=battery.active,
        created_at=battery.created_at,
        created_by=battery.created_by,
        modified_at=battery.modified_at,
        modified_by=battery.modified_by,
        analyses_count=analyses_count
    )


@router.delete("/{battery_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_battery(
    battery_id: UUID,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Soft delete a test battery.
    Requires config:edit or test:configure permission.
    Fails if battery is referenced by any tests (409 Conflict).
    """
    battery = db.query(TestBattery).filter(TestBattery.id == battery_id).first()
    if not battery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test battery not found"
        )
    
    # Check if battery is referenced by any tests
    tests_count = db.query(Test).filter(
        Test.battery_id == battery_id,
        Test.active == True
    ).count()
    
    if tests_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete test battery: {tests_count} test(s) reference this battery"
        )
    
    battery.active = False
    battery.modified_by = current_user.id
    db.commit()
    
    return None


# Battery-Analyses sub-routes

@router.get("/{battery_id}/analyses", response_model=List[BatteryAnalysisResponse])
async def get_battery_analyses(
    battery_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all analyses for a test battery.
    """
    battery = db.query(TestBattery).filter(
        TestBattery.id == battery_id,
        TestBattery.active == True
    ).first()
    
    if not battery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test battery not found"
        )
    
    battery_analyses = db.query(BatteryAnalysis, Analysis).join(
        Analysis, BatteryAnalysis.analysis_id == Analysis.id
    ).filter(
        BatteryAnalysis.battery_id == battery_id,
        Analysis.active == True
    ).order_by(BatteryAnalysis.sequence).all()
    
    result = []
    for ba, analysis in battery_analyses:
        result.append(BatteryAnalysisResponse(
            battery_id=ba.battery_id,
            analysis_id=ba.analysis_id,
            analysis_name=analysis.name,
            analysis_method=analysis.method,
            sequence=ba.sequence,
            optional=ba.optional
        ))
    
    return result


@router.post("/{battery_id}/analyses", response_model=BatteryAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def add_analysis_to_battery(
    battery_id: UUID,
    analysis_data: BatteryAnalysisCreate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Add an analysis to a test battery.
    Requires config:edit or test:configure permission.
    """
    # Verify battery exists
    battery = db.query(TestBattery).filter(TestBattery.id == battery_id).first()
    if not battery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test battery not found"
        )
    
    # Verify analysis exists and is active
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_data.analysis_id,
        Analysis.active == True
    ).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis not found or inactive"
        )
    
    # Check if analysis is already in battery
    existing = db.query(BatteryAnalysis).filter(
        BatteryAnalysis.battery_id == battery_id,
        BatteryAnalysis.analysis_id == analysis_data.analysis_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis already exists in this battery"
        )
    
    # Create battery-analysis relationship
    battery_analysis = BatteryAnalysis(
        battery_id=battery_id,
        analysis_id=analysis_data.analysis_id,
        sequence=analysis_data.sequence,
        optional=analysis_data.optional
    )
    
    db.add(battery_analysis)
    db.commit()
    db.refresh(battery_analysis)
    
    return BatteryAnalysisResponse(
        battery_id=battery_analysis.battery_id,
        analysis_id=battery_analysis.analysis_id,
        analysis_name=analysis.name,
        analysis_method=analysis.method,
        sequence=battery_analysis.sequence,
        optional=battery_analysis.optional
    )


@router.patch("/{battery_id}/analyses/{analysis_id}", response_model=BatteryAnalysisResponse)
async def update_battery_analysis(
    battery_id: UUID,
    analysis_id: UUID,
    analysis_data: BatteryAnalysisUpdate,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Update an analysis in a test battery (sequence or optional flag).
    Requires config:edit or test:configure permission.
    """
    # Verify battery exists
    battery = db.query(TestBattery).filter(TestBattery.id == battery_id).first()
    if not battery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test battery not found"
        )
    
    # Get existing battery-analysis relationship
    battery_analysis = db.query(BatteryAnalysis).filter(
        BatteryAnalysis.battery_id == battery_id,
        BatteryAnalysis.analysis_id == analysis_id
    ).first()
    if not battery_analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found in this battery"
        )
    
    # Update fields
    if analysis_data.sequence is not None:
        battery_analysis.sequence = analysis_data.sequence
    if analysis_data.optional is not None:
        battery_analysis.optional = analysis_data.optional
    
    db.commit()
    db.refresh(battery_analysis)
    
    # Get analysis details
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    
    return BatteryAnalysisResponse(
        battery_id=battery_analysis.battery_id,
        analysis_id=battery_analysis.analysis_id,
        analysis_name=analysis.name if analysis else "Unknown",
        analysis_method=analysis.method if analysis else None,
        sequence=battery_analysis.sequence,
        optional=battery_analysis.optional
    )


@router.delete("/{battery_id}/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_analysis_from_battery(
    battery_id: UUID,
    analysis_id: UUID,
    current_user: User = Depends(require_any_permission(["config:edit", "test:configure"])),
    db: Session = Depends(get_db)
):
    """
    Remove an analysis from a test battery.
    Requires config:edit or test:configure permission.
    """
    # Verify battery exists
    battery = db.query(TestBattery).filter(TestBattery.id == battery_id).first()
    if not battery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test battery not found"
        )
    
    # Get existing battery-analysis relationship
    battery_analysis = db.query(BatteryAnalysis).filter(
        BatteryAnalysis.battery_id == battery_id,
        BatteryAnalysis.analysis_id == analysis_id
    ).first()
    if not battery_analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found in this battery"
        )
    
    db.delete(battery_analysis)
    db.commit()
    
    return None

