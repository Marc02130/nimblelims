"""
InstrumentDataService — parses uploaded instrument CSV files using parser_config
and returns validated ExperimentDataRow objects ready for import.

Separates the CSV parsing concern from ExperimentRunService so that the import
preview (first 10 rows) and full import share the same parsing logic.
"""
from __future__ import annotations

import csv
import io
from typing import List, Tuple, Optional

from fastapi import HTTPException, status

from app.schemas.flexible_experiment import ExperimentDataRow, ParserConfig


class InstrumentDataService:
    """
    Parses an instrument CSV file using a parser_config and returns rows.

    Usage:
        service = InstrumentDataService(parser_config_dict)
        rows, warnings = service.parse(csv_bytes)
        preview = rows[:10]
    """

    def __init__(self, parser_config: dict) -> None:
        try:
            self._config = ParserConfig(**parser_config)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid parser config: {e}",
            )

    def parse(
        self,
        csv_bytes: bytes,
        *,
        max_rows: Optional[int] = None,
    ) -> Tuple[List[ExperimentDataRow], List[str]]:
        """
        Parse CSV bytes into ExperimentDataRow objects.

        Returns:
            (rows, warnings)
            rows: list of ExperimentDataRow ready for import
            warnings: list of non-fatal messages (e.g., skipped rows)
        """
        text = csv_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        warnings: list[str] = []

        # Skip header rows
        for _ in range(self._config.skip_rows):
            try:
                next(reader)
            except StopIteration:
                break

        # Read column headers
        try:
            headers = [h.strip() for h in next(reader)]
        except StopIteration:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="CSV file appears to be empty after skipping header rows",
            )

        # Validate that expected source_cols exist
        expected_source_cols = {col.source_col for col in self._config.columns}
        missing_cols = expected_source_cols - set(headers)
        if missing_cols:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"CSV is missing expected columns: {sorted(missing_cols)}",
            )

        well_col = self._config.well_col
        col_map = {col.source_col: col for col in self._config.columns}

        rows: list[ExperimentDataRow] = []
        for row_num, raw_row in enumerate(reader, start=self._config.skip_rows + 2):
            if max_rows and len(rows) >= max_rows:
                break
            if not any(raw_row):
                continue  # skip blank rows

            row_dict = dict(zip(headers, raw_row))

            # Build row_data with field_name keys
            row_data: dict = {}
            for source_col, col_def in col_map.items():
                raw_val = row_dict.get(source_col, "").strip()
                try:
                    row_data[col_def.field_name] = _coerce(raw_val, col_def.data_type)
                except ValueError:
                    warnings.append(
                        f"Row {row_num}: could not coerce '{raw_val}' to {col_def.data_type} "
                        f"for column '{source_col}' — stored as string"
                    )
                    row_data[col_def.field_name] = raw_val

            well_position = row_dict.get(well_col, "").strip() if well_col else None

            rows.append(
                ExperimentDataRow(
                    well_position=well_position or None,
                    row_data=row_data,
                )
            )

        return rows, warnings


def _coerce(value: str, data_type: str):
    """Coerce a string value to the target data type."""
    if value == "":
        return None
    if data_type == "float":
        return float(value)
    if data_type == "integer":
        return int(value)
    if data_type == "boolean":
        return value.lower() in ("true", "1", "yes")
    return value  # string
