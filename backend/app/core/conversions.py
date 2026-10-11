"""
Unit conversion utilities for NimbleLims.

A lab picks one base unit per type. That unit's multiplier is 1.
Every other unit of the type stores how many base units are in one of it.
``value_in_base = value * multiplier``.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Sequence, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from models.unit import Unit


class ConversionError(Exception):
    """Raised when unit conversion fails"""
    pass


_MULTIPLIER_SCALE = Decimal("0.0000000001")  # units.multiplier is numeric(20, 10)


def multiplier_decimal(value) -> Optional[Decimal]:
    """Multiplier as a Decimal, or None when the unit has none."""
    if value is None:
        return None
    return Decimal(str(value))


def is_base_multiplier(value) -> bool:
    """True when this multiplier is the base (exactly 1)."""
    dec = multiplier_decimal(value)
    return dec is not None and dec == Decimal("1")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_MULTIPLIER_SCALE, rounding=ROUND_HALF_UP)


def require_positive_multiplier(value) -> Decimal:
    """Multiplier used to convert into the base. Missing or non-positive is an error."""
    dec = multiplier_decimal(value)
    if dec is None:
        raise ConversionError("Multiplier is required")
    if dec <= 0:
        raise ConversionError("Multiplier must be greater than zero")
    return dec


def active_base_units(db: Session, type_id) -> list[Unit]:
    """Active units of this type whose multiplier is 1. There should be one."""
    units = (
        db.query(Unit)
        .filter(Unit.type == type_id, Unit.active == True)  # noqa: E712
        .all()
    )
    return [unit for unit in units if is_base_multiplier(unit.multiplier)]


def require_base_unit_named(db: Session, type_name: str) -> Unit:
    """Base unit for a unit-type list entry, looked up by its name (``volume``)."""
    from models.list import ListEntry

    entry = (
        db.query(ListEntry)
        .filter(ListEntry.name == type_name, ListEntry.active == True)  # noqa: E712
        .first()
    )
    if not entry:
        raise ConversionError(f"Unit type {type_name} is not configured")
    return require_base_unit(db, entry.id)


def require_base_unit(db: Session, type_id) -> Unit:
    """The lab's base unit for a type: the one active unit with multiplier 1."""
    bases = active_base_units(db, type_id)
    if len(bases) == 1:
        return bases[0]
    if not bases:
        raise ConversionError(
            "No base unit for this type. Pick one under Units. Its multiplier is 1."
        )
    names = ", ".join(sorted(unit.name for unit in bases))
    raise ConversionError(
        f"This type has more than one base unit ({names}). "
        "Pick one under Units and set the others relative to it."
    )


def designate_base_unit(db: Session, unit: Unit) -> None:
    """Make ``unit`` the base for its type and rescale the others.

    ``new_multiplier = old_multiplier / chosen_multiplier``, so a quantity
    still lands on the same base amount. The chosen unit becomes 1.
    Does not commit.
    """
    if not unit.active:
        raise ConversionError("An inactive unit cannot be the base")
    factor = require_positive_multiplier(unit.multiplier)
    siblings = db.query(Unit).filter(Unit.type == unit.type).all()
    same = [
        sibling
        for sibling in siblings
        if sibling.id != unit.id and multiplier_decimal(sibling.multiplier) == factor
    ]
    if same:
        names = ", ".join(sorted(sibling.name for sibling in same))
        raise ConversionError(
            f"{names} has the same multiplier as {unit.name}. "
            "Set that multiplier relative to this unit before using it as the base."
        )
    updates = []
    for sibling in siblings:
        current = require_positive_multiplier(sibling.multiplier)
        updates.append((sibling, _quantize(current / factor)))
    for sibling, new_value in updates:
        sibling.multiplier = new_value
    unit.multiplier = Decimal("1")


def assert_multiplier_for_save(
    db: Session,
    *,
    type_id,
    multiplier,
    current: Optional[Unit] = None,
) -> Decimal:
    """Check a create/update multiplier against the type's base.

    Switching which unit is the base is ``designate_base_unit``, not a raw 1
    typed over another unit. The only base unit stays at 1.
    """
    dec = require_positive_multiplier(multiplier)
    bases = active_base_units(db, type_id)
    current_id = current.id if current is not None else None
    others = [base for base in bases if base.id != current_id]
    current_is_base = current is not None and is_base_multiplier(current.multiplier)
    if not others and not current_is_base and dec != Decimal("1"):
        raise ConversionError("The first unit of a type is the base. Its multiplier is 1.")
    if dec == Decimal("1") and others:
        staying_base = (
            current is not None and current.type == type_id and current_is_base
        )
        if not staying_base:
            names = ", ".join(sorted(base.name for base in others))
            raise ConversionError(
                f"This type already has a base ({names}). "
                "Enter how many of that base are in one of this unit, "
                "or use this unit as the base."
            )
        return dec
    if dec == Decimal("1"):
        return dec
    if current_is_base and not others:
        raise ConversionError(
            "The base unit multiplier stays 1. Pick another unit as the base first."
        )
    return dec


