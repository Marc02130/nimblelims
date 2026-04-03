"""
Pydantic schemas for experiments and experiment templates.

JSONB fields: custom_attributes, template_definition, content, processing_conditions.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ---------- Experiment Template ----------


class ExperimentTemplateBase(BaseModel):
    """Base schema for experiment template."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    template_definition: Dict[str, Any] = Field(default_factory=dict, description="JSONB: structure/params")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="EAV / custom attributes JSONB")
    lifecycle_type: str = Field(default="standard", description="'standard' or 'cro'")


class ExperimentTemplateCreate(ExperimentTemplateBase):
    """Schema for creating an experiment template."""
    name: str = Field(..., min_length=1, max_length=255)


class ExperimentTemplateUpdate(BaseModel):
    """Schema for updating an experiment template."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    active: Optional[bool] = None
    template_definition: Optional[Dict[str, Any]] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    lifecycle_type: Optional[str] = Field(None, description="'standard' or 'cro'")


class ExperimentTemplateRead(ExperimentTemplateBase):
    """Schema for reading an experiment template."""
    id: UUID
    active: bool
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class ExperimentTemplateListResponse(BaseModel):
    """Paginated list of experiment templates."""
    templates: List[ExperimentTemplateRead]
    total: int
    page: int
    size: int
    pages: int


# ---------- Experiment ----------


class ExperimentBase(BaseModel):
    """Base schema for experiment."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    experiment_template_id: Optional[UUID] = None
    status_id: Optional[UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="EAV / custom attributes JSONB")


class ExperimentCreate(ExperimentBase):
    """Schema for creating an experiment."""
    name: str = Field(..., min_length=1, max_length=255)


class ExperimentUpdate(BaseModel):
    """Schema for updating an experiment."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    active: Optional[bool] = None
    experiment_template_id: Optional[UUID] = None
    status_id: Optional[UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class ExperimentFilter(BaseModel):
    """Query filters for listing experiments."""
    experiment_template_id: Optional[UUID] = None
    status_id: Optional[UUID] = None
    active: Optional[bool] = True


# ---------- Experiment Detail ----------


class ExperimentDetailBase(BaseModel):
    """Base schema for experiment detail step."""
    detail_type: str = Field(..., min_length=1, max_length=255)
    content: Dict[str, Any] = Field(default_factory=dict, description="JSONB content")
    sort_order: int = 0
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)


class ExperimentDetailCreate(ExperimentDetailBase):
    """Schema for creating an experiment detail."""
    pass


class ExperimentDetailRead(ExperimentDetailBase):
    """Schema for reading an experiment detail."""
    id: UUID
    experiment_id: UUID
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class AddExperimentDetailStepRequest(BaseModel):
    """Request body for add_experiment_detail_step."""
    detail_type: str = Field(..., min_length=1, max_length=255)
    content: Dict[str, Any] = Field(default_factory=dict)
    sort_order: Optional[int] = None  # If omitted, append at end


# ---------- Experiment Sample Execution ----------


class ExperimentSampleExecutionBase(BaseModel):
    """Base schema for experiment-sample junction."""
    sample_id: UUID
    role_in_experiment_id: Optional[UUID] = None
    processing_conditions: Dict[str, Any] = Field(default_factory=dict, description="JSONB")
    replicate_number: int = 1
    test_id: Optional[UUID] = None
    result_id: Optional[UUID] = None
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)


class ExperimentSampleExecutionCreate(ExperimentSampleExecutionBase):
    """Schema for linking a sample to an experiment."""
    pass


class ExperimentSampleExecutionRead(ExperimentSampleExecutionBase):
    """Schema for reading an experiment sample execution."""
    id: UUID
    experiment_id: UUID
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class LinkSampleToExperimentRequest(BaseModel):
    """Request body for link_sample_to_experiment."""
    sample_id: UUID = Field(..., description="Sample (or aliquot) to link")
    role_in_experiment_id: Optional[UUID] = None
    processing_conditions: Dict[str, Any] = Field(default_factory=dict)
    replicate_number: int = Field(1, ge=1)
    test_id: Optional[UUID] = None
    result_id: Optional[UUID] = None
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)


# ---------- Experiment Read (with optional nested data) ----------


class ExperimentRead(ExperimentBase):
    """Schema for reading an experiment (single get, with optional nested data)."""
    id: UUID
    active: bool
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None
    details: Optional[List[ExperimentDetailRead]] = Field(None, description="Detail steps")
    sample_executions: Optional[List[ExperimentSampleExecutionRead]] = Field(
        None, description="Linked samples/executions"
    )

    class Config:
        from_attributes = True


class ExperimentListEntry(ExperimentBase):
    """Slim experiment schema for list (no details/sample_executions to avoid N+1)."""
    id: UUID
    active: bool
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class ExperimentListResponse(BaseModel):
    """Paginated list of experiments."""
    experiments: List[ExperimentListEntry]
    total: int
    page: int
    size: int
    pages: int


# ---------- Extra endpoints ----------


class LinkExperimentsRequest(BaseModel):
    """Request body for link_experiments (store as experiment_detail with type experiment_link)."""
    linked_experiment_id: UUID = Field(..., description="ID of experiment to link to")


class ExperimentLineageRead(BaseModel):
    """Response for get_experiment_lineage: experiment + template + linked experiment ids."""
    experiment: ExperimentRead
    template: Optional[ExperimentTemplateRead] = None
    linked_experiment_ids: List[UUID] = Field(default_factory=list)


class SampleExperimentEntry(BaseModel):
    """One experiment that a sample participates in."""
    experiment_id: UUID
    experiment_name: str
    role_in_experiment_id: Optional[UUID] = None
    replicate_number: int = 1
    processing_conditions: Dict[str, Any] = Field(default_factory=dict)
    execution_id: UUID


class GetSampleExperimentsResponse(BaseModel):
    """Response for get_sample_experiments."""
    sample_id: UUID
    experiments: List[SampleExperimentEntry]
    total: int
