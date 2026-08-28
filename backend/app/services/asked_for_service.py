"""Asked-for P1: record requested analyses. Does not mint Tests or work orders."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.services.atomic_receive_service import (
    require_project_for_receive,
    resolve_available_for_testing_status,
)
from models.analysis import Analysis
from models.asked_for import AnalysisParamDef, AskedFor
from models.list import ListEntry
from models.sample import Sample
from models.user import User

logger = logging.getLogger(__name__)

PROJECT_DENIED = "Access denied: insufficient project permissions"
CLIENT_DENIED = "Client role cannot record asked-for"
OPEN_DUP = "An open asked-for already exists for this sample and analysis"


def _role_name(user: User) -> str:
    return getattr(getattr(user, "role", None), "name", "") or ""


def deny_client_write(user: User) -> None:
    if _role_name(user) == "Client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=CLIENT_DENIED,
        )


def _hidden_sample() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=PROJECT_DENIED,
    )


class AskedForService:
    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.user = current_user

    def to_read(self, row: AskedFor) -> Dict[str, Any]:
        sample = getattr(row, "sample", None)
        analysis = getattr(row, "analysis", None)
        return {
            "id": row.id,
            "sample_id": row.sample_id,
            "sample_name": getattr(sample, "name", None),
            "analysis_id": row.analysis_id,
            "analysis_name": getattr(analysis, "name", None),
            "tat_days": row.tat_days,
            "params": row.params or {},
            "status": row.status,
            "created_at": row.created_at,
            "created_by": row.created_by,
            "modified_at": row.modified_at,
            "modified_by": row.modified_by,
        }

    def _load(self, asked_for_id: UUID) -> AskedFor:
        row = (
            self.db.query(AskedFor)
            .options(joinedload(AskedFor.sample), joinedload(AskedFor.analysis))
            .filter(AskedFor.id == asked_for_id)
            .first()
        )
        if not row:
            raise _hidden_sample()
        return row

    def _require_visible_sample(self, sample_id: UUID) -> Sample:
        sample = self.db.query(Sample).filter(Sample.id == sample_id).first()
        if not sample:
            raise _hidden_sample()
        require_project_for_receive(self.db, self.user, sample.project_id)
        return sample

    def _require_active_analysis(self, analysis_id: UUID) -> Analysis:
        analysis = self.db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis or not analysis.active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Analysis is missing or inactive",
            )
        return analysis

    def _require_available_for_testing(self, sample: Sample) -> None:
        available = resolve_available_for_testing_status(self.db)
        if sample.status != available.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Sample status must be Available for Testing",
            )

    def _get_analysis(self, analysis_id: UUID) -> Analysis:
        analysis = self.db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found",
            )
        return analysis

    def list_param_defs(self, analysis_id: UUID) -> List[AnalysisParamDef]:
        self._get_analysis(analysis_id)
        return (
            self.db.query(AnalysisParamDef)
            .filter(
                AnalysisParamDef.analysis_id == analysis_id,
                AnalysisParamDef.active == True,  # noqa: E712
            )
            .order_by(AnalysisParamDef.sort_order, AnalysisParamDef.key)
            .all()
        )

    def replace_param_defs(
        self, analysis_id: UUID, items: Sequence[Any]
    ) -> List[AnalysisParamDef]:
        self._get_analysis(analysis_id)
        keys = [item.key for item in items]
        if len(keys) != len(set(keys)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Param def keys must be unique for an analysis",
            )
        existing = (
            self.db.query(AnalysisParamDef)
            .filter(AnalysisParamDef.analysis_id == analysis_id)
            .all()
        )
        for row in existing:
            self.db.delete(row)
        self.db.flush()
        created: List[AnalysisParamDef] = []
        for item in items:
            row = AnalysisParamDef(
                analysis_id=analysis_id,
                key=item.key,
                data_type=item.data_type,
                unit=item.unit,
                required=bool(item.required),
                source_list_id=item.source_list_id,
                allowed_values=item.allowed_values,
                sort_order=item.sort_order,
                created_by=self.user.id,
                modified_by=self.user.id,
            )
            self.db.add(row)
            created.append(row)
        self.db.commit()
        for row in created:
            self.db.refresh(row)
        return created

    def validate_params(
        self, analysis_id: UUID, params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        params = dict(params or {})
        defs = self.list_param_defs(analysis_id)
        def_by_key = {d.key: d for d in defs}
        unknown = [k for k in params.keys() if k not in def_by_key]
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown param key(s): {', '.join(sorted(unknown))}",
            )
        for d in defs:
            present = d.key in params and params[d.key] is not None and params[d.key] != ""
            if d.required and not present:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Missing required param '{d.key}'",
                )
            if d.key not in params or params[d.key] is None:
                continue
            self._check_param_value(d, params[d.key])
        return params

    def _check_param_value(self, d: AnalysisParamDef, value: Any) -> None:
        dt = d.data_type
        if dt == "bool":
            if not isinstance(value, bool):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Param '{d.key}' must be a boolean",
                )
        elif dt == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Param '{d.key}' must be an integer",
                )
        elif dt == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Param '{d.key}' must be a number",
                )
        elif dt == "text":
            if not isinstance(value, str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Param '{d.key}' must be text",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Param '{d.key}' has unsupported data_type",
            )

        allowed = d.allowed_values
        if isinstance(allowed, list) and allowed and value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Param '{d.key}' is not an allowed value",
            )
        if d.source_list_id:
            q = self.db.query(ListEntry).filter(
                ListEntry.list_id == d.source_list_id,
                ListEntry.active == True,  # noqa: E712
            )
            if _is_uuid(value):
                q = q.filter(
                    (ListEntry.name == str(value))
                    | (ListEntry.id == UUID(str(value)))
                )
            else:
                q = q.filter(ListEntry.name == str(value))
            if not q.first():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Param '{d.key}' is not in the source list",
                )

    def create(
        self,
        sample_ids: List[UUID],
        analysis_id: UUID,
        tat_days: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[AskedFor]:
        deny_client_write(self.user)
        if tat_days < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="tat_days must be greater than 0",
            )
        self._require_active_analysis(analysis_id)
        validated = self.validate_params(analysis_id, params)
        rows: List[AskedFor] = []
        try:
            with self.db.begin_nested():
                for sample_id in sample_ids:
                    sample = self._require_visible_sample(sample_id)
                    self._require_available_for_testing(sample)
                    row = AskedFor(
                        sample_id=sample.id,
                        analysis_id=analysis_id,
                        tat_days=tat_days,
                        params=validated,
                        status="requested",
                        created_by=self.user.id,
                        modified_by=self.user.id,
                    )
                    self.db.add(row)
                    rows.append(row)
                self.db.flush()
        except HTTPException:
            raise
        except IntegrityError as e:
            logger.info("Asked-for unique conflict: %s", e)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=OPEN_DUP,
            ) from e
        except Exception:
            logger.exception("Asked-for create failed")
            raise
        self.db.commit()

        ids = [row.id for row in rows]
        loaded = (
            self.db.query(AskedFor)
            .options(joinedload(AskedFor.sample), joinedload(AskedFor.analysis))
            .filter(AskedFor.id.in_(ids))
            .all()
        )
        by_id = {row.id: row for row in loaded}
        return [by_id[row.id] for row in rows]

    def list(
        self,
        sample_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        analysis_id: Optional[UUID] = None,
        status_filter: Optional[str] = None,
    ) -> List[AskedFor]:
        q = self.db.query(AskedFor).options(
            joinedload(AskedFor.sample), joinedload(AskedFor.analysis)
        )
        if sample_id is not None:
            q = q.filter(AskedFor.sample_id == sample_id)
        if analysis_id is not None:
            q = q.filter(AskedFor.analysis_id == analysis_id)
        if status_filter is not None:
            q = q.filter(AskedFor.status == status_filter)
        if project_id is not None:
            q = q.join(Sample, Sample.id == AskedFor.sample_id).filter(
                Sample.project_id == project_id
            )
        return q.order_by(AskedFor.created_at.desc()).all()

    def get(self, asked_for_id: UUID) -> AskedFor:
        return self._load(asked_for_id)

    def cancel(self, asked_for_id: UUID) -> AskedFor:
        deny_client_write(self.user)
        row = self._load(asked_for_id)
        self._require_visible_sample(row.sample_id)
        if row.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Asked-for is already cancelled",
            )
        if row.status == "routed":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cancel after routed is not allowed in P1",
            )
        row.status = "cancelled"
        row.modified_by = self.user.id
        self.db.commit()
        self.db.refresh(row)
        return row


def _is_uuid(value: Any) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False
