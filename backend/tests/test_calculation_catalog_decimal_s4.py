"""S4 backend decimal catalog functions (CALC-REQ-38, 51, 53, 39, 28, 37).

KATs are the acceptance-criterion cases on the four versions. They run in
the backend decimal context and make no R call. Other cases here are unit
tests, not extra KAT cases.
"""
from __future__ import annotations

import inspect
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import calculation_catalog_decimal as dec
from app.services import calculation_catalog_r as rcat
from app.services.calculation_catalog_r import CatalogInputRefused
from app.services.calculation_kat import run_kats, version_fingerprint
from app.services.calculation_release import prepare_release
from app.services.calculation_runtime import expected_lock_from_commit, find_repo_root
from app.services.calculation_catalog_decimal import UnitFactor

DIGEST = "sha256:" + ("ab" * 32)


def _health() -> dict[str, Any]:
    lock = expected_lock_from_commit(find_repo_root())
    return {
        "status": "ok",
        "base": lock.base,
        "renv": lock.renv,
        "tree": lock.tree,
        "lock_hash": lock.lock_hash,
        "R_IMAGE_DIGEST": DIGEST,
        "sandbox": {
            "uid": 1000,
            "root_read_only": True,
            "scratch_tmpfs": True,
            "egress_blocked": True,
            "cpu_limited": True,
            "memory_limited": True,
            "pids_limited": True,
            "forbidden_env_absent": True,
        },
    }


def _factor(name: str, type_name: str, multiplier: Optional[str]) -> UnitFactor:
    return UnitFactor(
        name=name,
        type_name=type_name,
        multiplier=None if multiplier is None else Decimal(multiplier),
    )


FACTORS = {
    "mg": _factor("mg", "mass", "0.001"),
    "g": _factor("g", "mass", "1"),
    "EU/mL": _factor("EU/mL", "activity", "1"),
    "mg/mL": _factor("mg/mL", "concentration", "1"),
    "OD": _factor("OD", "absorbance", "1"),
    "s": _factor("s", "time", "1"),
    "pg/mL": _factor("pg/mL", "concentration", "0.000000001"),
    "g/L": _factor("g/L", "concentration", "1"),
    "blank-mult": _factor("blank-mult", "mass", None),
    "zero-mult": _factor("zero-mult", "mass", "0"),
}


def lookup(name: str) -> Optional[UnitFactor]:
    return FACTORS.get(name)


def _client() -> TestClient:
    return TestClient(dec.decimal_catalog_app(lookup))


# ---- apply_dilution (CALC-REQ-38) ------------------------------------------


def test_apply_dilution_multiplies_0_026_by_100_exactly() -> None:
    result = dec.apply_dilution("0.026", "100")
    assert result.stop is None and result.flags == () and result.r_called is False
    assert result.outputs == {"value": "2.6"}


def test_apply_dilution_missing_factor_is_missing_input() -> None:
    for factor in (None, "", "N/A"):
        result = dec.apply_dilution("0.026", factor)
        assert result.outputs == {} and result.flags == ("missing_input",)
        assert result.stop is None and result.r_called is False


def test_apply_dilution_missing_value_is_missing_input() -> None:
    result = dec.apply_dilution(None, "100")
    assert result.outputs == {} and result.flags == ("missing_input",)


@pytest.mark.parametrize("factor", ["0.999", "0", "0.0", "-1", "1e-1"])
def test_apply_dilution_factor_below_one_is_refused(factor: str) -> None:
    with pytest.raises(CatalogInputRefused) as caught:
        dec.apply_dilution("0.026", factor)
    assert caught.value.code == "invalid_input"
    assert "below 1" in caught.value.detail


@pytest.mark.parametrize("factor", ["1", "1.0", "1e0"])
def test_apply_dilution_factor_of_one_is_allowed(factor: str) -> None:
    result = dec.apply_dilution("0.026", factor)
    assert result.outputs["value"] == "0.026"
    assert result.stop is None


def test_apply_dilution_negative_value_is_multiplied() -> None:
    result = dec.apply_dilution("-0.026", "100")
    assert result.outputs == {"value": "-2.6"}
    assert result.stop is None


