"""Helpers for fixtures that used to pass random uuid4() values into FK columns.

The test schema enforces foreign keys (list_entries, lists, users), so a mock
``uuid4()`` for a status/sample_type/matrix/list_id raises ForeignKeyViolation.
These helpers create a real, uniquely named List/ListEntry row instead.
"""
from uuid import uuid4

from models.list import List, ListEntry


def scratch_list_id(session):
    lst = List(name=f"scratch_list_{uuid4().hex[:8]}", description="test scratch list")
    session.add(lst)
    session.flush()
    return lst.id


def scratch_entry_id(session, name=None):
    entry = ListEntry(
        list_id=scratch_list_id(session),
        name=name or f"scratch_entry_{uuid4().hex[:8]}",
        description="test scratch entry",
    )
    session.add(entry)
    session.flush()
    return entry.id


def get_or_create_list_entry(session, list_name, entry_name):
    """Find/create entry_name in the list named list_name (lists are looked up by name)."""
    lst = session.query(List).filter(List.name == list_name).first()
    if not lst:
        lst = List(name=list_name, description=list_name)
        session.add(lst)
        session.flush()
    entry = (
        session.query(ListEntry)
        .filter(ListEntry.list_id == lst.id, ListEntry.name == entry_name)
        .first()
    )
    if not entry:
        entry = ListEntry(list_id=lst.id, name=entry_name, description=entry_name)
        session.add(entry)
        session.flush()
    return entry


def custom_attr(session, entity_type, attr_name, data_type="text"):
    """Register a custom attribute; PATCH rejects unknown custom_attributes keys."""
    from models.custom_attributes_config import CustomAttributeConfig

    cfg = CustomAttributeConfig(
        entity_type=entity_type,
        attr_name=attr_name,
        data_type=data_type,
    )
    session.add(cfg)
    session.flush()
    return cfg
