"""
Promote LimsRun JSONB data → structured tests/results on publish (P3).

Rules (open-questions/run-results.md):
- Only when run.analysis_id is set
- Ensure Test instance per (sample, analysis)
- Column → analyte via name or analyte_aliases (casefold)
- raw_result only; lims_run_id lineage; replicate from JSONB or row order
- Same lims_run_id → update; other lims_run_id → conflict fail
"""
from __future__ import annotations

import os
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models.analysis import Analysis, Analyte, AnalysisAnalyte
from models.flexible_experiment import LimsRun, LimsRunData
from models.list import List as ListModel, ListEntry
from models.result import Result
from models.sample import Sample
from models.test import Test
from models.user import User

# Non-analyte keys commonly present in instrument rows
_DEFAULT_SKIP_KEYS = frozenset({
    "units", "unit", "well", "well_position", "sample", "sample_id",
    "sample_name", "replicate", "rep", "container", "container_id",
    "row", "col", "plate",
})

DEFAULT_BATCH_SIZE = int(os.getenv("LIMS_PROMOTE_BATCH_SIZE", "200"))


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


@dataclass
class PromoteItem:
    action: str  # create | update | conflict | skip
    sample_id: Optional[str] = None
    test_id: Optional[str] = None
    analyte_id: Optional[str] = None
    analyte_name: Optional[str] = None
    raw_result: Optional[str] = None
    replicate: int = 1
    column_key: Optional[str] = None
    match_via: Optional[str] = None  # name | alias
    message: Optional[str] = None
    lims_run_data_id: Optional[str] = None


@dataclass
class PromotePlan:
    run_id: str
    analysis_id: Optional[str]
    will_promote: bool
    items: List[PromoteItem] = field(default_factory=list)
    create_count: int = 0
    update_count: int = 0
    conflict_count: int = 0
    skip_count: int = 0
    unresolved_columns: List[str] = field(default_factory=list)
    missing_sample_rows: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "analysis_id": self.analysis_id,
            "will_promote": self.will_promote,
            "create_count": self.create_count,
            "update_count": self.update_count,
            "conflict_count": self.conflict_count,
            "skip_count": self.skip_count,
            "unresolved_columns": self.unresolved_columns,
            "missing_sample_rows": self.missing_sample_rows,
            "errors": self.errors,
            "items": [asdict(i) for i in self.items[:500]],  # cap payload
            "items_truncated": len(self.items) > 500,
        }


