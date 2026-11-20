"""Result-entry rows on a LIMS run (calculations S6).

A LIMS run has one experiment sample data entry, ``Results``. Its records are
``result_entries`` rows: one per Test, analyte, and replicate. Raw comes from a
file upload or is typed. Calculated is written only by a calculation (a later
slice); the API never writes it. Reported may be overwritten by a user once
calculated has a value. Publish copies the rows to ``results`` (a later slice).

Database triggers (migration 0123) back each rule for the app role. This module
gives the API its 400 refusals before the database is reached.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.analysis import Analyte, AnalysisAnalyte
from models.entry import Entry, ResultEntry
from models.flexible_experiment import LimsRun, LimsRunStatus
from models.test import Test

RESULTS_ENTRY_KEY = "lims_run_results"
RESULTS_ENTRY_NAME = "Results"
RESULTS_ENTRY_TYPE = "experiment_sample_data"

CALCULATION_WRITE_SETTING = "lims.calculation_write"

# The only fields a user may send on PATCH. calculated_result is refused by name.
EDITABLE_FIELDS = frozenset({"raw_result", "raw_units", "reported_result"})
MAX_RESULT_LENGTH = 255
MAX_UNITS_LENGTH = 64


def refuse(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": code, "message": message},
    )


@contextmanager
def calculation_write(db: Session) -> Iterator[None]:
    """Let the calculation path write calculated_result in this transaction.

    The setting is transaction-local. Only server code that runs a bound
    calculation may use this; no API route sets it.
    """
    db.execute(
        text("SELECT set_config(:name, 'on', true)"),
        {"name": CALCULATION_WRITE_SETTING},
    )
    try:
        yield
        db.flush()
    finally:
        db.execute(
            text("SELECT set_config(:name, 'off', true)"),
            {"name": CALCULATION_WRITE_SETTING},
        )


def _blank_to_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value if value.strip() != "" else None


def _check_text(field: str, value: Any, max_length: int) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise refuse("invalid_input", f"{field} must be a string or null.")
    if len(value) > max_length:
        raise refuse("invalid_input", f"{field} is longer than {max_length} characters.")
    return value


class ResultEntryService:
    def __init__(self, db: Session, user_id: Optional[UUID] = None) -> None:
        self.db = db
        self.user_id = user_id

    # ------------------------------------------------------------------ rows

    def run_entry(self, run_id: UUID) -> Optional[Entry]:
        return (
            self.db.query(Entry)
            .filter(
                Entry.lims_run_id == run_id,
                Entry.predefined_entry_key == RESULTS_ENTRY_KEY,
            )
            .first()
        )

    def ensure_run_entry(self, run: LimsRun) -> Entry:
        entry = self.run_entry(run.id)
        if entry is not None:
            return entry
        entry = Entry(
            lims_run_id=run.id,
            experiment_id=None,
            entry_type=RESULTS_ENTRY_TYPE,
            name=RESULTS_ENTRY_NAME,
            predefined_entry_key=RESULTS_ENTRY_KEY,
            sort_order=0,
            config={},
            created_by=self.user_id,
            modified_by=self.user_id,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def ensure_rows(
        self, run: LimsRun, replicate_counts: Optional[Dict[UUID, int]] = None
    ) -> int:
        """Create the missing result-entry rows for the run's Tests.

        One row per Test x analyte on the run's analysis x replicate 1..N. There
        is no replicate count column (CALC-REQ-54): N comes from the caller,
        which is the bound configuration once one exists (CALC-REQ-15, #258),
        and is 1 for an analyte the caller does not name. Final units start as
        the analyte's pairing unit; display order is copied from the analysis
        analyte. Returns the number of rows created.
        """
        counts = replicate_counts or {}
        for analyte_id, count in counts.items():
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                raise refuse(
                    "invalid_input",
                    f"Replicate count for analyte {analyte_id} must be a whole number of at least 1.",
                )
        if run.analysis_id is None:
            return 0
        tests = (
            self.db.query(Test)
            .filter(Test.lims_run_id == run.id, Test.active.is_(True))
            .all()
        )
        if not tests:
            return 0
        links = (
            self.db.query(AnalysisAnalyte)
            .join(Analyte, Analyte.id == AnalysisAnalyte.analyte_id)
            .filter(
                AnalysisAnalyte.analysis_id == run.analysis_id,
                Analyte.active.is_(True),
            )
            .all()
        )
        if not links:
            return 0
        entry = self.ensure_run_entry(run)
        test_ids = [t.id for t in tests]
        existing = {
            (row.test_id, row.analyte_id, row.replicate)
            for row in self.db.query(
                ResultEntry.test_id, ResultEntry.analyte_id, ResultEntry.replicate
            ).filter(ResultEntry.test_id.in_(test_ids))
        }
        created = 0
        for test in tests:
            for link in links:
                for replicate in range(1, counts.get(link.analyte_id, 1) + 1):
                    key = (test.id, link.analyte_id, replicate)
                    if key in existing:
                        continue
                    self.db.add(
                        ResultEntry(
                            entry_id=entry.id,
                            test_id=test.id,
                            analyte_id=link.analyte_id,
                            replicate=replicate,
                            final_units_id=link.pairing_unit_id,
                            display_order=link.display_order,
                            created_by=self.user_id,
                            modified_by=self.user_id,
                        )
                    )
                    existing.add(key)
                    created += 1
        self.db.flush()
        return created

    def get_row(self, run_id: UUID, row_id: UUID) -> ResultEntry:
        row = (
            self.db.query(ResultEntry)
            .join(Entry, Entry.id == ResultEntry.entry_id)
            .filter(ResultEntry.id == row_id, Entry.lims_run_id == run_id)
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Result entry not found on this LIMS run",
            )
        return row

    def list_rows(
        self, run_id: UUID, page: int, size: int
    ) -> Tuple[List[ResultEntry], int]:
        from models.sample import Sample

        query = (
            self.db.query(ResultEntry)
            .join(Entry, Entry.id == ResultEntry.entry_id)
            .join(Test, Test.id == ResultEntry.test_id)
            .join(Sample, Sample.id == Test.sample_id)
            .join(Analyte, Analyte.id == ResultEntry.analyte_id)
            .filter(Entry.lims_run_id == run_id)
        )
        total = query.count()
        rows = (
            query.order_by(
                Sample.name,
                ResultEntry.display_order.asc().nullslast(),
                Analyte.name,
                ResultEntry.replicate,
            )
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return rows, total

    # --------------------------------------------------------------- writes

    def _refuse_if_published(self, row: ResultEntry) -> None:
        run = self.db.get(LimsRun, row.test.lims_run_id)
        if run is not None and run.status == LimsRunStatus.published:
            raise refuse(
                "run_published",
                "This LIMS run is published. Its result entries cannot be edited.",
            )

    def apply_user_edit(self, row: ResultEntry, body: Dict[str, Any]) -> ResultEntry:
        """Apply a PATCH body from a user. Refusals are HTTP 400."""
        if not isinstance(body, dict):
            raise refuse("invalid_input", "The request body must be a JSON object.")
        if "calculated_result" in body:
            raise refuse(
                "calculated_locked",
                "calculated_result is written only by a calculation.",
            )
        unknown = sorted(set(body) - EDITABLE_FIELDS)
        if unknown:
            raise refuse(
                "invalid_input",
                f"Unknown field(s): {', '.join(unknown)}. "
                f"Allowed: {', '.join(sorted(EDITABLE_FIELDS))}.",
            )
        if not body:
            raise refuse("invalid_input", "Send at least one field to change.")
        self._refuse_if_published(row)

        raw_given = "raw_result" in body or "raw_units" in body
        if raw_given:
            if row.raw_origin == "upload":
                raise refuse(
                    "raw_uploaded",
                    "Raw from a file upload cannot be edited. "
                    "Correct the file and upload it again.",
                )
            if "raw_result" in body:
                raw = _blank_to_none(
                    _check_text("raw_result", body["raw_result"], MAX_RESULT_LENGTH)
                )
                row.raw_result = raw
            if "raw_units" in body:
                row.raw_units = _blank_to_none(
                    _check_text("raw_units", body["raw_units"], MAX_UNITS_LENGTH)
                )
            if row.raw_result is None:
                if "raw_units" in body and row.raw_units is not None:
                    raise refuse(
                        "invalid_input", "raw_units needs a raw_result on the same row."
                    )
                row.raw_units = None
            row.raw_origin = "typed" if row.raw_result is not None else None

        if "reported_result" in body:
            reported = _check_text(
                "reported_result", body["reported_result"], MAX_RESULT_LENGTH
            )
            if reported is None or reported.strip() == "":
                raise refuse(
                    "invalid_input",
                    "reported_result must be a value. "
                    "A blank reported result is not an override.",
                )
            if row.calculated_result is None:
                raise refuse(
                    "reported_before_calculation",
                    "Reported can be overwritten only after the calculation "
                    "has written a calculated result.",
                )
            row.reported_result = reported

        row.modified_by = self.user_id
        row.modified_at = datetime.now(timezone.utc)
        self.db.flush()
        return row

    def record_uploaded_raw(
        self, row: ResultEntry, raw_result: Optional[str], raw_units: Optional[str] = None
    ) -> ResultEntry:
        """Write raw from a file upload. Not reachable from the PATCH route."""
        self._refuse_if_published(row)
        row.raw_result = _blank_to_none(
            _check_text("raw_result", raw_result, MAX_RESULT_LENGTH)
        )
        row.raw_units = _blank_to_none(_check_text("raw_units", raw_units, MAX_UNITS_LENGTH))
        row.raw_origin = "upload" if row.raw_result is not None else None
        if row.raw_result is None:
            row.raw_units = None
        row.modified_by = self.user_id
        row.modified_at = datetime.now(timezone.utc)
        self.db.flush()
        return row

    def write_calculation(
        self,
        row: ResultEntry,
        calculated_result: Optional[str],
        reported_result: Optional[str],
    ) -> ResultEntry:
        """Write a calculation's outputs. Raw is never changed here."""
        self._refuse_if_published(row)
        with calculation_write(self.db):
            row.calculated_result = calculated_result
            row.reported_result = reported_result
            row.modified_by = self.user_id
            row.modified_at = datetime.now(timezone.utc)
        return row
