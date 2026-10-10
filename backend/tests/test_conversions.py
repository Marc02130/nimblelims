"""
Tests for unit conversion utilities
"""
import pytest
from decimal import Decimal
from uuid import uuid4

from app.core.conversions import (
    ConversionError,
    convert_to_base_unit, convert_from_base_unit,
    designate_base_unit, require_base_unit,
    calculate_volume_from_concentration_and_amount,
    calculate_pooled_concentration, calculate_pooled_volume,
    validate_result_value,
)


class TestUnitConversions:
    """Test unit conversion functions"""
    
    def test_convert_to_base_unit(self, db_session, sample_units):
        """Test converting values to base units"""
        # Test with mg (multiplier 0.001 relative to g)
        mg_unit = sample_units['mg']
        result = convert_to_base_unit(1000.0, str(mg_unit.id), db_session)
        assert result == 1.0  # 1000 mg = 1 g
        
        # Test with µg (multiplier 0.000001 relative to g)
        ug_unit = sample_units['ug']
        result = convert_to_base_unit(1000000.0, str(ug_unit.id), db_session)
        assert result == 1.0  # 1000000 µg = 1 g
    
    def test_convert_from_base_unit(self, db_session, sample_units):
        """Test converting values from base units"""
        # Test with mg (multiplier 0.001 relative to g)
        mg_unit = sample_units['mg']
        result = convert_from_base_unit(1.0, str(mg_unit.id), db_session)
        assert result == 1000.0  # 1 g = 1000 mg
        
        # Test with µg (multiplier 0.000001 relative to g)
        ug_unit = sample_units['ug']
        result = convert_from_base_unit(1.0, str(ug_unit.id), db_session)
        assert result == 1000000.0  # 1 g = 1000000 µg
    
    def test_convert_to_base_unit_invalid_unit(self, db_session):
        """Test converting with invalid unit ID"""
        with pytest.raises(ConversionError):
            convert_to_base_unit(100.0, "invalid-unit-id", db_session)
    
    def test_convert_to_base_unit_no_multiplier(self, db_session, sample_units):
        """Test converting with unit that has no multiplier"""
        # Create a unit without multiplier
        from models.unit import Unit

        unit = Unit(
            name="test_unit_no_multiplier",
            description="Test unit without multiplier",
            type=sample_units["g"].type,
            multiplier=None,  # No multiplier
            created_by=sample_units['g'].created_by,
            modified_by=sample_units['g'].modified_by
        )
        db_session.add(unit)
        db_session.commit()
        
        with pytest.raises(ConversionError):
            convert_to_base_unit(100.0, str(unit.id), db_session)


class TestVolumeCalculations:
    """Test volume calculation functions"""
    
    def test_calculate_volume_from_concentration_and_amount(self, db_session, sample_units):
        """Test calculating volume from concentration and amount"""
        # Test: 10 mg/mL concentration, 5 mg amount = 0.5 mL volume
        concentration = 10.0  # mg/mL
        concentration_units = str(sample_units['mg_ml'].id)
        amount = 5.0  # mg
        amount_units = str(sample_units['mg'].id)
        
        volume = calculate_volume_from_concentration_and_amount(
            concentration, concentration_units,
            amount, amount_units,
            db_session
        )
        
        # 5 mg is 0.005 of the mass base (g). 10 mg/mL is already the
        # concentration base. 0.005 / 10 = 0.0005 in those bases.
        assert abs(volume - 0.0005) < 0.0000001
    
    def test_calculate_volume_zero_concentration(self, db_session, sample_units):
        """Test calculating volume with zero concentration"""
        with pytest.raises(ConversionError):
            calculate_volume_from_concentration_and_amount(
                0.0, str(sample_units['mg_ml'].id),
                5.0, str(sample_units['mg'].id),
                db_session
            )


class TestPooledCalculations:
    """Test pooled sample calculations"""
    
    def test_calculate_pooled_concentration(self, db_session, sample_units):
        """Test calculating pooled concentration"""
        concentrations = [10.0, 20.0]  # mg/mL
        concentration_units = [str(sample_units['mg_ml'].id), str(sample_units['mg_ml'].id)]
        amounts = [5.0, 10.0]  # mg
        amount_units = [str(sample_units['mg'].id), str(sample_units['mg'].id)]
        
        pooled_conc, base_unit_id = calculate_pooled_concentration(
            concentrations, concentration_units,
            amounts, amount_units,
            db_session
        )
        
        # Expected: weighted average
        # Sample 1: 10 mg/mL, 0.5 mL volume
        # Sample 2: 20 mg/mL, 0.5 mL volume
        # Pooled: (10*0.5 + 20*0.5) / (0.5 + 0.5) = 15 mg/mL
        assert abs(pooled_conc - 15.0) < 0.001
        assert base_unit_id == str(sample_units['mg_ml'].id)
    
    def test_calculate_pooled_concentration_empty_list(self, db_session):
        """Test calculating pooled concentration with empty list"""
        with pytest.raises(ConversionError):
            calculate_pooled_concentration([], [], [], [], db_session)
    
    def test_calculate_pooled_volume(self, db_session, sample_units):
        """Test calculating pooled volume"""
        amounts = [5.0, 10.0]  # mg
        amount_units = [str(sample_units['mg'].id), str(sample_units['mg'].id)]
        
        total_volume, base_unit_id = calculate_pooled_volume(
            amounts, amount_units, db_session
        )
        
        # 5 mg + 10 mg = 0.015 g when grams are the base (multiplier 1)
        # and milligrams are 0.001.
        assert abs(total_volume - 0.015) < 0.0000001
        assert base_unit_id == str(sample_units['g'].id)
    
    def test_calculate_pooled_volume_empty_list(self, db_session):
        """Test calculating pooled volume with empty list"""
        with pytest.raises(ConversionError):
            calculate_pooled_volume([], [], db_session)