def test_apply_dilution_json_number_is_refused() -> None:
    with pytest.raises(CatalogInputRefused) as caught:
        dec.apply_dilution("0.026", 100)
    assert caught.value.code == "invalid_input"
    with pytest.raises(CatalogInputRefused):
        dec.apply_dilution(0.026, "100")


# ---- subtract (CALC-REQ-51) ------------------------------------------------


def test_subtract_2_572_minus_0_050_is_exactly_2_522() -> None:
    result = dec.subtract("2.572", "0.050")
    assert result.outputs == {"difference": "2.522"}
    assert result.stop is None and result.r_called is False
    # The same subtraction in binary is not 2.522.
    assert Decimal(str(2.572 - 0.050)) != Decimal("2.522")


def test_subtract_zero_difference_stores_0_and_does_not_stop() -> None:
    result = dec.subtract("2.572", "2.572")
    assert result.outputs == {"difference": "0"}
    assert result.stop is None and result.flags == ()


@pytest.mark.parametrize("minuend,subtrahend", [("2.572", None), (None, "0.050"), ("", "0.050"), ("2.572", "N/A")])
def test_subtract_missing_input_is_missing_input(minuend: Any, subtrahend: Any) -> None:
    result = dec.subtract(minuend, subtrahend)
    assert result.outputs == {} and result.flags == ("missing_input",)
    assert result.stop is None


def test_subtract_negative_difference_is_not_refused() -> None:
    result = dec.subtract("0.050", "2.572")
    assert result.outputs == {"difference": "-2.522"}
    assert result.stop is None


def test_subtract_does_not_substitute_zero_for_a_missing_input() -> None:
    result = dec.subtract("2.572", None)
    assert result.outputs == {}
    assert "0" not in result.outputs.values()


# ---- copy_raw (CALC-REQ-53) ------------------------------------------------


def test_copy_raw_writes_0_026_to_calculated_and_reported() -> None:
    raw = "0.026"
    result = dec.copy_raw(raw)
    assert result.outputs == {"calculated": "0.026", "reported": "0.026"}
    assert result.outputs["calculated"] == raw
    assert result.outputs["reported"] == raw
    assert result.stop is None and result.r_called is False


@pytest.mark.parametrize("raw", ["0.0260", "1.50", "1.5e-3", "-0.026", "0"])
def test_copy_raw_keeps_the_input_characters(raw: str) -> None:
    result = dec.copy_raw(raw)
    assert result.outputs["calculated"] == raw
    assert result.outputs["reported"] == raw
    assert result.stop is None


@pytest.mark.parametrize("raw", [None, "", "N/A"])
def test_copy_raw_missing_input_is_missing_input(raw: Any) -> None:
    result = dec.copy_raw(raw)
    assert result.outputs == {} and result.flags == ("missing_input",)
    assert result.stop is None


def test_copy_raw_json_number_is_refused_and_is_not_a_stop() -> None:
    with pytest.raises(CatalogInputRefused):
        dec.copy_raw(0.026)


# ---- convert_units (CALC-REQ-39, 37, 28) -----------------------------------


def test_convert_units_divides_2_6_by_10_exactly() -> None:
    result = dec.convert_units("2.6", mode="per_amount", amount="10")
    assert result.outputs == {"value": "0.26"}
    assert result.stop is None and result.r_called is False


def test_convert_units_division_uses_precision_50() -> None:
    result = dec.convert_units("1", mode="per_amount", amount="3")
    assert result.outputs["value"] == "0." + ("3" * 50)


@pytest.mark.parametrize("amount", [None, "", "N/A"])
def test_convert_units_missing_amount_is_missing_input(amount: Any) -> None:
    result = dec.convert_units("2.6", mode="per_amount", amount=amount)
    assert result.outputs == {} and result.flags == ("missing_input",)
    assert result.stop is None


@pytest.mark.parametrize("amount", ["0", "0.0", "-1", "-0.01"])
def test_convert_units_amount_not_positive_is_refused(amount: str) -> None:
    with pytest.raises(CatalogInputRefused) as caught:
        dec.convert_units("2.6", mode="per_amount", amount=amount)
    assert "greater than 0" in caught.value.detail


