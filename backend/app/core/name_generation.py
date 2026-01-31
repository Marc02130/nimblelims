"""
Utility functions for generating entity names from configurable templates.

Templates support placeholders:
- {SEQ}: Auto-incrementing sequence per entity type (padded by template.seq_padding_digits)
- {YYYY}: 4-digit year
- {YY}: 2-digit year (e.g. '24' for 2024)
- {MM}: 2-digit month
- {DD}: 2-digit day
- {YYYYMMDD}: Date in YYYYMMDD format
- {CLIENT}: Client name/code (from linked client)
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from models.name_template import NameTemplate
import uuid


def get_active_template(db: Session, entity_type: str) -> Optional[NameTemplate]:
    """Get the active template for an entity type."""
    return db.query(NameTemplate).filter(
        NameTemplate.entity_type == entity_type,
        NameTemplate.active == True
    ).first()


def get_next_sequence(db: Session, entity_type: str) -> int:
    """
    Get the next sequence number for an entity type.
    Uses PostgreSQL sequences transactionally to avoid gaps.
    """
    sequence_name = f'name_template_seq_{entity_type}'
    result = db.execute(text(f"SELECT nextval('{sequence_name}')"))
    return result.scalar()


def check_name_uniqueness(db: Session, entity_type: str, name: str) -> bool:
    """
    Check if a generated name is unique for the entity type.
    
    Args:
        db: Database session
        entity_type: Type of entity (sample, project, batch, analysis, container)
        name: Generated name to check
    
    Returns:
        True if name is unique, False otherwise
    """
    # Map entity types to their model classes and table names
    entity_models = {
        'sample': ('Sample', 'samples'),
        'project': ('Project', 'projects'),
        'batch': ('Batch', 'batches'),
        'analysis': ('Analysis', 'analyses'),
        'container': ('Container', 'containers'),
    }
    
    if entity_type not in entity_models:
        return True  # Unknown entity type, assume unique
    
    table_name = entity_models[entity_type][1]
    # Check if name exists in the table
    result = db.execute(
        text(f"SELECT COUNT(*) FROM {table_name} WHERE name = :name"),
        {'name': name}
    )
    count = result.scalar()
    return count == 0


def generate_name(
    db: Session,
    entity_type: str,
    client_name: Optional[str] = None,
    reference_date: Optional[datetime] = None,
    max_retries: int = 10,
    **kwargs
) -> str:
    """
    Generate a unique name for an entity using the configured template.
    
    Args:
        db: Database session
        entity_type: Type of entity (sample, project, batch, analysis, container)
        client_name: Optional client name/code for {CLIENT} placeholder
        reference_date: Optional date to use for date placeholders (defaults to now)
        max_retries: Maximum number of retries if name is not unique
        **kwargs: Additional context for template placeholders
    
    Returns:
        Generated unique name string
    
    Raises:
        ValueError: If no active template found for entity_type
        RuntimeError: If unable to generate unique name after max_retries
    """
    template_obj = get_active_template(db, entity_type)
    if not template_obj:
        # Fallback to UUID if no template
        return str(uuid.uuid4())
    
    template = template_obj.template
    now = reference_date if reference_date else datetime.now()
    
    # Retry loop for uniqueness
    for attempt in range(max_retries):
        # Build replacement dictionary
        replacements: Dict[str, str] = {}
        
        # Date placeholders
        if '{YYYY}' in template:
            replacements['{YYYY}'] = str(now.year)
        if '{YY}' in template:
            replacements['{YY}'] = str(now.year % 100).zfill(2)
        if '{MM}' in template:
            replacements['{MM}'] = f"{now.month:02d}"
        if '{DD}' in template:
            replacements['{DD}'] = f"{now.day:02d}"
        if '{YYYYMMDD}' in template:
            replacements['{YYYYMMDD}'] = now.strftime('%Y%m%d')
        # Sequence placeholder: get seq_padding_digits from the template, fetch seq, then format
        if '{SEQ}' in template:
            seq_padding_digits = template_obj.seq_padding_digits or 1
            seq = get_next_sequence(db, entity_type)
            formatted_seq = str(seq).zfill(seq_padding_digits)
            replacements['{SEQ}'] = formatted_seq
        
        # Client placeholder
        if '{CLIENT}' in template:
            if client_name:
                # Use first 10 characters of client name, uppercase, no spaces
                client_code = client_name.upper().replace(' ', '').replace('-', '')[:10]
                replacements['{CLIENT}'] = client_code
            else:
                replacements['{CLIENT}'] = 'UNKNOWN'
        
        # Apply replacements
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        # Apply any additional kwargs replacements
        for key, value in kwargs.items():
            placeholder = f'{{{key.upper()}}}'
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        
        # Check uniqueness
        if check_name_uniqueness(db, entity_type, result):
            return result
        
        # If not unique and we have SEQ, try again with next sequence
        if '{SEQ}' in template:
            continue
    
    # If we exhausted retries, fallback to UUID
    return str(uuid.uuid4())


def generate_name_for_sample(
    db: Session,
    project_id: Optional[str] = None,
    received_date: Optional[datetime] = None,
    **kwargs
) -> str:
    """
    Generate a name for a sample, optionally using project's client.
    
    Args:
        db: Database session
        project_id: Optional project ID to get client name from
        received_date: Optional received date to use for date placeholders
        **kwargs: Additional context for template placeholders
    
    Returns:
        Generated sample name
    """
    client_name = None
    if project_id:
        from models.project import Project
        project = db.query(Project).filter(Project.id == project_id).first()
        if project and project.client:
            client_name = project.client.name
    
    return generate_name(
        db, 
        'sample', 
        client_name=client_name, 
        reference_date=received_date,
        **kwargs
    )


def generate_name_for_project(
    db: Session,
    client_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    **kwargs
) -> str:
    """
    Generate a name for a project, optionally using client.
    
    Args:
        db: Database session
        client_id: Optional client ID to get client name from
        start_date: Optional start date to use for date placeholders
        **kwargs: Additional context for template placeholders
    
    Returns:
        Generated project name
    """
    client_name = None
    if client_id:
        from models.client import Client
        client = db.query(Client).filter(Client.id == client_id).first()
        if client:
            client_name = client.name
    
    return generate_name(
        db, 
        'project', 
        client_name=client_name,
        reference_date=start_date,
        **kwargs
    )


def generate_name_for_batch(
    db: Session,
    start_date: Optional[datetime] = None,
    **kwargs
) -> str:
    """
    Generate a name for a batch.
    
    Args:
        db: Database session
        start_date: Optional start date to use for date placeholders
        **kwargs: Additional context for template placeholders
    
    Returns:
        Generated batch name
    """
    return generate_name(db, 'batch', reference_date=start_date, **kwargs)


def generate_name_for_analysis(
    db: Session,
    **kwargs
) -> str:
    """
    Generate a name for an analysis.
    
    Args:
        db: Database session
        **kwargs: Additional context for template placeholders
    
    Returns:
        Generated analysis name
    """
    return generate_name(db, 'analysis', **kwargs)


def generate_name_for_container(
    db: Session,
    **kwargs
) -> str:
    """
    Generate a name for a container.
    
    Args:
        db: Database session
        **kwargs: Additional context for template placeholders
    
    Returns:
        Generated container name
    """
    return generate_name(db, 'container', **kwargs)

