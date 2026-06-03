from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query, status

from backend.app.core.security import get_current_user
from backend.app.models.user import User, UserRole


def require_role(*roles: str):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' does not have access. Required: {list(roles)}",
            )
        return current_user
    return role_checker


require_admin = require_role(UserRole.ADMIN.value)
require_manager_or_admin = require_role(UserRole.ADMIN.value, UserRole.MANAGER.value)