def test_convert_units_negative_value_is_divided() -> None:
    result = dec.convert_units("-2.6", mode="per_amount", amount="10")
    assert result.outputs == {"value": "-0.26"}


def test_convert_units_within_type_is_exact_in_decimal() -> None:
    result = dec.convert_units(
        "1000000000",
        mode="within_type",
        from_unit="pg/mL",
        to_unit="g/L",
        lookup=lookup,
    )
    assert result.outputs == {"value": "1"}
    grams = dec.convert_units("1000", mode="within_type", from_unit="mg", to_unit="g", lookup=lookup)
    assert grams.outputs == {"value": "1"}


def test_convert_units_same_unit_keeps_the_value() -> None:
    result = dec.convert_units("0.026", mode="within_type", from_unit="OD", to_unit="OD", lookup=lookup)
    assert result.outputs == {"value": "0.026"}


def test_convert_units_cross_type_is_refused() -> None:
    with pytest.raises(CatalogInputRefused) as caught:
        dec.convert_units(
            "2.6",
            mode="within_type",
            from_unit="EU/mL",
            to_unit="mg/mL",
            lookup=lookup,
        )
    assert caught.value.code == "invalid_input"
    assert "EU/mL" in caught.value.detail and "mg/mL" in caught.value.detail
    assert "differ" in caught.value.detail
    with pytest.raises(CatalogInputRefused):
        dec.convert_units("1", mode="within_type", from_unit="OD", to_unit="s", lookup=lookup)


def test_convert_units_unknown_unit_stops_and_names_it() -> None:
    result = dec.convert_units(
        "1",
        mode="within_type",
        from_unit="EU/kg",
        to_unit="EU/mL",
        lookup=lookup,
    )
    assert result.stop == dec.UNIT_NOT_FOUND
    assert result.outputs == {} and result.r_called is False
    assert result.detail is not None and "EU/kg" in result.detail


def test_convert_units_missing_unit_name_is_missing_input() -> None:
    result = dec.convert_units("1", mode="within_type", from_unit=None, to_unit="g", lookup=lookup)
    assert result.flags == ("missing_input",) and result.stop is None


def test_convert_units_bad_multiplier_is_refused() -> None:
    with pytest.raises(CatalogInputRefused):
        dec.convert_units("1", mode="within_type", from_unit="blank-mult", to_unit="g", lookup=lookup)
    with pytest.raises(CatalogInputRefused):
        dec.convert_units("1", mode="within_type", from_unit="zero-mult", to_unit="g", lookup=lookup)


def test_convert_units_unknown_mode_is_refused_and_does_not_default() -> None:
    with pytest.raises(CatalogInputRefused):
        dec.convert_units("2.6", mode="sideways", amount="10")
    with pytest.raises(CatalogInputRefused):
        dec.convert_units("2.6", mode="", amount="10")


def test_convert_units_json_number_is_refused() -> None:
    with pytest.raises(CatalogInputRefused):
        dec.convert_units(2.6, mode="per_amount", amount="10")


def test_factor_lookup_source_does_not_enable_rls_or_use_float_helpers() -> None:
    module = Path(dec.__file__).read_text(encoding="utf-8")
    assert "httpx" not in module
    assert "r_calculator" not in module
    assert "convert_to_base_unit" not in module
    assert "convert_from_base_unit" not in module
    query = inspect.getsource(dec.load_unit_factor).split("text(", 1)[1]
    assert "row_security" not in query
    assert "multiplier::text" in query


# ---- HTTP: stops 200, refusals 400 -----------------------------------------


def test_http_success_and_missing_input_are_200_with_string_outputs() -> None:
    with _client() as client:
        diluted = client.post(
            "/catalog/apply_dilution/v1",
            json={"value": "0.026", "dilution_factor": "100"},
        )
        assert diluted.status_code == 200
        body = diluted.json()
        assert body["outputs"] == {"value": "2.6"}
        assert body["r_called"] is False
        assert "stop" not in body
        assert all(isinstance(item, str) for item in body["outputs"].values())

        copied = client.post("/catalog/copy_raw/v1", json={"value": "0.026"})
        assert copied.status_code == 200
        assert copied.json()["outputs"] == {"calculated": "0.026", "reported": "0.026"}

        missing = client.post(
            "/catalog/apply_dilution/v1",
            json={"value": "0.026", "dilution_factor": None},
        )
        assert missing.status_code == 200
        assert missing.json()["outputs"] == {}
        assert missing.json()["flags"] == ["missing_input"]
        assert "stop" not in missing.json()


