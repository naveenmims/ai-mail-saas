from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.models import User

router = APIRouter(tags=["auth"])

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    # Be defensive: different DB revisions may not have these columns yet
    return {
        "id": getattr(user, "id", None),
        "org_id": getattr(user, "org_id", None),
        "email": getattr(user, "email", None),
        "role": getattr(user, "role", None),
        "is_email_verified": getattr(user, "is_email_verified", None),
        "created_at": str(getattr(user, "created_at", "")),
    }
