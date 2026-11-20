from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from routes.auth import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=6, max_length=200)
    role: str = Field(default="admin", pattern="^(admin|viewer)$")


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=100)
    role: str | None = Field(default=None, pattern="^(admin|viewer)$")
    is_active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=200)


def _serialize(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("/")
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    users = db.query(User).filter(User.organization_id == user.organization_id).order_by(User.created_at).all()
    return [_serialize(u) for u in users]


@router.post("/", status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Only admins can create users")
    existing = db.query(User).filter(User.organization_id == user.organization_id, User.username == data.username).first()
    if existing:
        raise HTTPException(409, "Username already taken")
    new_user = User(
        organization_id=user.organization_id,
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return _serialize(new_user)


@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Only admins can update users")
    target = db.query(User).filter(User.id == user_id, User.organization_id == user.organization_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    if data.username is not None:
        conflict = db.query(User).filter(
            User.organization_id == user.organization_id, User.username == data.username, User.id != user_id
        ).first()
        if conflict:
            raise HTTPException(409, "Username already taken")
        target.username = data.username
    if data.role is not None:
        target.role = data.role
    if data.is_active is not None:
        if target.id == user.id and not data.is_active:
            raise HTTPException(400, "Cannot deactivate yourself")
        target.is_active = data.is_active
    db.commit()
    db.refresh(target)
    return _serialize(target)


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Only admins can delete users")
    target = db.query(User).filter(User.id == user_id, User.organization_id == user.organization_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    if target.id == user.id:
        raise HTTPException(400, "Cannot delete yourself")
    db.delete(target)
    db.commit()
    return {"message": "User deleted"}


@router.put("/me/password")
def change_password(data: PasswordChange, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated"}
