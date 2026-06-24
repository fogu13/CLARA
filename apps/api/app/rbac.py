"""RBAC enforcement — role-based access control for the FastAPI API.

Port of Elvis's app_role enum (owner/admin/editor/viewer) with actual
enforcement. Elvis had the schema but no UI or edge-fn enforcement;
CLARA_2 had no RBAC at all.

Usage:
  from app.rbac import require_role, Role

  @app.get("/admin/users")
  def list_users(user: UserContext = Depends(get_current_user),
                 _: None = Depends(require_role(Role.admin))):
      ...
"""

from __future__ import annotations

from enum import Enum

from fastapi import Depends, HTTPException

from app.auth import UserContext, get_current_user


class Role(str, Enum):  # noqa: UP042
    """Application roles — port of Elvis's app_role enum."""

    owner = "owner"
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


# Role hierarchy: owner > admin > editor > viewer
ROLE_LEVEL: dict[str, int] = {
    Role.owner.value: 4,
    Role.admin.value: 3,
    Role.editor.value: 2,
    Role.viewer.value: 1,
}


def require_role(min_role: Role):
    """FastAPI dependency factory: require the user to have at least min_role.

    Usage:
        @app.delete("/signals/{id}")
        def delete_signal(
            user: UserContext = Depends(get_current_user),
            _: None = Depends(require_role(Role.editor)),
        ):
            ...
    """

    def _check(user: UserContext = Depends(get_current_user)) -> None:  # noqa: B008
        user_role = user.role or "viewer"
        user_level = ROLE_LEVEL.get(user_role, 1)
        required_level = ROLE_LEVEL.get(min_role.value, 1)

        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role '{min_role.value}' or higher. You have '{user_role}'.",
            )

    return _check


def can_edit(user: UserContext) -> bool:
    """Check if a user can edit (editor or higher)."""
    return ROLE_LEVEL.get(user.role or "viewer", 1) >= ROLE_LEVEL[Role.editor.value]


def can_admin(user: UserContext) -> bool:
    """Check if a user can admin (admin or higher)."""
    return ROLE_LEVEL.get(user.role or "viewer", 1) >= ROLE_LEVEL[Role.admin.value]


def is_owner(user: UserContext) -> bool:
    """Check if a user is an owner."""
    return (user.role or "viewer") == Role.owner.value
