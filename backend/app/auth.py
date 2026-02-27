"""
Compatibility wrapper.

Older routes imported get_current_user from app/auth.py.
The canonical implementation is now app/core/auth.py (FastAPI-native HTTPBearer).
"""
from app.core.auth import get_current_user  # re-export

# Keep these helpers as-is (they are still useful)
from fastapi import HTTPException

def require_roles(user, allowed_roles: list[str]) -> None:
    if getattr(user, "role", None) not in allowed_roles:
        raise HTTPException(status_code=403, detail="Forbidden (role)")

def require_same_org(user, org_id: int) -> None:
    if getattr(user, "org_id", None) != org_id:
        raise HTTPException(status_code=403, detail="Forbidden (org)")
