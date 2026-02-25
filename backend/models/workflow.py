"""Workflow template and instance models."""
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel


class WorkflowTemplate(BaseModel):
    """Template defining workflow steps (action/params) stored in template_definition JSONB."""
    __tablename__ = 'workflow_templates'

    template_definition = Column(JSONB, nullable=False, server_default='{}')
    # BaseModel: id, name, description, active, created_at, created_by, modified_at, modified_by

    instances = relationship("WorkflowInstance", back_populates="workflow_template")


class WorkflowInstance(BaseModel):
    """A run of a workflow with runtime state in JSONB."""
    __tablename__ = 'workflow_instances'

    workflow_template_id = Column(PostgresUUID(as_uuid=True), ForeignKey('workflow_templates.id'), nullable=False)
    runtime_state = Column(JSONB, nullable=False, server_default='{}')
    status_id = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=True)
    # BaseModel: id, name, description, active, created_at, created_by, modified_at, modified_by

    workflow_template = relationship("WorkflowTemplate", back_populates="instances")
