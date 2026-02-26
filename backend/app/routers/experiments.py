"""
Experiments and experiment-templates API.

Routers: /api/v1/experiments and /api/v1/experiment-templates.
Full CRUD plus link_sample_to_experiment, add_experiment_detail_step,
link_experiments, get_experiment_lineage, get_sample_experiments.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.core.rbac import require_experiment_manage
from app.services.experiment_service import ExperimentService
from app.schemas.experiment import (
    ExperimentTemplateCreate,
    ExperimentTemplateUpdate,
    ExperimentTemplateRead,
    ExperimentTemplateListResponse,
    ExperimentCreate,
    ExperimentUpdate,
    ExperimentRead,
    ExperimentListEntry,
    ExperimentListResponse,
    AddExperimentDetailStepRequest,
    ExperimentDetailRead,
    LinkSampleToExperimentRequest,
    ExperimentSampleExecutionRead,
    LinkExperimentsRequest,
    ExperimentLineageRead,
    GetSampleExperimentsResponse,
    SampleExperimentEntry,
)
from models.user import User


# Prefixes are applied in main: /api/v1/experiment-templates, /api/v1/experiments
experiment_templates_router = APIRouter(
    prefix="/experiment-templates",
    tags=["experiment-templates"],
)

experiments_router = APIRouter(
    prefix="/experiments",
    tags=["experiments"],
)


def get_experiment_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_experiment_manage),
) -> ExperimentService:
    """Inject DB session and current user (experiment:manage required)."""
    return ExperimentService(db, current_user=current_user)


# ---------- Experiment Templates CRUD ----------


@experiment_templates_router.get("", response_model=ExperimentTemplateListResponse)
def list_experiment_templates(
    active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=500, description="Page size (up to 500 for dropdown use)"),
    service: ExperimentService = Depends(get_experiment_service),
):
    """List experiment templates with optional filter and pagination."""
    items, total = service.list_templates(active=active, page=page, size=size)
    pages = (total + size - 1) // size if size else 0
    return ExperimentTemplateListResponse(
        templates=[ExperimentTemplateRead.model_validate(t) for t in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@experiment_templates_router.get("/{template_id}", response_model=ExperimentTemplateRead)
def get_experiment_template(
    template_id: UUID,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Get a single experiment template by ID."""
    t = service.get_template(template_id)
    return ExperimentTemplateRead.model_validate(t)


