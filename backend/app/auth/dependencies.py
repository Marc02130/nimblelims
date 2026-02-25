"""
Auth dependencies and permission lists for NimbleLIMS.
Centralizes get_current_user, get_user_permissions, and RBAC decorators.
"""
from typing import List

from app.core.security import (
    get_current_user,
    get_user_permissions,
    CORE_PERMISSIONS,
)
from app.core.rbac import (
    require_permission,
    require_any_permission,
    require_all_permissions,
    require_config_edit,
    require_workflow_execute,
    require_sample_create,
    require_sample_read,
    require_sample_update,
    require_sample_delete,
    require_test_assign,
    require_test_update,
    require_result_enter,
    require_result_review,
    require_result_read,
    require_result_update,
    require_result_delete,
    require_batch_manage,
    require_batch_read,
    require_batch_update,
    require_batch_delete,
    require_project_manage,
    require_project_read,
    require_user_manage,
    require_analysis_manage,
)

__all__ = [
    "get_current_user",
    "get_user_permissions",
    "CORE_PERMISSIONS",
    "ALL_PERMISSION_NAMES",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "require_config_edit",
    "require_workflow_execute",
    "require_sample_create",
    "require_sample_read",
    "require_sample_update",
    "require_sample_delete",
    "require_test_assign",
    "require_test_update",
    "require_result_enter",
    "require_result_review",
    "require_result_read",
    "require_result_update",
    "require_result_delete",
    "require_batch_manage",
    "require_batch_read",
    "require_batch_update",
    "require_batch_delete",
    "require_project_manage",
    "require_project_read",
    "require_user_manage",
    "require_analysis_manage",
]

# Full list of permission names (includes workflow:execute and all CORE_PERMISSIONS)
ALL_PERMISSION_NAMES: List[str] = list(CORE_PERMISSIONS)
