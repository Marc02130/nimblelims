"""Atomic receive CORE: Sample + 1..N Containers + Contents in one transaction.

AuthZ = sample create (router) + project RLS / access checks inside this service.
No project auto-create. No sample-ID field. Status forced to Available for Testing.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.name_generation import generate_name_for_sample
from app.core.rbac import validate_client_access
from app.schemas.sample import (
    ReceivedContainerInfo,
    SampleReceiveRequest,
    SampleReceiveResponse,
)
from models.container import Container, ContainerType, Contents
from models.list import List, ListEntry
from models.project import Project, ProjectUser
from models.sample import Sample
from models.user import User

logger = logging.getLogger(__name__)

AVAILABLE_FOR_TESTING = "Available for Testing"


def _list_entry_by_names(
    db: Session, list_names: Sequence[str], entry_name: str
) -> Optional[ListEntry]:
    for list_name in list_names:
        lst = db.query(List).filter(List.name == list_name).first()
        if not lst:
            continue
        entry = (
            db.query(ListEntry)
            .filter(ListEntry.list_id == lst.id, ListEntry.name == entry_name)
            .first()
        )
        if entry:
            return entry
    # Fallback: entry name alone (create_all tests may use orphan list_entries)
    return db.query(ListEntry).filter(ListEntry.name == entry_name).first()


def resolve_available_for_testing_status(db: Session) -> ListEntry:
    entry = _list_entry_by_names(
        db, ("Sample Status", "sample_status"), AVAILABLE_FOR_TESTING
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample status 'Available for Testing' not found in configuration",
        )
    return entry


def resolve_default_tube_type(db: Session) -> ContainerType:
    """Default tube off-form: prefer name 'Tube', else first active *tube* type."""
    exact = (
        db.query(ContainerType)
        .filter(ContainerType.active == True, ContainerType.name == "Tube")  # noqa: E712
        .first()
    )
    if exact:
        return exact

    fuzzy = (
        db.query(ContainerType)
        .filter(
            ContainerType.active == True,  # noqa: E712
            ContainerType.name.ilike("%tube%"),
        )
        .order_by(ContainerType.name)
        .first()
    )
    if fuzzy:
        return fuzzy

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Default tube container type not found in configuration",
    )


def require_project_for_receive(db: Session, user: User, project_id: UUID) -> Project:
    """Project required + sticky. Enforce client access and project RLS when available."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    validate_client_access(user, project.client_id)

    # Prefer DB has_project_access when present (lims_app / migrated DBs).
    try:
        with db.begin_nested():
            ok = db.execute(
                text("SELECT has_project_access(CAST(:pid AS uuid))"),
                {"pid": str(project_id)},
            ).scalar()
        if ok is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions",
            )
        if ok is True:
            return project
    except HTTPException:
        raise
    except Exception:
        pass

    # Fallback for create_all / unit tests without has_project_access.
    if getattr(user.role, "name", None) != "Administrator":
        access = (
            db.query(ProjectUser)
            .filter(
                ProjectUser.project_id == project_id,
                ProjectUser.user_id == user.id,
            )
            .first()
        )
        if not access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions",
            )
    return project


def _normalize_barcodes(req: SampleReceiveRequest) -> List[str]:
    barcodes = [req.container_barcode] + list(req.additional_container_barcodes or [])
    if len(barcodes) != len(set(barcodes)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate container barcode in request",
        )
    return barcodes


def _assert_barcodes_available(db: Session, barcodes: Sequence[str]) -> None:
    existing = (
        db.query(Container)
        .filter(Container.name.in_(list(barcodes)), Container.active == True)  # noqa: E712
        .all()
    )
    if existing:
        dups = ", ".join(sorted({c.name for c in existing}))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Container barcode already exists: {dups}",
        )


def receive_sample(
    db: Session,
    req: SampleReceiveRequest,
    current_user: User,
) -> SampleReceiveResponse:
    """
    One transaction: system sample name + Available for Testing + 1..N vessels.
    CORE never creates tests. Request validation rejects non-empty analysis_ids.
    """
    barcodes = _normalize_barcodes(req)
    project = require_project_for_receive(db, current_user, req.project_id)
    available_status = resolve_available_for_testing_status(db)
    tube_type = resolve_default_tube_type(db)
    _assert_barcodes_available(db, barcodes)

    # Validate list FKs exist when possible (create_all may use orphan entries)
    for field_name, entry_id in (("sample_type", req.sample_type), ("matrix", req.matrix)):
        if not db.query(ListEntry).filter(ListEntry.id == entry_id).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {field_name}",
            )

    if req.client_sample_id:
        clash = (
            db.query(Sample)
            .filter(
                Sample.client_sample_id == req.client_sample_id,
                Sample.active == True,  # noqa: E712
            )
            .first()
        )
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="client_sample_id already exists",
            )

    received_at = datetime.utcnow()

    try:
        sample_name = generate_name_for_sample(
            db=db,
            project_id=str(project.id),
            received_date=received_at,
        )
    except Exception as e:
        logger.warning("Name generation failed (%s); falling back to UUID", e)
        import uuid as _uuid

        sample_name = str(_uuid.uuid4())

    sample = Sample(
        name=sample_name,
        sample_type=req.sample_type,
        matrix=req.matrix,
        status=available_status.id,
        project_id=project.id,
        received_date=received_at,
        temperature=req.temperature,
        client_sample_id=req.client_sample_id,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    db.add(sample)

    created_containers: List[Container] = []
    try:
        db.flush()  # sample.id

        for barcode in barcodes:
            container = Container(
                name=barcode,
                type_id=tube_type.id,
                row=1,
                column=1,
                created_by=current_user.id,
                modified_by=current_user.id,
            )
            db.add(container)
            db.flush()
            db.add(Contents(container_id=container.id, sample_id=sample.id))
            created_containers.append(container)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.info("Atomic receive integrity conflict: %s", e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate barcode or unique constraint violation",
        ) from e
    except Exception as e:
        db.rollback()
        logger.exception("Atomic receive failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Atomic receive failed: {e}",
        ) from e

    db.refresh(sample)
    for c in created_containers:
        db.refresh(c)

    return SampleReceiveResponse(
        sample_id=sample.id,
        sample_name=sample.name,
        status=sample.status,
        project_id=sample.project_id,
        received_date=sample.received_date,
        containers=[
            ReceivedContainerInfo(id=c.id, barcode=c.name) for c in created_containers
        ],
        tests=[],
    )