def _unit_uuid(unit_id: str) -> UUID:
    try:
        return UUID(str(unit_id))
    except (ValueError, TypeError, AttributeError):
        raise ConversionError(f"Unit {unit_id} not found") from None


def _units_for_ids(db: Session, unit_ids: Sequence[str]) -> list[Unit]:
    rows = []
    for unit_id in unit_ids:
        unit = (
            db.query(Unit)
            .filter(Unit.id == _unit_uuid(unit_id), Unit.active == True)  # noqa: E712
            .first()
        )
        if not unit:
            raise ConversionError(f"Unit {unit_id} not found")
        rows.append(unit)
    return rows


def _require_one_type(units: Sequence[Unit], label: str) -> None:
    types = {unit.type for unit in units}
    if len(types) != 1:
        raise ConversionError(f"Cannot convert {label} units of different types")


def convert_to_base_unit(value: float, unit_id: str, db: Session) -> float:
    """
    Convert a value to its base unit using the unit's multiplier.
    
    Args:
        value: The value to convert
        unit_id: The ID of the unit to convert from
        db: Database session
        
    Returns:
        The value converted to base unit
        
    Raises:
        ConversionError: If unit not found or conversion fails
    """
    unit = db.query(Unit).filter(Unit.id == _unit_uuid(unit_id), Unit.active == True).first()  # noqa: E712

    if not unit:
        raise ConversionError(f"Unit {unit_id} not found")

    if unit.multiplier is None:
        raise ConversionError(f"Unit {unit_id} has no multiplier defined")

    return float(Decimal(str(value)) * Decimal(str(unit.multiplier)))


def convert_from_base_unit(value: float, unit_id: str, db: Session) -> float:
    """
    Convert a value from its base unit using the unit's multiplier.
    
    Args:
        value: The value to convert from base unit
        unit_id: The ID of the unit to convert to
        db: Database session
        
    Returns:
        The value converted from base unit
        
    Raises:
        ConversionError: If unit not found or conversion fails
    """
    unit = db.query(Unit).filter(Unit.id == _unit_uuid(unit_id), Unit.active == True).first()  # noqa: E712

    if not unit:
        raise ConversionError(f"Unit {unit_id} not found")

    if unit.multiplier is None:
        raise ConversionError(f"Unit {unit_id} has no multiplier defined")

    return float(Decimal(str(value)) / Decimal(str(unit.multiplier)))


def calculate_volume_from_concentration_and_amount(
    concentration: float, 
    concentration_units: str,
    amount: float, 
    amount_units: str,
    db: Session
) -> float:
    """
    Calculate volume from concentration and amount.
    Volume = Amount / Concentration (in base units)
    
    Args:
        concentration: The concentration value
        concentration_units: The concentration units ID
        amount: The amount value
        amount_units: The amount units ID
        db: Database session
        
    Returns:
        The calculated volume in base units
        
    Raises:
        ConversionError: If conversion fails
    """
    # Convert to base units
    concentration_base = convert_to_base_unit(concentration, concentration_units, db)
    amount_base = convert_to_base_unit(amount, amount_units, db)
    
    if concentration_base == 0:
        raise ConversionError("Cannot calculate volume: concentration is zero")
    
    return amount_base / concentration_base


