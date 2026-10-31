from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User
from routes.auth import get_current_user
import crud

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

@router.post("/")
def create_subscription(tenant_id: int, package_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subscription = crud.create_subscription(db, user.organization_id, tenant_id, package_id)
    if not subscription:
        raise HTTPException(404, "Tenant or package not found")
    return subscription

@router.get("/expiring")
def expiring_soon(days: int = 2, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return crud.get_expiring_soon(db, user.organization_id, days)