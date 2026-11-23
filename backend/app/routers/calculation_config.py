"""Calculation configuration, saved formulas, and analysis versions (calculations S7).

The catalog is read-only here: it has no write route, so a POST, PUT, PATCH, or
DELETE on it is 405 (CALC-REQ-22). There is no constants route (CALC-REQ-41),
and no route that accepts R source or runs R. Nothing here runs a calculation;
that is the stage runner (S9).

A refusal is HTTP 400 with ``{"code", "message"}`` (and ``stage`` when a stage
is named). A caller without the Admin role that writes a formula gets 403.
"""
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from app.core.rbac import require_admin, require_any_permission
from app.core.security import get_current_user
from app.database import get_db
from app.schemas.calculation_config import (
    AnalysisVersionDetail,
    AnalysisVersionSummary,
    CalculationConfigurationResponse,
    CalculationFormulaResponse,
    CatalogEntryResponse,
    FormulaEvaluationResponse,
    NewAnalysisVersionResponse,
)
from app.services import calculation_config_service as service
from app.services.calculation_config import catalog_entries
from models.user import User

router = APIRouter(prefix="/v1", tags=["calculation-configuration"])

_CONFIG_PERMISSIONS = ["config:edit", "test:configure", "analysis:manage"]


@router.get("/calculation-catalog", response_model=List[CatalogEntryResponse])
def read_calculation_catalog(current_user: User = Depends(get_current_user)):
    """The validated catalog functions the builder offers. Read-only."""
    return catalog_entries()


@router.get("/calculation-formulas", response_model=List[CalculationFormulaResponse])
def list_calculation_formulas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [service.formula_response(row) for row in service.list_saved_formulas(db)]


@router.post(
    "/calculation-formulas",
    response_model=CalculationFormulaResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_calculation_formula(
    body: Dict[str, Any] = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Save a formula as the next version of its name. Admin role only."""
    return service.formula_response(service.create_saved_formula(db, body, current_user))


@router.post("/calculation-formulas/evaluate", response_model=FormulaEvaluationResponse)
def evaluate_calculation_formula(
    body: Dict[str, Any] = Body(...),
    current_user: User = Depends(require_admin),
):
    """Try formula text on typed terms. Admin role only. Stores nothing."""
    return service.evaluate_formula_text(body)


@router.get(
    "/calculation-formulas/{name}/versions/{version}",
    response_model=CalculationFormulaResponse,
)
def read_calculation_formula(
    name: str,
    version: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.formula_response(service.get_saved_formula(db, name, version))


@router.get(
    "/analyses/{analysis_id}/analytes/{analyte_id}/calculation-config",
    response_model=CalculationConfigurationResponse,
)
def read_calculation_config(
    analysis_id: UUID,
    analyte_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rule = service.get_rule(db, analysis_id, analyte_id)
    return service.configuration_response(rule, service.current_analysis_version(db, analysis_id))


@router.put(
    "/analyses/{analysis_id}/analytes/{analyte_id}/calculation-config",
    response_model=CalculationConfigurationResponse,
)
def save_calculation_config(
    analysis_id: UUID,
    analyte_id: UUID,
    body: Dict[str, Any] = Body(...),
    current_user: User = Depends(require_any_permission(_CONFIG_PERMISSIONS)),
    db: Session = Depends(get_db),
):
    """Save a draft configuration. An active configuration is refused (HTTP 400)."""
    return service.save_configuration(db, analysis_id, analyte_id, body, current_user)


@router.patch(
    "/analyses/{analysis_id}/analytes/{analyte_id}/calculation-order",
    response_model=CalculationConfigurationResponse,
)
def patch_calculation_order(
    analysis_id: UUID,
    analyte_id: UUID,
    body: Dict[str, Any] = Body(...),
    current_user: User = Depends(require_any_permission(_CONFIG_PERMISSIONS)),
    db: Session = Depends(get_db),
):
    return service.set_calculation_order(db, analysis_id, analyte_id, body, current_user)


@router.delete(
    "/analyses/{analysis_id}/analytes/{analyte_id}/calculation-config",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_calculation_config(
    analysis_id: UUID,
    analyte_id: UUID,
    current_user: User = Depends(require_any_permission(_CONFIG_PERMISSIONS)),
    db: Session = Depends(get_db),
):
    service.delete_configuration(db, analysis_id, analyte_id, current_user)
    return None


@router.post(
    "/analyses/{analysis_id}/new-version",
    response_model=NewAnalysisVersionResponse,
)
def start_new_analysis_version(
    analysis_id: UUID,
    current_user: User = Depends(require_any_permission(_CONFIG_PERMISSIONS)),
    db: Session = Depends(get_db),
):
    """Take the active configurations to draft as a new analysis version.

    The request has no body. The previous version stays readable and unchanged.
    """
    return service.start_new_version(db, analysis_id, current_user)


@router.get(
    "/analyses/{analysis_id}/versions",
    response_model=List[AnalysisVersionSummary],
)
def list_analysis_versions(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_versions(db, analysis_id)


@router.get(
    "/analyses/{analysis_id}/versions/{version}",
    response_model=AnalysisVersionDetail,
)
def read_analysis_version(
    analysis_id: UUID,
    version: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_version(db, analysis_id, version)
