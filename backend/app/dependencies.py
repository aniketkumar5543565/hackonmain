"""
FastAPI dependency injection utilities.

Provides:
  - get_current_user  → validates Supabase JWT, returns UserProfile
  - require_role()    → factory for role-based access control guards
  - get_user_role_names() → returns list of role name strings for a user

Usage:
    @router.post("/admin/something")
    async def admin_endpoint(user = Depends(require_role("SUPER_ADMIN"))):
        ...

    @router.post("/hostel/menu")
    async def hostel_menu(user = Depends(require_role("SUPER_ADMIN", "HOSTEL_ADMIN", "HOSTEL_COORDINATOR"))):
        ...
"""
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_supabase_token
from app.database import get_db
from app.models.rbac import UserRole
from app.models.user import UserProfile

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfile:
    """
    Validate a Supabase-issued JWT and return the user's profile row.
    Returns 401 if the token is missing, expired, or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    try:
        payload = verify_supabase_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    result = await db.execute(
        select(UserProfile)
        .where(UserProfile.id == uuid.UUID(user_id))
        .options(selectinload(UserProfile.user_roles).selectinload(UserRole.role))
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User profile not found. Please complete registration.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return profile


async def get_user_role_names(user: UserProfile) -> list[str]:
    """Return list of role name strings for a user (from the join table)."""
    names: list[str] = []
    for ur in user.user_roles:
        if ur.role:
            names.append(ur.role.name)
    # Also include the legacy role field as fallback
    if user.role and user.role not in names:
        names.append(user.role)
    return names


def require_role(*roles: str):
    """
    Dependency factory that requires the current user to have at least one
    of the given role names. Raises 403 if none match.

    Example:
        Depends(require_role("SUPER_ADMIN", "ACADEMIC_ADMIN"))
    """
    async def _check(
        current_user: Annotated[UserProfile, Depends(get_current_user)],
    ) -> UserProfile:
        user_role_names = await get_user_role_names(current_user)
        if not any(r in user_role_names for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(roles)}",
            )
        return current_user

    return _check


# ── Pre-built dependency type aliases ─────────────────────────────────────── #

CurrentUser = Annotated[UserProfile, Depends(get_current_user)]

SuperAdmin = Annotated[UserProfile, Depends(require_role("SUPER_ADMIN"))]

AcademicWrite = Annotated[
    UserProfile,
    Depends(require_role("SUPER_ADMIN", "ACADEMIC_ADMIN")),
]

HostelWrite = Annotated[
    UserProfile,
    Depends(require_role("SUPER_ADMIN", "HOSTEL_ADMIN", "HOSTEL_COORDINATOR")),
]

MessWrite = Annotated[
    UserProfile,
    Depends(require_role("SUPER_ADMIN", "HOSTEL_ADMIN", "MESS_ADMIN")),
]

PlacementWrite = Annotated[
    UserProfile,
    Depends(require_role("SUPER_ADMIN", "PLACEMENT_ADMIN", "PLACEMENT_COORDINATOR")),
]

ClubWrite = Annotated[
    UserProfile,
    Depends(require_role("SUPER_ADMIN", "CLUB_ADMIN", "CLUB_COORDINATOR")),
]

FacultyWrite = Annotated[
    UserProfile,
    Depends(require_role("SUPER_ADMIN", "FACULTY")),
]
