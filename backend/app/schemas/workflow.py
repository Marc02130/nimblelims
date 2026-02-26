"""
Pydantic schemas for workflow templates and instances.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


VALID_WORKFLOW_ACTIONS = [
    "update_status",
    "validate_custom",
    "create_qc",
    "assign_tests",
    "create_batch",
    "enter_results",
    "send_notification",
    "accession_sample",
    "link_container",
    "review_result",
    # Experiment actions (context carries experiment_id, execution_id for downstream steps)
    "create_experiment",
    "create_experiment_from_template",
    "link_sample_to_experiment",
    "add_experiment_detail_step",
    "link_experiments",
    "update_experiment_status",
]

# Params hints for workflow builder UI: action -> list of param keys (required/optional).
# experiment_id can come from context (set by create_experiment / create_experiment_from_template).
WORKFLOW_EXPERIMENT_ACTION_PARAMS = {
    "create_experiment": ["name (required)", "description", "experiment_template_id", "status_id", "custom_attributes"],
    "create_experiment_from_template": ["experiment_template_id (required)", "name", "description", "status_id"],
    "link_sample_to_experiment": ["experiment_id (or from context)", "sample_id (required)", "role_in_experiment_id", "processing_conditions", "replicate_number", "test_id", "result_id"],
    "add_experiment_detail_step": ["experiment_id (or from context)", "detail_type (required)", "content", "sort_order"],
    "link_experiments": ["experiment_id (or from context)", "linked_experiment_id (required)"],
    "update_experiment_status": ["experiment_id (or from context)", "status_id (required)"],
}


def validate_template_definition(v: Any) -> Dict[str, Any]:
    """Validate template_definition has steps array with valid action/params."""
    if not isinstance(v, dict):
        raise ValueError("template_definition must be a dictionary")
    if "steps" not in v:
        raise ValueError("template_definition must contain 'steps' key")
    steps = v["steps"]
    if not isinstance(steps, list):
        raise ValueError("template_definition.steps must be a list")
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"template_definition.steps[{i}] must be an object")
        if "action" not in step:
            raise ValueError(f"template_definition.steps[{i}] must contain 'action'")
        action = step["action"]
        if not isinstance(action, str):
            raise ValueError(f"template_definition.steps[{i}].action must be a string")
        if action not in VALID_WORKFLOW_ACTIONS:
            raise ValueError(
                f"template_definition.steps[{i}].action must be one of: {', '.join(VALID_WORKFLOW_ACTIONS)}"
            )
        if "params" in step and not isinstance(step["params"], dict):
            raise ValueError(f"template_definition.steps[{i}].params must be an object when present")
    return v


class WorkflowTemplateBase(BaseModel):
    """Base schema for workflow template data."""
    name: str = Field(..., min_length=1, max_length=255, description="Unique template name")
    description: Optional[str] = Field(None, description="Template description")
    active: bool = Field(True, description="Whether the template is active")
    template_definition: Dict[str, Any] = Field(
        ...,
        description="JSON object with 'steps' array; each step has 'action' and optional 'params'",
    )

    @validator("template_definition")
    def validate_template_definition_steps(cls, v):
        return validate_template_definition(v)


class WorkflowTemplateCreate(WorkflowTemplateBase):
    """Schema for creating a new workflow template."""
    pass


class WorkflowTemplateRead(BaseModel):
    """Schema for workflow template response."""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    template_definition: Dict[str, Any]
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class WorkflowTemplateUpdate(BaseModel):
    """Schema for updating a workflow template (partial)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    active: Optional[bool] = None
    template_definition: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON object with 'steps' array; each step has 'action' and optional 'params'",
    )

    @validator("template_definition")
    def validate_template_definition_steps(cls, v):
        if v is None:
            return v
        return validate_template_definition(v)


class WorkflowExecuteRequest(BaseModel):
    """Schema for requesting execution of a workflow (start an instance)."""
    workflow_template_id: Optional[UUID] = Field(None, description="ID of the workflow template (optional when template_id is in path)")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Optional instance name (auto-generated if omitted)")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Initial context passed to the workflow. May contain: sample_id, batch_id, etc. "
            "Experiment actions set/use: experiment_id (UUID str, set by create_experiment/create_experiment_from_template), "
            "execution_id (UUID str, set by link_sample_to_experiment for the experiment_sample_execution id). "
            "Later steps can reference context.experiment_id or params.experiment_id."
        ),
    )


class WorkflowInstanceRead(BaseModel):
    """Schema for workflow instance response."""
    id: UUID
    name: str
    description: Optional[str] = None
    active: bool
    workflow_template_id: UUID
    runtime_state: Dict[str, Any]
    status_id: Optional[UUID] = None
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True
