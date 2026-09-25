from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import crud

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

@router.post("/")
def create_subscription(tenant_id: int, package_id: int, db: Session = Depends(get_db)):
    return crud.create_subscription(db, tenant_id, package_id)

@router.get("/expiring")
def expiring_soon(days: int = 2, db: Session = Depends(get_db)):
    return crud.get_expiring_soon(db, days)