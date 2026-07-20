"""
InstrumentDataService / ParserEngine — parse uploaded text tables using ParserConfig.

Decision #1: schema-first; engine implements every ParserConfig field.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.schemas.flexible_experiment import LimsRunDataRow, ParserConfig


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


class InstrumentDataService:
    """
    Parses an instrument/CRO text file using a parser_config and returns rows.

    Usage:
        service = InstrumentDataService(parser_config_dict)
        rows, warnings = service.parse(file_bytes)
        report = service.parse_report(file_bytes, max_rows=50)
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
        report = self.parse_report(file_bytes, max_rows=max_rows)
        if raise_on_hard and report.hard_errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="; ".join(report.hard_errors),
            )
        # Rebuild LimsRunDataRow list from successful parse
        rows, warnings, hard = self._parse_internal(file_bytes, max_rows=max_rows)
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
            text = file_bytes.decode(encoding, errors="replace")
        except LookupError:
            hard_errors.append(f"Unknown encoding: {encoding}")
            return [], warnings, hard_errors

        delimiter = self._config.delimiter if self._config.delimiter is not None else ","
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)

        # skip_rows: lines before header
        for _ in range(self._config.skip_rows):
            try:
                next(reader)
            except StopIteration:
                break

        # header_row: additional rows to skip after skip_rows (0 = next line is header)
        for _ in range(self._config.header_row):
            try:
                next(reader)
            except StopIteration:
                break

        try:
            headers = [h.strip() for h in next(reader)]
        except StopIteration:
            hard_errors.append("File appears empty after skipping header rows")
            return [], warnings, hard_errors

        expected_source_cols = {col.source_col for col in self._config.columns}
        missing_cols = expected_source_cols - set(headers)
        if missing_cols:
            hard_errors.append(f"Missing expected columns: {sorted(missing_cols)}")
            return [], warnings, hard_errors

        well_col = self._config.well_col
        sample_col = self._config.sample_col
        col_map = {col.source_col: col for col in self._config.columns}

        rows: list[LimsRunDataRow] = []
        for row_num, raw_row in enumerate(reader, start=self._config.skip_rows + self._config.header_row + 2):
            if max_rows and len(rows) >= max_rows:
                break
            if not any(raw_row):
                continue

            row_dict = dict(zip(headers, raw_row))
            row_data: dict = {}
            for source_col, col_def in col_map.items():
                raw_val = (row_dict.get(source_col) or "").strip()
                try:
                    row_data[col_def.field_name] = _coerce(raw_val, col_def.data_type)
                except ValueError:
                    warnings.append(
                        f"Row {row_num}: could not coerce '{raw_val}' to {col_def.data_type} "
                        f"for column '{source_col}' — stored as string"
                    )
                    row_data[col_def.field_name] = raw_val

            well_position = row_dict.get(well_col, "").strip() if well_col else None
            # sample_col stored in row_data only if mapped; optional separate handling later
            if sample_col and sample_col in row_dict and "sample_id" not in row_data:
                # leave as field if not mapped; do not invent UUID
                pass

            rows.append(
                LimsRunDataRow(
                    well_position=well_position or None,
                    row_data=row_data,
                )
            )

        if not rows and not hard_errors:
            hard_errors.append("No data rows found after header")

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
        return reports


def _coerce(value: str, data_type: str):
    if value == "":
        return None
    if data_type == "float":
        return float(value)
    if data_type == "integer":
        return int(value)
    if data_type == "boolean":
        return value.lower() in ("true", "1", "yes")
    return value
