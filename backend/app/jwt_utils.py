import time
import jwt

# DEV ONLY secret (we will move to env later)
JWT_SECRET = "dev-secret-change-me"
JWT_ALG = "HS256"
JWT_EXP_SECONDS = 60 * 60 * 24  # 24 hours


def create_access_token(user_id: int, org_id: int, role: str) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "role": role,
        "iat": now,
        "exp": now + JWT_EXP_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def verify_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
