"""
Utility functions for custom attributes validation and querying
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.custom_attributes_config import CustomAttributeConfig
from fastapi import HTTPException, status
from datetime import datetime


def validate_custom_attributes(
    db: Session,
    entity_type: str,
    custom_attributes: Optional[Dict[str, Any]],
    configs: Optional[List[CustomAttributeConfig]] = None
) -> Dict[str, Any]:
    """
    Validate custom_attributes against active configs for the given entity_type.
    
    Args:
        db: Database session
        entity_type: Entity type (e.g., 'samples', 'tests')
        custom_attributes: Dictionary of custom attributes to validate
        configs: Optional pre-fetched configs (if None, will fetch from DB)
    
    Returns:
        Validated and normalized custom_attributes dict
    
    Raises:
        HTTPException: If validation fails
    """
    if not custom_attributes:
        return {}
    
    # Fetch configs if not provided
    if configs is None:
        configs = db.query(CustomAttributeConfig).filter(
            and_(
                CustomAttributeConfig.entity_type == entity_type,
                CustomAttributeConfig.active == True
            )
        ).all()
    
    # Create a map of attr_name -> config for quick lookup
    config_map = {config.attr_name: config for config in configs}
    
    errors = []
    validated_attrs = {}
    
    # Validate each attribute
    for attr_name, attr_value in custom_attributes.items():
        if attr_name not in config_map:
            errors.append(f"Unknown custom attribute '{attr_name}' for entity type '{entity_type}'")
            continue
        
        config = config_map[attr_name]
        validated_value = _validate_attribute_value(attr_name, attr_value, config)
        if validated_value is None:
            errors.append(f"Invalid value for '{attr_name}': {attr_value}")
        else:
            validated_attrs[attr_name] = validated_value
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Custom attributes validation failed",
                "errors": errors
            }
        )
    
    return validated_attrs


def _validate_attribute_value(
    attr_name: str,
    value: Any,
    config: CustomAttributeConfig
) -> Optional[Any]:
    """
    Validate a single attribute value against its config.
    
    Returns:
        Validated and normalized value, or None if invalid
    """
    data_type = config.data_type
    validation_rules = config.validation_rules or {}
    
    # Type validation
    if data_type == "text":
        if not isinstance(value, str):
            return None
        if 'max_length' in validation_rules:
            if len(value) > validation_rules['max_length']:
                return None
        if 'min_length' in validation_rules:
            if len(value) < validation_rules['min_length']:
                return None
        return value
    
    elif data_type == "number":
        try:
            num_value = float(value) if isinstance(value, str) else value
            if not isinstance(num_value, (int, float)):
                return None
        except (ValueError, TypeError):
            return None
        
        if 'min' in validation_rules and num_value < validation_rules['min']:
            return None
        if 'max' in validation_rules and num_value > validation_rules['max']:
            return None
        return num_value
    
    elif data_type == "date":
        if isinstance(value, str):
            try:
                # Try parsing ISO format
                parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return parsed.date().isoformat()  # Return as ISO string for JSONB storage
            except (ValueError, AttributeError):
                try:
                    # Try parsing date-only format
                    from datetime import date
                    parsed = date.fromisoformat(value)
                    return parsed.isoformat()
                except (ValueError, AttributeError):
                    return None
        elif isinstance(value, datetime):
            return value.date().isoformat()
        elif hasattr(value, 'date'):  # date object
            return value.isoformat()
        else:
            return None
    
    elif data_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        if isinstance(value, (int, float)):
            return bool(value)
        return None
    
    elif data_type == "select":
        options = validation_rules.get('options', [])
        if value not in options:
            return None
        return value
    
    return None


def build_custom_attributes_filter(
    custom_attributes_column,
    filters: Dict[str, Any]
) -> List:
    """
    Build SQLAlchemy filter conditions for custom_attributes JSONB column.
    
    Args:
        custom_attributes_column: SQLAlchemy column for custom_attributes (e.g., Sample.custom_attributes)
        filters: Dictionary of custom attribute filters (e.g., {'ph_level': 7.0})
    
    Returns:
        List of SQLAlchemy filter conditions
    """
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import cast
    
    conditions = []
    
    for attr_name, attr_value in filters.items():
        # Use JSONB containment operator (@>) for filtering
        # This checks if the JSONB column contains the key-value pair
        filter_dict = {attr_name: attr_value}
        conditions.append(
            custom_attributes_column.op("@>")(cast(filter_dict, JSONB))
        )
    
    return conditions

