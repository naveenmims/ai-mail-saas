from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import os

from app.db import SessionLocal
from app.models import User
from app.core.security import verify_password, create_access_token

router = APIRouter(tags=["auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    email = str(payload.email).lower()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # IMPORTANT: models.py exposes DB column "password" as user.password_hash
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    jwt_secret = os.getenv("JWT_SECRET", "")
    if not jwt_secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET not configured")

    expires = int(os.getenv("JWT_EXPIRES_MINUTES", "60"))
    token = create_access_token(
        subject=str(user.id),
        secret_key=jwt_secret,
        expires_minutes=expires,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "org_id": user.org_id,
    }
