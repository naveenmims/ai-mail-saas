import os
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(*, subject: str, secret_key: str, expires_minutes: int = 60) -> str:
    """
    Creates HS256 JWT compatible with app/core/auth.py (jose decode).
    """
    env_secret = os.getenv("JWT_SECRET", "")
    # Safety: if env secret exists and differs, fail fast (prevents "Invalid token" confusion)
    if env_secret and env_secret != secret_key:
        raise RuntimeError("JWT secret mismatch: env JWT_SECRET differs from provided secret_key")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)

    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    return jwt.encode(payload, secret_key, algorithm="HS256")
