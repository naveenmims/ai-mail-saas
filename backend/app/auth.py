from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from app.db import engine
from app.models import User
from app.jwt_utils import verify_token


def get_current_user(authorization: str = Header(None)) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    token = parts[1].strip()
    try:
        payload = verify_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    with Session(engine) as db:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
def require_roles(user: User, allowed_roles: list[str]) -> None:
    if user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Forbidden (role)")


def require_same_org(user: User, org_id: int) -> None:
    if user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Forbidden (org)")