@experiment_templates_router.post("", response_model=ExperimentTemplateRead, status_code=201)
def create_experiment_template(
    data: ExperimentTemplateCreate,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Create a new experiment template."""
    t = service.create_template(data)
    return ExperimentTemplateRead.model_validate(t)


@experiment_templates_router.patch("/{template_id}", response_model=ExperimentTemplateRead)
def update_experiment_template(
    template_id: UUID,
    data: ExperimentTemplateUpdate,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Update an experiment template (partial)."""
    t = service.update_template(template_id, data)
    return ExperimentTemplateRead.model_validate(t)


@experiment_templates_router.delete("/{template_id}", status_code=204)
def delete_experiment_template(
    template_id: UUID,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Soft-delete an experiment template."""
    service.delete_template(template_id)


# ---------- Experiments CRUD ----------


@experiments_router.get("", response_model=ExperimentListResponse)
def list_experiments(
    experiment_template_id: Optional[UUID] = Query(None, description="Filter by template ID"),
    status_id: Optional[UUID] = Query(None, description="Filter by status ID"),
    active: Optional[bool] = Query(True, description="Filter by active status"),
    mine: Optional[bool] = Query(None, description="If true, filter to experiments created by current user"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_experiment_manage),
    service: ExperimentService = Depends(get_experiment_service),
):
    """List experiments with filters and pagination. Use mine=true for 'My Experiments'."""
    created_by = current_user.id if mine else None
    items, total = service.list_experiments(
        experiment_template_id=experiment_template_id,
        status_id=status_id,
        active=active,
        created_by=created_by,
        page=page,
        size=size,
    )
    pages = (total + size - 1) // size if size else 0
    return ExperimentListResponse(
        experiments=[ExperimentListEntry.model_validate(e) for e in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@experiments_router.get("/{experiment_id}", response_model=ExperimentRead)
def get_experiment(
    experiment_id: UUID,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Get a single experiment by ID with details and sample executions."""
    e = service.get_experiment(experiment_id, load_details=True, load_sample_executions=True)
    return ExperimentRead.model_validate(e)


@experiments_router.post("", response_model=ExperimentRead, status_code=201)
def create_experiment(
    data: ExperimentCreate,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Create a new experiment."""
    e = service.create_experiment(data)
    return ExperimentRead.model_validate(e)


@experiments_router.patch("/{experiment_id}", response_model=ExperimentRead)
def update_experiment(
    experiment_id: UUID,
    data: ExperimentUpdate,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Update an experiment (partial)."""
    e = service.update_experiment(experiment_id, data)
    return ExperimentRead.model_validate(e)


@experiments_router.delete("/{experiment_id}", status_code=204)
def delete_experiment(
    experiment_id: UUID,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Soft-delete an experiment."""
    service.delete_experiment(experiment_id)


# ---------- Link sample to experiment ----------


@experiments_router.post(
    "/{experiment_id}/samples",
    response_model=ExperimentSampleExecutionRead,
    status_code=201,
)
def link_sample_to_experiment(
    experiment_id: UUID,
    data: LinkSampleToExperimentRequest,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Link a sample (or aliquot) to an experiment with role, processing_conditions, replicate_number."""
    ex = service.link_sample_to_experiment(experiment_id, data)
    return ExperimentSampleExecutionRead.model_validate(ex)


# ---------- Add experiment detail step ----------


@experiments_router.post(
    "/{experiment_id}/details",
    response_model=ExperimentDetailRead,
    status_code=201,
)
def add_experiment_detail_step(
    experiment_id: UUID,
    data: AddExperimentDetailStepRequest,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Add a detail step (protocol, conditions, or experiment_link) to an experiment."""
    d = service.add_experiment_detail_step(experiment_id, data)
    return ExperimentDetailRead.model_validate(d)


# ---------- Link experiments ----------


@experiments_router.post(
    "/{experiment_id}/links",
    response_model=ExperimentDetailRead,
    status_code=201,
)
def link_experiments(
    experiment_id: UUID,
    data: LinkExperimentsRequest,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Link another experiment to this one (stored as experiment_detail with type experiment_link)."""
    d = service.link_experiments(experiment_id, data)
    return ExperimentDetailRead.model_validate(d)


# ---------- Get experiment lineage ----------


@experiments_router.get("/{experiment_id}/lineage", response_model=ExperimentLineageRead)
def get_experiment_lineage(
    experiment_id: UUID,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Get experiment with template and linked experiment IDs (lineage)."""
    e, template, linked_ids = service.get_experiment_lineage(experiment_id)
    return ExperimentLineageRead(
        experiment=ExperimentRead.model_validate(e),
        template=ExperimentTemplateRead.model_validate(template) if template else None,
        linked_experiment_ids=linked_ids,
    )


# ---------- Get sample experiments ----------


@experiments_router.get("/by-sample/{sample_id}", response_model=GetSampleExperimentsResponse)
def get_sample_experiments(
    sample_id: UUID,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Get all experiments that include the given sample (via experiment_sample_executions)."""
    executions = service.get_sample_experiments(sample_id)
    entries = [
        SampleExperimentEntry(
            experiment_id=ex.experiment_id,
            experiment_name=ex.experiment.name if ex.experiment else "",
            role_in_experiment_id=ex.role_in_experiment_id,
            replicate_number=ex.replicate_number,
            processing_conditions=ex.processing_conditions or {},
            execution_id=ex.id,
        )
        for ex in executions
    ]
    return GetSampleExperimentsResponse(
        sample_id=sample_id,
        experiments=entries,
        total=len(entries),
    )
