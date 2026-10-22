"""Reviewer pick between a run and the run it replaces.

Imported rows and result rows stay. The active acceptance is the choice.
The result row shows the accepted value. The previous value is stored here.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.lab_time import current_lab_day
from app.schemas.flexible_experiment import (
    AcceptValueRequest,
    ValueChoiceOption,
    ValueChoiceRead,
)
from app.services.result_promotion_service import ResultPromotionService, _norm, _stringify
from models.flexible_experiment import LimsRun, LimsRunData
from models.result import Result
from models.result_acceptance import ResultAcceptance
from models.sample import Sample
from models.test import Test
from models.user import User


def _is_failed(run: LimsRun) -> bool:
    status_value = run.status.value if hasattr(run.status, "value") else str(run.status)
    return status_value == "failed"


def _explicit_replicate(row_data: Dict[str, Any]) -> int:
    for key in ("replicate", "rep", "Replicate", "Rep"):
        if key in row_data and row_data[key] is not None and str(row_data[key]).strip() != "":
            try:
                value = int(row_data[key])
                return value if value >= 1 else 1
            except (TypeError, ValueError):
                return 1
    return 1


class ResultAcceptanceService:
    def __init__(self, db: Session, current_user: Optional[User] = None) -> None:
        self.db = db
        self.current_user = current_user

    def _user_id(self) -> Optional[uuid.UUID]:
        return self.current_user.id if self.current_user else None

    def list_for_run(self, run_id: uuid.UUID) -> List[ValueChoiceRead]:
        run = self._run(run_id)
        if not run.replaces_run_id or not run.analysis_id:
            return []
        other = self._run(run.replaces_run_id)
        return self._choices(run, other)

    def accept(self, run_id: uuid.UUID, body: AcceptValueRequest) -> ValueChoiceRead:
        run = self._run(run_id)
        if not run.replaces_run_id or not run.analysis_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Value choices are on the rerun, which links to the run it replaces",
            )
        other = self._run(run.replaces_run_id)
        allowed = {run.id, other.id}
        if body.accepted_lims_run_id not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Pick a value from this run or the run it replaces",
            )
        choices = self._choices(run, other)
        match = next(
            (
                row
                for row in choices
                if row.sample_id == body.sample_id
                and row.analyte_id == body.analyte_id
                and row.replicate == body.replicate
            ),
            None,
        )
        if match is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No values to choose for that sample, analyte, and replicate",
            )
        picked = next(
            (opt for opt in match.options if opt.lims_run_id == body.accepted_lims_run_id),
            None,
        )
        if picked is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="That run has no value for this sample",
            )
        other_opt = next(
            (opt for opt in match.options if opt.lims_run_id != body.accepted_lims_run_id),
            None,
        )
        reason = body.reason.strip()
        if not reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A reason is required",
            )
        chosen_run = run if body.accepted_lims_run_id == run.id else other
        if _is_failed(chosen_run) and not body.override_failed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Accepting a value from a failed or rejected run requires "
                    "override_failed and a reason"
                ),
            )

        test = (
            self.db.query(Test)
            .filter(
                Test.sample_id == body.sample_id,
                Test.analysis_id == run.analysis_id,
                Test.active == True,  # noqa: E712
            )
            .first()
        )
        if test is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "test_missing",
                    "message": "Test missing; Tests are created at LimsRun start (WO-7).",
                },
            )

        existing = (
            self.db.query(Result)
            .filter(
                Result.test_id == test.id,
                Result.analyte_id == body.analyte_id,
                Result.replicate == body.replicate,
                Result.active == True,  # noqa: E712
            )
            .first()
        )
        previous_value = existing.raw_result if existing else None
        previous_run = existing.lims_run_id if existing else None
        user_id = self._user_id()
        if existing:
            existing.raw_result = picked.raw_result
            existing.lims_run_id = picked.lims_run_id
            existing.modified_by = user_id
            existing.entry_date = current_lab_day()
        else:
            if not user_id:
                raise HTTPException(status_code=400, detail="Authenticated user required")
            self.db.add(
                Result(
                    test_id=test.id,
                    analyte_id=body.analyte_id,
                    raw_result=picked.raw_result,
                    replicate=body.replicate,
                    lims_run_id=picked.lims_run_id,
                    entry_date=current_lab_day(),
                    entered_by=user_id,
                    created_by=user_id,
                    modified_by=user_id,
                )
            )

        (
            self.db.query(ResultAcceptance)
            .filter(
                ResultAcceptance.sample_id == body.sample_id,
                ResultAcceptance.analyte_id == body.analyte_id,
                ResultAcceptance.replicate == body.replicate,
                ResultAcceptance.active == True,  # noqa: E712
            )
            .update({ResultAcceptance.active: False, ResultAcceptance.modified_by: user_id}, synchronize_session=False)
        )
        self.db.flush()
        self.db.add(
            ResultAcceptance(
                sample_id=body.sample_id,
                analyte_id=body.analyte_id,
                replicate=body.replicate,
                accepted_lims_run_id=picked.lims_run_id,
                accepted_value=picked.raw_result,
                other_lims_run_id=other_opt.lims_run_id if other_opt else None,
                other_value=other_opt.raw_result if other_opt else None,
                previous_lims_run_id=previous_run,
                previous_value=previous_value,
                reason=reason,
                override_failed=bool(body.override_failed),
                active=True,
                created_by=user_id,
                modified_by=user_id,
            )
        )
        self.db.commit()
        refreshed = self._choices(run, other)
        found = next(
            row
            for row in refreshed
            if row.sample_id == body.sample_id
            and row.analyte_id == body.analyte_id
            and row.replicate == body.replicate
        )
        return found

    def _run(self, run_id: uuid.UUID) -> LimsRun:
        run = self.db.query(LimsRun).filter(LimsRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LIMS run not found")
        return run

    def _choices(self, run: LimsRun, other: LimsRun) -> List[ValueChoiceRead]:
        promo = ResultPromotionService(self.db, current_user=self.current_user)
        lookup = promo.build_analyte_lookup(run.analysis_id)
        analytes: Dict[uuid.UUID, str] = {}
        for analyte, _via in lookup.values():
            analytes[analyte.id] = analyte.name
        sample_ids = self._sample_ids(run) | self._sample_ids(other)
        if not sample_ids or not analytes:
            return []

        samples = {
            s.id: s
            for s in self.db.query(Sample).filter(Sample.id.in_(list(sample_ids))).all()
        }
        runs = {run.id: run, other.id: other}
        values: Dict[Tuple[uuid.UUID, uuid.UUID, int, uuid.UUID], Tuple[str, str]] = {}

        data_rows = (
            self.db.query(LimsRunData)
            .filter(
                LimsRunData.lims_run_id.in_([run.id, other.id]),
                LimsRunData.sample_id.in_(list(sample_ids)),
            )
            .all()
        )
        for row in data_rows:
            if not row.sample_id:
                continue
            row_data = row.row_data or {}
            if not isinstance(row_data, dict):
                continue
            replicate = _explicit_replicate(row_data)
            for key, raw in row_data.items():
                if _norm(key) in {"replicate", "rep"}:
                    continue
                hit = lookup.get(_norm(key))
                if not hit:
                    continue
                text = _stringify(raw)
                if text == "":
                    continue
                analyte, _via = hit
                slot = (row.sample_id, analyte.id, replicate, row.lims_run_id)
                values[slot] = (text, "import")

        tests = (
            self.db.query(Test)
            .filter(
                Test.sample_id.in_(list(sample_ids)),
                Test.analysis_id == run.analysis_id,
                Test.active == True,  # noqa: E712
            )
            .all()
        )
        test_by_sample = {t.sample_id: t for t in tests}
        if tests:
            results = (
                self.db.query(Result)
                .filter(
                    Result.test_id.in_([t.id for t in tests]),
                    Result.active == True,  # noqa: E712
                )
                .all()
            )
            for result in results:
                if result.analyte_id not in analytes or not result.lims_run_id:
                    continue
                if result.lims_run_id not in runs:
                    continue
                sample_id = next(
                    (sid for sid, test in test_by_sample.items() if test.id == result.test_id),
                    None,
                )
                if sample_id is None or not result.raw_result:
                    continue
                slot = (sample_id, result.analyte_id, result.replicate, result.lims_run_id)
                values[slot] = (result.raw_result, "result")

        acceptances = (
            self.db.query(ResultAcceptance)
            .filter(
                ResultAcceptance.sample_id.in_(list(sample_ids)),
                ResultAcceptance.active == True,  # noqa: E712
            )
            .all()
        )
        accepted = {
            (a.sample_id, a.analyte_id, a.replicate): a for a in acceptances
        }

        grouped: Dict[Tuple[uuid.UUID, uuid.UUID, int], List[ValueChoiceOption]] = {}
        for (sample_id, analyte_id, replicate, lims_run_id), (raw, source) in values.items():
            owner = runs.get(lims_run_id)
            if owner is None:
                continue
            grouped.setdefault((sample_id, analyte_id, replicate), []).append(
                ValueChoiceOption(
                    lims_run_id=lims_run_id,
                    run_name=owner.name,
                    run_status=owner.status.value if hasattr(owner.status, "value") else str(owner.status),
                    status_reason=owner.status_reason,
                    raw_result=raw,
                    source=source,
                )
            )

        out: List[ValueChoiceRead] = []
        for (sample_id, analyte_id, replicate), options in sorted(
            grouped.items(), key=lambda item: (str(item[0][0]), str(item[0][1]), item[0][2])
        ):
            if not options:
                continue
            sample = samples.get(sample_id)
            choice = accepted.get((sample_id, analyte_id, replicate))
            out.append(
                ValueChoiceRead(
                    sample_id=sample_id,
                    sample_name=sample.name if sample else None,
                    client_sample_id=sample.client_sample_id if sample else None,
                    analyte_id=analyte_id,
                    analyte_name=analytes.get(analyte_id, ""),
                    replicate=replicate,
                    options=options,
                    accepted_lims_run_id=choice.accepted_lims_run_id if choice else None,
                    accepted_value=choice.accepted_value if choice else None,
                    acceptance_reason=choice.reason if choice else None,
                )
            )
        return out

    def _sample_ids(self, run: LimsRun) -> set:
        raw = (run.cohort or {}).get("sample_ids") or []
        found = set()
        for sid in raw:
            found.add(sid if isinstance(sid, uuid.UUID) else uuid.UUID(str(sid)))
        return found