class ResultPromotionService:
    def __init__(
        self,
        db: Session,
        current_user: Optional[User] = None,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.db = db
        self.current_user = current_user
        self.batch_size = max(1, batch_size)

    def _user_id(self) -> Optional[uuid.UUID]:
        return self.current_user.id if self.current_user else None

    def build_analyte_lookup(
        self, analysis_id: uuid.UUID
    ) -> Dict[str, Tuple[Analyte, str]]:
        """
        Map normalized key → (analyte, match_via) for analytes on this analysis.
        """
        aa_rows = (
            self.db.query(AnalysisAnalyte)
            .options(joinedload(AnalysisAnalyte.analyte).joinedload(Analyte.aliases))
            .filter(AnalysisAnalyte.analysis_id == analysis_id)
            .all()
        )
        lookup: Dict[str, Tuple[Analyte, str]] = {}
        for aa in aa_rows:
            an = aa.analyte
            if not an or not an.active:
                continue
            lookup[_norm(an.name)] = (an, "name")
            if aa.reported_name:
                lookup.setdefault(_norm(aa.reported_name), (an, "name"))
            for al in an.aliases or []:
                lookup.setdefault(_norm(al.alias), (an, "alias"))
        return lookup

    def _default_test_status_id(self) -> uuid.UUID:
        lst = self.db.query(ListModel).filter(ListModel.name == "test_status").first()
        if not lst:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="List 'test_status' not found; cannot create tests",
            )
        for preferred in ("In Process", "Assigned", "Pending", "Complete"):
            entry = (
                self.db.query(ListEntry)
                .filter(ListEntry.list_id == lst.id, ListEntry.name == preferred)
                .first()
            )
            if entry:
                return entry.id
        entry = (
            self.db.query(ListEntry)
            .filter(ListEntry.list_id == lst.id)
            .order_by(ListEntry.name)
            .first()
        )
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No entries in test_status list",
            )
        return entry.id

    def ensure_test(
        self,
        sample_id: uuid.UUID,
        analysis_id: uuid.UUID,
        *,
        cache: Dict[uuid.UUID, Test],
    ) -> Test:
        if sample_id in cache:
            return cache[sample_id]
        test = (
            self.db.query(Test)
            .filter(
                Test.sample_id == sample_id,
                Test.analysis_id == analysis_id,
                Test.active == True,  # noqa: E712
            )
            .first()
        )
        if test:
            cache[sample_id] = test
            return test

        sample = self.db.query(Sample).filter(Sample.id == sample_id).first()
        analysis = self.db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sample {sample_id} not found",
            )
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Analysis {analysis_id} not found",
            )

        status_id = self._default_test_status_id()
        base_name = f"{sample.name}_{analysis.name}"
        name = base_name[:240]
        # Ensure global unique name
        n = 0
        while self.db.query(Test.id).filter(Test.name == name).first():
            n += 1
            name = f"{base_name[:220]}_{n}"

        test = Test(
            name=name,
            sample_id=sample_id,
            analysis_id=analysis_id,
            status=status_id,
            test_date=datetime.now(),
            technician_id=self._user_id(),
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        self.db.add(test)
        self.db.flush()
        cache[sample_id] = test
        return test

    def _get_or_none_test(
        self,
        sample_id: uuid.UUID,
        analysis_id: uuid.UUID,
        cache: Dict[uuid.UUID, Optional[Test]],
    ) -> Optional[Test]:
        if sample_id in cache:
            return cache[sample_id]
        test = (
            self.db.query(Test)
            .filter(
                Test.sample_id == sample_id,
                Test.analysis_id == analysis_id,
                Test.active == True,  # noqa: E712
            )
            .first()
        )
        cache[sample_id] = test
        return test

    def plan_promotion(self, run: LimsRun, *, dry_run: bool = False) -> PromotePlan:
        """
        Build a promote plan for this run.

        dry_run=True: never create tests (preview-safe; no DB writes).
        dry_run=False: ensure Test instances exist (used on publish).
        """
        plan = PromotePlan(
            run_id=str(run.id),
            analysis_id=str(run.analysis_id) if run.analysis_id else None,
            will_promote=bool(run.analysis_id),
        )
        if not run.analysis_id:
            plan.errors.append("No analysis_id — publish will not write tests/results")
            return plan

        lookup = self.build_analyte_lookup(run.analysis_id)
        if not lookup:
            plan.errors.append("Analysis has no active analytes; nothing to promote")

        data_rows: List[LimsRunData] = (
            self.db.query(LimsRunData)
            .filter(LimsRunData.lims_run_id == run.id)
            .order_by(LimsRunData.created_at, LimsRunData.id)
            .all()
        )

        # Order-based replicate counters when JSONB has no replicate
        order_counters: Dict[Tuple[uuid.UUID, uuid.UUID], int] = defaultdict(int)
        seen_unresolved: set = set()
        test_cache: Dict[uuid.UUID, Test] = {}
        dry_test_cache: Dict[uuid.UUID, Optional[Test]] = {}

        for row in data_rows:
            if not row.sample_id:
                plan.missing_sample_rows += 1
                plan.items.append(
                    PromoteItem(
                        action="skip",
                        lims_run_data_id=str(row.id),
                        message="Row has no sample_id",
                    )
                )
                plan.skip_count += 1
                continue

            row_data = row.row_data or {}
            if not isinstance(row_data, dict):
                plan.skip_count += 1
                continue

            # Explicit replicate from JSONB if present
            explicit_rep: Optional[int] = None
            for rk in ("replicate", "rep", "Replicate", "Rep"):
                if rk in row_data and row_data[rk] is not None and str(row_data[rk]).strip() != "":
                    try:
                        explicit_rep = int(row_data[rk])
                        if explicit_rep < 1:
                            explicit_rep = 1
                    except (TypeError, ValueError):
                        explicit_rep = None
                    break

            test: Optional[Test] = None
            if dry_run:
                test = self._get_or_none_test(
                    row.sample_id, run.analysis_id, dry_test_cache
                )
            else:
                try:
                    test = self.ensure_test(
                        row.sample_id, run.analysis_id, cache=test_cache
                    )
                except HTTPException as e:
                    plan.errors.append(str(e.detail))
                    continue

            for key, value in row_data.items():
                # Structural / non-analyte keys — ignore silently (not "unresolved")
                if _norm(key) in _DEFAULT_SKIP_KEYS or _norm(key) in ("replicate", "rep"):
                    continue
                raw = _stringify(value)
                if raw == "":
                    continue

                hit = lookup.get(_norm(key))
                if not hit:
                    if key not in seen_unresolved:
                        seen_unresolved.add(key)
                        plan.unresolved_columns.append(key)
                    plan.items.append(
                        PromoteItem(
                            action="skip",
                            sample_id=str(row.sample_id),
                            column_key=key,
                            raw_result=raw,
                            message="Unresolved column (no analyte name/alias match)",
                            lims_run_data_id=str(row.id),
                        )
                    )
                    plan.skip_count += 1
                    continue

                analyte, via = hit
                if explicit_rep is not None:
                    replicate = explicit_rep
                else:
                    order_counters[(row.sample_id, analyte.id)] += 1
                    replicate = order_counters[(row.sample_id, analyte.id)]

                existing = None
                if test is not None:
                    existing = (
                        self.db.query(Result)
                        .filter(
                            Result.test_id == test.id,
                            Result.analyte_id == analyte.id,
                            Result.replicate == replicate,
                            Result.active == True,  # noqa: E712
                        )
                        .first()
                    )

                if existing:
                    if existing.lims_run_id == run.id:
                        action = "update"
                        plan.update_count += 1
                    else:
                        action = "conflict"
                        plan.conflict_count += 1
                        plan.errors.append(
                            f"Conflict: sample result for analyte '{analyte.name}' "
                            f"replicate {replicate} already owned by another run or manual entry"
                        )
                else:
                    action = "create"
                    plan.create_count += 1

                plan.items.append(
                    PromoteItem(
                        action=action,
                        sample_id=str(row.sample_id),
                        test_id=str(test.id) if test else None,
                        analyte_id=str(analyte.id),
                        analyte_name=analyte.name,
                        raw_result=raw,
                        replicate=replicate,
                        column_key=key,
                        match_via=via,
                        lims_run_data_id=str(row.id),
                        message=(
                            "Would update existing result from this run"
                            if action == "update"
                            else (
                                "Blocked: result owned by another run or manual entry"
                                if action == "conflict"
                                else (
                                    "Would create test + result"
                                    if test is None
                                    else None
                                )
                            )
                        ),
                    )
                )

        if plan.conflict_count:
            plan.errors = list(dict.fromkeys(plan.errors))  # dedupe preserve order
        return plan

    def apply_plan(self, run: LimsRun, plan: PromotePlan) -> None:
        """Write results from plan; assumes plan has no conflicts. Does not commit."""
        if plan.conflict_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "promotion_conflict",
                    "message": "Cannot promote: results already exist from another run or manual entry",
                    "errors": plan.errors,
                    "conflict_count": plan.conflict_count,
                },
            )
        if plan.errors and not plan.create_count and not plan.update_count:
            # Hard errors with nothing to write
            if any("test_status" in e or "not found" in e.lower() for e in plan.errors):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "promotion_failed", "errors": plan.errors},
                )

        user_id = self._user_id()
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authenticated user required to promote results",
            )
        # Use local now() — ResultResponse validator rejects utcnow() as "future"
        # when the host timezone is behind UTC (see schemas/result.py).
        now = datetime.now()
        pending = 0

        for item in plan.items:
            if item.action not in ("create", "update"):
                continue
            if not item.test_id or not item.analyte_id:
                continue
            test_id = uuid.UUID(item.test_id)
            analyte_id = uuid.UUID(item.analyte_id)

            if item.action == "update":
                existing = (
                    self.db.query(Result)
                    .filter(
                        Result.test_id == test_id,
                        Result.analyte_id == analyte_id,
                        Result.replicate == item.replicate,
                        Result.lims_run_id == run.id,
                    )
                    .first()
                )
                if existing:
                    existing.raw_result = item.raw_result
                    existing.modified_by = user_id
                    existing.modified_at = now
                    existing.entered_by = user_id
                    existing.entry_date = now
            else:
                res = Result(
                    test_id=test_id,
                    analyte_id=analyte_id,
                    raw_result=item.raw_result,
                    replicate=item.replicate,
                    lims_run_id=run.id,
                    entry_date=now,
                    entered_by=user_id,
                    created_by=user_id,
                    modified_by=user_id,
                )
                self.db.add(res)

            pending += 1
            if pending >= self.batch_size:
                self.db.flush()
                pending = 0

        if pending:
            self.db.flush()

    def promote_on_publish(self, run: LimsRun) -> PromotePlan:
        """
        Build plan and apply if analysis_id set. Raises on conflicts.
        Does not set run status or commit — caller owns transaction.
        """
        plan = self.plan_promotion(run)
        if not run.analysis_id:
            return plan
        # Ensure tests were flushed during plan (ensure_test flushes)
        self.apply_plan(run, plan)
        return plan
