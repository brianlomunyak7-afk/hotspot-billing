import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import Organization, User

router = APIRouter(prefix="/auth", tags=["Auth"])
JWT_ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt, expected = encoded.split("$", 1)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240_000).hex()
    return hmac.compare_digest(actual, expected)


def create_access_token(user: User) -> str:
    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY must be configured")
    expires = datetime.now(timezone.utc) + timedelta(hours=int(os.getenv("ACCESS_TOKEN_HOURS", "12")))
    return jwt.encode({"sub": str(user.id), "org": user.organization_id, "role": user.role, "exp": expires},
                      secret, algorithm=JWT_ALGORITHM)


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username, User.is_active.is_(True)).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return {"access_token": create_access_token(user), "token_type": "bearer", "organization_id": user.organization_id}


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=500, detail="Authentication is not configured")
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], secret, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (ValueError, KeyError, jwt.PyJWTError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User is inactive or missing")
    return user


def verify_token(user: User = Depends(get_current_user)) -> str:
    return str(user.id)


def get_public_organization(slug: str | None = None, db: Session = Depends(get_db)) -> Organization:
    slug = slug or os.getenv("DEFAULT_ORGANIZATION_SLUG", "default")
    organization = db.query(Organization).filter(Organization.slug == slug, Organization.is_active.is_(True)).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Business account not found")
    return organization
