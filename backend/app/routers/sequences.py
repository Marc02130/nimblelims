"""
Admin router for name-template sequence management (e.g. set sequence start value).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.core.security import get_current_user
from app.core.rbac import require_config_edit
from models.user import User
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin/sequences", tags=["sequences"])

ALLOWED_ENTITY_TYPES = ['sample', 'project', 'batch', 'analysis', 'container']


class SequenceStartRequest(BaseModel):
    """Request body for setting sequence start value."""
    start_value: int = Field(..., ge=1, description="Starting value for the sequence (>= 1)")


class SequenceStartResponse(BaseModel):
    """Response after setting sequence start."""
    entity_type: str
    start_value: int
    message: str


@router.post("/{entity_type}/start", response_model=SequenceStartResponse)
async def set_sequence_start(
    entity_type: str,
    body: SequenceStartRequest,
    current_user: User = Depends(require_config_edit),
    db: Session = Depends(get_db)
):
    """
    Set the starting value for an entity type's name sequence.
    Executes ALTER SEQUENCE name_template_seq_{entity_type} RESTART WITH {start_value}.
    Requires config:edit (admin) permission.
    """
    entity_type_lower = entity_type.lower().strip()
    if entity_type_lower not in ALLOWED_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"entity_type must be one of: {', '.join(ALLOWED_ENTITY_TYPES)}"
        )
    sequence_name = f"name_template_seq_{entity_type_lower}"
    # Ensure sequence exists (lazy creation) before setval
    from app.core.name_generation import _ensure_sequence_exists
    _ensure_sequence_exists(db, entity_type_lower)
    # Use setval so we can pass start_value as a bind parameter (ALTER SEQUENCE RESTART WITH doesn't support params).
    # setval(seq, value, is_called=False) means the next nextval() will return value.
    try:
        db.execute(
            text(f"SELECT setval('{sequence_name}'::regclass, :start_value, false)"),
            {"start_value": body.start_value}
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set sequence start: {str(e)}"
        )
    return SequenceStartResponse(
        entity_type=entity_type_lower,
        start_value=body.start_value,
        message=f"Sequence {sequence_name} restarted with {body.start_value}"
    )
