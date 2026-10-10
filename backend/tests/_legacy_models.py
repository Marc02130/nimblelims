"""Test-only compatibility shims for models that were folded into other modules.

Older test modules were written against ``models.role``, ``models.permission``,
``models.role_permission`` and ``models.container_type``. Those modules were
removed when Role/Permission moved into ``models.user`` (with a plain
``role_permissions`` association Table) and ContainerType moved into
``models.container``. Rather than rewrite every fixture, this module exposes a
small ``RolePermission`` class mapped imperatively onto the association table so
``RolePermission(role_id=..., permission_id=...)`` and joins against
``RolePermission.role_id`` keep working. It is not used by application code.
"""
from sqlalchemy.orm import registry

from models.user import role_permissions

_registry = registry()


class RolePermission:
    def __init__(self, role_id=None, permission_id=None):
        self.role_id = role_id
        self.permission_id = permission_id


_registry.map_imperatively(RolePermission, role_permissions)