def calculate_pooled_concentration(
    concentrations: list[float],
    concentration_units: list[str],
    amounts: list[float],
    amount_units: list[str],
    db: Session
) -> Tuple[float, str]:
    """
    Calculate pooled concentration from multiple samples.
    Uses weighted average: sum(concentration * volume) / sum(volume)
    
    Args:
        concentrations: List of concentration values
        concentration_units: List of concentration units IDs
        amounts: List of amount values
        amount_units: List of amount units IDs
        db: Database session
        
    Returns:
        Tuple of (pooled_concentration, base_concentration_unit_id)
        
    Raises:
        ConversionError: If conversion fails
    """
    if len(concentrations) != len(concentration_units) or len(amounts) != len(amount_units):
        raise ConversionError("All lists must have the same length")
    
    if len(concentrations) == 0:
        raise ConversionError("Cannot calculate pooled concentration: no samples provided")

    concentration_rows = _units_for_ids(db, concentration_units)
    _require_one_type(concentration_rows, "concentration")
    base_concentration_unit = require_base_unit(db, concentration_rows[0].type)
    
    total_weighted_concentration = 0.0
    total_volume = 0.0
    
    for i in range(len(concentrations)):
        # Convert to base units
        concentration_base = convert_to_base_unit(concentrations[i], concentration_units[i], db)
        amount_base = convert_to_base_unit(amounts[i], amount_units[i], db)
        
        # Calculate volume
        if concentration_base > 0:
            volume = amount_base / concentration_base
            total_weighted_concentration += concentration_base * volume
            total_volume += volume
    
    if total_volume == 0:
        raise ConversionError("Cannot calculate pooled concentration: total volume is zero")
    
    pooled_concentration = total_weighted_concentration / total_volume
    
    return float(pooled_concentration), str(base_concentration_unit.id)


def calculate_pooled_volume(
    amounts: list[float],
    amount_units: list[str],
    db: Session
) -> Tuple[float, str]:
    """
    Calculate total pooled volume from multiple samples.
    
    Args:
        amounts: List of amount values
        amount_units: List of amount units IDs
        db: Database session
        
    Returns:
        Tuple of (total_volume, base_volume_unit_id)
        
    Raises:
        ConversionError: If conversion fails
    """
    if len(amounts) != len(amount_units):
        raise ConversionError("Amounts and units lists must have the same length")
    
    if len(amounts) == 0:
        raise ConversionError("Cannot calculate pooled volume: no samples provided")

    # Sum amounts in the base unit of their type. The name is historical;
    # the base is whichever unit of that type the lab set to multiplier 1.
    amount_rows = _units_for_ids(db, amount_units)
    _require_one_type(amount_rows, "amount")
    base_volume_unit = require_base_unit(db, amount_rows[0].type)
    
    total_volume = 0.0
    
    for i in range(len(amounts)):
        # Convert to base units
        amount_base = convert_to_base_unit(amounts[i], amount_units[i], db)
        total_volume += amount_base
    
    return float(total_volume), str(base_volume_unit.id)


def validate_result_value(
    value: str,
    data_type: str,
    low_value: Optional[float] = None,
    high_value: Optional[float] = None,
    significant_figures: Optional[int] = None
) -> Tuple[bool, list[str]]:
    """
    Validate a result value against analysis_analytes rules.
    
    Args:
        value: The result value to validate
        data_type: Expected data type (e.g., 'numeric', 'text')
        low_value: Minimum allowed value
        high_value: Maximum allowed value
        significant_figures: Required significant figures
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check data type
    if data_type == "numeric":
        try:
            float(value)
        except ValueError:
            errors.append(f"Value '{value}' is not numeric")
            return False, errors
    
    # Check range
    if data_type == "numeric" and (low_value is not None or high_value is not None):
        try:
            num_value = float(value)
            if low_value is not None and num_value < low_value:
                errors.append(f"Value {num_value} is below minimum {low_value}")
            if high_value is not None and num_value > high_value:
                errors.append(f"Value {num_value} is above maximum {high_value}")
        except ValueError:
            pass  # Already caught by data type validation
    
    # Significant figures are a reporting/rounding rule, not an entry rule: raw
    # values routinely carry more digits than are reported. POST /results/validate
    # surfaces excess digits as a *warning*; this validator used to turn them into
    # a hard error (with a count based on str(float), which drops trailing zeros
    # and miscounts e.g. "1200" or "0.0012"). It no longer fails validation.
    return len(errors) == 0, errors


def count_significant_figures(value: str) -> Optional[int]:
    """Count significant figures in a numeric string as entered.

    Leading zeros never count; trailing zeros count only when a decimal point is
    present ("1200" -> 2, "1200." -> 4, "0.00120" -> 3). Scientific notation
    counts the mantissa. Returns None for non-numeric input.
    """
    s = (value or "").strip().lstrip("+-")
    mantissa = s.split("e")[0].split("E")[0]
    try:
        float(mantissa)
    except ValueError:
        return None
    has_point = "." in mantissa
    digits = mantissa.replace(".", "").lstrip("0")
    if not digits:
        return 1  # zero
    if not has_point:
        digits = digits.rstrip("0") or "0"
    return len(digits)
