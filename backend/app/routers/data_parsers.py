"""CRUD + versioning + setup test for data_parsers (P1)."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.rbac import require_config_edit
from app.core.security import get_current_user
from app.database import get_db
from app.schemas.data_parser import (
    DataParserCreate,
    DataParserNewVersion,
    DataParserRead,
    SetupFileMeta,
    TestSuiteResponse,
)
from app.schemas.flexible_experiment import ParserConfig
from app.services.data_parser_service import (
    MAX_SETUP_FILE_BYTES,
    MAX_SETUP_FILES,
    DataParserService,
)
from models.user import User

router = APIRouter(prefix="/data-parsers", tags=["data-parsers"])


def _svc(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DataParserService:
    return DataParserService(db, current_user=user)


@router.get("", response_model=List[DataParserRead])
def list_data_parsers(
    active_only: bool = Query(True),
    instrument_id: Optional[UUID] = None,
    cro_source_id: Optional[UUID] = None,
    analysis_id: Optional[UUID] = None,
    version_group_id: Optional[UUID] = None,
    svc: DataParserService = Depends(_svc),
):
    return svc.list_parsers(
        active_only=active_only,
        instrument_id=instrument_id,
        cro_source_id=cro_source_id,
        analysis_id=analysis_id,
        version_group_id=version_group_id,
    )


@router.get("/{parser_id}", response_model=DataParserRead)
def get_data_parser(parser_id: UUID, svc: DataParserService = Depends(_svc)):
    return svc._to_read(svc.get(parser_id))


@router.post("", response_model=DataParserRead, status_code=status.HTTP_201_CREATED)
def create_data_parser(
    body: DataParserCreate,
    user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    return DataParserService(db, current_user=user).create(body)


@router.post(
    "/groups/{version_group_id}/versions",
    response_model=DataParserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_parser_version(
    version_group_id: UUID,
    body: DataParserNewVersion,
    user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    return DataParserService(db, current_user=user).create_version(version_group_id, body)


@router.post("/{parser_id}/activate", response_model=DataParserRead)
def activate_parser(
    parser_id: UUID,
    user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    return DataParserService(db, current_user=user).activate(parser_id)


@router.post("/validate-config")
def validate_config(
    body: ParserConfig,
    user: User = Depends(get_current_user),
):
    return {"ok": True, "parser_config": body.model_dump()}


@router.post("/test", response_model=TestSuiteResponse)
async def test_parser_config(
    parser_config: str = Form(..., description="JSON ParserConfig"),
    files: List[UploadFile] = File(...),
    user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    import json

    try:
        cfg = ParserConfig.model_validate(json.loads(parser_config))
    except Exception as e:
        raise HTTPException(422, f"Invalid parser_config: {e}")
    if len(files) > MAX_SETUP_FILES:
        raise HTTPException(400, f"Max {MAX_SETUP_FILES} files")
    payloads: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        if len(content) > MAX_SETUP_FILE_BYTES:
            raise HTTPException(400, f"{f.filename} exceeds size limit")
        payloads.append((f.filename or "file", content))
    return DataParserService(db, current_user=user).test_config(cfg, payloads)


@router.post(
    "/{parser_id}/setup-files",
    response_model=SetupFileMeta,
    status_code=status.HTTP_201_CREATED,
)
async def upload_setup_file(
    parser_id: UUID,
    role: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require_config_edit),
    db: Session = Depends(get_db),
):
    content = await file.read()
    return DataParserService(db, current_user=user).add_setup_file(
        parser_id=parser_id,
        role=role,
        filename=file.filename or "upload",
        content_type=file.content_type,
        content=content,
    )


@router.get("/{parser_id}/setup-files", response_model=List[SetupFileMeta])
def list_setup_files(
    parser_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return DataParserService(db, current_user=user).list_setup_files(parser_id)
