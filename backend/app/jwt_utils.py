import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

JWT_ALG = os.getenv("JWT_ALG", "HS256")

def _secret() -> str:
    s = os.getenv("JWT_SECRET", "")
    if not s:
        raise RuntimeError("JWT_SECRET not configured")
    return s

def create_access_token(user_id: int, org_id: int, role: str) -> str:
    """
    Backwards-compatible signature used by app/main.py and backups.
    Uses the SAME env JWT_SECRET as app/core/auth.py, and jose encoding.
    """
    now = datetime.now(timezone.utc)
    exp_minutes = int(os.getenv("JWT_EXPIRES_MINUTES", "120"))
    exp = now + timedelta(minutes=exp_minutes)

    payload = {
        "sub": str(user_id),
        "org_id": int(org_id) if org_id is not None else None,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALG)

def verify_token(token: str) -> dict:
    """
    Backwards-compatible: returns decoded payload dict or raises.
    """
    try:
        return jwt.decode(token, _secret(), algorithms=[JWT_ALG])
    except JWTError as e:
        raise ValueError("Invalid token") from e