def test_http_refusal_is_400_and_stop_is_200() -> None:
    with _client() as client:
        refused = client.post(
            "/catalog/apply_dilution/v1",
            json={"value": "0.026", "dilution_factor": "0.5"},
        )
        assert refused.status_code == 400
        assert refused.json()["code"] == "invalid_input"
        assert "stop" not in refused.json()

        number = client.post(
            "/catalog/subtract/v1",
            json={"minuend": "2.572", "subtrahend": 0.05},
        )
        assert number.status_code == 400
        assert number.json()["code"] == "invalid_input"

        amount = client.post(
            "/catalog/convert_units/v1",
            json={"mode": "per_amount", "value": "2.6", "amount": "0"},
        )
        assert amount.status_code == 400

        cross = client.post(
            "/catalog/convert_units/v1",
            json={"mode": "within_type", "value": "1", "from_unit": "EU/mL", "to_unit": "mg/mL"},
        )
        assert cross.status_code == 400
        assert "differ" in cross.json()["detail"]

        unknown = client.post(
            "/catalog/convert_units/v1",
            json={"mode": "within_type", "value": "1", "from_unit": "EU/kg", "to_unit": "mg"},
        )
        assert unknown.status_code == 200
        assert unknown.json()["stop"] == "unit_not_found"
        assert "EU/kg" in unknown.json()["detail"]
        assert unknown.json()["outputs"] == {}

        extra = client.post(
            "/catalog/copy_raw/v1",
            json={"value": "0.026", "model": "LL.4"},
        )
        assert extra.status_code == 400
        assert "unknown field" in extra.json()["detail"]


