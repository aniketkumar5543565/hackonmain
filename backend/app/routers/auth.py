"""
Auth router.

Supabase handles email/password auth entirely on the frontend.
This router provides:
  POST /auth/sync-profile  — called once after Supabase sign-up to
                             create the user_profiles row with role.
  GET  /auth/me            — returns the current user's profile.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_supabase_token
from app.database import get_db
from app.dependencies import CurrentUser
from app.models.user import UserProfile
from app.schemas.auth import SyncProfileRequest, UserProfileOut

router = APIRouter(prefix="/auth", tags=["auth"])

bearer_scheme = HTTPBearer(auto_error=False)


@router.post(
    "/sync-profile",
    response_model=UserProfileOut,
    status_code=status.HTTP_200_OK,
    summary="Create or update the user profile after Supabase sign-up",
)
async def sync_profile(
    body: SyncProfileRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfileOut:
    """
    Called by the frontend immediately after Supabase signUp() succeeds.
    Creates the user_profiles row if it doesn't exist, or updates it if it does.
    The Supabase JWT is required to prove identity.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid Supabase token required",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    try:
        payload = verify_supabase_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (PyJWTError, KeyError, ValueError):
        raise credentials_exception

    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = UserProfile(
            id=user_id,
            email=body.email,
            full_name=body.full_name,
            role="STUDENT",  # All new users start as STUDENT; admins elevate roles
            is_demo=False,
            department_id=body.department_id,
            year_of_study=body.year_of_study,
        )
        db.add(profile)
    else:
        # Allow updating name and department context on re-sync
        profile.full_name = body.full_name
        if body.department_id:
            profile.department_id = body.department_id
        if body.year_of_study:
            profile.year_of_study = body.year_of_study

    await db.commit()
    await db.refresh(profile)
    out = UserProfileOut.model_validate(profile)
    out.roles = [ur.role.name for ur in profile.user_roles if ur.role] if profile.user_roles else []
    if not out.roles:
        out.roles = [profile.role]  # fallback to legacy role
    return out


@router.get(
    "/me",
    response_model=UserProfileOut,
    summary="Return the currently authenticated user's profile",
)
async def me(current_user: CurrentUser) -> UserProfileOut:
    out = UserProfileOut.model_validate(current_user)
    out.roles = [ur.role.name for ur in current_user.user_roles if ur.role] if current_user.user_roles else []
    if not out.roles:
        out.roles = [current_user.role]  # fallback to legacy role
    return out
