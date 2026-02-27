from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.models import User

router = APIRouter(tags=["auth"])

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "org_id": user.org_id,
        "email": user.email,
        "role": user.role,
        "is_email_verified": user.is_email_verified,
        "created_at": str(user.created_at),
    }