def test_decimal_routes_are_not_mounted_on_the_lims_app_or_in_r() -> None:
    root = find_repo_root()
    main = (root / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert "calculation_catalog_decimal" not in main
    plumber = (root / "services" / "r-calculator" / "plumber.R").read_text(encoding="utf-8")
    catalog_r = (root / "services" / "r-calculator" / "R" / "catalog.R").read_text(encoding="utf-8")
    for name in ("apply_dilution", "subtract", "copy_raw", "convert_units"):
        assert name not in plumber
        assert name not in catalog_r
        assert all(version.name != name for version in rcat.R_CATALOG_VERSIONS)


# ---- KATs ------------------------------------------------------------------


def test_kats_pass_at_tolerance_zero_and_do_not_call_r() -> None:
    log = run_kats(list(dec.DECIMAL_CATALOG_VERSIONS), health=_health())
    assert log.lock_hash == expected_lock_from_commit(find_repo_root()).lock_hash
    assert len(log.cases) == 4
    for case in log.cases:
        assert case.passed, (case.case_id, case.error, [(o.name, o.observed, o.expected) for o in case.outputs])
        assert case.side == "backend"
        assert case.version == 1
        assert case.citation.strip()
        assert "Not an SOP" in case.citation
        for output in case.outputs:
            assert output.tolerance.kind == "absolute"
            assert output.tolerance.value == "0"
            assert output.passed
    by_id = {case.case_id: case for case in log.cases}
    assert by_id["apply-dilution-0.026-times-100"].outputs[0].observed == "2.6"
    assert by_id["subtract-2.572-minus-0.050"].outputs[0].observed == "2.522"
    copy = {item.name: item.observed for item in by_id["copy-raw-0.026"].outputs}
    assert copy == {"calculated": "0.026", "reported": "0.026"}
    assert by_id["convert-units-2.6-over-10"].outputs[0].observed == "0.26"

    record = prepare_release(
        "s4-decimal-v1",
        [version.key for version in dec.DECIMAL_CATALOG_VERSIONS],
        catalog=list(dec.DECIMAL_CATALOG_VERSIONS),
        ledger=[],
        run_log=log,
    )
    assert record.lock_hash == log.lock_hash
    assert {item.name for item in record.adds} == {
        "apply_dilution",
        "subtract",
        "copy_raw",
        "convert_units",
    }
    # The check above is in memory. S4 does not write a release record.
    assert "write_release" not in Path(dec.__file__).read_text(encoding="utf-8")


def test_versions_are_backend_v1_with_no_r_route() -> None:
    names = [version.name for version in dec.DECIMAL_CATALOG_VERSIONS]
    assert names == ["apply_dilution", "subtract", "copy_raw", "convert_units"]
    for version in dec.DECIMAL_CATALOG_VERSIONS:
        assert version.version == 1 and version.side == "backend"
        assert version.route is None and version.r_sources == ()
        assert version.compute is not None
        assert version.kats and version.description
        assert version.stop_rule and version.missing_data_rule
        version_fingerprint(version)
        for case in version.kats:
            for tolerance in case.tolerance.values():
                assert tolerance.kind == "absolute" and tolerance.value == "0"


def test_0122_sits_under_the_single_alembic_head() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    backend = Path(__file__).resolve().parents[1]
    revision = "0122_calculation_units_seed"
    src = (backend / "db/migrations/versions" / f"{revision}.py").read_text(encoding="utf-8")
    assert f'revision = "{revision}"' in src
    assert 'down_revision = "0121_shared_reason_rules"' in src
    assert len(revision) <= 32
    assert "ENABLE ROW LEVEL SECURITY" not in src
    assert "DELETE FROM units" not in src.split("def downgrade()", 1)[0]
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "db/migrations"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["0127_calculation_attempts"], script.get_heads()
    assert script.get_revision("0123_result_entry_data_model").down_revision == revision


# ---- units seed and the real multiplier lookup -----------------------------


def test_seeded_units_and_lookup_do_not_use_rls(migrated_engine) -> None:
    with migrated_engine.connect() as conn:
        flags = conn.execute(
            text(
                """
                SELECT c.relrowsecurity, c.relforcerowsecurity,
                       (SELECT count(*) FROM pg_policy p WHERE p.polrelid = c.oid)
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = 'units'
                """
            )
        ).one()
        assert tuple(flags) == (False, False, 0)
        scale = conn.execute(
            text(
                """
                SELECT numeric_precision, numeric_scale
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'units'
                  AND column_name = 'multiplier'
                """
            )
        ).one()
        assert tuple(scale) == (20, 10)

    with migrated_engine.connect() as conn:
        conn.execute(text("SET ROLE app_test_role"))
        session = Session(bind=conn)
        try:
            for name, type_name in (("OD", "absorbance"), ("s", "time"), ("1", "dimensionless")):
                factor = dec.load_unit_factor(session, name)
                assert factor is not None, name
                assert factor.type_name == type_name
                assert factor.multiplier == Decimal("1")
                assert type(factor.multiplier) is Decimal
            same = dec.convert_units(
                "0.026", mode="within_type", from_unit="OD", to_unit="OD", session=session
            )
            assert same.outputs["value"] == "0.026"
            grams = dec.convert_units(
                "1000", mode="within_type", from_unit="mg", to_unit="g", session=session
            )
            assert grams.outputs["value"] == "1"
            picograms = dec.convert_units(
                "1000000000",
                mode="within_type",
                from_unit="pg/mL",
                to_unit="g/L",
                session=session,
            )
            assert picograms.outputs["value"] == "1"
            with pytest.raises(CatalogInputRefused) as caught:
                dec.convert_units(
                    "1",
                    mode="within_type",
                    from_unit="EU/mL",
                    to_unit="mg/mL",
                    session=session,
                )
            assert "differ" in caught.value.detail
            missing = dec.convert_units(
                "1",
                mode="within_type",
                from_unit="EU/kg",
                to_unit="EU/mL",
                session=session,
            )
            assert missing.stop == "unit_not_found"
            assert missing.detail is not None and "EU/kg" in missing.detail
        finally:
            session.close()
            conn.execute(text("RESET ROLE"))
