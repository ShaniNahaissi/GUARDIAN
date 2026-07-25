from __future__ import annotations

from typing import FrozenSet

CAMERAS_READ = "cameras:read"
CAMERAS_WRITE = "cameras:write"
STATS_READ = "stats:read"

ROLE_PERMISSIONS: dict[str, FrozenSet[str]] = {
    # ponytail: every role gets full self-service camera/stats permissions now;
    # "admin" is distinguished only by the separate get_admin_user gate on
    # /api/admin/users (managing OTHER users), not by these permissions.
    "admin": frozenset({CAMERAS_READ, CAMERAS_WRITE, STATS_READ}),
    "operator": frozenset({CAMERAS_READ, CAMERAS_WRITE, STATS_READ}),
    "viewer": frozenset({CAMERAS_READ, CAMERAS_WRITE, STATS_READ}),
}

VALID_ROLES = frozenset(ROLE_PERMISSIONS.keys())


def permissions_for_role(role: str) -> FrozenSet[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def role_has(role: str, permission: str) -> bool:
    return permission in permissions_for_role(role)