class TestResultValidation:
    """Test result validation functions"""
    
    def test_validate_numeric_result(self):
        """Test validating numeric results"""
        is_valid, errors = validate_result_value("123.45", "numeric")
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_numeric_result_invalid(self):
        """Test validating invalid numeric results"""
        is_valid, errors = validate_result_value("abc", "numeric")
        assert not is_valid
        assert len(errors) > 0
    
    def test_validate_numeric_result_range(self):
        """Test validating numeric results with range constraints"""
        is_valid, errors = validate_result_value("5.0", "numeric", low_value=0.0, high_value=10.0)
        assert is_valid
        assert len(errors) == 0
        
        is_valid, errors = validate_result_value("15.0", "numeric", low_value=0.0, high_value=10.0)
        assert not is_valid
        assert any("above maximum" in error for error in errors)
        
        is_valid, errors = validate_result_value("-5.0", "numeric", low_value=0.0, high_value=10.0)
        assert not is_valid
        assert any("below minimum" in error for error in errors)
    
    def test_validate_text_result(self):
        """Test validating text results"""
        is_valid, errors = validate_result_value("Positive", "text")
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_significant_figures(self):
        """Test validating significant figures"""
        is_valid, errors = validate_result_value("123.456", "numeric", significant_figures=3)
        assert is_valid  # This is a simplified check
        assert len(errors) == 0


@pytest.fixture
def sample_units(db_session):
    """Units on their own types, so seed data with several multiplier-1 rows cannot collide."""
    from models.unit import Unit
    from models.list import List, ListEntry

    unit_list = db_session.query(List).filter(List.name == "Unit Types").first()
    if unit_list is None:
        unit_list = List(name="Unit Types", description="unit types")
        db_session.add(unit_list)
        db_session.flush()

    suffix = uuid4().hex[:8]

    def entry(label: str) -> ListEntry:
        row = ListEntry(name=f"{label}-{suffix}", description=label, list_id=unit_list.id)
        db_session.add(row)
        db_session.flush()
        return row

    mass_type = entry("mass")
    volume_type = entry("volume")
    concentration_type = entry("concentration")

    g_unit = Unit(
        name=f"g-{suffix}",
        description="Gram (base mass unit)",
        type=mass_type.id,
        multiplier=1.0,
        created_by=None,
        modified_by=None,
    )
    db_session.add(g_unit)
    
    ml_unit = Unit(
        name=f"mL-{suffix}",
        description="Milliliter (base volume unit)",
        type=volume_type.id,
        multiplier=1.0,
        created_by=None,
        modified_by=None
    )
    db_session.add(ml_unit)
    
    mg_ml_unit = Unit(
        name=f"mg/mL-{suffix}",
        description="Milligram per milliliter (base concentration unit)",
        type=concentration_type.id,
        multiplier=1.0,
        created_by=None,
        modified_by=None
    )
    db_session.add(mg_ml_unit)
    
    # Create derived units
    mg_unit = Unit(
        name=f"mg-{suffix}",
        description="Milligram",
        type=mass_type.id,
        multiplier=0.001,  # 1 mg = 0.001 g
        created_by=None,
        modified_by=None
    )
    db_session.add(mg_unit)
    
    ug_unit = Unit(
        name=f"ug-{suffix}",
        description="Microgram",
        type=mass_type.id,
        multiplier=0.000001,  # 1 µg = 0.000001 g
        created_by=None,
        modified_by=None
    )
    db_session.add(ug_unit)
    
    db_session.commit()
    
    return {
        'g': g_unit,
        'mg': mg_unit,
        'ug': ug_unit,
        'ml': ml_unit,
        'mg_ml': mg_ml_unit
    }


def test_require_base_unit_is_the_multiplier_one(db_session, sample_units):
    base = require_base_unit(db_session, sample_units['g'].type)
    assert base.id == sample_units['g'].id


def test_designate_base_rescales_other_units(db_session, sample_units):
    """Picking milligrams as the base keeps 1 g == 1000 mg."""
    designate_base_unit(db_session, sample_units['mg'])
    db_session.flush()
    db_session.refresh(sample_units['g'])
    db_session.refresh(sample_units['mg'])
    db_session.refresh(sample_units['ug'])
    assert sample_units['mg'].multiplier == Decimal("1.0000000000")
    assert sample_units['g'].multiplier == Decimal("1000.0000000000")
    assert sample_units['ug'].multiplier == Decimal("0.0010000000")
    # 2 old-grams are 2000 of the new base (mg).
    assert convert_to_base_unit(2, str(sample_units['g'].id), db_session) == 2000


def test_designate_base_refuses_a_duplicate_multiplier(db_session, sample_units):
    from models.unit import Unit

    twin = Unit(
        name=f"g-twin-{uuid4().hex[:8]}",
        description="Same factor as the gram",
        type=sample_units['g'].type,
        multiplier=1,
        created_by=None,
        modified_by=None,
    )
    db_session.add(twin)
    db_session.flush()
    with pytest.raises(ConversionError, match="same multiplier"):
        designate_base_unit(db_session, sample_units['g'])


class TestCountSignificantFigures:
    """count_significant_figures backs the POST /results/validate sig-fig warning."""

    @pytest.mark.parametrize(
        "value,expected",
        [("123.456", 6), ("1200", 2), ("1200.", 4), ("0.00120", 3), ("0.0012", 2),
         ("1.20e3", 3), ("-45.0", 3), ("0", 1), ("abc", None)],
    )
    def test_counts(self, value, expected):
        from app.core.conversions import count_significant_figures
        assert count_significant_figures(value) == expected
