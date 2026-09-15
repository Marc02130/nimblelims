"""Predefined entry wrappers: catalog of functionality on the two entry kinds.

Cardinality, pairing, and mint are properties of the wrapper row — not
if-aliquot branches. Aliquot/pool is the first mint proof (cardinality 1).
n-instances and predecessor source_from are parked:
``.docs/internal/ideas/aliquot-pool-multiple-pairs.md``.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, Optional, Tuple

WRAPPER_CATALOG: Dict[str, Dict[str, Any]] = {
    "aliquot_pool": {
        "keys": ("aliquot_pool_plan", "aliquots_pools"),
        "cardinality": 1,
        "atomic_pair": True,
        "mint": True,
        "source_from": "start_cohort",
        "add_label": "Aliquot/pool",
    },
    "experiment_header": {
        "keys": ("experiment_header",),
        "cardinality": 1,
        "atomic_pair": False,
        "mint": False,
        "add_label": "Header",
    },
    "samples": {
        "keys": ("samples",),
        "cardinality": 1,
        "atomic_pair": False,
        "mint": False,
        "add_label": "Samples",
    },
}

_KEY_TO_WRAPPER = {
    key: wrapper_id
    for wrapper_id, spec in WRAPPER_CATALOG.items()
    for key in spec["keys"]
}


def wrapper_id_for_key(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    return _KEY_TO_WRAPPER.get(key)


def wrapper_mate_key(key: Optional[str]) -> Optional[str]:
    """Other key in an atomic-pair wrapper; None for single-key wrappers."""
    wrapper_id = wrapper_id_for_key(key)
    if not wrapper_id:
        return None
    spec = WRAPPER_CATALOG[wrapper_id]
    if not spec.get("atomic_pair"):
        return None
    keys: Tuple[str, ...] = spec["keys"]
    if key not in keys or len(keys) != 2:
        return None
    return keys[0] if key == keys[1] else keys[1]


def wrapper_role_taken(
    key: Optional[str], existing_keys: Iterable[Optional[str]]
) -> bool:
    """True when this wrapper role key is already present (cardinality 1 per key)."""
    if not key or wrapper_id_for_key(key) is None:
        return False
    return key in {k for k in existing_keys if k}


def wrapper_over_capacity_id(keys: Iterable[Optional[str]]) -> Optional[str]:
    """Return wrapper_id if any role key appears more than that wrapper's cardinality."""
    counts = Counter(k for k in keys if k)
    for wrapper_id, spec in WRAPPER_CATALOG.items():
        cap = spec["cardinality"]
        for key in spec["keys"]:
            if counts[key] > cap:
                return wrapper_id
    return None


def wrapper_at_capacity_detail(wrapper_id: str) -> Dict[str, Any]:
    spec = WRAPPER_CATALOG[wrapper_id]
    label = spec.get("add_label") or wrapper_id
    return {
        "code": "wrapper_at_capacity",
        "wrapper_id": wrapper_id,
        "message": (
            f"This experiment or template already has the {label} wrapper "
            f"(at most {spec['cardinality']} instance). "
            "Delete it before adding another."
        ),
    }
