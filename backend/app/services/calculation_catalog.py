"""Closed calculation catalog (CALC-REQ-22).

Version 1 is these eleven functions, declared in code. This module does not
add, enable, or remove an entry. There is no API, UI, database table, runtime
switch, or agent path that changes the list.
"""
from __future__ import annotations

from app.services.calculation_catalog_decimal import DECIMAL_CATALOG_VERSIONS
from app.services.calculation_catalog_r import R_CATALOG_VERSIONS
from app.services.calculation_catalog_s5 import S5_CATALOG_VERSIONS
from app.services.calculation_kat import FunctionVersion

# Spec order (CALC-REQ-22).
CLOSED_CATALOG_NAMES: tuple[str, ...] = (
    "fit_4pl",
    "inverse_4pl",
    "fit_loglog_linear",
    "inverse_loglog_linear",
    "replicate_mean_cv",
    "spike_recovery",
    "limit_compare",
    "apply_dilution",
    "convert_units",
    "subtract",
    "copy_raw",
)


def closed_catalog() -> tuple[FunctionVersion, ...]:
    """The eleven catalog versions, in Spec order."""
    by_name = {
        version.name: version
        for version in (*R_CATALOG_VERSIONS, *S5_CATALOG_VERSIONS, *DECIMAL_CATALOG_VERSIONS)
    }
    if set(by_name) != set(CLOSED_CATALOG_NAMES) or len(by_name) != len(CLOSED_CATALOG_NAMES):
        raise RuntimeError("the catalog is not the eleven functions in CALC-REQ-22")
    return tuple(by_name[name] for name in CLOSED_CATALOG_NAMES)
