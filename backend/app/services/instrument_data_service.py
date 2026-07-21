"""
Parser engine — applies ParserConfig (file definition) to a text table.

Rules:
- The config is the definition of a valid file.
- Deviations produce hard_errors with line, column (source_col), and issue.
- well_col / sample_col are optional LIMS hints only — not assumed for every instrument.
- Never raise uncaught validation errors during test/import (return report instead).
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.schemas.flexible_experiment import LimsRunDataRow, ParserConfig

# LIMS DB / LimsRunDataRow constraint when denormalizing well_col into well_position
WELL_POSITION_MAX_LEN = 10
# Cap errors so one huge file does not flood the UI
MAX_HARD_ERRORS = 50
MAX_WARNINGS = 50


@dataclass
class ParseReport:
    ok: bool
    hard_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    row_count: int = 0
    preview_rows: List[dict] = field(default_factory=list)


@dataclass
class FileReport:
    filename: str
    ok: bool
    hard_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    row_count: int = 0


def _err(line: Optional[int], column: Optional[str], issue: str) -> str:
    """Standard diagnostic: line / column / issue."""
    parts = []
    if line is not None:
        parts.append(f"line {line}")
    if column:
        parts.append(f"column '{column}'")
    prefix = ", ".join(parts)
    return f"{prefix}: {issue}" if prefix else issue


class InstrumentDataService:
    """
    Parses a text table using a parser_config and returns rows + diagnostics.

    Usage:
        service = InstrumentDataService(parser_config_dict)
        rows, warnings, hard = service.parse(file_bytes)
        report = service.parse_report(file_bytes)
    """

    def __init__(self, parser_config: dict) -> None:
        try:
            self._config = ParserConfig.model_validate(parser_config)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid parser config: {e}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid parser config: {e}",
            )

    def parse(
        self,
        file_bytes: bytes,
        *,
        max_rows: Optional[int] = None,
        raise_on_hard: bool = True,
    ) -> Tuple[List[LimsRunDataRow], List[str], List[str]]:
        """
        Returns (rows, warnings, hard_errors).
        If raise_on_hard and hard_errors, raises 422 (import path).
        """
        rows, warnings, hard = self._parse_internal(file_bytes, max_rows=max_rows)
        if raise_on_hard and hard:
            detail = "; ".join(hard[:20])
            if len(hard) > 20:
                detail += f" … (+{len(hard) - 20} more)"
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )
        return rows, warnings, hard

    def parse_report(
        self,
        file_bytes: bytes,
        *,
        max_rows: Optional[int] = None,
        preview_cap: int = 10,
    ) -> ParseReport:
        rows, warnings, hard = self._parse_internal(file_bytes, max_rows=max_rows)
        preview = [r.row_data for r in rows[:preview_cap]]
        return ParseReport(
            ok=len(hard) == 0,
            hard_errors=hard,
            warnings=warnings,
            row_count=len(rows),
            preview_rows=preview,
        )

    def _add_hard(self, hard_errors: list[str], msg: str) -> None:
        if len(hard_errors) < MAX_HARD_ERRORS:
            hard_errors.append(msg)
        elif len(hard_errors) == MAX_HARD_ERRORS:
            hard_errors.append(f"… further errors omitted (limit {MAX_HARD_ERRORS})")

    def _add_warn(self, warnings: list[str], msg: str) -> None:
        if len(warnings) < MAX_WARNINGS:
            warnings.append(msg)

    def _parse_internal(
        self,
        file_bytes: bytes,
        *,
        max_rows: Optional[int] = None,
    ) -> Tuple[List[LimsRunDataRow], List[str], List[str]]:
        hard_errors: list[str] = []
        warnings: list[str] = []
        encoding = self._config.encoding or "utf-8"
        try:
            text = file_bytes.decode(encoding, errors="strict")
        except LookupError:
            hard_errors.append(_err(None, None, f"unknown encoding '{encoding}'"))
            return [], warnings, hard_errors
        except UnicodeDecodeError as e:
            hard_errors.append(
                _err(
                    None,
                    None,
                    f"file is not valid {encoding} (decode error at byte {e.start}: {e.reason})",
                )
            )
            return [], warnings, hard_errors

        delimiter = self._config.delimiter if self._config.delimiter is not None else ","
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)

        line_no = 0
        # skip_rows: lines discarded before header
        for _ in range(self._config.skip_rows):
            try:
                next(reader)
                line_no += 1
            except StopIteration:
                hard_errors.append(
                    _err(None, None, f"file ended while applying skip_rows={self._config.skip_rows}")
                )
                return [], warnings, hard_errors

        # header_row: extra discarded lines after skip_rows (0 = next line is header)
        for _ in range(self._config.header_row):
            try:
                next(reader)
                line_no += 1
            except StopIteration:
                hard_errors.append(
                    _err(None, None, f"file ended while applying header_row={self._config.header_row}")
                )
                return [], warnings, hard_errors

        try:
            headers = [h.strip() for h in next(reader)]
            line_no += 1
            header_line = line_no
        except StopIteration:
            hard_errors.append(_err(None, None, "file empty after skip_rows/header_row; no header line"))
            return [], warnings, hard_errors

        if not any(headers):
            hard_errors.append(_err(header_line, None, "header line is empty"))
            return [], warnings, hard_errors

        expected_source_cols = {col.source_col for col in self._config.columns}
        missing_cols = sorted(expected_source_cols - set(headers))
        if missing_cols:
            hard_errors.append(
                _err(
                    header_line,
                    None,
                    f"missing expected column(s) defined in parser: {missing_cols}; "
                    f"found headers: {headers}",
                )
            )
            return [], warnings, hard_errors

        # Optional LIMS hints must name a column that exists if set
        well_col = self._config.well_col
        sample_col = self._config.sample_col
        if well_col and well_col not in headers:
            hard_errors.append(
                _err(
                    header_line,
                    well_col,
                    f"well_col '{well_col}' is not among file headers: {headers}",
                )
            )
        if sample_col and sample_col not in headers:
            hard_errors.append(
                _err(
                    header_line,
                    sample_col,
                    f"sample_col '{sample_col}' is not among file headers: {headers}",
                )
            )
        if hard_errors:
            return [], warnings, hard_errors

        col_map = {col.source_col: col for col in self._config.columns}
        rows: list[LimsRunDataRow] = []

        for raw_row in reader:
            line_no += 1
            if max_rows and len(rows) >= max_rows:
                break
            if not any(cell.strip() if isinstance(cell, str) else cell for cell in raw_row):
                continue  # blank line

            row_dict = dict(zip(headers, raw_row))
            row_data: dict[str, Any] = {}
            row_failed = False

            for source_col, col_def in col_map.items():
                raw_val = (row_dict.get(source_col) or "").strip()
                try:
                    row_data[col_def.field_name] = _coerce(raw_val, col_def.data_type)
                except ValueError as ve:
                    row_failed = True
                    self._add_hard(
                        hard_errors,
                        _err(
                            line_no,
                            source_col,
                            f"{ve} (data_type={col_def.data_type}, value={raw_val!r})",
                        ),
                    )

            # Optional: denormalize well into LimsRunData.well_position (only if well_col set)
            well_position: Optional[str] = None
            if well_col:
                well_raw = (row_dict.get(well_col) or "").strip()
                if well_raw:
                    if len(well_raw) > WELL_POSITION_MAX_LEN:
                        row_failed = True
                        self._add_hard(
                            hard_errors,
                            _err(
                                line_no,
                                well_col,
                                f"value {well_raw!r} exceeds maximum length "
                                f"{WELL_POSITION_MAX_LEN} for LIMS well_position "
                                f"(parser well_col is set; leave well_col null if this "
                                f"file has no well IDs)",
                            ),
                        )
                    else:
                        well_position = well_raw

            if row_failed:
                continue

            try:
                rows.append(
                    LimsRunDataRow(
                        well_position=well_position,
                        row_data=row_data,
                    )
                )
            except ValidationError as e:
                for err in e.errors():
                    loc = ".".join(str(x) for x in err.get("loc", ()))
                    self._add_hard(
                        hard_errors,
                        _err(line_no, loc or None, err.get("msg", "validation error")),
                    )

        if not rows and not hard_errors:
            hard_errors.append(_err(None, None, "no data rows found after header"))

        return rows, warnings, hard_errors


class ParserEngine:
    """Dual-use engine: production import + setup test suite."""

    def parse(
        self,
        file_bytes: bytes,
        config: dict | ParserConfig,
        *,
        max_rows: Optional[int] = None,
    ) -> ParseReport:
        cfg = config if isinstance(config, dict) else config.model_dump()
        return InstrumentDataService(cfg).parse_report(file_bytes, max_rows=max_rows)

    def run_test_suite(
        self,
        config: dict | ParserConfig,
        files: list[tuple[str, bytes]],
    ) -> list[FileReport]:
        cfg = config if isinstance(config, dict) else config.model_dump()
        reports: list[FileReport] = []
        for name, content in files:
            try:
                pr = InstrumentDataService(cfg).parse_report(content)
                reports.append(
                    FileReport(
                        filename=name,
                        ok=pr.ok,
                        hard_errors=pr.hard_errors,
                        warnings=pr.warnings,
                        row_count=pr.row_count,
                    )
                )
            except HTTPException as e:
                detail = e.detail if isinstance(e.detail, str) else str(e.detail)
                reports.append(
                    FileReport(filename=name, ok=False, hard_errors=[detail], row_count=0)
                )
            except Exception as e:
                reports.append(
                    FileReport(
                        filename=name,
                        ok=False,
                        hard_errors=[f"Parse failed: {type(e).__name__}: {e}"],
                        row_count=0,
                    )
                )
        return reports


def _coerce(value: str, data_type: str) -> Any:
    """
    Coerce cell text to the type declared in the parser definition.
    Empty string → None (null cell). Raises ValueError with a short reason.
    """
    if value == "":
        return None
    if data_type == "float":
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"number (float) expected, got {value!r}") from None
    if data_type == "integer":
        try:
            # allow "12.0" only if integral? keep strict int()
            return int(value)
        except ValueError:
            raise ValueError(f"integer expected, got {value!r}") from None
    if data_type == "boolean":
        low = value.lower()
        if low in ("true", "1", "yes", "y", "t"):
            return True
        if low in ("false", "0", "no", "n", "f"):
            return False
        raise ValueError(f"boolean expected (true/false/0/1), got {value!r}")
    # string
    return value
