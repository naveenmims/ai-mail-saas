from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.models import User

router = APIRouter(tags=["auth"])

@router.get("/whoami")
def whoami(user: User = Depends(get_current_user)):
    return {"id": user.id, "org_id": user.org_id, "email": user.email, "role": user.role}
