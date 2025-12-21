"""
Unit conversion utilities for LIMS MVP
"""
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from models.unit import Unit


class ConversionError(Exception):
    """Raised when unit conversion fails"""
    pass


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
    unit = db.query(Unit).filter(Unit.id == unit_id, Unit.active == True).first()
    
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
    unit = db.query(Unit).filter(Unit.id == unit_id, Unit.active == True).first()
    
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
    
    # Get base concentration unit
    base_concentration_unit = db.query(Unit).filter(
        Unit.type == "concentration",  # Assuming this list entry exists
        Unit.multiplier == 1.0  # Base unit
    ).first()
    
    if not base_concentration_unit:
        raise ConversionError("Base concentration unit not found")
    
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
    
    # Get base volume unit
    base_volume_unit = db.query(Unit).filter(
        Unit.type == "volume",  # Assuming this list entry exists
        Unit.multiplier == 1.0  # Base unit
    ).first()
    
    if not base_volume_unit:
        raise ConversionError("Base volume unit not found")
    
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
    
    # Check significant figures (simplified check)
    if data_type == "numeric" and significant_figures is not None:
        try:
            num_value = float(value)
            # This is a simplified check - in practice, you'd count actual significant figures
            if len(str(num_value).replace('.', '').lstrip('0')) > significant_figures:
                errors.append(f"Value may have more than {significant_figures} significant figures")
        except ValueError:
            pass  # Already caught by data type validation
    
    return len(errors) == 0, errors
