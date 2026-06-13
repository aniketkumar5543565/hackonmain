"""
Supabase JWT verification for FastAPI.

Supabase issues JWTs signed with HS256 using the project's JWT secret.
We verify them here without any custom password hashing — Supabase Auth
handles all of that on the frontend.
"""
import jwt
from jwt import PyJWTError

from app.config import settings


def verify_supabase_token(token: str) -> dict:
    """
    Decode and verify a Supabase-issued JWT.

    Returns the payload dict on success.
    Raises PyJWTError if the token is invalid or expired.

    Payload shape from Supabase:
        {
            "sub": "<user-uuid>",
            "email": "user@example.com",
            "role": "authenticated",
            "user_metadata": { "full_name": "...", "app_role": "student" | "professor" },
            "exp": <unix timestamp>,
            ...
        }
    """
    payload = jwt.decode(
        token,
        settings.SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        audience="authenticated",
    )
    return payload
