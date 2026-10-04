"""Configuring agent: settings, named configurations, proposals, and atomic apply."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_user_permissions
from app.database import get_db
from app.services.configuring_agent_service import (
    SETTINGS_DENIED,
    accept_step,
    add_document,
    apply_run,
    clear_key,
    configuration_payload,
    create_configuration,
    list_configurations,
    models_for,
    redo_step,
    run_payload,
    save_provider_and_model,
    set_key,
    settings_payload,
    skip_step,
    start_run,
    _settings,
)
from models.user import User

router = APIRouter(prefix="/configuring-agent", tags=["configuring-agent"])


class ProviderBody(BaseModel):
    provider: str
    model: str | None = None


class KeyBody(BaseModel):
    api_key: str = Field(min_length=1)


class ConfigurationBody(BaseModel):
    name: str
    description: str | None = None


class RunBody(BaseModel):
    goal_note: str | None = None


class FeedbackBody(BaseModel):
    feedback: str


def require_configuring_agent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if "config:edit" not in set(get_user_permissions(current_user, db)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SETTINGS_DENIED)
    return current_user


def _json(payload, code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=code, content=jsonable_encoder(payload))


@router.get("/settings")
def get_settings(
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    return _json(settings_payload(_settings(db)))


@router.put("/settings")
def put_settings(
    body: ProviderBody,
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    row = save_provider_and_model(db, user, body.provider, body.model)
    return _json(settings_payload(row))


@router.put("/settings/key")
def put_key(
    body: KeyBody,
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    row = set_key(db, user, body.api_key)
    return _json(settings_payload(row))


@router.delete("/settings/key")
def delete_key(
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    row = clear_key(db, user)
    return _json(settings_payload(row))


@router.get("/models")
def get_models(
    provider: str,
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    return _json({"provider": provider, "models": models_for(db, provider)})


@router.get("/configurations")
def get_configurations(
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    rows = list_configurations(db, user)
    return _json([configuration_payload(db, row) for row in rows])


@router.post("/configurations", status_code=201)
def post_configuration(
    body: ConfigurationBody,
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    row = create_configuration(db, user, body.name, body.description)
    return _json(configuration_payload(db, row), 201)


@router.get("/configurations/{configuration_id}")
def get_configuration(
    configuration_id: UUID,
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    from app.services.configuring_agent_service import _configuration

    row = _configuration(db, user, configuration_id)
    return _json(configuration_payload(db, row))


@router.post("/configurations/{configuration_id}/documents", status_code=201)
async def post_document(
    configuration_id: UUID,
    file: UploadFile = File(...),
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    data = await file.read()
    doc = add_document(db, user, configuration_id, file.filename or "upload", data)
    return _json(
        {
            "id": doc.id,
            "name": doc.name,
            "configuration_id": doc.configuration_id,
            "file_type": doc.file_type,
            "status": doc.status,
            "chunk_count": doc.chunk_count,
            "error_message": doc.error_message,
            "created_by": doc.created_by,
        },
        201,
    )


@router.post("/configurations/{configuration_id}/runs", status_code=201)
def post_run(
    configuration_id: UUID,
    body: RunBody,
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    run = start_run(db, user, configuration_id, body.goal_note)
    return _json(run_payload(run), 201)


@router.get("/runs/{run_id}")
def get_run(
    run_id: UUID,
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    from app.services.configuring_agent_service import _run

    return _json(run_payload(_run(db, user, run_id)))


@router.post("/runs/{run_id}/steps/{step_id}/accept")
def post_accept(
    run_id: UUID,
    step_id: UUID,
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    return _json(run_payload(accept_step(db, user, run_id, step_id)))


@router.post("/runs/{run_id}/steps/{step_id}/skip")
def post_skip(
    run_id: UUID,
    step_id: UUID,
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    return _json(run_payload(skip_step(db, user, run_id, step_id)))


@router.post("/runs/{run_id}/steps/{step_id}/redo")
def post_redo(
    run_id: UUID,
    step_id: UUID,
    body: FeedbackBody,
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    return _json(run_payload(redo_step(db, user, run_id, step_id, body.feedback)))


@router.post("/runs/{run_id}/apply")
async def post_apply(
    run_id: UUID,
    user: User = Depends(require_configuring_agent),
    db: Session = Depends(get_db),
):
    run, code = await apply_run(db, user, run_id)
    return _json(run_payload(run), code)
