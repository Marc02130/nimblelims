"""PATCH bodies distinguish an omitted field from an explicit null.

``model_dump(exclude_unset=True)`` keeps a key the client sent as JSON null.
``exclude_none`` drops that key, so the column never changes. A null sent for
a NOT NULL column (or any extra name in ``refuse_null``) is 422. Nullable
columns receive the null and clear.
"""
from typing import Any, Iterable, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel


def explicit_updates(
    model: BaseModel,
    instance: Any = None,
    *,
    refuse_null: Iterable[str] = (),
) -> dict[str, Any]:
    """Return only the fields the client sent, including explicit nulls."""
    data = model.model_dump(exclude_unset=True)
    blocked = set(refuse_null)
    table = getattr(instance, "__table__", None)
    if table is not None:
        for key, value in data.items():
            column = table.columns.get(key)
            if value is None and column is not None and not column.nullable:
                blocked.add(key)
    refused = [name for name in data if data[name] is None and name in blocked]
    if refused:
        joined = ", ".join(refused)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{joined} cannot be cleared",
        )
    return data


def assign_updates(instance: Any, updates: dict[str, Any], *, skip: Optional[Iterable[str]] = None) -> None:
    """Set each sent field, including None, on the instance."""
    skipped = set(skip or ())
    for key, value in updates.items():
        if key in skipped:
            continue
        if hasattr(instance, key):
            setattr(instance, key, value)
