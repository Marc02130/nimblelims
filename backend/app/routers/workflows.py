"""
Workflow templates (admin CRUD) and workflow execution.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.rbac import require_config_edit, require_workflow_execute
from models.user import User
from models.workflow import WorkflowTemplate, WorkflowInstance
from app.schemas.workflow import (
    WorkflowTemplateCreate,
    WorkflowTemplateRead,
    WorkflowTemplateUpdate,
    WorkflowExecuteRequest,
    WorkflowInstanceRead,
    VALID_WORKFLOW_ACTIONS,
)

logger = logging.getLogger(__name__)

# Admin CRUD under /admin/workflow-templates (prefix added in main)
workflow_templates_router = APIRouter(
    prefix="/workflow-templates",
    tags=["workflow-templates"],
)

# Execute under /workflows
workflows_router = APIRouter(
    prefix="",
    tags=["workflows"],
)


def _run_action(
    db: Session,
    action: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
    step_index: int,
) -> Dict[str, Any]:
    """
    Run a single workflow action. Stub implementations; each action
    can be extended to call real services. Returns updated context.
    """
    # Stub runners: no-op for now; integrate with real services as needed
    if action == "update_status":
        pass  # e.g. update sample/test status from params
    elif action == "validate_custom":
        pass  # validate custom_attributes against config
    elif action == "create_qc":
        pass  # create QC sample/container
    elif action == "assign_tests":
        pass  # assign tests to sample
    elif action == "create_batch":
        pass  # create batch
    elif action == "enter_results":
        pass  # enter results
    elif action == "send_notification":
        pass  # send notification
    elif action == "accession_sample":
        pass  # accession sample
    elif action == "link_container":
        pass  # link container to sample
    elif action == "review_result":
        pass  # review result
    return dict(context)


# --- Admin workflow-templates CRUD (config:edit) ---


@workflow_templates_router.get("", response_model=List[WorkflowTemplateRead])
def list_workflow_templates(
    active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    """
    List workflow templates. Requires config:edit permission.
    """
    query = db.query(WorkflowTemplate)
    if active is not None:
        query = query.filter(WorkflowTemplate.active == active)
    templates = query.order_by(WorkflowTemplate.name).all()
    return [WorkflowTemplateRead.model_validate(t) for t in templates]


@workflow_templates_router.post("", response_model=WorkflowTemplateRead, status_code=status.HTTP_201_CREATED)
def create_workflow_template(
    body: WorkflowTemplateCreate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    """
    Create a workflow template. Requires config:edit permission.
    """
    existing = db.query(WorkflowTemplate).filter(WorkflowTemplate.name == body.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A template with name '{body.name}' already exists.",
        )
    template = WorkflowTemplate(
        name=body.name,
        description=body.description,
        active=body.active,
        template_definition=body.template_definition,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return WorkflowTemplateRead.model_validate(template)


@workflow_templates_router.get("/{template_id}", response_model=WorkflowTemplateRead)
def get_workflow_template(
    template_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    """
    Get a workflow template by ID. Requires config:edit permission.
    """
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow template not found",
        )
    return WorkflowTemplateRead.model_validate(template)


@workflow_templates_router.patch("/{template_id}", response_model=WorkflowTemplateRead)
def update_workflow_template(
    template_id: UUID,
    body: WorkflowTemplateUpdate,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    """
    Update a workflow template (partial). Requires config:edit permission.
    """
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow template not found",
        )
    if body.name is not None:
        other = db.query(WorkflowTemplate).filter(
            WorkflowTemplate.name == body.name,
            WorkflowTemplate.id != template_id,
        ).first()
        if other:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A template with name '{body.name}' already exists.",
            )
        template.name = body.name
    if body.description is not None:
        template.description = body.description
    if body.active is not None:
        template.active = body.active
    if body.template_definition is not None:
        template.template_definition = body.template_definition
    template.modified_by = current_user.id
    db.commit()
    db.refresh(template)
    return WorkflowTemplateRead.model_validate(template)


@workflow_templates_router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow_template(
    template_id: UUID,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    """
    Deactivate a workflow template (soft delete). Requires config:edit permission.
    """
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow template not found",
        )
    template.active = False
    template.modified_by = current_user.id
    db.commit()


# --- Execute workflow (workflow:execute) ---


@workflows_router.post("/execute/{template_id}", response_model=WorkflowInstanceRead, status_code=status.HTTP_201_CREATED)
def execute_workflow(
    template_id: UUID,
    body: WorkflowExecuteRequest,
    current_user: User = Depends(require_workflow_execute),
    db: Session = Depends(get_db),
):
    """
    Execute a workflow template: parse steps, run each action in a single transaction,
    and create a workflow_instance record. Requires workflow:execute permission.
    """
    template = db.query(WorkflowTemplate).filter(
        WorkflowTemplate.id == template_id,
        WorkflowTemplate.active == True,
    ).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow template not found or inactive",
        )

    if body.workflow_template_id is not None and body.workflow_template_id != template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="template_id in path must match workflow_template_id in body",
        )

    definition = template.template_definition or {}
    steps: List[Dict[str, Any]] = definition.get("steps") or []

    context: Dict[str, Any] = dict(body.context or {})
    steps_run: List[Dict[str, Any]] = []

    try:
        for i, step in enumerate(steps):
            action = step.get("action") or ""
            params = step.get("params") or {}
            if action not in VALID_WORKFLOW_ACTIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid action '{action}' at step {i}; must be one of: {', '.join(VALID_WORKFLOW_ACTIONS)}",
                )
            context = _run_action(db, action, params, context, i)
            steps_run.append({
                "step_index": i,
                "action": action,
                "status": "ok",
            })
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Workflow step failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow step failed: {str(e)}",
        )

    runtime_state: Dict[str, Any] = {
        "context": context,
        "steps_run": steps_run,
        "completed": True,
    }

    # Unique instance name: use body name or generate from template + timestamp
    base_name = (body.name or template.name).strip()
    if not base_name:
        base_name = template.name
    instance_name = f"{base_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    # Ensure uniqueness
    existing = db.query(WorkflowInstance).filter(WorkflowInstance.name == instance_name).first()
    if existing:
        instance_name = f"{base_name}_{uuid4().hex[:8]}"

    instance = WorkflowInstance(
        name=instance_name,
        description=f"Run of {template.name}",
        active=True,
        workflow_template_id=template_id,
        runtime_state=runtime_state,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return WorkflowInstanceRead.model_validate(instance)
