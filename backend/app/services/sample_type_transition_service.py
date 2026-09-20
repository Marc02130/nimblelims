"""CRUD for client-scoped sample type transitions. Mutate is config:edit (S3)."""

from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.sample_type_transition import (
    SampleTypeTransitionCreate,
    SampleTypeTransitionRead,
    SampleTypeTransitionUpdate,
)
from models.list import ListEntry
from models.sample import SampleTypeTransition
from models.user import User


class SampleTypeTransitionService:
    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.current_user = current_user

    def _client_id(self) -> UUID:
        if not self.current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "client_required",
                    "message": "User has no client_id; cannot own catalog rows",
                },
            )
        return self.current_user.client_id

    def _to_read(self, row: SampleTypeTransition) -> SampleTypeTransitionRead:
        source = (
            self.db.query(ListEntry)
            .filter(ListEntry.id == row.source_sample_type)
            .first()
        )
        dest = (
            self.db.query(ListEntry)
            .filter(ListEntry.id == row.allowed_dest_sample_type)
            .first()
        )
        return SampleTypeTransitionRead(
            id=row.id,
            client_id=row.client_id,
            source_sample_type=row.source_sample_type,
            source_sample_type_name=source.name if source else None,
            operation=row.operation,
            allowed_dest_sample_type=row.allowed_dest_sample_type,
            allowed_dest_sample_type_name=dest.name if dest else None,
            active=row.active,
            created_at=row.created_at,
            modified_at=row.modified_at,
        )

    def _require_type(self, type_id: UUID, label: str) -> ListEntry:
        entry = self.db.query(ListEntry).filter(ListEntry.id == type_id).first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "invalid_sample_type",
                    "message": f"{label} is not a list entry",
                },
            )
        return entry

    def _conflict(
        self,
        source: UUID,
        operation: str,
        dest: UUID,
        exclude_id: Optional[UUID] = None,
    ) -> bool:
        q = self.db.query(SampleTypeTransition).filter(
            SampleTypeTransition.client_id == self._client_id(),
            SampleTypeTransition.source_sample_type == source,
            SampleTypeTransition.operation == operation,
            SampleTypeTransition.allowed_dest_sample_type == dest,
        )
        if exclude_id is not None:
            q = q.filter(SampleTypeTransition.id != exclude_id)
        return q.first() is not None

    def list(
        self,
        operation: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[SampleTypeTransitionRead]:
        q = self.db.query(SampleTypeTransition).filter(
            SampleTypeTransition.client_id == self._client_id()
        )
        if operation:
            q = q.filter(SampleTypeTransition.operation == operation)
        if not include_inactive:
            q = q.filter(SampleTypeTransition.active.is_(True))
        rows = q.order_by(SampleTypeTransition.operation, SampleTypeTransition.id).all()
        return [self._to_read(r) for r in rows]

    def create(self, data: SampleTypeTransitionCreate) -> SampleTypeTransitionRead:
        self._require_type(data.source_sample_type, "source_sample_type")
        self._require_type(data.allowed_dest_sample_type, "allowed_dest_sample_type")
        if self._conflict(
            data.source_sample_type,
            data.operation,
            data.allowed_dest_sample_type,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "transition_exists",
                    "message": "This source × operation × dest already exists for the client",
                },
            )
        row = SampleTypeTransition(
            client_id=self._client_id(),
            source_sample_type=data.source_sample_type,
            operation=data.operation,
            allowed_dest_sample_type=data.allowed_dest_sample_type,
            active=data.active,
            created_by=self.current_user.id,
            modified_by=self.current_user.id,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_read(row)

    def update(
        self, row_id: UUID, data: SampleTypeTransitionUpdate
    ) -> SampleTypeTransitionRead:
        row = (
            self.db.query(SampleTypeTransition)
            .filter(
                SampleTypeTransition.id == row_id,
                SampleTypeTransition.client_id == self._client_id(),
            )
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transition not found",
            )
        payload = data.model_dump(exclude_unset=True)
        if "source_sample_type" in payload:
            self._require_type(payload["source_sample_type"], "source_sample_type")
        if "allowed_dest_sample_type" in payload:
            self._require_type(
                payload["allowed_dest_sample_type"], "allowed_dest_sample_type"
            )
        next_source = payload.get("source_sample_type", row.source_sample_type)
        next_op = payload.get("operation", row.operation)
        next_dest = payload.get(
            "allowed_dest_sample_type", row.allowed_dest_sample_type
        )
        if self._conflict(next_source, next_op, next_dest, exclude_id=row.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "transition_exists",
                    "message": "This source × operation × dest already exists for the client",
                },
            )
        for key, val in payload.items():
            setattr(row, key, val)
        row.modified_by = self.current_user.id
        self.db.commit()
        self.db.refresh(row)
        return self._to_read(row)

    def delete(self, row_id: UUID) -> None:
        row = (
            self.db.query(SampleTypeTransition)
            .filter(
                SampleTypeTransition.id == row_id,
                SampleTypeTransition.client_id == self._client_id(),
            )
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transition not found",
            )
        row.active = False
        row.modified_by = self.current_user.id
        self.db.commit()
