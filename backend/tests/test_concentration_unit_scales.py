"""Migration 0092 puts mass concentration on one scale and splits other dimensions."""
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

NAMES = (
    "g/L",
    "mg/L",
    "ng/µL",
    "µg/mL",
    "mg/mL",
    "pg/mL",
    "EU/mL",
    "copies/µL",
    "cfu",
    "mM",
    "µM",
    "nM",
    "mol/L",
)


def test_seeded_units_convert_only_within_a_dimension(migrated_engine):
    session = sessionmaker(bind=migrated_engine)()
    try:
        rows = session.execute(
            text(
                """
                SELECT u.name, u.multiplier, t.name
                FROM units u
                JOIN list_entries t ON t.id = u.type
                WHERE u.name = ANY(:names)
                """
            ),
            {"names": list(NAMES)},
        ).fetchall()
    finally:
        session.close()
    found = {name: (Decimal(multiplier), type_name) for name, multiplier, type_name in rows}
    assert set(NAMES) <= set(found)

    def multiplier(name: str) -> Decimal:
        return found[name][0]

    def unit_type(name: str) -> str:
        return found[name][1]

    assert unit_type("g/L") == "concentration"
    assert multiplier("g/L") == Decimal("1")
    assert multiplier("mg/mL") == Decimal("1")
    assert multiplier("ng/µL") == multiplier("µg/mL") == multiplier("mg/L") == Decimal("0.001")
    assert multiplier("g/L") == multiplier("ng/µL") * Decimal("1000")
    assert multiplier("pg/mL") == Decimal("0.000000001")
    assert unit_type("EU/mL") == "activity"
    assert multiplier("EU/mL") == Decimal("1")
    assert unit_type("copies/µL") == "copy_concentration"
    assert unit_type("cfu") == "count"
    assert unit_type("EU/mL") != unit_type("ng/µL")
    assert unit_type("copies/µL") != unit_type("ng/µL")
    assert unit_type("mM") == "molar"
    assert multiplier("mol/L") == Decimal("1")
    assert multiplier("mM") == Decimal("0.001")
    assert multiplier("µM") == Decimal("0.000001")
    assert multiplier("nM") == Decimal("0.000000001")
