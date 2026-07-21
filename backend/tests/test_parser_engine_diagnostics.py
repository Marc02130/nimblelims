"""Parser engine: definition-driven errors with line/column diagnostics."""
from app.services.instrument_data_service import InstrumentDataService, ParserEngine


def _cfg(**overrides):
    base = {
        "schema_version": "1",
        "delimiter": ",",
        "encoding": "utf-8",
        "skip_rows": 0,
        "header_row": 0,
        "columns": [
            {"source_col": "Well", "field_name": "well_position", "data_type": "string"},
            {"source_col": "LabNumber", "field_name": "lab_number", "data_type": "string"},
        ],
        "well_col": "Well",
        "sample_col": None,
    }
    base.update(overrides)
    return base


def test_long_well_is_hard_error_with_line_and_column():
    csv = b"Well,LabNumber\nXinyao Xiao,12345\nA01,999\n"
    pr = InstrumentDataService(_cfg()).parse_report(csv)
    assert pr.ok is False
    assert pr.row_count == 1  # A01 row still accepted
    assert any("line 2" in e and "Well" in e and "maximum length" in e for e in pr.hard_errors)


def test_no_well_col_allows_long_string_fields():
    """Files without wells: leave well_col null; long strings are fine."""
    cfg = _cfg(
        well_col=None,
        columns=[
            {"source_col": "Name", "field_name": "person_name", "data_type": "string"},
            {"source_col": "LabNumber", "field_name": "lab_number", "data_type": "string"},
        ],
    )
    csv = b"Name,LabNumber\nXinyao Xiao,12345\n"
    pr = InstrumentDataService(cfg).parse_report(csv)
    assert pr.ok is True
    assert pr.row_count == 1
    assert pr.preview_rows[0]["person_name"] == "Xinyao Xiao"


def test_float_type_error_reports_line_column():
    cfg = _cfg(
        well_col=None,
        columns=[
            {"source_col": "Well", "field_name": "well_position", "data_type": "string"},
            {"source_col": "Value", "field_name": "raw_value", "data_type": "float"},
        ],
    )
    csv = b"Well,Value\nA01,not-a-number\nB01,1.5\n"
    pr = InstrumentDataService(cfg).parse_report(csv)
    assert pr.ok is False
    assert any("line 2" in e and "Value" in e and "float" in e for e in pr.hard_errors)
    assert pr.row_count == 1


def test_missing_column_reports_header_line():
    csv = b"Well,Other\nA01,x\n"
    pr = InstrumentDataService(_cfg()).parse_report(csv)
    assert pr.ok is False
    assert any("LabNumber" in e and "missing" in e for e in pr.hard_errors)


def test_fluidx_suite_still_clean():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "TestData" / "FluidX"
    if not root.exists():
        return  # optional local fixture
    files = [(p.name, p.read_bytes()) for p in sorted(root.glob("test*.csv"))]
    reps = ParserEngine().run_test_suite(_cfg(), files)
    assert all(r.ok for r in reps)
